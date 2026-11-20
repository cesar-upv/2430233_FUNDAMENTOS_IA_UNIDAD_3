"""ABC-specific rules and integration with the common execution contract."""

from dataclasses import asdict
from types import SimpleNamespace

import numpy as np
import pytest

from src.algorithms import abc, execution
from src.algorithms.execution import Budget
from src.evaluation import evaluate_cost, validate_cycle
from src.graphs import Graph

PARAMETERS = {"source_count": 2, "limit": 100}


class Clock:
    now = 0

    def __call__(self):
        return self.now


def solve(graph=None, *, parameters=None, budget=None, seed=7, clock=None):
    return abc.solve_abc(
        Graph(range(5), []) if graph is None else graph,
        parameters=PARAMETERS if parameters is None else parameters,
        seed=seed, budget=Budget(max_evaluations=9) if budget is None else budget,
        clock=Clock() if clock is None else clock,
    )


def test_parameters_are_copied():
    params = dict(PARAMETERS)
    effective = abc.resolve_abc_parameters(params)
    params["limit"] = 1
    assert effective == PARAMETERS


@pytest.mark.parametrize("params", [None, {}, {"source_count": 2},
    {**PARAMETERS, "extra": 1}, {1: 2},
    *[{**PARAMETERS, "source_count": x} for x in (1, True, 2.0, np.int64(2))],
    *[{**PARAMETERS, "limit": x} for x in (0, -1, True, float("nan"))],
])
def test_config_rejected_before_clock_or_rng(params, monkeypatch):
    def forbidden(*args):
        pytest.fail("Invalid configuration started a run")
    monkeypatch.setattr(execution.np.random, "PCG64", forbidden)
    result = abc.solve_abc(
        Graph(range(3), []), parameters=params, seed=0,
        budget=Budget(max_evaluations=1), clock=forbidden,
    )
    assert result.status == "error" and result.stop_reason == "invalid_config"
    assert result.counters.evaluations_started == result.timing.solver_ns == 0


def test_guided_neighbor_and_identical_fallback():
    p, partner = (0, 1, 2, 3), (0, 2, 1, 3)
    choices = []
    def integers(high):
        choices.append(high)
        return 0
    rng = SimpleNamespace(integers=integers, choice=lambda n, size, replace: np.array([0, 3]))
    assert abc._guided_neighbor(p, partner, rng) == (0, 2, 1, 3)
    assert choices == [2]
    assert abc._guided_neighbor(p, p, rng) == (3, 1, 2, 0)
    assert p == (0, 1, 2, 3) and partner == (0, 2, 1, 3)


def test_partner_never_selects_self():
    for i in range(4):
        selected = {abc._partner_index(i, 4, SimpleNamespace(integers=lambda n, j=j: j)) for j in range(3)}
        assert selected == set(range(4)) - {i}


def test_strict_improvement_trials_and_scout_ties():
    source = abc._Source((0, 1, 2), 3, 4)
    abc._accept(source, (1, 0, 2), 3)
    assert source.trials == 5 and source.route == (0, 1, 2)
    abc._accept(source, (1, 0, 2), 2)
    assert (source.route, source.cost, source.trials) == ((1, 0, 2), 2, 0)
    sources = [abc._Source((0, 1, 2), 2, t) for t in (5, 6, 6)]
    assert abc._scout_index(sources, 5) == 1
    assert abc._scout_index(sources, 7) is None


def test_onlooker_weights_are_frozen_and_proportional():
    sources = [abc._Source((0, 1, 2), c) for c in (1, 2)]
    probabilities = abc._onlooker_weights(sources)
    sources[0].cost = 5
    assert probabilities == pytest.approx((0.6, 0.4))


@pytest.mark.parametrize("cap, phase, items, cycles", [
    (1, "initialization", 1, 0), (2, None, None, 0),
    (3, "abc_cycle", 1, 0), (4, "abc_cycle", 2, 0),
    (5, "abc_cycle", 3, 0), (6, None, None, 1),
])
def test_budget_in_each_phase(cap, phase, items, cycles):
    result = solve(budget=Budget(max_evaluations=cap))
    assert result.stop_reason == "evaluation_limit"
    assert result.counters.evaluations_started == result.counters.evaluations_completed == cap
    assert result.counters.iterations_completed == cycles
    partial = result.counters.partial_iteration
    assert (partial.phase, partial.completed_items) == (phase, items) if phase else partial is None


