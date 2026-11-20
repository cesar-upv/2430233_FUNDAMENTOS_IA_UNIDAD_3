"""Cycle certification against contract #17, independent of search and files."""

from itertools import combinations, permutations

import numpy as np
import pytest

from src import evaluation
from src.graphs import Graph


def test_minimum_triangle_is_certified():
    graph = Graph([10, 20, 30], [(10, 20), (20, 30), (10, 30)])
    result = evaluation.validate_cycle(graph, (0, 2, 1))
    assert (result.valid, result.reason, result.position, result.vertices) == (
        True, None, None, (),
    )


@pytest.mark.parametrize("route, reason, position, vertices", [
    ([0, 1, 2, 3, 4], None, None, ()),
    ([0, 4, 3, 2, 1], None, None, ()),
    ([2, 3, 4, 0, 1], None, None, ()),
    ([0, 1, 3, 4], "invalid_length", None, ()),
    ([0, 1, 2, 3, 4, 0], "invalid_length", None, ()),
    ([0, 1, 3, 1, 2], "repeated_vertex", 3, (1,)),
    ([0, 1, 2, 3, 5], "unknown_vertex", 4, (5,)),
    ([0, 1, 2, 3, -1], "unknown_vertex", 4, (-1,)),
    ([0, 1, 2, 3, 1.0], "invalid_vertex_type", 4, ()),
    ([0, 1, 3, 2, 4], "missing_edge", 3, (2, 4)),
    ([1, 0, 2, 3, 4], "missing_closing_edge", 4, (4, 1)),
    ([1, 3, 0, 4, 2], "missing_edge", 1, (3, 0)),
    ([0, 3, 1, 2, 4], "missing_edge", 0, (0, 3)),
    ([0, 3, 1, 1, 4], "repeated_vertex", 3, (1,)),
    ([True], "invalid_length", None, ()),
    ([0, 0, "2", 3, 4], "repeated_vertex", 1, (0,)),
])
def test_first_failure_and_input_preservation(example_graph, route, reason, position, vertices):
    before = route.copy()
    edges = tuple(example_graph.edges())
    result = evaluation.validate_cycle(example_graph, route)
    assert (result.valid, result.reason, result.position, result.vertices) == (
        reason is None, reason, position, vertices,
    )
    assert route == before
    assert tuple(example_graph.edges()) == edges


@pytest.mark.parametrize("bad", [True, np.bool_(True), "1", None, np.float64(1),
                                  np.timedelta64(1, "D")])
def test_invalid_scalars_are_not_coerced(example_graph, bad):
    result = evaluation.validate_cycle(example_graph, [0, bad, 2, 3, 4])
    assert (result.valid, result.reason, result.position, result.vertices) == (
        False, "invalid_vertex_type", 1, (),
    )


@pytest.mark.parametrize("n", [1, 2])
@pytest.mark.parametrize("route", [[], [True], [0], [0, 1], None])
def test_small_graph_precedes_route_checks(n, route):
    graph = Graph(range(n), list(combinations(range(n), 2)))
    result = evaluation.validate_cycle(graph, route)
    assert (result.valid, result.reason, result.position, result.vertices) == (
        False, "graph_too_small", None, (),
    )


@pytest.mark.parametrize("route", [{0, 1, 2}, {0: 0, 1: 1, 2: 2}, None])
def test_non_sequence_is_a_programming_error(route):
    graph = Graph(range(3), [(0, 1), (1, 2), (0, 2)])
    with pytest.raises(TypeError):
        evaluation.validate_cycle(graph, route)


@pytest.mark.parametrize("dtype", [np.int32, np.int64, np.uint64])
def test_numpy_routes_preserve_order_and_support_read_only_arrays(example_graph, dtype):
    route = np.array([2, 3, 4, 0, 1], dtype=dtype)
    route.setflags(write=False)
    before = route.copy()
    assert evaluation.validate_cycle(example_graph, route).valid
    np.testing.assert_array_equal(route, before)


def test_known_non_hamiltonian_path_rejects_candidate():
    # Endpoints have degree one: this path cannot have a Hamiltonian cycle.
    # The validator only rejects this candidate; it does not prove that fact.
    graph = Graph(range(5), [(0, 1), (1, 2), (2, 3), (3, 4)])
    result = evaluation.validate_cycle(graph, [0, 1, 2, 3, 4])
    assert (result.valid, result.reason, result.position, result.vertices) == (
        False, "missing_closing_edge", 4, (4, 0),
    )


def test_all_simple_graphs_through_four_vertices_against_edge_set_oracle():
    # Independent expected result uses the supplied edge set, not graph.has_edge
    # or the legality helper. Includes empty, disconnected and complete graphs.
    for n in (3, 4):
        possible = list(combinations(range(n), 2))
        for mask in range(1 << len(possible)):
            edges = {edge for bit, edge in enumerate(possible) if mask & (1 << bit)}
            graph = Graph(range(n), edges)
            for route in permutations(range(n)):
                pairs = list(zip(route, route[1:] + route[:1]))
                failures = [i for i, pair in enumerate(pairs) if tuple(sorted(pair)) not in edges]
                result = evaluation.validate_cycle(graph, route)
                if failures:
                    first = failures[0]
                    expected_reason = "missing_closing_edge" if first == n - 1 else "missing_edge"
                    assert (result.valid, result.reason, result.position, result.vertices) == (
                        False, expected_reason, first, pairs[first],
                    )
                else:
                    assert (result.valid, result.reason, result.position, result.vertices) == (
                        True, None, None, (),
                    )
