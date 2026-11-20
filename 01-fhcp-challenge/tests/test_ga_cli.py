"""Verify the GA command, RunRecord provenance and failure paths."""

from dataclasses import replace
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID

import pytest

from src.cli import __main__ as cli
from src.cli import run_record


_ROOT = Path(__file__).resolve().parents[1]
_ARGS = ["--instance", "graph1", "--seed", "17", "--population-size", "8",
         "--tournament-size", "3", "--max-evaluations", "20"]


def _invoke(*args):
    return subprocess.run(
        [sys.executable, "-m", "src.cli", *_ARGS, *map(str, args)],
        cwd=_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
    )


def _parse(payload):
    def reject_constant(value):
        pytest.fail(f"Non-finite value in JSON: {value}")

    return json.loads(payload, parse_constant=reject_constant)


def test_real_command_emits_run_record_with_effective_parameters_and_verified_provenance():
    proc = _invoke("--seed", 2**64 - 1)
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    record = _parse(proc.stdout)
    assert record["schema_version"] == "fhcp-run-record/1"
    assert UUID(record["run"]["run_id"]).version == 4
    assert datetime.fromisoformat(record["run"]["started_at_utc"]).utcoffset().total_seconds() == 0
    assert record["randomness"]["seed_decimal"] == str(2**64 - 1)
    assert record["randomness"]["generator"] == "PCG64"
    assert record["procedure"]["parameters"] == {
        "population_size": 8, "tournament_size": 3, "crossover_rate": 0.8,
        "mutation_rate": 0.010, "elite_count": 1,
    }
    instance = record["instance"]
    assert (instance["id"], instance["n"], instance["m"]) == ("graph1", 66, 99)
    assert instance["source_path"] == "data/raw/FHCPCS/graph1.hcp"
    assert instance["sha256"] == sha256((_ROOT / instance["source_path"]).read_bytes()).hexdigest()
    manifest = _ROOT / "docs/decisions/fhcp-instances.json"
    assert instance["manifest_revision"] == sha256(manifest.read_bytes()).hexdigest()
    code = record["code"]
    if code["commit"] is not None:
        assert len(code["commit"]) in (40, 64) and int(code["commit"], 16) > 0
    else:
        assert any(entry["field"] == "code.commit" for entry in record["missing_metadata"])
    assert record["environment"]["python_version"] == ".".join(map(str, sys.version_info[:3]))
    assert record["environment"]["dependencies"]["numpy"] == record["randomness"]["library_version"]
    assert record["budget"]["max_evaluations"] == 20
    result = record["result"]
    assert result["schema_version"] == "fhcp-solver-result/1"
    assert (result["status"], result["stop_reason"]) == ("exhausted", "evaluation_limit")
    assert result["counters"]["evaluations_completed"] == 20
    assert sorted(result["best_route"]) == list(range(66))
    assert result["success_within_budget"] is False
    timing = record["timing"]
    assert timing["total_ns"] >= timing["preparation_ns"] + result["timing"]["solver_ns"] + timing["finalization_ns"]


def test_saves_exhausted_and_failed_attempts_with_distinct_ids(tmp_path):
    output = tmp_path / "records with spaces"
    first = _invoke("--output-dir", output)
    failure = _invoke("--instance", "unselected-instance", "--output-dir", output)
    assert first.returncode == 0, first.stderr
    assert failure.returncode == 1
    records = [_parse(first.stdout), _parse(failure.stdout)]
    assert len(list(output.iterdir())) == 2
    for record in records:
        path = output / record["run"]["run_id"] / "run.json"
        assert _parse(path.read_text(encoding="utf-8")) == record
        assert list(path.parent.iterdir()) == [path]
    failed = records[1]
    assert failed["result"]["stop_reason"] == "invalid_input"
    assert failed["result"]["error"]["code"] == "manifest_mismatch"
    assert "manifest_mismatch" in failure.stderr
    assert failed["instance"]["sha256"] is None
    assert any(entry["field"] == "instance.sha256" for entry in failed["missing_metadata"])


