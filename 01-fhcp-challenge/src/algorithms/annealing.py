"""Sequential swap-based simulated annealing on legal route permutations."""

from collections.abc import Callable, Mapping
from math import isfinite, log
from time import perf_counter_ns
from typing import cast

import numpy as np

from src.evaluation import evaluate_cost
from src.graphs import Graph, GraphError

from .graph_guidance import greedy_route, guided_inversion, resolve_search_options
from .local_moves import guided_move, random_swap_move, resolve_cost_options
from .execution import Budget, Counters, SolverError, SolverResult, SolverRun, Timing, start_run
from .permutation import initialize_route, swap_mutation

SA_VARIANT = "geometric_swap_v1"


class SAConfigurationError(ValueError):
    """Rejected SA configuration, with a stable code and affected parameter."""

    def __init__(self, code: str, parameter: str | None, message: str):
        self.code = code
        self.parameter = parameter
        super().__init__(message)


def resolve_sa_parameters(parameters: Mapping[str, object]) -> dict[str, int | float]:
    """Copy and validate all four required parameters before clock or RNG use.

    Temperatures and cooling_factor accept finite Python int/float except bool,
    normalized to float. Require initial_temperature > 0, 0 < cooling_factor < 1,
    0 <= minimum_temperature < initial_temperature and a positive Python int
    moves_per_temperature. No experimental defaults are supplied.
    """
    if not isinstance(parameters, Mapping):
        raise SAConfigurationError("invalid_parameters", None, "Parameters must be a mapping.")
    values = dict(parameters)
    names = ("initial_temperature", "cooling_factor", "minimum_temperature", "moves_per_temperature")
    if any(not isinstance(key, str) for key in values):
        raise SAConfigurationError("invalid_parameters", None, "Parameter names must be strings.")
    unknown = sorted(values.keys() - (set(names) | {"initialization", "guided_move_rate", "cost_mode", "incremental_check_interval", "reheat_after"}))
    if unknown:
        raise SAConfigurationError("unknown_parameter", unknown[0], "Unknown SA parameter.")
    for name in names:
        if name not in values:
            raise SAConfigurationError("missing_parameter", name, "Missing required SA parameter.")

    effective: dict[str, int | float] = {}
    for name in names[:3]:
        value = values[name]
        if type(value) not in (int, float):
            raise SAConfigurationError("invalid_parameter", name, "Expected a finite Python number.")
        try:
            number = float(value)
        except OverflowError:
            raise SAConfigurationError("invalid_parameter", name, "Number exceeds the float range.") from None
        if not isfinite(number):
            raise SAConfigurationError("invalid_parameter", name, "Expected a finite Python number.")
        effective[name] = number
    if effective["initial_temperature"] <= 0:
        raise SAConfigurationError("invalid_parameter", "initial_temperature", "Initial temperature must be positive.")
    if not 0 < effective["cooling_factor"] < 1:
        raise SAConfigurationError("invalid_parameter", "cooling_factor", "Cooling factor must be in (0, 1).")
    if not 0 <= effective["minimum_temperature"] < effective["initial_temperature"]:
        raise SAConfigurationError("invalid_parameter", "minimum_temperature", "Minimum temperature must be in [0, initial_temperature).")
    moves = values["moves_per_temperature"]
    if type(moves) is not int or moves <= 0:
        raise SAConfigurationError("invalid_parameter", "moves_per_temperature", "Moves per temperature must be a positive Python integer.")
    effective["moves_per_temperature"] = moves
    effective.update(resolve_search_options(values, SAConfigurationError, moves=True))
    effective.update(resolve_cost_options(values, SAConfigurationError))
    if "reheat_after" in values:
        reheat = values["reheat_after"]
        if type(reheat) is not int or reheat < 0:
            raise SAConfigurationError("invalid_parameter", "reheat_after", "Expected an integer >= 0.")
        effective["reheat_after"] = reheat
    return effective


def _accept_move(delta: int, temperature: float, rng: np.random.Generator) -> bool:
    if delta <= 0:
        return True
    if temperature <= 0:
        return False
    uniform = rng.random()
    # Generator.random() includes zero. Avoid log(0) and preserve the strict
    # U < exp(-delta/T) rule even when that positive probability underflows.
    return uniform == 0 or log(uniform) < -delta / temperature


