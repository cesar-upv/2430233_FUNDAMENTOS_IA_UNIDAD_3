"""Repeat the public FHCP CLI in separate processes and audit its result."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.graphs import check_route_legality, load_fhcp_graph


_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def fhcp_attempts(tmp_path_factory):
    output = tmp_path_factory.mktemp("ga-reproducibility")
    command = [
        sys.executable, "-m", "src.cli",
        "--instance", "graph1", "--seed", "17",
        "--population-size", "8", "--tournament-size", "3",
        "--max-evaluations", "20", "--output-dir", str(output),
    ]
    records = []
    for _ in range(2):
        process = subprocess.run(
            command, cwd=_ROOT, capture_output=True, text=True,
            encoding="utf-8", timeout=30,
        )
        assert process.returncode == 0, process.stderr
        assert process.stderr == ""
        records.append(json.loads(process.stdout))
    return output, records


def test_fhcp_cli_repeats_result_and_preserves_both_attempts(fhcp_attempts):
    output, (first, repeated) = fhcp_attempts
    for field in ("instance", "procedure", "randomness", "budget", "code", "environment"):
        assert first[field] == repeated[field]
    for record in (first, repeated):
        assert record["randomness"]["seed_decimal"] == "17"
        assert record["budget"] == {
            "max_elapsed_ns": None, "max_evaluations": 20, "max_iterations": None,
            "time_scope": "solver_including_initialization_and_validation",
        }
        assert record["procedure"]["parameters"] == {
            "population_size": 8, "tournament_size": 3,
            "crossover_rate": 0.8, "mutation_rate": 0.010, "elite_count": 1,
        }
    first_result = {field: value for field, value in first["result"].items() if field != "timing"}
    repeated_result = {field: value for field, value in repeated["result"].items() if field != "timing"}
    assert first_result == repeated_result
    assert first["run"]["run_id"] != repeated["run"]["run_id"]
    assert len(list(output.iterdir())) == 2
    for record in (first, repeated):
        saved = output / record["run"]["run_id"] / "run.json"
        assert json.loads(saved.read_text(encoding="utf-8")) == record


def test_exhausted_fhcp_result_has_independently_checked_cost_and_counters(fhcp_attempts):
    _, records = fhcp_attempts
    graph = load_fhcp_graph("graph1", root=_ROOT)
    for record in records:
        assert record["instance"]["sha256"] == graph.source["sha256"]
        assert record["instance"]["manifest_revision"] == graph.source["manifest_revision"]
        result = record["result"]
        assert result["status"] == "exhausted"
        assert result["stop_reason"] == "evaluation_limit"
        assert result["limits_reached"] == ["evaluation_limit"]
        assert result["success_within_budget"] is False
        assert result["error"] is None
        route = result["best_route"]
        assert check_route_legality(graph.vertex_count(), route).valid
        # Recount every cyclic pair directly, independently of the fitness API.
        missing = sum(
            not graph.has_edge(route[position], route[(position + 1) % len(route)])
            for position in range(len(route))
        )
        assert result["best_cost"] == missing > 0
        assert result["validation"]["valid"] is None
        assert result["validation"]["reason"] == "not_run"
        counters = result["counters"]
        assert counters["evaluations_started"] == counters["evaluations_completed"] == 20
        assert counters["full_evaluations"] == 20
        assert counters["incremental_evaluations"] == counters["cache_hits"] == 0
        assert counters["validations_started"] == counters["validations_completed"] == 0
        assert counters["iteration_unit"] == "generation"
        assert counters["iterations_completed"] == 1
        assert counters["partial_iteration"] == {
            "phase": "generation", "completed_items": 5, "planned_items": 7,
        }
        assert counters["restarts"] == 0
        assert result["timing"]["first_success"] is None
