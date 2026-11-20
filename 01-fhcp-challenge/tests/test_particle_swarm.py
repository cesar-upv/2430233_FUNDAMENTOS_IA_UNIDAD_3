"""PSO motion, synchronous memories and integration with the common runtime."""

from dataclasses import asdict
from types import SimpleNamespace

import numpy as np
import pytest

from src.algorithms import PSO_VARIANT, PSOConfigurationError, resolve_pso_parameters, solve_pso
from src.algorithms import execution, particle_swarm as pso
from src.algorithms.execution import Budget, PartialIteration
from src.evaluation import validate_cycle
from src.graphs import Graph, check_route_legality


PARAMETERS = {
    "swarm_size": 4,
    "inertia": 0.65,
    "cognitive_coefficient": 1.25,
    "social_coefficient": 1.25,
    "velocity_limit": 0.8,
}


class Clock:
    now = 0

    def __call__(self):
        return self.now


def unexpected(*args, **kwargs):
    pytest.fail("This work must not start.")


@pytest.fixture
def empty_graph():
    return Graph(range(5), [])


def solve(graph, *, parameters=PARAMETERS, seed=54, budget=Budget(max_evaluations=12), clock=None):
    return solve_pso(
        graph, parameters=parameters, seed=seed, budget=budget,
        clock=Clock() if clock is None else clock,
    )


def script_rng(monkeypatch, vectors):
    start = pso.start_run
    draws = iter(vectors)

    def begin(*args, **kwargs):
        run = start(*args, **kwargs)
        run.rng = SimpleNamespace(random=lambda n: next(draws))
        return run

    monkeypatch.setattr(pso, "start_run", begin)


def test_effective_parameters_are_copied_and_expand_optional_limit():
    supplied = {key: value for key, value in PARAMETERS.items() if key != "velocity_limit"}
    supplied["inertia"] = 1
    effective = resolve_pso_parameters(supplied)
    supplied["inertia"] = 2
    assert effective == {**PARAMETERS, "inertia": 1.0, "velocity_limit": None}
    assert type(effective["inertia"]) is float
    assert PSO_VARIANT == "global_real_keys_v1"


@pytest.mark.parametrize(("parameters", "field", "code"), [
    (None, None, "invalid_parameters"),
    ({1: 4}, None, "invalid_parameters"),
    ({}, "swarm_size", "missing_parameter"),
    ({"swarm_size": 4}, "inertia", "missing_parameter"),
    ({**PARAMETERS, "extra": 1}, "extra", "unknown_parameter"),
    *[({**PARAMETERS, "swarm_size": value}, "swarm_size", "invalid_parameter")
      for value in (1, True, 4.0, np.int64(4), "4")],
    *[({**PARAMETERS, field: value}, field, "invalid_parameter")
      for field, value in (("inertia", -1), ("inertia", True), ("inertia", 2**10000),
                           ("cognitive_coefficient", float("nan")), ("cognitive_coefficient", "1"),
                           ("social_coefficient", float("inf")), ("social_coefficient", np.float64(1)),
                           ("velocity_limit", 0), ("velocity_limit", -0.1))],
])
def test_rejects_configuration_before_clock_and_rng(empty_graph, monkeypatch, parameters, field, code):
    with pytest.raises(PSOConfigurationError) as error:
        resolve_pso_parameters(parameters)
    assert (error.value.parameter, error.value.code) == (field, code)
    monkeypatch.setattr(pso, "start_run", unexpected)
    result = solve(empty_graph, parameters=parameters, clock=unexpected)
    assert result.stop_reason == "invalid_config"
    assert result.error.code == code and result.error.detail == {"parameter": field}
    assert result.counters.evaluations_started == 0


@pytest.mark.parametrize(("options", "code"), [
    ({"seed": True}, "invalid_seed"), ({"budget": Budget()}, "invalid_budget"),
    ({"graph": Graph(range(2), [])}, "graph_too_small"),
])
def test_common_input_validation_precedes_rng(empty_graph, monkeypatch, options, code):
    monkeypatch.setattr(execution.np.random, "PCG64", unexpected)
    arguments = dict(graph=empty_graph, parameters=PARAMETERS, seed=54,
                     budget=Budget(max_evaluations=1), clock=unexpected)
    result = solve_pso(**(arguments | options))
    assert result.status == "error" and result.error.code == code
    assert result.counters.evaluations_started == 0


