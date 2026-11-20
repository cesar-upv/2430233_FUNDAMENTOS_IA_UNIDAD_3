"""Campaign coverage, immutable evidence, crash recovery and real CLI integration."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import zipfile

import pytest

from src.graphs import GraphError, load_fhcp_graph
from src.cli import distributed_campaign as campaign
from src.cli.campaign_evidence import atomic_json, audit_attempt, read_json
from src.cli.campaign_system import exclusive_lock
from src.cli.dataset_catalog import build_catalog
from src.cli.distributed_plan import (
    ROOT, CATALOG, PRESETS, attempt_keys, attempt_name, check_installation,
    digest, make_plan, partition, source_inventory, validate_plan,
)


def seal(plan):
    plan.pop('plan_sha256', None)
    plan['plan_sha256'] = digest(plan)
    return plan


@pytest.fixture
def setup(tmp_path, monkeypatch):
    root = tmp_path / 'checkout'
    root.mkdir()
    shutil.copytree(ROOT / 'src', root / 'src', ignore=shutil.ignore_patterns('__pycache__'))
    (root / 'docs/decisions').mkdir(parents=True)
    (root / 'experiments/configs').mkdir(parents=True)
    shutil.copy2(ROOT / PRESETS, root / PRESETS)
    original = read_json(ROOT / 'docs/decisions/fhcp-instances.json')
    atomic_json(root / 'docs/decisions/fhcp-instances.json', original)
    data = root / 'data/raw/FHCPCS'
    data.mkdir(parents=True)
    payload = b'TYPE : HCP\nDIMENSION : 3\nEDGE_DATA_FORMAT : EDGE_LIST\nEDGE_DATA_SECTION\n1 2\n2 3\n3 1\n-1\nEOF\n'
    (data / 'graph1.hcp').write_bytes(payload)
    atomic_json(root / CATALOG, build_catalog(root, count=1))
    plan = make_plan(['Arturo2430'], root, expected_count=1)
    plan['seeds'] = [1001]
    plan['budget']['max_elapsed_ns'] = 200_000_000
    plan['process_timeout_seconds'] = 10
    seal(plan)
    monkeypatch.setattr(campaign, 'observation', lambda: {'ac_online': True, 'available_ram_bytes': 8 * 1024**3})
    return root, plan, tmp_path / 'results'


def failed_attempt(plan, key, directory, root):
    directory.mkdir()
    atomic_json(directory / 'intent.json', {'plan_sha256': plan['plan_sha256'], 'key': list(key)})
    (directory / 'stdout.json').write_text('')
    (directory / 'stderr.log').write_text('timeout evidence')
    atomic_json(directory / 'exit.json', {'reason': 'external_timeout', 'returncode': -9, 'process_seconds': 90})
    return False


def test_catalog_complete_and_historical_selection_unchanged():
    catalog = read_json(ROOT / CATALOG)
    assert len(catalog['instances']) == 1001
    assert [e['id'] for e in catalog['instances']] == [f'graph{i}' for i in range(1, 1002)]
    assert len(read_json(ROOT / 'docs/decisions/fhcp-instances.json')['instances']) == 9
    graph = load_fhcp_graph('graph3', manifest=CATALOG)
    assert (graph.vertex_count(), graph.edge_count()) == (78, 117)
    with pytest.raises(GraphError, match='manifest_mismatch'):
        load_fhcp_graph('graph3')


def test_partition_covers_all_graphs_once_and_balances_counts():
    entries = read_json(ROOT / CATALOG)['instances']
    owners = ['one', 'two', 'three', 'four', 'five']
    assigned = partition(entries, owners)
    all_ids = [name for ids in assigned.values() for name in ids]
    assert len(all_ids) == len(set(all_ids)) == 1001
    assert max(map(len, assigned.values())) - min(map(len, assigned.values())) <= 1
    assert assigned == partition(list(reversed(entries)), owners)
    historical = {entry['id'] for entry in read_json(ROOT / 'docs/decisions/fhcp-instances.json')['instances']}
    assert historical <= set(all_ids)


@pytest.mark.parametrize('members', [[], ['a', 'a'], ['../bad'], ['a/b'], [''], ['a', 'b']])
def test_invalid_or_excess_members_rejected(setup, members):
    root, _, _ = setup
    with pytest.raises(ValueError):
        make_plan(members, root, expected_count=1)


def test_approved_budget_is_time_only_and_10_seeds(setup):
    root, _, _ = setup
    plan = make_plan(['Arturo2430'], root, expected_count=1)
    assert plan['budget'] == {'max_elapsed_ns': 60_000_000_000, 'max_evaluations': None, 'max_iterations': None}
    assert plan['seeds'] == list(range(1001, 1011))
    assert len(list(attempt_keys(plan, 'Arturo2430'))) == 60
    assert plan['process_timeout_seconds'] == 120
    assert plan['goal_distinct_solved_graphs'] == 60
    command = campaign.child_command(plan, ('graph1', 'abc', 1001), root)
    assert command[command.index('--max-elapsed-ns') + 1] == '60000000000'
    assert '--max-evaluations' not in command
    assert '--catalog' in command and '--cost-mode' in command


def test_current_shared_plan_preserves_graphs_and_solver_parameters():
    original = read_json(ROOT / 'experiments/configs/distributed-fhcp-15x30.json')
    current = read_json(ROOT / 'experiments/configs/distributed-fhcp-10x60.json')
    check_installation(current)
    assert current['campaign_id'] != original['campaign_id']
    assert current['plan_sha256'] != original['plan_sha256']
    assert current['assignments'] == original['assignments']
    assert current['instances'] == original['instances']
    assert current['solvers'] == original['solvers']
    assert current['seeds'] == list(range(1001, 1011))
    assert current['budget'] == {'max_elapsed_ns': 60_000_000_000,
                                 'max_evaluations': None, 'max_iterations': None}
    assert current['process_timeout_seconds'] == 120
    assert sum(len(list(attempt_keys(current, m))) for m in current['assignments']) == 60_060


@pytest.mark.parametrize('mutation', ['hash', 'overlap', 'missing', 'seeds', 'budget', 'families', 'params'])
def test_corrupt_plan_rejected(setup, mutation):
    _, original, _ = setup
    plan = deepcopy(original)
    if mutation == 'hash':
        plan['purpose'] = 'changed'
    elif mutation == 'overlap':
        plan['assignments']['other'] = ['graph1']
    elif mutation == 'missing':
        plan['assignments']['Arturo2430'] = []
    elif mutation == 'seeds':
        plan['seeds'] *= 2
    elif mutation == 'budget':
        plan['budget']['max_elapsed_ns'] = -1
    elif mutation == 'families':
        plan['solvers'].pop()
    else:
        plan['solvers'][0]['parameters']['population_size'] = -1
    if mutation != 'hash':
        seal(plan)
    with pytest.raises(ValueError):
        validate_plan(plan)


def test_input_hash_and_code_changes_rejected(setup):
    root, plan, _ = setup
    campaign.verify_inputs(plan, 'Arturo2430', root)
    graph = root / 'data/raw/FHCPCS/graph1.hcp'
    graph.write_bytes(graph.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='instance'):
        campaign.verify_inputs(plan, 'Arturo2430', root)
    module = root / 'src/graphs/fhcp.py'
    module.write_text(module.read_text() + '\n')
    with pytest.raises(ValueError, match='Source'):
        check_installation(plan, root)


def test_exclusive_lock_rejects_second_owner_and_releases(tmp_path):
    path = tmp_path / 'lock'
    with exclusive_lock(path):
        with pytest.raises(ValueError, match='holds'):
            with exclusive_lock(path):
                pytest.fail('Acquired a held lock')
    with exclusive_lock(path):
        pass


def test_real_cli_pause_resume_combine_and_zip(setup):
    root, plan, output = setup
    first = campaign.run_campaign(plan, 'Arturo2430', output, root=root, max_attempts=2)
    assert first['attempted'] == first['successes'] == 2
    assert first['distinct_solved_graphs'] == 1
    original_stdout = {p: p.read_bytes() for p in (output / 'attempts').glob('*/stdout.json')}
    final = campaign.run_campaign(plan, 'Arturo2430', output, root=root)
    assert final['attempted'] == final['planned'] == final['successes'] == 6
    assert final['errors'] == 0
    assert final['distinct_solved_graphs'] == 1 and final['solved_graph_ids'] == ['graph1']
    assert all(p.read_bytes() == payload for p, payload in original_stdout.items())
    assert len(list((output / 'sessions').glob('*.json'))) == 2
    merged = campaign.combine(plan, [output], output.parent / 'combined', root)
    assert merged['successes'] == 6
    archive = output.parent / 'results.zip'
    checksum = campaign.package(output, archive)
    assert checksum == sha256(archive.read_bytes()).hexdigest()
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        assert len([name for name in zipped.namelist() if name.endswith('stdout.json')]) == 6
    with pytest.raises(FileExistsError):
        campaign.package(output, archive)


def test_external_timeouts_stay_in_denominator(setup, monkeypatch):
    root, plan, output = setup
    monkeypatch.setattr(campaign, 'execute_attempt', failed_attempt)
    summary = campaign.run_campaign(plan, 'Arturo2430', output, root=root)
    assert summary['planned'] == summary['attempted'] == summary['errors'] == 6
    assert sum(c['external_timeouts'] for c in summary['cells']) == 6
    assert summary['successes'] == 0


@pytest.mark.parametrize('intent_exists', [True, False])
def test_crash_reservation_preserved_without_retry(setup, monkeypatch, intent_exists):
    root, plan, output = setup
    monkeypatch.setattr(campaign, 'execute_attempt', failed_attempt)
    campaign.run_campaign(plan, 'Arturo2430', output, root=root, max_attempts=1)
    attempt = next((output / 'attempts').iterdir())
    (attempt / 'audit.json').unlink()
    (attempt / 'exit.json').unlink()
    if not intent_exists:
        (attempt / 'intent.json').unlink()
    before = (attempt / 'stdout.json').read_bytes()
    result = campaign.run_campaign(plan, 'Arturo2430', output, root=root)
    assert result['attempted'] == 6
    audit = read_json(attempt / 'audit.json')
    assert audit['stop_reason'] == 'interrupted_without_exit'
    assert (attempt / 'stdout.json').read_bytes() == before


def test_tampered_artifact_stops_resume_and_combine(setup, monkeypatch):
    root, plan, output = setup
    monkeypatch.setattr(campaign, 'execute_attempt', failed_attempt)
    campaign.run_campaign(plan, 'Arturo2430', output, root=root, max_attempts=1)
    next((output / 'attempts').glob('*/stderr.log')).write_text('changed')
    with pytest.raises(ValueError, match='Changed artifact'):
        campaign.run_campaign(plan, 'Arturo2430', output, root=root)
    with pytest.raises(ValueError, match='Changed artifact'):
        campaign.combine(plan, [output], output.parent / 'combined', root)


def test_duplicate_member_outputs_rejected(setup, monkeypatch):
    root, plan, output = setup
    monkeypatch.setattr(campaign, 'execute_attempt', failed_attempt)
    campaign.run_campaign(plan, 'Arturo2430', output, root=root, max_attempts=1)
    duplicate = output.parent / 'duplicate'
    shutil.copytree(output, duplicate)
    with pytest.raises(ValueError, match='Duplicate'):
        campaign.combine(plan, [output, duplicate], output.parent / 'combined', root)


def test_changed_seed_count_or_budget_cannot_resume_or_combine(setup, monkeypatch):
    root, original, output = setup
    monkeypatch.setattr(campaign, 'execute_attempt', failed_attempt)
    campaign.run_campaign(original, 'Arturo2430', output, root=root, max_attempts=1)
    current = deepcopy(original)
    current['seeds'] = list(range(1001, 1011))
    current['budget']['max_elapsed_ns'] = 60_000_000_000
    current['process_timeout_seconds'] = 120
    seal(current)
    with pytest.raises(ValueError, match='different plan'):
        campaign.run_campaign(current, 'Arturo2430', output, root=root)
    with pytest.raises(ValueError, match='plans differ'):
        campaign.combine(current, [output], output.parent / 'combined', root)
    assert len(list((output / 'attempts').iterdir())) == 1


def test_changed_machine_rejected_on_resume(setup, monkeypatch):
    root, plan, output = setup
    monkeypatch.setattr(campaign, 'execute_attempt', failed_attempt)
    campaign.run_campaign(plan, 'Arturo2430', output, root=root, max_attempts=1, machine='machine-one')
    with pytest.raises(ValueError, match='Machine/member changed'):
        campaign.run_campaign(plan, 'Arturo2430', output, root=root, machine='machine-two')


def test_ac_pause_admits_no_attempts(setup, monkeypatch):
    root, plan, output = setup
    monkeypatch.setattr(campaign, 'observation', lambda: {'ac_online': False, 'available_ram_bytes': 8 * 1024**3})
    result = campaign.run_campaign(plan, 'Arturo2430', output, root=root)
    assert result['attempted'] == 0 and result['planned'] == 6
    assert not list((output / 'attempts').iterdir())


def test_pack_inside_source_rejected(setup, monkeypatch):
    root, plan, output = setup
    monkeypatch.setattr(campaign, 'execute_attempt', failed_attempt)
    campaign.run_campaign(plan, 'Arturo2430', output, root=root, max_attempts=1)
    with pytest.raises(ValueError, match='outside'):
        campaign.package(output, output / 'bad.zip')


@pytest.mark.parametrize('mutation', ['route', 'cost', 'seed', 'parameters', 'budget', 'source', 'late', 'status'])
def test_independent_audit_rejects_forged_success(setup, mutation):
    root, plan, output = setup
    output.mkdir()
    key = ('graph1', 'ga', 1001)
    directory = output / attempt_name(key)
    campaign.execute_attempt(plan, key, directory, root)
    assert audit_attempt(directory, plan, key, root=root)['certified_success']
    record = read_json(directory / 'stdout.json')
    if mutation == 'route':
        record['result']['best_route'] = [0, 0, 2]
    elif mutation == 'cost':
        record['result']['best_cost'] = 1
    elif mutation == 'seed':
        record['randomness']['seed_decimal'] = '999'
    elif mutation == 'parameters':
        record['procedure']['parameters']['mutation_rate'] = 0.2
    elif mutation == 'budget':
        record['budget']['max_elapsed_ns'] += 1
    elif mutation == 'source':
        record['procedure']['implementation_version'] = 'sha256:' + '0' * 64
    elif mutation == 'late':
        record['result']['timing']['first_success']['elapsed_ns'] = plan['budget']['max_elapsed_ns'] + 1
    else:
        record['result']['status'] = 'exhausted'
    atomic_json(directory / 'stdout.json', record)
    audit = audit_attempt(directory, plan, key, root=root)
    assert audit['status'] == 'error' and audit['stop_reason'] == 'invalid_evidence'
    assert not audit['certified_success']


def test_resume_rejects_worker_that_is_still_alive(setup, monkeypatch):
    root, plan, output = setup
    monkeypatch.setattr(campaign, 'execute_attempt', failed_attempt)
    campaign.run_campaign(plan, 'Arturo2430', output, root=root, max_attempts=1)
    directory = next((output / 'attempts').iterdir())
    (directory / 'audit.json').unlink()
    (directory / 'exit.json').unlink()
    atomic_json(directory / 'worker.json', {'pid': 1234, 'birth': 'same'})
    monkeypatch.setattr(campaign, 'process_identity', lambda pid: 'same')
    with pytest.raises(ValueError, match='still be active'):
        campaign.run_campaign(plan, 'Arturo2430', output, root=root)


def test_combination_reports_missing_members_as_pending(setup, monkeypatch):
    root, plan, output = setup
    graph2 = root / 'data/raw/FHCPCS/graph2.hcp'
    graph2.write_bytes((root / 'data/raw/FHCPCS/graph1.hcp').read_bytes())
    atomic_json(root / CATALOG, build_catalog(root, count=2))
    plan = make_plan(['Arturo2430', 'ZapataFrame'], root, expected_count=2)
    plan['seeds'] = [1001]
    seal(plan)
    monkeypatch.setattr(campaign, 'execute_attempt', failed_attempt)
    campaign.run_campaign(plan, 'Arturo2430', output, root=root, max_attempts=1)
    summary = campaign.combine(plan, [output], output.parent / 'combined', root)
    assert summary['planned'] == 12 and summary['attempted'] == 1
    assert sum(cell['pending'] for cell in summary['cells']) == 11
    assert read_json(output.parent / 'combined/inputs.json')['members_missing'] == ['ZapataFrame']


def test_issue_handoff_preserves_assignment_and_never_overwrites(setup):
    root, _, output = setup
    plan = make_plan(['Arturo2430'], root, expected_count=1)
    assert campaign.handoff(plan, output) == 1
    text = (output / 'Arturo2430.md').read_text()
    assert plan['plan_sha256'] in text and 'graph1' in text
    assert '60 intentos' in text and '10 semillas (1001, 1002' in text
    assert '60 s de solver' in text and '120 s externos' in text
    assert 'Techo de búsqueda: 1.00 h' in text
    assert '.venv\\Scripts\\python.exe' in text
    with pytest.raises(FileExistsError):
        campaign.handoff(plan, output)


def test_issue_handoff_uses_the_supplied_budget_instead_of_the_default(setup):
    _, plan, output = setup
    plan['budget']['max_elapsed_ns'] = 30_000_000_000
    plan['process_timeout_seconds'] = 90
    plan['seeds'] = list(range(1001, 1016))
    seal(plan)
    campaign.handoff(plan, output)
    text = (output / 'Arturo2430.md').read_text()
    assert '90 intentos' in text and '15 semillas' in text
    assert '30 s de solver' in text and '90 s externos' in text
    assert 'Techo de búsqueda: 0.75 h' in text


def test_case_insensitive_duplicate_members_rejected(setup):
    root, _, _ = setup
    with pytest.raises(ValueError):
        make_plan(['Arturo2430', 'arturo2430'], root, expected_count=2)


def test_explicit_graph_quota_covers_all_graphs_and_balances_remainder():
    entries = read_json(ROOT / CATALOG)['instances']
    members = ['Arturo2430', 'ZapataFrame', 'cesar-upv', 'KirbyStone69', 'ELIASDEJESUSZUNIGADELEON']
    assigned = partition(entries, members, {'Arturo2430': 220})
    assert len(assigned['Arturo2430']) == 220
    assert sorted(len(assigned[m]) for m in members[1:]) == [195, 195, 195, 196]
    all_ids = [name for group in assigned.values() for name in group]
    assert len(all_ids) == len(set(all_ids)) == 1001
    assert assigned == partition(list(reversed(entries)), members, {'Arturo2430': 220})


@pytest.mark.parametrize('quotas', [{'unknown': 1}, {'a': 0}, {'a': True}, {'a': 1001}, {'a': 1002}])
def test_invalid_graph_quotas_rejected(quotas):
    entries = read_json(ROOT / CATALOG)['instances']
    with pytest.raises(ValueError):
        partition(entries, ['a', 'b'], quotas)
