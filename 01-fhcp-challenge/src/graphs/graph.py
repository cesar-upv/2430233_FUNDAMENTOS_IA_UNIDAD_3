"""Immutable, simple undirected graphs with sorted CSR adjacency."""

from bisect import bisect_left
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from numbers import Integral
from types import MappingProxyType

import numpy as np
from numpy.typing import NDArray


class GraphError(ValueError):
    """A rejected graph or route input, with a code from contract #17."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _is_integer(value: object) -> bool:
    """Accept integer scalars without treating durations as numeric indices."""
    # NumPy timedelta64 satisfies Integral but represents a duration.
    return isinstance(value, Integral) and not isinstance(value, (bool, np.timedelta64))


def _label_index(labels: tuple[int, ...], label: object) -> int:
    if not _is_integer(label):
        raise GraphError("invalid_label_type", "An external label must be an integer.")
    label = int(label)
    index = bisect_left(labels, label)
    if index == len(labels) or labels[index] != label:
        raise GraphError("unknown_label", f"Unknown external label: {label}.")
    return index


def _immutable_int32(values: Iterable[int]) -> NDArray[np.int32]:
    """Detach storage from all mutable inputs; WRITEABLE cannot be re-enabled."""
    return np.frombuffer(np.fromiter(values, dtype=np.int32).tobytes(), dtype=np.int32)


@dataclass(frozen=True, slots=True, init=False, eq=False)
class Graph:
    """Construct CSR from ascending integer labels and external edge pairs.

    Input order and endpoint orientation do not affect the resulting graph.
    No file is read, no edge is repaired and no Hamiltonicity is assumed.
    """

    _labels: tuple[int, ...]
    _offsets: NDArray[np.int32]
    _adjacency: NDArray[np.int32]
    _source: Mapping[str, str]

    def __init__(
        self,
        external_labels: Iterable[int],
        external_edges: Iterable[tuple[int, int]],
        *,
        source: Mapping[str, str] | None = None,
    ) -> None:
        labels = tuple(external_labels)
        if not labels or any(not _is_integer(label) for label in labels):
            raise GraphError("invalid_labels", "Labels must be nonempty integers.")
        labels = tuple(int(label) for label in labels)
        if any(left >= right for left, right in zip(labels, labels[1:])):
            raise GraphError("invalid_labels", "Labels must be strictly ascending.")
        if len(labels) > np.iinfo(np.int32).max:
            raise OverflowError("The vertex count exceeds int32 CSR capacity.")

        rows: list[list[int]] = [[] for _ in labels]
        seen: set[tuple[int, int]] = set()
        for left, right in external_edges:
            u = _label_index(labels, left)
            v = _label_index(labels, right)
            if u == v:
                raise GraphError("self_loop", f"Self loop at external label {left}.")
            edge = (min(u, v), max(u, v))
            if edge in seen:
                raise GraphError("duplicate_edge", f"Repeated undirected edge: {left}, {right}.")
            seen.add(edge)
            rows[u].append(v)
            rows[v].append(u)
        if 2 * len(seen) > np.iinfo(np.int32).max:
            raise OverflowError("The adjacency length exceeds int32 CSR capacity.")

        offsets = [0]
        for row in rows:
            row.sort()
            offsets.append(offsets[-1] + len(row))
        metadata = {} if source is None else dict(source)
        if any(not isinstance(key, str) or not isinstance(value, str)
               for key, value in metadata.items()):
            raise TypeError("Source metadata must map strings to strings.")
        object.__setattr__(self, "_labels", labels)
        object.__setattr__(self, "_offsets", _immutable_int32(offsets))
        object.__setattr__(self, "_adjacency", _immutable_int32(v for row in rows for v in row))
        object.__setattr__(self, "_source", MappingProxyType(metadata))

    @property
    def source(self) -> Mapping[str, str]:
        """Detached, read-only provenance; empty for an in-memory graph by default."""
        return self._source

    def vertex_count(self) -> int:
        return len(self._labels)

    def edge_count(self) -> int:
        return len(self._adjacency) // 2

    def _vertex_index(self, vertex: object) -> int:
        if not _is_integer(vertex) or not 0 <= vertex < self.vertex_count():
            raise GraphError("invalid_vertex_index", f"Invalid internal index: {vertex!r}.")
        return int(vertex)

    def degree(self, u: int) -> int:
        u = self._vertex_index(u)
        return int(self._offsets[u + 1]) - int(self._offsets[u])

    def neighbors(self, u: int) -> NDArray[np.int32]:
        """Return an O(1) view with immutable bytes as its only storage owner.

        A fresh array header also prevents changing the shape/dtype of an
        internal array through the public view's ``base`` attribute.
        """
        u = self._vertex_index(u)
        start = int(self._offsets[u])
        stop = int(self._offsets[u + 1])
        return np.frombuffer(
            self._adjacency.base, dtype=np.int32, count=stop - start,
            offset=start * np.dtype(np.int32).itemsize,
        )

    def has_edge(self, u: int, v: int) -> bool:
        u = self._vertex_index(u)
        v = self._vertex_index(v)
        if u == v:
            return False
        start, stop = int(self._offsets[u]), int(self._offsets[u + 1])
        other_start, other_stop = int(self._offsets[v]), int(self._offsets[v + 1])
        if other_stop - other_start < stop - start:
            start, stop, v = other_start, other_stop, u
        position = bisect_left(self._adjacency, v, start, stop)
        return position < stop and int(self._adjacency[position]) == v

    def edges(self) -> Iterator[tuple[int, int]]:
        """Yield every undirected edge once, in lexicographic internal order."""
        for u in range(self.vertex_count()):
            for position in range(int(self._offsets[u]), int(self._offsets[u + 1])):
                v = int(self._adjacency[position])
                if u < v:
                    yield u, v

    def external_label(self, i: int) -> int:
        return self._labels[self._vertex_index(i)]

    def index_of(self, label: int) -> int:
        return _label_index(self._labels, label)
