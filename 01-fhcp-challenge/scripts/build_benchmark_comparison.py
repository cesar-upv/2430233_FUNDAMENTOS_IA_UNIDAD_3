"""Derive the #71 comparison tables from accepted, hash-checked M6 analyses."""
import csv
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = Path('experiments/results/e390b61f-aae4-4248-ba71-4467920d7bac')
OUTPUT = ROOT / 'docs/research/evidence/m6'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_csv(name, rows):
    with (OUTPUT / name).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    state = read(ROOT / CAMPAIGN / 'manifest.json')
    config_path = ROOT / state['config_path']
    if sha256(config_path.read_bytes()).hexdigest() != state['config_sha256']:
        raise ValueError('Campaign configuration hash changed.')
    config = read(config_path)
    instances = {row['id']: row for row in config['instances']}
    cells, contrasts = [], []
    sources = read(OUTPUT / 'published-results.json')['sources']
    for phase in ('smoke', 'tuning', 'evaluation', 'scale', 'verification'):
        info = state['phases'][phase]
        directory = ROOT / info['analysis_path']
        metadata_path = directory / 'analysis.json'
        if sha256(metadata_path.read_bytes()).hexdigest() != info['analysis_sha256']:
            raise ValueError('Original analysis metadata changed.')
        metadata = read(metadata_path)
        for item in metadata['outputs']:
            if sha256((directory / item['path']).read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('Original analysis output changed: ' + item['path'])
        attempts = read(directory / 'attempts.json')
        for row in read(directory / 'summary.json'):
            if not row['final'] or row['pending']:
                raise ValueError('Incomplete campaign cell.')
            n = instances[row['instance_id']]['dimension']
            m = instances[row['instance_id']]['edge_count']
            selected = [a for a in attempts if a['identity']['instance_id'] == row['instance_id']
                        and a['config_id'] == row['config_id']
                        and a['role'] == 'primary']
            costs = [round(a['normalized_cost'] * n) for a in selected
                     if a['normalized_cost'] is not None]
            timing = row['timings_seconds']['solver_ns']
            cells.append(dict(phase=phase, instance=row['instance_id'], n=n, m=m,
                mean_degree=2*m/n, density=2*m/(n*(n-1)), algorithm=row['algorithm'],
                config_id=row['config_id'], expected_primary=row['expected'], resolved_primary=row['resolved'],
                records_all_roles=sum(a['identity']['instance_id']==row['instance_id'] and a['config_id']==row['config_id'] for a in attempts),
                successes=row['successes'],
                without_candidate_primary=sum(a['normalized_cost'] is None for a in selected),
                other_outcomes=sum(count for outcome,count in row['outcomes'].items()
                                   if outcome not in ('success','exhausted','cooperative_timeout')),
                cooperative_timeouts=row['outcomes'].get('cooperative_timeout', 0),
                best_primary_cost=min(costs) if costs else None,
                solver_median_seconds=timing['median'], solver_q1_seconds=timing['q1'],
                solver_q3_seconds=timing['q3'], solver_sample_stdev_seconds=timing['sample_stdev'],
                mean_evaluations=row['counters']['evaluations_completed']['mean'],
                max_peak_rss_bytes=row['max_peak_rss_bytes'], original_analysis=info['analysis_path'],
                original_attempts=str(Path(info['analysis_path'])/'attempts.json'),
                original_commit=row['code_commit']))
            for source in sources:
                times = source.get('instance_seconds') or {}
                if row['instance_id'] not in times:
                    continue
                contrasts.append(dict(source_id=source['id'], locator=source['locator'],
                    instance=row['instance_id'], own_phase=phase, own_algorithm=row['algorithm'],
                    own_config=row['config_id'], own_successes=row['successes'],
                    own_expected=row['expected'], own_solver_median_seconds=timing['median'],
                    published_algorithm=source['algorithm'],
                    published_output=source.get('instance_output', {}).get(row['instance_id'], 'HC'),
                    published_seconds=times[row['instance_id']], equivalent_conditions=False,
                    limitation='Different method, hardware/budget/repetitions; smoke/verification are not final evaluation',
                    source_url=source['url']))
    assert len(cells) == 72 and sum(r['records_all_roles'] for r in cells) == 1044
    write_csv('campaign-cells.csv', cells)
    write_csv('published-contrast.csv', contrasts)
    print(f'{len(cells)} campaign cells; {len(contrasts)} qualified contrasts; 1044 resolved attempts')


if __name__ == '__main__':
    main()
