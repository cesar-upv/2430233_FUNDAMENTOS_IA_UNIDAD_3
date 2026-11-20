"""Verify selection and integrity without downloading or altering FHCP originals."""

import hashlib
import json

import pytest

from src.graphs import Graph, GraphError, load_fhcp_certificate, load_fhcp_graph


_ID = "selected-id"
_MANIFEST = "docs/decisions/fhcp-instances.json"


def write_manifest(root, manifest):
    (root / _MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")


@pytest.fixture
def selection(tmp_path):
    def member(directory, name, payload):
        path = tmp_path / "data/raw" / directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return {"archive_member": name, "sha256": hashlib.sha256(payload).hexdigest()}

    hcp = b"NAME : unrelated-header\r\nTYPE : HCP\r\nDIMENSION : 3\r\n"
    hcp += b"EDGE_DATA_FORMAT : EDGE_LIST\r\nEDGE_DATA_SECTION\r\n1 2\r\n2 3\r\n3 1\r\n-1\r\nEOF\r\n"
    tour = b"TYPE : TOUR\nDIMENSION : 3\nTOUR_SECTION\n3\n1\n2\n-1\nEOF\n"
    graph = member("FHCPCS", "fixture.hcp", hcp)
    certificate = member("FHCPCS_sols", "reference.hcp.tou", tour)
    manifest = {
        "manifest_version": 1,
        "instances": [dict(graph, id=_ID, dimension=3, edge_count=3, certificate=certificate)],
    }
    (tmp_path / _MANIFEST).parent.mkdir(parents=True)
    write_manifest(tmp_path, manifest)
    return tmp_path, manifest


def test_graph1_matches_versioned_selection(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    graph = load_fhcp_graph("graph1")
    assert (graph.vertex_count(), graph.edge_count()) == (66, 99)
    assert graph.source["instance_id"] == "graph1"
    assert graph.source["sha256"] == "124c185cebd9782e037bf16c88cb26002352e10e3ab634bf51ff481296c2e0b2"
    assert graph.external_label(0) == 1 and graph.external_label(65) == 66


def test_selection_uses_manifest_members_and_keeps_tour_external(selection):
    root, manifest = selection
    graph = load_fhcp_graph(_ID, root=root)
    assert graph.source["instance_id"] == _ID
    assert graph.source["name"] == "unrelated-header"
    assert graph.source["sha256"] == manifest["instances"][0]["sha256"]
    assert load_fhcp_certificate(graph, root=root) == (3, 1, 2)


def test_loading_graph_needs_no_certificate_file(selection):
    root, _ = selection
    (root / "data/raw/FHCPCS_sols/reference.hcp.tou").unlink()
    graph = load_fhcp_graph(_ID, root=root)
    assert graph.edge_count() == 3
    with pytest.raises(FileNotFoundError):
        load_fhcp_certificate(graph, root=root)


@pytest.mark.parametrize("certificate", [False, True])
def test_hash_mismatch_precedes_reader_errors(selection, certificate):
    root, _ = selection
    if certificate:
        graph = load_fhcp_graph(_ID, root=root)
        (root / "data/raw/FHCPCS_sols/reference.hcp.tou").write_bytes(b"\xff")
    else:
        (root / "data/raw/FHCPCS/fixture.hcp").write_bytes(b"\xff")
    with pytest.raises(GraphError) as error:
        if certificate:
            load_fhcp_certificate(graph, root=root)
        else:
            load_fhcp_graph(_ID, root=root)
    assert error.value.code == "source_hash_mismatch"


@pytest.mark.parametrize("field", ["dimension", "edge_count"])
def test_valid_hcp_bytes_with_wrong_manifest_counts_are_rejected(selection, field):
    root, manifest = selection
    manifest["instances"][0][field] = 4
    write_manifest(root, manifest)
    with pytest.raises(GraphError) as error:
        load_fhcp_graph(_ID, root=root)
    assert error.value.code == "manifest_mismatch"
    assert field in error.value.detail


def test_certificate_cannot_be_selected_for_an_unmatched_graph(selection):
    root, _ = selection
    graph = Graph(range(1, 4), [(1, 2), (2, 3), (3, 1)], source={
        "instance_id": _ID, "sha256": "0" * 64,
    })
    with pytest.raises(GraphError) as error:
        load_fhcp_certificate(graph, root=root)
    assert error.value.code == "manifest_mismatch"


@pytest.mark.parametrize("instance_id", ["unknown", "unrelated-header"])
def test_unknown_selection_ids_are_rejected(selection, instance_id):
    root, _ = selection
    with pytest.raises(GraphError) as error:
        load_fhcp_graph(instance_id, root=root)
    assert error.value.code == "manifest_mismatch"


def test_duplicate_id_is_rejected(selection):
    root, manifest = selection
    manifest["instances"] *= 2
    write_manifest(root, manifest)
    with pytest.raises(GraphError) as error:
        load_fhcp_graph(_ID, root=root)
    assert error.value.code == "manifest_mismatch"


@pytest.mark.parametrize("member", ["../fixture.hcp", r"..\fixture.hcp"])
def test_manifest_cannot_select_a_member_outside_the_graph_directory(selection, member):
    root, manifest = selection
    manifest["instances"][0]["archive_member"] = member
    write_manifest(root, manifest)
    with pytest.raises(GraphError) as error:
        load_fhcp_graph(_ID, root=root)
    assert error.value.code == "manifest_mismatch"
