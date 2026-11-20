"""GA integration with synthetic graphs, independent certification and fake time."""

from dataclasses import asdict
import json
from types import SimpleNamespace

import numpy as np
import pytest

from src.algorithms import GA_VARIANT, GAConfigurationError, resolve_ga_parameters, solve_ga
from src.algorithms import execution, genetic
from src.algorithms.execution import Budget, PartialIteration
from src.evaluation import evaluate_cost, validate_cycle
from src.graphs import Graph, check_route_legality

PARAMETERS = {"population_size": 4, "tournament_size": 2}
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
    return Graph(range(1, 6), [])


def solve(graph, *, parameters=None, budget=None, seed=17, clock=None):
    return solve_ga(
        graph, parameters=PARAMETERS if parameters is None else parameters, seed=seed,
        budget=Budget(max_evaluations=10) if budget is None else budget,
        clock=Clock() if clock is None else clock,
    )


@pytest.mark.parametrize("size,elites", [(2, 1), (50, 1), (99, 1), (100, 1), (128, 1), (200, 2), (250, 2)])
def test_effective_defaults_and_one_percent_rounding(size, elites):
    parameters = {"population_size": size, "tournament_size": 1}
    effective = resolve_ga_parameters(parameters)
    assert effective == {
        **parameters, "crossover_rate": 0.8, "mutation_rate": 0.010, "elite_count": elites,
    }
    assert parameters == {"population_size": size, "tournament_size": 1}
    assert GA_VARIANT == "generational_ox_swap_v1"


def test_explicit_values_override_defaults_and_are_detached():
    parameters = {**PARAMETERS, "elite_count": 0, "crossover_rate": 0, "mutation_rate": 1}
    effective = resolve_ga_parameters(parameters)
    assert effective == {**parameters, "crossover_rate": 0.0, "mutation_rate": 1.0}
    assert type(effective["crossover_rate"]) is type(effective["mutation_rate"]) is float
    parameters["elite_count"] = 3
    assert effective["elite_count"] == 0


INVALID_PARAMETERS = [
    (None, "invalid_parameters", None),
    ([], "invalid_parameters", None),
    ({1: 2}, "invalid_parameters", None),
    ({**PARAMETERS, "unknown": 1}, "unknown_parameter", "unknown"),
    ({}, "missing_parameter", "population_size"),
    ({"population_size": 4}, "missing_parameter", "tournament_size"),
    *[({**PARAMETERS, "population_size": value}, "invalid_parameter", "population_size")
      for value in (1, 0, -1, True, 4.0, "4", None, np.int64(4))],
    *[({**PARAMETERS, "tournament_size": value}, "invalid_parameter", "tournament_size")
      for value in (0, 5, True, 2.0, "2", None, np.int64(2))],
    *[({**PARAMETERS, name: value}, "invalid_parameter", name)
      for name in ("crossover_rate", "mutation_rate")
      for value in (-0.1, 1.1, True, "0.5", None, float("nan"), float("inf"), -float("inf"), np.float64(0.5), 2**10000)],
    *[({**PARAMETERS, "elite_count": value}, "invalid_parameter", "elite_count")
      for value in (-1, 4, True, 1.0, "1", None, np.int64(1))],
]


@pytest.mark.parametrize("parameters,code,field", INVALID_PARAMETERS)
def test_invalid_parameters_precede_rng_and_clock(empty_graph, monkeypatch, parameters, code, field):
    with pytest.raises(GAConfigurationError) as error:
        resolve_ga_parameters(parameters)
    assert (error.value.code, error.value.parameter) == (code, field)
    monkeypatch.setattr(genetic, "start_run", unexpected)
    result = solve_ga(empty_graph, parameters=parameters, seed=17,
                      budget=Budget(max_evaluations=10), clock=unexpected)
    assert result.status == "error" and result.stop_reason == "invalid_config"
    assert result.error.code == code
    assert result.error.detail == {"parameter": field}
    assert result.error.phase == "input"
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
def test_common_validation_is_delegated(empty_graph, monkeypatch, options, reason, code):
    monkeypatch.setattr(execution.np.random, "PCG64", unexpected)
    arguments = {"graph": empty_graph, "parameters": PARAMETERS, "seed": 17,
                 "budget": Budget(max_evaluations=1), "clock": unexpected, **options}
    result = solve_ga(**arguments)
    assert (result.stop_reason, result.error.code) == (reason, code)
    assert result.counters.evaluations_started == 0


