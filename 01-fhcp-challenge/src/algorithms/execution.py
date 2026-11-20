"""Sequential solver admission, timing and result snapshots for contract #19."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from time import perf_counter_ns
from typing import Literal

import numpy as np

from src.evaluation import evaluate_cost, validate_cycle
from src.graphs import Graph, check_route_legality

Route = Sequence[object] | np.ndarray
CostFunction = Callable[[Graph, tuple[int, ...]], int | None]
Limit = Literal["time_limit", "evaluation_limit", "iteration_limit"]
ErrorReason = Literal[
    "invalid_input", "invalid_config", "invalid_candidate", "non_finite_state",
    "fitness_validation_mismatch", "runtime_error",
]
StopReason = Limit | ErrorReason | Literal["validated_cycle", "algorithm_stop"]


@dataclass(frozen=True, slots=True)
class Budget:
    max_elapsed_ns: int | None = None
    max_evaluations: int | None = None
    max_iterations: int | None = None


@dataclass(frozen=True, slots=True)
class PartialIteration:
    phase: str
    completed_items: int
    planned_items: int | None


@dataclass(frozen=True, slots=True)
class Counters:
    iteration_unit: str
    evaluations_started: int = 0
    evaluations_completed: int = 0
    full_evaluations: int = 0
    incremental_evaluations: int = 0
    cache_hits: int = 0
    validations_started: int = 0
    validations_completed: int = 0
    iterations_completed: int = 0
    partial_iteration: PartialIteration | None = None
    restarts: int = 0
    algorithm_counters: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Validation:
    valid: bool | None = None
    reason: str | None = "not_run"
    position: int | None = None
    vertices: tuple[int, ...] | None = None


@dataclass(frozen=True, slots=True)
class FirstSuccess:
    elapsed_ns: int
    evaluations_started: int
    evaluations_completed: int
    iterations_completed: int


@dataclass(frozen=True, slots=True)
class Timing:
    solver_ns: int = 0
    validation_ns: int = 0
    overrun_ns: int | None = None
    first_success: FirstSuccess | None = None


@dataclass(frozen=True, slots=True)
class SolverError:
    code: str
    message: str
    phase: str
    detail: dict[str, int | str | tuple[int, ...] | None] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SolverResult:
    status: Literal["success", "exhausted", "error"]
    stop_reason: StopReason
    counters: Counters
    timing: Timing
    best_route: tuple[int, ...] | None = None
    best_cost: int | None = None
    validation: Validation = field(default_factory=Validation)
    limits_reached: tuple[Limit, ...] = ()
    error: SolverError | None = None
    success_within_budget: bool = False
    telemetry_complete: bool = True
    schema_version: str = field(default="fhcp-solver-result/1", init=False)


def start_run(
    graph: Graph, *, seed: int, budget: Budget, iteration_unit: str,
    clock: Callable[[], int] = perf_counter_ns,
) -> "SolverRun | SolverResult":
    """Validate common inputs, then start the clock and create a private PCG64."""
    invalid: tuple[str, str] | None = None
    if type(seed) is not int or not 0 <= seed < 2**64:
        invalid = ("invalid_seed", "Seed must be a Python integer in [0, 2**64 - 1].")
    elif not isinstance(budget, Budget):
        invalid = ("invalid_budget", "Budget must be a Budget instance.")
    else:
        limits = (budget.max_elapsed_ns, budget.max_evaluations, budget.max_iterations)
        if all(limit is None for limit in limits) or any(
            limit is not None and (type(limit) is not int or limit <= 0)
            for limit in limits
        ):
            invalid = ("invalid_budget", "Supply at least one positive integer limit.")
        elif not isinstance(graph, Graph):
            invalid = ("invalid_graph", "Graph must be a Graph instance.")
        elif graph.vertex_count() < 3:
            invalid = ("graph_too_small", "A solver requires at least three vertices.")
    if invalid is not None:
        code, message = invalid
        reason = "invalid_config" if code in ("invalid_seed", "invalid_budget") else "invalid_input"
        time_limit = budget.max_elapsed_ns if isinstance(budget, Budget) else None
        timed = type(time_limit) is int and time_limit > 0
        return SolverResult(
            "error", reason, Counters(iteration_unit),
            Timing(overrun_ns=0 if timed else None),
            error=SolverError(code, message, "input"),
        )
    return SolverRun(graph, seed, budget, iteration_unit, clock)


class SolverRun:
    """Mutable, sequential state for one attempt. Construct via start_run()."""

    def __init__(
        self, graph: Graph, seed: int, budget: Budget, iteration_unit: str,
        clock: Callable[[], int],
    ):
        self._start_ns = clock()
        self.rng = np.random.Generator(np.random.PCG64(seed))
        self._graph = graph
        self._budget = budget
        self._clock = clock
        self._counters = Counters(iteration_unit)
        self._counts_as_iteration = False
        self._best_route: tuple[int, ...] | None = None
        self._best_cost: int | None = None
        self._validation = Validation()
        self._validation_ns = 0
        self.result: SolverResult | None = None

    def _elapsed(self) -> int:
        return self._clock() - self._start_ns

    def _time_reached(self, elapsed_ns: int) -> bool:
        limit = self._budget.max_elapsed_ns
        return limit is not None and elapsed_ns >= limit

    def time_expired(self) -> bool:
        """Check the clock inside an admitted operation without stopping it."""
        return self._time_reached(self._elapsed())

    def _limits_reached(self, elapsed_ns: int) -> tuple[Limit, ...]:
        reached: list[Limit] = []
        if self._time_reached(elapsed_ns):
            reached.append("time_limit")
        if (self._budget.max_evaluations is not None
                and self._counters.evaluations_started >= self._budget.max_evaluations):
            reached.append("evaluation_limit")
        if (self._budget.max_iterations is not None
                and self._counters.iterations_completed >= self._budget.max_iterations):
            reached.append("iteration_limit")
        return tuple(reached)

    def checkpoint(self) -> bool:
        """Admit another work item or stop with the applicable limit."""
        if self.result is not None:
            return False
        if self._best_cost == 0:
            raise RuntimeError("Call certify_best before admitting more work.")
        elapsed_ns = self._elapsed()
        limits = self._limits_reached(elapsed_ns)
        if limits:
            self._stop("exhausted", limits[0], elapsed_ns)
            return False
        return True

    def begin_phase(
        self, phase: str, planned_items: int | None, *, iteration: bool = False,
    ) -> bool:
        if self._counters.partial_iteration is not None and self.result is None:
            raise RuntimeError("Complete the current phase before starting another.")
        if not self.checkpoint():
            return False
        if planned_items is not None and (type(planned_items) is not int or planned_items < 0):
            raise ValueError("Planned items must be a nonnegative integer or None.")
        self._counters = replace(
            self._counters, partial_iteration=PartialIteration(phase, 0, planned_items),
        )
        self._counts_as_iteration = iteration
        return True

    def _active_phase(self) -> PartialIteration:
        phase = self._counters.partial_iteration
        if self.result is not None or phase is None:
            raise RuntimeError("This operation requires an active phase.")
        return phase

    def record_item(self) -> None:
        phase = self._active_phase()
        if phase.completed_items == phase.planned_items:
            raise RuntimeError("The phase already completed its planned items.")
        self._counters = replace(
            self._counters, partial_iteration=replace(phase, completed_items=phase.completed_items + 1),
        )

    def complete_phase(self) -> None:
        """Record completion after the variant finishes the entire update."""
        phase = self._active_phase()
        if phase.planned_items is not None and phase.completed_items != phase.planned_items:
            raise RuntimeError("The phase still has pending items.")
        self._counters = replace(
            self._counters, partial_iteration=None,
            iterations_completed=self._counters.iterations_completed + int(self._counts_as_iteration),
        )

    def record_restart(self) -> None:
        self._active_phase()
        self._counters = replace(self._counters, restarts=self._counters.restarts + 1)

    def count(self, name: str) -> None:
        """Count one event specific to the variant."""
        self._active_phase()
        counters = self._counters.algorithm_counters
        counters[name] = counters.get(name, 0) + 1

    def evaluate(self, route: Route, cost_function: CostFunction) -> int | None:
        """Reserve and evaluate a legal full route. None means the run stopped."""
        return self._evaluate(route, cost_function)

    def evaluate_incremental(
        self, route: Route, cost_function: CostFunction, *, check_interval: int = 1000,
    ) -> int | None:
        """Reserve one delta evaluation, checking new bests and periodic candidates.

        Full verification belongs to this same admitted evaluation; it does not
        consume another reservation. Zero-cost candidates still need certification.
        """
        if type(check_interval) is not int or check_interval < 1:
            raise ValueError("Incremental check interval must be a positive integer.")
        return self._evaluate(route, cost_function, incremental=True, check_interval=check_interval)

    def _evaluate(
        self, route: Route, cost_function: CostFunction, *, incremental: bool = False,
        check_interval: int = 1000,
    ) -> int | None:
        if not self.checkpoint():
            return None
        self._active_phase()
        try:
            legality = check_route_legality(self._graph.vertex_count(), route)
        except TypeError:
            self._fail_candidate("invalid_route_type", None, ())
            return None
        if not legality.valid:
            self._fail_candidate(legality.reason, legality.position, legality.vertices)
            return None
        snapshot = tuple(int(route[index]) for index in range(self._graph.vertex_count()))
        if not self.checkpoint():
            return None
        self._counters = replace(
            self._counters, evaluations_started=self._counters.evaluations_started + 1,
        )
        try:
            cost = cost_function(self._graph, snapshot)
        except Exception as exc:
            self._fail_callback(exc, "The cost function failed.")
            return None
        if cost is None:
            elapsed_ns = self._elapsed()
            if self._time_reached(elapsed_ns):
                self._stop("exhausted", "time_limit", elapsed_ns)
                return None
        if type(cost) is not int or not 0 <= cost <= self._graph.vertex_count():
            self.fail("runtime_error", "invalid_cost", "Expected an integer cost in [0, n].")
            return None
        if incremental and (
            self._best_cost is None or cost < self._best_cost
            or (self._counters.incremental_evaluations + 1) % check_interval == 0
        ):
            self.count("incremental_full_checks")
            try:
                verified = evaluate_cost(self._graph, snapshot)
            except Exception as exc:
                self._fail_callback(exc, "Full verification of incremental cost failed.")
                return None
            if verified != cost:
                self.fail("fitness_validation_mismatch", "incremental_cost_mismatch",
                          "Incremental cost differs from full recomputation.",
                          incremental_cost=cost, full_cost=verified)
                return None
        self._counters = replace(
            self._counters,
            evaluations_completed=self._counters.evaluations_completed + 1,
            full_evaluations=self._counters.full_evaluations + int(not incremental),
            incremental_evaluations=self._counters.incremental_evaluations + int(incremental),
        )
        if self._best_cost is None or cost < self._best_cost:
            self._best_route = snapshot
            self._best_cost = cost
        return cost

    def certify_best(self) -> SolverResult:
        """Certify a zero cost route, including after the last evaluation reservation."""
        if self.result is not None:
            return self.result
        if self._best_cost != 0 or self._best_route is None:
            raise RuntimeError("Certification requires an evaluated zero cost route.")
        started_ns = self._elapsed()
        if self._time_reached(started_ns):
            return self._stop("exhausted", "time_limit", started_ns)

        self._counters = replace(
            self._counters, validations_started=self._counters.validations_started + 1,
        )
        try:
            certificate = validate_cycle(self._graph, self._best_route)
        except Exception as exc:
            elapsed_ns = self._elapsed()
            self._validation_ns += elapsed_ns - started_ns
            return self._fail_callback(exc, "Independent validation failed.", elapsed_ns)
        elapsed_ns = self._elapsed()
        self._validation_ns += elapsed_ns - started_ns
        self._counters = replace(
            self._counters, validations_completed=self._counters.validations_completed + 1,
        )
        self._validation = Validation(
            certificate.valid, certificate.reason, certificate.position, certificate.vertices or None,
        )
        if not certificate.valid:
            error = SolverError(
                certificate.reason, "Independent validation rejected a zero cost route.",
                self._phase_name(),
                {"position": certificate.position, "vertices": certificate.vertices},
            )
            return self._stop("error", "fitness_validation_mismatch", elapsed_ns, error)
        limit = self._budget.max_elapsed_ns
        if limit is not None and elapsed_ns > limit:
            return self._stop("exhausted", "time_limit", elapsed_ns)
        return self._stop("success", "validated_cycle", elapsed_ns)

    def _phase_name(self) -> str:
        phase = self._counters.partial_iteration
        return phase.phase if phase is not None else "solver"

    def _fail_candidate(self, code: str, position: int | None, vertices: tuple[int, ...]) -> None:
        self.fail(
            "invalid_candidate", code, "The candidate is not a legal route.",
            position=position, vertices=vertices,
        )

    def _fail_callback(
        self, exc: Exception, message: str, elapsed_ns: int | None = None,
    ) -> SolverResult:
        error = SolverError(type(exc).__name__, message, self._phase_name())
        return self._stop(
            "error", "runtime_error", self._elapsed() if elapsed_ns is None else elapsed_ns, error,
        )

    def fail(
        self, reason: ErrorReason, code: str, message: str,
        **detail: int | str | tuple[int, ...] | None,
    ) -> SolverResult:
        """Report a variant error, which takes precedence over any coincident limits."""
        if self.result is not None:
            return self.result
        error = SolverError(code, message, self._phase_name(), detail)
        return self._stop("error", reason, self._elapsed(), error)

    def finish(self) -> SolverResult:
        """Return the terminal result or apply the variant's declared stop rule."""
        if self.result is not None:
            return self.result
        if self._best_cost == 0:
            return self.certify_best()
        elapsed_ns = self._elapsed()
        limits = self._limits_reached(elapsed_ns)
        return self._stop("exhausted", limits[0] if limits else "algorithm_stop", elapsed_ns)

    def _stop(
        self, status: Literal["success", "exhausted", "error"], reason: StopReason,
        elapsed_ns: int, error: SolverError | None = None,
    ) -> SolverResult:
        counters = self._counters
        success = status == "success"
        first_success = None
        if success:
            first_success = FirstSuccess(
                elapsed_ns, counters.evaluations_started,
                counters.evaluations_completed, counters.iterations_completed,
            )
        limit = self._budget.max_elapsed_ns
        overrun = None if limit is None else max(0, elapsed_ns - limit)
        self.result = SolverResult(
            status=status,
            stop_reason=reason,
            counters=replace(counters, algorithm_counters=dict(counters.algorithm_counters)),
            timing=Timing(elapsed_ns, self._validation_ns, overrun, first_success),
            best_route=self._best_route,
            best_cost=self._best_cost,
            validation=self._validation,
            limits_reached=self._limits_reached(elapsed_ns),
            error=error,
            success_within_budget=success,
        )
        return self.result
