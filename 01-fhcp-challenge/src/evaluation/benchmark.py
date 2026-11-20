"""Audit immutable benchmark evidence and aggregate the preregistered metrics.

This module has no dependency on the CLI or the batch coordinator. Missing or
contradictory attempts remain visible; they never become successes by inference.
"""

from collections import Counter, defaultdict
from hashlib import sha256
import json
from math import sqrt
from pathlib import Path
from statistics import fmean, median, stdev
from uuid import UUID

from src.graphs import load_fhcp_graph
from .cost import evaluate_cost
from .cycle import validate_cycle


NORMAL = frozenset({'success', 'exhausted', 'cooperative_timeout'})
OUTCOMES = NORMAL | {'external_timeout', 'config_error', 'runtime_error', 'save_error',
                      'interrupted', 'invalid_evidence'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def file_hash(path):
    return sha256(path.read_bytes()).hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    result = json.loads(path.read_bytes(), object_pairs_hook=unique)
    canonical(result)
    return result


def evidence_path(root, batch, value):
    path = Path(value)
    resolved = (root / path).resolve()
    if path.is_absolute() or '..' in path.parts or not resolved.is_relative_to(batch):
        raise ValueError(f'Evidence outside its batch: {value}')
    return resolved


def _nonnegative(value):
    return type(value) is int and value >= 0


def audit_record(record, manifest, trial, entry, graph, implementation):
    """Return a classification only after checking identity, limits and candidate."""
    identity = trial['identity']
    result, procedure = record['result'], record['procedure']
    if str(UUID(record['run']['run_id'])) != record['run']['run_id']:
        raise ValueError('Noncanonical RunRecord UUID.')
    if (record['schema_version'] != 'fhcp-run-record/1'
        or record['code']['commit'] != manifest['code']['commit']
        or record['code']['dirty'] is not False
        or record['instance']['id'] != identity['instance_id']
        or record['randomness']['seed_decimal'] != identity['seed_decimal']
        or procedure['family'] != entry['family'] or procedure['variant'] != entry['variant']):
        raise ValueError('RunRecord identity or code differs from the planned trial.')
    for field in ('python_implementation', 'python_version', 'dependencies', 'os', 'architecture', 'ram_bytes'):
        if record['environment'][field] != manifest['environment'][field]:
            raise ValueError(f'RunRecord environment differs: {field}')
    versions = {'implementation_version': implementation,
                'fitness_version': 'src/evaluation/cost.py',
                'validator_version': 'src/evaluation/cycle.py',
                'instrumentation_version': 'src/algorithms/execution.py'}
    if identity['algorithm'] in ('de', 'pso'):
        versions['decoder_version'] = 'src/algorithms/real_keys.py'
    for field, module in versions.items():
        if procedure[field] != 'sha256:' + manifest['code']['modules'][module]:
            raise ValueError(f'RunRecord implementation hash differs: {field}')
    route, cost = result['best_route'], result['best_cost']
    if (route is None) != (cost is None) or (route is not None and
        (type(cost) is not int or evaluate_cost(graph, route) != cost)):
        raise ValueError('Candidate legality or independently recalculated cost differs.')
    if result['status'] == 'error':
        if result['success_within_budget'] is not False or result['timing']['first_success'] is not None:
            raise ValueError('Error contradicts success evidence.')
        return 'config_error' if result['stop_reason'] == 'invalid_config' else 'runtime_error'
    if (record['instance']['sha256'] != identity['instance_sha256']
        or record['instance']['n'] != graph.vertex_count() or record['instance']['m'] != graph.edge_count()
        or record['instance']['mapping'] != 'ascending_external_labels_zero_based_internal'
        or canonical(procedure['parameters']) != canonical(entry['parameters']) or procedure['iteration_unit'] != entry['iteration_unit']
        or canonical({k: record['budget'][k] for k in identity['budget']}) != canonical(identity['budget'])
        or result['telemetry_complete'] is not True):
        raise ValueError('RunRecord graph, configuration, budget or telemetry differs.')
    route, cost = result['best_route'], result['best_cost']
    if (route is None) != (cost is None) or (route is not None and
        (type(cost) is not int or evaluate_cost(graph, route) != cost)):
        raise ValueError('Candidate legality or independently recalculated cost differs.')
    counters, timing = result['counters'], result['timing']
    started, completed = counters['evaluations_started'], counters['evaluations_completed']
    if not (_nonnegative(started) and _nonnegative(completed) and completed <= started):
        raise ValueError('Invalid evaluation counters.')
    for field in ('solver_ns', 'validation_ns'):
        if not _nonnegative(timing[field]):
            raise ValueError('Invalid solver timing.')
    if timing['validation_ns'] > timing['solver_ns']:
        raise ValueError('Validation exceeds its parent solver interval.')
    for name, value in (('max_evaluations', started), ('max_iterations', counters['iterations_completed'])):
        cap = identity['budget'][name]
        if not _nonnegative(value) or (cap is not None and value > cap):
            raise ValueError('RunRecord exceeds a work budget.')
    limit = identity['budget']['max_elapsed_ns']
    expected_overrun = None if limit is None else max(0, timing['solver_ns'] - limit)
    if timing['overrun_ns'] != expected_overrun:
        raise ValueError('Inconsistent temporal overrun.')
    if (counters['iteration_unit'] != entry['iteration_unit']
        or any(not _nonnegative(counters[k]) for k in
               ('full_evaluations', 'incremental_evaluations', 'cache_hits', 'validations_started',
                'validations_completed', 'restarts'))
        or counters['full_evaluations'] + counters['incremental_evaluations'] != completed
        or counters['validations_completed'] > counters['validations_started']):
        raise ValueError('Inconsistent counter partition or validation counters.')
    first = timing['first_success']
    if result['status'] == 'success':
        if (result['stop_reason'] != 'validated_cycle' or cost != 0 or result['success_within_budget'] is not True or first is None
            or result['validation']['valid'] is not True or not validate_cycle(graph, route).valid
            or not _nonnegative(first['elapsed_ns']) or first['elapsed_ns'] > timing['solver_ns']
            or (limit is not None and first['elapsed_ns'] > limit)
            or not all(_nonnegative(first[k]) for k in ('evaluations_started', 'evaluations_completed', 'iterations_completed'))
            or counters['validations_completed'] < 1
            or not 1 <= first['evaluations_completed'] <= first['evaluations_started'] <= started
            or first['evaluations_completed'] > completed
            or first['iterations_completed'] > counters['iterations_completed']):
            raise ValueError('Success lacks a valid independent certificate within budget.')
        return 'success'
    if (result['status'] != 'exhausted' or result['success_within_budget'] is not False
        or first is not None or result['stop_reason'] not in
        {'time_limit', 'evaluation_limit', 'iteration_limit', 'algorithm_stop'}):
        raise ValueError('Contradictory exhaustion or unknown result.')
    return 'cooperative_timeout' if result['stop_reason'] == 'time_limit' else 'exhausted'


def audit_batch(root, manifest_path, config, expected, implementations):
    """Reconcile the entire inventory; structural conflicts reject the analysis."""
    root, manifest_path = Path(root).resolve(), Path(manifest_path).resolve()
    batch = manifest_path.parent
    manifest = read_json(manifest_path)
    if str(UUID(manifest['batch_id'])) != manifest['batch_id']:
        raise ValueError('Noncanonical batch UUID.')
    if (manifest['schema_version'] != 'fhcp-batch-manifest/1'
        or manifest['protocol_id'] != config['protocol_id'] or manifest['batch_id'] != batch.name
        or manifest['code']['dirty'] is not False
        or manifest['expected_trials'] != len(expected)):
        raise ValueError('Incompatible batch manifest.')
    keys = ('trial_id', 'ordinal', 'identity', 'config_id')
    if ([{k: t[k] for k in keys} for t in manifest['trials']]
        != [{k: t[k] for k in keys} for t in expected]):
        raise ValueError('Manifest inventory differs from the entire approved plan.')
    inputs = manifest['inputs']
    if len({i['role'] for i in inputs}) != len(inputs) or not {'config', 'protocol', 'dataset_manifest'} <= {i['role'] for i in inputs}:
        raise ValueError('Missing or duplicated batch inputs.')
    if read_json(evidence_path(root, batch, next(i['path'] for i in inputs if i['role']=='config'))) != config:
        raise ValueError('Analysis plan differs from the original batch configuration.')
    inventory = [i for t in manifest['trials'] for a in t['attempts'] for i in a['artifacts']]
    if sorted(manifest['artifacts'], key=canonical) != sorted(inventory, key=canonical):
        raise ValueError('Top-level artifact inventory differs from its attempts.')
    for item in inputs:
        path = evidence_path(root, batch, item['path'])
        if file_hash(path) != item['sha256']:
            raise ValueError('Changed batch input: ' + item['role'])
    profile = {k: v for k, v in manifest['environment'].items() if k != 'environment_id'}
    if sha256(canonical(profile)).hexdigest() != manifest['environment']['environment_id']:
        raise ValueError('Environment profile hash mismatch.')
    current = manifest
    for number in reversed(range(manifest['revision'])):
        path = batch / 'manifest-history' / f'{number:06d}.json'
        if file_hash(path) != current['previous_manifest_sha256']:
            raise ValueError('Manifest history hash mismatch.')
        current = read_json(path)
    entries = {e['config_id']: e for e in config['configurations']}
    ids, run_ids, hashes, graphs, rows = set(), set(), set(), {}, []
    for trial in manifest['trials']:
        required = ('primary', 'verification_repeat') if manifest['phase'] == 'verification' else ('primary',)
        for role in required:
            if sum(a['role'] == role for a in trial['attempts']) > 1:
                raise ValueError('Duplicate primary or verification role.')
        previous = set()
        if trial['attempts'] and trial['attempts'][0]['role'] != 'primary':
            raise ValueError('The first started attempt must remain the primary.')
        for attempt in trial['attempts']:
            if str(UUID(attempt['attempt_id'])) != attempt['attempt_id']:
                raise ValueError('Noncanonical attempt UUID.')
            if attempt['role'] not in (*required, 'diagnostic_retry'):
                raise ValueError('Unknown attempt role.')
            if attempt['role'] == 'diagnostic_retry':
                if attempt['retry_of'] not in previous:
                    raise ValueError('Diagnostic retry must reference an earlier attempt in its trial.')
            elif attempt['retry_of'] is not None:
                raise ValueError('A predefined primary/repeat cannot replace an earlier attempt.')
            previous.add(attempt['attempt_id'])
            if attempt['attempt_id'] in ids:
                raise ValueError('Attempt UUID reused across trials.')
            ids.add(attempt['attempt_id'])
            if attempt['run_id'] is not None:
                if attempt['run_id'] in run_ids:
                    raise ValueError('RunRecord UUID reused across attempts.')
                run_ids.add(attempt['run_id'])
            row = dict(batch_id=manifest['batch_id'], trial_id=trial['trial_id'],
                       attempt_id=attempt['attempt_id'], run_id=attempt['run_id'],
                       identity=trial['identity'], config_id=trial['config_id'], role=attempt['role'],
                       resolved=attempt['state'] == 'finished', outcome=attempt['outcome'],
                       issues=[], timings={}, counters={}, normalized_cost=None,
                       record_path=attempt['record_path'], record_sha256=attempt['record_sha256'],
                       peak_rss_bytes=attempt['peak_rss_bytes'], iteration_unit=entries[trial['config_id']]['iteration_unit'])
            record = None
            try:
                if row['outcome'] not in OUTCOMES and attempt['state'] == 'finished':
                    raise ValueError('Unknown terminal outcome.')
                attempt_dir = batch / 'attempts' / attempt['attempt_id']
                paths = {item['path'] for item in attempt['artifacts']}
                if len(paths) != len(attempt['artifacts']):
                    raise ValueError('Repeated artifact path in attempt inventory.')
                for item in attempt['artifacts']:
                    path = evidence_path(root, batch, item['path'])
                    if not path.is_relative_to(attempt_dir):
                        raise ValueError('Artifact belongs to another attempt.')
                    if file_hash(path) != item['sha256']:
                        raise ValueError('Missing or changed attempt artifact: ' + item['path'])
                if row['resolved']:
                    terminal_path = batch / 'attempts' / attempt['attempt_id'] / 'process.json'
                    if not terminal_path.is_file():
                        row['resolved'] = False
                        raise ValueError('Missing terminal supervisor evidence.')
                    if terminal_path.relative_to(root).as_posix() not in paths:
                        row['resolved'] = False
                        raise ValueError('Supervisor journal is absent from the hash inventory.')
                    terminal = read_json(terminal_path)
                    if terminal['exit_code'] != attempt['exit_code'] or terminal['signal'] != attempt['signal']:
                        raise ValueError('Terminal supervisor evidence contradicts manifest.')
                    if terminal['exit_code'] is None and terminal['signal'] is None and terminal['outcome'] != 'runtime_error':
                        row['resolved'] = False
                        raise ValueError('No terminal process diagnosis.')
                for stream in ('stdout', 'stderr'):
                    if attempt[stream + '_path'] is not None:
                        if file_hash(evidence_path(root, batch, attempt[stream + '_path'])) != attempt[stream + '_sha256']:
                            raise ValueError('Stream hash mismatch.')
                if attempt['record_path'] is not None:
                    path = evidence_path(root, batch, attempt['record_path'])
                    if file_hash(path) != attempt['record_sha256']:
                        raise ValueError('RunRecord hash mismatch.')
                    if attempt['record_sha256'] in hashes:
                        raise ValueError('Identical RunRecord copied between attempts.')
                    hashes.add(attempt['record_sha256'])
                    record = read_json(path)
                    if record['run']['run_id'] != attempt['run_id']:
                        raise ValueError('RunRecord ID differs from its linked attempt.')
                    name = trial['identity']['instance_id']
                    if name not in graphs:
                        graphs[name] = load_fhcp_graph(name, root=root)
                    graph = graphs[name]
                    if graph.source['sha256'] != trial['identity']['instance_sha256']:
                        raise ValueError('Graph input hash differs.')
                    classified = audit_record(record, manifest, trial, entries[trial['config_id']],
                                              graph, implementations[trial['identity']['algorithm']])
                    if attempt['outcome'] in NORMAL and classified != attempt['outcome']:
                        raise ValueError('Outcome contradicts independently audited record.')
                    if attempt['outcome'] in NORMAL and attempt['exit_code'] != 0:
                        raise ValueError('Normal solver outcome has a failed process exit.')
                    cost = record['result']['best_cost']
                    row['normalized_cost'] = None if cost is None else cost / graph.vertex_count()
                elif attempt['outcome'] in NORMAL:
                    raise ValueError('Normal outcome has no original RunRecord.')
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                row['issues'].append(str(error))
                row['outcome'] = 'invalid_evidence'
            # Never invent missing telemetry, including when an audit failed.
            if record is not None and not row['issues']:
                result = record['result']
                for key in ('solver_ns', 'validation_ns', 'overrun_ns'):
                    row['timings'][key] = result['timing'][key]
                for key in ('preparation_ns', 'finalization_ns', 'total_ns'):
                    row['timings'][key] = record['timing'].get(key)
                first = result['timing']['first_success']
                row['timings']['first_success_ns'] = first['elapsed_ns'] if first and row['outcome'] == 'success' else None
                row['counters'] = dict(result['counters'])
                row['counters'].update({'algorithm_counters.' + k: v
                                        for k, v in result['counters']['algorithm_counters'].items()})
            for key in ('process_elapsed_ns', 'capture_write_ns', 'load_ns', 'reconciliation_ns'):
                value = attempt.get(key)
                row['timings'][key] = value if value is None or _nonnegative(value) else None
            row['censoring'] = None
            if row['outcome'] == 'cooperative_timeout':
                row['censoring'] = dict(scope='solver_time', threshold_ns=trial['identity']['budget']['max_elapsed_ns'])
            elif row['outcome'] == 'external_timeout':
                row['censoring'] = dict(scope='process_time', threshold_ns=attempt['process_elapsed_ns'])
            elif row['outcome'] == 'exhausted' and row['counters'].get('evaluations_started') == trial['identity']['budget']['max_evaluations']:
                row['censoring'] = dict(scope='evaluations', threshold=trial['identity']['budget']['max_evaluations'])
            rows.append(row)
        for role in required:
            if any(a['role'] == role for a in trial['attempts']):
                continue
            rows.append(dict(batch_id=manifest['batch_id'], trial_id=trial['trial_id'],
                             attempt_id=None, run_id=None, identity=trial['identity'],
                             config_id=trial['config_id'], role=role, resolved=False,
                             outcome='pending', issues=[], timings={}, counters={},
                             normalized_cost=None, record_path=None, record_sha256=None,
                             peak_rss_bytes=None, iteration_unit=entries[trial['config_id']]['iteration_unit']))
    manifest['audit_complete'] = manifest['status'] == 'complete' and all(
        r['resolved'] for r in rows if r['role'] in ('primary', 'verification_repeat'))
    return manifest, rows


def distribution(values, expected):
    values = sorted(v for v in values if v is not None)
    def quantile(q):
        position = (len(values) - 1) * q
        lo = int(position)
        return values[lo] + (values[min(lo + 1, len(values) - 1)] - values[lo]) * (position - lo)
    return dict(observed=len(values), missing=expected - len(values),
                mean=fmean(values) if values else None, median=median(values) if values else None,
                q1=quantile(.25) if values else None, q3=quantile(.75) if values else None,
                sample_stdev=stdev(values) if len(values) > 1 else None)


def aggregate(manifest, rows):
    """Group primaries only, retaining the full predeclared denominator."""
    groups = defaultdict(list)
    for row in rows:
        if row['role'] == 'primary':
            identity = row['identity']
            groups[identity['instance_id'], identity['algorithm'], row['config_id']].append(row)
    summaries = []
    for (instance, algorithm, config_id), observations in sorted(groups.items()):
        n = len(observations)
        counts = Counter(r['outcome'] for r in observations if r['resolved'])
        successes = counts['success']
        resolved = sum(r['resolved'] for r in observations)
        complete = resolved == n and manifest.get('audit_complete', manifest['status'] == 'complete')
        p = successes / n
        timings = {key: distribution([None if r['timings'].get(key) is None else r['timings'][key] / 1e9
                                     for r in observations], n)
                   for key in ('solver_ns', 'validation_ns', 'preparation_ns', 'finalization_ns',
                               'total_ns', 'process_elapsed_ns', 'capture_write_ns', 'load_ns',
                               'overrun_ns', 'reconciliation_ns')}
        successes_rows = [r for r in observations if r['resolved'] and r['outcome'] == 'success']
        timing_success = distribution([r['timings'].get('first_success_ns', None) / 1e9
                                      for r in successes_rows], successes)
        counters = {key: distribution([r['counters'].get(key) for r in observations], n)
                    for key in sorted({k for r in observations for k, v in r['counters'].items()
                                       if type(v) is int})}
        summaries.append(dict(instance_id=instance, algorithm=algorithm, config_id=config_id,
                              phase=manifest['phase'], environment_id=manifest['environment']['environment_id'],
                              code_commit=manifest['code']['commit'], budget=observations[0]['identity']['budget'],
                              iteration_unit=observations[0]['iteration_unit'], expected=n, resolved=resolved,
                              pending=n-resolved, successes=successes, final=complete,
                              success_percent=100*p if complete else None,
                              provisional_lower_bound_percent=None if complete else 100*p,
                              binary_sample_stdev=sqrt(n*p*(1-p)/(n-1)) if complete and n>1 else None,
                              outcomes=dict(counts), timings_seconds=timings, success_time_seconds=timing_success,
                              temporal_censoring=dict(cooperative=counts['cooperative_timeout'],
                                                     external_process_scope=counts['external_timeout']),
                              evaluation_censoring=sum(r['resolved'] and r['outcome']=='exhausted'
                                                       and r['counters'].get('evaluations_started') == r['identity']['budget']['max_evaluations']
                                                       for r in observations),
                              counters=counters,
                              max_peak_rss_bytes=max((r['peak_rss_bytes'] for r in observations
                                                      if r['peak_rss_bytes'] is not None), default=None),
                              precision=None, recall=None, f1=None))
    return summaries
