"""Known-value metrics and adversarial, fully controlled benchmark evidence."""

from copy import deepcopy
import json
from pathlib import Path
from statistics import stdev

import pytest

from src.cli.benchmark_plan import CONFIG, expand_plan, load_config
from src.cli.variants import VARIANTS
from src.evaluation.benchmark import aggregate, audit_batch, audit_record, distribution, read_json
from src.graphs import Graph, load_fhcp_graph

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / 'experiments/results/972e2ae0-f2f3-4375-91b7-ef10e9641b10/manifest.json'


@pytest.fixture
def evidence():
    manifest = read_json(SMOKE)
    trial = next(t for t in manifest['trials'] if t['identity']['algorithm']=='ga')
    record = read_json(ROOT / trial['attempts'][0]['record_path'])
    config = load_config(ROOT, ROOT / CONFIG)
    entry = next(e for e in config['configurations'] if e['config_id']==trial['config_id'])
    return manifest, trial, record, entry


def test_full_smoke_is_audited_without_using_its_certificates():
    config = load_config(ROOT, ROOT / CONFIG)
    manifest, rows = audit_batch(ROOT, SMOKE, config, expand_plan(config, 'smoke'),
                                {k:f'src/algorithms/{v.module}.py' for k,v in VARIANTS.items()})
    assert manifest['audit_complete']
    assert len(rows)==12 and all(not r['issues'] and r['outcome']=='exhausted' for r in rows)
    summaries = aggregate(manifest, rows)
    assert len(summaries)==12
    assert all(s['expected']==s['resolved']==1 and s['successes']==0 for s in summaries)
    assert all(s['success_time_seconds']['observed']==0 and s['success_time_seconds']['mean'] is None for s in summaries)


def test_distribution_uses_linear_quartiles_sample_variability_and_missing_counts():
    d = distribution([1, 2, None, 3, 8], 5)
    assert d == dict(observed=4, missing=1, mean=3.5, median=2.5,
                     q1=1.75, q3=4.25, sample_stdev=stdev([1,2,3,8]))
    assert distribution([], 2)['mean'] is None
    assert distribution([0],1)['sample_stdev'] is None


def _row(outcome, *, resolved=True, role='primary', seconds=None):
    return dict(identity=dict(instance_id='g', algorithm='ga', budget=dict(max_evaluations=10)),
                config_id='ga-c1', role=role, resolved=resolved, outcome=outcome,
                timings={'solver_ns': None if seconds is None else seconds*10**9,
                         'first_success_ns': 10**9 if outcome=='success' else None},
                counters={}, iteration_unit='generation', peak_rss_bytes=None)


def test_denominators_retries_timeouts_errors_and_success_times_are_separate():
    rows = [_row('success', seconds=2), _row('cooperative_timeout', seconds=10),
            _row('runtime_error'), _row('external_timeout'),
            _row('success', role='diagnostic_retry', seconds=1)]
    manifest=dict(status='complete',phase='evaluation', environment={'environment_id':'e'},code={'commit':'c'})
    summary, = aggregate(manifest,rows)
    assert summary['expected']==summary['resolved']==4 and summary['successes']==1
    assert summary['success_percent']==25
    assert summary['binary_sample_stdev']==pytest.approx(.5)
    assert summary['timings_seconds']['solver_ns']['mean']==6
    assert summary['timings_seconds']['solver_ns']['missing']==2
    assert summary['success_time_seconds']['mean']==1
    assert summary['temporal_censoring']==dict(cooperative=1,external_process_scope=1)
    assert summary['outcomes']['runtime_error']==1
    rows.append(_row('pending',resolved=False))
    summary, = aggregate({**manifest,'status':'incomplete'},rows)
    assert summary['success_percent'] is None and summary['provisional_lower_bound_percent']==20
    assert summary['pending']==1 and summary['expected']==5


@pytest.mark.parametrize('mutation', ['hash','identity','budget','cost','environment','counter','first_success'])
def test_record_rejects_contradictions(evidence, mutation):
    manifest, trial, record, entry = evidence
    graph=load_fhcp_graph(trial['identity']['instance_id'],root=ROOT)
    if mutation=='hash': record['procedure']['fitness_version']='sha256:'+'0'*64
    elif mutation=='identity': record['instance']['id']='graph999'
    elif mutation=='budget': record['budget']['max_evaluations']=21
    elif mutation=='cost': record['result']['best_cost']=0
    elif mutation=='environment': record['environment']['python_version']='unknown'
    elif mutation=='counter': record['result']['counters']['evaluations_started']=21
    else: record['result']['timing']['first_success']={'elapsed_ns':1}
    with pytest.raises(ValueError):
        audit_record(record,manifest,trial,entry,graph,'src/algorithms/genetic.py')


