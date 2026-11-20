"""Route legality is distinct from edge feasibility and cycle certification."""

from dataclasses import FrozenInstanceError
from itertools import permutations
from math import factorial

import numpy as np
import pytest

from src.graphs import (
    Graph,
    GraphError,
    canonical_route,
    check_route_legality,
    route_to_external,
    route_to_internal,
)


def test_contract_conversion_example(example_graph):
    labels = [30, 40, 50, 10, 20]
    snapshot = labels.copy()
    route = route_to_internal(example_graph, labels)
    assert route == (2, 3, 4, 0, 1)
    assert route_to_external(example_graph, route) == tuple(labels)
    assert canonical_route(route) == (0, 1, 2, 3, 4)
    assert labels == snapshot


@pytest.mark.parametrize("indices", [(), (0, 2), (0, 0, 1), (0, 1, 2, 3, 4, 0)])
def test_conversions_preserve_length_order_and_repetitions(example_graph, indices):
    labels = route_to_external(example_graph, indices)
    assert labels == tuple([10, 20, 30, 40, 50][i] for i in indices)
    assert route_to_internal(example_graph, iter(labels)) == indices
    assert route_to_external(example_graph, iter(indices)) == labels


@pytest.mark.parametrize("labels, code", [
    ([10, 20, 30, 40, 60], "unknown_label"),
    ([10, True], "invalid_label_type"),
    ([10, np.bool_(True)], "invalid_label_type"),
    ([10, 20.0], "invalid_label_type"),
    ([10, "20"], "invalid_label_type"),
])
def test_external_conversion_errors(example_graph, labels, code):
    with pytest.raises(GraphError) as error:
        route_to_internal(example_graph, labels)
    assert error.value.code == code


@pytest.mark.parametrize("indices", [[-1], [5], [True], [1.0], ["1"]])
def test_internal_conversion_errors(example_graph, indices):
    with pytest.raises(GraphError) as error:
        route_to_external(example_graph, indices)
    assert error.value.code == "invalid_vertex_index"


@pytest.mark.parametrize("route, reason, position, vertices", [
    ([0, 1, 2, 3, 4], None, None, ()),
    ([0, 4, 3, 2, 1], None, None, ()),
    ([2, 3, 4, 0, 1], None, None, ()),
    ([0, 1, 3, 1, 2], "repeated_vertex", 3, (1,)),
    ([0, 1, 3, 4], "invalid_length", None, ()),
    ([0, 1, 2, 3, 4, 0], "invalid_length", None, ()),
    ([0, 1, 2, 3, 5], "unknown_vertex", 4, (5,)),
    ([0, 1, 2, 3, -1], "unknown_vertex", 4, (-1,)),
    ([0, 1, 2, 3, 1.0], "invalid_vertex_type", 4, ()),
    ([0, 1, 3, 2, 4], None, None, ()),  # Internal edge absent, still legal.
    ([1, 0, 2, 3, 4], None, None, ()),  # Closing edge absent, still legal.
    ([True], "invalid_length", None, ()),  # Length precedes element type.
    ([0, 0, "2", 3, 4], "repeated_vertex", 1, (0,)),
    ([0, 7, 0, 3, 4], "unknown_vertex", 1, (7,)),
    ([0, 1.0, 0, 3, 4], "invalid_vertex_type", 1, ()),
])
def test_legality_matches_contract_and_first_failure(route, reason, position, vertices):
    snapshot = route.copy()
    result = check_route_legality(5, route)
    assert result.valid is (reason is None)
    assert result.reason == reason
    assert result.position == position
    assert result.vertices == vertices
    assert route == snapshot


@pytest.mark.parametrize("bad", [
    True, False, np.bool_(True), 1.0, np.float64(1), "1", None,
    float("nan"), np.array(1),
])
def test_legality_does_not_coerce_non_integer_types(bad):
    result = check_route_legality(3, [0, bad, 2])
    assert (result.valid, result.reason, result.position) == (False, "invalid_vertex_type", 1)


