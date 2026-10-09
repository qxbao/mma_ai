"""Kiểm thử bộ chuẩn hoá quan sát chạy."""

import numpy as np


def test_inv_004_matches_numpy_stats() -> None:
    """INV-004: thống kê chạy khớp với trung bình và phương sai của NumPy."""
    from mma_ai.learning.normalizer import RunningNorm

    batches = [np.array([[1.0, 2.0], [3.0, 4.0]]), np.array([[5.0, 6.0]])]
    normalizer = RunningNorm()
    for batch in batches:
        normalizer.update(batch)

    samples = np.concatenate(batches)
    state = normalizer.state_dict()
    np.testing.assert_allclose(state["mean"], np.mean(samples, axis=0), atol=1e-9)
    np.testing.assert_allclose(state["var"], np.var(samples, axis=0), atol=1e-9)
    assert state["count"] == 3


def test_inv_004_state_dict_roundtrip() -> None:
    """INV-004: nạp lại trạng thái giữ nguyên phép chuẩn hoá."""
    from mma_ai.learning.normalizer import RunningNorm

    source = RunningNorm()
    source.update(np.array([[1.0, 3.0], [5.0, 7.0]]))
    restored = RunningNorm()
    restored.load_state_dict(source.state_dict())

    np.testing.assert_allclose(restored(np.array([3.0, 5.0])), source(np.array([3.0, 5.0])))


def test_inv_004_clip_obs() -> None:
    """INV-004: đầu ra chuẩn hoá được kẹp theo clip_obs."""
    from mma_ai.learning.normalizer import RunningNorm

    normalizer = RunningNorm(clip_obs=1.0)
    normalizer.update(np.array([[0.0], [1.0]]))

    assert float(normalizer(np.array([100.0]))[0]) == 1.0
    assert float(normalizer(np.array([-100.0]))[0]) == -1.0


def test_inv_004_update_order_independent_batches() -> None:
    """INV-004: gộp các lô theo thứ tự khác nhau cho cùng thống kê."""
    from mma_ai.learning.normalizer import RunningNorm

    batches = [np.array([[1.0, 2.0]]), np.array([[3.0, 4.0], [5.0, 6.0]])]
    first, second = RunningNorm(), RunningNorm()
    for batch in batches:
        first.update(batch)
    for batch in reversed(batches):
        second.update(batch)

    np.testing.assert_allclose(first.state_dict()["mean"], second.state_dict()["mean"], atol=1e-9)
    np.testing.assert_allclose(first.state_dict()["var"], second.state_dict()["var"], atol=1e-9)
