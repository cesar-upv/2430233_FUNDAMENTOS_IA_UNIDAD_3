"""Focused checks for the M6 plan and the batch supervisor."""

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from src.cli import batch
from src.cli.benchmark_plan import CONFIG, PROTOCOL, digest, expand_plan, load_config, read_json


ROOT = Path(__file__).resolve().parents[1]


def test_plan_uses_approved_identity_order_and_rejects_unapproved_config(tmp_path):
    config = load_config(ROOT, ROOT / CONFIG)
    for phase, count in (("smoke", 12), ("tuning", 120)):
        trials = expand_plan(config, phase)
        assert trials == expand_plan(config, phase)
        assert [t["ordinal"] for t in trials] == list(range(count))
        assert all(t["trial_id"] == digest(t["identity"]) for t in trials)
        assert [t["trial_id"] for t in trials] == sorted(
            (t["trial_id"] for t in trials),
            key=lambda value: (sha256(f"fhcp-m6-v1\n{phase}\n{value}".encode()).hexdigest(), value),
        )
    selection = {row["algorithm"]: row for row in config["configurations"] if row["config_id"].endswith("-c1")}
    for phase, count in (("evaluation", 720), ("scale", 180), ("verification", 6)):
        assert len(expand_plan(config, phase, selection)) == count
    with pytest.raises(ValueError, match="requires a complete freeze"):
        expand_plan(config, "evaluation")
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"protocol_id":"x","protocol_id":"y"}')
    with pytest.raises(ValueError, match="Duplicate JSON key"):
        load_config(ROOT, invalid)
    config["phases"]["smoke"]["budget"]["max_evaluations"] = 21
    invalid.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="differs"):
        load_config(ROOT, invalid)


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    shutil.copytree(ROOT / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
    for relative in (CONFIG, PROTOCOL, Path("docs/decisions/fhcp-instances.json"), Path(".gitignore")):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    for name in ("graph1", "graph2"):
        relative = Path("data/raw/FHCPCS") / f"{name}.hcp"
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, root / relative)
    for command in (["git", "init", "-q"], ["git", "add", "."], [
        "git", "-c", "user.name=FHCP test", "-c", "user.email=fhcp@example.invalid",
        "commit", "-qm", "fixture",
    ]):
        subprocess.run(command, cwd=root, check=True)
    return root


def _start(root):
    return batch.create_batch(root, root / CONFIG, "smoke", min(os.sched_getaffinity(0)))


def _assert_history(path, manifest):
    revision = manifest["revision"]
    current = manifest
    for number in reversed(range(revision)):
        prior = path / "manifest-history" / f"{number:06d}.json"
        assert sha256(prior.read_bytes()).hexdigest() == current["previous_manifest_sha256"]
        current = read_json(prior)
    assert current["status"] == "planned"


def test_preflight_keeps_unstarted_trials_pending(checkout, monkeypatch):
    path = _start(checkout)
    monkeypatch.setattr(batch, "_memory_available", lambda: 1)
    manifest = batch.resume_batch(checkout, path)
    assert manifest["status"] == "incomplete"
    assert all(row["state"] == "pending" and not row["attempts"] for row in manifest["trials"])
    assert manifest["deviations"][-1]["code"] == "insufficient_available_ram"
    assert len(manifest["trials"]) == 12
    assert not batch._git(checkout, "status", "--porcelain")
    _assert_history(path, manifest)


def test_smoke_uses_real_cli_and_resumes_without_duplicates(checkout, monkeypatch):
    path = _start(checkout)
    # Controlled integration fixture. The command-line preflight remains enabled.
    monkeypatch.setattr(batch, "_has_required_memory", lambda *args: True)
    manifest = batch.resume_batch(checkout, path)
    assert manifest["status"] == "complete"
    assert len(manifest["trials"]) == 12
    ids = set()
    for trial in manifest["trials"]:
        attempt, = trial["attempts"]
        assert trial["state"] == "finished" and attempt["outcome"] == "exhausted"
        assert attempt["exit_code"] == 0
        raw = (checkout / attempt["record_path"]).read_bytes()
        assert raw == (checkout / attempt["stdout_path"]).read_bytes()
        record = json.loads(raw)
        assert record["code"]["dirty"] is False
        assert record["run"]["batch_id"] is None
        assert attempt["run_id"] == record["run"]["run_id"]
        assert record["result"]["counters"]["evaluations_completed"] == 20
        ids.add(attempt["attempt_id"])
    assert len(ids) == 12
    resumed = batch.resume_batch(checkout, path)
    assert {a["attempt_id"] for t in resumed["trials"] for a in t["attempts"]} == ids
    _assert_history(path, resumed)


