"""Check CSR against explicit examples and an independent edge-set oracle."""

from dataclasses import FrozenInstanceError
from itertools import combinations
from random import Random

import numpy as np
import pytest

from src.graphs import Graph, GraphError


def test_contract_example(example_graph):
    graph = example_graph
    assert graph.vertex_count() == 5
    assert graph.edge_count() == 7
    # White-box assertions here verify the exact CSR agreed in #17.
    np.testing.assert_array_equal(graph._offsets, [0, 3, 6, 9, 12, 14])
    np.testing.assert_array_equal(
        graph._adjacency, [1, 2, 4, 0, 2, 3, 0, 1, 3, 1, 2, 4, 0, 3],
    )
    assert graph._offsets.dtype == graph._adjacency.dtype == np.dtype(np.int32)
    assert list(graph.edges()) == [(0, 1), (0, 2), (0, 4), (1, 2), (1, 3), (2, 3), (3, 4)]
    assert graph.neighbors(4).tolist() == [0, 3]
    assert graph.degree(4) == 2
    assert graph.has_edge(0, 4) is True
    assert graph.has_edge(4, 0) is True
    assert graph.has_edge(2, 4) is False
    assert graph.has_edge(2, 2) is False
    assert graph.index_of(30) == 2
    assert graph.external_label(2) == 30
    for i in range(graph.vertex_count()):
        assert graph.index_of(graph.external_label(i)) == i


def test_all_simple_graphs_up_to_four_vertices():
    # An edge-set oracle checks every possible query, including disconnected
    # graphs and empty rows, without relying on CSR construction logic.
    rng = Random(26)
    for n in range(1, 5):
        possible = list(combinations(range(n), 2))
        labels = [10 * (i + 1) for i in range(n)]
        for mask in range(1 << len(possible)):
            expected = {edge for i, edge in enumerate(possible) if mask & (1 << i)}
            external = [(labels[u], labels[v]) for u, v in sorted(expected)]
            rng.shuffle(external)
            external = [(v, u) if rng.randrange(2) else (u, v) for u, v in external]
            graph = Graph(labels, external)
            assert graph.vertex_count() == n
            assert graph.edge_count() == len(expected)
            assert list(graph.edges()) == sorted(expected)
            assert graph._offsets[0] == 0
            assert graph._offsets[-1] == 2 * len(expected)
            assert np.all(np.diff(graph._offsets) >= 0)
            for u in range(n):
                neighbors = [v for v in range(n) if (min(u, v), max(u, v)) in expected]
                assert graph.neighbors(u).tolist() == neighbors
                assert graph.degree(u) == len(neighbors)
                for v in range(n):
                    assert graph.has_edge(u, v) is ((min(u, v), max(u, v)) in expected)
                    assert graph.has_edge(u, v) == graph.has_edge(v, u)


def test_edge_order_and_orientation_preserve_exact_csr(example_graph):
    external = [(example_graph.external_label(u), example_graph.external_label(v))
                for u, v in example_graph.edges()]
    for edges in [external, list(reversed(external)), [(v, u) for u, v in external]]:
        graph = Graph([10, 20, 30, 40, 50], edges)
        np.testing.assert_array_equal(graph._offsets, example_graph._offsets)
        np.testing.assert_array_equal(graph._adjacency, example_graph._adjacency)


@pytest.mark.parametrize("labels, edges, degrees", [
    ([10], [], [0]),
    ([10, 20], [], [0, 0]),
    ([10, 20], [(10, 20)], [1, 1]),
    ([10, 20, 30, 40], [(10, 30)], [1, 0, 1, 0]),
])
def test_small_graphs_and_isolated_vertices(labels, edges, degrees):
    graph = Graph(labels, edges)
    assert graph.vertex_count() == len(labels)
    assert [graph.degree(i) for i in range(len(labels))] == degrees
    assert [graph.external_label(i) for i in range(len(labels))] == labels
    for i, degree in enumerate(degrees):
        if degree == 0:
            assert graph.neighbors(i).tolist() == []
            assert not graph.has_edge(i, i)


@pytest.mark.parametrize("labels", [
    [], [20, 10], [10, 10], [True], [np.bool_(True)],
    [10.0], ["10"], [None], [10, 20.0],
])
def test_invalid_label_universe(labels):
    with pytest.raises(GraphError) as error:
        Graph(labels, [])
    assert error.value.code == "invalid_labels"


def test_in_memory_labels_can_include_negative_and_zero():
    graph = Graph([-10, 0, 20], [(-10, 20)])
    assert tuple(graph.external_label(i) for i in range(3)) == (-10, 0, 20)
    assert graph.index_of(0) == 1
    assert list(graph.edges()) == [(0, 2)]
    assert graph.degree(1) == 0


@pytest.mark.parametrize("edges, code", [
    ([(10, 60)], "unknown_label"),
    ([(0, 20)], "unknown_label"),
    ([(60, 60)], "unknown_label"),
    ([(20, 20)], "self_loop"),
    ([(10, 20), (10, 20)], "duplicate_edge"),
    ([(10, 20), (20, 10)], "duplicate_edge"),
    ([(True, 20)], "invalid_label_type"),
    ([(10, np.bool_(True))], "invalid_label_type"),
    ([(10, 20.0)], "invalid_label_type"),
    ([("10", 20)], "invalid_label_type"),
    ([(np.timedelta64(10, "ns"), 20)], "invalid_label_type"),
])
def test_invalid_edges(edges, code):
    with pytest.raises(GraphError) as error:
        Graph([10, 20, 30], edges)
    assert error.value.code == code