@pytest.mark.parametrize(("limit", "expected_x", "expected_v"), [
    (None, [6.5, 3.25, -0.28125], [4.5, 4.25, -0.53125]),
    (1.0, [3.0, 0.0, -0.28125], [1.0, 1.0, -0.53125]),
])
def test_coordinate_equations_and_velocity_bound(limit, expected_x, expected_v):
    x = np.array([2.0, -1.0, 0.25])
    v = np.array([1.0, 2.0, -2.0])
    personal = np.array([4.0, 3.0, 0.0])
    shared = np.array([6.0, -3.0, 1.0])
    particle = pso._Particle(x, v, pso._Best(personal, 2))
    samples = iter([np.array([0.25, 0.5, 0.75]), np.array([0.5, 0.25, 0.75])])
    sizes = []

    def random(n):
        sizes.append(n)
        return next(samples)

    parameters = resolve_pso_parameters({
        **PARAMETERS, "inertia": 0.5, "cognitive_coefficient": 2, "social_coefficient": 1.5,
        "velocity_limit": limit,
    })
    moved, velocity = pso._advance(particle, shared, parameters, SimpleNamespace(random=random))
    assert sizes == [3, 3]
    np.testing.assert_array_equal(moved, expected_x)
    np.testing.assert_array_equal(velocity, expected_v)
    for array, original in zip((x, v, personal, shared), ([2, -1, .25], [1, 2, -2], [4, 3, 0], [6, -3, 1])):
        np.testing.assert_array_equal(array, original)
        assert not np.shares_memory(moved, array)
        assert not np.shares_memory(velocity, array)


def test_rounds_freeze_global_and_keep_independent_memories_on_ties(empty_graph, monkeypatch):
    initial = [np.roll(np.arange(5, dtype=float) / 5, i) for i in range(3)]
    draws = [item for position in initial for item in (position, np.full(5, 0.99))]
    script_rng(monkeypatch, draws)
    positions = [np.roll(np.arange(5, dtype=float) + 2 + i, i % 5) for i in range(9)]
    # Initial tie, two equal improvements, then a worse move and another tie.
    costs = iter([4, 4, 5, 3, 3, 5, 4, 3, 4, 3, 3, 5])
    captured = []

    def advance(particle, shared, parameters, rng):
        index = len(captured)
        captured.append((particle, shared))
        return positions[index], np.zeros(5)

    monkeypatch.setattr(pso, "_advance", advance)
    monkeypatch.setattr(pso, "evaluate_cost", lambda graph, route: next(costs))
    result = solve(empty_graph, parameters={**PARAMETERS, "swarm_size": 3, "velocity_limit": 0.25},
                   budget=Budget(max_iterations=3))
    assert result.counters.iterations_completed == 3
    assert result.counters.evaluations_completed == 12
    assert result.best_cost == 3 and result.best_route == pso.decode_real_keys(5, positions[0])
    for index, (particle, shared) in enumerate(captured):
        expected_global = initial[0] if index < 3 else positions[0]
        np.testing.assert_array_equal(shared, expected_global)
        assert not np.shares_memory(shared, expected_global)
        assert not np.shares_memory(particle.position, particle.personal_best.keys)
        assert not np.shares_memory(shared, particle.personal_best.keys)
    for particle, _ in captured[:3]:
        np.testing.assert_array_equal(particle.velocity, np.full(5, 0.25))
    third = captured[5][0]
    np.testing.assert_array_equal(third.position, positions[2])
    np.testing.assert_array_equal(third.personal_best.keys, initial[2])
    for index in (0, 1):
        particle = captured[6 + index][0]
        np.testing.assert_array_equal(particle.position, positions[3 + index])
        np.testing.assert_array_equal(particle.personal_best.keys, positions[index])
        assert particle.personal_best.cost == 3
    positions[0][:] = -99
    assert captured[3][1][0] == 2
    assert captured[3][0].personal_best.keys[0] == 2


def test_equal_keys_use_the_shared_decoder_and_first_evaluated_route(empty_graph, monkeypatch):
    script_rng(monkeypatch, [np.full(5, 0.4), np.full(5, 0.5)])
    result = solve(empty_graph, budget=Budget(max_evaluations=1))
    assert result.best_route == (0, 1, 2, 3, 4)
    assert result.counters.partial_iteration == PartialIteration("initialization", 1, 4)


