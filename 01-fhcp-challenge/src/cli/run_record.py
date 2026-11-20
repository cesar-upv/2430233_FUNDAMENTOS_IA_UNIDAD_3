"""Collect provenance and write a single FHCP RunRecord."""

from dataclasses import asdict
from hashlib import file_digest, sha256
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import platform
import subprocess
import time

import numpy as np

from src.algorithms.execution import Budget
from src.graphs import Graph

from .variants import VARIANTS, Variant


def _missing(fields: list, field: str, reason: str) -> None:
    fields.append({"field": field, "reason": reason})
    return None


def _git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", str(root), *args],
        capture_output=True, check=True, timeout=10,
    ).stdout


def _file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def _dirty_hash(root: Path) -> str:
    patch = _git(root, "diff", "--binary", "--no-ext-diff", "--no-textconv", "HEAD", "--")
    paths = _git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    untracked = []
    for name in sorted(filter(None, paths)):
        path = root / os.fsdecode(name)
        if path.is_symlink():
            digest = sha256(os.fsencode(os.readlink(path))).hexdigest()
            kind = "symlink"
        elif path.is_file():
            digest = _file_hash(path)
            kind = "file"
        else:
            raise OSError("Untracked path is not a regular file or symlink.")
        untracked.append([name.hex(), kind, digest])
    snapshot = {"tracked_diff_sha256": sha256(patch).hexdigest(), "untracked": untracked}
    return sha256(json.dumps(snapshot, sort_keys=True).encode("ascii")).hexdigest()


def _code(root: Path, missing: list) -> dict:
    errors = (OSError, subprocess.SubprocessError, ValueError)
    try:
        top, commit_bytes = _git(root, "rev-parse", "--show-toplevel", "--verify", "HEAD").splitlines()
        if Path(os.fsdecode(top)).resolve() != root.resolve():
            raise ValueError("Git reports a different checkout.")
        commit = commit_bytes.decode("ascii")
    except errors:
        return {
            field: _missing(missing, f"code.{field}", "Git could not identify this checkout and its HEAD.")
            for field in ("commit", "dirty", "patch_sha256")
        }
    try:
        dirty = bool(_git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all"))
    except errors:
        dirty = _missing(missing, "code.dirty", "Git status could not be read.")
    patch_sha256 = None
    if dirty is None:
        _missing(missing, "code.patch_sha256", "The working tree status is unknown.")
    elif dirty:
        try:
            patch_sha256 = _dirty_hash(root)
        except errors:
            _missing(missing, "code.patch_sha256", "The complete local diff could not be read.")
    return {"commit": commit, "dirty": dirty, "patch_sha256": patch_sha256}


def _ram_bytes() -> int | None:
    if os.name == "nt":
        import ctypes

        kib = ctypes.c_ulonglong()
        try:
            read_memory = ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory
            if read_memory(ctypes.byref(kib)) and kib.value > 0:
                return kib.value * 1024
        except (AttributeError, OSError):
            pass
    elif hasattr(os, "sysconf"):
        try:
            pages, size = os.sysconf("SC_PHYS_PAGES"), os.sysconf("SC_PAGE_SIZE")
            if pages > 0 and size > 0:
                return pages * size
        except (OSError, ValueError):
            pass
    return None


def _environment(missing: list) -> dict:
    dependencies = {
        name: distribution.version
        for distribution in distributions()
        if (name := distribution.metadata.get("Name")) and distribution.version
    }
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "dependencies": dependencies,
        "os": platform.platform(),
        "architecture": platform.machine() or _missing(
            missing, "environment.architecture", "Python did not report the machine architecture.",
        ),
        "cpu": platform.processor() or _missing(
            missing, "environment.cpu", "Python did not report a processor identifier.",
        ),
        "ram_bytes": _ram_bytes() or _missing(
            missing, "environment.ram_bytes", "The OS did not report physical memory.",
        ),
        "workers": 1,
        "native_threads": _missing(missing, "environment.native_threads", "Native library threads were not measured."),
        "concurrent_workload": _missing(missing, "environment.concurrent_workload", "Other processes were not sampled."),
    }