@pytest.mark.parametrize("edges", [[(10,)], [(10, 20, 30)], [None]])
def test_malformed_python_edge_arguments(edges):
    with pytest.raises((TypeError, ValueError)):
        Graph([10, 20, 30], edges)


@pytest.mark.parametrize("index", [-1, 5, 2**80, True, np.bool_(True), 1.0, "1", None])
def test_all_index_operations_reject_invalid_indices(example_graph, index):
    operations = [
        lambda: example_graph.degree(index),
        lambda: example_graph.neighbors(index),
        lambda: example_graph.external_label(index),
        lambda: example_graph.has_edge(index, 0),
        lambda: example_graph.has_edge(0, index),
        lambda: example_graph.has_edge(index, index),
    ]
    for operation in operations:
        with pytest.raises(GraphError) as error:
            operation()
        assert error.value.code == "invalid_vertex_index"


@pytest.mark.parametrize("label, code", [
    (60, "unknown_label"), (0, "unknown_label"), (-10, "unknown_label"),
    (True, "invalid_label_type"), (10.0, "invalid_label_type"),
    ("10", "invalid_label_type"), (None, "invalid_label_type"),
])
def test_index_of_rejects_unknown_labels_and_bad_types(example_graph, label, code):
    with pytest.raises(GraphError) as error:
        example_graph.index_of(label)
    assert error.value.code == code


def test_integer_types_and_large_external_labels():
    huge = 2**80
    graph = Graph([np.int32(10), np.int64(30), huge], [(np.int64(30), huge)])
    assert graph.index_of(np.uint64(30)) == 1
    assert graph.external_label(np.int32(2)) == huge
    assert graph.has_edge(np.uint32(1), np.int64(2)) is True
    assert graph.degree(np.int64(2)) == 1


def test_constructor_detaches_mutable_inputs():
    labels = np.array([10, 20, 30], dtype=np.int32)
    edges = np.array([[10, 20], [20, 30]], dtype=np.int32)
    source = {"instance_id": "synthetic", "sha256": "example-only"}
    graph = Graph(labels, edges, source=source)
    labels[:] = 99
    edges[:] = 99
    source["instance_id"] = "changed"
    assert [graph.external_label(i) for i in range(3)] == [10, 20, 30]
    assert list(graph.edges()) == [(0, 1), (1, 2)]
    assert graph.source["instance_id"] == "synthetic"


def test_neighbors_cannot_expose_mutable_storage(example_graph):
    original = list(example_graph.edges())
    row = example_graph.neighbors(0)
    assert row.tolist() == [1, 2, 4]
    assert row.flags.writeable is False
    assert isinstance(row.base, bytes)
    assert np.shares_memory(row, example_graph.neighbors(0))
    for alias in [row, row.view(), row[:], np.asarray(row), np.frombuffer(row.base, dtype=np.int32)]:
        with pytest.raises(ValueError):
            alias[0] = 99
        with pytest.raises(ValueError):
            alias.setflags(write=True)
    # Mutating the returned array header must not alter internal array headers.
    # These legacy mutations still exist in the pinned NumPy 2.5.4.
    with pytest.warns(DeprecationWarning, match="Setting the shape"):
        row.shape = (1, 3)
    with pytest.warns(DeprecationWarning, match="Setting the dtype"):
        row.dtype = np.int8
    assert example_graph.neighbors(0).tolist() == [1, 2, 4]
    assert list(example_graph.edges()) == original
    detached = example_graph.neighbors(0).copy()
    detached[0] = 99
    assert example_graph.neighbors(0).tolist() == [1, 2, 4]


def test_graph_and_provenance_are_read_only(example_graph):
    assert dict(example_graph.source) == {}
    with pytest.raises(TypeError):
        example_graph.source["instance_id"] = "changed"
    with pytest.raises(FrozenInstanceError):
        example_graph._labels = (99,)
    with pytest.raises(AttributeError):
        example_graph.source = {}
    graph = Graph([10], [], source={"name": "description"})
    assert dict(graph.source) == {"name": "description"}
    assert graph.degree(0) == 0
    with pytest.raises(TypeError):
        Graph([10], [], source={"instance_id": ["mutable"]})


def test_has_edge_searches_the_shorter_row(monkeypatch):
    graph = Graph([10, 20, 30, 40, 50], [(10, 20), (10, 30), (10, 40)])
    from bisect import bisect_left

    lengths = []

    def record_search(values, target, start, stop):
        lengths.append(stop - start)
        return bisect_left(values, target, start, stop)

    monkeypatch.setattr("src.graphs.graph.bisect_left", record_search)
    assert graph.has_edge(0, 1)
    assert graph.has_edge(1, 0)
    assert not graph.has_edge(0, 4)
    assert not graph.has_edge(4, 0)
    assert lengths == [1, 1, 0, 0]
