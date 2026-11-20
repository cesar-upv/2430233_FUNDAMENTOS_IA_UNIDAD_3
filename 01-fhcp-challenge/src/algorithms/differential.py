"""Synchronous DE/rand/1/bin on real keys and the common solver runtime."""

from collections.abc import Callable, Mapping
from math import isfinite
from time import perf_counter_ns
from typing import cast

import numpy as np

from src.evaluation import evaluate_cost
from src.graphs import Graph

from .graph_guidance import greedy_keys, resolve_search_options
from .execution import Budget, Counters, SolverError, SolverResult, SolverRun, Timing, start_run
from .real_keys import KeyDecodingError, decode_real_keys

DE_VARIANT = "rand_1_bin_real_keys_v1"

type Individual = tuple[np.ndarray, tuple[int, ...], int]


class DEConfigurationError(ValueError):
    """Rejected DE parameter, with a stable code and field name."""

    def __init__(self, code: str, parameter: str | None, message: str):
        self.code = code
        self.parameter = parameter
        super().__init__(message)


def resolve_de_parameters(parameters: Mapping[str, object]) -> dict[str, int | float]:
    """Validate and copy the three required parameters, without experimental defaults."""
    if not isinstance(parameters, Mapping):
        raise DEConfigurationError("invalid_parameters", None, "Parameters must be a mapping.")
    values = dict(parameters)
    names = ("population_size", "differential_weight", "crossover_rate")
    if any(not isinstance(key, str) for key in values):
        raise DEConfigurationError("invalid_parameters", None, "Parameter names must be strings.")
    unknown = sorted(values.keys() - (set(names) | {"initialization"}))
    if unknown:
        raise DEConfigurationError("unknown_parameter", unknown[0], "Unknown DE parameter.")
    for name in names:
        if name not in values:
            raise DEConfigurationError("missing_parameter", name, "Missing required DE parameter.")
    size = values["population_size"]
    if type(size) is not int or size < 4:
        raise DEConfigurationError("invalid_parameter", "population_size", "Population size must be an integer >= 4.")
    effective: dict[str, int | float] = {"population_size": size}
    for name in names[1:]:
        value = values[name]
        if type(value) not in (int, float):
            raise DEConfigurationError("invalid_parameter", name, "Expected a finite Python number.")
        try:
            number = float(value)
        except OverflowError:
            raise DEConfigurationError("invalid_parameter", name, "Number exceeds the float range.") from None
        if not isfinite(number):
            raise DEConfigurationError("invalid_parameter", name, "Expected a finite Python number.")
        effective[name] = number
    if effective["differential_weight"] <= 0:
        raise DEConfigurationError("invalid_parameter", "differential_weight", "Differential weight must be positive.")
    if not 0 <= effective["crossover_rate"] <= 1:
        raise DEConfigurationError("invalid_parameter", "crossover_rate", "Crossover rate must be in [0, 1].")
    effective.update(resolve_search_options(values, DEConfigurationError, moves=False))
    return effective


def _trial(
    population: list[Individual], target: int, weight: float, rate: float,
    rng: np.random.Generator,
) -> np.ndarray:
    # Sample from a compressed index domain, then skip the target index.
    indices = rng.choice(len(population) - 1, size=3, replace=False)
    a, b, c = (int(index) + int(index >= target) for index in indices)
    with np.errstate(over="raise", invalid="raise", under="ignore"):
        donor = population[a][0] + weight * (population[b][0] - population[c][0])
    n = len(donor)
    forced = int(rng.integers(n))
    mask = rng.random(n) < rate
    mask[forced] = True
    return np.where(mask, donor, population[target][0])


def _search(graph: Graph, parameters: dict[str, int | float], run: SolverRun) -> SolverResult:
    size = cast(int, parameters["population_size"])
    weight = float(parameters["differential_weight"])
    rate = float(parameters["crossover_rate"])
    n = graph.vertex_count()
    population: list[Individual] = []
    if not run.begin_phase("initialization", size):
        return run.finish()
    for _ in range(size):
        if not run.checkpoint():
            return run.finish()
        keys = (greedy_keys(graph, run) if parameters.get("initialization") == "greedy"
                    else run.rng.random(n))
        if keys is None:
            return run.finish()
        if not run.checkpoint():
            return run.finish()
        route = decode_real_keys(n, keys)
        cost = run.evaluate(route, evaluate_cost)
        if cost is None:
            return run.finish()
        population.append((keys.copy(), route, cost))
        run.record_item()
        if cost == 0:
            return run.certify_best()
    run.complete_phase()

    while run.begin_phase("generation", size, iteration=True):
        next_population = list(population)
        for target in range(size):
            if not run.checkpoint():
                return run.finish()
            keys = _trial(population, target, weight, rate, run.rng)
            if not run.checkpoint():
                return run.finish()
            route = decode_real_keys(n, keys)
            cost = run.evaluate(route, evaluate_cost)
            if cost is None:
                return run.finish()
            run.record_item()
            if cost == 0:
                return run.certify_best()
            # An admitted trial may finish selection after its last reservation.
            if run.time_expired():
                return run.finish()
            if cost < population[target][2]:
                next_population[target] = (keys.copy(), route, cost)
        if run.time_expired():
            return run.finish()
        population = next_population
        run.complete_phase()
    return run.finish()


def solve_de(
    graph: Graph, *, parameters: Mapping[str, object], seed: int, budget: Budget,
    clock: Callable[[], int] = perf_counter_ns,
) -> SolverResult:
    """Run DE_VARIANT with finite float64 keys, strict improvement and private PCG64."""
    try:
        effective = resolve_de_parameters(parameters)
    except DEConfigurationError as error:
        limit = budget.max_elapsed_ns if isinstance(budget, Budget) else None
        timed = type(limit) is int and limit > 0
        return SolverResult(
            "error", "invalid_config", Counters("generation"),
            Timing(overrun_ns=0 if timed else None),
            error=SolverError(error.code, str(error), "input", {"parameter": error.parameter}),
        )
    run = start_run(graph, seed=seed, budget=budget, iteration_unit="generation", clock=clock)
    if isinstance(run, SolverResult):
        return run
    try:
        return _search(graph, effective, run)
    except KeyDecodingError as error:
        reason = "non_finite_state" if error.code == "non_finite_state" else "runtime_error"
        return run.fail(reason, error.code, "DE key decoding failed.", position=error.position)
    except FloatingPointError:
        return run.fail("non_finite_state", "non_finite_state", "DE arithmetic overflowed or produced an invalid value.")
    except Exception as error:
        return run.fail("runtime_error", type(error).__name__, "DE failed during execution.")
