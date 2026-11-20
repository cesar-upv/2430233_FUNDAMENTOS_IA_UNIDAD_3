"""GA operators on legal routes; no fitness, graph edges or cycle certification."""

from collections.abc import Sequence

import numpy as np

from src.graphs import GraphError, check_route_legality
from src.graphs.graph import _is_integer


def _legal_route(route: Sequence[int] | np.ndarray, n: int | None = None) -> tuple[int, ...]:
    if n is None:
        n = len(route)
    if n < 3:
        raise ValueError("GA operators require at least three vertices, as does the solver.")
    result = check_route_legality(n, route)
    if not result.valid:
        raise GraphError(result.reason, f"Illegal route at position {result.position}.")
    return tuple(int(route[i]) for i in range(n))


def _choose_pair(
    size: int,
    rng: np.random.Generator | None,
    pair: tuple[int, int] | None,
) -> tuple[int, int]:
    if (rng is None) == (pair is None):
        raise ValueError("Supply exactly one of rng or an explicit pair of decisions.")
    if rng is not None:
        if not isinstance(rng, np.random.Generator):
            raise TypeError("rng must be a NumPy Generator.")
        first, second = rng.choice(size, size=2, replace=False)
        return int(first), int(second)
    if (
        not isinstance(pair, Sequence) or len(pair) != 2
        or any(not _is_integer(value) for value in pair)
    ):
        raise ValueError("Decisions must be two distinct integer positions.")
    first, second = (int(value) for value in pair)
    if not (0 <= first < size and 0 <= second < size) or first == second:
        raise ValueError("Decisions must be distinct positions within range.")
    return first, second


def initialize_route(n: int, rng: np.random.Generator) -> tuple[int, ...]:
    """Return a random permutation of 0..n-1 using the attempt's injected RNG.

    n must be an integer >= 3 (the solver minimum). No start vertex or
    orientation is fixed. Each call constructs one candidate, not a population.
    Invalid n raises ValueError; an invalid RNG raises TypeError.
    """
    if not _is_integer(n) or n < 3:
        raise ValueError("The route size must be an integer of at least three.")
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a NumPy Generator.")
    return tuple(int(vertex) for vertex in rng.permutation(int(n)))


def order_crossover(
    parent_a: Sequence[int] | np.ndarray,
    parent_b: Sequence[int] | np.ndarray,
    *,
    rng: np.random.Generator | None = None,
    cuts: tuple[int, int] | None = None,
) -> tuple[int, ...]:
    """Return one OX child without modifying either legal parent (n >= 3).

    Supply exactly one of rng or cuts. Cuts are boundaries [start, stop),
    with 0 <= start < stop <= n. With rng, choose two distinct boundaries
    uniformly from 0..n and sort them; a one-element or full segment is allowed.
    Copy parent_a[start:stop] at the same positions. Scan parent_b circularly
    from stop % n, skip copied vertices and fill circularly from stop % n.
    Reverse the parents in a separate call for the complementary child.

    Illegal parents raise GraphError with a #17 legality code. Sizes below three
    and invalid decisions raise ValueError; an invalid RNG raises TypeError.
    Validation precedes RNG draws. The result is not canonicalized and need not
    be a Hamiltonian cycle.
    """
    first = _legal_route(parent_a)
    n = len(first)
    second = _legal_route(parent_b, n)
    start, stop = _choose_pair(n + 1, rng, cuts)
    if rng is not None:
        start, stop = min(start, stop), max(start, stop)
    elif start > stop:
        raise ValueError("OX cuts must satisfy start < stop.")

    child = list(first)
    copied = bytearray(n)
    for vertex in first[start:stop]:
        copied[vertex] = 1
    position = stop % n
    for offset in range(n):
        vertex = second[(stop + offset) % n]
        if not copied[vertex]:
            child[position] = vertex
            position = (position + 1) % n
    return tuple(child)


def swap_mutation(
    route: Sequence[int] | np.ndarray,
    *,
    rng: np.random.Generator | None = None,
    positions: tuple[int, int] | None = None,
) -> tuple[int, ...]:
    """Swap two distinct positions in a new legal route, without canonicalizing.

    Supply exactly one of rng or positions. With rng, sample two distinct
    positions uniformly without replacement from 0..n-1; with positions, accept
    either order. The route must be legal with n >= 3. Errors and validation
    order follow order_crossover. No mutation probability or edge test is applied.
    """
    child = list(_legal_route(route))
    first, second = _choose_pair(len(child), rng, positions)
    child[first], child[second] = child[second], child[first]
    return tuple(child)
