"""Real-key ordering and permutation checks, without fitness or certification."""

from decimal import Decimal
from fractions import Fraction
from itertools import product

import numpy as np
import pytest

from src.algorithms import KeyDecodingError, decode_real_keys
from src.algorithms import real_keys
from src.algorithms.execution import Budget, SolverRun, start_run


@pytest.mark.parametrize("keys, expected", [
    ([0.10, 0.40, 0.20, 0.30], (0, 2, 3, 1)),  # Research #2, section 9.
    ([0.5, -2.0, 0.5, 7.0, -2.0], (1, 4, 0, 2, 3)),
    ([4.0, 4.0, 4.0], (0, 1, 2)),
    ([0.0, -0.0, 0.0, -0.0], (0, 1, 2, 3)),
    ([9, -1, -7], (2, 1, 0)),
    ([1.0, 2.0, 3.0], (0, 1, 2)),
    ([3.0, 2.0, 1.0], (2, 1, 0)),
    ([17.0], (0,)),
    ([2.0, -3.0], (1, 0)),
])
def test_examples_ties_and_small_legal_routes(keys, expected):
    before = keys.copy()
    result = decode_real_keys(len(keys), keys)
    assert result == expected
    assert isinstance(result, tuple)
    assert all(type(index) is int for index in result)
    assert keys == before


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_exhaustive_small_vectors_preserve_domain_and_order(n):
    for keys in product((-1, 0, 1), repeat=n):
        route = decode_real_keys(n, keys)
        assert len(route) == n
        assert set(route) == set(range(n))
        assert all((keys[a], a) < (keys[b], b) for a, b in zip(route, route[1:]))
        assert decode_real_keys(n, keys) == route


@pytest.mark.parametrize("dtype", [np.float16, np.float32, np.float64, np.longdouble])
def test_extreme_finite_floats_keep_their_order_and_precision(dtype):
    limit = np.finfo(dtype).max
    tiny = np.nextafter(dtype(0), dtype(1))
    after_one = np.nextafter(dtype(1), dtype(2))
    keys = np.array([limit, after_one, 1, tiny, -tiny, -limit], dtype=dtype)
    before = keys.copy()
    assert decode_real_keys(6, keys) == (5, 4, 3, 2, 1, 0)
    np.testing.assert_array_equal(keys, before)


def test_mixed_numeric_keys_do_not_create_ties_by_rounding():
    # np.float64 comparisons can round the adjacent large integer to a tie.
    keys = [2**53 + 1, np.float64(2**53), np.uint64(2**63 + 1), float(2**63)]
    assert decode_real_keys(4, keys) == (1, 0, 3, 2)
    huge = 10**1000
    assert decode_real_keys(3, [huge, np.longdouble(1), -huge]) == (2, 1, 0)


@pytest.mark.parametrize("n", [3, np.int32(3), np.int64(3), np.uint64(3)])
@pytest.mark.parametrize("keys", [
    [2, -3, 1], (2, -3, 1),
    np.array([2, -3, 1], dtype=np.int32),
    np.array([2, -3, 1], dtype=np.int64),
    np.array([2, 0, 1], dtype=np.uint64),
    np.array([2.0, -3, np.float32(1)], dtype=object),
])
def test_python_and_numpy_numeric_containers(n, keys):
    assert decode_real_keys(n, keys) == (1, 2, 0)


def test_range_is_a_positional_numeric_sequence():
    assert decode_real_keys(3, range(2, -1, -1)) == (2, 1, 0)


@pytest.mark.parametrize("read_only", [False, True])
def test_numpy_views_are_unchanged_and_output_has_no_alias(read_only):
    owner = np.array([99.0, 3.0, 99.0, -1.0, 99.0, 2.0])
    keys = owner[1::2][::-1]
    keys.setflags(write=not read_only)
    before = owner.copy()
    result = decode_real_keys(3, keys)
    assert result == (1, 0, 2)
    np.testing.assert_array_equal(owner, before)
    owner[:] = -99.0
    assert result == (1, 0, 2)


def test_mutable_sequence_is_unchanged_and_output_has_no_alias():
    keys = [3.0, -1.0, 2.0]
    result = decode_real_keys(3, keys)
    assert keys == [3.0, -1.0, 2.0]
    keys[:] = [0.0, 0.0, 0.0]
    assert result == (1, 2, 0)


