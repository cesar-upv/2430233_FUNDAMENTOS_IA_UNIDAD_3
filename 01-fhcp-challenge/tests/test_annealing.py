"""SA mechanism, numerical boundaries and integration with the #19 runtime."""

from dataclasses import asdict
import json
from math import exp
import random
from types import SimpleNamespace

import numpy as np
import pytest

from src.algorithms import SA_VARIANT, SAConfigurationError, resolve_sa_parameters, solve_sa
from src.algorithms import annealing, execution
from src.algorithms.execution import Budget, PartialIteration
from src.evaluation import evaluate_cost, validate_cycle
from src.graphs import Graph, GraphError, check_route_legality

PARAMETERS = {
    "initial_temperature": 2, "cooling_factor": 0.5,
    "minimum_temperature": 0, "moves_per_temperature": 100,
}
CYCLE = (0, 1, 2, 3, 4)
OTHER = (0, 1, 3, 2, 4)


class Clock:
    now = 0

    def __call__(self):
        return self.now


def unexpected(*args, **kwargs):
    pytest.fail("This operation must not be admitted.")


@pytest.fixture
def empty_graph():
    return Graph(range(5), [])


def solve(graph, *, parameters=None, budget=None, seed=50, clock=None):
    return solve_sa(
        graph, parameters=PARAMETERS if parameters is None else parameters, seed=seed,
        budget=Budget(max_evaluations=10) if budget is None else budget,
        clock=Clock() if clock is None else clock,
    )


def test_effective_parameters_are_copied_and_normalized():
    parameters = dict(PARAMETERS)
    effective = resolve_sa_parameters(parameters)
    assert effective == PARAMETERS
    assert effective is not parameters
    for name in ("initial_temperature", "cooling_factor", "minimum_temperature"):
        assert type(effective[name]) is float
    assert type(effective["moves_per_temperature"]) is int
    parameters["moves_per_temperature"] = 1
    assert effective["moves_per_temperature"] == 100
    assert SA_VARIANT == "geometric_swap_v1"


INVALID_PARAMETERS = [
    (None, "invalid_parameters", None),
    ([], "invalid_parameters", None),
    ({1: 2}, "invalid_parameters", None),
    ({**PARAMETERS, "unknown": 1}, "unknown_parameter", "unknown"),
    *[({k: v for k, v in PARAMETERS.items() if k != name}, "missing_parameter", name)
      for name in PARAMETERS],
    *[({**PARAMETERS, name: value}, "invalid_parameter", name)
      for name in ("initial_temperature", "cooling_factor", "minimum_temperature")
      for value in (True, "1", None, float("nan"), float("inf"), -float("inf"), np.float64(0.5), np.int64(1), 2**10000)],
    *[({**PARAMETERS, "initial_temperature": value}, "invalid_parameter", "initial_temperature")
      for value in (0, -1)],
    *[({**PARAMETERS, "cooling_factor": value}, "invalid_parameter", "cooling_factor")
      for value in (0, 1, -0.1, 1.1)],
    *[({**PARAMETERS, "minimum_temperature": value}, "invalid_parameter", "minimum_temperature")
      for value in (-1, 2, 3)],
    *[({**PARAMETERS, "moves_per_temperature": value}, "invalid_parameter", "moves_per_temperature")
      for value in (0, -1, True, 1.0, "1", None, np.int64(1))],
]


@pytest.mark.parametrize("parameters,code,field", INVALID_PARAMETERS)
def test_configuration_rejected_before_clock_or_rng(empty_graph, monkeypatch, parameters, code, field):
    with pytest.raises(SAConfigurationError) as error:
        resolve_sa_parameters(parameters)
    assert (error.value.code, error.value.parameter) == (code, field)
    monkeypatch.setattr(annealing, "start_run", unexpected)
    result = solve_sa(empty_graph, parameters=parameters, seed=50,
                      budget=Budget(max_evaluations=10), clock=unexpected)
    assert (result.status, result.stop_reason) == ("error", "invalid_config")
    assert result.error.code == code and result.error.phase == "input"
    assert result.error.detail == {"parameter": field}
    assert result.counters.evaluations_started == result.counters.iterations_completed == 0
    assert result.best_route is result.best_cost is None
    assert result.timing.solver_ns == 0


