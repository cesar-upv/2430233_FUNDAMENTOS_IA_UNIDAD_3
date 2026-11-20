"""Preregistered campaign selection, resource gates and orchestration."""

from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4
from hashlib import sha256

import pytest

from src.cli import benchmark_campaign as campaign
from src.cli import batch
from src.cli.benchmark_plan import CONFIG, load_config, expand_plan, protocol_path

ROOT=Path(__file__).resolve().parents[1]


def _rows(config):
    return [dict(config_id=e['config_id'],role='primary',resolved=True,outcome='exhausted',normalized_cost=.5)
            for e in config['configurations'] for _ in range(10)]


def test_v2_preserves_all_search_choices_and_versions_the_environment():
    first=load_config(ROOT,ROOT/CONFIG)
    second=load_config(ROOT,ROOT/campaign.CONFIG)
    for key in ('dataset_manifest','instances','algorithms','configurations','phases','selection','order','attempts'):
        assert first[key]==second[key]
    assert second['execution']['campaign_profile']['logical_cpu']==10
    assert second['execution']['minimum_free_disk_bytes']==10*1024**3
    assert protocol_path(second).name=='benchmark-protocol-v2.md'
    assert len(expand_plan(second,'tuning'))==120
    assert {t['trial_id'] for t in expand_plan(first,'tuning')}.isdisjoint(t['trial_id'] for t in expand_plan(second,'tuning'))


def test_v3_changes_only_the_machine_and_keeps_previous_plans_loadable(tmp_path):
    previous=load_config(ROOT,ROOT/campaign.CONFIG)
    path=ROOT/'experiments/configs/benchmark-v3.json'
    laptop=load_config(ROOT,path)
    expected=deepcopy(previous)
    expected['protocol_id']='fhcp-m6-v3'
    expected['execution']['campaign_profile'].update(
        cpu_model='12th Gen Intel(R) Core(TM) i5-12450H',logical_cpu=2,
        ram_bytes=33293524992,kernel='7.2.9-2-cachyos')
    assert laptop==expected
    assert protocol_path(laptop).name=='benchmark-protocol-v3.md'
    selection={e['algorithm']:e for e in laptop['configurations'] if e['config_id'].endswith('-c1')}
    for phase in campaign.PHASES:
        a=expand_plan(previous,phase,selection)
        b=expand_plan(laptop,phase,selection)
        assert len(a)==len(b)
        assert {t['trial_id'] for t in a}.isdisjoint(t['trial_id'] for t in b)
    laptop['phases']['tuning']['budget']['max_evaluations']+=1
    changed=tmp_path/'changed.json'
    changed.write_text(json.dumps(laptop))
    with pytest.raises(ValueError,match='differs'):
        load_config(ROOT,changed)


@pytest.mark.parametrize('field', ['cpu','ram_bytes','kernel','energy_policy'])
def test_v3_rejects_a_machine_that_differs_from_the_preregistered_profile(field,monkeypatch):
    config=load_config(ROOT,ROOT/'experiments/configs/benchmark-v3.json')
    p=config['execution']['campaign_profile']
    env=dict(cpu=p['cpu_model'],ram_bytes=p['ram_bytes'],kernel=p['kernel'],energy_policy=p['energy_policy'])
    env[field]='another machine'
    monkeypatch.setattr(campaign,'_profile',lambda *args:env)
    with pytest.raises(ValueError,match=f'machine differs: {field}'):
        campaign.campaign_environment(config)


@pytest.mark.parametrize('issues', [[],['ac_power_unavailable'],['swap_activity']])
def test_check_is_read_only_and_reports_resource_incidents(issues,monkeypatch):
    monkeypatch.setattr(campaign,'campaign_environment',lambda config:{'environment_id':'test'})
    monkeypatch.setattr(campaign,'preflight',lambda *args:dict(before={},after={},issues=issues))
    def forbidden(*args):
        raise AssertionError('A readiness check must not create artifacts or require a commit.')
    monkeypatch.setattr(campaign,'_commit',forbidden)
    monkeypatch.setattr(campaign,'_exclude_batch',forbidden)
    monkeypatch.setattr(campaign,'_record_manifest',forbidden)
    report=campaign.check(ROOT,ROOT/'experiments/configs/benchmark-v3.json')
    assert report['scope']=='machine_and_resources_only'
    assert report['resources_ready']==(not issues)
    assert report['issues']==issues


