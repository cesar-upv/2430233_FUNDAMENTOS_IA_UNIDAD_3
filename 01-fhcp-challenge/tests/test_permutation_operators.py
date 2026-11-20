"""Deterministic GA primitives: permutation invariants do not certify cycles."""

from itertools import combinations, permutations
import random

import numpy as np
import pytest

from src.algorithms import initialize_route, order_crossover, swap_mutation
from src.evaluation import validate_cycle
from src.graphs import GraphError, check_route_legality


def make_rng(seed=38):
    return np.random.Generator(np.random.PCG64(seed))


@pytest.mark.parametrize("n", [3, 5, np.int32(8), np.int64(20)])
def test_initialization_matches_injected_generator(n):
    expected_rng = make_rng()
    expected = tuple(int(v) for v in expected_rng.permutation(int(n)))
    rng = make_rng()
    route = initialize_route(n, rng)
    assert isinstance(route, tuple)
    assert all(type(v) is int for v in route)
    assert route == expected
    assert check_route_legality(n, route).valid
    assert rng.bit_generator.state == expected_rng.bit_generator.state


@pytest.mark.parametrize("n", [
    -1, 0, 1, 2, True, np.bool_(True), 3.0, "3", None,
    np.timedelta64(3, "D"), np.array(3),
])
def test_initialization_rejects_invalid_sizes_without_drawing(n):
    rng = make_rng()
    before = rng.bit_generator.state
    with pytest.raises(ValueError):
        initialize_route(n, rng)
    assert rng.bit_generator.state == before


@pytest.mark.parametrize("cuts, expected", [
    ((0, 1), (0, 2, 3, 1, 4)),
    ((4, 5), (2, 0, 3, 1, 4)),
    ((0, 5), (0, 1, 2, 3, 4)),
    ((0, 2), (0, 1, 3, 4, 2)),
    ((2, 5), (0, 1, 2, 3, 4)),
    ((1, 4), (0, 1, 2, 3, 4)),
    ((2, 3), (4, 0, 2, 3, 1)),
])
def test_ox_exact_cuts_and_circular_donor_order(cuts, expected):
    parent_a = [0, 1, 2, 3, 4]
    parent_b = [4, 2, 0, 3, 1]
    child = order_crossover(parent_a, parent_b, cuts=cuts)
    assert child == expected
    assert parent_a == [0, 1, 2, 3, 4]
    assert parent_b == [4, 2, 0, 3, 1]


def test_ox_wraps_both_read_and_write_positions():
    # Starting the donor at zero would give a different child.
    parent_a = [0, 1, 2, 3, 4, 5, 6, 7]
    parent_b = [1, 2, 0, 5, 6, 7, 4, 3]
    assert order_crossover(parent_a, parent_b, cuts=(2, 5)) == (5, 6, 2, 3, 4, 7, 1, 0)
    assert order_crossover(parent_b, parent_a, cuts=(2, 5)) == (3, 4, 0, 5, 6, 7, 1, 2)


@pytest.mark.parametrize("positions, expected", [
    ((0, 4), (4, 1, 2, 3, 0)),
    ((4, 0), (4, 1, 2, 3, 0)),
    ((1, 2), (0, 2, 1, 3, 4)),
    ((2, 3), (0, 1, 3, 2, 4)),
])
def test_swap_changes_exactly_the_two_selected_positions(positions, expected):
    parent = [0, 1, 2, 3, 4]
    child = swap_mutation(parent, positions=positions)
    assert child == expected
    assert {i for i in range(5) if child[i] != parent[i]} == set(positions)
    assert parent == [0, 1, 2, 3, 4]
    assert swap_mutation(child, positions=positions) == tuple(parent)


def test_exhaustive_minimum_solver_routes_preserve_segment_order_and_domain():
    # All parents, all nonempty boundary intervals and all swaps at n=3.
    routes = list(permutations(range(3)))
    for first in routes:
        for i, j in combinations(range(3), 2):
            mutated = swap_mutation(first, positions=(i, j))
            assert check_route_legality(3, mutated).valid
            assert mutated != first
        for second in routes:
            for start, stop in combinations(range(4), 2):
                child = order_crossover(first, second, cuts=(start, stop))
                assert len(child) == 3
                assert sorted(child) == [0, 1, 2]
                assert child[start:stop] == first[start:stop]
                copied = set(first[start:stop])
                expected_order = [v for v in second[stop:] + second[:stop] if v not in copied]
                assert list(child[stop:] + child[:start]) == expected_order