def test_success_during_initialization_uses_independent_certificate():
    triangle = Graph([1, 2, 3], [(1, 2), (2, 3), (3, 1)])
    result = solve(triangle, budget=Budget(max_evaluations=1))
    assert result.status == "success" and result.success_within_budget
    assert result.best_cost == 0
    assert validate_cycle(triangle, result.best_route).valid
    assert result.counters.evaluations_started == result.counters.evaluations_completed == 1
    assert result.counters.validations_completed == 1
    assert result.counters.partial_iteration == PartialIteration("initialization", 1, 4)
    assert result.counters.iterations_completed == 0
    assert result.limits_reached == ("evaluation_limit",)
    assert result.timing.first_success.evaluations_completed == 1
    json.dumps(asdict(result), allow_nan=False)


@pytest.mark.parametrize("child_index", [1, 3])
def test_success_in_last_admitted_descendant(example_graph, monkeypatch, child_index):
    monkeypatch.setattr(genetic, "initialize_route", lambda n, rng: OTHER)
    children = iter([OTHER] * (child_index - 1) + [CYCLE])
    monkeypatch.setattr(genetic, "order_crossover", lambda a, b, **kwargs: next(children))
    parameters = {**PARAMETERS, "crossover_rate": 1, "mutation_rate": 0}
    result = solve(example_graph, parameters=parameters, budget=Budget(max_evaluations=4 + child_index))
    assert result.status == "success" and result.best_route == CYCLE
    assert validate_cycle(example_graph, result.best_route).valid
    assert result.counters.evaluations_completed == 4 + child_index
    assert result.counters.partial_iteration == PartialIteration("generation", child_index, 3)
    assert result.counters.iterations_completed == 0


def test_real_evolution_finds_and_certifies_a_synthetic_cycle():
    graph = Graph(range(5), [(i, (i + 1) % 5) for i in range(5)])
    result = solve(graph, budget=Budget(max_evaluations=500))
    assert result.status == "success" and result.best_cost == 0
    assert validate_cycle(graph, result.best_route).valid
    assert 4 < result.counters.evaluations_completed <= 500
    assert result.counters.iterations_completed > 0
    assert result.counters.validations_completed == 1


@pytest.mark.parametrize("limit,completed,partial", [
    (1, 0, PartialIteration("initialization", 1, 4)),
    (4, 0, None), (5, 0, PartialIteration("generation", 1, 3)),
    (7, 1, None), (8, 1, PartialIteration("generation", 1, 3)), (10, 2, None),
])
def test_exact_evaluation_limits_and_partial_generations(empty_graph, monkeypatch, limit, completed, partial):
    evaluated = []

    def cost(graph, route):
        evaluated.append(route)
        return evaluate_cost(graph, route)

    monkeypatch.setattr(genetic, "evaluate_cost", cost)
    result = solve(empty_graph, budget=Budget(max_evaluations=limit))
    assert result.status == "exhausted" and result.stop_reason == "evaluation_limit"
    assert result.counters.evaluations_started == result.counters.evaluations_completed == limit
    assert len(evaluated) == limit
    assert result.counters.iterations_completed == completed
    assert result.counters.partial_iteration == partial
    assert result.counters.full_evaluations == limit
    assert result.counters.cache_hits == result.counters.incremental_evaluations == result.counters.restarts == 0
    assert result.best_route == evaluated[0]
    assert result.best_cost == 5 and check_route_legality(5, result.best_route).valid
    assert result.validation.reason == "not_run"


@pytest.mark.parametrize("size,elites", [(2, 0), (2, 1), (4, 0), (4, 3)])
def test_iteration_budget_excludes_initialization_and_elites(empty_graph, size, elites):
    result = solve(empty_graph, parameters={"population_size": size, "tournament_size": size, "elite_count": elites},
                   budget=Budget(max_iterations=2))
    assert result.stop_reason == "iteration_limit"
    assert result.counters.iterations_completed == 2
    assert result.counters.evaluations_completed == size + 2 * (size - elites)
    assert result.counters.partial_iteration is None


