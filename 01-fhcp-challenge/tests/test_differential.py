"""DE equations, synchronous selection and integration with contract #19."""

from dataclasses import asdict
from types import SimpleNamespace

import numpy as np
import pytest

from src.algorithms import DEConfigurationError, DE_VARIANT, resolve_de_parameters, solve_de
from src.algorithms import differential as de, execution
from src.algorithms.execution import Budget, PartialIteration
from src.evaluation import validate_cycle
from src.graphs import Graph, check_route_legality

PARAMETERS = {'population_size': 4, 'differential_weight': 0.5, 'crossover_rate': 0.8}


class Clock:
    now = 0

    def __call__(self):
        return self.now


def unexpected(*args, **kwargs):
    pytest.fail('Work must not start.')


@pytest.fixture
def empty_graph():
    return Graph(range(5), [])


def solve(graph, *, parameters=None, budget=None, clock=None, seed=53):
    return solve_de(
        graph, parameters=PARAMETERS if parameters is None else parameters,
        seed=seed, budget=Budget(max_evaluations=12) if budget is None else budget,
        clock=Clock() if clock is None else clock,
    )


def test_parameters_are_effective_and_detached():
    parameters = {**PARAMETERS, 'differential_weight': 1, 'crossover_rate': 0}
    effective = resolve_de_parameters(parameters)
    parameters['population_size'] = 99
    assert effective == {'population_size': 4, 'differential_weight': 1.0, 'crossover_rate': 0.0}
    assert type(effective['differential_weight']) is float
    assert DE_VARIANT == 'rand_1_bin_real_keys_v1'


@pytest.mark.parametrize('parameters,field', [
    (None, None), ([], None), ({1: 4}, None), ({}, 'population_size'),
    ({'population_size': 4}, 'differential_weight'),
    ({'population_size': 4, 'differential_weight': 1}, 'crossover_rate'),
    ({**PARAMETERS, 'unknown': 1}, 'unknown'),
    *[({**PARAMETERS, 'population_size': x}, 'population_size')
      for x in [3, True, 4.0, np.int64(4), '4']],
    *[({**PARAMETERS, 'differential_weight': x}, 'differential_weight')
      for x in [0, -1, True, None, np.float64(0.5), float('nan'), float('inf'), 2**10000]],
    *[({**PARAMETERS, 'crossover_rate': x}, 'crossover_rate')
      for x in [-0.1, 1.1, True, None, float('nan'), float('inf'), '0.5']],
])
def test_rejected_configuration_never_starts_clock_or_rng(empty_graph, monkeypatch, parameters, field):
    with pytest.raises(DEConfigurationError) as error:
        resolve_de_parameters(parameters)
    assert error.value.parameter == field
    monkeypatch.setattr(de, 'start_run', unexpected)
    result = solve_de(empty_graph, parameters=parameters, seed=53,
                      budget=Budget(max_evaluations=1), clock=unexpected)
    assert result.stop_reason == 'invalid_config'
    assert result.error.code == error.value.code
    assert result.error.detail == {'parameter': field}
    assert result.counters.evaluations_started == 0


@pytest.mark.parametrize('options,code', [
    ({'seed': True}, 'invalid_seed'), ({'budget': Budget()}, 'invalid_budget'),
    ({'graph': Graph([0, 1], [])}, 'graph_too_small'),
])
def test_common_input_rejection_precedes_rng(empty_graph, monkeypatch, options, code):
    monkeypatch.setattr(execution.np.random, 'PCG64', unexpected)
    arguments = dict(graph=empty_graph, parameters=PARAMETERS, seed=53,
                     budget=Budget(max_evaluations=1), clock=unexpected)
    result = solve_de(**(arguments | options))
    assert result.status == 'error' and result.error.code == code
    assert result.counters.evaluations_started == 0


