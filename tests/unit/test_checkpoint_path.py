"""Kiểm thử độc lập cho đường dẫn checkpoint dạng portable."""

from mma_ai.learning.checkpoint_path import checkpoint_record_path


def test_inv_005_checkpoint_record_path_normalizes_windows_roots() -> None:
    """INV-005: Đường dẫn Windows thành đường dẫn record tương đối có dấu `/`."""
    assert checkpoint_record_path(r"\runs\checkpoints\state.pt") == (
        "runs/checkpoints/state.pt"
    )
    assert checkpoint_record_path(r"C:\runs\checkpoints\state.pt") == (
        "runs/checkpoints/state.pt"
    )
