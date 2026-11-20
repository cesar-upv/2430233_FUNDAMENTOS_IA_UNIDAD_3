"""Controlled AS transitions, packed updates, budgets and independent certificates."""

from collections import Counter
from dataclasses import asdict
from itertools import combinations
import json
from types import SimpleNamespace

import numpy as np
import pytest

from src.algorithms import AS_VARIANT, ASConfigurationError, resolve_as_parameters, solve_as
from src.algorithms import ant_system as ants, execution
from src.algorithms.execution import Budget, PartialIteration
from src.evaluation import evaluate_cost, validate_cycle
from src.graphs import Graph, check_route_legality

PARAMETERS = {
    "ant_count": 3, "alpha": 1, "beta": 2, "rho": 0.5, "q": 1, "epsilon": 0.1,
    "initial_pheromone": 1, "pheromone_min": 0.01, "pheromone_max": 10,
}


class Clock:
    now = 0

    def __call__(self):
        return self.now


def unexpected(*args, **kwargs):
    pytest.fail("This work must not be admitted.")


@pytest.fixture
def empty_graph():
    return Graph(range(5), [])


def solve(graph, *, parameters=PARAMETERS, budget=Budget(max_evaluations=7), seed=51, clock=None):
    return solve_as(graph, parameters=parameters, seed=seed, budget=budget,
                    clock=Clock() if clock is None else clock)


class Admitted:
    """Unit-test work admission, independent of the already-tested SolverRun."""
    def __init__(self):
        self.counts = Counter()

    def checkpoint(self):
        return True

    def count(self, name):
        self.counts[name] += 1


def test_parameters_are_explicit_copied_and_normalized():
    supplied = dict(PARAMETERS)
    result = resolve_as_parameters(supplied)
    supplied["q"] = 99
    assert result == PARAMETERS
    assert type(result["ant_count"]) is int
    assert all(type(result[key]) is float for key in PARAMETERS if key != "ant_count")
    assert AS_VARIANT == "ant_system_missing_pairs_v1"
    assert resolve_as_parameters({**PARAMETERS, "ant_count": 1, "alpha": 0, "beta": 0})["ant_count"] == 1
    assert resolve_as_parameters({**PARAMETERS, "pheromone_min": 1, "pheromone_max": 1})["initial_pheromone"] == 1


INVALID = [
    (None, "invalid_parameters", None), ([], "invalid_parameters", None),
    ({1: 2}, "invalid_parameters", None),
    ({**PARAMETERS, "extra": 1}, "unknown_parameter", "extra"),
    *[({key: value for key, value in PARAMETERS.items() if key != missing}, "missing_parameter", missing)
      for missing in PARAMETERS],
    *[({**PARAMETERS, "ant_count": value}, "invalid_parameter", "ant_count")
      for value in (0, -1, True, "3", 3.0, None, np.int64(3))],
    *[({**PARAMETERS, key: value}, "invalid_parameter", key)
      for key in PARAMETERS if key != "ant_count"
      for value in (True, "1", None, float("nan"), float("inf"), np.float64(1), 2**10000)],
    *[({**PARAMETERS, key: value}, "invalid_parameter", key)
      for key, values in (("alpha", [-1]), ("beta", [-1]), ("rho", [0, 1, -0.1]),
                          ("q", [0, -1]), ("epsilon", [0, 1]), ("initial_pheromone", [0, -1, 11]),
                          ("pheromone_min", [0, -1]), ("pheromone_max", [0, -1]))
      for value in values],
    ({**PARAMETERS, "pheromone_min": 2}, "invalid_parameter", "initial_pheromone"),
    ({**PARAMETERS, "pheromone_min": 11}, "invalid_parameter", "pheromone_max"),
]


@pytest.mark.parametrize("parameters,code,field", INVALID)
def test_invalid_configuration_precedes_clock_and_rng(empty_graph, monkeypatch, parameters, code, field):
    with pytest.raises(ASConfigurationError) as error:
        resolve_as_parameters(parameters)
    assert (error.value.code, error.value.parameter) == (code, field)
    monkeypatch.setattr(ants, "start_run", unexpected)
    result = solve(empty_graph, parameters=parameters, clock=unexpected)
    assert (result.status, result.stop_reason, result.error.code) == ("error", "invalid_config", code)
    assert result.error.detail == {"parameter": field}
    assert result.counters.evaluations_started == result.counters.iterations_completed == 0
    assert result.best_route is result.best_cost is None and result.timing.solver_ns == 0


