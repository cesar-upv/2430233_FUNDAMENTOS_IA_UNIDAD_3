"""Run the verified FHCP loader and a selected solver for a single instance."""

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from time import perf_counter_ns
from uuid import uuid4

from src.algorithms.execution import Budget, Counters, SolverError, SolverResult, Timing
from src.graphs import GraphError, ReaderError, load_fhcp_graph

from .run_record import build_record, save_record
from .variants import CONFIGURATION_ERRORS, INTEGER_OPTIONS, STRING_OPTIONS, VARIANTS, effective_variant


_ROOT = Path(__file__).resolve().parents[2]
_SOLVER_OPTIONS = tuple(dict.fromkeys(name for spec in VARIANTS.values() for name in spec.options + spec.optional_options))


class CLIConfigurationError(ValueError):
    def __init__(self, code: str, parameter: str, message: str):
        self.code = code
        self.parameter = parameter
        super().__init__(message)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.cli", allow_abbrev=False,
        description="Run one solver and emit an FHCP RunRecord as JSON.",
    )
    parser.add_argument("--instance", required=True, help="ID from the versioned FHCP selection")
    parser.add_argument("--catalog", type=Path, help="explicit FHCP catalog; default keeps the original M6 selection")
    parser.add_argument("--seed", required=True, type=int, help="unsigned 64-bit integer seed")
    parser.add_argument("--algorithm", choices=VARIANTS, default="ga", help="solver family (default: ga)")
    parser.add_argument("--variant", help="optional exact variant identifier for the selected family")
    for name in _SOLVER_OPTIONS:
        families = ", ".join(key for key, spec in VARIANTS.items() if name in spec.options + spec.optional_options)
        parser.add_argument(
            "--" + name.replace("_", "-"), type=str if name in STRING_OPTIONS else (int if name in INTEGER_OPTIONS else float),
            choices=STRING_OPTIONS.get(name),
            help=f"solver parameter for {families}",
        )
    budget = parser.add_argument_group("budget", "Supply at least one positive limit.")
    budget.add_argument("--max-evaluations", type=int, help="maximum cost evaluations")
    budget.add_argument("--max-iterations", type=int, help="maximum completed solver iterations")
    budget.add_argument("--max-elapsed-ns", type=int, help="cooperative solver limit in nanoseconds")
    parser.add_argument("--output-dir", type=Path, help="also save <run_id>/run.json in this directory")
    return parser


def _check_limits(seed: int, budget: Budget) -> None:
    if not 0 <= seed < 2**64:
        raise CLIConfigurationError("invalid_seed", "seed", "Seed must be an unsigned 64-bit integer.")
    limits = asdict(budget)
    for name, value in limits.items():
        if value is not None and value <= 0:
            raise CLIConfigurationError("invalid_budget", name, "Budget limits must be positive integers.")
    if all(value is None for value in limits.values()):
        raise CLIConfigurationError("invalid_budget", "budget", "Supply at least one positive budget limit.")


def _preparation_error(reason, code, message, phase, budget, iteration_unit, **detail) -> SolverResult:
    timed = budget.max_elapsed_ns is not None and budget.max_elapsed_ns > 0
    return SolverResult(
        "error", reason, Counters(iteration_unit),
        Timing(overrun_ns=0 if timed else None),
        error=SolverError(code, message, phase, detail),
    )


def _incomplete_result(reason: str, code: str, message: str) -> dict:
    return {
        "schema_version": "fhcp-solver-result/1", "status": "error", "stop_reason": reason,
        "success_within_budget": False, "best_route": None, "best_cost": None,
        "validation": {"valid": None, "reason": None, "position": None, "vertices": None},
        "counters": None, "limits_reached": None, "telemetry_complete": False,
        "timing": {"solver_ns": None, "validation_ns": None, "overrun_ns": None, "first_success": None},
        "error": {"code": code, "message": message, "phase": "solver",
                  "detail": {"reason": "The solver did not return its result."}},
    }