@pytest.fixture
def forbid_sort(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("Rejected inputs must not reach sorting.")

    monkeypatch.setattr(real_keys, "sorted", fail, raising=False)


@pytest.mark.parametrize("n", [
    0, -1, True, np.bool_(True), 3.0, "3", None, np.array(3),
    np.timedelta64(3, "D"),
])
def test_invalid_size_is_rejected_first(n, forbid_sort):
    with pytest.raises(KeyDecodingError) as error:
        decode_real_keys(n, None)
    assert (error.value.code, error.value.position) == ("invalid_size", None)


@pytest.mark.parametrize("keys", [
    None, 3, 3.0, "123", b"123", bytearray(b"123"),
    {0, 1, 2}, {0: 1, 1: 2, 2: 3}, iter([0, 1, 2]),
])
def test_non_positional_and_text_inputs_are_rejected(keys, forbid_sort):
    with pytest.raises(KeyDecodingError) as error:
        decode_real_keys(3, keys)
    assert (error.value.code, error.value.position) == ("invalid_keys_type", None)


@pytest.mark.parametrize("keys", [
    np.array(3), np.ones((3, 1)), np.ones((1, 3)), np.ones((3, 1, 1)),
])
def test_numpy_shape_is_rejected_before_length_or_values(keys, forbid_sort):
    with pytest.raises(KeyDecodingError) as error:
        decode_real_keys(3, keys)
    assert (error.value.code, error.value.position) == ("invalid_shape", None)


@pytest.mark.parametrize("keys", [[], [None], [0, 1], [0, 1, 2, 3], np.array([])])
def test_length_is_checked_before_elements(keys, forbid_sort):
    with pytest.raises(KeyDecodingError) as error:
        decode_real_keys(3, keys)
    assert (error.value.code, error.value.position) == ("invalid_length", None)


@pytest.mark.parametrize("value", [
    True, np.bool_(False), "1", b"1", None, 1 + 0j, np.complex128(1),
    [1], (1,), np.array(1), np.timedelta64(1, "D"), np.datetime64("2026-11-11"),
    Decimal("1"), Fraction(1, 2),
])
def test_unsupported_scalar_types_are_rejected_without_coercion(value, forbid_sort):
    with pytest.raises(KeyDecodingError) as error:
        decode_real_keys(3, [0, value, 2])
    assert (error.value.code, error.value.position) == ("invalid_key_type", 1)


@pytest.mark.parametrize("keys", [
    np.array([True, False, True]), np.array(["0", "1", "2"]),
    np.array([0j, 1j, 2j]), [[0], [1], [2]],
])
def test_typed_arrays_and_nested_sequences_are_not_coerced(keys, forbid_sort):
    with pytest.raises(KeyDecodingError) as error:
        decode_real_keys(3, keys)
    assert (error.value.code, error.value.position) == ("invalid_key_type", 0)


@pytest.mark.parametrize("dtype", [float, np.float16, np.float32, np.float64, np.longdouble])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("position", [0, 1, 2])
def test_non_finite_keys_are_rejected_before_sorting(dtype, value, position, forbid_sort):
    keys = [0.0, 1.0, 2.0]
    keys[position] = dtype(value)
    with pytest.raises(KeyDecodingError) as error:
        decode_real_keys(3, keys)
    assert (error.value.code, error.value.position) == ("non_finite_state", position)


def test_first_invalid_element_is_reported_in_position_order(forbid_sort):
    with pytest.raises(KeyDecodingError) as error:
        decode_real_keys(3, [float("nan"), "bad", float("inf")])
    assert (error.value.code, error.value.position) == ("non_finite_state", 0)
    with pytest.raises(KeyDecodingError) as error:
        decode_real_keys(3, [0, "bad", float("nan")])
    assert (error.value.code, error.value.position) == ("invalid_key_type", 1)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_error_can_propagate_through_existing_run(example_graph, value):
    run = start_run(
        example_graph, seed=49, budget=Budget(max_evaluations=1),
        iteration_unit="generation", clock=lambda: 0,
    )
    assert isinstance(run, SolverRun)
    assert run.begin_phase("initialization", 1)
    with pytest.raises(KeyDecodingError) as error:
        decode_real_keys(5, [0, 1, value, 3, 4])
    exc = error.value
    result = run.fail("non_finite_state", exc.code, str(exc), position=exc.position)
    assert result.status == "error"
    assert result.stop_reason == "non_finite_state"
    assert result.error.code == "non_finite_state"
    assert result.error.detail == {"position": 2}
    assert result.error.phase == "initialization"
    assert result.counters.evaluations_started == 0
    assert result.counters.validations_started == 0
    assert result.best_route is None and result.best_cost is None
