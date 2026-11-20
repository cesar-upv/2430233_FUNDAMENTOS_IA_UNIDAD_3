"""Run the fixed, exploratory three-graph plan; never replace prior results."""
import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cli.batch import resource_sample
from src.evaluation import evaluate_cost, validate_cycle
from src.graphs import load_fhcp_graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate setup without running solvers')
    args = parser.parse_args()
    os.chdir(ROOT)
    config_path = ROOT / 'experiments/configs/search-exploration-40min.json'
    config = json.loads(config_path.read_text())
    presets = json.loads((ROOT / config['presets']).read_text())
    graphs = {name: load_fhcp_graph(name, root=ROOT) for name in config['instances']}
    cpu = config['cpu']
    if cpu not in os.sched_getaffinity(0):
        raise SystemExit(f'CPU {cpu} is unavailable.')
    resources = resource_sample(cpu)
    if not shutil.which('taskset') or not (ROOT / '.venv/bin/python').exists():
        raise SystemExit('Missing taskset or .venv/bin/python.')
    print(json.dumps({'instances': list(graphs), 'solvers': [s['algorithm'] for s in presets['solvers']],
                      'seeds': config['seeds'], 'planned': 180, 'resources': resources}, indent=2), flush=True)
    if args.check:
        return
    if not resources['ac_online'] or (resources['available_ram_bytes'] or 0) < 4 * 1024**3:
        raise SystemExit('Connect AC and leave at least 4 GiB available RAM before starting.')
    output = ROOT / 'experiments/results' / ('search-exploration-' + str(uuid.uuid4()))
    output.mkdir()
    print(f'RESULTADOS: {output}', flush=True)
    (ROOT / '.tools').mkdir(exist_ok=True)
    (ROOT / '.tools/latest-search-exploration.txt').write_text(str(output) + '\n')
    log = (output / 'terminal.log').open('w', buffering=1)

    def report(message):
        print(message, flush=True)
        log.write(message + '\n')

    def write(path, value):
        path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

    source_hashes = {}
    for source in sorted((ROOT / 'src').rglob('*.py')):
        relative = source.relative_to(ROOT)
        destination = output / 'source-snapshot' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        source_hashes[str(relative)] = sha256(source.read_bytes()).hexdigest()
    shutil.copy2(__file__, output / 'runner.py')
    write(output / 'plan.json', {'config': config, 'presets': presets, 'source_sha256': source_hashes,
          'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
          'started_utc': datetime.now(timezone.utc).isoformat(), 'resources': resources,
          'purpose': 'Exploratory, reused instances; separate from M6; local modified source snapshot retained'})
    rows = []
    start = time.monotonic()
    deadline = start + config['session_seconds']
    env = {**os.environ, **{key: '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                                               'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')}}

    def summarize():
        summary = []
        for instance in graphs:
            for solver in presets['solvers']:
                selected = [r for r in rows if r['instance'] == instance and r['algorithm'] == solver['algorithm']]
                costs = [r['best_cost'] for r in selected if r['best_cost'] is not None]
                summary.append({'instance': instance, 'algorithm': solver['algorithm'], 'attempted': len(selected),
                    'planned': len(config['seeds']), 'certified_successes': sum(r['certified_success'] for r in selected),
                    'errors': sum(r['status'] == 'error' for r in selected),
                    'best_cost': min(costs) if costs else None,
                    'median_cost': statistics.median(costs) if costs else None,
                    'mean_process_seconds': statistics.mean(r['process_seconds'] for r in selected) if selected else None})
        write(output / 'summary.json', {'attempted': len(rows), 'planned': 180, 'cells': summary})
        with (output / 'summary.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
            writer.writeheader()
            writer.writerows(summary)
        table = '# Prueba exploratoria\n\n10 semillas; 10 s o 1,000,000 evaluaciones por intento. Instancias reutilizadas; separado de M6.\n\n'
        table += '| Grafo | Algoritmo | Intentados/10 | Ciclos certificados/10 | Mejor costo | Mediana costo | Errores |\n|---|---|---:|---:|---:|---:|---:|\n'
        for row in summary:
            table += f"| {row['instance']} | {row['algorithm']} | {row['attempted']} | {row['certified_successes']} | {row['best_cost']} | {row['median_cost']} | {row['errors']} |\n"
        table += '\nCosto positivo: aristas faltantes, no prueba de imposibilidad. None: sin candidato disponible. Los tiempos CSV incluyen arranque del proceso y los intentos censurados; no son tiempos medios hasta resolver. Intentos no iniciados = 10 menos intentados. Los errores permanecen en el denominador previsto.\n'
        (output / 'summary.md').write_text(table)

    summarize()
    stop = 'complete'
    try:
        for seed in config['seeds']:
            for instance, graph in graphs.items():
                for solver in presets['solvers']:
                    if deadline - time.monotonic() < config['process_timeout_seconds'] + 3:
                        stop = 'session_time_limit'
                        return
                    before = resource_sample(cpu)
                    if not before['ac_online'] or (before['available_ram_bytes'] or 0) < 4 * 1024**3:
                        stop = 'ac_or_memory_unavailable'
                        return
                    for name, digest in source_hashes.items():
                        if sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                            stop = 'source_changed'
                            return
                    algorithm = solver['algorithm']
                    attempt = output / f'{instance}-{algorithm}-{seed}'
                    attempt.mkdir()
                    command = ['taskset', '-c', str(cpu), str(ROOT / '.venv/bin/python'), '-m', 'src.cli',
                        '--instance', instance, '--algorithm', algorithm, '--seed', str(seed),
                        '--max-evaluations', str(config['max_evaluations']),
                        '--max-elapsed-ns', str(config['max_elapsed_ns']), '--output-dir', str(attempt / 'records')]
                    for key, value in solver['parameters'].items():
                        command.extend(['--' + key.replace('_', '-'), str(value)])
                    write(attempt / 'command.json', command)
                    row = dict(instance=instance, algorithm=algorithm, seed=seed, status='error', best_cost=None,
                               certified_success=False, resources_before=before)
                    started = time.monotonic()
                    interrupted = False
                    with (attempt / 'stdout.json').open('w') as stdout, (attempt / 'stderr.log').open('w') as stderr:
                        try:
                            process = subprocess.run(command, env=env, stdout=stdout, stderr=stderr,
                                                     timeout=config['process_timeout_seconds'])
                            row['returncode'] = process.returncode
                        except subprocess.TimeoutExpired:
                            row['error'] = 'external_timeout'
                        except KeyboardInterrupt:
                            row['error'] = 'interrupted'
                            interrupted = True
                    row['process_seconds'] = time.monotonic() - started
                    row['resources_after'] = resource_sample(cpu)
                    if row.get('returncode') == 0:
                        try:
                            record = json.loads((attempt / 'stdout.json').read_text())
                            result = record['result']
                            row.update(status=result['status'], best_cost=result['best_cost'],
                                       stop_reason=result['stop_reason'], counters=result['counters'], timing=result['timing'])
                            if result['best_route'] is not None:
                                cost = evaluate_cost(graph, result['best_route'])
                                validation = validate_cycle(graph, result['best_route'])
                                row['independent_validation'] = asdict(validation)
                                row['recalculated_cost'] = cost
                                if cost != result['best_cost'] or (result['validation']['valid'] is not None and validation.valid != result['validation']['valid']):
                                    raise ValueError('Independent cost/validation mismatch')
                                row['certified_success'] = bool(validation.valid and result['success_within_budget'])
                        except (ValueError, KeyError, TypeError) as error:
                            row.update(status='error', error=str(error), certified_success=False)
                    write(attempt / 'audit.json', row)
                    rows.append(row)
                    summarize()
                    report(f"{len(rows)}/180 {instance} {algorithm} seed={seed}: {row['status']}, costo={row['best_cost']}, certificado={row['certified_success']}")
                    if interrupted:
                        stop = 'interrupted'
                        return
    except KeyboardInterrupt:
        stop = 'interrupted'
    except Exception:
        stop = 'runner_error'
        raise
    finally:
        summarize()
        write(output / 'session.json', {'stop_reason': stop, 'attempted': len(rows), 'planned': 180,
              'elapsed_seconds': time.monotonic() - start, 'ended_utc': datetime.now(timezone.utc).isoformat()})
        report(f'FIN: {stop}. Tabla: {output / "summary.md"}')
        log.close()


if __name__ == '__main__':
    main()
