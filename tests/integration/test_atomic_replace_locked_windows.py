"""Trace: API-PLT-0005 / INV-003 / AC-4."""

from pathlib import Path

import pytest

from mma_ai.compat.fsio import write_bytes_atomic

pytestmark = pytest.mark.windows_only(
    reason="Kiểm chứng thay thế tệp đang mở trên Windows thật."
)


def test_inv_003_replace_over_open_destination_keeps_old_bytes(tmp_path: Path) -> None:
    destination = tmp_path / "locked.bin"
    destination.write_bytes(b"old")

    with destination.open("rb"):
        with pytest.raises(OSError):
            write_bytes_atomic(destination, b"new")

    assert destination.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [destination]