@pytest.mark.parametrize("options,code", [
    ({"seed": True}, "invalid_seed"), ({"budget": Budget()}, "invalid_budget"),
    ({"graph": Graph([0, 1], [])}, "graph_too_small"),
])
def test_common_validation_is_delegated(empty_graph, monkeypatch, options, code):
    monkeypatch.setattr(execution.np.random, "PCG64", unexpected)
    arguments = dict(graph=empty_graph, parameters=PARAMETERS, seed=51,
                     budget=Budget(max_evaluations=1), clock=unexpected)
    result = solve_as(**(arguments | options))
    assert result.status == "error" and result.error.code == code


@pytest.mark.parametrize("n", [3, 5, 8])
def test_packed_indices_match_an_independent_pair_enumeration(n):
    data = ants._allocate_pheromone(n)
    assert data.dtype == np.float64 and data.shape == (n * (n - 1) // 2,)
    assert data.nbytes == n * (n - 1) // 2 * 8
    for index, (u, v) in enumerate(combinations(range(n), 2)):
        assert ants._pair_index(n, u, v) == ants._pair_index(n, v, u) == index
        data[index] = index + 1
        assert data[ants._pair_index(n, v, u)] == index + 1
    for u in range(n):
        with pytest.raises(ValueError):
            ants._pair_index(n, u, u)
    with pytest.raises(ValueError):
        ants._pair_index(n, -1, 0)
    with pytest.raises(ValueError):
        ants._pair_index(n, 0, n)


def test_unrepresentable_allocation_is_rejected_before_numpy(monkeypatch):
    monkeypatch.setattr(ants.np, "empty", unexpected)
    with pytest.raises(MemoryError):
        ants._allocate_pheromone(2**40)


def test_allocation_failure_returns_a_diagnostic_without_evaluation(empty_graph, monkeypatch):
    def fail(n):
        raise MemoryError
    monkeypatch.setattr(ants, "_allocate_pheromone", fail)
    result = solve(empty_graph)
    assert (result.status, result.stop_reason, result.error.code) == ("error", "runtime_error", "allocation_failed")
    assert result.error.phase == "initialization" and result.error.detail["pheromone_bytes"] == 80
    assert result.counters.evaluations_started == 0 and result.best_route is None


@pytest.mark.parametrize("alpha,beta,tau,epsilon,expected", [
    (1, 0, [2, 1, 1], 0.1, [2 / 3, 1 / 3]),
    (1, 1, [1, 1, 1], 0.25, [0.8, 0.2]),
    (2, 2, [2, 1, 1], 0.5, [16 / 17, 1 / 17]),
    (0, 0, [2, 9, 1], 0.1, [0.5, 0.5]),
    (4, 0, [1e-250] * 3, 0.1, [0.5, 0.5]),
    (4, 0, [1e250] * 3, 0.1, [0.5, 0.5]),
])
def test_transition_probabilities_without_frequency_estimation(alpha, beta, tau, epsilon, expected):
    graph = Graph(range(3), [(0, 1)])
    parameters = resolve_as_parameters({**PARAMETERS, "alpha": alpha, "beta": beta, "epsilon": epsilon})
    with np.errstate(over="raise", under="raise", invalid="raise"):
        probabilities = ants._probabilities(graph, np.array(tau), 0, np.array([1, 2]), parameters, Admitted())
        assert np.geterr()["under"] == "raise"
    np.testing.assert_allclose(probabilities, expected)


@pytest.mark.parametrize("tau", [0, -1, float("nan"), float("inf")])
def test_invalid_pheromone_is_rejected_before_sampling(tau):
    with pytest.raises(FloatingPointError):
        ants._probabilities(Graph(range(3), []), np.array([tau, 1.0, 1.0]), 0,
                            np.array([1, 2]), resolve_as_parameters(PARAMETERS), Admitted())


def test_degenerate_weights_are_not_repaired_uniformly(monkeypatch):
    with pytest.raises(ants._TransitionError):
        ants._normalize_log_weights(np.array([]))
    monkeypatch.setattr(ants.np, "exp", lambda scores: np.zeros(len(scores)))
    with pytest.raises(ants._TransitionError):
        ants._normalize_log_weights(np.array([0.0, 0.0]))


def test_numeric_overflow_stops_before_cost_and_degenerate_distribution_is_reported(empty_graph, monkeypatch):
    monkeypatch.setattr(ants, "evaluate_cost", unexpected)
    result = solve(empty_graph, parameters={**PARAMETERS, "alpha": float(np.finfo(np.float64).max),
                                           "initial_pheromone": 10})
    assert result.stop_reason == "non_finite_state" and result.counters.evaluations_started == 0
    def fail(scores):
        raise ants._TransitionError
    monkeypatch.setattr(ants, "_normalize_log_weights", fail)
    result = solve(empty_graph)
    assert result.error.code == "invalid_transition_weights" and result.stop_reason == "runtime_error"


def test_vertex_order_missing_pairs_and_rng_consumption(empty_graph, monkeypatch):
    events = []
    start = ants.start_run
    def begin(*args, **kwargs):
        run = start(*args, **kwargs)
        def first(n):
            events.append(("start", n))
            return 2
        def choice(candidates, *, p):
            events.append((tuple(candidates), tuple(p)))
            return candidates[-1]
        run.rng = SimpleNamespace(integers=first, choice=choice)
        return run
    monkeypatch.setattr(ants, "start_run", begin)
    result = solve(empty_graph, budget=Budget(max_evaluations=1))
    assert result.best_route == (2, 4, 3, 1, 0)
    assert [event[0] for event in events[1:]] == [(0, 1, 3, 4), (0, 1, 3), (0, 1), (0,)]
    assert events[0] == ("start", 5)
    assert result.counters.algorithm_counters == {"constructions_started": 1, "construction_steps": 4}


def test_evaporation_and_deposits_match_a_pair_dictionary_including_closure():
    n = 4
    pheromone = np.full(6, 2.0)
    tours = [((0, 1, 2, 3), 1), ((3, 2, 1, 0), 1)]
    parameters = resolve_as_parameters({**PARAMETERS, "initial_pheromone": 2, "rho": 0.25, "q": 2})
    expected = dict.fromkeys(combinations(range(n), 2), 1.5)
    for route, cost in tours:
        for u, v in zip(route, (*route[1:], route[0])):
            expected[min(u, v), max(u, v)] += 2 / (1 + cost)
    run = Admitted()
    assert ants._update_pheromone(n, pheromone, tours, parameters, run)
    for (u, v), value in expected.items():
        assert pheromone[ants._pair_index(n, u, v)] == value
    assert pheromone[ants._pair_index(n, 0, 3)] == 3.5  # Closure is reinforced.
    assert run.counts == {"pheromone_updates_started": 1, "pheromone_updates_completed": 1, "pheromone_deposits": 8}


def test_lower_bound_is_applied_after_deposits_and_upper_bound_cannot_overflow():
    pheromone = np.full(3, 0.1)
    parameters = resolve_as_parameters({**PARAMETERS, "initial_pheromone": 0.1,
                                       "pheromone_min": 0.1, "q": 0.02})
    assert ants._update_pheromone(3, pheromone, [((0, 1, 2), 1)], parameters, Admitted())
    np.testing.assert_array_equal(pheromone, [0.1] * 3)  # Not 0.11 from premature clipping.
    maximum = float(np.finfo(np.float64).max)
    pheromone.fill(maximum)
    parameters = resolve_as_parameters({**PARAMETERS, "initial_pheromone": maximum,
                                       "pheromone_max": maximum, "q": maximum, "rho": 0.01})
    with np.errstate(over="raise", invalid="raise"):
        assert ants._update_pheromone(3, pheromone, [((0, 1, 2), 1)] * 2, parameters, Admitted())
    np.testing.assert_array_equal(pheromone, [maximum] * 3)


@pytest.mark.parametrize("limit,iterations,items,updates", [(1, 0, 1, 0), (3, 0, 3, 0),
                                                          (4, 1, 1, 1), (6, 1, 3, 1), (7, 2, 1, 2)])
def test_evaluation_admission_blocks_even_a_complete_round_update(empty_graph, monkeypatch, limit, iterations, items, updates):
    evaluated = []
    def cost(graph, route):
        evaluated.append(route)
        assert check_route_legality(5, route).valid
        return evaluate_cost(graph, route)
    monkeypatch.setattr(ants, "evaluate_cost", cost)
    result = solve(empty_graph, budget=Budget(max_evaluations=limit))
    assert result.stop_reason == "evaluation_limit" and len(evaluated) == limit
    assert result.counters.evaluations_started == result.counters.evaluations_completed == limit
    assert result.counters.iterations_completed == iterations
    assert result.counters.partial_iteration == PartialIteration("round", items, 4)
    assert result.counters.algorithm_counters.get("pheromone_updates_started", 0) == updates
    assert result.counters.algorithm_counters.get("pheromone_updates_completed", 0) == updates
    assert result.counters.algorithm_counters.get("pheromone_deposits", 0) == updates * 3 * 5
    assert result.counters.algorithm_counters["constructions_started"] == limit
    assert result.best_route == evaluated[0] and result.best_cost == 5


@pytest.mark.parametrize("ant_count", [1, 3])
def test_iteration_budget_counts_only_rounds_after_pheromone_update(empty_graph, ant_count):
    result = solve(empty_graph, parameters={**PARAMETERS, "ant_count": ant_count}, budget=Budget(max_iterations=2))
    assert result.stop_reason == "iteration_limit" and result.counters.iterations_completed == 2
    assert result.counters.evaluations_completed == 2 * ant_count
    assert result.counters.partial_iteration is None


def test_all_ants_in_a_round_use_frozen_pheromone(empty_graph, monkeypatch):
    snapshots = []
    construct = ants._construct
    def capture(graph, pheromone, parameters, run):
        snapshots.append(pheromone.copy())
        return construct(graph, pheromone, parameters, run)
    monkeypatch.setattr(ants, "_construct", capture)
    result = solve(empty_graph, budget=Budget(max_iterations=2))
    assert result.counters.evaluations_completed == 6
    for offset in (0, 3):
        for index in range(offset, offset + 3):
            np.testing.assert_array_equal(snapshots[index], snapshots[offset])
    assert np.any(snapshots[0] != snapshots[3])


def test_timeout_before_allocation_and_between_initialization_blocks(empty_graph, monkeypatch):
    clock = Clock()
    original_blocks = ants._blocks
    monkeypatch.setattr(ants, "_PHEROMONE_BLOCK", 2)
    def interrupted(length):
        for index, block in enumerate(original_blocks(length)):
            if index == 1:
                clock.now = 10
            yield block
    monkeypatch.setattr(ants, "_blocks", interrupted)
    result = solve(empty_graph, budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.stop_reason == "time_limit" and result.best_route is None
    assert result.counters.evaluations_started == 0
    assert result.counters.partial_iteration == PartialIteration("initialization", 1, 5)
    monkeypatch.setattr(ants, "_allocate_pheromone", unexpected)
    ticks = iter([0, 10])
    result = solve(empty_graph, budget=Budget(max_elapsed_ns=10), clock=lambda: next(ticks))
    assert result.stop_reason == "time_limit" and result.counters.partial_iteration is None


def test_interrupted_prefix_has_no_evaluation_or_deposit(empty_graph, monkeypatch):
    clock = Clock()
    start = ants.start_run
    calls = []
    def begin(*args, **kwargs):
        run = start(*args, **kwargs)
        def choice(candidates, *, p):
            calls.append(tuple(candidates))
            clock.now = 10
            return candidates[0]
        run.rng = SimpleNamespace(integers=lambda n: 0, choice=choice)
        return run
    monkeypatch.setattr(ants, "start_run", begin)
    monkeypatch.setattr(ants, "evaluate_cost", unexpected)
    result = solve(empty_graph, budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.best_route is result.best_cost is None
    assert result.counters.evaluations_started == 0 and len(calls) == 1
    assert result.counters.partial_iteration == PartialIteration("round", 0, 4)
    assert result.counters.algorithm_counters == {"constructions_started": 1, "construction_steps": 1}


def test_time_is_checked_inside_candidate_preparation(monkeypatch):
    clock = Clock()
    calls = 0
    def has_edge(graph, u, v):
        nonlocal calls
        calls += 1
        if calls == 256:
            clock.now = 10
        return False
    monkeypatch.setattr(Graph, "has_edge", has_edge)
    result = solve(Graph(range(260), []), budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.stop_reason == "time_limit" and calls == 256
    assert result.counters.evaluations_started == 0
    assert result.counters.algorithm_counters == {"constructions_started": 1}


def test_timeout_during_second_ant_preserves_only_the_first_evaluated_tour(empty_graph, monkeypatch):
    clock = Clock()
    probability = ants._probabilities
    calls = 0
    def interrupt(*args):
        nonlocal calls
        calls += 1
        result = probability(*args)
        if calls == 5:  # Four moves completed the first tour; the second is only a prefix.
            clock.now = 10
        return result
    monkeypatch.setattr(ants, "_probabilities", interrupt)
    result = solve(empty_graph, budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.stop_reason == "time_limit" and result.best_cost == 5
    assert check_route_legality(5, result.best_route).valid
    assert result.counters.evaluations_started == result.counters.evaluations_completed == 1
    assert result.counters.partial_iteration == PartialIteration("round", 1, 4)
    assert result.counters.algorithm_counters == {"constructions_started": 2, "construction_steps": 4}


def test_deadline_after_last_cost_blocks_update_admission(empty_graph, monkeypatch):
    clock = Clock()
    costs = 0
    def evaluate(graph, route):
        nonlocal costs
        costs += 1
        if costs == 3:
            clock.now = 10
        return evaluate_cost(graph, route)
    monkeypatch.setattr(ants, "evaluate_cost", evaluate)
    result = solve(empty_graph, budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.stop_reason == "time_limit" and result.counters.evaluations_completed == 3
    assert result.counters.partial_iteration == PartialIteration("round", 3, 4)
    assert "pheromone_updates_started" not in result.counters.algorithm_counters
    assert result.counters.iterations_completed == 0


@pytest.mark.parametrize("stage", ["evaporation", "deposit", "bounds"])
def test_interrupted_update_never_completes_round(empty_graph, monkeypatch, stage):
    clock = Clock()
    multiply, deposit, clip = ants.np.multiply, ants._deposit_value, ants.np.clip
    def evaporate(*args, **kwargs):
        value = multiply(*args, **kwargs)
        if stage == "evaporation":
            clock.now = 10
        return value
    def add(*args):
        value = deposit(*args)
        if stage == "deposit":
            clock.now = 10
        return value
    def bound(*args, **kwargs):
        value = clip(*args, **kwargs)
        if stage == "bounds":
            clock.now = 10
        return value
    monkeypatch.setattr(ants.np, "multiply", evaporate)
    monkeypatch.setattr(ants, "_deposit_value", add)
    monkeypatch.setattr(ants.np, "clip", bound)
    result = solve(empty_graph, budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.stop_reason == "time_limit" and result.counters.evaluations_completed == 3
    assert result.counters.iterations_completed == 0
    assert result.counters.partial_iteration == PartialIteration("round", 3, 4)
    counts = result.counters.algorithm_counters
    assert counts["pheromone_updates_started"] == 1 and "pheromone_updates_completed" not in counts
    assert counts.get("pheromone_deposits", 0) == {"evaporation": 0, "deposit": 1, "bounds": 15}[stage]


@pytest.mark.parametrize("finish,status", [(9, "success"), (10, "success"), (11, "exhausted")])
def test_last_reservation_certification_at_or_after_deadline(monkeypatch, finish, status):
    triangle = Graph(range(3), [(0, 1), (1, 2), (2, 0)])
    clock = Clock()
    def certify(graph, route):
        result = validate_cycle(graph, route)
        clock.now = finish
        return result
    monkeypatch.setattr(execution, "validate_cycle", certify)
    result = solve(triangle, budget=Budget(max_elapsed_ns=10, max_evaluations=1), clock=clock)
    assert result.status == status and result.validation.valid is True
    assert result.success_within_budget == (status == "success")
    assert result.counters.evaluations_started == result.counters.validations_completed == 1
    assert result.counters.partial_iteration == PartialIteration("round", 1, 4)
    assert result.timing.overrun_ns == max(0, finish - 10)
    assert (result.timing.first_success is not None) == (status == "success")


def test_cost_zero_at_deadline_does_not_start_validation(monkeypatch):
    triangle = Graph(range(3), [(0, 1), (1, 2), (2, 0)])
    clock = Clock()
    def cost(graph, route):
        clock.now = 10
        return evaluate_cost(graph, route)
    monkeypatch.setattr(ants, "evaluate_cost", cost)
    monkeypatch.setattr(execution, "validate_cycle", unexpected)
    result = solve(triangle, budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.stop_reason == "time_limit" and result.best_cost == 0
    assert result.validation.reason == "not_run" and result.counters.validations_started == 0


def test_fitness_discrepancy_is_not_success(empty_graph, monkeypatch):
    monkeypatch.setattr(ants, "evaluate_cost", lambda graph, route: 0)
    result = solve(empty_graph, budget=Budget(max_evaluations=1))
    assert result.stop_reason == "fitness_validation_mismatch" and result.validation.valid is False
    assert result.timing.first_success is None


@pytest.mark.parametrize("error,code", [(MemoryError, "allocation_failed"), (RuntimeError, "RuntimeError")])
def test_update_failure_preserves_best_without_counting_round(empty_graph, monkeypatch, error, code):
    def fail(*args):
        raise error("Do not disclose callback details.")
    monkeypatch.setattr(ants, "_deposit_value", fail)
    result = solve(empty_graph, budget=Budget(max_iterations=1))
    assert result.status == "error" and result.error.code == code
    assert result.best_cost == 5 and result.counters.evaluations_completed == 3
    assert result.counters.iterations_completed == 0
    assert "callback details" not in json.dumps(asdict(result))


def test_real_solver_constructs_and_certifies_a_synthetic_cycle():
    graph = Graph(range(5), [(i, (i + 1) % 5) for i in range(5)])
    result = solve(graph, budget=Budget(max_evaluations=100))
    assert result.status == "success" and result.success_within_budget
    assert result.best_cost == 0 and validate_cycle(graph, result.best_route).valid


def test_reproduction_trajectory_and_isolation_of_rng_and_configuration(empty_graph, monkeypatch):
    traces, results, generators = [], [], []
    state = np.random.get_state()
    cost_function, construct = ants.evaluate_cost, ants._construct
    supplied = dict(PARAMETERS)
    def cost(graph, route):
        traces[-1].append(route)
        return cost_function(graph, route)
    def build(graph, pheromone, parameters, run):
        assert isinstance(run.rng.bit_generator, np.random.PCG64)
        if len(traces[-1]) == 0:
            generators.append(run.rng)
        supplied["ant_count"] = 99
        return construct(graph, pheromone, parameters, run)
    monkeypatch.setattr(ants, "evaluate_cost", cost)
    monkeypatch.setattr(ants, "_construct", build)
    for seed in (51, 52, 51):
        supplied.update(PARAMETERS)
        traces.append([])
        record = asdict(solve(empty_graph, parameters=supplied, seed=seed, budget=Budget(max_evaluations=10)))
        record.pop("timing")
        results.append(record)
    assert traces[0] == traces[2] and traces[0] != traces[1]
    assert results[0] == results[2]
    assert results[0]["counters"]["iterations_completed"] == 3
    assert len(traces[0]) == 10 and len({id(rng) for rng in generators}) == 3
    after = np.random.get_state()
    assert state[0] == after[0] and state[2:] == after[2:]
    np.testing.assert_array_equal(state[1], after[1])