def _procedure(root: Path, variant: Variant, parameters: dict | None, missing: list) -> dict:
    versions = {}
    modules = [
        ("implementation_version", f"algorithms/{variant.module}.py"),
        ("fitness_version", "evaluation/cost.py"),
        ("validator_version", "evaluation/cycle.py"),
        ("instrumentation_version", "algorithms/execution.py"),
    ]
    if variant.name.endswith(("_graph_guided_v2", "_enhanced_v3")):
        modules.append(("search_operator_version", "algorithms/graph_guidance.py"))
    if parameters and parameters.get("cost_mode") == "incremental":
        modules.append(("local_moves_version", "algorithms/local_moves.py"))
    if parameters and parameters.get("pheromone_storage") == "edges":
        modules.append(("pheromone_storage_version", "algorithms/sparse_pheromone.py"))
    if variant.uses_real_keys:
        modules.append(("decoder_version", "algorithms/real_keys.py"))
    for field, module in modules:
        try:
            versions[field] = "sha256:" + _file_hash(root / "src" / module)
        except OSError:
            versions[field] = _missing(missing, f"procedure.{field}", "Module source could not be read.")
    return {
        "family": variant.family,
        "variant": variant.name,
        "iteration_unit": variant.iteration_unit,
        "parameters": parameters if parameters is not None else _missing(
            missing, "procedure.parameters", "The selected solver configuration was rejected.",
        ),
        "initialization": variant.initialization,
        "tie_policy": {"best": "first_seen", **variant.ties},
        "decoder_version": None,
        **versions,
    }


def build_record(
    root: Path, *, run_id: str, started_at_utc: str, instance_id: str,
    graph: Graph | None, parameters: dict | None, seed: int, budget: Budget, variant: Variant = VARIANTS["ga"],
) -> dict:
    missing = []
    instance = {
        "id": instance_id, "source_kind": "fhcp", "transformations": [],
        "mapping": "ascending_external_labels_zero_based_internal",
    }
    source = graph.source if graph is not None else {}
    for name in ("sha256", "source_path", "manifest_revision"):
        instance[name] = source.get(name) or _missing(
            missing, f"instance.{name}", "Verified graph provenance was not available.",
        )
    if graph is None:
        for name in ("n", "m"):
            instance[name] = _missing(missing, f"instance.{name}", "The graph did not load successfully.")
    else:
        instance.update(n=graph.vertex_count(), m=graph.edge_count())
    limits = asdict(budget)
    for name, value in limits.items():
        if value is not None and value <= 0:
            limits[name] = _missing(missing, f"budget.{name}", "The supplied limit was not positive.")
    clock = time.get_clock_info("perf_counter")
    return {
        "schema_version": "fhcp-run-record/1",
        "run": {"run_id": run_id, "started_at_utc": started_at_utc, "retry_of": None, "batch_id": None},
        "instance": instance,
        "procedure": _procedure(root, variant, parameters, missing),
        "randomness": {
            "seed_decimal": str(seed) if 0 <= seed < 2**64 else _missing(
                missing, "randomness.seed_decimal", "The supplied seed was outside the unsigned 64-bit range.",
            ),
            "generator": "PCG64", "library": "numpy", "library_version": np.__version__,
        },
        "budget": {**limits, "time_scope": "solver_including_initialization_and_validation"},
        "code": _code(root, missing),
        "environment": _environment(missing),
        "timing": {"clock": "perf_counter_ns", "clock_resolution_ns": max(1, round(clock.resolution * 1e9))},
        "artifacts": [],
        "missing_metadata": missing,
    }


def save_record(directory: Path, run_id: str, payload: str) -> Path:
    """Reserve an exclusive attempt directory and publish only a complete JSON file."""
    directory.mkdir(parents=True, exist_ok=True)
    attempt = directory / run_id
    attempt.mkdir()
    pending = attempt / ".run.json.tmp"
    target = attempt / "run.json"
    try:
        with pending.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
        pending.rename(target)
    except OSError:
        try:
            pending.unlink(missing_ok=True)
            attempt.rmdir()
        except OSError:
            pass
        raise
    return target