def test_v3_batch_preserves_the_base_and_machine_protocol_bytes(tmp_path,monkeypatch):
    config_path=Path('experiments/configs/benchmark-v3.json')
    config=load_config(ROOT,ROOT/config_path)
    paths=[config_path,protocol_path(config),Path('docs/decisions/benchmark-protocol.md'),
           Path(config['dataset_manifest']['path'])]
    for relative in paths:
        path=tmp_path/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((ROOT/relative).read_bytes())
    p=config['execution']['campaign_profile']
    env=dict(cpu=p['cpu_model'],ram_bytes=p['ram_bytes'],kernel=p['kernel'],energy_policy=p['energy_policy'])
    monkeypatch.setattr(batch,'_commit',lambda root:'test commit')
    monkeypatch.setattr(batch,'_profile',lambda *args:env)
    monkeypatch.setattr(batch,'_exclude_batch',lambda *args:{})
    directory=batch.create_batch(tmp_path,tmp_path/config_path,'smoke',p['logical_cpu'])
    manifest=campaign.read_json(directory/'manifest.json')
    inputs={r['role']:r for r in manifest['inputs']}
    for role,relative in [('protocol',paths[1]),('protocol_base',paths[2])]:
        copied=tmp_path/inputs[role]['path']
        assert copied.read_bytes()==(ROOT/relative).read_bytes()
        assert inputs[role]['sha256']==sha256(copied.read_bytes()).hexdigest()


def test_selection_uses_success_then_errors_then_cost_and_fixed_ordinal():
    config=load_config(ROOT,ROOT/campaign.CONFIG)
    rows=_rows(config)
    scores,selected=campaign.choose(config,rows)
    assert len(scores)==12 and all(r['config_id'].endswith('-c1') for r in selected)
    rows[10].update(outcome='success',normalized_cost=0)
    _,selected=campaign.choose(config,rows)
    assert selected[0]['config_id']=='ga-c2'
    rows[10].update(outcome='runtime_error',normalized_cost=0)
    _,selected=campaign.choose(config,rows)
    assert selected[0]['config_id']=='ga-c1'
    rows[10].update(outcome='exhausted',normalized_cost=.1)
    _,selected=campaign.choose(config,rows)
    assert selected[0]['config_id']=='ga-c2'
    rows[0]['resolved']=False
    with pytest.raises(ValueError,match='resolved'):
        campaign.choose(config,rows)
    rows[0]['resolved']=True
    for row in rows[:20]: row['outcome']='runtime_error'
    with pytest.raises(ValueError,match='failed entirely'):
        campaign.choose(config,rows)


@pytest.mark.parametrize('mutation,code',[('power','ac_power_unavailable'),('swap','swap_activity'),
                                        ('governor','energy_policy_changed'),('suspend','system_suspend')])
def test_resource_incidents_are_observed_without_deleting_the_attempt(mutation,code):
    sample=dict(ac_online=True,governor='powersave',swap_pages={'pswpin':1,'pswpout':2},suspend_offset_ns=1)
    after=deepcopy(sample)
    if mutation=='power': after['ac_online']=False
    elif mutation=='swap': after['swap_pages']['pswpout']+=1
    elif mutation=='governor': after['governor']='performance'
    else: after['suspend_offset_ns']+=2_000_000_000
    assert code in batch.resource_incidents(sample,after,{'energy_policy':'powersave'})
    assert not batch.resource_incidents(sample,sample,{'energy_policy':'powersave'})