@pytest.mark.parametrize(("limit", "iterations", "partial"), [
    (1, 0, PartialIteration("initialization", 1, 4)), (4, 0, None),
    (5, 0, PartialIteration("round", 1, 4)), (8, 1, None),
    (9, 1, PartialIteration("round", 1, 4)), (12, 2, None),
])
def test_budget_counts_initialization_and_complete_or_partial_rounds(empty_graph, limit, iterations, partial):
    result = solve(empty_graph, budget=Budget(max_evaluations=limit))
    assert (result.status, result.stop_reason) == ("exhausted", "evaluation_limit")
    assert result.counters.iteration_unit == "round"
    assert result.counters.evaluations_started == result.counters.evaluations_completed == limit
    assert result.counters.iterations_completed == iterations
    assert result.counters.partial_iteration == partial
    assert result.best_cost == 5 and check_route_legality(5, result.best_route).valid


def test_iteration_limit_finishes_one_round_after_initialization(empty_graph):
    result = solve(empty_graph, budget=Budget(max_iterations=1))
    assert result.stop_reason == "iteration_limit"
    assert result.counters.evaluations_completed == 8
    assert result.counters.iterations_completed == 1
    assert result.counters.partial_iteration is None


@pytest.mark.parametrize(("stage", "completed"), [("move", 4), ("decode", 4), ("last_cost", 8)])
def test_time_boundaries_during_round_preserve_completed_work(empty_graph, monkeypatch, stage, completed):
    clock = Clock()
    advance, decode, evaluate = pso._advance, pso.decode_real_keys, pso.evaluate_cost
    decoded = evaluations = 0

    def move(*args):
        result = advance(*args)
        if stage == "move":
            clock.now = 10
        return result

    def decoder(n, keys):
        nonlocal decoded
        decoded += 1
        if stage == "decode" and decoded == 5:
            clock.now = 10
        return decode(n, keys)

    def cost(graph, route):
        nonlocal evaluations
        evaluations += 1
        if stage == "last_cost" and evaluations == 8:
            clock.now = 10
        return evaluate(graph, route)

    monkeypatch.setattr(pso, "_advance", move)
    monkeypatch.setattr(pso, "decode_real_keys", decoder)
    monkeypatch.setattr(pso, "evaluate_cost", cost)
    result = solve(empty_graph, budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.stop_reason == "time_limit"
    assert result.counters.evaluations_started == result.counters.evaluations_completed == completed
    assert result.counters.iterations_completed == 0
    assert result.counters.partial_iteration == PartialIteration("round", completed - 4, 4)


@pytest.mark.parametrize("bad_vector", ["position", "velocity"])
def test_nonfinite_initial_state_is_rejected_before_decoding(empty_graph, monkeypatch, bad_vector):
    position, velocity = np.zeros(5), np.full(5, 0.5)
    (position if bad_vector == "position" else velocity)[1] = np.inf
    script_rng(monkeypatch, [position, velocity])
    monkeypatch.setattr(pso, "decode_real_keys", unexpected)
    result = solve(empty_graph)
    assert (result.status, result.stop_reason) == ("error", "non_finite_state")
    assert result.counters.evaluations_started == 0


def test_velocity_overflow_is_detected_before_clipping_or_reserving(empty_graph, monkeypatch):
    maximum = float(np.finfo(np.float64).max)
    script_rng(monkeypatch, [np.full(5, x) for x in (0.9, 0.99, 0.1, 0.99, 0.99, 0.99, 0.99, 0.99)])
    parameters = {**PARAMETERS, "swarm_size": 2, "inertia": maximum,
                  "cognitive_coefficient": 0, "social_coefficient": maximum, "velocity_limit": 0.5}
    with np.errstate(over="ignore", invalid="ignore", under="raise"):
        result = solve(empty_graph, parameters=parameters)
        assert np.geterr()["over"] == "ignore" and np.geterr()["under"] == "raise"
    assert (result.status, result.stop_reason) == ("error", "non_finite_state")
    assert result.counters.evaluations_started == result.counters.evaluations_completed == 3
    assert result.counters.partial_iteration == PartialIteration("round", 1, 2)
    assert result.best_cost == 5


def test_position_addition_rejects_overflow_after_a_finite_velocity():
    x = np.full(3, np.finfo(np.float64).max)
    particle = pso._Particle(x, x.copy(), pso._Best(x.copy(), 3))
    parameters = resolve_pso_parameters({**PARAMETERS, "inertia": 1, "velocity_limit": None})
    with pytest.raises(FloatingPointError):
        pso._advance(particle, x.copy(), parameters, np.random.Generator(np.random.PCG64(54)))


@pytest.mark.parametrize(("finished", "status", "reason"), [
    (10, "success", "validated_cycle"), (11, "exhausted", "time_limit"),
])
def test_last_evaluation_can_certify_at_deadline_or_report_late_certificate(monkeypatch, finished, status, reason):
    triangle = Graph(range(3), [(0, 1), (1, 2), (2, 0)])
    clock = Clock()

    def certify(graph, route):
        result = validate_cycle(graph, route)
        clock.now = finished
        return result

    monkeypatch.setattr(execution, "validate_cycle", certify)
    result = solve(triangle, budget=Budget(max_elapsed_ns=10, max_evaluations=1), clock=clock)
    assert (result.status, result.stop_reason) == (status, reason)
    assert result.counters.evaluations_started == result.counters.validations_completed == 1
    assert result.validation.valid is True
    assert result.success_within_budget is (status == "success")
    assert result.timing.overrun_ns == finished - 10
    assert (result.timing.first_success is not None) is (status == "success")


def test_cost_zero_at_deadline_preserves_route_without_starting_validation(monkeypatch):
    triangle = Graph(range(3), [(0, 1), (1, 2), (2, 0)])
    clock = Clock()

    def cost(graph, route):
        clock.now = 10
        return 0

    monkeypatch.setattr(pso, "evaluate_cost", cost)
    monkeypatch.setattr(execution, "validate_cycle", unexpected)
    result = solve(triangle, budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.stop_reason == "time_limit" and result.best_cost == 0
    assert result.validation.reason == "not_run"
    assert result.counters.validations_started == 0


def test_fitness_discrepancy_uses_independent_validator(empty_graph, monkeypatch):
    monkeypatch.setattr(pso, "evaluate_cost", lambda graph, route: 0)
    result = solve(empty_graph, budget=Budget(max_evaluations=1))
    assert (result.status, result.stop_reason) == ("error", "fitness_validation_mismatch")
    assert result.validation.valid is False and result.validation.reason == "missing_edge"


def test_unexpected_motion_error_retains_the_best_and_pending_round(empty_graph, monkeypatch):
    def broken(*args):
        raise RuntimeError("Unexpected particle update failure.")

    monkeypatch.setattr(pso, "_advance", broken)
    result = solve(empty_graph)
    assert (result.status, result.stop_reason) == ("error", "runtime_error")
    assert result.error.code == "RuntimeError"
    assert result.best_cost == 5 and result.counters.evaluations_completed == 4
    assert result.counters.partial_iteration == PartialIteration("round", 0, 4)


def test_real_pso_moves_and_finds_a_certified_synthetic_cycle():
    graph = Graph(range(5), [(i, (i + 1) % 5) for i in range(5)])
    result = solve(graph, budget=Budget(max_evaluations=100))
    assert result.status == "success" and result.best_cost == 0
    assert result.counters.iterations_completed > 0
    assert validate_cycle(graph, result.best_route).valid


def test_reproduction_includes_trajectory_and_leaves_global_rng_unchanged(empty_graph, monkeypatch):
    state = np.random.get_state()
    cost_function = pso.evaluate_cost
    traces, results = [], []

    def cost(graph, route):
        traces[-1].append(route)
        return cost_function(graph, route)

    monkeypatch.setattr(pso, "evaluate_cost", cost)
    for seed in (54, 55, 54):
        traces.append([])
        snapshot = asdict(solve(empty_graph, seed=seed, budget=Budget(max_evaluations=17)))
        snapshot.pop("timing")
        results.append(snapshot)
    assert traces[0] == traces[2] and traces[0] != traces[1]
    assert results[0] == results[2]
    after = np.random.get_state()
    assert state[0] == after[0] and state[2:] == after[2:]
    np.testing.assert_array_equal(state[1], after[1])
