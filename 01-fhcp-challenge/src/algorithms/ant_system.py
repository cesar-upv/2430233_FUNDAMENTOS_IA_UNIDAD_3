"""Ant System with missing-pair penalties and packed undirected pheromone."""

from collections.abc import Callable, Iterator, Mapping
from math import fsum, isfinite, log
from time import perf_counter_ns
from typing import cast

import numpy as np

from src.evaluation import evaluate_cost
from src.graphs import Graph

from .graph_guidance import resolve_search_options
from .sparse_pheromone import EdgePheromone, initialize_sparse
from .execution import Budget, Counters, SolverError, SolverResult, SolverRun, Timing, start_run

AS_VARIANT = "ant_system_missing_pairs_v1"
_PHEROMONE_BLOCK = 65_536
_CANDIDATE_BLOCK = 256
_PARAMETERS = (
    "ant_count", "alpha", "beta", "rho", "q", "epsilon",
    "initial_pheromone", "pheromone_min", "pheromone_max",
)

type Tour = tuple[tuple[int, ...], int]


class ASConfigurationError(ValueError):
    """Rejected AS configuration, with a stable code and affected field."""

    def __init__(self, code: str, parameter: str | None, message: str):
        self.code = code
        self.parameter = parameter
        super().__init__(message)


def resolve_as_parameters(parameters: Mapping[str, object]) -> dict[str, int | float]:
    """Copy all nine explicit parameters, rejecting coercions and nonfinite values."""
    if not isinstance(parameters, Mapping):
        raise ASConfigurationError("invalid_parameters", None, "Parameters must be a mapping.")
    values = dict(parameters)
    if any(not isinstance(key, str) for key in values):
        raise ASConfigurationError("invalid_parameters", None, "Parameter names must be strings.")
    unknown = sorted(values.keys() - (set(_PARAMETERS) | {"construction", "pheromone_storage"}))
    if unknown:
        raise ASConfigurationError("unknown_parameter", unknown[0], "Unknown Ant System parameter.")
    for name in _PARAMETERS:
        if name not in values:
            raise ASConfigurationError("missing_parameter", name, "Missing required Ant System parameter.")
    size = values["ant_count"]
    if type(size) is not int or size < 1:
        raise ASConfigurationError("invalid_parameter", "ant_count", "Ant count must be a Python integer >= 1.")
    effective: dict[str, int | float] = {"ant_count": size}
    for name in _PARAMETERS[1:]:
        value = values[name]
        if type(value) not in (int, float):
            raise ASConfigurationError("invalid_parameter", name, "Expected a finite Python number.")
        try:
            number = float(value)
        except OverflowError:
            raise ASConfigurationError("invalid_parameter", name, "Number exceeds the float range.") from None
        if not isfinite(number):
            raise ASConfigurationError("invalid_parameter", name, "Expected a finite Python number.")
        if name in ("alpha", "beta"):
            valid = number >= 0
        elif name in ("rho", "epsilon"):
            valid = 0 < number < 1
        else:
            valid = number > 0
        if not valid:
            raise ASConfigurationError("invalid_parameter", name, "Parameter is outside its declared range.")
        effective[name] = number
    if effective["pheromone_min"] > effective["pheromone_max"]:
        raise ASConfigurationError("invalid_parameter", "pheromone_max", "Maximum pheromone is below minimum.")
    if not effective["pheromone_min"] <= effective["initial_pheromone"] <= effective["pheromone_max"]:
        raise ASConfigurationError("invalid_parameter", "initial_pheromone", "Initial pheromone is outside the bounds.")
    effective.update(resolve_search_options(values, ASConfigurationError, construction=True))
    if "pheromone_storage" in values:
        storage = values["pheromone_storage"]
        if type(storage) is not str or storage not in ("all_pairs", "edges"):
            raise ASConfigurationError("invalid_parameter", "pheromone_storage", "Expected all_pairs or edges.")
        effective["pheromone_storage"] = storage
    return effective


def _pair_index(n: int, u: int, v: int) -> int:
    u, v = int(u), int(v)
    if not (0 <= u < n and 0 <= v < n) or u == v:
        raise ValueError("Pheromone requires two distinct internal vertices.")
    if u > v:
        u, v = v, u
    return u * (2 * n - u - 1) // 2 + v - u - 1


def _blocks(length: int) -> Iterator[tuple[int, int]]:
    for start in range(0, length, _PHEROMONE_BLOCK):
        yield start, min(start + _PHEROMONE_BLOCK, length)


