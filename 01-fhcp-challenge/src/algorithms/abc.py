"""Sequential Artificial Bee Colony on permutations, with common execution control."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import fsum
from time import perf_counter_ns

import numpy as np

from src.evaluation import evaluate_cost
from src.graphs import Graph, GraphError
from .graph_guidance import greedy_route, guided_inversion, resolve_search_options
from .local_moves import RouteMove, guided_move, resolve_cost_options
from .execution import Budget, Counters, SolverError, SolverResult, SolverRun, Timing, start_run
from .permutation import initialize_route

ABC_VARIANT = "sequential_partner_swap_v1"


class ABCConfigurationError(ValueError):
    """Invalid variant parameter, rejected before clock or RNG creation."""

    def __init__(self, code: str, parameter: str | None, message: str):
        self.code = code
        self.parameter = parameter
        super().__init__(message)


def resolve_abc_parameters(parameters: Mapping[str, object]) -> dict[str, int]:
    """Copy and validate required source_count >= 2 and limit >= 1."""
    if not isinstance(parameters, Mapping) or any(type(k) is not str for k in parameters):
        raise ABCConfigurationError("invalid_parameters", None, "Parameters must be a string-keyed mapping.")
    values = dict(parameters)
    unknown = sorted(values.keys() - {"source_count", "limit", "initialization", "guided_move_rate", "cost_mode", "incremental_check_interval"})
    if unknown:
        raise ABCConfigurationError("unknown_parameter", unknown[0], "Unknown ABC parameter.")
    for name, minimum in (("source_count", 2), ("limit", 1)):
        if name not in values:
            raise ABCConfigurationError("missing_parameter", name, "Missing ABC parameter.")
        if type(values[name]) is not int or values[name] < minimum:
            raise ABCConfigurationError("invalid_parameter", name, f"Expected a Python integer >= {minimum}.")
    return {"source_count": values["source_count"], "limit": values["limit"],
            **resolve_search_options(values, ABCConfigurationError, moves=True),
            **resolve_cost_options(values, ABCConfigurationError)}


@dataclass(slots=True)
class _Source:
    route: tuple[int, ...]
    cost: int
    trials: int = 0


def _partner_index(index: int, size: int, rng: np.random.Generator) -> int:
    partner = int(rng.integers(size - 1))
    return partner + (partner >= index)


def _guided_neighbor(route: tuple[int, ...], partner: tuple[int, ...], rng: np.random.Generator) -> tuple[int, ...]:
    different = [i for i, (u, v) in enumerate(zip(route, partner)) if u != v]
    if different:
        first = different[int(rng.integers(len(different)))]
        second = route.index(partner[first])
    else:
        first, second = (int(i) for i in rng.choice(len(route), size=2, replace=False))
    child = list(route)
    child[first], child[second] = child[second], child[first]
    return tuple(child)


def _accept(source: _Source, route: tuple[int, ...], cost: int) -> None:
    if cost < source.cost:
        source.route, source.cost, source.trials = route, cost, 0
    else:
        source.trials += 1


def _onlooker_weights(sources: list[_Source]) -> tuple[float, ...]:
    weights = tuple(1.0 / (1 + source.cost) for source in sources)
    total = fsum(weights)
    return tuple(weight / total for weight in weights)


def _scout_index(sources: list[_Source], limit: int) -> int | None:
    candidates = (i for i, source in enumerate(sources) if source.trials >= limit)
    return min(candidates, key=lambda i: (-sources[i].trials, i), default=None)


def _proposal(index: int, sources: list[_Source], run: SolverRun, phase: str, graph: Graph, rate: float, check_interval: int | None = None) -> bool:
    if not run.checkpoint():
        return False
    if check_interval is not None:
        source = sources[index]
        if rate > 0 and run.rng.random() < rate:
            move = guided_move(graph, source.route, run)
            if move is None:
                return False
        else:
            partner = sources[_partner_index(index, len(sources), run.rng)].route
            different = [i for i, (u, v) in enumerate(zip(source.route, partner)) if u != v]
            if different:
                first = different[int(run.rng.integers(len(different)))]
                second = source.route.index(partner[first])
            else:
                first, second = (int(i) for i in run.rng.choice(len(source.route), size=2, replace=False))
            move = RouteMove("swap", first, second)
        route = move.apply(source.route)
        cost = run.evaluate_incremental(
            route, lambda g, candidate: move.cost_after(g, source.route, source.cost),
            check_interval=check_interval,
        )
    else:
        if rate > 0 and run.rng.random() < rate:
            route = guided_inversion(graph, sources[index].route, run)
            if route is None:
                return False
        else:
            partner = _partner_index(index, len(sources), run.rng)
            route = _guided_neighbor(sources[index].route, sources[partner].route, run.rng)
        cost = run.evaluate(route, evaluate_cost)
    if cost is None:
        return False
    improved = cost < sources[index].cost
    _accept(sources[index], route, cost)
    run.count(f"{phase}_proposals")
    if improved:
        run.count(f"{phase}_improvements")
    run.record_item()
    if cost == 0:
        run.certify_best()
        return False
    return True


def _search(graph: Graph, parameters: dict[str, int], run: SolverRun) -> SolverResult:
    size, limit = parameters["source_count"], parameters["limit"]
    check_interval = parameters.get("incremental_check_interval") if parameters.get("cost_mode") == "incremental" else None
    sources: list[_Source] = []
    if not run.begin_phase("initialization", size):
        return run.finish()
    for _ in range(size):
        if not run.checkpoint():
            return run.finish()
        route = (greedy_route(graph, run) if parameters.get("initialization") == "greedy"
                 else initialize_route(graph.vertex_count(), run.rng))
        if route is None:
            return run.finish()
        cost = run.evaluate(route, evaluate_cost)
        if cost is None:
            return run.finish()
        sources.append(_Source(route, cost))
        run.record_item()
        if cost == 0:
            return run.certify_best()
    if run.time_expired():
        return run.finish()
    run.complete_phase()

    # One composite phase counts a cycle only after its scout decision finishes.
    # Items 0..S-1: employed; S..2S-1: onlookers; item 2S: scout decision.
    while run.begin_phase("abc_cycle", 2 * size + 1, iteration=True):
        for index in range(size):
            if not _proposal(index, sources, run, "employed", graph, parameters.get("guided_move_rate", 0), check_interval):
                return run.finish()
        if not run.checkpoint():
            return run.finish()
        probabilities = _onlooker_weights(sources)
        for _ in range(size):
            if not run.checkpoint():
                return run.finish()
            index = int(run.rng.choice(size, p=probabilities))
            if not _proposal(index, sources, run, "onlooker", graph, parameters.get("guided_move_rate", 0), check_interval):
                return run.finish()
        if run.time_expired():
            return run.finish()
        expired = _scout_index(sources, limit)
        if expired is not None:
            if not run.checkpoint():
                return run.finish()
            run.count("scout_abandonments")
            route = (greedy_route(graph, run) if parameters.get("initialization") == "greedy"
                     else initialize_route(graph.vertex_count(), run.rng))
            if route is None:
                return run.finish()
            cost = run.evaluate(route, evaluate_cost)
            if cost is None:
                return run.finish()
            sources[expired] = _Source(route, cost)
            run.count("scout_renewals")
            run.record_restart()
            run.record_item()
            if cost == 0:
                return run.certify_best()
        else:
            run.count("scout_skips")
            run.record_item()
        if run.time_expired():
            return run.finish()
        run.complete_phase()
    return run.finish()


def solve_abc(
    graph: Graph, *, parameters: Mapping[str, object], seed: int, budget: Budget,
    clock: Callable[[], int] = perf_counter_ns,
) -> SolverResult:
    """Run ABC with S employed proposals, S onlookers and at most one scout.

    Private PCG64, frozen onlooker weights, strict improvement and preserved
    historical best; no CLI, dataset, official certificates or global RNG.
    """
    try:
        effective = resolve_abc_parameters(parameters)
    except ABCConfigurationError as error:
        time_limit = budget.max_elapsed_ns if isinstance(budget, Budget) else None
        timed = type(time_limit) is int and time_limit > 0
        return SolverResult(
            "error", "invalid_config", Counters("abc_cycle"),
            Timing(overrun_ns=0 if timed else None),
            error=SolverError(error.code, str(error), "input", {"parameter": error.parameter}),
        )
    run = start_run(graph, seed=seed, budget=budget, iteration_unit="abc_cycle", clock=clock)
    if isinstance(run, SolverResult):
        return run
    try:
        return _search(graph, effective, run)
    except GraphError as error:
        return run.fail("invalid_candidate", error.code, "An ABC operator rejected a candidate.")
    except Exception as error:
        return run.fail("runtime_error", type(error).__name__, "ABC failed during execution.")
