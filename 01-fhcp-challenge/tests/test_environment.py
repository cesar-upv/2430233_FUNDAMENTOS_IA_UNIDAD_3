"""Integration smoke checks for the numerical environment, not FHCP solvers."""

import numpy as np
import pytest


def test_numpy_executes_vector_operations():
    values = np.array([2, 3, 5], dtype=np.int32)
    np.testing.assert_array_equal(values * values, [4, 9, 25])


def test_explicit_int32_storage_preserves_large_indices():
    values = np.array([0, 9527, 630566, 2**31 - 1], dtype=np.int32)
    assert values.itemsize == 4
    assert values.tolist() == [0, 9527, 630566, 2**31 - 1]


def test_read_only_view_shares_storage_and_rejects_assignment():
    owner = np.array([1, 2, 4], dtype=np.int32)
    view = owner.view()
    view.setflags(write=False)
    assert np.shares_memory(owner, view)
    with pytest.raises(ValueError):
        view[0] = 99
    np.testing.assert_array_equal(owner, [1, 2, 4])