def _allocate_pheromone(n: int) -> np.ndarray:
    pairs = n * (n - 1) // 2
    if pairs > np.iinfo(np.intp).max // np.dtype(np.float64).itemsize:
        raise MemoryError("Packed pheromone exceeds the addressable array size.")
    return np.empty(pairs, dtype=np.float64)


def _initialize(n: int, value: float, run: SolverRun) -> np.ndarray | None:
    pairs = n * (n - 1) // 2
    blocks = (pairs + _PHEROMONE_BLOCK - 1) // _PHEROMONE_BLOCK
    if not run.begin_phase("initialization", blocks):
        return None
    pheromone = _allocate_pheromone(n)
    for start, stop in _blocks(pairs):
        if not run.checkpoint():
            return None
        pheromone[start:stop].fill(value)
        run.record_item()
    if not run.checkpoint():
        return None
    run.complete_phase()
    return pheromone


class _TransitionError(ValueError):
    """A finite but unusable transition distribution; never repair it silently."""


def _normalize_log_weights(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        raise _TransitionError("No transition candidates.")
    if not np.isfinite(scores).all():
        raise FloatingPointError("Nonfinite transition score.")
    with np.errstate(over="raise", invalid="raise", under="ignore"):
        weights = np.exp(scores - np.max(scores))
        total = fsum(float(value) for value in weights)
        if not isfinite(total) or total <= 0:
            raise _TransitionError("Invalid transition weight sum.")
        probabilities = weights / total
    if not np.isfinite(probabilities).all() or np.any(probabilities < 0):
        raise _TransitionError("Invalid transition probabilities.")
    return probabilities


def _probabilities(
    graph: Graph, pheromone: np.ndarray, current: int, candidates: np.ndarray,
    parameters: dict[str, int | float], run: SolverRun, remaining_degrees=None,
) -> np.ndarray | None:
    scores = np.empty(len(candidates), dtype=np.float64)
    penalty = log(parameters["epsilon"])
    n = graph.vertex_count()
    for start in range(0, len(candidates), _CANDIDATE_BLOCK):
        if not run.checkpoint():
            return None
        for index in range(start, min(start + _CANDIDATE_BLOCK, len(candidates))):
            vertex = int(candidates[index])
            tau = (pheromone.value(current, vertex) if isinstance(pheromone, EdgePheromone)
                   else float(pheromone[_pair_index(n, current, vertex)]))
            if not isfinite(tau) or tau <= 0:
                raise FloatingPointError("Nonpositive or nonfinite pheromone.")
            visibility = (-log(1 + remaining_degrees[vertex]) if remaining_degrees is not None
                          else (0.0 if graph.has_edge(current, vertex) else penalty))
            score = parameters["alpha"] * log(tau) + parameters["beta"] * visibility
            if not isfinite(score):
                raise FloatingPointError("Nonfinite transition score.")
            scores[index] = score
    if not run.checkpoint():
        return None
    return _normalize_log_weights(scores)


def _construct(
    graph: Graph, pheromone: np.ndarray, parameters: dict[str, int | float], run: SolverRun,
) -> tuple[int, ...] | None:
    if not run.checkpoint():
        return None
    run.count("constructions_started")
    n = graph.vertex_count()
    guided = parameters.get("construction") == "neighbor_guided"
    free = [] if guided else None
    if guided:
        for vertex in range(n):
            if not run.checkpoint():
                return None
            free.append(graph.degree(vertex))
    first = int(run.rng.integers(n))
    route = [first]
    visited = np.zeros(n, dtype=bool)
    visited[first] = True
    while len(route) < n:
        if not run.checkpoint():
            return None
        if guided:
            candidates = []
            for neighbor in graph.neighbors(route[-1]):
                if not run.checkpoint():
                    return None
                neighbor = int(neighbor)
                free[neighbor] -= 1
                if not visited[neighbor]:
                    candidates.append(neighbor)
            if candidates:
                candidates = np.asarray(candidates, dtype=np.intp)
                probabilities = _probabilities(graph, pheromone, route[-1], candidates, parameters, run, free)
            else:
                # Blocked: keep a full permutation, recording a non-edge jump.
                candidates = np.flatnonzero(~visited)
                probabilities = np.full(len(candidates), 1.0 / len(candidates))
                run.count("neighbor_guided_jumps")
        else:
            candidates = np.flatnonzero(~visited)
            probabilities = _probabilities(graph, pheromone, route[-1], candidates, parameters, run)
        if probabilities is None or not run.checkpoint():
            return None
        vertex = int(run.rng.choice(candidates, p=probabilities))
        route.append(vertex)
        visited[vertex] = True
        run.count("construction_steps")
    return tuple(route)


def _deposit_value(current: float, increment: float, upper: float) -> float:
    # Positive additions can saturate early at the upper bound. Do not apply
    # the lower bound until all deposits; that would change the update rule.
    return upper if increment >= upper - current else min(upper, current + increment)


def _update_pheromone(
    n: int, pheromone: np.ndarray, tours: list[Tour],
    parameters: dict[str, int | float], run: SolverRun,
) -> bool:
    # Updating pheromone is new work, unlike finishing one admitted evaluation.
    if not run.checkpoint():
        return False
    run.count("pheromone_updates_started")
    values = pheromone.values if isinstance(pheromone, EdgePheromone) else pheromone
    with np.errstate(over="raise", invalid="raise", under="ignore"):
        for start, stop in _blocks(len(values)):
            if not run.checkpoint():
                return False
            block = values[start:stop]
            np.multiply(block, 1 - parameters["rho"], out=block)
            if not np.isfinite(block).all():
                raise FloatingPointError("Nonfinite evaporated pheromone.")
        for route, cost in tours:
            increment = parameters["q"] / (1 + cost)
            for position, u in enumerate(route):
                if not run.checkpoint():
                    return False
                v = route[(position + 1) % n]
                index = (pheromone.index(u, v) if isinstance(pheromone, EdgePheromone)
                         else _pair_index(n, u, v))
                if index is None:
                    run.count("pheromone_missing_deposits_skipped")
                    continue
                values[index] = _deposit_value(
                    float(values[index]), increment, parameters["pheromone_max"],
                )
                run.count("pheromone_deposits")
        for start, stop in _blocks(len(values)):
            if not run.checkpoint():
                return False
            np.clip(values[start:stop], parameters["pheromone_min"],
                    parameters["pheromone_max"], out=values[start:stop])
    if not run.checkpoint():
        return False
    run.count("pheromone_updates_completed")
    return True


def _search(graph: Graph, parameters: dict[str, int | float], run: SolverRun) -> SolverResult:
    count = cast(int, parameters["ant_count"])
    n = graph.vertex_count()
    pheromone = (initialize_sparse(graph, parameters["initial_pheromone"], parameters["pheromone_min"], run)
                 if parameters.get("pheromone_storage") == "edges"
                 else _initialize(n, parameters["initial_pheromone"], run))
    if pheromone is None:
        return run.finish()
    while run.begin_phase("round", count + 1, iteration=True):
        tours: list[Tour] = []
        for _ in range(count):
            route = _construct(graph, pheromone, parameters, run)
            if route is None:
                return run.finish()
            cost = run.evaluate(route, evaluate_cost)
            if cost is None:
                return run.finish()
            tours.append((route, cost))
            run.record_item()
            if cost == 0:
                return run.certify_best()
        if not _update_pheromone(n, pheromone, tours, parameters, run):
            return run.finish()
        run.record_item()
        run.complete_phase()
    return run.finish()


def solve_as(
    graph: Graph, *, parameters: Mapping[str, object], seed: int, budget: Budget,
    clock: Callable[[], int] = perf_counter_ns,
) -> SolverResult:
    """Run AS_VARIANT with private PCG64 and independent zero-cost certification.

    Pheromone is packed float64; initialization and updates are cooperative.
    Every unvisited vertex remains a candidate, including missing graph pairs.
    Configuration is explicit; no files, global RNG or solver caches are used.
    """
    try:
        effective = resolve_as_parameters(parameters)
    except ASConfigurationError as error:
        limit = budget.max_elapsed_ns if isinstance(budget, Budget) else None
        timed = type(limit) is int and limit > 0
        return SolverResult(
            "error", "invalid_config", Counters("round"),
            Timing(overrun_ns=0 if timed else None),
            error=SolverError(error.code, str(error), "input", {"parameter": error.parameter}),
        )
    run = start_run(graph, seed=seed, budget=budget, iteration_unit="round", clock=clock)
    if isinstance(run, SolverResult):
        return run
    try:
        return _search(graph, effective, run)
    except MemoryError:
        n = graph.vertex_count()
        return run.fail("runtime_error", "allocation_failed", "Ant System could not allocate its state.",
                        pheromone_bytes=(graph.edge_count() if effective.get("pheromone_storage") == "edges"
                                         else n * (n - 1) // 2) * 8)
    except FloatingPointError:
        return run.fail("non_finite_state", "non_finite_state", "Ant System encountered invalid numeric state.")
    except _TransitionError:
        return run.fail("runtime_error", "invalid_transition_weights", "Ant System could not normalize transition weights.")
    except Exception as error:
        return run.fail("runtime_error", type(error).__name__, "Ant System failed during execution.")