@pytest.mark.parametrize("dtype", [np.int32, np.int64, np.uint64])
@pytest.mark.parametrize("read_only", [False, True])
def test_numpy_parents_are_detached_and_normalized_to_python_integers(dtype, read_only):
    owner = np.array([4, 0, 3, 1, 2, 99], dtype=dtype)
    parent_a = owner[:5]
    parent_b = np.array([1, 2, 0, 4, 3], dtype=dtype)
    parent_a.setflags(write=not read_only)
    parent_b.setflags(write=not read_only)
    before_a, before_b = parent_a.copy(), parent_b.copy()
    child = order_crossover(parent_a, parent_b, cuts=(1, 3))
    mutated = swap_mutation(parent_a, positions=(0, 4))
    for result in (child, mutated):
        assert isinstance(result, tuple)
        assert all(type(v) is int for v in result)
        assert check_route_legality(5, result).valid
    np.testing.assert_array_equal(parent_a, before_a)
    np.testing.assert_array_equal(parent_b, before_b)
    owner[0] = 99
    assert 99 not in child and 99 not in mutated


@pytest.mark.parametrize("parent, code", [
    ([0, 0, 2], "repeated_vertex"),
    ([0, 1, 3], "unknown_vertex"),
    ([0, 1, -1], "unknown_vertex"),
    ([0, True, 2], "invalid_vertex_type"),
    ([0, np.bool_(True), 2], "invalid_vertex_type"),
    ([0, 1.0, 2], "invalid_vertex_type"),
    ([0, "1", 2], "invalid_vertex_type"),
    ([0, np.timedelta64(1, "D"), 2], "invalid_vertex_type"),
    (np.array([[0], [1], [2]]), "invalid_vertex_type"),
])
def test_illegal_parents_are_rejected_before_rng_draws(parent, code):
    for operation in (
        lambda rng: order_crossover(parent, [0, 1, 2], rng=rng),
        lambda rng: order_crossover([0, 1, 2], parent, rng=rng),
        lambda rng: swap_mutation(parent, rng=rng),
    ):
        rng = make_rng()
        before = rng.bit_generator.state
        with pytest.raises(GraphError) as error:
            operation(rng)
        assert error.value.code == code
        assert rng.bit_generator.state == before


@pytest.mark.parametrize("parent", [[], [0], [0, 1]])
def test_operators_reject_routes_below_solver_minimum(parent):
    with pytest.raises(ValueError):
        order_crossover(parent, parent, cuts=(0, 1))
    with pytest.raises(ValueError):
        swap_mutation(parent, positions=(0, 1))


@pytest.mark.parametrize("parent_b", [[0], [0, 1, 2, 3], [0, 1, 2, 0]])
def test_ox_requires_same_length_and_rejects_explicit_closure(parent_b):
    rng = make_rng()
    before = rng.bit_generator.state
    with pytest.raises(GraphError) as error:
        order_crossover([0, 1, 2], parent_b, rng=rng)
    assert error.value.code == "invalid_length"
    assert rng.bit_generator.state == before


@pytest.mark.parametrize("parent", [None, {0, 1, 2}, {0: 0, 1: 1, 2: 2}, np.array(3)])
def test_non_positional_parents_are_programming_errors(parent):
    with pytest.raises(TypeError):
        order_crossover(parent, [0, 1, 2], cuts=(0, 1))
    with pytest.raises(TypeError):
        swap_mutation(parent, positions=(0, 1))


@pytest.mark.parametrize("pair", [
    (), (0,), (0, 1, 2), (1, 1), (-1, 2), (0, 6),
    (True, 2), (np.bool_(False), 2), (1.0, 2), ("1", 2),
    (np.timedelta64(1, "D"), 2), {0, 1}, {0: 0, 1: 1}, 1,
])
def test_invalid_explicit_decisions(pair):
    with pytest.raises(ValueError):
        order_crossover(range(5), range(5), cuts=pair)
    with pytest.raises(ValueError):
        swap_mutation(range(5), positions=pair)


def test_ox_rejects_reversed_cuts_and_swap_rejects_boundary_n():
    with pytest.raises(ValueError):
        order_crossover(range(5), range(5), cuts=(4, 1))
    with pytest.raises(ValueError):
        swap_mutation(range(5), positions=(0, 5))


def test_numpy_integer_decisions():
    pair = (np.int32(0), np.int64(2))
    assert order_crossover([0, 1, 2], [2, 1, 0], cuts=pair) == (0, 1, 2)
    assert swap_mutation([0, 1, 2], positions=pair) == (2, 1, 0)