def _search(graph: Graph, parameters: dict[str, int | float], run: SolverRun) -> SolverResult:
    temperature = float(parameters["initial_temperature"])
    minimum = parameters["minimum_temperature"]
    cooling = parameters["cooling_factor"]
    moves_per_temperature = cast(int, parameters["moves_per_temperature"])
    if not run.begin_phase("initialization", 1) or not run.checkpoint():
        return run.finish()
    current = (greedy_route(graph, run) if parameters.get("initialization") == "greedy"
             else initialize_route(graph.vertex_count(), run.rng))
    if current is None:
        return run.finish()
    current_cost = run.evaluate(current, evaluate_cost)
    if current_cost is None:
        return run.finish()
    run.record_item()
    if current_cost == 0:
        return run.certify_best()
    if run.time_expired():
        return run.finish()
    run.complete_phase()

    moves_at_temperature = 0
    reheat_after = parameters.get("reheat_after", 0)
    stagnant = 0
    best_seen_route, best_seen_cost = current, current_cost
    incremental = parameters.get("cost_mode") == "incremental"
    while (temperature > minimum or reheat_after > 0) and run.begin_phase("move", 1, iteration=True):
        if not run.checkpoint():
            return run.finish()
        rate = parameters.get("guided_move_rate", 0)
        if incremental:
            move = (guided_move(graph, current, run) if rate > 0 and run.rng.random() < rate
                    else random_swap_move(len(current), run))
            if move is None:
                return run.finish()
            neighbor = move.apply(current)
            cost = run.evaluate_incremental(
                neighbor, lambda g, route: move.cost_after(g, current, current_cost),
                check_interval=parameters["incremental_check_interval"],
            )
        else:
            neighbor = (guided_inversion(graph, current, run) if rate > 0 and run.rng.random() < rate
                        else swap_mutation(current, rng=run.rng))
            if neighbor is None:
                return run.finish()
            cost = run.evaluate(neighbor, evaluate_cost)
        if cost is None:
            return run.finish()
        run.record_item()
        if cost == 0:
            return run.certify_best()
        if reheat_after > 0:
            if cost < best_seen_cost:
                best_seen_route, best_seen_cost = neighbor, cost
                stagnant = 0
            else:
                stagnant += 1
        # Only time can interrupt an already admitted acceptance decision;
        # exhausting the final evaluation reservation must still allow it.
        if run.time_expired():
            return run.finish()
        accepted = _accept_move(cost - current_cost, temperature, run.rng)
        if run.time_expired():
            return run.finish()
        if accepted:
            current, current_cost = neighbor, cost
        run.count("accepted_moves" if accepted else "rejected_moves")
        moves_at_temperature += 1
        stalled = False
        if moves_at_temperature == moves_per_temperature:
            cooled = temperature * cooling
            stalled = cooled == temperature
            temperature = cooled
            moves_at_temperature = 0
            run.count("cooling_steps")
            if stalled:
                run.count("cooling_stalls")
        if reheat_after > 0 and (stagnant >= reheat_after or temperature <= minimum or stalled):
            # Return to the independently checked historical best, then reheat.
            current, current_cost = best_seen_route, best_seen_cost
            temperature = float(parameters["initial_temperature"])
            stagnant = moves_at_temperature = 0
            stalled = False
            run.count("reheats")
            run.record_restart()
        run.complete_phase()
        if stalled:
            break
    return run.finish()


def solve_sa(
    graph: Graph, *, parameters: Mapping[str, object], seed: int, budget: Budget,
    clock: Callable[[], int] = perf_counter_ns,
) -> SolverResult:
    """Run SA_VARIANT with private PCG64 and the #19 result/budget contract.

    A move counts only after evaluation and acceptance decision; initialization
    is excluded. Zero cost is certified immediately, leaving its phase partial.
    Stop on budget, certificate, T <= minimum or rounded cooling stagnation.
    See docs/decisions/sa-baseline.md for numerical and RNG policies.
    """
    try:
        effective = resolve_sa_parameters(parameters)
    except SAConfigurationError as error:
        limit = budget.max_elapsed_ns if isinstance(budget, Budget) else None
        timed = type(limit) is int and limit > 0
        return SolverResult(
            "error", "invalid_config", Counters("move"),
            Timing(overrun_ns=0 if timed else None),
            error=SolverError(error.code, str(error), "input", {"parameter": error.parameter}),
        )
    run = start_run(graph, seed=seed, budget=budget, iteration_unit="move", clock=clock)
    if isinstance(run, SolverResult):
        return run
    try:
        return _search(graph, effective, run)
    except GraphError as error:
        return run.fail("invalid_candidate", error.code, "An SA operator rejected a candidate.")
    except Exception as error:
        return run.fail("runtime_error", type(error).__name__, "The SA failed during execution.")
