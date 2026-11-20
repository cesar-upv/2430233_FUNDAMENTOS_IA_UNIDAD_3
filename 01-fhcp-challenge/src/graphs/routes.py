"""Conversions, permutation legality and canonical forms; no cycle certification."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np

from .graph import Graph, GraphError, _is_integer


@dataclass(frozen=True, slots=True)
class RouteLegalityResult:
    """First legality failure; ``valid`` says nothing about edges or closure."""

    valid: bool
    reason: str | None = None
    position: int | None = None
    vertices: tuple[int, ...] = ()


def route_to_external(graph: Graph, route: Iterable[int]) -> tuple[int, ...]:
    """Map each index independently, preserving length, order and repetitions."""
    return tuple(graph.external_label(vertex) for vertex in route)


def route_to_internal(graph: Graph, labels: Iterable[int]) -> tuple[int, ...]:
    """Map each external label independently; never certify or normalize it."""
    return tuple(graph.index_of(label) for label in labels)


def _require_route_sequence(route: object) -> None:
    if isinstance(route, Sequence) or (isinstance(route, np.ndarray) and route.ndim > 0):
        return
    raise TypeError("A route must be a positional sequence.")


def check_route_legality(n: int, route: Sequence[object] | np.ndarray) -> RouteLegalityResult:
    """Check length, then type/domain/uniqueness at each position, as in #17.

    ``n`` is a positive graph size. Invalid elements return a rejection result;
    a non-sequence route or an invalid n is a programming error.
    Python and NumPy integers are accepted without casting other scalar types.
    """
    if not _is_integer(n) or n < 1:
        raise ValueError("The graph size must be a positive integer.")
    n = int(n)
    _require_route_sequence(route)
    if len(route) != n:
        return RouteLegalityResult(False, "invalid_length")
    seen = bytearray(n)
    for position in range(n):
        vertex = route[position]
        if not _is_integer(vertex):
            return RouteLegalityResult(False, "invalid_vertex_type", position)
        vertex = int(vertex)
        if not 0 <= vertex < n:
            return RouteLegalityResult(False, "unknown_vertex", position, (vertex,))
        if seen[vertex]:
            return RouteLegalityResult(False, "repeated_vertex", position, (vertex,))
        seen[vertex] = 1
    return RouteLegalityResult(True)


def canonical_route(route: Sequence[int] | np.ndarray) -> tuple[int, ...]:
    """Return a legal permutation rotated to zero, choosing its orientation.

    The domain is 0..len(route)-1. Invalid input raises GraphError using the
    legality reason; the input is never changed and no graph edges are checked.
    """
    _require_route_sequence(route)
    snapshot = tuple(route[i] for i in range(len(route)))
    if not snapshot:
        raise GraphError("invalid_length", "A legal route cannot be empty.")
    result = check_route_legality(len(snapshot), snapshot)
    if not result.valid:
        raise GraphError(result.reason, f"Illegal route at position {result.position}.")
    values = tuple(int(vertex) for vertex in snapshot)
    start = values.index(0)
    rotated = values[start:] + values[:start]
    if len(rotated) >= 3 and rotated[1] > rotated[-1]:
        return (0,) + rotated[:0:-1]
    return rotated
