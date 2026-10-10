"""Kiểm thử tích hợp cho bộ xem mô phỏng 3D thật (MuJoCo Real Viewer Integration Test).

Truy vết các yêu cầu kỹ thuật và tiêu chí chấp nhận (acceptance criteria):
- 005 AC-1: Mở MuJoCo Viewer và phát lại một episode đã lưu theo đúng thứ tự các khung đã ghi.
- 005 AC-2: Demo: chạy policy và xem khuỷu tay tới mục tiêu (hiển thị trực tiếp).
- FR-001: Phát lại chuỗi khung hình theo đúng thứ tự đã ghi trong MuJoCo Viewer.
- FR-004: Hiển thị điểm đánh dấu mục tiêu (target marker) tại đúng vị trí đã ghi.
- FR-005: Hiển thị 6 giá trị kích hoạt cơ (muscle activation) của từng khung hình kèm tên cơ.
- FR-014: Mã thoát phản ánh kết quả phát lại (thoát mã 0 khi phát xong hoặc đóng viewer).
- FR-011: Khi thiếu màn hình, báo lỗi rõ bằng tiếng Việt và thoát mã 7 trong <= 5 s.
- CMD-VIS-0001: Giao diện dòng lệnh python -m mma_ai.visualization.cli.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

from mma_ai.physics.body_model import load_muscle_model
from mma_ai.visualization.display import display_available
from mma_ai.visualization.episode import (
    Episode,
    Frame,
    ModelRecord,
    OutcomeRecord,
    TargetRecord,
    TimingRecord,
    write_episode,
)


def _create_real_viewer_episode(file_path: Path) -> Path:
    """Tạo một bản ghi episode mẫu hợp lệ phục vụ kiểm thử tích hợp viewer thật."""
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
            qpos=[0.1],
            qvel=[0.03],
            activation=[0.15, 0.12, 0.2, 0.18, 0.11, 0.25],
            excitation=[0.15, 0.12, 0.2, 0.18, 0.11, 0.25],
            fingertip_position_m=(-0.205, -0.105, 1.125),
            distance_m=0.10,
            reward=0.5,
        ),
        Frame(
            t_s=0.08,
            qpos=[0.2],
            qvel=[0.05],
            activation=[0.2, 0.15, 0.3, 0.22, 0.12, 0.35],
            excitation=[0.2, 0.15, 0.3, 0.22, 0.12, 0.35],
            fingertip_position_m=(-0.20, -0.104, 1.13),
            distance_m=0.05,
            reward=0.9,
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
            n_actions=2,
            final_distance_m=0.05,
        ),
        library_versions={"mujoco": "3.15.0", "numpy": "1.26.0"},
        frames=frames,
        source=None,
    )

    write_episode(episode, file_path)
    return file_path


def _create_real_viewer_config(file_path: Path, hold_s: float = 0.1) -> Path:
    """Tạo tệp cấu hình replay tuỳ biến với thời gian giữ khung cuối xác định."""
    config_dict = {
        "playback": {
            "speed": 1.0,
            "loop": False,
            "display_hz": 60,
            "hold_after_end_s": hold_s,
        },
        "demo": {
            "split": "test",
            "target_index": 0,
            "seed": 12345,
        },
        "hud": {
            "decimals": 3,
            "bar_width": 10,
        },
        "target_marker": {
            "radius_m": 0.02,
            "rgba": [1.0, 0.2, 0.2, 0.6],
        },
    }
    with file_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(config_dict, fh)
    return file_path


@pytest.mark.display  # type: ignore[untyped-decorator]
def test_real_viewer_plays_or_reports_no_display(tmp_path: Path) -> None:
    """AC-1, AC-2, FR-001, FR-004, FR-005, FR-014: Kiểm thử viewer thật theo display_available().

    - Có màn hình: python -m mma_ai.visualization.cli --episode mở viewer, phát đủ khung, mã 0.
    - Không màn hình: mã 7 + thông báo tiếng Việt gợi ý --headless.
    - Cả hai nhánh là khẳng định thật, KHÔNG skip/xfail.
    """
    ep_file = _create_real_viewer_episode(tmp_path / "valid_episode.json")
    cfg_file = _create_real_viewer_config(tmp_path / "viewer_config.yaml", hold_s=0.1)

    disp_status = display_available()

    if disp_status.available:
        # ----------------------------------------------------------------------
        # NHÁNH CÓ MÀN HÌNH HIỂN THỊ (REAL DISPLAY AVAILABLE)
        # ----------------------------------------------------------------------
        cmd = [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(ep_file),
            "--config",
            str(cfg_file),
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=25.0,
            check=False,
        )

        # FR-014: Thoát mã 0 sau khi hoàn tất phát lại bình thường
        assert proc.returncode == 0, (
            f"Kỳ vọng mã thoát 0 khi mở viewer có màn hình nhưng nhận {proc.returncode}.\n"
            f"Stdout: {proc.stdout}\nStderr: {proc.stderr}"
        )

        # FR-001, AC-1: Dòng tóm tắt tiếng Việt ở cuối phiên phát lại
        assert "Tóm tắt phiên phát lại:" in proc.stdout, (
            f"Thiếu thông điệp tóm tắt tiếng Việt trong stdout: {proc.stdout}"
        )
        assert "Thời lượng mô phỏng=" in proc.stdout, "Thiếu thời lượng mô phỏng"
        assert "Thời gian thực=" in proc.stdout, "Thiếu thời gian thực"
        assert "Tỷ lệ tốc độ=" in proc.stdout, "Thiếu tỷ lệ tốc độ"
        assert "Số khung trễ=" in proc.stdout, "Thiếu số khung trễ"

    else:
        # ----------------------------------------------------------------------
        # NHÁNH KHÔNG CÓ MÀN HÌNH HIỂN THỊ (HEADLESS / NO DISPLAY)
        # ----------------------------------------------------------------------
        cmd = [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(ep_file),
        ]

        start_time = time.perf_counter()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15.0,
            check=False,
        )
        elapsed = time.perf_counter() - start_time

        # FR-011, NFR-HEADLESS-001: Phản hồi nhanh trong <= 5.0 s
        assert elapsed <= 5.0, f"Thời gian thực thi {elapsed:.2f} s vượt quá ngưỡng 5.0 s"

        # INV-004, CMD-VIS-0001: Mã thoát 7 khi thiếu màn hình hiển thị
        assert proc.returncode == 7, (
            f"Kỳ vọng mã thoát 7 khi thiếu màn hình nhưng nhận {proc.returncode}.\n"
            f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
        )

        # FR-011: Thông báo lỗi tiếng Việt và gợi ý cờ --headless
        assert "--headless" in proc.stderr, "Stderr thiếu gợi ý sử dụng cờ '--headless'"
        stderr_lower = proc.stderr.lower()
        assert "màn hình" in stderr_lower or "hiển thị" in stderr_lower, (
            f"Stderr thiếu giải thích nguyên nhân màn hình hiển thị: {proc.stderr}"
        )


def test_real_viewer_forced_no_display_reports_code_7(tmp_path: Path) -> None:
    """FR-011, INV-004, AC-3: Kiểm tra độc lập nhánh không màn hình bằng môi trường cách ly.

    Đảm bảo nhánh không màn hình luôn được thực thi kể cả khi chạy trên máy có màn hình.
    """
    ep_file = _create_real_viewer_episode(tmp_path / "valid_episode.json")

    # Tạo môi trường cách ly loại bỏ hoàn toàn biến hiển thị DISPLAY và WAYLAND_DISPLAY
    clean_env = os.environ.copy()
    clean_env.pop("DISPLAY", None)
    clean_env.pop("WAYLAND_DISPLAY", None)

    start_time = time.perf_counter()
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(ep_file),
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )
    elapsed = time.perf_counter() - start_time

    assert elapsed <= 5.0, f"Thời gian phản hồi {elapsed:.2f} s vượt quá 5.0 s"
    assert proc.returncode == 7, (
        f"Kỳ vọng mã thoát 7 khi không có màn hình nhưng nhận {proc.returncode}.\n"
        f"Stderr: {proc.stderr}"
    )
    assert "--headless" in proc.stderr
    assert "màn hình" in proc.stderr.lower() or "hiển thị" in proc.stderr.lower()