@pytest.mark.parametrize("unit", ["ns", "D"])
def test_route_rejects_numpy_durations_as_indices(unit):
    result = check_route_legality(3, [0, np.timedelta64(1, unit), 2])
    assert (result.valid, result.reason, result.position) == (False, "invalid_vertex_type", 1)


@pytest.mark.parametrize("route", [{0: 2, 1: 0, 2: 1}, {0, 1, 2}])
def test_route_operations_require_a_positional_sequence(route):
    with pytest.raises(TypeError, match="sequence"):
        check_route_legality(3, route)
    with pytest.raises(TypeError, match="sequence"):
        canonical_route(route)


def test_numpy_integer_routes_and_conversion(example_graph):
    route = np.array([2, 3, 4, 0, 1], dtype=np.int32)
    labels = np.array([30, 40, 50, 10, 20], dtype=np.int64)
    assert check_route_legality(np.int64(5), route).valid
    assert canonical_route(route) == (0, 1, 2, 3, 4)
    assert route_to_internal(example_graph, labels) == tuple(route)
    assert route_to_external(example_graph, route) == tuple(labels)
    assert not check_route_legality(3, [0, np.uint64(2**64 - 1), 2]).valid


@pytest.mark.parametrize("n, route", [(1, [0]), (2, [1, 0]), (3, [2, 0, 1])])
def test_legality_does_not_certify_cycles(n, route):
    graph = Graph(range(1, n + 1), [])
    assert graph.edge_count() == 0
    assert check_route_legality(graph.vertex_count(), route).valid
    assert len(canonical_route(route)) == n


@pytest.mark.parametrize("n", [0, -1, True, np.bool_(True), 3.0, "3"])
def test_invalid_programming_argument_n(n):
    with pytest.raises(ValueError):
        check_route_legality(n, [])


def test_legality_result_is_immutable():
    result = check_route_legality(3, [0, 1, 2])
    with pytest.raises(FrozenInstanceError):
        result.valid = False


@pytest.mark.parametrize("route, expected", [
    ([0], (0,)), ([0, 1], (0, 1)), ([1, 0], (0, 1)),
    ([3, 4, 0, 1, 2], (0, 1, 2, 3, 4)),
    ([0, 4, 3, 2, 1], (0, 1, 2, 3, 4)),
    ([3, 1, 4, 0, 2], (0, 2, 3, 1, 4)),
])
def test_canonical_examples_preserve_input(route, expected):
    snapshot = route.copy()
    assert canonical_route(route) == expected
    assert route == snapshot


@pytest.mark.parametrize("route, code", [
    ([], "invalid_length"),
    ([0, 1, 2, 0], "repeated_vertex"),
    ([0, 2], "unknown_vertex"),
    ([1, 2, 3], "unknown_vertex"),
    ([0, True], "invalid_vertex_type"),
    ([0, 1.0], "invalid_vertex_type"),
    ([0, "1"], "invalid_vertex_type"),
])
def test_canonicalization_requires_legal_input(route, code):
    with pytest.raises(GraphError) as error:
        canonical_route(route)
    assert error.value.code == code


def test_canonicalization_symmetries_exhaustively_up_to_six_vertices():
    for n in range(1, 7):
        representatives = set()
        for route in permutations(range(n)):
            canonical = canonical_route(route)
            representatives.add(canonical)
            assert canonical[0] == 0
            assert sorted(canonical) == list(range(n))
            assert canonical_route(canonical) == canonical
            for offset in range(n):
                rotated = route[offset:] + route[:offset]
                assert canonical_route(rotated) == canonical
                assert canonical_route(rotated[::-1]) == canonical
            # Canonicalization must preserve all undirected pairs, including closure.
            pairs = lambda values: {frozenset((values[i], values[(i + 1) % n]))
                                    for i in range(n)}
            assert pairs(route) == pairs(canonical)
        assert len(representatives) == (1 if n < 3 else factorial(n - 1) // 2)
