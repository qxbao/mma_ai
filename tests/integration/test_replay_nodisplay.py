"""Kiểm thử tích hợp cho môi trường không có màn hình hiển thị (no display environment).

Truy vết các yêu cầu kỹ thuật và tiêu chí chấp nhận (acceptance criteria):
- 005 AC-3: Môi trường không màn hình thoát mã khác 0 (mã 7) trong <= 5 s khi không có --headless.
- FR-010: Chế độ --headless hoàn tất thành công mã 0 và in bản tóm tắt hợp lệ.
- FR-011: Báo lỗi rõ bằng tiếng Việt nêu nguyên nhân và gợi ý --headless khi thiếu màn hình.
- FR-015: Chế độ --headless không phụ thuộc và không nạp thư viện đồ hoạ (graphics library).
- NFR-HEADLESS-001: Đường không màn hình không treo, phản hồi nhanh (thời gian thực thi <= 5 s).
- INV-004: Thoát mã lỗi 7 xác định khi không thể khởi tạo giao diện đồ hoạ.
- CMD-VIS-0001: Hợp đồng dòng lệnh và các mã thoát của python -m mma_ai.visualization.cli.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from mma_ai.physics.body_model import load_muscle_model
from mma_ai.visualization.episode import (
    Episode,
    Frame,
    ModelRecord,
    OutcomeRecord,
    TargetRecord,
    TimingRecord,
    write_episode,
)


def _create_test_episode(file_path: Path) -> Path:
    """Tạo tệp episode mẫu hợp lệ phục vụ kiểm thử tích hợp không màn hình."""
    model_info = load_muscle_model("myoelbow").info
    names = list(model_info.muscle_names)
    model_sha = model_info.sha256

    frames = [
        Frame(
            t_s=0.0,
            qpos=[0.0],
            qvel=[0.0],
            activation=[0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
            excitation=None,
            fingertip_position_m=(-0.21, -0.106, 1.12),
            distance_m=0.15,
            reward=0.0,
        ),
        Frame(
            t_s=0.04,
            qpos=[0.2],
            qvel=[0.05],
            activation=[0.15, 0.2, 0.1, 0.25, 0.1, 0.3],
            excitation=[0.15, 0.2, 0.1, 0.25, 0.1, 0.3],
            fingertip_position_m=(-0.20, -0.105, 1.13),
            distance_m=0.05,
            reward=0.8,
        ),
    ]

    episode = Episode(
        schema_version="1.0.0",
        created_utc="2026-10-10T12:00:00Z",
        seed=42,
        model=ModelRecord(
            sha256=model_sha,
            source="myo_sim/elbow/myoelbow_1dof6muscles.xml",
            muscle_names=names,
            nq=1,
            nv=1,
        ),
        target=TargetRecord(
            position_m=(-0.19, -0.10, 1.16),
            split="test",
            index=0,
            tolerance_m=0.05,
        ),
        timing=TimingRecord(action_dt_s=0.04, physics_timestep_s=0.002),
        outcome=OutcomeRecord(
            terminated=True,
            truncated=False,
            end_reason="reached",
            reached=True,
            n_actions=1,
            final_distance_m=0.05,
        ),
        library_versions={"mujoco": "3.15.0", "numpy": "1.26.0"},
        frames=frames,
        source=None,
    )

    write_episode(episode, file_path)
    return file_path


def _get_clean_env() -> dict[str, str]:
    """Tạo bản sao biến môi trường đã loại bỏ DISPLAY và WAYLAND_DISPLAY."""
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    return env


def test_no_display_exits_7_fast_with_hint(tmp_path: Path) -> None:
    """005 AC-3, FR-011, NFR-HEADLESS-001, INV-004: Thoát mã 7 trong <= 5 s và gợi ý --headless."""
    ep_file = _create_test_episode(tmp_path / "valid_episode.json")
    clean_env = _get_clean_env()

    start_time = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "mma_ai.visualization.cli", "--episode", str(ep_file)],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )
    elapsed = time.perf_counter() - start_time

    # NFR-HEADLESS-001: Phải hoàn tất kiểm tra và thoát trong tối đa 5.0 giây
    assert elapsed <= 5.0, f"Thời gian thực thi {elapsed:.2f} s vượt quá ngưỡng 5.0 s"

    # CMD-VIS-0001: Mã thoát 7 tương ứng với DisplayUnavailable
    assert proc.returncode == 7, (
        f"Kỳ vọng mã thoát 7 khi thiếu màn hình nhưng nhận {proc.returncode}.\n"
        f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    )

    # FR-011: Thông báo lỗi bằng tiếng Việt và gợi ý cờ --headless
    stderr_lower = proc.stderr.lower()
    assert "--headless" in proc.stderr, "Stderr thiếu gợi ý sử dụng cờ '--headless'"
    assert "màn hình" in stderr_lower or "hiển thị" in stderr_lower, (
        f"Stderr thiếu giải thích nguyên nhân màn hình hiển thị: {proc.stderr}"
    )


def test_headless_exit0_with_summary(tmp_path: Path) -> None:
    """005 AC-3, FR-010: Chế độ --headless không cần màn hình, thoát mã 0 kèm tóm tắt JSON."""
    ep_file = _create_test_episode(tmp_path / "valid_episode.json")
    clean_env = _get_clean_env()

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(ep_file),
            "--headless",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=20.0,
        check=False,
    )

    assert proc.returncode == 0, (
        f"Chế độ --headless thất bại với mã {proc.returncode}.\n"
        f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    )

    summary_dict: dict[str, Any] = json.loads(proc.stdout)
    assert summary_dict.get("headless") is True
    assert summary_dict.get("mode") == "episode"
    assert summary_dict.get("schema_version") == "1.0.0"


def test_bogus_display_handled_like_no_display(tmp_path: Path) -> None:
    """005 AC-3, FR-011, NFR-HEADLESS-001: DISPLAY giả lập hỏng được xử lý như không có màn hình."""
    ep_file = _create_test_episode(tmp_path / "valid_episode.json")
    bogus_env = _get_clean_env()
    bogus_env["DISPLAY"] = ":99"

    start_time = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "mma_ai.visualization.cli", "--episode", str(ep_file)],
        capture_output=True,
        text=True,
        env=bogus_env,
        timeout=15.0,
        check=False,
    )
    elapsed = time.perf_counter() - start_time

    assert elapsed <= 5.0, f"Thời gian thực thi {elapsed:.2f} s vượt ngưỡng 5.0 s"
    assert proc.returncode == 7, (
        f"Kỳ vọng mã thoát 7 khi DISPLAY hỏng nhưng nhận {proc.returncode}.\n"
        f"Stderr: {proc.stderr}"
    )
    assert "--headless" in proc.stderr
    assert ":99" in proc.stderr or "màn hình" in proc.stderr.lower()


def test_missing_display_library_handled_gracefully(tmp_path: Path) -> None:
    """005 AC-3, FR-010, FR-011, FR-015: Hoạt động bền bỉ khi thiếu thư viện đồ hoạ (vd glfw)."""
    ep_file = _create_test_episode(tmp_path / "valid_episode.json")
    clean_env = _get_clean_env()

    # 1. Khi thiếu thư viện đồ hoạ và không dùng cờ --headless: báo lỗi thoát mã 7
    no_display_script = (
        "import sys\n"
        "sys.modules['glfw'] = None\n"
        "from mma_ai.visualization.cli import main\n"
        f"sys.exit(main(['--episode', {str(ep_file)!r}]))\n"
    )

    start_time = time.perf_counter()
    proc_no_display = subprocess.run(
        [sys.executable, "-c", no_display_script],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )
    elapsed = time.perf_counter() - start_time

    assert elapsed <= 5.0, f"Thời gian thực thi {elapsed:.2f} s vượt ngưỡng 5.0 s"
    assert proc_no_display.returncode == 7
    assert "--headless" in proc_no_display.stderr

    # 2. Khi thiếu thư viện đồ hoạ nhưng dùng cờ --headless: chạy bình thường thoát mã 0 (FR-015)
    headless_script = (
        "import sys\n"
        "sys.modules['glfw'] = None\n"
        "from mma_ai.visualization.cli import main\n"
        f"sys.exit(main(['--episode', {str(ep_file)!r}, '--headless']))\n"
    )

    proc_headless = subprocess.run(
        [sys.executable, "-c", headless_script],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=20.0,
        check=False,
    )

    assert proc_headless.returncode == 0, (
        f"Chế độ --headless không hoạt động khi thiếu glfw: {proc_headless.stderr}"
    )
    summary_data = json.loads(proc_headless.stdout)
    assert summary_data.get("headless") is True