@pytest.mark.parametrize(("args", "code", "parameter"), [
    (["--seed", "-1"], "invalid_seed", "seed"),
    (["--max-evaluations", "0"], "invalid_budget", "max_evaluations"),
    (["--crossover-rate", "nan"], "invalid_parameter", "crossover_rate"),
    (["--tournament-size", "9"], "invalid_parameter", "tournament_size"),
])
def test_invalid_configuration_returns_a_record_and_does_not_load_graph(args, code, parameter, monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_fhcp_graph", lambda *a, **kw: pytest.fail("Graph loading began"))
    assert cli.main([*_ARGS, *args]) == 2
    captured = capsys.readouterr()
    record = _parse(captured.out)
    assert record["result"]["stop_reason"] == "invalid_config"
    assert record["result"]["error"]["code"] == code
    assert record["result"]["error"]["detail"]["parameter"] == parameter
    assert record["result"]["counters"]["evaluations_started"] == 0
    assert code in captured.err


def test_requires_a_budget_and_reports_malformed_arguments(capsys):
    assert cli.main(_ARGS[:-2]) == 2
    assert _parse(capsys.readouterr().out)["result"]["error"]["code"] == "invalid_budget"
    with pytest.raises(SystemExit, match="2"):
        cli.main([*_ARGS, "--seed", "not-an-integer"])
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--seed" in captured.err and "invalid int value" in captured.err


@pytest.fixture
def triangle_checkout(tmp_path, monkeypatch):
    manifest_path = tmp_path / "docs/decisions/fhcp-instances.json"
    manifest_path.parent.mkdir(parents=True)
    graph_path = tmp_path / "data/raw/FHCPCS/triangle.hcp"
    graph_path.parent.mkdir(parents=True)
    hcp = b"TYPE:HCP\nDIMENSION:3\nEDGE_DATA_FORMAT:EDGE_LIST\nEDGE_DATA_SECTION\n1 2\n2 3\n3 1\n-1\nEOF\n"
    graph_path.write_bytes(hcp)
    entry = {"id": "triangle", "archive_member": graph_path.name, "sha256": sha256(hcp).hexdigest(),
             "dimension": 3, "edge_count": 3}
    manifest_path.write_text(json.dumps({"manifest_version": 1, "instances": [entry]}), encoding="utf-8")
    monkeypatch.setattr(cli, "_ROOT", tmp_path)
    return graph_path


def test_success_is_certified_using_only_a_graph_and_manifest(triangle_checkout, capsys):
    assert cli.main([*_ARGS, "--instance", "triangle", "--max-evaluations", "1"]) == 0
    result = _parse(capsys.readouterr().out)["result"]
    assert result["status"] == "success" and result["success_within_budget"] is True
    assert result["validation"]["valid"] is True
    assert result["counters"]["validations_completed"] == 1


def test_corrupted_graph_is_rejected_before_search(triangle_checkout, monkeypatch, capsys):
    with triangle_checkout.open("ab") as stream:
        stream.write(b"\n")
    monkeypatch.setitem(cli.VARIANTS, "ga", replace(
        cli.VARIANTS["ga"], solve=lambda *a, **kw: pytest.fail("The GA started with unverified bytes"),
    ))
    assert cli.main([*_ARGS, "--instance", "triangle"]) == 1
    record = _parse(capsys.readouterr().out)
    assert record["result"]["error"]["code"] == "source_hash_mismatch"
    assert record["result"]["counters"]["evaluations_started"] == 0


def test_existing_attempt_is_never_overwritten(tmp_path):
    run_id = "existing-attempt"
    path = run_record.save_record(tmp_path, run_id, '{"value": 1}\n')
    with pytest.raises(FileExistsError):
        run_record.save_record(tmp_path, run_id, '{"value": 2}\n')
    assert path.read_text(encoding="utf-8") == '{"value": 1}\n'


def test_output_failure_keeps_json_on_stdout(tmp_path):
    target = tmp_path / "existing-file"
    target.write_text("keep", encoding="utf-8")
    proc = _invoke("--output-dir", target)
    assert proc.returncode == 1
    assert "output_error" in proc.stderr
    assert _parse(proc.stdout)["result"]["status"] == "exhausted"
    assert target.read_text(encoding="utf-8") == "keep"


def test_missing_git_metadata_has_field_level_reasons(monkeypatch, capsys):
    def git_unavailable(*args):
        raise FileNotFoundError("git")

    monkeypatch.setattr(run_record, "_git", git_unavailable)
    assert cli.main(_ARGS) == 0
    record = _parse(capsys.readouterr().out)
    assert record["code"] == {"commit": None, "dirty": None, "patch_sha256": None}
    fields = {item["field"] for item in record["missing_metadata"] if item["reason"]}
    assert fields >= {"code.commit", "code.dirty", "code.patch_sha256",
                      "environment.native_threads", "environment.concurrent_workload"}


def test_dirty_snapshot_includes_new_file_contents(tmp_path, monkeypatch):
    def git_output(root, command, *args):
        return {"diff": b"tracked patch", "ls-files": b"new.py\0"}[command]

    monkeypatch.setattr(run_record, "_git", git_output)
    new_file = tmp_path / "new.py"
    new_file.write_bytes(b"x = 1\n")
    first = run_record._dirty_hash(tmp_path)
    new_file.write_bytes(b"x = 2\n")
    assert run_record._dirty_hash(tmp_path) != first


def test_interrupted_solver_retains_attempt_with_unknown_telemetry(monkeypatch, capsys):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setitem(cli.VARIANTS, "ga", replace(cli.VARIANTS["ga"], solve=interrupted))
    assert cli.main(_ARGS) == 130
    record = _parse(capsys.readouterr().out)
    result = record["result"]
    assert result["stop_reason"] == "external_termination"
    assert result["telemetry_complete"] is False
    assert result["counters"] is None and result["timing"]["solver_ns"] is None
    assert record["instance"]["sha256"] and record["run"]["run_id"]