@pytest.mark.parametrize('target', range(4))
@pytest.mark.parametrize('rate', [0.0, 0.5, 1.0])
def test_trial_equation_donor_exclusion_forced_coordinate_and_no_alias(target, rate):
    population = [(np.array([i, i + 0.2, i + 0.5]), (0, 1, 2), 3) for i in range(4)]
    before = [keys.copy() for keys, _, _ in population]
    events = []

    class Decisions:
        def choice(self, domain, *, size, replace):
            assert (domain, size, replace) == (3, 3, False)
            events.append('donors')
            return np.array([0, 1, 2])

        def integers(self, n):
            assert n == 3
            events.append('forced')
            return 1

        def random(self, n):
            assert n == 3
            events.append('uniforms')
            return np.array([0.1, 0.9, 0.6])

    donors = [i for i in range(4) if i != target]
    donor = before[donors[0]] + 0.5 * (before[donors[1]] - before[donors[2]])
    mask = np.array([0.1, 0.9, 0.6]) < rate
    mask[1] = True
    trial = de._trial(population, target, 0.5, rate, Decisions())
    np.testing.assert_array_equal(trial, np.where(mask, donor, before[target]))
    assert events == ['donors', 'forced', 'uniforms']
    for (keys, _, _), saved in zip(population, before):
        np.testing.assert_array_equal(keys, saved)
        assert not np.shares_memory(trial, keys)


@pytest.mark.parametrize('limit,generations,partial', [
    (1, 0, PartialIteration('initialization', 1, 4)), (4, 0, None),
    (5, 0, PartialIteration('generation', 1, 4)), (8, 1, None),
    (9, 1, PartialIteration('generation', 1, 4)), (12, 2, None),
])
def test_budget_reservations_and_partial_generations(empty_graph, limit, generations, partial):
    result = solve(empty_graph, budget=Budget(max_evaluations=limit))
    assert result.stop_reason == 'evaluation_limit'
    assert result.counters.evaluations_started == result.counters.evaluations_completed == limit
    assert result.counters.full_evaluations == limit
    assert result.counters.iterations_completed == generations
    assert result.counters.partial_iteration == partial
    assert result.best_cost == 5 and check_route_legality(5, result.best_route).valid


def test_population_is_frozen_and_vector_route_cost_remain_associated(empty_graph, monkeypatch):
    initial = [np.roll(np.arange(5, dtype=float), i) for i in range(4)]
    stream = iter(initial)
    start = de.start_run
    snapshots = []
    trial = np.arange(5, dtype=float)[::-1]
    costs = iter([4, 3, 2, 1, 2, 3, 3, 2, 2, 3, 3, 2])

    def begin(*args, **kwargs):
        run = start(*args, **kwargs)
        run.rng = SimpleNamespace(random=lambda n: next(stream))
        return run

    def propose(population, target, *args):
        snapshots.append([(keys.copy(), route, cost) for keys, route, cost in population])
        return trial.copy()

    monkeypatch.setattr(de, 'start_run', begin)
    monkeypatch.setattr(de, '_trial', propose)
    monkeypatch.setattr(de, 'evaluate_cost', lambda graph, route: next(costs))
    result = solve(empty_graph, budget=Budget(max_iterations=2))
    assert result.counters.iterations_completed == 2
    for snapshot in snapshots[:4]:
        for index, (keys, route, cost) in enumerate(snapshot):
            np.testing.assert_array_equal(keys, initial[index])
            assert route == de.decode_real_keys(5, keys)
            assert cost == [4, 3, 2, 1][index]
    for snapshot in snapshots[4:]:
        for index, (keys, route, cost) in enumerate(snapshot):
            expected = trial if index == 0 else initial[index]
            np.testing.assert_array_equal(keys, expected)
            assert route == de.decode_real_keys(5, keys)
            assert cost == [2, 3, 2, 1][index]
    assert result.best_route == de.decode_real_keys(5, initial[3])
    assert result.best_cost == 1  # A rejected or tied trial cannot replace the first best.


def test_equal_keys_still_consume_all_evaluations(empty_graph, monkeypatch):
    start = de.start_run

    def begin(*args, **kwargs):
        run = start(*args, **kwargs)
        rng = run.rng
        run.rng = SimpleNamespace(random=lambda n: np.zeros(n), choice=rng.choice, integers=rng.integers)
        return run

    monkeypatch.setattr(de, 'start_run', begin)
    result = solve(empty_graph)
    assert result.best_route == tuple(range(5))
    assert result.counters.evaluations_completed == 12
    assert result.counters.iterations_completed == 2
    assert result.counters.cache_hits == result.counters.incremental_evaluations == 0


