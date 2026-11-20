"""Exercise the selected FHCP checkout and the complete certification pipeline."""

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from src.evaluation import CycleValidationResult, validate_cycle
from src.graphs import (
    GraphError,
    ReaderError,
    load_fhcp_certificate,
    load_fhcp_graph,
    read_hcp,
    read_tour,
    route_to_external,
    route_to_internal,
)


_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST = Path("docs/decisions/fhcp-instances.json")
_INSTANCES = json.loads((_ROOT / _MANIFEST).read_text(encoding="utf-8"))["instances"]
_FIXTURES = Path(__file__).parent / "fixtures/fhcp"
_MEMBERS = [
    pytest.param(directory, record, id=f"{entry['id']}-{kind}")
    for entry in _INSTANCES
    for kind, directory, record in (
        ("graph", "FHCPCS", entry),
        ("certificate", "FHCPCS_sols", entry["certificate"]),
    )
]


def _write_tour(path, labels):
    """Write a controlled candidate, including malformed labels when requested."""
    lines = ["TYPE : TOUR", "DIMENSION : 5", "TOUR_SECTION"]
    lines.extend(str(label) for label in labels)
    path.write_bytes(("\n".join([*lines, "-1", "EOF"]) + "\n").encode("ascii"))
    return path


def _certify_files(graph_path, tour_path):
    graph = read_hcp(graph_path)
    labels = read_tour(tour_path, graph)
    route = route_to_internal(graph, labels)
    return validate_cycle(graph, route)


def test_selection_covers_the_nine_agreed_graphs_and_eighteen_members():
    assert len(_INSTANCES) == 9
    assert {entry["id"] for entry in _INSTANCES} == {
        "graph1", "graph2", "graph58", "graph268", "graph48",
        "graph175", "graph74", "graph479", "graph1001",
    }
    assert len(_MEMBERS) == 18


@pytest.mark.parametrize("directory,record", _MEMBERS)
def test_selected_member_matches_original_bytes(directory, record):
    payload = (_ROOT / "data/raw" / directory / record["archive_member"]).read_bytes()
    assert len(payload) == record["size_bytes"]
    assert hashlib.sha256(payload).hexdigest() == record["sha256"]


@pytest.mark.parametrize("entry", _INSTANCES, ids=lambda entry: entry["id"])
def test_selected_fhcp_certificate_passes_the_complete_pipeline(entry, tmp_path, monkeypatch):
    # Loaders must resolve the checkout independently of the current directory.
    monkeypatch.chdir(tmp_path)
    graph = load_fhcp_graph(entry["id"])
    assert (graph.vertex_count(), graph.edge_count()) == (entry["dimension"], entry["edge_count"])
    assert graph.source["instance_id"] == entry["id"]
    assert graph.source["sha256"] == entry["sha256"]

    # Certificates are an explicit second operation, never an input to graph loading.
    labels = load_fhcp_certificate(graph)
    certificate_path = _ROOT / "data/raw/FHCPCS_sols" / entry["certificate"]["archive_member"]
    assert labels == read_tour(certificate_path, graph)
    route = route_to_internal(graph, labels)
    assert route_to_external(graph, route) == labels
    assert validate_cycle(graph, route) == CycleValidationResult(True)


def test_real_graph_can_be_loaded_without_a_certificate_directory(tmp_path):
    manifest_path = tmp_path / _MANIFEST
    manifest_path.parent.mkdir(parents=True)
    shutil.copyfile(_ROOT / _MANIFEST, manifest_path)
    entry = next(entry for entry in _INSTANCES if entry["id"] == "graph1")
    graph_path = tmp_path / "data/raw/FHCPCS" / entry["archive_member"]
    graph_path.parent.mkdir(parents=True)
    shutil.copyfile(_ROOT / "data/raw/FHCPCS" / entry["archive_member"], graph_path)

    graph = load_fhcp_graph("graph1", root=tmp_path)
    assert graph.vertex_count() == entry["dimension"]
    assert not (tmp_path / "data/raw/FHCPCS_sols").exists()
    with pytest.raises(FileNotFoundError):
        load_fhcp_certificate(graph, root=tmp_path)


def test_controlled_files_certify_a_known_cycle():
    assert _certify_files(_FIXTURES / "control.hcp", _FIXTURES / "control.hcp.tou") == CycleValidationResult(True)


@pytest.mark.parametrize(
    "labels,expected",
    [
        pytest.param((1, 2, 4, 5), CycleValidationResult(False, "invalid_length"), id="missing-vertex"),
        pytest.param((1, 2, 4, 2, 3), CycleValidationResult(False, "repeated_vertex", 3, (1,)), id="repeated-vertex"),
        pytest.param((1, 2, 4, 3, 5), CycleValidationResult(False, "missing_edge", 3, (2, 4)), id="missing-internal-edge"),
        pytest.param((2, 1, 3, 4, 5), CycleValidationResult(False, "missing_closing_edge", 4, (4, 1)), id="invalid-closure"),
    ],
)
def test_controlled_tour_is_rejected_after_reading_and_conversion(tmp_path, labels, expected):
    tour_path = _write_tour(tmp_path / "candidate.hcp.tou", labels)
    assert _certify_files(_FIXTURES / "control.hcp", tour_path) == expected


def test_unknown_external_label_is_rejected_during_conversion(tmp_path):
    graph = read_hcp(_FIXTURES / "control.hcp")
    labels = read_tour(_write_tour(tmp_path / "unknown.hcp.tou", (1, 2, 3, 4, 6)), graph)
    assert labels == (1, 2, 3, 4, 6)
    with pytest.raises(GraphError) as error:
        route_to_internal(graph, labels)
    assert error.value.code == "unknown_label"


def test_malformed_graph_stops_the_file_pipeline(tmp_path):
    lines = (_FIXTURES / "control.hcp").read_text(encoding="ascii").splitlines()
    lines[5] = "1 2 3"
    path = tmp_path / "malformed.hcp"
    path.write_bytes(("\n".join(lines) + "\n").encode("ascii"))
    with pytest.raises(ReaderError) as error:
        _certify_files(path, _FIXTURES / "control.hcp.tou")
    assert (error.value.code, error.value.line) == ("malformed_edge_line", 6)


def test_malformed_tour_stops_the_file_pipeline(tmp_path):
    tour_path = _write_tour(tmp_path / "malformed.hcp.tou", (1, 2, "x", 4, 5))
    with pytest.raises(ReaderError) as error:
        _certify_files(_FIXTURES / "control.hcp", tour_path)
    assert (error.value.code, error.value.line) == ("malformed_tour_line", 6)


def test_path_graph_loads_but_its_hamiltonian_path_is_not_a_cycle():
    # The two degree-one endpoints make this controlled graph non-Hamiltonian.
    expected = CycleValidationResult(False, "missing_closing_edge", 4, (4, 0))
    assert _certify_files(_FIXTURES / "path.hcp", _FIXTURES / "control.hcp.tou") == expected
