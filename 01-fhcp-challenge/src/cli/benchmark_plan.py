"""Validation and deterministic identities for the accepted FHCP M6 plan."""

from hashlib import sha256
from itertools import product
import json
from math import fsum
from pathlib import Path

from .variants import VARIANTS


CONFIG = Path("experiments/configs/benchmark-v1.json")
PROTOCOL = Path("docs/decisions/benchmark-protocol.md")
PROTOCOL_V2 = Path("docs/decisions/benchmark-protocol-v2.md")
PROTOCOL_V3 = Path("docs/decisions/benchmark-protocol-v3.md")
# Canonical content of the configuration accepted in PR #72. Whitespace is free.
_V1_DIGEST = "f0984af3d1c50be0488f5aa95efea39122233f8064bd508d7ef4ff42055bb6d3"
_V2_DIGEST = "cea4b1f93bf5058ed057dda0780de5a73d591ee8f8aedde939d48a8d2d7e5445"
# Laptop plan; review the accompanying decision before starting a campaign.
_V3_DIGEST = "ee6b3889e7828112773bc2f4d5c9c732ded0f8f3f7499f66f6b000c946c8fe2a"


def protocol_path(config):
    return {"fhcp-m6-v1": PROTOCOL, "fhcp-m6-v2": PROTOCOL_V2,
            "fhcp-m6-v3": PROTOCOL_V3}[config["protocol_id"]]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(value):
    return sha256(canonical(value)).hexdigest()


def _unique(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(f"Duplicate JSON key: {name}")
        result[name] = value
    return result


def _nonfinite(value):
    raise ValueError(f"Nonfinite JSON constant: {value}")


def read_json(path):
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique,
                       parse_constant=_nonfinite)
    canonical(value)  # Also rejects values such as 1e999, parsed as infinity.
    return value


def checked_path(root, value):
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not (root / path).resolve().is_relative_to(root):
        raise ValueError(f"Expected a path inside the repository: {value}")
    return root / path


def load_config(root, path):
    config = read_json(path)
    if digest(config) not in {_V1_DIGEST, _V2_DIGEST, _V3_DIGEST}:
        raise ValueError("Configuration differs from the accepted M6 plans.")
    dataset = config["dataset_manifest"]
    source = checked_path(root, dataset["path"])
    if sha256(source.read_bytes()).hexdigest() != dataset["sha256"]:
        raise ValueError("Dataset manifest differs from the accepted plan.")
    if config["algorithms"] != list(VARIANTS):
        raise ValueError("Installed solver families differ from the accepted plan.")
    for entry in config["configurations"]:
        spec = VARIANTS[entry["algorithm"]]
        if (
            (entry["family"], entry["variant"], entry["iteration_unit"])
            != (spec.family, spec.name, spec.iteration_unit)
            or canonical(spec.resolve(entry["parameters"])) != canonical(entry["parameters"])
        ):
            raise ValueError(f"Solver contract differs for {entry['config_id']}.")
    return config