def test_same_mutable_parent_can_supply_both_roles():
    parent = [3, 1, 4, 0, 2]
    for cuts in combinations(range(6), 2):
        assert order_crossover(parent, parent, cuts=cuts) == (3, 1, 4, 0, 2)
        assert parent == [3, 1, 4, 0, 2]


def test_exactly_one_decision_source_is_required():
    rng = make_rng()
    before = rng.bit_generator.state
    for operation in (
        lambda: order_crossover(range(3), range(3)),
        lambda: swap_mutation(range(3)),
        lambda: order_crossover(range(3), range(3), rng=rng, cuts=(0, 2)),
        lambda: swap_mutation(range(3), rng=rng, positions=(0, 2)),
    ):
        with pytest.raises(ValueError):
            operation()
    assert rng.bit_generator.state == before


@pytest.mark.parametrize("rng", [None, 38, random.Random(38), np.random.RandomState(38)])
def test_invalid_rng(rng):
    with pytest.raises(TypeError):
        initialize_route(3, rng)
    # None denotes a missing decision source for crossover and mutation.
    error_type = ValueError if rng is None else TypeError
    with pytest.raises(error_type):
        order_crossover(range(3), range(3), rng=rng)
    with pytest.raises(error_type):
        swap_mutation(range(3), rng=rng)


@pytest.mark.parametrize("n", [3, 5, 32])
@pytest.mark.parametrize("seed", [0, 38, 2**64 - 1])
def test_equal_seeds_reproduce_repeated_operations_and_preserve_inputs(n, seed):
    left, right = make_rng(seed), make_rng(seed)
    for _ in range(12):
        a, b = initialize_route(n, left), initialize_route(n, left)
        assert (a, b) == (initialize_route(n, right), initialize_route(n, right))
        snapshot_a, snapshot_b = list(a), list(b)
        child = order_crossover(snapshot_a, snapshot_b, rng=left)
        assert child == order_crossover(a, b, rng=right)
        mutated = swap_mutation(snapshot_a, rng=left)
        assert mutated == swap_mutation(a, rng=right)
        assert snapshot_a == list(a) and snapshot_b == list(b)
        assert check_route_legality(n, child).valid
        assert check_route_legality(n, mutated).valid
        assert sum(x != y for x, y in zip(a, mutated)) == 2
    assert left.bit_generator.state == right.bit_generator.state


def test_random_decisions_match_explicit_sampling_contract():
    expected_rng = make_rng()
    cuts = tuple(sorted(int(v) for v in expected_rng.choice(6, size=2, replace=False)))
    rng = make_rng()
    first, second = [0, 1, 2, 3, 4], [4, 2, 0, 3, 1]
    assert order_crossover(first, second, rng=rng) == order_crossover(first, second, cuts=cuts)
    assert rng.bit_generator.state == expected_rng.bit_generator.state
    positions = tuple(int(v) for v in expected_rng.choice(5, size=2, replace=False))
    assert swap_mutation(first, rng=rng) == swap_mutation(first, positions=positions)
    assert rng.bit_generator.state == expected_rng.bit_generator.state


def test_no_operator_uses_global_randomness(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Global randomness must not be used.")

    rng = make_rng()
    for name in ("permutation", "choice", "shuffle", "randint", "random", "default_rng", "seed"):
        monkeypatch.setattr(np.random, name, forbidden)
    for name in ("random", "choice", "sample", "shuffle", "seed"):
        monkeypatch.setattr(random, name, forbidden)
    first, second = initialize_route(5, rng), initialize_route(5, rng)
    assert check_route_legality(5, order_crossover(first, second, rng=rng)).valid
    assert check_route_legality(5, swap_mutation(first, rng=rng)).valid


def test_project_counterexamples_require_independent_edge_validation(example_graph):
    # Examples from search-space.md §5.1; neither operator consults the graph.
    first, second = [0, 1, 2, 3, 4], [0, 2, 1, 3, 4]
    child = order_crossover(first, second, cuts=(0, 2))
    mutated = swap_mutation(first, positions=(2, 3))
    assert child == (0, 1, 3, 4, 2)
    assert mutated == (0, 1, 3, 2, 4)
    for candidate in (child, mutated):
        assert check_route_legality(5, candidate).valid
        result = validate_cycle(example_graph, candidate)
        assert (result.valid, result.reason) == (False, "missing_edge")