def test_interrupted_reservation_and_diagnostic_retry_keep_original(checkout, monkeypatch):
    path = _start(checkout)
    manifest = read_json(path / "manifest.json")
    trial = manifest["trials"][0]
    monkeypatch.setattr(batch, "_has_required_memory", lambda *args: True)

    def interrupted(*args):
        raise KeyboardInterrupt

    with monkeypatch.context() as context:
        context.setattr(batch, "_execute", interrupted)
        with pytest.raises(KeyboardInterrupt):
            batch.resume_batch(checkout, path)
    saved = read_json(path / "manifest.json")
    original = saved["trials"][0]["attempts"][0]
    assert original["state"] == "started"
    key = original["attempt_id"]
    (path / "attempts" / key / "stdout.partial").write_text("partial data")

    monkeypatch.setattr(batch, "command_for", lambda *args: [sys.executable, "-c", "raise SystemExit(3)"])
    resumed = batch.resume_batch(checkout, path)
    assert resumed["status"] == "incomplete"
    original, = resumed["trials"][0]["attempts"]
    assert original["state"] == "interrupted"
    assert original["stdout_path"].endswith("stdout.partial")
    with pytest.raises(ValueError, match="requires terminal supervisor evidence"):
        batch.resume_batch(checkout, path, close_ids=[key])
    # A terminal supervisor diagnostic may be recovered later, never fabricated
    # by merely asking the coordinator to close an unresolved reservation.
    batch._write_json(path / "attempts" / key / "process.json", {
        "outcome": "interrupted", "diagnostic": "synthetic terminal signal evidence",
        "exit_code": None, "signal": 9, "process_elapsed_ns": 123,
        "capture_write_ns": 0, "observed": {},
    })
    final = batch.resume_batch(checkout, path, retry_ids=[key], close_ids=[key])
    primary, retry = final["trials"][0]["attempts"]
    assert final["status"] == "complete"
    assert primary["role"] == "primary" and primary["outcome"] == "interrupted"
    assert retry["role"] == "diagnostic_retry" and retry["retry_of"] == key
    assert retry["outcome"] == "runtime_error" and retry["exit_code"] == 3
    assert (checkout / primary["stdout_path"]).read_text() == "partial data"
    assert trial["trial_id"] == final["trials"][0]["trial_id"]


def test_resume_recovers_completed_process_after_write_failure(checkout, monkeypatch):
    path = _start(checkout)
    monkeypatch.setattr(batch, "_has_required_memory", lambda *args: True)
    with monkeypatch.context() as context:
        def fail_once(*args, **kwargs):
            raise OSError("temporary artifact write failure")

        context.setattr(batch, "_finish", fail_once)
        with pytest.raises(OSError, match="temporary artifact write failure"):
            batch.resume_batch(checkout, path)
    interrupted = read_json(path / "manifest.json")
    first = interrupted["trials"][0]["attempts"][0]
    assert interrupted["status"] == "incomplete" and first["state"] == "started"
    assert interrupted["deviations"][-1]["code"] == "batch_error"

    manifest = batch.resume_batch(checkout, path)
    assert manifest["status"] == "complete"
    recovered, = manifest["trials"][0]["attempts"]
    assert recovered["attempt_id"] == first["attempt_id"]
    assert recovered["outcome"] == "exhausted" and recovered["record_sha256"]
    assert any(item["code"] == "batch_error" for item in manifest["deviations"])
    _assert_history(path, manifest)


