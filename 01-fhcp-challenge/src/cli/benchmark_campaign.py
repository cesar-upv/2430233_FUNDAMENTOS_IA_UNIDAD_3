"""Prepare, resume and audit the preregistered M6 campaign without replacing trials."""

import argparse
import csv
import fcntl
from io import StringIO
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import shutil
from statistics import fmean
import sys
from time import sleep
from uuid import uuid4

from src.evaluation.benchmark import NORMAL, file_hash
from .__main__ import _ROOT
from .batch import (_commit, _exclude_batch, _profile, _record_manifest, _write_json,
                    _write_bytes, create_batch, resource_incidents, resource_sample, resume_batch)
from .benchmark_analysis import generate
from .benchmark_plan import load_config, load_freeze, protocol_path, read_json

CONFIG = Path('experiments/configs/benchmark-v2.json')
PHASES = ('smoke', 'tuning', 'evaluation', 'scale', 'verification')


def choose(config, rows):
    """Apply the fixed lexicographic rule to all ten primaries per candidate."""
    scores = {}
    for entry in config['configurations']:
        samples = [r for r in rows if r['role']=='primary' and r['config_id']==entry['config_id']]
        if len(samples)!=10 or any(not r['resolved'] for r in samples):
            raise ValueError('Selection requires ten resolved primaries per candidate.')
        scores[entry['config_id']] = dict(
            successes=sum(r['outcome']=='success' for r in samples),
            errors=sum(r['outcome'] not in NORMAL for r in samples),
            mean_normalized_cost=fmean(1 if r['outcome'] not in NORMAL or r['normalized_cost'] is None
                                      else r['normalized_cost'] for r in samples),
            ordinal=int(entry['config_id'][-1]))
    selected=[]
    for algorithm in config['algorithms']:
        candidates=[e for e in config['configurations'] if e['algorithm']==algorithm]
        def key(entry):
            s=scores[entry['config_id']]
            return -s['successes'],s['errors'],s['mean_normalized_cost'],s['ordinal']
        winner=min(candidates,key=key)
        score=scores[winner['config_id']]
        if score['errors']==10:
            raise ValueError('Both candidates failed entirely; review before evaluating.')
        selected.append(dict(algorithm=algorithm,config_id=winner['config_id'],
                             parameters=winner['parameters'],score=score))
    return scores,selected


def campaign_environment(config):
    """Check the preregistered machine without creating campaign artifacts."""
    profile=config['execution']['campaign_profile']
    cpu=profile['logical_cpu']
    observed=_profile(cpu,config['execution'],[])
    for field,expected in (('cpu',profile['cpu_model']),('ram_bytes',profile['ram_bytes']),
                           ('kernel',profile['kernel']),('energy_policy',profile['energy_policy'])):
        if observed[field]!=expected:
            raise ValueError(f'Campaign machine differs: {field}')
    return observed


def check(root, config_path):
    """Read-only machine/resource check; does not approve a protocol or code."""
    config_path=Path(config_path).resolve()
    config=load_config(Path(root).resolve(),config_path)
    environment=campaign_environment(config)
    resources=preflight(config,config['execution']['campaign_profile']['logical_cpu'])
    return dict(protocol_id=config['protocol_id'],scope='machine_and_resources_only',
                resources_ready=not resources['issues'],environment=environment,**resources)


def prepare(root, config_path):
    root=Path(root).resolve()
    config_path=Path(config_path).resolve()
    config=load_config(root,config_path)
    code=_commit(root)
    observed=campaign_environment(config)
    directory=root/'experiments/results'/str(uuid4())
    _exclude_batch(root,directory.relative_to(root))
    directory.mkdir(parents=True)
    (directory/'manifest-history').mkdir()
    state=dict(schema_version='fhcp-campaign/1',batch_id=directory.name,revision=0,
               previous_manifest_sha256=None,created_at_utc=datetime.now(UTC).isoformat(),
               protocol_id=config['protocol_id'],config_path=config_path.relative_to(root).as_posix(),
               config_sha256=file_hash(config_path),code_commit=code,environment=observed,
               status='planned',phases={},freeze=None,verification=None,preflights=[])
    _record_manifest(directory,state)
    return directory