def test_tournament_samples_without_replacement_and_breaks_ties_by_index():
    population = [(CYCLE, 2), (OTHER, 1), (tuple(reversed(CYCLE)), 1)]
    calls = []

    def choice(n, *, size, replace):
        calls.append((n, size, replace))
        return [2, 1, 0]

    run = SimpleNamespace(rng=SimpleNamespace(choice=choice))
    assert genetic._tournament(population, 3, run) == OTHER
    assert calls == [(3, 3, False)]


def test_stable_elites_frozen_population_and_no_reevaluations(empty_graph, monkeypatch):
    routes = [tuple(np.roll(CYCLE, i)) for i in range(5)]
    initial = iter(routes[:4])
    artificial_costs = dict(zip(routes, [4, 1, 1, 2, 3]))
    evaluations, populations = [], []
    monkeypatch.setattr(genetic, "initialize_route", lambda n, rng: next(initial))

    def cost(graph, route):
        evaluations.append(route)
        return artificial_costs[route]

    def tournament(population, size, run):
        populations.append(tuple(population))
        return population[0][0]

    monkeypatch.setattr(genetic, "evaluate_cost", cost)
    monkeypatch.setattr(genetic, "_tournament", tournament)
    monkeypatch.setattr(genetic, "order_crossover", lambda a, b, **kwargs: routes[4])
    result = solve(empty_graph, parameters={**PARAMETERS, "elite_count": 2, "crossover_rate": 1, "mutation_rate": 0},
                   budget=Budget(max_iterations=2))
    assert evaluations == [*routes[:4], *([routes[4]] * 4)]
    assert all(p == tuple(zip(routes[:4], [4, 1, 1, 2])) for p in populations[:4])
    assert all(p == ((routes[1], 1), (routes[2], 1), (routes[4], 3), (routes[4], 3)) for p in populations[4:])
    assert result.best_route == routes[1] and result.best_cost == 1
    assert result.counters.evaluations_completed == 8


@pytest.mark.parametrize("cross,mutation", [(0, 0), (0, 1), (1, 0), (1, 1)])
def test_operator_probability_endpoints_and_parent_preservation(empty_graph, monkeypatch, cross, mutation):
    cross_calls, mutation_calls, generators, evaluated = [], [], [], []
    real_cross, real_mutation = genetic.order_crossover, genetic.swap_mutation

    def crossover(a, b, *, rng):
        before = (tuple(a), tuple(b))
        child = real_cross(a, b, rng=rng)
        assert (a, b) == before
        cross_calls.append(child)
        generators.append(rng)
        return child

    def mutate(route, *, rng):
        before = tuple(route)
        child = real_mutation(route, rng=rng)
        assert route == before
        mutation_calls.append(child)
        generators.append(rng)
        return child

    def cost(graph, route):
        assert check_route_legality(5, route).valid
        evaluated.append(route)
        return evaluate_cost(graph, route)

    monkeypatch.setattr(genetic, "order_crossover", crossover)
    monkeypatch.setattr(genetic, "swap_mutation", mutate)
    monkeypatch.setattr(genetic, "evaluate_cost", cost)
    result = solve(empty_graph, parameters={**PARAMETERS, "crossover_rate": cross, "mutation_rate": mutation},
                   budget=Budget(max_iterations=1))
    assert len(cross_calls) == 3 * cross and len(mutation_calls) == 3 * mutation
    assert len(evaluated) == result.counters.evaluations_completed == 7
    assert all(rng is generators[0] for rng in generators)


def test_configuration_is_snapshotted_before_population_creation(empty_graph, monkeypatch):
    parameters = dict(PARAMETERS)
    initialize = genetic.initialize_route

    def mutate_configuration(n, rng):
        parameters.update(population_size=100, crossover_rate=float("nan"), elite_count=100)
        return initialize(n, rng)

    monkeypatch.setattr(genetic, "initialize_route", mutate_configuration)
    result = solve(empty_graph, parameters=parameters, budget=Budget(max_iterations=1))
    assert result.counters.evaluations_completed == 7
    assert result.counters.iterations_completed == 1


