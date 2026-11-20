"""Full missing-edge count for legal Hamiltonian cycle candidates."""

from collections.abc import Sequence

import numpy as np

from src.graphs import Graph, check_route_legality


class CostEvaluationError(ValueError):
    """Rejected evaluation with contract code and context, without a cost."""

    def __init__(
        self, code: str, position: int | None = None, vertices: tuple[int, ...] = (),
    ) -> None:
        self.code = code
        self.position = position
        self.vertices = vertices
        super().__init__(f"{code}: position={position}, vertices={vertices}")


def evaluate_cost(graph: Graph, route: Sequence[object] | np.ndarray) -> int:
    """Return the integer cost to minimize, including the implicit closure.

    Raise CostEvaluationError for small graphs or illegal routes before querying
    any edge. Non-positional containers retain the legality helper's TypeError.
    Recompute every pair, without repair, mutation, caching or certification.
    """
    n = graph.vertex_count()
    if n < 3:
        raise CostEvaluationError("graph_too_small")
    legality = check_route_legality(n, route)
    if not legality.valid:
        raise CostEvaluationError(legality.reason, legality.position, legality.vertices)
    cost = 0
    for position in range(n):
        if not graph.has_edge(route[position], route[(position + 1) % n]):
            cost += 1
    return cost
