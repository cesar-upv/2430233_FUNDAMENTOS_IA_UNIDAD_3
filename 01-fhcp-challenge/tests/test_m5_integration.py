"""Public-entry-point evidence for the six integrated solver families."""

from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

from src import algorithms
from src.algorithms.execution import Budget
from src.evaluation import validate_cycle
from src.graphs import Graph, load_fhcp_graph

ROOT = Path(__file__).resolve().parents[1]
INTEGER_PARAMETERS = {'population_size', 'tournament_size', 'ant_count', 'source_count',
                      'limit', 'swarm_size', 'moves_per_temperature'}


def _audit_route(graph, route, cost):
    assert sorted(route) == list(range(graph.vertex_count()))
    missing = sum(
        not graph.has_edge(route[index], route[(index + 1) % len(route)])
        for index in range(len(route))
    )
    assert cost == missing
    certificate = validate_cycle(graph, route)
    assert certificate.valid == (missing == 0)


def _audit_work(name, counters):
    assert counters['evaluations_started'] == counters['evaluations_completed'] == 20
    assert counters['full_evaluations'] == 20
    assert counters['incremental_evaluations'] == counters['cache_hits'] == 0
    assert counters['validations_started'] == counters['validations_completed'] == 0
    iterations = counters['iterations_completed']
    partial = counters['partial_iteration']
    if name == 'ga':
        assert 8 + 7 * iterations + partial['completed_items'] == 20
        assert partial == {'phase': 'generation', 'completed_items': 5, 'planned_items': 7}
    elif name == 'sa':
        assert iterations + 1 == 20 and partial is None
        events = counters['algorithm_counters']
        assert events.get('accepted_moves', 0) + events.get('rejected_moves', 0) == iterations
    elif name in ('de', 'pso'):
        assert 4 + 4 * iterations == 20 and partial is None
    elif name == 'as':
        assert 4 * iterations + partial['completed_items'] == 20
        assert partial == {'phase': 'round', 'completed_items': 4, 'planned_items': 5}
        assert counters['algorithm_counters']['pheromone_updates_completed'] == iterations
    else:
        events = counters['algorithm_counters']
        employed = events.get('employed_proposals', 0)
        onlookers = events.get('onlooker_proposals', 0)
        renewals = events.get('scout_renewals', 0)
        assert 4 + employed + onlookers + renewals == 20
        assert counters['restarts'] == renewals
        items = partial['completed_items'] if partial is not None else 0
        assert employed == 4 * iterations + min(items, 4)
        assert onlookers == 4 * iterations + min(max(items - 4, 0), 4)
        assert renewals + events.get('scout_skips', 0) == iterations + int(items == 9)
        if partial is not None:
            assert partial['phase'] == 'abc_cycle'
            assert 0 <= partial['completed_items'] <= partial['planned_items'] == 9


def test_public_cli_repeats_and_audits_each_fhcp_family(cli_solver_case, tmp_path):
    name, flags, family, unit, _ = cli_solver_case
    command = [sys.executable, '-m', 'src.cli', '--instance', 'graph1', '--seed', '17',
               '--max-evaluations', '20', '--algorithm', name, *flags, '--output-dir', str(tmp_path)]
    graph = load_fhcp_graph('graph1', root=ROOT)
    records = []
    for _ in range(2):
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                 encoding='utf-8', timeout=30)
        assert process.returncode == 0, process.stderr
        assert process.stderr == ''
        record = json.loads(process.stdout)
        saved = tmp_path / record['run']['run_id'] / 'run.json'
        assert json.loads(saved.read_text()) == record
        assert record['procedure']['family'] == family
        assert record['result']['counters']['iteration_unit'] == unit
        assert record['instance']['sha256'] == graph.source['sha256']
        result = record['result']
        assert result['status'] == 'exhausted' and result['stop_reason'] == 'evaluation_limit'
        assert result['limits_reached'] == ['evaluation_limit']
        assert result['success_within_budget'] is False and result['error'] is None
        assert result['validation']['reason'] == 'not_run'
        assert result['timing']['first_success'] is None
        _audit_route(graph, result['best_route'], result['best_cost'])
        _audit_work(name, result['counters'])
        records.append(record)
    first, repeated = records
    for field in ('procedure', 'instance', 'randomness', 'budget', 'code', 'environment'):
        assert first[field] == repeated[field]
    assert {k: v for k, v in first['result'].items() if k != 'timing'} == {
        k: v for k, v in repeated['result'].items() if k != 'timing'
    }
    assert first['run']['run_id'] != repeated['run']['run_id']
    assert len(list(tmp_path.iterdir())) == 2


def test_each_public_solver_certifies_a_separate_synthetic_graph(cli_solver_case):
    name, flags, _, unit, _ = cli_solver_case
    requested = {}
    for option, value in zip(flags[::2], flags[1::2]):
        key = option.removeprefix('--').replace('-', '_')
        requested[key] = int(value) if key in INTEGER_PARAMETERS else float(value)
    parameters = getattr(algorithms, f'resolve_{name}_parameters')(requested)
    solver = getattr(algorithms, f'solve_{name}')
    graph = Graph([10, 30, 90], [(10, 30), (30, 90), (90, 10)])
    result = solver(graph, parameters=parameters, seed=17, budget=Budget(max_evaluations=1))
    assert result.status == 'success' and result.success_within_budget
    assert result.validation.valid is True
    _audit_route(graph, result.best_route, result.best_cost)
    assert result.counters.evaluations_started == result.counters.evaluations_completed == 1
    assert result.counters.validations_started == result.counters.validations_completed == 1
    assert result.counters.iterations_completed == 0
    assert result.counters.iteration_unit == unit
    assert result.timing.first_success is not None
    assert result.timing.first_success.evaluations_completed == 1
    assert result.limits_reached == ('evaluation_limit',)
    json.dumps(asdict(result), allow_nan=False)