@pytest.fixture
def zero_trial(monkeypatch):
    start = de.start_run

    def begin(*args, **kwargs):
        run = start(*args, **kwargs)
        run.rng = SimpleNamespace(random=lambda n: np.array([0., 1., 3., 2., 4.]))
        return run

    monkeypatch.setattr(de, 'start_run', begin)
    monkeypatch.setattr(de, '_trial', lambda *args: np.arange(5, dtype=float))


@pytest.mark.parametrize('finish,status', [(9, 'success'), (10, 'success'), (11, 'exhausted')])
def test_last_reservation_and_certification_boundary(example_graph, zero_trial, monkeypatch, finish, status):
    clock = Clock()
    validate = execution.validate_cycle

    def certificate(graph, route):
        result = validate(graph, route)
        clock.now = finish
        return result

    monkeypatch.setattr(execution, 'validate_cycle', certificate)
    result = solve(example_graph, budget=Budget(max_evaluations=5, max_elapsed_ns=10), clock=clock)
    assert result.status == status and result.validation.valid
    assert result.counters.evaluations_completed == 5
    assert result.counters.validations_completed == 1
    assert result.counters.iterations_completed == 0
    assert result.counters.partial_iteration == PartialIteration('generation', 1, 4)
    assert result.success_within_budget == (status == 'success')
    assert (result.timing.first_success is not None) == (status == 'success')
    assert result.timing.overrun_ns == max(0, finish - 10)


@pytest.mark.parametrize('stage,completed', [('trial', 4), ('decode', 4), ('cost', 5)])
def test_timeout_prevents_more_work_and_keeps_partial_phase(empty_graph, monkeypatch, stage, completed):
    clock = Clock()
    trial, decoder, cost_function = de._trial, de.decode_real_keys, de.evaluate_cost
    calls = 0

    def propose(*args):
        keys = trial(*args)
        if stage == 'trial':
            clock.now = 10
        return keys

    def decode(n, keys):
        nonlocal calls
        calls += 1
        route = decoder(n, keys)
        if stage == 'decode' and calls == 5:
            clock.now = 10
        return route

    def cost(graph, route):
        if stage == 'cost' and calls == 5:
            clock.now = 10
        return cost_function(graph, route)

    monkeypatch.setattr(de, '_trial', propose)
    monkeypatch.setattr(de, 'decode_real_keys', decode)
    monkeypatch.setattr(de, 'evaluate_cost', cost)
    result = solve(empty_graph, budget=Budget(max_elapsed_ns=10), clock=clock)
    assert result.stop_reason == 'time_limit'
    assert result.counters.evaluations_completed == completed
    assert result.counters.iterations_completed == 0
    assert result.counters.partial_iteration == PartialIteration('generation', completed - 4, 4)


def test_nonfinite_state_before_decoding_is_reported_with_previous_best(empty_graph, monkeypatch):
    maximum = np.finfo(np.float64).max
    start = de.start_run
    values = iter([np.arange(5, dtype=float), np.arange(5, dtype=float),
                   np.array([maximum, 0, 1, 2, 3.]),
                   np.array([-maximum, 0, 1, 2, 3.])])

    def begin(*args, **kwargs):
        run = start(*args, **kwargs)
        run.rng = SimpleNamespace(random=lambda n: next(values),
                                  choice=lambda *args, **kwargs: np.array([0, 1, 2]))
        return run

    monkeypatch.setattr(de, 'start_run', begin)
    result = solve(empty_graph)
    assert result.stop_reason == 'non_finite_state'
    assert result.error.code == 'non_finite_state'
    assert result.counters.evaluations_started == result.counters.evaluations_completed == 4
    assert result.best_cost == 5 and result.validation.valid is None


