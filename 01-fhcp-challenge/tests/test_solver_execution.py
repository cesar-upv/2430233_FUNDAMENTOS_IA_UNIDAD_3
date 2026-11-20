"""Contract #19 checks with explicit clock readings and synthetic graphs."""

import json
from dataclasses import asdict

import numpy as np
import pytest

from src.algorithms import execution
from src.algorithms.execution import Budget, PartialIteration, SolverResult, SolverRun, start_run
from src.graphs import Graph

CYCLE = (0, 1, 2, 3, 4)
OTHER_ROUTE = (0, 1, 3, 2, 4)
OPEN_ROUTE = (1, 0, 2, 3, 4)


class Clock:
    now = 0

    def __call__(self):
        return self.now


def unexpected(*args):
    pytest.fail("This operation must not start.")


def begin(graph, budget, clock):
    run = start_run(graph, seed=17, budget=budget, iteration_unit="generation", clock=clock)
    assert isinstance(run, SolverRun)
    assert run.begin_phase("initialization", 3)
    return run


@pytest.mark.parametrize("seed", [True, -1, 2**64, 1.0, "1", None, np.int64(1)])
def test_invalid_seed_precedes_clock_and_rng(example_graph, monkeypatch, seed):
    monkeypatch.setattr(execution.np.random, "PCG64", unexpected)
    result = start_run(
        example_graph, seed=seed, budget=Budget(max_evaluations=1),
        iteration_unit="generation", clock=unexpected,
    )
    assert (result.status, result.stop_reason, result.error.code) == (
        "error", "invalid_config", "invalid_seed",
    )
    assert result.counters.evaluations_started == 0
    assert result.timing.solver_ns == 0


@pytest.mark.parametrize("budget", [
    None, {"max_evaluations": 1}, Budget(), Budget(max_evaluations=0),
    Budget(max_elapsed_ns=True), Budget(max_elapsed_ns=float("inf")),
    Budget(max_iterations=-1), Budget(max_iterations=2.0, max_evaluations=1),
])
def test_invalid_budget_precedes_clock_and_rng(example_graph, monkeypatch, budget):
    monkeypatch.setattr(execution.np.random, "PCG64", unexpected)
    result = start_run(
        example_graph, seed=0, budget=budget, iteration_unit="generation", clock=unexpected,
    )
    assert (result.stop_reason, result.error.code) == ("invalid_config", "invalid_budget")
    assert result.best_route is None
    assert result.counters.evaluations_completed == 0


def test_small_graph_is_rejected_without_starting():
    result = start_run(
        Graph([1, 2], [(1, 2)]), seed=0, budget=Budget(max_evaluations=1),
        iteration_unit="generation", clock=unexpected,
    )
    assert (result.stop_reason, result.error.code) == ("invalid_input", "graph_too_small")


@pytest.mark.parametrize("seed", [0, 2**64 - 1])
def test_private_pcg64_streams(example_graph, seed):
    options = dict(seed=seed, budget=Budget(max_iterations=1), iteration_unit="generation")
    first = start_run(example_graph, **options)
    second = start_run(example_graph, **options)
    assert first.rng is not second.rng
    assert isinstance(first.rng.bit_generator, np.random.PCG64)
    assert first.rng.integers(100, size=40).tolist() == second.rng.integers(100, size=40).tolist()


def test_last_reservation_preserves_partial_phase_and_best_snapshot(example_graph):
    run = begin(example_graph, Budget(max_evaluations=2), Clock())
    route = list(CYCLE)
    assert run.evaluate(route, lambda graph, route: 1) == 1
    run.record_item()
    route.reverse()
    assert run.evaluate(OTHER_ROUTE, lambda graph, route: 1) == 1
    run.record_item()
    assert run.evaluate(CYCLE, unexpected) is None
    result = run.finish()
    assert result.best_route == CYCLE
    assert result.best_cost == 1
    assert result.validation.valid is None
    assert result.limits_reached == ("evaluation_limit",)
    assert result.counters.partial_iteration == PartialIteration("initialization", 2, 3)
    assert result.counters.evaluations_started == result.counters.evaluations_completed == 2
    assert result.counters.full_evaluations == 2
    assert result.counters.incremental_evaluations == result.counters.cache_hits == 0
    assert result.counters.iterations_completed == 0
    assert result.timing.overrun_ns is None


