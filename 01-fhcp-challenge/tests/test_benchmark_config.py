"""Check the preregistered M6 plan against the integrated public contracts.

These checks exercise configuration compatibility, not a batch runner or a
measurement of solver performance. No official certificates are read.
"""

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

import pytest

from src.algorithms.execution import Budget
from src.cli.__main__ import _parser
from src.cli.variants import VARIANTS
from src.graphs import Graph

ROOT = Path(__file__).resolve().parents[1]


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, f'Duplicate JSON key: {key}'
        result[key] = value
    return result


def _reject_constant(value):
    raise AssertionError(f'Nonfinite JSON value: {value}')


PLAN = json.loads(
    (ROOT / 'experiments/configs/benchmark-v1.json').read_text(encoding='utf-8'),
    object_pairs_hook=_unique_object, parse_constant=_reject_constant,
)


def test_dataset_snapshot_preserves_partition_and_original_graphs():
    reference = PLAN['dataset_manifest']
    raw = (ROOT / reference['path']).read_bytes()
    assert sha256(raw).hexdigest() == reference['sha256']
    source = json.loads(raw)
    assert len(PLAN['instances']) == 9
    assert len({row['id'] for row in PLAN['instances']}) == 9
    for row, original in zip(PLAN['instances'], source['instances'], strict=True):
        assert row == {key: original[key] for key in row}
        graph_bytes = (ROOT / 'data/raw/FHCPCS' / original['archive_member']).read_bytes()
        assert sha256(graph_bytes).hexdigest() == row['sha256']
    partitions = {row['id']: row['partition'] for row in PLAN['instances']}
    for phase, partition in [('smoke', 'smoke'), ('tuning', 'tuning'),
                             ('evaluation', 'evaluation'), ('scale', 'evaluation_scale')]:
        assert set(PLAN['phases'][phase]['instances']) == {
            name for name, use in partitions.items() if use == partition
        }


def test_catalog_covers_exactly_two_distinct_candidates_per_integrated_family():
    assert PLAN['schema_version'] == 'fhcp-benchmark-config/1'
    assert PLAN['algorithms'] == list(VARIANTS)
    catalog = PLAN['configurations']
    assert len({entry['config_id'] for entry in catalog}) == len(catalog) == 12
    for name in PLAN['algorithms']:
        candidates = [entry for entry in catalog if entry['algorithm'] == name]
        assert [entry['config_id'] for entry in candidates] == [f'{name}-c1', f'{name}-c2']
        first, second = [entry['parameters'] for entry in candidates]
        assert first.keys() == second.keys()
        assert sum(first[key] != second[key] for key in first) == 1


@pytest.mark.parametrize('entry', PLAN['configurations'], ids=lambda entry: entry['config_id'])
def test_every_candidate_is_effective_cli_compatible_and_certifies_synthetic_cycle(entry):
    spec = VARIANTS[entry['algorithm']]
    parameters = entry['parameters']
    assert (entry['family'], entry['variant'], entry['iteration_unit']) == (
        spec.family, spec.name, spec.iteration_unit,
    )
    assert set(parameters) == set(spec.options)
    effective = spec.resolve(parameters)
    assert effective == parameters
    # Float normalization affects canonical configuration hashes; compare bytes too.
    assert json.dumps(effective, sort_keys=True) == json.dumps(parameters, sort_keys=True)
    flags = ['--instance', 'graph1', '--algorithm', entry['algorithm'],
             '--variant', entry['variant'], '--seed', '17', '--max-evaluations', '1']
    for key, value in parameters.items():
        if value is not None:
            flags.extend(['--' + key.replace('_', '-'), str(value)])
    parsed = vars(_parser().parse_args(flags))
    assert spec.resolve({key: parsed[key] for key in spec.options if parsed[key] is not None}) == effective
    # A real solver call checks budget admission/certification with the exact
    # catalog parameters, without starting tuning or using an FHCP tour.
    graph = Graph([10, 30, 90], [(10, 30), (30, 90), (90, 10)])
    result = spec.solve(graph, parameters=parameters, seed=17, budget=Budget(max_evaluations=1))
    assert result.status == 'success' and result.success_within_budget
    assert result.validation.valid is True
    assert result.best_cost == 0 and sorted(result.best_route) == [0, 1, 2]
    assert result.counters.evaluations_started == result.counters.evaluations_completed == 1
    assert result.counters.validations_completed == 1


def test_phase_counts_seeds_and_work_limits_are_consistent():
    expected = {'smoke': 12, 'tuning': 120, 'evaluation': 720, 'scale': 180, 'verification': 6}
    allowed_sources = {'smoke': 'candidate_1_per_algorithm', 'tuning': 'all_candidates',
                       'evaluation': 'frozen_selection', 'scale': 'frozen_selection',
                       'verification': 'frozen_selection'}
    assert set(PLAN['phases']) == set(expected)
    for name, phase in PLAN['phases'].items():
        seeds = phase['seeds_decimal']
        assert len(set(seeds)) == len(seeds)
        assert all(str(int(seed)) == seed and 0 <= int(seed) < 2**64 for seed in seeds)
        assert phase['configuration_source'] == allowed_sources[name]
        candidate_count = 12 if name == 'tuning' else 6
        assert len(phase['instances']) == len(set(phase['instances']))
        assert len(phase['instances']) * len(seeds) * candidate_count == phase['expected_trials'] == expected[name]
        budget = Budget(**phase['budget'])
        assert all(value is None or type(value) is int and value > 0 for value in asdict(budget).values())
        assert budget.max_evaluations is not None and budget.max_iterations is None
        assert phase['external_timeout_ns'] == 120_000_000_000
        if name == 'verification':
            assert budget.max_elapsed_ns is None
        else:
            assert 0 < budget.max_elapsed_ns < phase['external_timeout_ns']
    assert PLAN['phases']['smoke']['seeds_decimal'] == ['17']
    assert PLAN['phases']['tuning']['seeds_decimal'] == ['101', '211', '307', '401', '503']
    evaluation = PLAN['phases']['evaluation']
    scale = PLAN['phases']['scale']
    assert evaluation['seeds_decimal'] == scale['seeds_decimal'] == [str(seed) for seed in range(1001, 1031)]
    assert evaluation['budget'] == scale['budget']
    assert set(evaluation['seeds_decimal']).isdisjoint(PLAN['phases']['tuning']['seeds_decimal'])
    assert PLAN['attempts'] == dict(primary='first_started', retries_in_primary=False, automatic_retries=0)


def test_estimated_process_time_and_pheromone_storage_match_the_plan():
    phases = PLAN['phases']
    primary_count = sum(phase['expected_trials'] for key, phase in phases.items() if key != 'verification')
    assert primary_count == 1032
    process_count = primary_count + 2 * phases['verification']['expected_trials']
    assert process_count == 1044
    assert process_count * 120 == 125280
    solver_ns = sum(phase['expected_trials'] * (phase['budget']['max_elapsed_ns'] or 0)
                    for phase in phases.values())
    assert solver_ns == 28_260_000_000_000
    n = next(row['dimension'] for row in PLAN['instances'] if row['id'] == 'graph1001')
    pheromone_bytes = 8 * n * (n - 1) // 2
    assert pheromone_bytes == 363_093_024
    assert pheromone_bytes < PLAN['execution']['minimum_available_ram_bytes'] == 4 * 1024**3
    assert PLAN['execution']['workers'] == PLAN['execution']['native_threads'] == 1
    assert set(PLAN['execution']['environment_variables'].values()) == {'1'}