def test_campaign_phase_order_freezes_before_evaluation_and_resumes_without_replacing(tmp_path,monkeypatch):
    config=load_config(ROOT,ROOT/campaign.CONFIG)
    config_path=tmp_path/campaign.CONFIG
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps(config))
    source=tmp_path/config['dataset_manifest']['path']
    source.parent.mkdir(parents=True)
    source.write_bytes((ROOT/config['dataset_manifest']['path']).read_bytes())
    profile=config['execution']['campaign_profile']
    env=dict(cpu=profile['cpu_model'],ram_bytes=profile['ram_bytes'],kernel=profile['kernel'],
             energy_policy=profile['energy_policy'],environment_id='e')
    monkeypatch.setattr(campaign,'_commit',lambda root:'commit')
    monkeypatch.setattr(campaign,'_profile',lambda *args:env)
    monkeypatch.setattr(campaign,'_exclude_batch',lambda *args:None)
    monkeypatch.setattr(campaign,'preflight',lambda *args:dict(before={},after={},issues=[]))
    events=[]
    def create(root,config_path,phase,cpu,freeze):
        if phase in ('evaluation','scale','verification'): assert freeze and freeze.exists()
        events.append(phase)
        directory=root/'experiments/results'/str(uuid4());directory.mkdir()
        campaign._write_json(directory/'manifest.json',dict(status='planned',batch_id=directory.name,phase=phase))
        return directory
    monkeypatch.setattr(campaign,'create_batch',create)
    def resume(root,directory):
        manifest=campaign.read_json(directory/'manifest.json');manifest['status']='complete'
        campaign._write_json(directory/'manifest.json',manifest)
        return manifest
    monkeypatch.setattr(campaign,'resume_batch',resume)
    def generate(root,path):
        directory=path.parent/'analyses'/str(uuid4());directory.mkdir(parents=True)
        campaign._write_json(directory/'analysis.json',{})
        return directory,[dict(final=True)]
    monkeypatch.setattr(campaign,'generate',generate)
    def freeze(root,directory,state,config,config_path):
        events.append('freeze')
        path=directory/'freeze.json';campaign._write_json(path,{})
        return dict(path=path.relative_to(root).as_posix(),sha256=campaign.file_hash(path))
    monkeypatch.setattr(campaign,'freeze_tuning',freeze)
    monkeypatch.setattr(campaign,'verify_repeats',lambda *args:[{'equal':True}]*6)
    directory=campaign.prepare(tmp_path,config_path)
    result=campaign.run(tmp_path,directory)
    assert result['status']=='complete'
    assert events==['smoke','tuning','freeze','evaluation','scale','verification']
    ids=deepcopy(result['phases'])
    again=campaign.run(tmp_path,directory)
    assert again['phases']==ids and len(events)==6


def test_archive_preserves_bytes_and_rejects_overwrite_escape_and_corruption(tmp_path,monkeypatch):
    import tarfile
    from io import BytesIO
    from src.cli import benchmark_archive as archive
    root=tmp_path/'checkout';root.mkdir()
    campaign_path=root/'experiments/results'/str(uuid4());campaign_path.mkdir(parents=True)
    (campaign_path/'manifest-history').mkdir()
    batch_path=root/'experiments/results'/str(uuid4());batch_path.mkdir()
    (batch_path/'manifest.json').write_text('{"raw":true}\n')
    (batch_path/'stdout.txt').write_bytes(b'original\r\nbytes\x00')
    state=dict(schema_version='fhcp-campaign/1',status='complete',batch_id=campaign_path.name,
               revision=0,previous_manifest_sha256=None,freeze={},
               phases={'smoke':{'manifest_path':(batch_path/'manifest.json').relative_to(root).as_posix()}})
    campaign._write_json(campaign_path/'manifest.json',state)
    index_path=archive.pack(root,campaign_path)
    assert archive.pack(root,campaign_path)==index_path
    index=campaign.read_json(index_path)
    import shutil
    shutil.rmtree(batch_path)
    monkeypatch.setattr(archive,'_exclude_batch',lambda *args:None)
    assert archive.restore(root,index_path)==[batch_path.name]
    assert (batch_path/'stdout.txt').read_bytes()==b'original\r\nbytes\x00'
    assert archive.restore(root,index_path)==[batch_path.name]
    (batch_path/'stdout.txt').write_text('different evidence')
    with pytest.raises(ValueError,match='overwrite'):
        archive.restore(root,index_path)
    row=index['archives'][0]
    path=root/row['path']
    with tarfile.open(path,'w:gz') as stream:
        item=tarfile.TarInfo(batch_path.name+'/../../escape');item.size=3
        stream.addfile(item,BytesIO(b'bad'))
    row['sha256']=archive.file_hash(path);row['members']=1
    campaign._write_json(index_path,index)
    with pytest.raises(ValueError,match='Unsafe'):
        archive.restore(root,index_path)
    path.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='SHA-256'):
        archive.restore(root,index_path)