@pytest.mark.parametrize(("finish_ns", "status"), [(9, "success"), (10, "success"), (11, "exhausted")])
def test_last_evaluation_certification_boundary(example_graph, monkeypatch, finish_ns, status):
    clock = Clock()
    run = begin(example_graph, Budget(max_elapsed_ns=10, max_evaluations=1), clock)

    def certify(graph, route):
        clock.now = finish_ns
        return validate_cycle(graph, route)

    validate_cycle = execution.validate_cycle
    monkeypatch.setattr(execution, "validate_cycle", certify)
    assert run.evaluate(CYCLE, lambda graph, route: 0) == 0
    run.record_item()
    clock.now = 7
    result = run.certify_best()
    assert result.status == status
    assert result.success_within_budget == (status == "success")
    assert result.validation.valid is True
    assert result.counters.validations_started == result.counters.validations_completed == 1
    assert result.timing.solver_ns == finish_ns
    assert result.timing.validation_ns == finish_ns - 7
    assert result.timing.overrun_ns == max(0, finish_ns - 10)
    limits = ("time_limit", "evaluation_limit") if finish_ns >= 10 else ("evaluation_limit",)
    assert result.limits_reached == limits
    if status == "success":
        assert result.stop_reason == "validated_cycle"
        assert result.timing.first_success.elapsed_ns == finish_ns
        assert result.timing.first_success.evaluations_completed == 1
    else:
        assert result.stop_reason == "time_limit"
        assert result.timing.first_success is None
    payload = json.loads(json.dumps(asdict(result), allow_nan=False))
    assert payload["schema_version"] == "fhcp-solver-result/1"
    assert payload["best_route"] == list(CYCLE)
    assert run.finish() is result


def test_exact_limit_prevents_starting_validation(example_graph, monkeypatch):
    clock = Clock()
    run = begin(example_graph, Budget(max_elapsed_ns=10, max_evaluations=1), clock)
    monkeypatch.setattr(execution, "validate_cycle", unexpected)
    assert run.evaluate(CYCLE, lambda graph, route: 0) == 0
    run.record_item()
    clock.now = 10
    result = run.certify_best()
    assert result.stop_reason == "time_limit"
    assert result.validation.reason == "not_run"
    assert result.counters.validations_started == 0
    assert result.best_route == CYCLE
    assert result.best_cost == 0


def test_exact_limit_prevents_next_evaluation_in_generation(example_graph):
    clock = Clock()
    run = start_run(
        example_graph, seed=1, budget=Budget(max_elapsed_ns=10),
        iteration_unit="generation", clock=clock,
    )
    assert run.begin_phase("generation", 2, iteration=True)
    assert run.evaluate(OTHER_ROUTE, lambda graph, route: 1) == 1
    run.record_item()
    clock.now = 10
    assert run.evaluate(CYCLE, unexpected) is None
    result = run.finish()
    assert result.limits_reached == ("time_limit",)
    assert result.counters.evaluations_started == 1
    assert result.counters.iterations_completed == 0
    assert result.counters.partial_iteration == PartialIteration("generation", 1, 2)


def test_cooperative_evaluation_keeps_reservation(example_graph):
    clock = Clock()
    run = begin(example_graph, Budget(max_elapsed_ns=10, max_evaluations=1), clock)

    def interrupted(graph, route):
        clock.now = 10
        assert run.time_expired()
        return None

    assert run.evaluate(CYCLE, interrupted) is None
    result = run.finish()
    assert result.stop_reason == "time_limit"
    assert result.limits_reached == ("time_limit", "evaluation_limit")
    assert result.counters.evaluations_started == 1
    assert result.counters.evaluations_completed == 0
    assert result.best_route is result.best_cost is None


