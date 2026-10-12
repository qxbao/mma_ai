"""PoC chạy tay cho phát hiện F-001 và F-002 của T639 (cố ý ĐỎ cho tới khi vai chủ sửa).

Tệp này KHÔNG khớp `test_*.py` nên cổng `tests` (thu thập mặc định) không nạp nó; INV-006 cấm thêm
dấu bỏ qua mới nên ca đỏ không được gắn dấu nào. Chạy tay, chỉ định đúng đường dẫn tệp:

    uv run --isolated --with pytest --with pytest-xdist pytest -q -p no:cacheprovider \
        tests/challenge/poc_inv006_xdist_report.py

- F-001 (CRITICAL, INV-006/AC-6): chạy song song `-n 2` (dạng lệnh cổng `tests` dùng `-n auto`)
  thì tóm tắt test bị loại biến mất và trần tỷ lệ loại hết hiệu lực (mã thoát 0 dù loại 2/3).
- F-002 (MINOR, INV-004): `probe_display` không có trần thời gian; GLFW khởi tạo treo ⇒ treo theo.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

from mma_ai.compat.display import probe_display
from mma_ai.compat.platform_info import PlatformProfile

ROOT = Path(__file__).resolve().parents[2]

_CHILD_SUITE = textwrap.dedent(
    """
    import pytest

    def test_chay_duoc():
        assert len('ok') == 2

    @pytest.mark.windows_only(reason="Chỉ chạy trên Windows.")
    def test_cua_windows():
        raise AssertionError("test này không được phép chạy")

    @pytest.mark.requires_cuda(reason="Cần CUDA.")
    def test_cua_cuda():
        raise AssertionError("test này không được phép chạy")
    """
)


def _run_child(workdir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(ROOT / "tests" / "unit"), str(ROOT / "src")]),
        "MMA_AI_FORCE_NO_DISPLAY": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    env.pop("PYTEST_ADDOPTS", None)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "capability_gate",
            "--rootdir",
            str(workdir),
            *extra,
            "test_child.py",
        ],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
        check=False,
    )


def test_f001_xdist_run_still_reports_deselected_and_enforces_ratio(tmp_path: Path) -> None:
    """Tuần tự: mã thoát 1 + liệt kê 2 test bị loại. Song song phải cho kết quả TƯƠNG ĐƯƠNG."""
    (tmp_path / "test_child.py").write_text(_CHILD_SUITE, encoding="utf-8")
    serial = _run_child(tmp_path)
    parallel = _run_child(tmp_path, "-n", "2")
    assert serial.returncode == 1, "đối chứng: chạy tuần tự phải chặn vì loại 2/3 > 5%"
    assert "test_child.py::test_cua_windows" in serial.stdout
    assert parallel.returncode == serial.returncode, (
        f"mã thoát song song {parallel.returncode} ≠ tuần tự {serial.returncode}: "
        "trần tỷ lệ loại không còn hiệu lực dưới xdist\n" + parallel.stdout
    )
    assert "test_child.py::test_cua_windows" in parallel.stdout, (
        "test bị loại không được liệt kê ở bản tóm tắt khi chạy song song\n" + parallel.stdout
    )


def test_f002_probe_display_is_bounded_when_glfw_init_hangs() -> None:
    """Bộ khởi tạo GLFW treo 8 s: phép dò phải trả không khả dụng trong ≤ 5 s."""
    profile = PlatformProfile("windows", "11", "AMD64", (3, 12, 0), False, True)
    outcome: dict[str, bool] = {}

    def hang() -> bool:
        time.sleep(8)
        return True

    def run() -> None:
        outcome["available"] = probe_display(profile, environ={}, glfw_init=hang).available

    worker = threading.Thread(target=run, daemon=True)
    started = time.monotonic()
    worker.start()
    worker.join(5)
    assert not worker.is_alive(), f"probe_display còn treo sau {time.monotonic() - started:.1f} s"
    assert outcome == {"available": False}