def _run(args: argparse.Namespace) -> dict:
    started = perf_counter_ns()
    started_at_utc = datetime.now(UTC).isoformat()
    run_id = str(uuid4())
    budget = Budget(args.max_elapsed_ns, args.max_evaluations, args.max_iterations)
    spec = VARIANTS[args.algorithm]
    requested = {
        name: value
        for name in _SOLVER_OPTIONS
        if (value := getattr(args, name)) is not None
    }
    parameters = graph = result = None
    try:
        guided_name = spec.name.removesuffix("_v1") + "_graph_guided_v2"
        enhanced_name = spec.name.removesuffix("_v1") + "_enhanced_v3"
        if args.variant is not None and args.variant not in (spec.name, guided_name, enhanced_name):
            raise CLIConfigurationError("invalid_variant", "variant", f"Expected variant {spec.name}, {guided_name} or {enhanced_name}.")
        incompatible = sorted(requested.keys() - set(spec.options + spec.optional_options))
        if incompatible:
            raise CLIConfigurationError(
                "incompatible_parameter", incompatible[0], "Parameter does not apply to the selected algorithm.",
            )
        parameters = spec.resolve(requested)
        spec = effective_variant(spec, parameters)
        if args.variant is not None and args.variant != spec.name:
            raise CLIConfigurationError("invalid_variant", "variant", f"Expected variant {spec.name}.")
        _check_limits(args.seed, budget)
        if args.catalog is None:
            graph = load_fhcp_graph(args.instance, root=_ROOT)
        else:
            graph = load_fhcp_graph(args.instance, root=_ROOT, manifest=args.catalog)
    except (CLIConfigurationError, *CONFIGURATION_ERRORS) as error:
        result = _preparation_error(
            "invalid_config", error.code, str(error), "input", budget, spec.iteration_unit,
            parameter=error.parameter,
        )
    except ReaderError as error:
        result = _preparation_error(
            "invalid_input", error.code, str(error), "load", budget, spec.iteration_unit, line=error.line,
        )
    except GraphError as error:
        result = _preparation_error("invalid_input", error.code, str(error), "load", budget, spec.iteration_unit)
    except OSError as error:
        result = _preparation_error(
            "invalid_input", "instance_unavailable", "The FHCP graph or manifest could not be read.",
            "load", budget, spec.iteration_unit, errno=error.errno,
        )
    except Exception as error:
        result = _preparation_error(
            "runtime_error", type(error).__name__, "Preparation failed.", "preparation", budget, spec.iteration_unit,
        )
    record = build_record(
        _ROOT, run_id=run_id, started_at_utc=started_at_utc, instance_id=args.instance,
        graph=graph, parameters=parameters, seed=args.seed, budget=budget, variant=spec,
    )
    prepared = perf_counter_ns()
    if result is None:
        try:
            result = spec.solve(graph, parameters=parameters, seed=args.seed, budget=budget)
        except KeyboardInterrupt:
            result = _incomplete_result("external_termination", "KeyboardInterrupt", "The solver was interrupted.")
        except Exception as error:
            result = _incomplete_result("runtime_error", type(error).__name__, "The solver failed before returning a result.")
    finalizing = perf_counter_ns()
    record["result"] = asdict(result) if isinstance(result, SolverResult) else result
    record["timing"]["preparation_ns"] = prepared - started
    finished = perf_counter_ns()
    record["timing"]["finalization_ns"] = finished - finalizing
    record["timing"]["total_ns"] = finished - started
    return record


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    record = _run(args)
    payload = json.dumps(record, allow_nan=False) + "\n"
    save_failed = False
    if args.output_dir is not None:
        try:
            save_record(args.output_dir, record["run"]["run_id"], payload)
        except OSError as error:
            print(f"output_error: {error}", file=sys.stderr)
            save_failed = True
    sys.stdout.write(payload)
    result = record["result"]
    if result["error"] is not None:
        error = result["error"]
        print(f"{error['code']}: {error['message']}", file=sys.stderr)
    if save_failed:
        return 1
    return {"invalid_config": 2, "external_termination": 130}.get(
        result["stop_reason"], int(result["status"] == "error"),
    )


if __name__ == "__main__":
    raise SystemExit(main())