@pytest.mark.parametrize("rate", [0, 1])
def test_probability_draws_are_consumed_even_at_endpoints(empty_graph, monkeypatch, rate):
    events = []
    start = genetic.start_run

    class Decisions:
        def __init__(self, rng):
            self.rng = rng

        def choice(self, n, *, size, replace):
            events.append("tournament")
            assert replace is False
            return self.rng.choice(n, size=size, replace=replace)

        def random(self):
            events.append("probability")
            return self.rng.random()

    def begin(*args, **kwargs):
        run = start(*args, **kwargs)
        run.rng = Decisions(run.rng)
        return run

    monkeypatch.setattr(genetic, "start_run", begin)
    monkeypatch.setattr(genetic, "initialize_route", lambda n, rng: CYCLE)
    monkeypatch.setattr(genetic, "order_crossover", lambda a, b, **kwargs: tuple(a))
    monkeypatch.setattr(genetic, "swap_mutation", lambda route, **kwargs: tuple(route))
    result = solve(empty_graph, parameters={**PARAMETERS, "crossover_rate": rate, "mutation_rate": rate},
                   budget=Budget(max_iterations=1))
    assert result.counters.iterations_completed == 1
    assert events == ["tournament", "tournament", "probability", "probability"] * 3


def test_timeout_before_first_candidate(empty_graph, monkeypatch):
    ticks = iter([0, 10])
    monkeypatch.setattr(genetic, "initialize_route", unexpected)
    result = solve(empty_graph, budget=Budget(max_elapsed_ns=10), clock=lambda: next(ticks))
    assert result.stop_reason == "time_limit"
    assert result.best_route is result.best_cost is None
    assert result.counters.evaluations_started == 0 and result.counters.partial_iteration is None


@pytest.mark.parametrize("evaluation,partial", [
    (1, PartialIteration("initialization", 1, 4)),
    (4, None),
    (5, PartialIteration("generation", 1, 3)),
    (7, PartialIteration("generation", 3, 3)),
])
def test_timeout_during_evaluation_and_before_replacement(empty_graph, monkeypatch, evaluation, partial):
    clock = Clock()
    calls = 0

    def cost(graph, route):
        nonlocal calls
        calls += 1
        if calls == evaluation:
            clock.now = 10
        return evaluate_cost(graph, route)

    monkeypatch.setattr(genetic, "evaluate_cost", cost)
    result = solve(empty_graph, budget=Budget(max_elapsed_ns=10, max_evaluations=7), clock=clock)
    assert result.stop_reason == "time_limit"
    assert result.counters.evaluations_started == result.counters.evaluations_completed == evaluation
    assert result.counters.partial_iteration == partial
    assert result.counters.iterations_completed == 0