def load_freeze(root, path, config, config_path):
    freeze = read_json(path)
    required = {"schema_version", "protocol_id", "created_at_utc", "config_sha256",
                "protocol_sha256", "tuning_batches", "selection", "code", "environment",
                "seeds_decimal", "budgets", "artifacts"}
    if (
        not isinstance(freeze, dict) or freeze.keys() != required
        or freeze["schema_version"] != "fhcp-benchmark-freeze/1"
        or freeze["protocol_id"] != config["protocol_id"]
        or freeze["config_sha256"] != sha256(config_path.read_bytes()).hexdigest()
        or freeze["protocol_sha256"] != sha256((root / protocol_path(config)).read_bytes()).hexdigest()
        or freeze["seeds_decimal"] != config["phases"]["evaluation"]["seeds_decimal"]
        or freeze["budgets"] != {p: config["phases"][p]["budget"] for p in ("evaluation", "scale")}
        or not isinstance(freeze["created_at_utc"], str) or not freeze["created_at_utc"]
        or not isinstance(freeze["code"], dict) or freeze["code"].get("dirty") is not False
        or not isinstance(freeze["environment"], dict) or not freeze["environment"].get("environment_id")
    ):
        raise ValueError("Freeze is incomplete or differs from the accepted protocol.")
    entries = {item["config_id"]: item for item in config["configurations"]}
    selected = {}
    for row in freeze["selection"]:
        entry = entries.get(row["config_id"])
        score = row["score"]
        if (
            entry is None or row["algorithm"] != entry["algorithm"]
            or row["algorithm"] in selected
            or canonical(row["parameters"]) != canonical(entry["parameters"])
            or set(score) != {"successes", "errors", "mean_normalized_cost", "ordinal"}
            or any(type(score[k]) is not int or not 0 <= score[k] <= 10 for k in ("successes", "errors"))
            or score["errors"] == 10 or score["successes"] + score["errors"] > 10
            or type(score["mean_normalized_cost"]) not in (int, float)
            or not 0 <= score["mean_normalized_cost"] <= 1
            or score["ordinal"] != int(entry["config_id"][-1])
        ):
            raise ValueError("Invalid frozen configuration or score.")
        selected[row["algorithm"]] = entry
    if set(selected) != set(VARIANTS):
        raise ValueError("Freeze must select exactly one candidate per family.")
    tuning_ids = set()
    evidence = []
    run_ids = set()
    attempt_ids = set()
    expected = {t["trial_id"]: t for t in expand_plan(config, "tuning")}
    seen_batches = set()
    for row in freeze["tuning_batches"]:
        manifest_path = checked_path(root, row["manifest_path"])
        if sha256(manifest_path.read_bytes()).hexdigest() != row["manifest_sha256"]:
            raise ValueError("Tuning manifest hash differs from the freeze.")
        manifest = read_json(manifest_path)
        if (
            manifest["schema_version"] != "fhcp-batch-manifest/1"
            or manifest["batch_id"] != row["batch_id"] or row["batch_id"] in seen_batches
            or manifest["protocol_id"] != config["protocol_id"]
            or manifest["phase"] != "tuning" or manifest["status"] != "complete"
            or manifest["code"]["dirty"] is not False
            or manifest["code"]["modules"] != freeze["code"]["modules"]
            or manifest["code"]["commit"] != freeze["code"]["commit"]
            or manifest["environment"]["environment_id"] != freeze["environment"]["environment_id"]
        ):
            raise ValueError("Freeze references incompatible or repeated tuning evidence.")
        seen_batches.add(row["batch_id"])
        # Resolve every planned primary from original, hash-checked evidence.
        # A top-level "complete" flag cannot establish a valid tuning freeze.
        from .batch import _audit, _graph
        if manifest["expected_trials"] != len(expected) or len(manifest["trials"]) != len(expected):
            raise ValueError("Tuning manifest has an incomplete trial inventory.")
        for item in manifest["inputs"] + manifest["artifacts"]:
            artifact_path = checked_path(root, item["path"])
            if not artifact_path.resolve().is_relative_to(manifest_path.parent):
                raise ValueError("Tuning evidence escapes its batch.")
            if sha256(artifact_path.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError("Tuning evidence hash mismatch.")
        graphs = {}
        for trial in manifest["trials"]:
            planned = expected.get(trial["trial_id"])
            keys = ("trial_id", "ordinal", "identity", "config_id")
            if (planned is None or trial["trial_id"] in tuning_ids or trial["state"] != "finished"
                or any(trial[k] != planned[k] for k in keys)):
                raise ValueError("Freeze contains incomplete, changed or duplicated tuning trials.")
            tuning_ids.add(trial["trial_id"])
            primaries = [a for a in trial["attempts"] if a["role"] == "primary"]
            if len(primaries) != 1 or primaries[0]["state"] != "finished":
                raise ValueError("Tuning trial lacks a reconciled primary.")
            primary = primaries[0]
            if primary["attempt_id"] in attempt_ids:
                raise ValueError("Duplicated primary attempt.")
            attempt_ids.add(primary["attempt_id"])
            for item in primary["artifacts"]:
                artifact_path = checked_path(root, item["path"])
                if not artifact_path.resolve().is_relative_to(manifest_path.parent):
                    raise ValueError("Primary evidence escapes its batch.")
                if sha256(artifact_path.read_bytes()).hexdigest() != item["sha256"]:
                    raise ValueError("Primary artifact hash mismatch.")
            name = trial["identity"]["instance_id"]
            graph = graphs.setdefault(name, None)
            if graph is None:
                graph = graphs[name] = _graph(root, trial["identity"])
            entry = entries[trial["config_id"]]
            record = None
            if primary["record_path"] is not None:
                record_path = checked_path(root, primary["record_path"])
                if not record_path.resolve().is_relative_to(manifest_path.parent):
                    raise ValueError("RunRecord escapes its batch.")
                if sha256(record_path.read_bytes()).hexdigest() != primary["record_sha256"]:
                    raise ValueError("Primary RunRecord hash mismatch.")
                record = read_json(record_path)
                if record["run"]["run_id"] != primary["run_id"] or primary["run_id"] in run_ids:
                    raise ValueError("Duplicated or mismatched RunRecord identity.")
                run_ids.add(primary["run_id"])
                try:
                    classification = _audit(record, manifest, trial, entry, graph)
                except (ValueError, KeyError, TypeError, AttributeError):
                    if primary["outcome"] != "invalid_evidence":
                        raise
                    classification = "invalid_evidence"
                if primary["outcome"] in {"success", "exhausted", "cooperative_timeout"} and classification != primary["outcome"]:
                    raise ValueError("Primary outcome contradicts its RunRecord.")
            elif primary["outcome"] in {"success", "exhausted", "cooperative_timeout"}:
                raise ValueError("Normal tuning outcome requires a RunRecord.")
            if not primary["artifacts"] or not any(Path(a["path"]).name == "process.json" for a in primary["artifacts"]):
                raise ValueError("Primary requires terminal supervisor evidence.")
            error = primary["outcome"] not in {"success", "exhausted", "cooperative_timeout"}
            cost = 1 if error or record is None or record["result"]["best_cost"] is None else record["result"]["best_cost"] / graph.vertex_count()
            evidence.append((entry["config_id"], primary["outcome"] == "success", error, cost))
    scores = {}
    for config_id, entry in entries.items():
        observations = [row for row in evidence if row[0] == config_id]
        if len(observations) != 10:
            raise ValueError("Each candidate requires ten reconciled primaries.")
        scores[config_id] = dict(successes=sum(r[1] for r in observations),
                                 errors=sum(r[2] for r in observations),
                                 mean_normalized_cost=fsum(r[3] for r in observations) / 10,
                                 ordinal=int(config_id[-1]))
    for row in freeze["selection"]:
        candidates = [e for e in config["configurations"] if e["algorithm"] == row["algorithm"]]
        def key(entry):
            score = scores[entry["config_id"]]
            return -score["successes"], score["errors"], score["mean_normalized_cost"], score["ordinal"]
        winner = min(candidates, key=key)
        if row["config_id"] != winner["config_id"] or row["score"] != scores[winner["config_id"]]:
            raise ValueError("Frozen selection or scores differ from audited tuning primaries.")
    if tuning_ids != {trial["trial_id"] for trial in expand_plan(config, "tuning")}:
        raise ValueError("Freeze must account for all planned tuning trials.")
    if not freeze["artifacts"]:
        raise ValueError("Freeze requires selection and audit artifacts.")
    for artifact in freeze["artifacts"]:
        if sha256(checked_path(root, artifact["path"]).read_bytes()).hexdigest() != artifact["sha256"]:
            raise ValueError("Freeze artifact hash mismatch.")
    return freeze, selected


def expand_plan(config, phase, selection=None):
    """Materialize the phase without using the solver RNG or observed outcomes."""
    rules = config["phases"][phase]
    source = rules["configuration_source"]
    if source == "frozen_selection":
        if selection is None:
            raise ValueError(f"{phase} requires a complete freeze.")
        entries = [selection[algorithm] for algorithm in config["algorithms"]]
    elif source == "all_candidates":
        entries = config["configurations"]
    else:
        entries = [item for item in config["configurations"] if item["config_id"].endswith("-c1")]
    instance_hashes = {item["id"]: item["sha256"] for item in config["instances"]}
    trials = []
    for instance, entry, seed in product(rules["instances"], entries, rules["seeds_decimal"]):
        configuration = {key: entry[key] for key in ("algorithm", "family", "variant", "parameters")}
        identity = {
            "protocol_id": config["protocol_id"], "phase": phase,
            "instance_id": instance, "instance_sha256": instance_hashes[instance],
            "algorithm": entry["algorithm"], "variant": entry["variant"],
            "configuration_sha256": digest(configuration), "seed_decimal": seed,
            "budget": dict(rules["budget"]), "external_timeout_ns": rules["external_timeout_ns"],
        }
        trials.append({
            "trial_id": digest(identity), "identity": identity, "config_id": entry["config_id"],
            "state": "pending", "attempts": [],
        })
    def order(trial):
        trial_id = trial["trial_id"]
        key = f"{config['protocol_id']}\n{phase}\n{trial_id}".encode("utf-8")
        return sha256(key).hexdigest(), trial_id

    trials.sort(key=order)
    if len({row["trial_id"] for row in trials}) != rules["expected_trials"]:
        raise ValueError("Expanded trial identities differ from the approved count.")
    for ordinal, trial in enumerate(trials):
        trial["ordinal"] = ordinal
    return trials
