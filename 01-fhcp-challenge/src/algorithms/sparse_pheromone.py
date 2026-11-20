"""O(m) pheromone storage on real undirected edges, with virtual missing pairs."""

from dataclasses import dataclass

import numpy as np

from src.graphs import Graph

from .execution import SolverRun


@dataclass(slots=True)
class EdgePheromone:
    values: np.ndarray
    edge_index: dict[tuple[int, int], int]
    missing_value: float

    def index(self, u: int, v: int) -> int | None:
        return self.edge_index.get((min(u, v), max(u, v)))

    def value(self, u: int, v: int) -> float:
        index = self.index(u, v)
        return self.missing_value if index is None else float(self.values[index])


def initialize_sparse(
    graph: Graph, initial: float, minimum: float, run: SolverRun,
) -> EdgePheromone | None:
    """Initialize only m entries; no n-by-n array or all-pairs index is built."""
    m = graph.edge_count()
    block_size = 65_536
    blocks = (m + block_size - 1) // block_size
    if not run.begin_phase("initialization", m + blocks):
        return None
    values = np.empty(m, dtype=np.float64)
    indices = {}
    for index, (u, v) in enumerate(graph.edges()):
        if not run.checkpoint():
            return None
        indices[(u, v)] = index
        run.record_item()
    for start in range(0, m, block_size):
        if not run.checkpoint():
            return None
        values[start:start + block_size].fill(initial)
        run.record_item()
    if not run.checkpoint():
        return None
    run.complete_phase()
    return EdgePheromone(values, indices, minimum)
