"""Independent Hamiltonian cycle certification using graph contract #17."""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from src.graphs import Graph, check_route_legality


@dataclass(frozen=True, slots=True)
class CycleValidationResult:
    """Certification or first rejection, with zero-based position and indices."""

    valid: bool
    reason: str | None = None
    position: int | None = None
    vertices: tuple[int, ...] = ()


def validate_cycle(graph: Graph, route: Sequence[object] | np.ndarray) -> CycleValidationResult:
    """Certify a route with implicit closure without modifying either input.

    Reject small graphs before inspecting the route, then propagate legality
    failures before checking consecutive edges and closure. Non-positional
    containers raise TypeError as in check_route_legality. Neither fitness nor
    a solver's success flag participates in certification.
    """
    n = graph.vertex_count()
    if n < 3:
        return CycleValidationResult(False, "graph_too_small")
    legality = check_route_legality(n, route)
    if not legality.valid:
        return CycleValidationResult(
            False, legality.reason, legality.position, legality.vertices,
        )
    for position in range(n - 1):
        u, v = int(route[position]), int(route[position + 1])
        if not graph.has_edge(u, v):
            return CycleValidationResult(False, "missing_edge", position, (u, v))
    last, first = int(route[n - 1]), int(route[0])
    if not graph.has_edge(last, first):
        return CycleValidationResult(False, "missing_closing_edge", n - 1, (last, first))
    return CycleValidationResult(True)