def preflight(config,cpu):
    before=resource_sample(cpu)
    sleep(1)
    after=resource_sample(cpu)
    issues=resource_incidents(before,after,config['execution']['campaign_profile'])
    if after['available_ram_bytes'] is None or after['available_ram_bytes']<config['execution']['minimum_available_ram_bytes']:
        issues.append('insufficient_available_ram')
    if shutil.disk_usage(_ROOT).free<config['execution'].get('minimum_free_disk_bytes',10*1024**3):
        issues.append('insufficient_free_disk')
    return dict(before=before,after=after,issues=issues)


def freeze_tuning(root,directory,state,config,config_path):
    tuning=state['phases']['tuning']
    manifest_path=root/tuning['manifest_path']
    manifest=read_json(manifest_path)
    analysis=root/tuning['analysis_path']
    rows=read_json(analysis/'attempts.json')
    scores,selection=choose(config,rows)
    audit=directory/'tuning-audit.json'
    audit_value=dict(schema_version='fhcp-tuning-audit/1',scores=scores,attempts=rows,
                          analysis_path=tuning['analysis_path'],analysis_sha256=file_hash(analysis/'analysis.json'))
    if audit.exists() and read_json(audit)!=audit_value:
        raise ValueError('Existing tuning audit contradicts its original evidence.')
    if not audit.exists():
        _write_json(audit,audit_value)
    table=directory/'selection.csv'
    stream=StringIO(newline='')
    fields=('config_id','successes','errors','mean_normalized_cost','ordinal')
    writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
    writer.writeheader()
    writer.writerows(dict(config_id=k,**v) for k,v in scores.items())
    table_bytes=stream.getvalue().encode('utf-8')
    if table.exists() and table.read_bytes()!=table_bytes:
        raise ValueError('Existing selection table contradicts audited tuning.')
    if not table.exists():
        _write_bytes(table,table_bytes)
    freeze=dict(schema_version='fhcp-benchmark-freeze/1',protocol_id=config['protocol_id'],
                created_at_utc=datetime.now(UTC).isoformat(),config_sha256=file_hash(config_path),
                protocol_sha256=file_hash(root/protocol_path(config)),
                tuning_batches=[dict(batch_id=manifest['batch_id'],manifest_path=tuning['manifest_path'],
                                     manifest_sha256=file_hash(manifest_path))],
                selection=selection,code=manifest['code'],environment=manifest['environment'],
                seeds_decimal=config['phases']['evaluation']['seeds_decimal'],
                budgets={p:config['phases'][p]['budget'] for p in ('evaluation','scale')},
                artifacts=[dict(path=p.relative_to(root).as_posix(),sha256=file_hash(p)) for p in (audit,table)])
    path=directory/'freeze.json'
    _write_json(path,freeze)
    load_freeze(root,path,config,config_path)
    return dict(path=path.relative_to(root).as_posix(),sha256=file_hash(path))


def verify_repeats(root,path):
    manifest=read_json(path)
    comparisons=[]
    for trial in manifest['trials']:
        attempts=[a for a in trial['attempts'] if a['role'] in ('primary','verification_repeat')]
        if len(attempts)!=2 or any(a['state']!='finished' or a['outcome'] not in NORMAL for a in attempts):
            raise ValueError('Verification requires two normally reconciled attempts per family.')
        records=[read_json(root/a['record_path'])['result'] for a in attempts]
        fields=('best_route','best_cost','status','stop_reason','success_within_budget','counters','validation')
        equal=all(records[0][key]==records[1][key] for key in fields)
        comparisons.append(dict(trial_id=trial['trial_id'],algorithm=trial['identity']['algorithm'],
                                attempt_ids=[a['attempt_id'] for a in attempts],equal=equal))
    if len(comparisons)!=6 or not all(row['equal'] for row in comparisons):
        raise ValueError('Predefined verification pairs do not reproduce their trajectories.')
    return comparisons