@pytest.mark.parametrize("options,reason,code", [
    ({"seed": True}, "invalid_config", "invalid_seed"),
    ({"budget": Budget()}, "invalid_config", "invalid_budget"),
    ({"budget": Budget(max_evaluations=0)}, "invalid_config", "invalid_budget"),
    ({"graph": Graph([1, 2], [])}, "invalid_input", "graph_too_small"),
    ({"graph": None}, "invalid_input", "invalid_graph"),
])
def test_common_validation_precedes_clock_and_rng(empty_graph, monkeypatch, options, reason, code):
    monkeypatch.setattr(execution.np.random, "PCG64", unexpected)
    arguments = {"graph": empty_graph, "parameters": PARAMETERS, "seed": 50,
                 "budget": Budget(max_evaluations=1), "clock": unexpected, **options}
    result = solve_sa(**arguments)
    assert (result.stop_reason, result.error.code) == (reason, code)
    assert result.counters.evaluations_started == 0


@pytest.mark.parametrize("delta,temperature", [(-1, 2), (0, 2), (-1, 0), (0, 0), (1, 0)])
def test_improvements_ties_and_zero_temperature_need_no_rng(delta, temperature):
    assert annealing._accept_move(delta, temperature, SimpleNamespace(random=unexpected)) == (delta <= 0)


@pytest.mark.parametrize("delta,temperature,uniform,expected", [
    (2, 4, 0.6, True), (2, 4, 0.61, False),
    (2, 0.5, 0.01, True), (2, 0.5, 0.02, False),
    (1, 1, exp(-1), False),  # Equality is rejected by the strict comparison.
    (1, 1, 0, True),
    (1, 0.001, 0, True), (1, 0.001, 5e-324, False),
    (1, 5e-324, 0, True), (1, 5e-324, 5e-324, False),
    (1, 1e308, 0.9999999999999999, True),
])
def test_stable_thermal_acceptance(delta, temperature, uniform, expected):
    draws = []

    def draw():
        draws.append(uniform)
        return uniform

    assert annealing._accept_move(delta, temperature, SimpleNamespace(random=draw)) is expected
    assert draws == [uniform]


def test_controlled_moves_cooling_current_state_and_first_best(empty_graph, monkeypatch):
    routes = [tuple(np.roll(CYCLE, i)) for i in range(5)] + [OTHER]
    proposals = iter(routes[1:])
    costs = iter([4, 2, 3, 4, 3, 2])
    uniforms = iter([0.5, 0.5])
    evaluated, parents, decisions = [], [], []
    start, accept = annealing.start_run, annealing._accept_move

    def begin(*args, **kwargs):
        run = start(*args, **kwargs)
        run.rng = SimpleNamespace(random=lambda: next(uniforms))
        return run

    def mutate(route, **kwargs):
        parents.append(route)
        return next(proposals)

    def cost(graph, route):
        evaluated.append(route)
        return next(costs)

    def decide(delta, temperature, rng):
        decisions.append((delta, temperature))
        return accept(delta, temperature, rng)

    monkeypatch.setattr(annealing, "start_run", begin)
    monkeypatch.setattr(annealing, "initialize_route", lambda n, rng: routes[0])
    monkeypatch.setattr(annealing, "swap_mutation", mutate)
    monkeypatch.setattr(annealing, "evaluate_cost", cost)
    monkeypatch.setattr(annealing, "_accept_move", decide)
    result = solve(empty_graph, parameters={**PARAMETERS, "moves_per_temperature": 2},
                   budget=Budget(max_iterations=5))
    assert parents == [routes[0], routes[1], routes[2], routes[2], routes[4]]
    assert evaluated == routes  # Exactly one evaluation per proposal, no reevaluation.
    assert decisions == [(-2, 2), (1, 2), (1, 1), (0, 1), (-1, 0.5)]
    assert list(uniforms) == []
    assert result.best_route == routes[1] and result.best_cost == 2
    assert result.counters.iterations_completed == 5
    assert result.counters.algorithm_counters == {"accepted_moves": 4, "rejected_moves": 1, "cooling_steps": 2}
    assert result.counters.partial_iteration is None


