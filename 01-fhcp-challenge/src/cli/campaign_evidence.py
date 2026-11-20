"""Independent recosting, artifact checks and summaries for distributed attempts."""

import csv
from hashlib import sha256
import json
import os
from pathlib import Path
import statistics
from uuid import uuid4

from src.evaluation import evaluate_cost, validate_cycle
from src.graphs import load_fhcp_graph

from .distributed_plan import ROOT, attempt_name, read_json
from .variants import VARIANTS, effective_variant


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp-' + uuid4().hex)
    with temporary.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def file_hash(path):
    with Path(path).open('rb') as stream:
        from hashlib import file_digest
        return file_digest(stream, 'sha256').hexdigest()


def audit_attempt(directory, plan, key, graph=None, root=ROOT):
    """An interrupted primary stays an error, even if partial stdout contains a route."""
    directory = Path(directory)
    intent = read_json(directory / 'intent.json')
    if intent['key'] != list(key) or intent['plan_sha256'] != plan['plan_sha256']:
        raise ValueError('Attempt intent differs from the frozen plan.')
    exit_path = directory / 'exit.json'
    completion = read_json(exit_path) if exit_path.exists() else {'reason': 'interrupted_without_exit', 'returncode': None}
    row = {'instance': key[0], 'algorithm': key[1], 'seed': key[2], 'status': 'error',
           'stop_reason': completion['reason'], 'certified_success': False, 'best_cost': None,
           'process_seconds': completion.get('process_seconds'), 'solver_ns': None,
           'returncode': completion['returncode'], 'artifact_sha256': {}}
    for name in ('intent.json', 'stdout.json', 'stderr.log', 'exit.json', 'worker.json'):
        if (directory / name).exists():
            row['artifact_sha256'][name] = file_hash(directory / name)
    if completion['reason'] != 'finished':
        return row
    try:
        record = read_json(directory / 'stdout.json')
        entry = next(e for e in plan['instances'] if e['id'] == key[0])
        solver = next(s for s in plan['solvers'] if s['algorithm'] == key[1])
        spec = effective_variant(VARIANTS[key[1]], solver['parameters'])
        procedure = record['procedure']
        if (record['instance']['id'] != key[0] or record['instance']['sha256'] != entry['sha256']
                or record['instance']['n'] != entry['dimension'] or record['instance']['m'] != entry['edge_count']
                or int(record['randomness']['seed_decimal']) != key[2]
                or record['budget'] != {**plan['budget'], 'time_scope': 'solver_including_initialization_and_validation'}
                or procedure['parameters'] != solver['parameters'] or procedure['variant'] != spec.name
                or procedure['family'] != spec.family):
            raise ValueError('RunRecord identity/parameters/budget differ from plan.')
        modules = {'implementation_version': f'src/algorithms/{spec.module}.py',
                   'fitness_version': 'src/evaluation/cost.py', 'validator_version': 'src/evaluation/cycle.py',
                   'instrumentation_version': 'src/algorithms/execution.py'}
        if spec.name.endswith(('_graph_guided_v2', '_enhanced_v3')):
            modules['search_operator_version'] = 'src/algorithms/graph_guidance.py'
        if solver['parameters'].get('cost_mode') == 'incremental':
            modules['local_moves_version'] = 'src/algorithms/local_moves.py'
        if solver['parameters'].get('pheromone_storage') == 'edges':
            modules['pheromone_storage_version'] = 'src/algorithms/sparse_pheromone.py'
        if spec.uses_real_keys:
            modules['decoder_version'] = 'src/algorithms/real_keys.py'
        for field, module in modules.items():
            if procedure[field] != 'sha256:' + plan['source_sha256'][module]:
                raise ValueError('Recorded component hash differs from frozen code.')
        result = record['result']
        if result['status'] not in ('success', 'exhausted', 'error'):
            raise ValueError('Unknown result status.')
        row.update(status=result['status'], stop_reason=result['stop_reason'],
                   solver_ns=result['timing']['solver_ns'], best_cost=result['best_cost'])
        if result['best_route'] is not None:
            if graph is None:
                graph = load_fhcp_graph(key[0], root=root, manifest=plan['catalog']['path'])
            cost = evaluate_cost(graph, result['best_route'])
            validation = validate_cycle(graph, result['best_route'])
            if cost != result['best_cost']:
                raise ValueError('Independent cost mismatch.')
            declared = result['validation']['valid']
            if declared is not None and declared != validation.valid:
                raise ValueError('Independent cycle validation mismatch.')
            row['independent_valid'] = validation.valid
            claimed = result['success_within_budget']
            if claimed:
                first = result['timing']['first_success']
                if (not validation.valid or declared is not True or result['status'] != 'success'
                        or first is None or not 0 <= first['elapsed_ns'] <= plan['budget']['max_elapsed_ns']):
                    raise ValueError('Success lacks an independent cycle or an in-budget certificate.')
                row['certified_success'] = True
            elif result['status'] == 'success':
                raise ValueError('Success status without a within-budget certificate.')
        elif result['success_within_budget'] or result['status'] == 'success' or result['best_cost'] is not None:
            raise ValueError('Candidate metadata without a route.')
        if completion['returncode'] != 0 and row['status'] != 'error':
            raise ValueError('Nonzero return code with a successful process record.')
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as error:
        row.update(status='error', stop_reason='invalid_evidence', certified_success=False,
                   best_cost=None, evidence_error=str(error))
    return row


