"""Audit a benchmark batch and publish a new, reproducible analysis directory."""

import argparse
import csv
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from src.evaluation.benchmark import OUTCOMES, aggregate, audit_batch, evidence_path, file_hash
from .__main__ import _ROOT
from .benchmark_plan import expand_plan, load_config, load_freeze, read_json
from .run_record import _code, _environment
from .variants import VARIANTS


def generate(root, manifest_path):
    root, manifest_path = Path(root).resolve(), Path(manifest_path).resolve()
    manifest = read_json(manifest_path)
    paths = {r['role']: evidence_path(root, manifest_path.parent, r['path']) for r in manifest['inputs']}
    config = load_config(root, paths['config'])
    selection = None
    if config['phases'][manifest['phase']]['configuration_source'] == 'frozen_selection':
        if 'freeze' not in paths:
            raise ValueError('Frozen phase requires original freeze evidence.')
        _, selection = load_freeze(root, paths['freeze'], config, paths['config'])
    expected = expand_plan(config, manifest['phase'], selection)
    modules = {name: f'src/algorithms/{spec.module}.py' for name, spec in VARIANTS.items()}
    manifest, rows = audit_batch(root, manifest_path, config, expected, modules)
    summaries = aggregate(manifest, rows)
    missing = []
    code, environment = _code(root, missing), _environment(missing)
    output = manifest_path.parent / 'analyses' / str(uuid4())
    output.mkdir(parents=True, exist_ok=False)
    def write_json(name, value):
        (output / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    write_json('attempts.json', rows)
    write_json('summary.json', summaries)
    fields = ('instance_id', 'algorithm', 'config_id', 'phase', 'environment_id', 'code_commit',
              'expected', 'resolved', 'pending', 'successes', 'final', 'success_percent',
              'provisional_lower_bound_percent', 'binary_sample_stdev', 'iteration_unit', 'max_peak_rss_bytes')
    with (output / 'summary.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({k: row[k] for k in fields} for row in summaries)
    with (output / 'attempts.csv').open('w', newline='', encoding='utf-8') as stream:
        fields = ('batch_id', 'trial_id', 'attempt_id', 'run_id', 'config_id', 'role', 'resolved',
                  'outcome', 'record_path', 'record_sha256', 'normalized_cost')
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({k: row[k] for k in fields} for row in rows)
    for name, source in (('durations.csv', 'timings_seconds'), ('counters.csv', 'counters')):
        with (output / name).open('w', newline='', encoding='utf-8') as stream:
            fields = ('instance_id', 'algorithm', 'config_id', 'metric', 'unit', 'observed', 'missing',
                      'mean', 'median', 'q1', 'q3', 'sample_stdev')
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for summary in summaries:
                metrics = dict(summary[source])
                if source == 'timings_seconds':
                    metrics['first_success_ns'] = summary['success_time_seconds']
                for key, values in metrics.items():
                    writer.writerow({**{k: summary[k] for k in ('instance_id', 'algorithm', 'config_id')},
                                     'metric': key, 'unit': 'seconds' if source=='timings_seconds' else 'count', **values})
    with (output / 'outcomes.csv').open('w', newline='', encoding='utf-8') as stream:
        fields = ('instance_id', 'algorithm', 'config_id', 'outcome', 'count')
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for summary in summaries:
            for outcome in sorted(OUTCOMES):
                count = summary['outcomes'].get(outcome, 0)
                writer.writerow({**{k: summary[k] for k in ('instance_id', 'algorithm', 'config_id')},
                                 'outcome': outcome, 'count': count})
    _plots(output, manifest, rows, summaries, config)
    inputs = [{'path': manifest_path.relative_to(root).as_posix(), 'sha256': file_hash(manifest_path)}]
    inputs += [dict(item) for item in manifest['inputs'] + manifest['artifacts']]
    metadata = dict(schema_version='fhcp-benchmark-analysis/1', created_at_utc=datetime.now(UTC).isoformat(),
                    batch_id=manifest['batch_id'], phase=manifest['phase'], protocol_id=config['protocol_id'],
                    configuration=dict(attempt_policy='first_started_primary', quartiles='linear_n_minus_1',
                                       variability='sample_n_minus_1', duration_unit='seconds', missing='null'),
                    analysis_code=code,
                    analysis_modules={str(p.relative_to(root)): file_hash(p) for p in
                                      (root/'src/evaluation/benchmark.py', root/'src/cli/benchmark_analysis.py')},
                    analysis_environment=environment, inputs=inputs, missing_metadata=missing,
                    precision_recall_f1='N/A: search does not predict a negative FHCP class',
                    final=all(r['final'] for r in summaries),
                    command=[sys.executable, '-m', 'src.cli.benchmark_analysis', str(manifest_path.relative_to(root))],
                    outputs=[dict(path=p.name, sha256=file_hash(p)) for p in sorted(output.iterdir()) if p.is_file()])
    write_json('analysis.json', metadata)
    return output, summaries


def _plots(output, manifest, rows, summaries, config):
    # Headless rendering; interactive/display backends never enter the solver.
    os.environ.setdefault('MPLCONFIGDIR', str(_ROOT / '.tools/matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    dimensions = {r['id']: r['dimension'] for r in config['instances']}
    dataset = read_json(_ROOT / config['dataset_manifest']['path'])
    structures = {r['id']: r.get('documented_structure') or 'no documentada' for r in dataset['instances']}
    for instance in sorted({r['instance_id'] for r in summaries}):
        selected = [r for r in summaries if r['instance_id'] == instance]
        labels = [r['config_id'] for r in selected]
        fig, axes = plt.subplots(3, 1, figsize=(11, 11), layout='constrained')
        values = [r['success_percent'] if r['final'] else r['provisional_lower_bound_percent'] for r in selected]
        axes[0].bar(labels, values)
        axes[0].set(ylim=(0, 100), ylabel='Éxitos / N previsto (%)')
        for i, r in enumerate(selected):
            axes[0].text(i, values[i]+1, f"{r['successes']}/{r['expected']}" + (' provisional' if not r['final'] else ''),
                         ha='center', fontsize=8)
        for axis, key, title in ((axes[1], 'solver_ns', 'Solver completo'),
                                 (axes[2], 'process_elapsed_ns', 'Proceso CLI completo')):
            samples = []
            for r in selected:
                samples.append([a['timings'][key]/1e9 for a in rows
                                if a['role']=='primary' and a['identity']['instance_id']==instance
                                and a['config_id']==r['config_id'] and a['timings'].get(key) is not None])
            axis.boxplot(samples, tick_labels=[f'{label}\nn={len(s)}' for label, s in zip(labels, samples)])
            axis.set(ylabel=f'{title} (s)')
        budget = selected[0]['budget']
        fig.suptitle(f"{manifest['phase']} · {instance} · n={dimensions[instance]} · estructura: {structures[instance]}\n"
                     f"Evaluaciones ≤ {budget['max_evaluations']} · plazo solver={None if budget['max_elapsed_ns'] is None else budget['max_elapsed_ns']/1e9} s")
        fig.savefig(output / f'{instance}.svg', metadata={'Date': None})
        svg = output / f'{instance}.svg'
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
        fig.savefig(output / f'{instance}.png', dpi=120)
        plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args(argv)
    try:
        output, summaries = generate(_ROOT, args.manifest)
        print(json.dumps(dict(analysis=str(output), final=all(r['final'] for r in summaries))))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f'analysis_error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