@pytest.mark.parametrize("initial,cooling,minimum,moves,iterations,steps,stall", [
    (2, 0.5, 0.5, 3, 6, 2, False),  # No proposals at T == minimum.
    (5e-324, 0.25, 0, 1, 1, 1, False),  # Rounded cooling reaches zero.
    (5e-324, 0.75, 0, 2, 2, 1, True),  # Rounded cooling cannot decrease T.
])
def test_natural_stops_include_zero_and_rounded_stagnation(empty_graph, initial, cooling, minimum, moves, iterations, steps, stall):
    parameters = {"initial_temperature": initial, "cooling_factor": cooling,
                  "minimum_temperature": minimum, "moves_per_temperature": moves}
    result = solve(empty_graph, parameters=parameters, budget=Budget(max_evaluations=100))
    assert (result.status, result.stop_reason) == ("exhausted", "algorithm_stop")
    assert result.counters.iterations_completed == iterations
    assert result.counters.evaluations_completed == 1 + iterations
    assert result.counters.algorithm_counters["cooling_steps"] == steps
    assert result.counters.algorithm_counters.get("cooling_stalls", 0) == int(stall)
    assert result.counters.partial_iteration is None


@pytest.mark.parametrize("limit", [1, 2, 3, 10])
def test_last_evaluation_allows_acceptance_and_counts_complete_moves(empty_graph, limit):
    result = solve(empty_graph, budget=Budget(max_evaluations=limit))
    assert (result.status, result.stop_reason) == ("exhausted", "evaluation_limit")
    assert result.counters.iterations_completed == limit - 1
    assert result.counters.evaluations_started == result.counters.evaluations_completed == limit
    assert result.counters.full_evaluations == limit
    assert result.counters.partial_iteration is None
    assert result.counters.cache_hits == result.counters.incremental_evaluations == result.counters.restarts == 0
    assert result.validation.reason == "not_run"


@pytest.mark.parametrize("uniform,accepted", [(0, True), (0.99, False)])
def test_thermal_decision_finishes_at_simultaneous_work_limits(empty_graph, monkeypatch, uniform, accepted):
    start = annealing.start_run
    costs = iter([2, 3])

    def begin(*args, **kwargs):
        run = start(*args, **kwargs)
        run.rng = SimpleNamespace(random=lambda: uniform)
        return run

    monkeypatch.setattr(annealing, "start_run", begin)
    monkeypatch.setattr(annealing, "initialize_route", lambda n, rng: CYCLE)
    monkeypatch.setattr(annealing, "swap_mutation", lambda route, **kwargs: OTHER)
    monkeypatch.setattr(annealing, "evaluate_cost", lambda graph, route: next(costs))
    result = solve(empty_graph, budget=Budget(max_evaluations=2, max_iterations=1))
    assert result.stop_reason == "evaluation_limit"
    assert result.limits_reached == ("evaluation_limit", "iteration_limit")
    assert result.counters.evaluations_completed == 2 and result.counters.iterations_completed == 1
    assert result.counters.partial_iteration is None
    assert result.counters.algorithm_counters == {"accepted_moves" if accepted else "rejected_moves": 1}
    assert result.best_route == CYCLE and result.best_cost == 2


