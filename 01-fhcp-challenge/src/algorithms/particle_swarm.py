"""Synchronous global PSO on real keys using the common solver runtime."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import isfinite
from time import perf_counter_ns
from typing import cast

import numpy as np

from src.evaluation import evaluate_cost
from src.graphs import Graph

from .graph_guidance import greedy_keys, resolve_search_options
from .execution import Budget, Counters, SolverError, SolverResult, SolverRun, Timing, start_run
from .real_keys import KeyDecodingError, decode_real_keys


PSO_VARIANT = "global_real_keys_v1"
_ITERATION_UNIT = "round"


class PSOConfigurationError(ValueError):
    """Rejected PSO configuration with a stable code and affected parameter."""

    def __init__(self, code: str, parameter: str | None, message: str):
        self.code = code
        self.parameter = parameter
        super().__init__(message)


def resolve_pso_parameters(parameters: Mapping[str, object]) -> dict[str, int | float | None]:
    """Copy the effective configuration and expand the optional velocity limit."""
    if not isinstance(parameters, Mapping):
        raise PSOConfigurationError("invalid_parameters", None, "Parameters must be a mapping.")
    values = dict(parameters)
    coefficients = ("inertia", "cognitive_coefficient", "social_coefficient")
    required = ("swarm_size", *coefficients)
    allowed = {*required, "velocity_limit", "initialization"}
    if any(not isinstance(key, str) for key in values):
        raise PSOConfigurationError("invalid_parameters", None, "Parameter names must be strings.")
    unknown = sorted(values.keys() - allowed)
    if unknown:
        raise PSOConfigurationError("unknown_parameter", unknown[0], "Unknown PSO parameter.")
    for name in required:
        if name not in values:
            raise PSOConfigurationError("missing_parameter", name, "Missing required PSO parameter.")

    size = values["swarm_size"]
    if type(size) is not int or size < 2:
        raise PSOConfigurationError("invalid_parameter", "swarm_size", "Swarm size must be an integer >= 2.")
    effective: dict[str, int | float | None] = {"swarm_size": size, "velocity_limit": None}
    for name in (*coefficients, "velocity_limit"):
        value = values.get(name)
        if name == "velocity_limit" and value is None:
            continue
        if type(value) not in (int, float):
            raise PSOConfigurationError("invalid_parameter", name, "Expected a finite Python number.")
        try:
            number = float(value)
        except OverflowError:
            raise PSOConfigurationError("invalid_parameter", name, "Number exceeds the float range.") from None
        if not isfinite(number) or number < 0:
            raise PSOConfigurationError("invalid_parameter", name, "Expected a finite, nonnegative number.")
        if name == "velocity_limit" and number == 0:
            raise PSOConfigurationError("invalid_parameter", name, "Velocity limit must be positive or None.")
        effective[name] = number
    effective.update(resolve_search_options(values, PSOConfigurationError, moves=False))
    return effective


@dataclass(frozen=True, slots=True)
class _Best:
    keys: np.ndarray
    cost: int


@dataclass(frozen=True, slots=True)
class _Particle:
    position: np.ndarray
    velocity: np.ndarray
    personal_best: _Best


def _improve(best: _Best | None, position: np.ndarray, cost: int) -> _Best:
    if best is None or cost < best.cost:
        return _Best(position.copy(), cost)
    return best


def _require_finite(vector: np.ndarray) -> None:
    if not np.isfinite(vector).all():
        raise FloatingPointError("PSO state contains non-finite values.")


def _bounded_velocity(velocity: np.ndarray, limit: float | None) -> np.ndarray:
    _require_finite(velocity)
    return velocity if limit is None else np.clip(velocity, -limit, limit)


def _advance(
    particle: _Particle, global_keys: np.ndarray, parameters: dict[str, int | float | None],
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    x = particle.position
    r1 = rng.random(len(x))
    r2 = rng.random(len(x))
    inertia = cast(float, parameters["inertia"])
    cognitive = cast(float, parameters["cognitive_coefficient"])
    social = cast(float, parameters["social_coefficient"])
    limit = cast(float | None, parameters["velocity_limit"])
    with np.errstate(over="raise", invalid="raise", under="ignore"):
        velocity = (
            inertia * particle.velocity
            + cognitive * r1 * (particle.personal_best.keys - x)
            + social * r2 * (global_keys - x)
        )
        velocity = _bounded_velocity(velocity, limit)
        position = x + velocity
    _require_finite(position)
    return position, velocity


def _search(graph: Graph, parameters: dict[str, int | float | None], run: SolverRun) -> SolverResult:
    size = cast(int, parameters["swarm_size"])
    limit = cast(float | None, parameters["velocity_limit"])
    n = graph.vertex_count()
    swarm: list[_Particle] = []
    global_best: _Best | None = None
    if not run.begin_phase("initialization", size):
        return run.finish()
    for _ in range(size):
        if not run.checkpoint():
            return run.finish()
        position = (greedy_keys(graph, run) if parameters.get("initialization") == "greedy"
                    else run.rng.random(n))
        if position is None:
            return run.finish()
        velocity = _bounded_velocity(run.rng.random(n) - 0.5, limit)
        _require_finite(position)
        if not run.checkpoint():
            return run.finish()
        cost = run.evaluate(decode_real_keys(n, position), evaluate_cost)
        if cost is None:
            return run.finish()
        run.record_item()
        if cost == 0:
            return run.certify_best()
        if run.time_expired():
            return run.finish()
        swarm.append(_Particle(position, velocity, _improve(None, position, cost)))
        global_best = _improve(global_best, position, cost)
    if run.time_expired():
        return run.finish()
    run.complete_phase()
    assert global_best is not None

    while run.begin_phase("round", size, iteration=True):
        # Each proposal uses the same global memory and its own previous personal memory.
        frozen_global = global_best.keys
        next_global = global_best
        next_swarm: list[_Particle] = []
        for particle in swarm:
            if not run.checkpoint():
                return run.finish()
            position, velocity = _advance(particle, frozen_global, parameters, run.rng)
            if not run.checkpoint():
                return run.finish()
            cost = run.evaluate(decode_real_keys(n, position), evaluate_cost)
            if cost is None:
                return run.finish()
            run.record_item()
            if cost == 0:
                return run.certify_best()
            # The last admitted evaluation can still update memories and finish the round.
            if run.time_expired():
                return run.finish()
            personal = _improve(particle.personal_best, position, cost)
            next_swarm.append(_Particle(position, velocity, personal))
            next_global = _improve(next_global, position, cost)
        if run.time_expired():
            return run.finish()
        swarm, global_best = next_swarm, next_global
        run.complete_phase()
    return run.finish()


def solve_pso(
    graph: Graph, *, parameters: Mapping[str, object], seed: int, budget: Budget,
    clock: Callable[[], int] = perf_counter_ns,
) -> SolverResult:
    """Run global PSO with private PCG64 and synchronous best memories."""
    try:
        effective = resolve_pso_parameters(parameters)
    except PSOConfigurationError as error:
        limit = budget.max_elapsed_ns if isinstance(budget, Budget) else None
        timed = type(limit) is int and limit > 0
        return SolverResult(
            "error", "invalid_config", Counters(_ITERATION_UNIT),
            Timing(overrun_ns=0 if timed else None),
            error=SolverError(error.code, str(error), "input", {"parameter": error.parameter}),
        )
    run = start_run(graph, seed=seed, budget=budget, iteration_unit=_ITERATION_UNIT, clock=clock)
    if isinstance(run, SolverResult):
        return run
    try:
        return _search(graph, effective, run)
    except KeyDecodingError as error:
        reason = "non_finite_state" if error.code == "non_finite_state" else "runtime_error"
        return run.fail(reason, error.code, "PSO key decoding failed.", position=error.position)
    except FloatingPointError:
        return run.fail("non_finite_state", "non_finite_state", "PSO position or velocity exceeded the finite range.")
    except Exception as error:
        return run.fail("runtime_error", type(error).__name__, "PSO failed during execution.")