def test_external_timeout_preserves_partial_output(tmp_path, monkeypatch):
    import fcntl

    attempt = {"command": [sys.executable, "-c", "import time; print('partial', flush=True); time.sleep(30)"],
               "variables": {}}
    with (tmp_path / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        batch._execute(ROOT, tmp_path, attempt, 400_000_000, (lock,))
    terminal = read_json(tmp_path / "process.json")
    assert terminal["outcome"] == "external_timeout"
    assert terminal["signal"] is not None
    assert (tmp_path / "stdout.partial").read_text().strip() == "partial"


def test_runtime_snapshot_includes_ingestion_and_shared_operators(checkout):
    before = batch._module_hashes(checkout)
    for name in ('src/graphs/readers.py', 'src/algorithms/permutation.py'):
        assert name in before
        path = checkout / name
        path.write_text(path.read_text() + '\n# changed dependency\n')
        assert batch._module_hashes(checkout)[name] != before[name]


def test_supervisor_kills_descendant_after_leader_exits(tmp_path):
    import time
    marker = tmp_path / 'escaped.txt'
    script = ('import subprocess,sys; subprocess.Popen([sys.executable,"-c",'
              f'"import time; from pathlib import Path; time.sleep(0.5); Path({str(marker)!r}).touch()"'
              '])')
    with (tmp_path / '.lock').open('a') as lock:
        batch._execute(ROOT, tmp_path, {'command': [sys.executable, '-c', script], 'variables': {}},
                       2_000_000_000, (lock,))
    time.sleep(0.7)
    assert not marker.exists()
    process = read_json(tmp_path / 'process.json')
    assert process['exit_code'] == 0 and process['capture_write_ns'] >= 0


@pytest.fixture
def tuning_evidence(tmp_path, monkeypatch):
    """Synthetic full tuning inventory: ten exhausted primaries per candidate."""
    from uuid import uuid4
    from src.graphs import Graph
    from src.cli.benchmark_plan import load_freeze

    config = load_config(ROOT, ROOT / CONFIG)
    root = tmp_path
    for relative in (CONFIG, PROTOCOL):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    directory = root / 'experiments/results' / str(uuid4())
    directory.mkdir(parents=True)
    graph = Graph([1, 2, 3], [(1, 2), (2, 3)])
    monkeypatch.setattr(batch, '_graph', lambda *args: graph)
    code = {'commit': 'a' * 40, 'dirty': False, 'modules': {}}
    env = {'environment_id': 'b' * 64}
    trials = expand_plan(config, 'tuning')
    entries = {e['config_id']: e for e in config['configurations']}
    for trial in trials:
        identity, entry = trial['identity'], entries[trial['config_id']]
        attempt_id, run_id = str(uuid4()), str(uuid4())
        adir = directory / 'attempts' / attempt_id
        adir.mkdir(parents=True)
        record = {
            'schema_version': 'fhcp-run-record/1', 'run': {'run_id': run_id},
            'instance': {'id': identity['instance_id'], 'sha256': identity['instance_sha256']},
            'procedure': {k: entry[k] for k in ('family', 'variant', 'parameters')},
            'randomness': {'seed_decimal': identity['seed_decimal']}, 'code': code,
            'budget': identity['budget'],
            'result': {'status': 'exhausted', 'stop_reason': 'evaluation_limit',
                       'success_within_budget': False, 'telemetry_complete': True,
                       'best_route': [0, 1, 2], 'best_cost': 1,
                       'counters': {'evaluations_started': 2000, 'evaluations_completed': 2000}},
        }
        batch._write_json(adir / 'run.json', record)
        batch._write_json(adir / 'process.json', {'exit_code': 0, 'signal': None,
                                                'outcome': None, 'diagnostic': None})
        artifacts = [dict(path=p.relative_to(root).as_posix(), sha256=sha256(p.read_bytes()).hexdigest())
                     for p in sorted(adir.iterdir())]
        trial.update(state='finished', attempts=[{
            'attempt_id': attempt_id, 'run_id': run_id, 'role': 'primary', 'state': 'finished',
            'outcome': 'exhausted', 'record_path': (adir / 'run.json').relative_to(root).as_posix(),
            'record_sha256': sha256((adir / 'run.json').read_bytes()).hexdigest(), 'artifacts': artifacts,
        }])
    manifest = dict(schema_version='fhcp-batch-manifest/1', batch_id=directory.name,
                    protocol_id=config['protocol_id'], phase='tuning', status='complete',
                    code=code, environment=env, expected_trials=120, trials=trials,
                    inputs=[], artifacts=[a for t in trials for a in t['attempts'][0]['artifacts']])
    selection = [dict(algorithm=e['algorithm'], config_id=e['config_id'], parameters=e['parameters'],
                      score=dict(successes=0, errors=0, mean_normalized_cost=1/3, ordinal=1))
                 for e in config['configurations'] if e['config_id'].endswith('-c1')]
    audit = root / 'audit.json'
    audit.write_text('{"synthetic":true}')
    freeze = dict(schema_version='fhcp-benchmark-freeze/1', protocol_id=config['protocol_id'],
                  created_at_utc='2026-11-12T00:00:00+00:00',
                  config_sha256=sha256((root / CONFIG).read_bytes()).hexdigest(),
                  protocol_sha256=sha256((root / PROTOCOL).read_bytes()).hexdigest(),
                  tuning_batches=[], selection=selection, code=code, environment=env,
                  seeds_decimal=config['phases']['evaluation']['seeds_decimal'],
                  budgets={p: config['phases'][p]['budget'] for p in ('evaluation', 'scale')},
                  artifacts=[{'path': 'audit.json', 'sha256': sha256(audit.read_bytes()).hexdigest()}])

    def validate():
        mpath = directory / 'manifest.json'
        batch._write_json(mpath, manifest)
        freeze['tuning_batches'] = [dict(batch_id=directory.name,
                                         manifest_path=mpath.relative_to(root).as_posix(),
                                         manifest_sha256=sha256(mpath.read_bytes()).hexdigest())]
        fpath = root / 'freeze.json'
        batch._write_json(fpath, freeze)
        return load_freeze(root, fpath, config, root / CONFIG)
    return manifest, freeze, validate


def test_freeze_accepts_ten_resolved_exhaustions_without_success_or_error(tuning_evidence):
    _, _, validate = tuning_evidence
    freeze, selected = validate()
    assert len(selected) == 6
    assert all(row['score']['successes'] + row['score']['errors'] == 0 for row in freeze['selection'])


@pytest.mark.parametrize('mutation', ['identity', 'missing_primary', 'unfinished', 'score', 'winner', 'corrupt'])
def test_freeze_rejects_unverified_or_changed_tuning(tuning_evidence, mutation):
    manifest, freeze, validate = tuning_evidence
    trial = manifest['trials'][0]
    if mutation == 'identity':
        trial['identity']['seed_decimal'] = '999'
    elif mutation == 'missing_primary':
        trial['attempts'] = []
    elif mutation == 'unfinished':
        trial['attempts'][0]['state'] = 'started'
    elif mutation == 'score':
        freeze['selection'][0]['score']['mean_normalized_cost'] = 0
    elif mutation == 'winner':
        freeze['selection'][0]['config_id'] = 'ga-c2'
        freeze['selection'][0]['score']['ordinal'] = 2
        freeze['selection'][0]['parameters']['mutation_rate'] = 0.1
    else:
        trial['attempts'][0]['record_sha256'] = '0' * 64
    with pytest.raises(ValueError):
        validate()


def test_terminal_keyboard_interrupt_stops_before_next_primary(checkout,monkeypatch):
    path=_start(checkout)
    monkeypatch.setattr(batch,'_has_required_memory',lambda *args:True)
    monkeypatch.setattr(batch,'command_for',lambda *args:[sys.executable,'-c','import time; time.sleep(30)'])
    def interrupt(*args):
        raise KeyboardInterrupt
    monkeypatch.setattr(batch,'_sample',interrupt)
    manifest=batch.resume_batch(checkout,path)
    assert manifest['status']=='incomplete'
    assert sum(len(t['attempts']) for t in manifest['trials'])==1
    first=manifest['trials'][0]['attempts'][0]
    assert first['state']=='finished' and first['outcome']=='interrupted'
    assert first['signal'] is not None
    assert all(t['state']=='pending' for t in manifest['trials'][1:])