def test_configuration_snapshot_survives_caller_mutation(empty_graph, monkeypatch):
    parameters = dict(PARAMETERS)
    initialize = annealing.initialize_route

    def initialize_and_modify(n, rng):
        parameters.update(minimum_temperature=100, cooling_factor=float("nan"), moves_per_temperature=0)
        return initialize(n, rng)

    monkeypatch.setattr(annealing, "initialize_route", initialize_and_modify)
    result = solve(empty_graph, parameters=parameters, budget=Budget(max_iterations=3))
    assert result.stop_reason == "iteration_limit"
    assert result.counters.iterations_completed == 3 and result.counters.evaluations_completed == 4


def test_initialization_success_on_minimum_graph_and_last_reservation():
    triangle = Graph([1, 2, 3], [(1, 2), (2, 3), (3, 1)])
    result = solve(triangle, budget=Budget(max_evaluations=1))
    assert result.status == "success" and result.success_within_budget
    assert result.best_cost == 0 and validate_cycle(triangle, result.best_route).valid
    assert result.counters.validations_completed == 1
    assert result.counters.iterations_completed == 0
    assert result.counters.partial_iteration == PartialIteration("initialization", 1, 1)
    assert result.limits_reached == ("evaluation_limit",)
    assert result.timing.first_success.evaluations_completed == 1
    json.dumps(asdict(result), allow_nan=False)


def test_zero_cost_neighbor_is_certified_immediately_on_last_reservation(example_graph, monkeypatch):
    monkeypatch.setattr(annealing, "initialize_route", lambda n, rng: OTHER)
    monkeypatch.setattr(annealing, "swap_mutation", lambda route, **kwargs: CYCLE)
    monkeypatch.setattr(annealing, "_accept_move", unexpected)
    result = solve(example_graph, budget=Budget(max_evaluations=2))
    assert result.status == "success" and result.best_route == CYCLE
    assert result.best_cost == 0 and validate_cycle(example_graph, result.best_route).valid
    assert result.counters.evaluations_completed == 2
    assert result.counters.validations_completed == 1
    assert result.counters.iterations_completed == 0
    assert result.counters.partial_iteration == PartialIteration("move", 1, 1)


def test_real_swaps_find_and_certify_synthetic_cycle():
    graph = Graph(range(5), [(i, (i + 1) % 5) for i in range(5)])
    result = solve(graph, budget=Budget(max_evaluations=500))
    assert result.status == "success" and result.best_cost == 0
    assert validate_cycle(graph, result.best_route).valid
    assert 1 < result.counters.evaluations_completed <= 500
    assert result.counters.iterations_completed == result.counters.evaluations_completed - 2


def test_timeout_before_initialization(empty_graph, monkeypatch):
    ticks = iter([0, 10])
    monkeypatch.setattr(annealing, "initialize_route", unexpected)
    result = solve(empty_graph, budget=Budget(max_elapsed_ns=10), clock=lambda: next(ticks))
    assert result.stop_reason == "time_limit"
    assert result.best_route is result.best_cost is None
    assert result.counters.evaluations_started == 0 and result.counters.partial_iteration is None