def _run(root,directory):
    root,directory=Path(root).resolve(),Path(directory).resolve()
    state=read_json(directory/'manifest.json')
    if state['schema_version']!='fhcp-campaign/1' or directory.parent!=root/'experiments/results':
        raise ValueError('Invalid campaign directory.')
    config_path=root/state['config_path']
    config=load_config(root,config_path)
    if _commit(root)!=state['code_commit'] or file_hash(config_path)!=state['config_sha256']:
        raise ValueError('Campaign requires its original clean code and configuration.')
    if state['freeze'] is not None and file_hash(root/state['freeze']['path'])!=state['freeze']['sha256']:
        raise ValueError('Previously published freeze changed.')
    cpu=config['execution']['campaign_profile']['logical_cpu']
    if _profile(cpu,config['execution'],[])['environment_id']!=state['environment']['environment_id']:
        raise ValueError('Campaign environment changed.')
    state['status']='running'
    _record_manifest(directory,state)
    for phase in PHASES:
        check=preflight(config,cpu)
        state['preflights'].append(dict(phase=phase,**check))
        _record_manifest(directory,state)
        if check['issues']:
            state['status']='incomplete'
            _record_manifest(directory,state)
            return state
        if phase not in state['phases']:
            freeze_path=root/state['freeze']['path'] if phase in ('evaluation','scale','verification') else None
            path=create_batch(root,config_path,phase,cpu,freeze_path)
            state['phases'][phase]=dict(manifest_path=(path/'manifest.json').relative_to(root).as_posix(),
                                       analysis_path=None,status='planned')
            _record_manifest(directory,state)
        info=state['phases'][phase]
        if info['analysis_path'] is not None and file_hash(root/info['analysis_path']/'analysis.json')!=info['analysis_sha256']:
            raise ValueError('Previously published phase analysis changed.')
        path=root/info['manifest_path']
        manifest=read_json(path)
        if manifest['status']!='complete':
            manifest=resume_batch(root,path.parent)
        info['status']=manifest['status']
        _record_manifest(directory,state)
        if manifest['status']!='complete':
            state['status']='incomplete'
            _record_manifest(directory,state)
            return state
        if info['analysis_path'] is None:
            analysis,summaries=generate(root,path)
            if not all(s['final'] for s in summaries):
                raise ValueError('Phase audit is incomplete.')
            info['analysis_path']=analysis.relative_to(root).as_posix()
            info['analysis_sha256']=file_hash(analysis/'analysis.json')
            _record_manifest(directory,state)
        if phase=='tuning' and state['freeze'] is None:
            freeze_path=directory/'freeze.json'
            if freeze_path.exists():
                load_freeze(root,freeze_path,config,config_path)
                state['freeze']=dict(path=freeze_path.relative_to(root).as_posix(),sha256=file_hash(freeze_path))
            else:
                state['freeze']=freeze_tuning(root,directory,state,config,config_path)
            _record_manifest(directory,state)
        if phase=='verification':
            comparisons=verify_repeats(root,path)
            report=directory/'verification.json'
            _write_json(report,dict(schema_version='fhcp-verification/1',comparisons=comparisons))
            state['verification']=dict(path=report.relative_to(root).as_posix(),sha256=file_hash(report))
            _record_manifest(directory,state)
        print(json.dumps(dict(phase=phase,status='complete',batch_id=manifest['batch_id'])),flush=True)
    state['status']='complete'
    _record_manifest(directory,state)
    return state


def run(root,directory):
    directory=Path(directory).resolve()
    with (directory/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _run(root,directory)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    prepare_parser=sub.add_parser('prepare')
    prepare_parser.add_argument('--config',type=Path,default=_ROOT/CONFIG)
    check_parser=sub.add_parser('check')
    check_parser.add_argument('--config',type=Path,default=_ROOT/CONFIG)
    run_parser=sub.add_parser('run')
    run_parser.add_argument('campaign',type=Path)
    args=parser.parse_args(argv)
    try:
        if args.action=='check':
            result=check(_ROOT,args.config)
            print(json.dumps(result))
            return int(not result['resources_ready'])
        if args.action=='prepare':
            print(prepare(_ROOT,args.config))
            return 0
        state=run(_ROOT,args.campaign)
        print(json.dumps(dict(campaign=state['batch_id'],status=state['status'])))
        return int(state['status']!='complete')
    except (ValueError,OSError,KeyError,TypeError) as error:
        print(f'campaign_error: {error}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
