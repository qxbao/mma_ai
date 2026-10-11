"""Kiểm thử đầu-cuối (end-to-end, E2E) cho các entrypoint Viewer của feature 007.

Truy vết: AC-1, AC-2, AC-3, AC-4, FR-001, FR-003, INV-002, INV-003,
NFR-PERF-001 và NFR-REL-001.

Các kiểm thử này chỉ gọi entrypoint thật bằng tiến trình con, không mock (đối tượng giả
trong test) và không gọi trực tiếp hàm nội bộ thay cho CLI.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_EPISODE = (
    PROJECT_ROOT
    / "specs/005-replay-3d-muscle-demo/contracts/examples/episode.from-checkpoint-reached.json"
)
NO_DISPLAY_TIMEOUT_S = 5.0
DISPLAY_TIMEOUT_S = 25.0
MONITOR_START_TIMEOUT_S = 5.0
MONITOR_STOP_TIMEOUT_S = 5.0


def _without_display() -> dict[str, str]:
    """Tạo môi trường buộc nhánh không màn hình của CLI thật."""
    environment = os.environ.copy()
    environment.pop("DISPLAY", None)
    environment.pop("WAYLAND_DISPLAY", None)
    return environment


def _run_bounded(
    command: Sequence[str],
    *,
    timeout_s: float,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Chạy CLI có timeout (hết hạn chờ) và dọn cả nhóm tiến trình khi quá hạn."""
    proc = subprocess.Popen(
        list(command),
        cwd=PROJECT_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = proc.communicate()
        pytest.fail(
            f"CLI vượt quá hạn mức {timeout_s:.1f} s.\n"
            f"Lệnh: {' '.join(command)}\nStdout: {stdout}\nStderr: {stderr}"
        )
        raise AssertionError("pytest.fail phải dừng kiểm thử")
    return subprocess.CompletedProcess(list(command), proc.returncode, stdout, stderr)


def _children_of(pid: int) -> set[int]:
    """Lấy PID con trực tiếp từ bảng tiến trình, không phụ thuộc thư viện ngoài."""
    table = subprocess.run(
        ["ps", "-eo", "pid=,ppid="],
        capture_output=True,
        text=True,
        check=True,
    )
    children: set[int] = set()
    for line in table.stdout.splitlines():
        fields = line.split()
        if len(fields) == 2 and int(fields[1]) == pid:
            children.add(int(fields[0]))
    return children


def _wait_for_ui_file(run_dir: Path, timeout_s: float) -> dict[str, object]:
    """Chờ điều kiện CLI sẵn sàng qua ui.json, không chờ mốc thời gian cố định."""
    deadline = time.monotonic() + timeout_s
    ui_path = run_dir / "ui.json"
    while time.monotonic() < deadline:
        if ui_path.is_file():
            return cast(dict[str, object], json.loads(ui_path.read_text(encoding="utf-8")))
        time.sleep(0.02)
    pytest.fail(f"CLI quan sát không tạo ui.json trong {timeout_s:.1f} s")
    raise AssertionError("pytest.fail phải dừng kiểm thử")


def _stop_monitor(proc: subprocess.Popen[str]) -> tuple[str, str]:
    """Gửi tín hiệu dừng, rồi ép dọn toàn nhóm nếu entrypoint không tự kết thúc."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGINT)
        return proc.communicate(timeout=MONITOR_STOP_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = proc.communicate()
        pytest.fail(
            f"CLI quan sát không dừng trong {MONITOR_STOP_TIMEOUT_S:.1f} s sau SIGINT.\n"
            f"Stdout: {stdout}\nStderr: {stderr}"
        )
        raise AssertionError("pytest.fail phải dừng kiểm thử")


def test_ac_1_ac_3_viewer_entrypoint_forced_no_display() -> None:
    """AC-1, AC-3, AC-4, FR-001, NFR-PERF-001, NFR-REL-001.

    Viewer thật báo thiếu màn hình trong hạn mức.
    """
    started = time.monotonic()
    result = _run_bounded(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(EXAMPLE_EPISODE),
            "--allow-model-mismatch",
        ],
        timeout_s=NO_DISPLAY_TIMEOUT_S,
        environment=_without_display(),
    )
    elapsed = time.monotonic() - started

    assert elapsed <= NO_DISPLAY_TIMEOUT_S
    assert result.returncode == 7, result.stderr
    assert "--headless" in result.stderr
    assert "màn hình" in result.stderr.lower() or "hiển thị" in result.stderr.lower()


def test_ac_1_ac_3_viewer_entrypoint_with_display_when_available() -> None:
    """AC-1, AC-3, AC-4, FR-001, NFR-PERF-001.

    Viewer thật phát lại và in tóm tắt khi màn hình dùng được.
    """
    # CLI tự chọn nhánh theo khả dụng thực tế; không dùng skip/xfail trong môi trường headless.
    from mma_ai.visualization.display import display_available  # type: ignore[import-untyped]

    if not display_available().available:
        result = _run_bounded(
            [
                sys.executable,
                "-m",
                "mma_ai.visualization.cli",
                "--episode",
                str(EXAMPLE_EPISODE),
                "--allow-model-mismatch",
            ],
            timeout_s=NO_DISPLAY_TIMEOUT_S,
            environment=_without_display(),
        )
        assert result.returncode == 7, result.stderr
        return

    result = _run_bounded(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(EXAMPLE_EPISODE),
            "--allow-model-mismatch",
        ],
        timeout_s=DISPLAY_TIMEOUT_S,
    )
    assert result.returncode == 0, f"Stdout: {result.stdout}\nStderr: {result.stderr}"
    for expected in (
        "Tóm tắt phiên phát lại:",
        "Thời lượng mô phỏng=",
        "Thời gian thực=",
        "Tỷ lệ tốc độ=",
        "Số khung trễ=",
    ):
        assert expected in result.stdout


def test_ac_2_monitoring_entrypoint_view3d_separate_process_cleans_up(tmp_path: Path) -> None:
    """AC-2, AC-4, FR-003, INV-002, NFR-PERF-001.

    Entrypoint quan sát dừng sạch sau khi gọi --view3d.
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "mma_ai.monitoring.cli",
            "--run",
            str(run_dir),
            "--port",
            "0",
            "--view3d",
        ],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        ui_info = _wait_for_ui_file(run_dir, MONITOR_START_TIMEOUT_S)
        assert ui_info["pid"] == proc.pid

        deadline = time.monotonic() + MONITOR_START_TIMEOUT_S
        observed_children: set[int] = set()
        while time.monotonic() < deadline:
            observed_children.update(_children_of(proc.pid))
            if observed_children:
                break
            time.sleep(0.02)

        # Không màn hình khiến View3D thoát ngay theo NFR-HEADLESS-001; có màn hình thì
        # PID con phải quan sát được và khác PID entrypoint thật.
        if observed_children:
            assert proc.pid not in observed_children
        else:
            assert not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"), (
                "Không quan sát được tiến trình View3D dù môi trường có màn hình"
            )
    finally:
        _stop_monitor(proc)

    assert proc.returncode == 0, "CLI quan sát phải dừng với mã 0 sau SIGINT"
    assert not _children_of(proc.pid), "Còn tiến trình con mồ côi sau khi CLI quan sát đã dừng"
