"""Kiểm thử tích hợp cho chế độ không màn hình (headless mode) qua giao diện dòng lệnh (CLI).

Truy vết các yêu cầu kỹ thuật và tiêu chí chấp nhận (acceptance criteria):
- 005 AC-3: Chế độ không màn hình (--headless) trên episode và kiểm tra dữ liệu tóm tắt.
- FR-006: Phiên phát cảnh báo thời lượng mô phỏng ngắn (simulation duration < 1.0 s) trên stderr.
- FR-010: Chế độ --headless xuất tóm tắt JSON chuẩn hoá ra stdout và không mở viewer.
- INV-003: Bản ghi tóm tắt máy đọc được không bỏ trường, không chứa NaN/Infinity.
- NFR-REL-001: Độ tin cậy số học (numerical reliability) của bản ghi tóm tắt.
- CMD-VIS-0001: Điểm vào dòng lệnh python -m mma_ai.visualization.cli.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

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


def _get_contracts_dir() -> Path:
    """Trả về đường dẫn thư mục hợp đồng (contracts directory) của phân hệ 005."""
    return (
        Path(__file__).resolve().parents[2]
        / "specs"
        / "005-replay-3d-muscle-demo"
        / "contracts"
    )


def _create_test_episode(
    file_path: Path,
    *,
    n_frames: int = 3,
    dt: float = 0.04,
) -> Path:
    """Tạo tệp episode JSON hợp lệ phục vụ kiểm thử tích hợp (integration testing)."""
    model_info = load_muscle_model("myoelbow").info
    names = list(model_info.muscle_names)
    model_sha = model_info.sha256

    frames: list[Frame] = []
    # Khung đầu tiên (t=0.0): excitation luôn là None theo luật R5
    frame0 = Frame(
        t_s=0.0,
        qpos=[0.0],
        qvel=[0.0],
        activation=[0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        excitation=None,
        fingertip_position_m=(-0.21, -0.106, 1.12),
        distance_m=0.15,
        reward=0.0,
    )
    frames.append(frame0)

    for i in range(1, n_frames):
        frames.append(
            Frame(
                t_s=round(i * dt, 4),
                qpos=[0.3],
                qvel=[0.05],
                activation=[0.2, 0.25, 0.15, 0.3, 0.2, 0.4],
                excitation=[0.2, 0.25, 0.15, 0.3, 0.2, 0.4],
                fingertip_position_m=(-0.20, -0.105, 1.14),
                distance_m=0.02,
                reward=1.0,
            )
        )

    episode = Episode(
        schema_version="1.0.0",
        created_utc="2026-10-10T12:00:00Z",
        seed=123,
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
        timing=TimingRecord(action_dt_s=dt, physics_timestep_s=0.002),
        outcome=OutcomeRecord(
            terminated=True,
            truncated=False,
            end_reason="reached",
            reached=True,
            n_actions=n_frames - 1,
            final_distance_m=0.02,
        ),
        library_versions={"mujoco": "3.15.0", "numpy": "1.26.0"},
        frames=frames,
        source=None,
    )

    write_episode(episode, file_path)
    return file_path


def _get_clean_env() -> dict[str, str]:
    """Tạo môi trường thực thi đã bỏ đặt DISPLAY và WAYLAND_DISPLAY."""
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    return env


def test_summary_has_all_fields(tmp_path: Path) -> None:
    """005 AC-3, FR-010, INV-003, NFR-REL-001: Tóm tắt JSON đầy đủ trường và hợp chuẩn schema."""
    # Tạo tệp episode hợp lệ có 35 khung hình (thời lượng 1.36 s > 1.0 s)
    ep_file = _create_test_episode(tmp_path / "long_episode.json", n_frames=35, dt=0.04)

    clean_env = _get_clean_env()
    cmd = [
        sys.executable,
        "-m",
        "mma_ai.visualization.cli",
        "--episode",
        str(ep_file),
        "--headless",
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=30.0,
        check=False,
    )

    assert proc.returncode == 0, (
        f"Lệnh CLI thất bại với mã thoát {proc.returncode}.\n"
        f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    )

    # 1. Kiểm tra cấu trúc JSON hợp lệ từ stdout
    assert len(proc.stdout.strip()) > 0, "Chế độ --headless không xuất dữ liệu ra stdout"
    summary_data: dict[str, Any] = json.loads(proc.stdout)

    # 2. Xác thực với JSON Schema chuẩn của hợp đồng
    schema_path = _get_contracts_dir() / "replay-summary.schema.json"
    assert schema_path.is_file(), f"Không tìm thấy lược đồ hợp đồng: {schema_path}"
    schema_dict = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema_dict)
    validator.validate(summary_data)

    # 3. Kiểm tra chi tiết sự hiện diện và giá trị của toàn bộ các trường bắt buộc
    expected_fields = [
        "schema_version",
        "mode",
        "headless",
        "source",
        "model_check",
        "n_frames",
        "n_actions",
        "duration_sim_s",
        "seed",
        "target",
        "outcome",
        "activation",
        "saved_episode",
        "playback",
        "warnings",
    ]
    for field in expected_fields:
        assert field in summary_data, f"Thiếu trường bắt buộc '{field}' trong tóm tắt JSON"

    assert summary_data["schema_version"] == "1.0.0"
    assert summary_data["mode"] == "episode"
    assert summary_data["headless"] is True
    assert summary_data["playback"] is None
    assert summary_data["n_frames"] == 35
    assert summary_data["n_actions"] == 34
    assert pytest.approx(summary_data["duration_sim_s"], rel=1e-3) == 1.36
    # Đường dẫn trong tóm tắt phải là đường dẫn tương đối (FR-018, constitution VI)
    ep_path_str = str(summary_data["source"]["episode_path"])
    assert not Path(ep_path_str).is_absolute(), (
        f"FR-018: Đường dẫn episode_path phải là tương đối, nhận: {ep_path_str}"
    )
    assert (Path.cwd() / ep_path_str).resolve() == ep_file.resolve()

    # Kiểm tra thống kê activation của 6 cơ bắp
    act = summary_data["activation"]
    assert len(act["muscle_names"]) == 6
    assert len(act["min"]) == 6
    assert len(act["max"]) == 6
    assert len(act["mean"]) == 6
    assert len(act["final"]) == 6


def test_short_episode_hint_on_stderr(tmp_path: Path) -> None:
    """005 AC-3, FR-006: Episode ngắn (< 1 s) in cảnh báo và gợi ý tốc độ ra stderr."""
    # Tạo episode ngắn gồm 2 khung hình (thời lượng 0.04 s < 1.0 s)
    short_ep_file = _create_test_episode(tmp_path / "short_episode.json", n_frames=2, dt=0.04)

    clean_env = _get_clean_env()
    cmd = [
        sys.executable,
        "-m",
        "mma_ai.visualization.cli",
        "--episode",
        str(short_ep_file),
        "--headless",
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=30.0,
        check=False,
    )

    assert proc.returncode == 0, (
        f"Lệnh CLI thất bại với mã thoát {proc.returncode}.\n"
        f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    )

    # Kiểm tra thông báo hướng dẫn cho episode ngắn xuất hiện trên stderr
    stderr_lower = proc.stderr.lower()
    assert "thời lượng mô phỏng của episode ngắn" in stderr_lower or "ngắn" in stderr_lower, (
        f"Stderr không chứa thông báo thời lượng episode ngắn: {proc.stderr}"
    )
    assert "--speed 0.1" in proc.stderr, "Stderr thiếu gợi ý cờ '--speed 0.1'"
    assert "--loop" in proc.stderr, "Stderr thiếu gợi ý cờ '--loop'"