@pytest.mark.parametrize("clock_ns", [9, 10])
def test_simultaneous_limits_after_complete_iteration(example_graph, clock_ns):
    clock = Clock()
    run = start_run(
        example_graph, seed=1,
        budget=Budget(max_elapsed_ns=10, max_evaluations=1, max_iterations=1),
        iteration_unit="generation", clock=clock,
    )
    assert run.begin_phase("generation", 1, iteration=True)
    run.record_restart()
    run.count("proposal")
    assert run.evaluate(OTHER_ROUTE, lambda graph, route: 1) == 1
    run.record_item()
    run.complete_phase()
    clock.now = clock_ns
    assert not run.begin_phase("generation", 1, iteration=True)
    result = run.finish()
    expected = ("evaluation_limit", "iteration_limit")
    if clock_ns == 10:
        expected = ("time_limit", *expected)
    assert result.limits_reached == expected
    assert result.stop_reason == expected[0]
    assert result.counters.iterations_completed == 1
    assert result.counters.partial_iteration is None
    assert result.counters.restarts == 1
    assert result.counters.algorithm_counters == {"proposal": 1}


def test_iteration_limit_excludes_initialization_and_blocks_next_generation(example_graph):
    run = start_run(
        example_graph, seed=1, budget=Budget(max_iterations=1),
        iteration_unit="generation", clock=Clock(),
    )
    assert run.begin_phase("initialization", 1)
    assert run.evaluate(OTHER_ROUTE, lambda graph, route: 1) == 1
    run.record_item()
    run.complete_phase()
    assert run.begin_phase("generation", 1, iteration=True)
    assert run.evaluate(OTHER_ROUTE, lambda graph, route: 1) == 1
    run.record_item()
    run.complete_phase()
    assert not run.begin_phase("generation", 1, iteration=True)
    assert run.finish().limits_reached == ("iteration_limit",)
    assert run.finish().counters.iterations_completed == 1


def test_invalid_candidate_is_not_reserved_and_does_not_replace_best(example_graph):
    run = begin(example_graph, Budget(max_evaluations=3), Clock())
    assert run.evaluate(CYCLE, lambda graph, route: 1) == 1
    run.record_item()
    assert run.evaluate((0, 1, 2, 1, 4), unexpected) is None
    result = run.finish()
    assert result.stop_reason == "invalid_candidate"
    assert result.error.code == "repeated_vertex"
    assert result.error.detail == {"position": 3, "vertices": (1,)}
    assert result.counters.evaluations_started == 1
    assert result.best_route == CYCLE


def test_independent_closing_edge_rejection(example_graph):
    run = begin(example_graph, Budget(max_evaluations=1), Clock())
    assert run.evaluate(OPEN_ROUTE, lambda graph, route: 0) == 0
    run.record_item()
    result = run.certify_best()
    assert (result.status, result.stop_reason) == ("error", "fitness_validation_mismatch")
    assert result.error.code == "missing_closing_edge"
    assert result.validation.vertices == (4, 1)
    assert result.timing.first_success is None


def test_runtime_error_takes_precedence_over_limits(example_graph):
    clock = Clock()
    run = begin(example_graph, Budget(max_elapsed_ns=10, max_evaluations=1), clock)

    def broken(graph, route):
        clock.now = 11
        raise ArithmeticError("Internal data should not enter the result.")

    assert run.evaluate(CYCLE, broken) is None
    result = run.finish()
    assert isinstance(result, SolverResult)
    assert result.stop_reason == "runtime_error"
    assert result.error.code == "ArithmeticError"
    assert result.limits_reached == ("time_limit", "evaluation_limit")
    assert result.timing.overrun_ns == 1
    assert result.counters.evaluations_completed == 0