@pytest.mark.parametrize("stage", ["first_parent", "second_parent", "crossover", "mutation"])
def test_timeout_between_child_operations_prevents_new_reservation(empty_graph, monkeypatch, stage):
    clock = Clock()
    real_tournament = genetic._tournament
    tournaments = 0

    def tournament(population, size, run):
        nonlocal tournaments
        tournaments += 1
        route = real_tournament(population, size, run)
        if (stage == "first_parent" and tournaments == 1) or (stage == "second_parent" and tournaments == 2):
            clock.now = 10
        return route

    def crossover(a, b, **kwargs):
        if stage == "crossover":
            clock.now = 10
        return a

    def mutation(route, **kwargs):
        if stage == "mutation":
            clock.now = 10
        return route

    monkeypatch.setattr(genetic, "_tournament", tournament)
    monkeypatch.setattr(genetic, "order_crossover", crossover)
    monkeypatch.setattr(genetic, "swap_mutation", mutation)
    result = solve(empty_graph, parameters={**PARAMETERS, "crossover_rate": 1, "mutation_rate": 1},
                   budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.stop_reason == "time_limit"
    assert result.counters.evaluations_started == 4
    assert result.counters.partial_iteration == PartialIteration("generation", 0, 3)


@pytest.mark.parametrize("finish,status", [(9, "success"), (10, "success"), (11, "exhausted")])
def test_last_reservation_certification_boundaries(monkeypatch, finish, status):
    triangle = Graph([1, 2, 3], [(1, 2), (2, 3), (3, 1)])
    clock = Clock()

    def cost(graph, route):
        clock.now = 5
        return evaluate_cost(graph, route)

    def certify(graph, route):
        certificate = validate_cycle(graph, route)
        clock.now = finish
        return certificate

    monkeypatch.setattr(genetic, "evaluate_cost", cost)
    monkeypatch.setattr(execution, "validate_cycle", certify)
    result = solve(triangle, budget=Budget(max_elapsed_ns=10, max_evaluations=1), clock=clock)
    assert result.status == status and result.validation.valid is True
    assert result.success_within_budget == (status == "success")
    assert (result.timing.first_success is not None) == (status == "success")
    assert result.timing.validation_ns == finish - 5
    assert result.timing.overrun_ns == max(0, finish - 10)
    assert result.counters.evaluations_started == result.counters.validations_completed == 1


def test_validation_cannot_start_at_time_limit(example_graph, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(genetic, "initialize_route", lambda n, rng: CYCLE)

    def cost(graph, route):
        clock.now = 10
        return evaluate_cost(graph, route)

    monkeypatch.setattr(genetic, "evaluate_cost", cost)
    monkeypatch.setattr(execution, "validate_cycle", unexpected)
    result = solve(example_graph, budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.status == "exhausted" and result.best_cost == 0
    assert result.validation.reason == "not_run" and result.counters.validations_started == 0


def test_zero_cost_mismatch_is_error_not_success(empty_graph, monkeypatch):
    monkeypatch.setattr(genetic, "evaluate_cost", lambda graph, route: 0)
    result = solve(empty_graph, budget=Budget(max_evaluations=1))
    assert result.status == "error" and result.stop_reason == "fitness_validation_mismatch"
    assert result.validation.valid is False and result.best_cost == 0
    assert result.timing.first_success is None


@pytest.mark.parametrize("source", ["candidate", "operator", "cost"])
def test_errors_preserve_best_and_do_not_fabricate_completed_work(empty_graph, monkeypatch, source):
    initial = genetic.initialize_route
    first = []

    def initialize(n, rng):
        if source == "candidate" and first:
            return (0, 1, 2, 3, 3)
        route = initial(n, rng)
        first.append(route)
        return route

    monkeypatch.setattr(genetic, "initialize_route", initialize)
    if source == "operator":
        def broken(*args, **kwargs):
            raise ArithmeticError("Private callback data must not be exposed.")
        monkeypatch.setattr(genetic, "order_crossover", broken)
    elif source == "cost":
        calls = 0

        def cost(graph, route):
            nonlocal calls
            calls += 1
            if calls == 5:
                raise ArithmeticError("Private callback data must not be exposed.")
            return evaluate_cost(graph, route)

        monkeypatch.setattr(genetic, "evaluate_cost", cost)
    result = solve(empty_graph, parameters={**PARAMETERS, "crossover_rate": 1})
    assert result.status == "error"
    assert result.stop_reason == ("invalid_candidate" if source == "candidate" else "runtime_error")
    assert result.best_route == first[0] and result.best_cost == 5
    assert result.counters.evaluations_completed == (1 if source == "candidate" else 4)
    assert result.counters.evaluations_started == (5 if source == "cost" else result.counters.evaluations_completed)
    assert result.counters.iterations_completed == 0
    assert "Private callback" not in json.dumps(asdict(result))


@pytest.mark.parametrize("seed", [0, 17, 2**64 - 1])
def test_reproduction_includes_trajectory_and_isolates_attempts(empty_graph, monkeypatch, seed):
    traces = []
    generators = []
    initialize = genetic.initialize_route

    def initial(n, rng):
        assert isinstance(rng.bit_generator, np.random.PCG64)
        generators.append(rng)
        return initialize(n, rng)

    monkeypatch.setattr(genetic, "initialize_route", initial)

    def cost(graph, route):
        traces[-1].append(route)
        return evaluate_cost(graph, route)

    monkeypatch.setattr(genetic, "evaluate_cost", cost)
    state = np.random.get_state()
    results = []
    for attempt_seed in (seed, (seed + 1) % 2**64, seed):
        traces.append([])
        results.append(solve(empty_graph, seed=attempt_seed, budget=Budget(max_evaluations=30)))
    assert traces[0] == traces[2] and traces[0] != traces[1]
    first, repeated = asdict(results[0]), asdict(results[2])
    first.pop("timing")
    repeated.pop("timing")
    assert first == repeated
    assert len(traces[0]) == 30
    assert generators[0] is not generators[4] and generators[0] is not generators[8]
    assert all(rng is generators[0] for rng in generators[:4])
    after = np.random.get_state()
    assert state[0] == after[0] and state[2:] == after[2:]
    np.testing.assert_array_equal(state[1], after[1])
