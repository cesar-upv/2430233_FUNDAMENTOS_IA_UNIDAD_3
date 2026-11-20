"""Execute and resume one phase of the accepted FHCP benchmark on Linux."""

import argparse
from collections import Counter
from datetime import UTC, datetime
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
from tempfile import NamedTemporaryFile
from time import CLOCK_BOOTTIME, clock_gettime_ns, get_clock_info, perf_counter_ns
from uuid import UUID, uuid4

import numpy as np

from src.evaluation import evaluate_cost, validate_cycle
from src.graphs import GraphError, ReaderError, load_fhcp_graph

from .__main__ import _ROOT
from .benchmark_plan import CONFIG, PROTOCOL, checked_path, digest, expand_plan, load_config, load_freeze, protocol_path, read_json
from .run_record import _environment, _file_hash, _git
from .variants import VARIANTS


RESULTS = Path("experiments/results")
SCHEMA = "fhcp-batch-manifest/1"


def _utc():
    return datetime.now(UTC).isoformat()


def _write_bytes(path, data):
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def _write_json(path, value):
    _write_bytes(path, (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"))


def _artifact(batch, path):
    return {"path": path.relative_to(batch.parents[2]).as_posix(), "sha256": _file_hash(path)}


def _evidence_path(batch, value):
    path = checked_path(batch.parents[2], value)
    if not path.resolve().is_relative_to(batch):
        raise ValueError(f"Evidence path is outside its batch: {value}")
    return path


def _record_manifest(batch, manifest):
    path = batch / "manifest.json"
    if path.exists():
        previous = path.read_bytes()
        revision = json.loads(previous)["revision"]
        history = batch / "manifest-history" / f"{revision:06d}.json"
        if history.exists() and history.read_bytes() != previous:
            raise ValueError("Manifest history conflicts with the current revision.")
        if not history.exists():
            _write_bytes(history, previous)
        manifest["revision"] = revision + 1
        manifest["previous_manifest_sha256"] = sha256(previous).hexdigest()
    manifest["updated_at_utc"] = _utc()
    _write_json(path, manifest)


def _commit(root):
    if _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all"):
        raise ValueError("Benchmark execution requires a clean checkout.")
    return _git(root, "rev-parse", "--verify", "HEAD").decode("ascii").strip()


def _exclude_batch(root, relative):
    exclude = Path(os.fsdecode(_git(root, "rev-parse", "--path-format=absolute",
                                    "--git-path", "info/exclude").rstrip(b"\n")))
    exclude.parent.mkdir(parents=True, exist_ok=True)
    rule = f"/{relative.as_posix()}/"
    with exclude.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.seek(0)
        if rule not in stream.read().splitlines():
            stream.write("\n" + rule + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    return {"path": relative.as_posix(), "rule": rule,
            "reason": "Exclude only the generated evidence of this batch from Git status."}


def _module_hashes(root):
    # Hash the complete runtime dependency tree, including graph ingestion and
    # shared operators. A clean resume must use the exact recorded implementation.
    paths = sorted((root / "src").rglob("*.py"))
    return {path.relative_to(root).as_posix(): _file_hash(path) for path in paths}


def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _profile(cpu, execution, missing):
    if cpu not in os.sched_getaffinity(0):
        raise ValueError(f"CPU {cpu} is not available in the current affinity mask.")
    env = _environment(missing)
    # These samples or unspecified settings are not part of the stable profile.
    env.pop("concurrent_workload", None)
    env.pop("native_threads", None)
    missing[:] = [item for item in missing if item["field"] not in {
        "environment.concurrent_workload", "environment.native_threads",
    }]
    cpuinfo = _read_text("/proc/cpuinfo") or ""
    model = re.search(r"^model name\s*:\s*(.+)$", cpuinfo, re.MULTILINE)
    env["cpu"] = model.group(1) if model else env["cpu"]
    if env["cpu"] is not None:
        missing[:] = [item for item in missing if item["field"] != "environment.cpu"]
    clock = get_clock_info("perf_counter")
    env.update(
        kernel=platform.release(), python_build=list(platform.python_build()),
        numpy_build=np.show_config(mode="dicts"), affinity=[cpu],
        clock={"name": "perf_counter_ns", "resolution_ns": max(1, round(clock.resolution * 1e9))},
        energy_policy=_read_text(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor"),
        thread_policy={"requested": execution["native_threads"],
                       "variables": execution["environment_variables"],
                       "measurement": "Threads sampled from /proc/<pid>/status"},
    )
    if env["energy_policy"] is None:
        missing.append({"field": "environment.energy_policy", "reason": "CPU governor not exposed by sysfs."})
    return {"environment_id": digest(env), **env}


def _memory_available():
    contents = _read_text("/proc/meminfo") or ""
    match = re.search(r"^MemAvailable:\s+(\d+)\s+kB$", contents, re.MULTILINE)
    return int(match.group(1)) * 1024 if match else None


def _has_required_memory(available, minimum):
    return available is not None and available >= minimum


def resource_sample(cpu):
    """Linux observations, never a claim of complete machine isolation."""
    vmstat = _read_text("/proc/vmstat") or ""
    swap = {name: int(value) for name, value in
            re.findall(r"^(pswpin|pswpout) (\d+)$", vmstat, re.MULTILINE)}
    power = list(Path("/sys/class/power_supply").glob("*/online"))
    return dict(available_ram_bytes=_memory_available(), swap_pages=swap,
                ac_online=any(_read_text(path) == "1" for path in power),
                governor=_read_text(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor"),
                suspend_offset_ns=clock_gettime_ns(CLOCK_BOOTTIME)-perf_counter_ns(),
                load_1m=os.getloadavg()[0], at_utc=_utc())


def resource_incidents(before, after, profile):
    issues = []
    if not before["ac_online"] or not after["ac_online"]:
        issues.append("ac_power_unavailable")
    if before["governor"] != profile["energy_policy"] or after["governor"] != profile["energy_policy"]:
        issues.append("energy_policy_changed")
    if (set(before["swap_pages"]) != {"pswpin", "pswpout"}
        or before["swap_pages"] != after["swap_pages"]):
        issues.append("swap_activity")
    if abs(after["suspend_offset_ns"] - before["suspend_offset_ns"]) > 1_000_000_000:
        issues.append("system_suspend")
    return issues


def _graph(root, identity):
    graph = load_fhcp_graph(identity["instance_id"], root=root)
    if graph.source["sha256"] != identity["instance_sha256"]:
        raise ValueError("Verified graph hash differs from trial identity.")
    return graph


def create_batch(root, config_path, phase, cpu, freeze_path=None):
    root = Path(root).resolve()
    commit = _commit(root)
    config = load_config(root, config_path)
    freeze = selection = None
    if freeze_path is not None:
        freeze, selection = load_freeze(root, freeze_path, config, config_path)
    needs_freeze = config["phases"][phase]["configuration_source"] == "frozen_selection"
    if needs_freeze != (freeze is not None):
        raise ValueError("Supply a freeze only for a phase that requires frozen selection.")
    trials = expand_plan(config, phase, selection)
    missing = []
    environment = _profile(cpu, config["execution"], missing)
    profile = config["execution"].get("campaign_profile")
    if profile and (environment["cpu"] != profile["cpu_model"]
                    or environment["ram_bytes"] != profile["ram_bytes"]
                    or environment["kernel"] != profile["kernel"]
                    or cpu != profile["logical_cpu"]
                    or environment["energy_policy"] != profile["energy_policy"]):
        raise ValueError("Machine differs from the preregistered campaign profile.")
    hashes = _module_hashes(root)
    if freeze and (
        freeze["code"]["commit"] != commit
        or freeze["code"].get("modules") != hashes
        or freeze["environment"]["environment_id"] != environment["environment_id"]
    ):
        raise ValueError("The checkout or environment differs from the freeze.")
    batch_id = str(uuid4())
    relative = RESULTS / batch_id
    exclusion = _exclude_batch(root, relative)
    batch = checked_path(root, relative)
    batch.mkdir(parents=True, exist_ok=False)
    (batch / "manifest-history").mkdir()
    (batch / "inputs").mkdir()
    sources = [
        ("protocol", root / protocol_path(config), "protocol.md"),
        ("config", config_path, config_path.name),
        ("dataset_manifest", root / config["dataset_manifest"]["path"], "fhcp-instances.json"),
    ]
    if protocol_path(config) != PROTOCOL:
        sources.append(("protocol_base", root / PROTOCOL, "protocol-base.md"))
    if freeze_path is not None:
        sources.append(("freeze", freeze_path, "freeze.json"))
    inputs = []
    for role, source, filename in sources:
        target = batch / "inputs" / filename
        _write_bytes(target, source.read_bytes())
        inputs.append({"role": role, **_artifact(batch, target)})
    now = _utc()
    manifest = {
        "schema_version": SCHEMA, "batch_id": batch_id, "protocol_id": config["protocol_id"],
        "phase": phase, "created_at_utc": now, "updated_at_utc": now,
        "status": "planned", "revision": 0, "previous_manifest_sha256": None,
        "inputs": inputs, "code": {"commit": commit, "dirty": False, "modules": hashes,
                                    "artifact_exclusion": exclusion},
        "environment": environment, "expected_trials": len(trials), "trials": trials,
        "artifacts": [], "missing_metadata": missing, "deviations": [],
    }
    if _commit(root) != commit:
        raise ValueError("Checkout changed while creating the batch.")
    _record_manifest(batch, manifest)
    return batch


def command_for(trial, entry, directory, cpu):
    identity = trial["identity"]
    command = [
        "taskset", "--cpu-list", str(cpu), sys.executable, "-m", "src.cli",
        "--instance", identity["instance_id"], "--algorithm", identity["algorithm"],
        "--variant", identity["variant"], "--seed", identity["seed_decimal"],
        "--output-dir", str(directory / "cli"),
    ]
    for settings in (entry["parameters"], identity["budget"]):
        for name, value in sorted(settings.items()):
            if value is not None:
                command.extend(("--" + name.replace("_", "-"), str(value)))
    return command


def _sample(pid, observed):
    status = _read_text(f"/proc/{pid}/status") or ""
    for key, field, multiplier in (("VmHWM", "peak_rss_bytes", 1024), ("Threads", "peak_threads", 1)):
        match = re.search(rf"^{key}:\s+(\d+)", status, re.MULTILINE)
        if match:
            observed[field] = max(observed.get(field, 0), int(match.group(1)) * multiplier)
    load = os.getloadavg()[0]
    observed["peak_load_1m"] = max(observed.get("peak_load_1m", 0), load)


def _execute(root, directory, attempt, timeout_ns, locks):
    outcome = diagnostic = exit_code = None
    observed = {"before_load_1m": os.getloadavg()[0], "available_ram_bytes": _memory_available()}
    with (directory / "stdout.partial").open("xb") as stdout, (directory / "stderr.partial").open("xb") as stderr:
        started = perf_counter_ns()
        try:
            with subprocess.Popen(attempt["command"], cwd=root, stdout=stdout, stderr=stderr,
                                  env={**os.environ, **attempt["variables"]},
                                  start_new_session=True, pass_fds=tuple(lock.fileno() for lock in locks)) as child:
                try:
                    deadline = started + timeout_ns
                    while True:
                        _sample(child.pid, observed)
                        remaining = (deadline - perf_counter_ns()) / 1e9
                        if remaining <= 0:
                            if child.poll() is None:
                                raise subprocess.TimeoutExpired(attempt["command"], timeout_ns / 1e9)
                            exit_code = child.returncode
                            break
                        try:
                            exit_code = child.wait(timeout=min(remaining, 0.1))
                            break
                        except subprocess.TimeoutExpired:
                            continue
                except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
                    exit_code = None
                    outcome = "external_timeout" if isinstance(error, subprocess.TimeoutExpired) else "interrupted"
                    diagnostic = outcome
                finally:
                    # Stop descendants too, including when a leader exits first.
                    # File locks inherited by children cannot outlive this group.
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    exit_code = child.wait()
        except OSError as error:
            outcome, diagnostic = "runtime_error", str(error)
        process_elapsed = perf_counter_ns() - started
        capture_started = perf_counter_ns()
        os.fsync(stdout.fileno())
        os.fsync(stderr.fileno())
    _write_json(directory / "process.json", {
        "exit_code": exit_code if exit_code is None or exit_code >= 0 else None,
        "signal": -exit_code if exit_code is not None and exit_code < 0 else None,
        "process_elapsed_ns": process_elapsed, "capture_write_ns": perf_counter_ns() - capture_started,
        "observed": observed, "outcome": outcome, "diagnostic": diagnostic,
    })


def _audit(record, manifest, trial, entry, graph):
    identity = trial["identity"]
    instance, procedure, result = record["instance"], record["procedure"], record["result"]
    if (
        record["schema_version"] != "fhcp-run-record/1"
        or str(UUID(record["run"]["run_id"])) != record["run"]["run_id"]
        or instance["id"] != identity["instance_id"]
        or procedure["family"] != entry["family"]
        or procedure["variant"] != identity["variant"]
        or record["randomness"]["seed_decimal"] != identity["seed_decimal"]
        or record["code"]["commit"] != manifest["code"]["commit"]
        or record["code"]["dirty"] is not False
    ):
        raise ValueError("RunRecord identity or checkout differs from the trial.")
    if result["status"] == "error":
        return "config_error" if result["stop_reason"] == "invalid_config" else "runtime_error"
    if (
        instance["sha256"] != identity["instance_sha256"]
        or procedure["parameters"] != entry["parameters"]
        or any(record["budget"][key] != value for key, value in identity["budget"].items())
        or result["telemetry_complete"] is not True
    ):
        raise ValueError("RunRecord provenance, parameters or telemetry differ from the trial.")
    route = result["best_route"]
    cost = result["best_cost"]
    if (route is None) != (cost is None) or (
        route is not None and (type(cost) is not int or evaluate_cost(graph, route) != cost)
    ):
        raise ValueError("RunRecord has an inconsistent candidate or cost.")
    counters = result["counters"]
    cap = identity["budget"]["max_evaluations"]
    if not 0 <= counters["evaluations_completed"] <= counters["evaluations_started"] <= cap:
        raise ValueError("RunRecord exceeds the evaluation budget.")
    if result["status"] == "success":
        first = result["timing"]["first_success"]
        limit = identity["budget"]["max_elapsed_ns"]
        if (
            cost != 0 or result["success_within_budget"] is not True or first is None
            or result["validation"]["valid"] is not True or not validate_cycle(graph, route).valid
            or not 1 <= first["evaluations_completed"] <= first["evaluations_started"]
            <= counters["evaluations_started"]
            or not 0 <= first["elapsed_ns"] <= result["timing"]["solver_ns"]
            or (limit is not None and first["elapsed_ns"] > limit)
        ):
            raise ValueError("Success lacks an independently valid certificate within the budget.")
        return "success"
    if result["status"] != "exhausted" or result["success_within_budget"] is not False:
        raise ValueError("Unknown or contradictory solver result.")
    return "cooperative_timeout" if result["stop_reason"] == "time_limit" else "exhausted"


def _finish(batch, manifest, trial, entry, attempt, graph, *, recovered=False):
    directory = batch / "attempts" / attempt["attempt_id"]
    process_path = directory / "process.json"
    process = read_json(process_path) if process_path.is_file() else {
        "outcome": "interrupted", "diagnostic": "Missing terminal supervisor journal.",
        "exit_code": None, "signal": None, "process_elapsed_ns": None, "observed": {},
    }
    outcome, diagnostic = process["outcome"], process["diagnostic"]
    publication_ns = 0
    audit_started = perf_counter_ns()
    for stream in ("stdout", "stderr"):
        path = directory / f"{stream}.txt"
        partial = directory / f"{stream}.partial"
        if process_path.is_file() and partial.exists():
            write_started = perf_counter_ns()
            partial.replace(path)
            publication_ns += perf_counter_ns() - write_started
        actual = path if path.exists() else partial
        artifact = _artifact(batch, actual) if actual.exists() else None
        attempt[f"{stream}_path"] = artifact["path"] if artifact else None
        attempt[f"{stream}_sha256"] = artifact["sha256"] if artifact else None
    files = list((directory / "cli").glob("*/run.json"))
    record_path = files[0] if len(files) == 1 else None
    stdout_path = attempt["stdout_path"]
    if record_path is None and stdout_path:
        raw = _evidence_path(batch, stdout_path)
        try:
            if read_json(raw)["schema_version"] == "fhcp-run-record/1":
                record_path = directory / "recovered-run.json"
                write_started = perf_counter_ns()
                _write_bytes(record_path, raw.read_bytes())
                publication_ns += perf_counter_ns() - write_started
        except (UnicodeError, ValueError, KeyError, TypeError):
            pass
    if (
        record_path is not None and record_path.name == "run.json" and stdout_path
        and outcome is None and record_path.read_bytes() != _evidence_path(batch, stdout_path).read_bytes()
    ):
        outcome, diagnostic = "invalid_evidence", "Saved RunRecord and stdout differ."
    if record_path is not None:
        attempt["record_path"] = record_path.relative_to(batch.parents[2]).as_posix()
        attempt["record_sha256"] = _file_hash(record_path)
        try:
            record = read_json(record_path)
            attempt["run_id"] = record["run"]["run_id"]
            classification = _audit(record, manifest, trial, entry, graph)
            if outcome is None:
                code = process["exit_code"]
                if record_path.name == "recovered-run.json":
                    outcome = "save_error"
                elif code in (0, 1, 2) and (
                    (code == 0) == (classification in {"success", "exhausted", "cooperative_timeout"})
                ):
                    outcome = classification
                else:
                    outcome = "invalid_evidence"
                diagnostic = record["result"]["stop_reason"]
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            if outcome is None:
                outcome, diagnostic = "invalid_evidence", str(error)
    if outcome is None:
        outcome = "runtime_error" if process["exit_code"] or process["signal"] else "invalid_evidence"
        diagnostic = "No valid RunRecord was recovered."
    observed = process["observed"]
    attempt.update(
        outcome=outcome, diagnostic=diagnostic, finished_at_utc=_utc(),
        state="interrupted" if not process_path.is_file() else "finished",
        exit_code=process["exit_code"], signal=process["signal"],
        external_timeout=outcome == "external_timeout",
        process_elapsed_ns=process["process_elapsed_ns"],
        capture_write_ns=None if recovered else process["capture_write_ns"] + publication_ns,
        reconciliation_ns=perf_counter_ns() - audit_started - publication_ns,
        peak_rss_bytes=observed.get("peak_rss_bytes"), load_observed=observed,
    )
    attempt["missing_metadata"] = [
        {"field": field, "reason": reason}
        for field, reason in (
            ("load_ns", "CLI preparation combines loading with other work."),
            ("process_elapsed_ns", "The supervisor did not persist a terminal time."),
            ("capture_write_ns", "Recovery cannot reconstruct the original write interval."),
            ("peak_rss_bytes", "The child did not expose a usable RSS sample."),
        ) if attempt[field] is None
    ]
    if "peak_threads" not in observed:
        attempt["missing_metadata"].append({"field": "native_threads", "reason": "No /proc thread sample."})
    attempt["artifacts"] = [
        _artifact(batch, path) for path in sorted(directory.rglob("*")) if path.is_file()
    ]


def _trial_state(trial, phase):
    required = {"primary", "verification_repeat"} if phase == "verification" else {"primary"}
    actual = {a["role"]: a["state"] for a in trial["attempts"] if a["role"] in required}
    if "started" in actual.values():
        return "started"
    if "interrupted" in actual.values():
        return "interrupted"
    if actual.keys() == required:
        return "finished"
    return "pending"


def _new_attempt(root, batch, manifest, trial, entry, role, previous, locks, graph, variables, resource_before=None):
    attempt_id = str(uuid4())
    directory = batch / "attempts" / attempt_id
    directory.mkdir(parents=True, exist_ok=False)
    attempt = {
        "attempt_id": attempt_id, "retry_of": previous["attempt_id"] if previous else None,
        "role": role, "started_at_utc": _utc(), "finished_at_utc": None,
        "state": "started", "outcome": None, "diagnostic": None,
        "command": command_for(trial, entry, directory, manifest["environment"]["affinity"][0]),
        "cwd": str(root), "variables": variables, "exit_code": None, "signal": None,
        "external_timeout": False, "run_id": None, "record_path": None, "record_sha256": None,
        "stdout_path": None, "stdout_sha256": None, "stderr_path": None, "stderr_sha256": None,
        "process_elapsed_ns": None, "capture_write_ns": None, "load_ns": None,
        "peak_rss_bytes": None, "load_observed": {}, "missing_metadata": [], "artifacts": [],
        "resource_before": resource_before,
    }
    trial["attempts"].append(attempt)
    trial["state"] = "started"
    _record_manifest(batch, manifest)
    _execute(root, directory, attempt, trial["identity"]["external_timeout_ns"], locks)
    _finish(batch, manifest, trial, entry, attempt, graph)
    trial["state"] = _trial_state(trial, manifest["phase"])
    _record_manifest(batch, manifest)
    return attempt


def _conflicts(manifest):
    seen = set()
    for trial in manifest["trials"]:
        for role in ("primary", "verification_repeat"):
            if sum(a["role"] == role for a in trial["attempts"]) > 1:
                raise ValueError(f"Duplicate {role} for trial {trial['trial_id']}.")
        for attempt in trial["attempts"]:
            run_id = attempt["run_id"]
            if run_id is not None:
                if run_id in seen:
                    raise ValueError(f"RunRecord UUID is linked twice: {run_id}.")
                seen.add(run_id)


def resume_batch(root, batch, *, retry_ids=(), close_ids=()):
    root, batch = Path(root).resolve(), Path(batch).resolve()
    if batch.parent != root / RESULTS or str(UUID(batch.name)) != batch.name:
        raise ValueError("Expected a batch UUID under experiments/results.")
    shared = root / ".tools/benchmark.lock"
    shared.parent.mkdir(exist_ok=True)
    with shared.open("a") as checkout_lock, (batch / ".lock").open("a") as batch_lock:
        locks = (checkout_lock, batch_lock)
        for lock in locks:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = read_json(batch / "manifest.json")
        if manifest["schema_version"] != SCHEMA or manifest["batch_id"] != batch.name:
            raise ValueError("Invalid batch manifest.")
        if _commit(root) != manifest["code"]["commit"] or _module_hashes(root) != manifest["code"]["modules"]:
            raise ValueError("Resume requires the original clean commit and modules.")
        for item in manifest["inputs"]:
            if _file_hash(_evidence_path(batch, item["path"])) != item["sha256"]:
                raise ValueError(f"Input artifact changed: {item['role']}.")
        input_paths = {item["role"]: _evidence_path(batch, item["path"]) for item in manifest["inputs"]}
        config_path = input_paths["config"]
        config = load_config(root, config_path)
        selection = None
        if "freeze" in input_paths:
            _, selection = load_freeze(root, input_paths["freeze"], config, config_path)
        expected = expand_plan(config, manifest["phase"], selection)
        keys = ("trial_id", "ordinal", "identity", "config_id")
        if (
            len(expected) != manifest["expected_trials"]
            or [{k: row[k] for k in keys} for row in manifest["trials"]]
            != [{k: row[k] for k in keys} for row in expected]
        ):
            raise ValueError("Batch plan differs from the approved configuration.")
        execution = config["execution"]
        profile = _profile(manifest["environment"]["affinity"][0], execution, [])
        if profile["environment_id"] != manifest["environment"]["environment_id"]:
            raise ValueError("Resume requires the original execution profile.")
        entries = {entry["config_id"]: entry for entry in config["configurations"]}
        graphs = {}
        for trial in manifest["trials"]:
            identity = trial["identity"]
            if identity["instance_id"] not in graphs:
                graphs[identity["instance_id"]] = _graph(root, identity)
        attempts = {a["attempt_id"]: (trial, a) for trial in manifest["trials"] for a in trial["attempts"]}
        if len(attempts) != sum(len(t["attempts"]) for t in manifest["trials"]):
            raise ValueError("Duplicate attempt UUID.")
        _conflicts(manifest)
        retries, closes = set(retry_ids), set(close_ids)
        if not (retries | closes) <= attempts.keys():
            raise ValueError("Unknown attempt UUID.")
        manifest["status"] = "running"
        _record_manifest(batch, manifest)
        failed = True
        try:
            for trial, attempt in attempts.values():
                if str(UUID(attempt["attempt_id"])) != attempt["attempt_id"]:
                    raise ValueError("Invalid attempt UUID.")
                if attempt["state"] == "started":
                    graph = graphs[trial["identity"]["instance_id"]]
                    _finish(batch, manifest, trial, entries[trial["config_id"]], attempt, graph, recovered=True)
                for item in attempt["artifacts"]:
                    if _file_hash(_evidence_path(batch, item["path"])) != item["sha256"]:
                        raise ValueError(f"Attempt artifact hash mismatch: {item['path']}")
                if attempt["attempt_id"] in closes:
                    if attempt["state"] != "interrupted":
                        raise ValueError("Only interrupted attempts can be closed explicitly.")
                    process_path = batch / "attempts" / attempt["attempt_id"] / "process.json"
                    if not process_path.is_file():
                        raise ValueError("Closing an interruption requires terminal supervisor evidence.")
                    graph = graphs[trial["identity"]["instance_id"]]
                    _finish(batch, manifest, trial, entries[trial["config_id"]], attempt, graph, recovered=True)
                trial["state"] = _trial_state(trial, manifest["phase"])
            if any(attempts[i][1]["state"] != "finished" for i in retries):
                raise ValueError("A diagnostic retry requires a reconciled previous attempt.")
            _conflicts(manifest)
            _record_manifest(batch, manifest)
            for trial in manifest["trials"]:
                entry = entries[trial["config_id"]]
                graph = graphs[trial["identity"]["instance_id"]]
                roles = ["primary", "verification_repeat"] if manifest["phase"] == "verification" else ["primary"]
                existing = {item["role"] for item in trial["attempts"]}
                jobs = [(role, None) for role in roles if role not in existing]
                jobs += [("diagnostic_retry", item) for item in trial["attempts"]
                         if item["attempt_id"] in retries]
                if trial["state"] == "interrupted":
                    continue
                for role, previous in jobs:
                    available = _memory_available()
                    if not _has_required_memory(available, execution["minimum_available_ram_bytes"]):
                        manifest["deviations"].append({
                            "code": "insufficient_available_ram", "observed_bytes": available,
                            "required_bytes": execution["minimum_available_ram_bytes"], "at_utc": _utc(),
                        })
                        return manifest
                    resource_before = None
                    campaign_profile = execution.get("campaign_profile")
                    if campaign_profile:
                        resource_before = resource_sample(manifest["environment"]["affinity"][0])
                        issues = resource_incidents(resource_before, resource_before, campaign_profile)
                        if issues:
                            manifest["deviations"].append(dict(code="resource_incident", issues=issues,
                                                               sample=resource_before, at_utc=_utc()))
                            return manifest
                    if _commit(root) != manifest["code"]["commit"]:
                        raise ValueError("Checkout changed before starting the next attempt.")
                    attempt = _new_attempt(root, batch, manifest, trial, entry, role, previous,
                                           locks, graph, execution["environment_variables"], resource_before)
                    if resource_before is not None:
                        after = resource_sample(manifest["environment"]["affinity"][0])
                        attempt["resource_after"] = after
                        issues = resource_incidents(resource_before, after, campaign_profile)
                        if issues:
                            manifest["deviations"].append(dict(code="resource_incident", issues=issues,
                                                               attempt_id=attempt["attempt_id"], at_utc=_utc()))
                            return manifest
                    _conflicts(manifest)
                    try:
                        unchanged = _commit(root) == manifest["code"]["commit"]
                    except ValueError:
                        unchanged = False
                    if not unchanged:
                        manifest["deviations"].append({"code": "checkout_changed", "at_utc": _utc()})
                        raise ValueError("Checkout changed during an attempt.")
                    if attempt["state"] == "interrupted" or attempt["outcome"] == "interrupted":
                        return manifest
            failed = False
            return manifest
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            manifest["deviations"].append({"code": "batch_error", "diagnostic": str(error), "at_utc": _utc()})
            raise
        finally:
            clean = not failed and not any(
                item["code"] == "checkout_changed" for item in manifest["deviations"]
            )
            manifest["status"] = "complete" if clean and all(
                t["state"] == "finished" for t in manifest["trials"]
            ) else "incomplete"
            manifest["artifacts"] = [
                item for trial in manifest["trials"] for attempt in trial["attempts"]
                for item in attempt["artifacts"]
            ]
            _record_manifest(batch, manifest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run")
    run.add_argument("--config", type=Path, default=_ROOT / CONFIG)
    run.add_argument("--phase", choices=("smoke", "tuning", "evaluation", "scale", "verification"), required=True)
    run.add_argument("--cpu", type=int, required=True)
    run.add_argument("--freeze", type=Path)
    resume = sub.add_parser("resume")
    resume.add_argument("batch", type=Path)
    resume.add_argument("--retry", action="append", default=[], metavar="ATTEMPT_ID")
    resume.add_argument("--close-interrupted", action="append", default=[], metavar="ATTEMPT_ID")
    args = parser.parse_args(argv)
    try:
        if args.action == "run":
            batch = create_batch(_ROOT, args.config, args.phase, args.cpu, args.freeze)
            print(f"Batch: {batch}", file=sys.stderr, flush=True)
            manifest = resume_batch(_ROOT, batch)
        else:
            batch = args.batch
            manifest = resume_batch(_ROOT, batch, retry_ids=args.retry, close_ids=args.close_interrupted)
        outcomes = Counter(attempt["outcome"] for trial in manifest["trials"]
                           for attempt in trial["attempts"] if attempt["outcome"] is not None)
        print(json.dumps({"batch": str(batch), "status": manifest["status"],
                          "trial_states": dict(Counter(t["state"] for t in manifest["trials"])),
                          "attempt_outcomes": dict(outcomes)}))
        return int(manifest["status"] != "complete")
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, KeyError, TypeError, GraphError, ReaderError, subprocess.SubprocessError) as error:
        print(f"batch_error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