def verify_audit(directory, row):
    if not row.get('artifact_sha256'):
        raise ValueError(f'Missing artifact inventory: {directory}')
    for name, expected in row['artifact_sha256'].items():
        if name not in ('intent.json', 'stdout.json', 'stderr.log', 'exit.json', 'worker.json'):
            raise ValueError('Unexpected artifact path.')
        if file_hash(Path(directory) / name) != expected:
            raise ValueError(f'Changed artifact: {directory}/{name}')


def summarize(plan, members, rows, output):
    grouped = {}
    for row in rows:
        grouped.setdefault((row['instance'], row['algorithm']), []).append(row)
    cells = []
    for member in members:
        for instance in plan['assignments'][member]:
            for solver in plan['solvers']:
                selected = grouped.get((instance, solver['algorithm']), [])
                costs = [r['best_cost'] for r in selected if r['best_cost'] is not None]
                durations = [r['process_seconds'] for r in selected if r['process_seconds'] is not None]
                cells.append({'member': member, 'instance': instance, 'algorithm': solver['algorithm'],
                    'planned': len(plan['seeds']), 'attempted': len(selected),
                    'pending': len(plan['seeds']) - len(selected),
                    'successes': sum(r['certified_success'] for r in selected),
                    'errors': sum(r['status'] == 'error' for r in selected),
                    'external_timeouts': sum(r['stop_reason'] == 'external_timeout' for r in selected),
                    'time_limits': sum(r['stop_reason'] == 'time_limit' for r in selected),
                    'best_cost': min(costs) if costs else None,
                    'median_cost': statistics.median(costs) if costs else None,
                    'mean_process_seconds_all_attempts': statistics.mean(durations) if durations else None})
    solved = sorted({row['instance'] for row in rows if row['certified_success']},
                    key=lambda name: int(name.removeprefix('graph')))
    result = {'plan_sha256': plan['plan_sha256'], 'planned': sum(c['planned'] for c in cells),
              'attempted': len(rows), 'successes': sum(c['successes'] for c in cells),
              'distinct_solved_graphs': len(solved), 'solved_graph_ids': solved,
              'global_goal_distinct_solved_graphs': plan.get('goal_distinct_solved_graphs', 60),
              'errors': sum(c['errors'] for c in cells), 'cells': cells}
    atomic_json(Path(output) / 'summary.json', result)
    with (Path(output) / 'summary.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(cells[0]))
        writer.writeheader()
        writer.writerows(cells)
    text = '# Campaña distribuida\n\nÉxitos certificados / semillas previstas; errores incluidos en el denominador.\n\n'
    text += f"Grafos distintos resueltos en esta agregación: **{len(solved)}**. Objetivo global compartido: **{result['global_goal_distinct_solved_graphs']}**; no es un objetivo por integrante.\n\n"
    text += '| Integrante | Grafo | Algoritmo | Intentados | Éxitos | Pendientes | Mejor costo | Errores |\n|---|---|---|---:|---:|---:|---:|---:|\n'
    for cell in cells:
        text += f"| {cell['member']} | {cell['instance']} | {cell['algorithm']} | {cell['attempted']}/{cell['planned']} | {cell['successes']}/{cell['planned']} | {cell['pending']} | {cell['best_cost']} | {cell['errors']} |\n"
    text += '\nLos costos positivos no prueban no hamiltonicidad. Los tiempos CSV incluyen intentos censurados y errores con duración disponible; no son tiempos medios hasta resolver. Los equipos se identifican por separado y no se normalizan sus tiempos.\n'
    (Path(output) / 'summary.md').write_text(text, encoding='utf-8')
    return result
