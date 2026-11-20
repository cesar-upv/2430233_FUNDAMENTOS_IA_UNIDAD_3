"""The campaign's time-only budget, with controlled clocks instead of real waits."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from src.algorithms.execution import Budget, SolverRun, start_run
from src.cli import __main__ as cli
from src.cli.variants import VARIANTS
from src.evaluation import evaluate_cost, validate_cycle
from src.graphs import Graph

ROOT = Path(__file__).resolve().parents[1]
SOLVERS = json.loads((ROOT / 'experiments/configs/search-enhanced-v3-presets.json').read_text())['solvers']
LIMIT = 30_000_000_000


class TickClock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        self.now += 1_000_000
        return self.now


def ring():
    return Graph(range(8), [(i, i + 1) for i in range(7)] + [(0, 7)])


@pytest.mark.parametrize('solver', SOLVERS, ids=lambda s: s['algorithm'])
def test_enhanced_solver_exhausts_time_without_evaluation_or_iteration_cap(solver):
    # An isolated vertex prevents accidental early success; it is only a fixture,
    # not a claim that solver exhaustion proves non-Hamiltonicity.
    graph = Graph(range(8), [(i, i + 1) for i in range(6)])
    budget = Budget(max_elapsed_ns=LIMIT)
    assert budget.max_evaluations is None and budget.max_iterations is None
    result = VARIANTS[solver['algorithm']].solve(
        graph, parameters=solver['parameters'], seed=1001, budget=budget, clock=TickClock(),
    )
    assert result.status == 'exhausted' and result.stop_reason == 'time_limit'
    assert result.timing.solver_ns >= LIMIT
    assert result.counters.evaluations_completed > 0 and result.counters.iterations_completed > 0
    assert not result.success_within_budget
    assert result.best_cost == evaluate_cost(graph, result.best_route)
    assert not validate_cycle(graph, result.best_route).valid


@pytest.mark.parametrize('solver', SOLVERS, ids=lambda s: s['algorithm'])
def test_time_only_solver_certifies_and_stops_before_deadline(solver):
    graph = ring()
    result = VARIANTS[solver['algorithm']].solve(
        graph, parameters=solver['parameters'], seed=1001,
        budget=Budget(max_elapsed_ns=LIMIT), clock=TickClock(),
    )
    assert result.status == 'success' and result.stop_reason == 'validated_cycle'
    assert result.success_within_budget and result.validation.valid
    assert result.counters.evaluations_completed == 1
    assert result.timing.first_success.elapsed_ns < LIMIT
    assert evaluate_cost(graph, result.best_route) == 0
    assert validate_cycle(graph, result.best_route).valid


def test_time_only_deadline_rejects_late_incremental_zero_before_certification():
    graph = ring()
    now = [0]
    run = start_run(graph, seed=1001, budget=Budget(max_elapsed_ns=LIMIT),
                    iteration_unit='move', clock=lambda: now[0])
    assert isinstance(run, SolverRun) and run.begin_phase('search', 1)

    def late_cost(graph, route):
        now[0] = LIMIT
        return 0

    assert run.evaluate_incremental(tuple(range(8)), late_cost) == 0
    result = run.certify_best()
    assert result.status == 'exhausted' and result.stop_reason == 'time_limit'
    assert not result.success_within_budget and result.counters.validations_started == 0


@pytest.mark.parametrize('solver', SOLVERS, ids=lambda s: s['algorithm'])
def test_time_only_cli_records_no_hidden_evaluation_or_iteration_limit(solver, monkeypatch, capsys):
    algorithm = solver['algorithm']
    original = VARIANTS[algorithm]

    def controlled_solve(graph, *, parameters, seed, budget):
        assert budget == Budget(max_elapsed_ns=LIMIT)
        return original.solve(graph, parameters=parameters, seed=seed, budget=budget, clock=TickClock())

    monkeypatch.setitem(cli.VARIANTS, algorithm, replace(original, solve=controlled_solve))
    monkeypatch.setattr(cli, 'load_fhcp_graph', lambda *args, **kwargs: ring())
    args = ['--instance', 'synthetic-ring', '--algorithm', algorithm, '--seed', '1001',
            '--max-elapsed-ns', str(LIMIT)]
    for name, value in solver['parameters'].items():
        args.extend(['--' + name.replace('_', '-'), str(value)])
    assert cli.main(args) == 0
    record = json.loads(capsys.readouterr().out)
    assert record['budget']['max_elapsed_ns'] == LIMIT
    assert record['budget']['max_evaluations'] is None and record['budget']['max_iterations'] is None
    assert record['result']['success_within_budget'] and record['result']['validation']['valid']