def test_scout_budget_and_best_history(monkeypatch):
    routes = iter([(0, 1, 2, 3, 4), (1, 0, 2, 3, 4), (4, 3, 2, 1, 0)])
    monkeypatch.setattr(abc, "initialize_route", lambda n, rng: next(routes))
    result = solve(parameters={"source_count": 2, "limit": 1}, budget=Budget(max_evaluations=7))
    assert result.best_route == (0, 1, 2, 3, 4)
    assert result.counters.iterations_completed == 1
    assert result.counters.restarts == 1
    assert result.counters.algorithm_counters["scout_renewals"] == 1


def test_scout_is_not_started_without_reservation():
    result = solve(parameters={"source_count": 2, "limit": 1}, budget=Budget(max_evaluations=6))
    assert result.counters.iterations_completed == 0
    assert result.counters.partial_iteration.completed_items == 4
    assert result.counters.restarts == 0
    assert result.counters.algorithm_counters.get("scout_abandonments", 0) == 0


def test_success_on_last_reservation():
    graph = Graph(range(3), [(0, 1), (1, 2), (0, 2)])
    result = solve(graph, budget=Budget(max_evaluations=1))
    assert result.success_within_budget and validate_cycle(graph, result.best_route).valid
    assert result.counters.evaluations_started == result.counters.validations_completed == 1


@pytest.mark.parametrize("when, success", [(10, True), (11, False)])
def test_certification_deadline(when, success, monkeypatch):
    clock = Clock()
    real = execution.validate_cycle
    def delayed(graph, route):
        clock.now = when
        return real(graph, route)
    monkeypatch.setattr(execution, "validate_cycle", delayed)
    graph = Graph(range(3), [(0, 1), (1, 2), (0, 2)])
    result = solve(graph, clock=clock, budget=Budget(max_elapsed_ns=10, max_evaluations=1))
    assert result.validation.valid and result.success_within_budget is success
    assert result.stop_reason == ("validated_cycle" if success else "time_limit")


def test_discrepancy_and_time_before_certification(monkeypatch):
    monkeypatch.setattr(abc, "evaluate_cost", lambda graph, route: 0)
    assert solve().stop_reason == "fitness_validation_mismatch"
    clock = Clock()
    def delayed(graph, route):
        clock.now = 10
        return 0
    monkeypatch.setattr(abc, "evaluate_cost", delayed)
    result = solve(clock=clock, budget=Budget(max_elapsed_ns=10))
    assert result.stop_reason == "time_limit" and result.counters.validations_started == 0


def test_iteration_budget_and_reproducibility_without_global_rng():
    state = np.random.get_state()
    first = solve(budget=Budget(max_iterations=2))
    second = solve(budget=Budget(max_iterations=2))
    assert asdict(first) == asdict(second)
    assert first.counters.iterations_completed == 2 and first.counters.evaluations_completed == 10
    after = np.random.get_state()
    assert state[0] == after[0] and np.array_equal(state[1], after[1]) and state[2:] == after[2:]


@pytest.mark.parametrize("stop_at", [1, 3, 5, 7])
def test_time_limit_during_each_phase(stop_at, monkeypatch):
    clock = Clock()
    calls = 0
    def delayed(graph, route):
        nonlocal calls
        calls += 1
        if calls == stop_at:
            clock.now = 10
        return evaluate_cost(graph, route)
    monkeypatch.setattr(abc, "evaluate_cost", delayed)
    result = solve(parameters={"source_count": 2, "limit": 1}, clock=clock,
                   budget=Budget(max_elapsed_ns=10, max_evaluations=20))
    assert result.stop_reason == "time_limit"
    assert result.counters.evaluations_started == result.counters.evaluations_completed == stop_at
    assert result.counters.iterations_completed == 0


def test_proposal_success_on_last_reservation(example_graph, monkeypatch):
    monkeypatch.setattr(abc, "initialize_route", lambda n, rng: (0, 1, 3, 2, 4))
    monkeypatch.setattr(abc, "_guided_neighbor", lambda p, q, rng: (0, 1, 2, 3, 4))
    result = solve(example_graph, budget=Budget(max_evaluations=3))
    assert result.success_within_budget and result.best_cost == 0
    assert result.counters.partial_iteration.completed_items == 1
    assert result.counters.iterations_completed == 0
    assert result.counters.validations_completed == 1