def test_success_and_late_certificate_are_distinguished(evidence):
    manifest,trial,record,entry=evidence
    graph=Graph([0,1,2],[(0,1),(1,2),(2,0)])
    record['instance'].update(n=3,m=3)
    result=record['result']
    result.update(status='success',success_within_budget=True,best_route=[0,1,2],best_cost=0,
                  validation={'valid':True},stop_reason='validated_cycle')
    result['counters'].update(evaluations_started=1,evaluations_completed=1,full_evaluations=1,
                              iterations_completed=0,validations_started=1,validations_completed=1)
    result['timing'].update(solver_ns=100,validation_ns=10,overrun_ns=0,
                            first_success=dict(elapsed_ns=50,evaluations_started=1,
                                               evaluations_completed=1,iterations_completed=0))
    assert audit_record(record,manifest,trial,entry,graph,'src/algorithms/genetic.py')=='success'
    limit=trial['identity']['budget']['max_elapsed_ns']
    result.update(status='exhausted',success_within_budget=False,stop_reason='time_limit')
    result['timing'].update(solver_ns=limit+10,overrun_ns=10,first_success=None)
    assert audit_record(record,manifest,trial,entry,graph,'src/algorithms/genetic.py')=='cooperative_timeout'
    result['timing']['first_success']={'elapsed_ns':limit+1}
    with pytest.raises(ValueError):
        audit_record(record,manifest,trial,entry,graph,'src/algorithms/genetic.py')


@pytest.mark.parametrize('mutation',['duplicate','inventory','missing_record','corrupt_record','pending'])
def test_manifest_conflicts_missing_and_corrupt_evidence(tmp_path,monkeypatch,mutation):
    # Keep a disposable copy; original scientific evidence is never modified.
    import shutil
    from src.evaluation import benchmark as module
    relative=SMOKE.parent.relative_to(ROOT)
    target=tmp_path/relative
    shutil.copytree(SMOKE.parent,target,ignore=shutil.ignore_patterns('analyses','.lock'))
    config=load_config(ROOT,ROOT/CONFIG)
    manifest=read_json(target/'manifest.json')
    trial=manifest['trials'][0]
    if mutation=='duplicate': trial['attempts'].append(deepcopy(trial['attempts'][0]))
    elif mutation=='inventory': trial['identity']['seed_decimal']='99'
    elif mutation=='missing_record': (tmp_path/trial['attempts'][0]['record_path']).unlink()
    elif mutation=='corrupt_record': (tmp_path/trial['attempts'][0]['record_path']).write_text('{}')
    else: trial['attempts']=[];trial['state']='pending';manifest['status']='incomplete'
    # This fixture publishes a new synthetic manifest without claiming the
    # original history chain, then audits unchanged real records independently.
    manifest['artifacts']=[i for t in manifest['trials'] for a in t['attempts'] for i in a['artifacts']]
    manifest.update(revision=0,previous_manifest_sha256=None)
    (target/'manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(module,'load_fhcp_graph',lambda name,root:load_fhcp_graph(name,root=ROOT))
    modules={k:f'src/algorithms/{v.module}.py' for k,v in VARIANTS.items()}
    if mutation in ('duplicate','inventory'):
        with pytest.raises(ValueError): module.audit_batch(tmp_path,target/'manifest.json',config,expand_plan(config,'smoke'),modules)
    else:
        checked,rows=module.audit_batch(tmp_path,target/'manifest.json',config,expand_plan(config,'smoke'),modules)
        first=next(r for r in rows if r['trial_id']==trial['trial_id'])
        assert first['outcome']==('pending' if mutation=='pending' else 'invalid_evidence')
        if mutation=='pending': assert not aggregate(checked,rows)[0]['final']


def test_analysis_regenerates_tables_and_figures_without_overwriting(tmp_path):
    import shutil
    import xml.etree.ElementTree as ET
    from PIL import Image
    from src.cli.benchmark_analysis import generate
    relative=SMOKE.parent.relative_to(ROOT)
    shutil.copytree(SMOKE.parent,tmp_path/relative,ignore=shutil.ignore_patterns('analyses','.lock'))
    for path in (CONFIG,Path('docs/decisions/fhcp-instances.json'),
                 Path('src/evaluation/benchmark.py'),Path('src/cli/benchmark_analysis.py')):
        target=tmp_path/path
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/path,target)
    for name in ('graph1','graph2'):
        path=Path(f'data/raw/FHCPCS/{name}.hcp')
        (tmp_path/path).parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/path,tmp_path/path)
    first,summaries=generate(tmp_path,tmp_path/relative/'manifest.json')
    second,repeated=generate(tmp_path,tmp_path/relative/'manifest.json')
    assert first != second and summaries==repeated
    for name in ('summary.json','attempts.json','summary.csv','durations.csv','counters.csv','outcomes.csv'):
        assert (first/name).read_bytes()==(second/name).read_bytes()
    assert all(s['success_percent']==0 for s in summaries)
    assert ET.parse(first/'graph1.svg').getroot().tag.endswith('svg')
    with Image.open(first/'graph1.png') as image:
        image.verify()
    meta=read_json(first/'analysis.json')
    assert meta['final'] and meta['schema_version']=='fhcp-benchmark-analysis/1'
    assert all((first/row['path']).is_file() for row in meta['outputs'])
