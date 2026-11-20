"""Sequential generational GA on permutations, using the #19 execution API."""

from collections.abc import Callable, Mapping
from time import perf_counter_ns
from typing import cast

from src.evaluation import evaluate_cost
from src.graphs import Graph, GraphError

from .graph_guidance import greedy_route, guided_inversion, resolve_search_options
from .execution import Budget, Counters, SolverError, SolverResult, SolverRun, Timing, start_run
from .permutation import initialize_route, order_crossover, swap_mutation

GA_VARIANT = "generational_ox_swap_v1"

type Individual = tuple[tuple[int, ...], int]


class GAConfigurationError(ValueError):
    """Rejected GA configuration, with a stable code and affected parameter."""

    def __init__(self, code: str, parameter: str | None, message: str):
        self.code = code
        self.parameter = parameter
        super().__init__(message)


def resolve_ga_parameters(parameters: Mapping[str, object]) -> dict[str, int | float]:
    """Copy, validate and expand the five effective parameters before a run.

    population_size and tournament_size are required. Rates default to 0.8
    and 0.010; elite_count defaults to max(1, population_size // 100).
    An explicit elite_count, including zero, overrides the percentage rule.
    Python integers are strict; rates accept Python int/float except bool.
    """
    if not isinstance(parameters, Mapping):
        raise GAConfigurationError("invalid_parameters", None, "Parameters must be a mapping.")
    values = dict(parameters)
    allowed = {"population_size", "tournament_size", "crossover_rate", "mutation_rate", "elite_count", "initialization", "guided_move_rate"}
    if any(not isinstance(key, str) for key in values):
        raise GAConfigurationError("invalid_parameters", None, "Parameter names must be strings.")
    unknown = sorted(values.keys() - allowed)
    if unknown:
        raise GAConfigurationError("unknown_parameter", unknown[0], "Unknown GA parameter.")
    for name in ("population_size", "tournament_size"):
        if name not in values:
            raise GAConfigurationError("missing_parameter", name, "Missing required GA parameter.")

    size = values["population_size"]
    if type(size) is not int or size < 2:
        raise GAConfigurationError("invalid_parameter", "population_size", "Population size must be an integer >= 2.")
    tournament = values["tournament_size"]
    if type(tournament) is not int or not 1 <= tournament <= size:
        raise GAConfigurationError("invalid_parameter", "tournament_size", "Tournament size must be an integer in [1, population_size].")
    rates = {}
    for name, default in (("crossover_rate", 0.8), ("mutation_rate", 0.010)):
        value = values.get(name, default)
        # The closed interval rejects NaN and infinities before float conversion.
        if type(value) not in (int, float) or not 0 <= value <= 1:
            raise GAConfigurationError("invalid_parameter", name, "Rate must be a finite Python number in [0, 1].")
        rates[name] = float(value)
    elites = values.get("elite_count", max(1, size // 100))
    if type(elites) is not int or not 0 <= elites < size:
        raise GAConfigurationError("invalid_parameter", "elite_count", "Elite count must be an integer in [0, population_size - 1].")
    return {"population_size": size, "tournament_size": tournament, **rates, "elite_count": elites,
            **resolve_search_options(values, GAConfigurationError, moves=True)}


def _tournament(population: list[Individual], size: int, run: SolverRun) -> tuple[int, ...]:
    indices = run.rng.choice(len(population), size=size, replace=False)
    winner = min((int(index) for index in indices), key=lambda i: (population[i][1], i))
    return population[winner][0]


def _search(graph: Graph, parameters: dict[str, int | float], run: SolverRun) -> SolverResult:
    # The resolver has already checked these strict integer fields.
    population_size = cast(int, parameters["population_size"])
    tournament_size = cast(int, parameters["tournament_size"])
    elite_count = cast(int, parameters["elite_count"])
    population: list[Individual] = []
    if not run.begin_phase("initialization", population_size):
        return run.finish()
    for _ in range(population_size):
        if not run.checkpoint():
            return run.finish()
        route = (greedy_route(graph, run) if parameters.get("initialization") == "greedy"
                 else initialize_route(graph.vertex_count(), run.rng))
        if route is None:
            return run.finish()
        cost = run.evaluate(route, evaluate_cost)
        if cost is None:
            return run.finish()
        population.append((tuple(route), cost))
        run.record_item()
        if cost == 0:
            return run.certify_best()
    run.complete_phase()

    children = population_size - elite_count
    while run.begin_phase("generation", children, iteration=True):
        # Stable sorting preserves population order for elite ties.
        elites = sorted(population, key=lambda individual: individual[1])[:elite_count] if elite_count else []
        next_population: list[Individual] = []
        for route, cost in elites:
            if not run.checkpoint():
                return run.finish()
            next_population.append((tuple(vertex for vertex in route), cost))

        for _ in range(children):
            if not run.checkpoint():
                return run.finish()
            first = _tournament(population, tournament_size, run)
            if not run.checkpoint():
                return run.finish()
            second = _tournament(population, tournament_size, run)
            if not run.checkpoint():
                return run.finish()
            if run.rng.random() < parameters["crossover_rate"]:
                route = order_crossover(first, second, rng=run.rng)
            else:
                route = tuple(vertex for vertex in first)
            if not run.checkpoint():
                return run.finish()
            if run.rng.random() < parameters["mutation_rate"]:
                rate = parameters.get("guided_move_rate", 0)
                route = (guided_inversion(graph, route, run) if rate > 0 and run.rng.random() < rate
                         else swap_mutation(route, rng=run.rng))
                if route is None:
                    return run.finish()
            cost = run.evaluate(route, evaluate_cost)
            if cost is None:
                return run.finish()
            next_population.append((tuple(route), cost))
            run.record_item()
            if cost == 0:
                return run.certify_best()

        # Do not use checkpoint here: the final admitted evaluation can exhaust
        # its limit while still allowing replacement and a completed generation.
        if run.time_expired():
            return run.finish()
        population = next_population
        run.complete_phase()
    return run.finish()


def solve_ga(
    graph: Graph, *, parameters: Mapping[str, object], seed: int, budget: Budget,
    clock: Callable[[], int] = perf_counter_ns,
) -> SolverResult:
    """Run GA_VARIANT with private PCG64, stored costs and independent certification.

    No files, certificates, cache, repair, restarts or global RNG are used.
    Limits are cooperative and include initialization and cycle certification.
    Only complete replacement counts as a generation. See ga-baseline.md.
    """
    try:
        effective = resolve_ga_parameters(parameters)
    except GAConfigurationError as error:
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
    except GraphError as error:
        return run.fail("invalid_candidate", error.code, "A GA operator rejected a candidate.")
    except Exception as error:
        return run.fail("runtime_error", type(error).__name__, "The GA failed during execution.")