def test_interrupted_evaluation_retains_reservation_and_previous_best(empty_graph, monkeypatch):
    clock = Clock()
    evaluated = []

    def cost(graph, route):
        evaluated.append(route)
        if len(evaluated) == 2:
            clock.now = 10
            return None
        return evaluate_cost(graph, route)

    monkeypatch.setattr(annealing, "evaluate_cost", cost)
    result = solve(empty_graph, budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.stop_reason == "time_limit"
    assert result.counters.evaluations_started == 2 and result.counters.evaluations_completed == 1
    assert result.counters.iterations_completed == 0
    assert result.counters.partial_iteration == PartialIteration("move", 0, 1)
    assert result.best_route == evaluated[0] and result.best_cost == 5


@pytest.mark.parametrize("stage,evaluations,completed,phase,items", [
    ("initialize", 0, 0, "initialization", 0),
    ("initial_cost", 1, 0, "initialization", 1),
    ("swap", 1, 0, "move", 0),
    ("neighbor_cost", 2, 0, "move", 1),
    ("decision", 2, 0, "move", 1),
    ("later_cost", 3, 1, "move", 1),
])
def test_timeouts_preserve_evaluated_best_and_partial_work(empty_graph, monkeypatch, stage, evaluations, completed, phase, items):
    clock = Clock()
    initialize, swap, accept = annealing.initialize_route, annealing.swap_mutation, annealing._accept_move
    evaluated, initial = [], []

    def initial_route(n, rng):
        route = initialize(n, rng)
        initial.append(route)
        if stage == "initialize":
            clock.now = 10
        return route

    def neighbor(route, **kwargs):
        child = swap(route, **kwargs)
        if stage == "swap":
            clock.now = 10
        return child

    def cost(graph, route):
        evaluated.append(route)
        if ((stage == "initial_cost" and len(evaluated) == 1)
                or (stage == "neighbor_cost" and len(evaluated) == 2)
                or (stage == "later_cost" and len(evaluated) == 3)):
            clock.now = 10
        return evaluate_cost(graph, route)

    def decision(*args):
        accepted = accept(*args)
        if stage == "decision":
            clock.now = 10
        return accepted

    monkeypatch.setattr(annealing, "initialize_route", initial_route)
    monkeypatch.setattr(annealing, "swap_mutation", neighbor)
    monkeypatch.setattr(annealing, "evaluate_cost", cost)
    monkeypatch.setattr(annealing, "_accept_move", decision)
    result = solve(empty_graph, budget=Budget(max_elapsed_ns=10, max_evaluations=10), clock=clock)
    assert result.stop_reason == "time_limit"
    assert result.counters.evaluations_started == result.counters.evaluations_completed == evaluations
    assert result.counters.iterations_completed == completed
    assert result.counters.partial_iteration == PartialIteration(phase, items, 1)
    assert result.best_route == (initial[0] if evaluations else None)
    assert result.best_cost == (5 if evaluations else None)


@pytest.mark.parametrize("finish,status", [(9, "success"), (10, "success"), (11, "exhausted")])
def test_certification_time_boundaries_on_neighbor_last_reservation(example_graph, monkeypatch, finish, status):
    clock = Clock()
    monkeypatch.setattr(annealing, "initialize_route", lambda n, rng: OTHER)
    monkeypatch.setattr(annealing, "swap_mutation", lambda route, **kwargs: CYCLE)

    def cost(graph, route):
        if route == CYCLE:
            clock.now = 5
        return evaluate_cost(graph, route)

    def certify(graph, route):
        certificate = validate_cycle(graph, route)
        clock.now = finish
        return certificate

    monkeypatch.setattr(annealing, "evaluate_cost", cost)
    monkeypatch.setattr(execution, "validate_cycle", certify)
    result = solve(example_graph, budget=Budget(max_elapsed_ns=10, max_evaluations=2), clock=clock)
    assert result.status == status and result.validation.valid is True
    assert result.success_within_budget == (status == "success")
    assert (result.timing.first_success is not None) == (status == "success")
    assert result.timing.validation_ns == finish - 5
    assert result.timing.overrun_ns == max(0, finish - 10)
    assert result.counters.evaluations_started == 2 and result.counters.validations_completed == 1


def test_zero_cost_with_no_time_to_start_certificate(example_graph, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(annealing, "initialize_route", lambda n, rng: CYCLE)

    def cost(graph, route):
        clock.now = 10
        return evaluate_cost(graph, route)

    monkeypatch.setattr(annealing, "evaluate_cost", cost)
    monkeypatch.setattr(execution, "validate_cycle", unexpected)
    result = solve(example_graph, budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.status == "exhausted" and result.best_cost == 0
    assert result.validation.reason == "not_run" and result.counters.validations_started == 0


def test_fitness_mismatch_is_error_even_on_last_reservation(empty_graph, monkeypatch):
    monkeypatch.setattr(annealing, "evaluate_cost", lambda graph, route: 0)
    result = solve(empty_graph, budget=Budget(max_evaluations=1))
    assert (result.status, result.stop_reason) == ("error", "fitness_validation_mismatch")
    assert result.validation.valid is False and result.timing.first_success is None


@pytest.mark.parametrize("source", ["candidate", "operator", "cost", "decision"])
def test_errors_keep_best_without_fabricating_completed_moves(empty_graph, monkeypatch, source):
    initial = []
    initialize = annealing.initialize_route

    def initial_route(n, rng):
        route = list(initialize(n, rng))
        initial.append(route)
        return route

    def broken(*args, **kwargs):
        raise ArithmeticError("Private callback data must not be exposed.")

    monkeypatch.setattr(annealing, "initialize_route", initial_route)
    if source == "candidate":
        monkeypatch.setattr(annealing, "swap_mutation", lambda *args, **kwargs: (0, 1, 2, 3, 3))
    elif source == "operator":
        def invalid_operator(*args, **kwargs):
            raise GraphError("repeated_vertex", "Private callback data.")
        monkeypatch.setattr(annealing, "swap_mutation", invalid_operator)
    elif source == "cost":
        def cost(graph, route):
            if route == tuple(initial[0]):
                return 5
            return broken()
        monkeypatch.setattr(annealing, "evaluate_cost", cost)
    else:
        monkeypatch.setattr(annealing, "_accept_move", broken)
    result = solve(empty_graph)
    assert result.status == "error"
    assert result.stop_reason == ("invalid_candidate" if source in ("candidate", "operator") else "runtime_error")
    assert result.best_route == tuple(initial[0]) and result.best_cost == 5
    initial[0][0] = 99
    assert 99 not in result.best_route
    assert result.counters.iterations_completed == 0
    assert result.counters.evaluations_completed == (2 if source == "decision" else 1)
    assert result.counters.evaluations_started == (2 if source in ("cost", "decision") else 1)
    assert "Private callback" not in json.dumps(asdict(result))


@pytest.mark.parametrize("seed", [0, 50, 2**64 - 1])
def test_reproducible_legal_trajectory_and_global_rng_isolation(monkeypatch, seed):
    # A path has varying costs but no cycle, so all 80 reservations are consumed.
    graph = Graph(range(6), [(i, i + 1) for i in range(5)])
    traces, generators, results = [], [], []
    initialize, swap = annealing.initialize_route, annealing.swap_mutation

    def initial(n, rng):
        assert isinstance(rng.bit_generator, np.random.PCG64)
        generators.append(rng)
        return initialize(n, rng)

    def neighbor(route, *, rng):
        assert rng is generators[-1]
        before = tuple(route)
        child = swap(route, rng=rng)
        assert tuple(route) == before
        assert sum(a != b for a, b in zip(route, child)) == 2
        return child

    def cost(graph, route):
        assert check_route_legality(6, route).valid
        traces[-1].append(route)
        return evaluate_cost(graph, route)

    monkeypatch.setattr(annealing, "initialize_route", initial)
    monkeypatch.setattr(annealing, "swap_mutation", neighbor)
    monkeypatch.setattr(annealing, "evaluate_cost", cost)
    python_state, numpy_state = random.getstate(), np.random.get_state()
    for attempt_seed in (seed, (seed + 1) % 2**64, seed):
        traces.append([])
        results.append(solve(graph, seed=attempt_seed, budget=Budget(max_evaluations=80)))
    assert traces[0] == traces[2] and traces[0] != traces[1]
    assert len(traces[0]) == 80
    first, repeated = asdict(results[0]), asdict(results[2])
    first.pop("timing")
    repeated.pop("timing")
    assert first == repeated
    assert results[0].counters.iterations_completed == 79
    assert len({id(rng) for rng in generators}) == 3
    assert random.getstate() == python_state
    after = np.random.get_state()
    assert numpy_state[0] == after[0] and numpy_state[2:] == after[2:]
    np.testing.assert_array_equal(numpy_state[1], after[1])
