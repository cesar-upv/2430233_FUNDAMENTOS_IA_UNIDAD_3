"""Optional graph-aware operators; no files, certificates or global RNG state."""

from collections.abc import Mapping

import numpy as np

from src.graphs import Graph, GraphError, check_route_legality

from .execution import SolverRun


def resolve_search_options(values: Mapping, error_type, *, moves=False, construction=False):
    """Validate opt-in choices without adding fields to legacy configurations."""
    effective = {}
    if not construction and "initialization" in values:
        value = values["initialization"]
        if type(value) is not str or value not in ("uniform", "greedy"):
            raise error_type("invalid_parameter", "initialization", "Expected uniform or greedy.")
        effective["initialization"] = value
    if moves and "guided_move_rate" in values:
        value = values["guided_move_rate"]
        if type(value) not in (int, float) or not 0 <= value <= 1:
            raise error_type("invalid_parameter", "guided_move_rate", "Expected a finite rate in [0, 1].")
        effective["guided_move_rate"] = float(value)
    if construction and "construction" in values:
        value = values["construction"]
        if type(value) is not str or value not in ("all_vertices", "neighbor_guided"):
            raise error_type("invalid_parameter", "construction", "Expected all_vertices or neighbor_guided.")
        effective["construction"] = value
    return effective


def greedy_route(graph: Graph, run: SolverRun) -> tuple[int, ...] | None:
    """Walk to an unvisited neighbor of minimum remaining degree, with random ties.

    Start uniformly; jump uniformly among remaining vertices when blocked.
    A jump may create a missing edge. Closure is left to fitness/validation.
    Time checks also cover construction; interrupted prefixes are never evaluated.
    """
    n = graph.vertex_count()
    if not run.checkpoint():
        return None
    free = []
    for u in range(n):
        if not run.checkpoint():
            return None
        free.append(graph.degree(u))
    remaining = list(range(n))
    positions = list(range(n))
    visited = bytearray(n)
    route = []
    current = int(run.rng.integers(n))
    while remaining:
        if not run.checkpoint():
            return None
        route.append(current)
        visited[current] = 1
        position = positions[current]
        last = remaining[-1]
        remaining[position] = last
        positions[last] = position
        remaining.pop()
        neighbors = graph.neighbors(current)
        candidates = []
        for neighbor in neighbors:
            if not run.checkpoint():
                return None
            neighbor = int(neighbor)
            free[neighbor] -= 1
            if not visited[neighbor]:
                candidates.append(neighbor)
        if not remaining:
            break
        if candidates:
            least = min(free[v] for v in candidates)
            tied = [v for v in candidates if free[v] == least]
            current = tied[int(run.rng.integers(len(tied)))]
        else:
            run.count("greedy_jumps")
            current = remaining[int(run.rng.integers(len(remaining)))]
    if not run.checkpoint():
        return None
    run.count("greedy_routes_completed")
    return tuple(route)


def greedy_keys(graph: Graph, run: SolverRun) -> np.ndarray | None:
    """Encode a greedy permutation as distinct rank keys in [0, 1)."""
    route = greedy_route(graph, run)
    if route is None:
        return None
    keys = np.empty(len(route), dtype=np.float64)
    # Positive gaps make the decoded order exact, independently of float ties.
    keys[np.asarray(route)] = np.arange(len(route), dtype=np.float64) / len(route)
    return keys if run.checkpoint() else None


def guided_inversion(graph: Graph, route, run: SolverRun) -> tuple[int, ...] | None:
    """Reverse a segment to make an anchor adjacent to a sampled real neighbor.

    Preserve a legal permutation without modifying its input. This creates one
    real edge but can remove other edges; it does not guarantee improvement.
    An anchor with no eligible nonconsecutive neighbor returns the same route.
    """
    n = graph.vertex_count()
    legality = check_route_legality(n, route)
    if not legality.valid:
        raise GraphError(legality.reason, "Guided inversion requires a legal route.")
    if not run.checkpoint():
        return None
    anchor = int(run.rng.integers(n))
    current = int(route[anchor])
    excluded = {int(route[(anchor - 1) % n]), int(route[(anchor + 1) % n])}
    candidates = []
    for neighbor in graph.neighbors(current):
        if not run.checkpoint():
            return None
        if int(neighbor) not in excluded:
            candidates.append(int(neighbor))
    if not candidates:
        run.count("guided_noops")
        return tuple(route)
    target = candidates[int(run.rng.integers(len(candidates)))]
    position = None
    for index, vertex in enumerate(route):
        if not run.checkpoint():
            return None
        if vertex == target:
            position = index
            break
    assert position is not None
    lo, hi = (anchor + 1, position) if position > anchor else (position, anchor - 1)
    child = list(route)
    child[lo:hi + 1] = reversed(child[lo:hi + 1])
    if not run.checkpoint():
        return None
    run.count("guided_inversions")
    return tuple(child)
