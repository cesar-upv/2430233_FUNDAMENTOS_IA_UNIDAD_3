"""Search cost contract, including rejection before graph access."""

from itertools import combinations, permutations

import numpy as np
import pytest

from src import evaluation
from src.graphs import Graph


@pytest.mark.parametrize("route, expected", [
    ([0, 1, 2, 3, 4], 0),
    ([0, 1, 3, 2, 4], 1),
    ([1, 0, 2, 3, 4], 1),
    ([1, 3, 0, 4, 2], 2),
])
def test_contract_costs_preserve_inputs(example_graph, route, expected):
    before = route.copy()
    edges = tuple(example_graph.edges())
    cost = evaluation.evaluate_cost(example_graph, route)
    assert type(cost) is int and cost == expected
    assert route == before and tuple(example_graph.edges()) == edges


@pytest.mark.parametrize("route, code, position, vertices", [
    ([0, 1, 3, 1, 2], "repeated_vertex", 3, (1,)),
    ([0, 1, 3, 4], "invalid_length", None, ()),
    ([0, 1, 2, 3, 4, 0], "invalid_length", None, ()),
    ([0, 1, 2, 3, 5], "unknown_vertex", 4, (5,)),
    ([0, 1, 2, 3, -1], "unknown_vertex", 4, (-1,)),
    ([0, 1, 2, 3, 1.0], "invalid_vertex_type", 4, ()),
    ([0, 1, 2, 3, True], "invalid_vertex_type", 4, ()),
    ([0, 1, 2, 3, "4"], "invalid_vertex_type", 4, ()),
    ([0, 1, 2, 3, np.bool_(True)], "invalid_vertex_type", 4, ()),
    ([0, 1, 2, 3, np.timedelta64(1, "D")], "invalid_vertex_type", 4, ()),
    ([0, 0, "2", 3, 4], "repeated_vertex", 1, (0,)),
    ([True], "invalid_length", None, ()),
])
def test_rejections_preserve_context_before_edge_access(example_graph, monkeypatch, route, code, position, vertices):
    def forbidden(*args):
        pytest.fail("Illegal routes must not query edges")
    monkeypatch.setattr(Graph, "has_edge", forbidden)
    before = route.copy()
    with pytest.raises(evaluation.CostEvaluationError) as error:
        evaluation.evaluate_cost(example_graph, route)
    assert (error.value.code, error.value.position, error.value.vertices) == (code, position, vertices)
    assert route == before


@pytest.mark.parametrize("n", [1, 2])
@pytest.mark.parametrize("route", [None, [], [0], [0, 1]])
def test_small_graph_rejected_first(n, route, monkeypatch):
    graph = Graph(range(n), list(combinations(range(n), 2)))
    def forbidden(*args):
        pytest.fail("Small graphs must not query edges")
    monkeypatch.setattr(Graph, "has_edge", forbidden)
    with pytest.raises(evaluation.CostEvaluationError) as error:
        evaluation.evaluate_cost(graph, route)
    assert (error.value.code, error.value.position, error.value.vertices) == ("graph_too_small", None, ())


@pytest.mark.parametrize("route", [None, {0, 1, 2}, {0: 0, 1: 1, 2: 2}])
def test_non_positional_containers_are_programming_errors(route):
    with pytest.raises(TypeError):
        evaluation.evaluate_cost(Graph(range(3), []), route)


@pytest.mark.parametrize("dtype", [np.int32, np.int64, np.uint64])
def test_read_only_numpy_routes(example_graph, dtype):
    route = np.array([1, 3, 0, 4, 2], dtype=dtype)
    before = route.copy()
    route.setflags(write=False)
    assert evaluation.evaluate_cost(example_graph, route) == 2
    np.testing.assert_array_equal(route, before)


def test_cost_never_calls_certificate_or_stops_at_first_gap(monkeypatch):
    from src.evaluation import cycle
    def forbidden(*args):
        pytest.fail("Cost must not call cycle certification")
    monkeypatch.setattr(evaluation, "validate_cycle", forbidden)
    monkeypatch.setattr(cycle, "validate_cycle", forbidden)
    assert evaluation.evaluate_cost(Graph(range(5), []), [0, 1, 2, 3, 4]) == 5


def test_exhaustive_cost_range_symmetries_and_certification():
    for n in (3, 4):
        possible = list(combinations(range(n), 2))
        for mask in range(1 << len(possible)):
            edges = {edge for bit, edge in enumerate(possible) if mask & (1 << bit)}
            graph = Graph(range(n), edges)
            for route in permutations(range(n)):
                expected = sum(tuple(sorted(pair)) not in edges
                               for pair in zip(route, route[1:] + route[:1]))
                cost = evaluation.evaluate_cost(graph, route)
                assert type(cost) is int and 0 <= cost <= n and cost == expected
                assert (cost == 0) == evaluation.validate_cycle(graph, route).valid
                assert evaluation.evaluate_cost(graph, route[::-1]) == cost
                for offset in range(n):
                    assert evaluation.evaluate_cost(graph, route[offset:] + route[:offset]) == cost


def test_consistent_vertex_renaming(example_graph):
    for mapping in permutations(range(5)):
        renamed = Graph(range(5), [(mapping[u], mapping[v]) for u, v in example_graph.edges()])
        route = [mapping[v] for v in (1, 3, 0, 4, 2)]
        assert evaluation.evaluate_cost(renamed, route) == 2
