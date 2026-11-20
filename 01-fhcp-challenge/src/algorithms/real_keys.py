"""Deterministic real-key decoding shared by the DE and PSO adaptations."""

from collections.abc import Sequence
from fractions import Fraction

import numpy as np

from src.graphs.graph import _is_integer


class KeyDecodingError(ValueError):
    """Rejected key vector, with a stable code and optional element position."""

    def __init__(self, code: str, position: int | None = None) -> None:
        self.code = code
        self.position = position
        super().__init__(f"{code}: position={position}")


def decode_real_keys(n: int, keys: Sequence[object] | np.ndarray) -> tuple[int, ...]:
    """Return indices sorted by (key, index), without changing the input.

    Require a positive Python/NumPy integer n and a positional 1-D vector of
    length n. Keys may be Python/NumPy integers or floating scalars, excluding
    booleans and durations. Reject invalid shape, length, types and non-finite
    values before sorting. KeyDecodingError exposes code and position; solvers
    must propagate code='non_finite_state' with that stop reason, before fitness.

    Finite keys outside [0, 1] are allowed. No RNG, graph, fitness, cycle check
    or canonicalization is involved. The tuple is a legal permutation, which
    does not establish the existence of its edges or implicit closing edge.
    """
    if not _is_integer(n) or n < 1:
        raise KeyDecodingError("invalid_size")
    n = int(n)
    if isinstance(keys, np.ndarray):
        if keys.ndim != 1:
            raise KeyDecodingError("invalid_shape")
    elif not isinstance(keys, Sequence) or isinstance(keys, (str, bytes, bytearray)):
        raise KeyDecodingError("invalid_keys_type")
    if len(keys) != n:
        raise KeyDecodingError("invalid_length")

    values: list[int | Fraction] = []
    for position in range(n):
        value = keys[position]
        if _is_integer(value):
            values.append(int(value))
        elif isinstance(value, (float, np.floating)):
            if not np.isfinite(value):
                raise KeyDecodingError("non_finite_state", position)
            # Exact ratios avoid narrowing extended floats or rounding mixed
            # integer/float comparisons into artificial ties.
            values.append(Fraction(*value.as_integer_ratio()))
        else:
            raise KeyDecodingError("invalid_key_type", position)

    return tuple(sorted(range(n), key=lambda index: (values[index], index)))
