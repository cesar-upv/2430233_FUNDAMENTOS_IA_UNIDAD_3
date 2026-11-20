"""Permutation moves and exact missing-edge deltas for undirected cycles."""

from dataclasses import dataclass
from typing import Literal

from src.graphs import Graph

from .execution import SolverRun


@dataclass(frozen=True, slots=True)
class RouteMove:
    kind: Literal["swap", "inversion"]
    first: int
    second: int

    def _check(self, n: int) -> None:
        if self.kind not in ("swap", "inversion"):
            raise ValueError("Unknown move kind.")
        if (type(self.first) is not int or type(self.second) is not int
                or not 0 <= self.first < n or not 0 <= self.second < n):
            raise ValueError("Move indices must be integers in [0, n).")
        if self.kind == "inversion" and self.first > self.second:
            raise ValueError("Inversion indices must be ordered.")

    def apply(self, route: tuple[int, ...]) -> tuple[int, ...]:
        self._check(len(route))
        child = list(route)
        if self.kind == "swap":
            child[self.first], child[self.second] = child[self.second], child[self.first]
        else:
            child[self.first:self.second + 1] = reversed(child[self.first:self.second + 1])
        return tuple(child)

    def cost_after(self, graph: Graph, route: tuple[int, ...], cost: int) -> int:
        """Update a known legal route's exact cost; include the closing edge.

        A swap affects at most four edge positions, with overlaps deduplicated.
        Reversal preserves internal undirected edges, changing two boundaries.
        Materialization/legality checks remain separate from these edge queries.
        """
        n = len(route)
        self._check(n)
        i, j = self.first, self.second
        if i == j or (self.kind == "inversion" and i == 0 and j == n - 1):
            return cost
        if self.kind == "swap":
            positions = {(i - 1) % n, i, (j - 1) % n, j}
            def vertex(k):
                return route[j] if k == i else (route[i] if k == j else route[k])
        else:
            positions = {(i - 1) % n, j}
            def vertex(k):
                return route[i + j - k] if i <= k <= j else route[k]
        delta = 0
        for k in sorted(positions):
            following = (k + 1) % n
            delta += int(not graph.has_edge(vertex(k), vertex(following)))
            delta -= int(not graph.has_edge(route[k], route[following]))
        return cost + delta


def random_swap_move(n: int, run: SolverRun) -> RouteMove:
    i, j = run.rng.choice(n, size=2, replace=False)
    return RouteMove("swap", int(i), int(j))


def guided_move(graph: Graph, route: tuple[int, ...], run: SolverRun) -> RouteMove | None:
    """Plan the v2 guided inversion without scanning graph edges for its cost."""
    n = len(route)
    if not run.checkpoint():
        return None
    anchor = int(run.rng.integers(n))
    excluded = {route[(anchor - 1) % n], route[(anchor + 1) % n]}
    candidates = []
    for neighbor in graph.neighbors(route[anchor]):
        if not run.checkpoint():
            return None
        if int(neighbor) not in excluded:
            candidates.append(int(neighbor))
    if not candidates:
        run.count("guided_noops")
        return RouteMove("inversion", 0, 0)
    target = candidates[int(run.rng.integers(len(candidates)))]
    for position, vertex in enumerate(route):
        if not run.checkpoint():
            return None
        if vertex == target:
            break
    lo, hi = (anchor + 1, position) if position > anchor else (position, anchor - 1)
    if not run.checkpoint():
        return None
    run.count("guided_inversions")
    return RouteMove("inversion", lo, hi)


def resolve_cost_options(values, error_type):
    """Keep legacy parameter dictionaries intact when options are absent."""
    options = {}
    if "cost_mode" in values:
        mode = values["cost_mode"]
        if type(mode) is not str or mode not in ("full", "incremental"):
            raise error_type("invalid_parameter", "cost_mode", "Expected full or incremental.")
        options["cost_mode"] = mode
    if "incremental_check_interval" in values:
        interval = values["incremental_check_interval"]
        if type(interval) is not int or interval < 1:
            raise error_type("invalid_parameter", "incremental_check_interval", "Expected an integer >= 1.")
        if values.get("cost_mode") != "incremental":
            raise error_type("invalid_parameter", "incremental_check_interval", "Requires incremental cost mode.")
        options["incremental_check_interval"] = interval
    if options.get("cost_mode") == "incremental":
        options.setdefault("incremental_check_interval", 1000)
    return options