def test_nonfinite_decoder_context_has_position(empty_graph, monkeypatch):
    monkeypatch.setattr(de, '_trial', lambda *args: np.array([0., float('nan'), 2, 3, 4]))
    result = solve(empty_graph)
    assert result.stop_reason == 'non_finite_state'
    assert result.error.detail == {'position': 1}
    assert result.counters.evaluations_started == 4


def test_real_de_finds_synthetic_cycle_and_is_reproducible():
    graph = Graph(range(5), [(i, (i + 1) % 5) for i in range(5)])
    first = solve(graph, budget=Budget(max_evaluations=500), seed=42)
    repeated = solve(graph, budget=Budget(max_evaluations=500), seed=42)
    assert first.status == 'success' and first.best_cost == 0
    assert 4 < first.counters.evaluations_completed <= 500
    assert first.counters.iterations_completed > 0
    assert validate_cycle(graph, first.best_route).valid
    a, b = asdict(first), asdict(repeated)
    a.pop('timing')
    b.pop('timing')
    assert a == b


@pytest.mark.parametrize('seed', [0, 53, 2**64 - 1])
def test_reproduction_includes_trajectory_and_global_rng_isolation(empty_graph, monkeypatch, seed):
    state = np.random.get_state()
    traces, results = [], []
    cost_function = de.evaluate_cost

    def cost(graph, route):
        traces[-1].append(route)
        return cost_function(graph, route)

    monkeypatch.setattr(de, 'evaluate_cost', cost)
    for run_seed in (seed, (seed + 1) % 2**64, seed):
        traces.append([])
        results.append(solve(empty_graph, seed=run_seed, budget=Budget(max_evaluations=16)))
    assert traces[0] == traces[2] and traces[0] != traces[1]
    first, repeated = asdict(results[0]), asdict(results[2])
    first.pop('timing')
    repeated.pop('timing')
    assert first == repeated
    after = np.random.get_state()
    assert state[0] == after[0] and state[2:] == after[2:]
    np.testing.assert_array_equal(state[1], after[1])


def test_underflow_rounds_to_finite_keys_and_restores_numpy_policy():
    population = [(np.array([i * 0.1, i * 0.2, i * 0.3]), (0, 1, 2), 3) for i in range(4)]
    rng = np.random.Generator(np.random.PCG64(53))
    with np.errstate(under='raise'):
        trial = de._trial(population, 0, 5e-324, 1, rng)
        assert np.isfinite(trial).all()
        assert np.geterr()['under'] == 'raise'


def test_zero_cost_cannot_start_validation_at_exact_time_limit(example_graph, zero_trial, monkeypatch):
    clock = Clock()
    cost_function = de.evaluate_cost

    def cost(graph, route):
        value = cost_function(graph, route)
        if value == 0:
            clock.now = 10
        return value

    monkeypatch.setattr(de, 'evaluate_cost', cost)
    monkeypatch.setattr(execution, 'validate_cycle', unexpected)
    result = solve(example_graph, budget=Budget(max_elapsed_ns=10, max_evaluations=5), clock=clock)
    assert result.stop_reason == 'time_limit'
    assert result.best_cost == 0 and result.validation.reason == 'not_run'
    assert result.counters.validations_started == 0
    assert result.timing.first_success is None


def test_fitness_mismatch_uses_independent_validator(empty_graph, monkeypatch):
    monkeypatch.setattr(de, 'evaluate_cost', lambda graph, route: 0)
    result = solve(empty_graph, budget=Budget(max_evaluations=1))
    assert result.stop_reason == 'fitness_validation_mismatch'
    assert result.validation.valid is False
    assert result.counters.validations_completed == 1
    assert result.timing.first_success is None


def test_runtime_error_preserves_best_and_partial_work(empty_graph, monkeypatch):
    def broken(*args):
        raise RuntimeError('This private message must not appear in the result.')

    monkeypatch.setattr(de, '_trial', broken)
    result = solve(empty_graph)
    assert result.stop_reason == 'runtime_error'
    assert result.error.code == 'RuntimeError'
    assert 'private message' not in result.error.message
    assert result.best_cost == 5
    assert result.counters.evaluations_completed == 4
    assert result.counters.partial_iteration == PartialIteration('generation', 0, 4)
