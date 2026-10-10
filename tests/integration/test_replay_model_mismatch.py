"""Kiểm thử tích hợp cho trường hợp mô hình mô phỏng bị lệch (model mismatch).

Truy vết các yêu cầu kỹ thuật và tiêu chí chấp nhận (acceptance criteria):
- 005 AC-4: Lệch mã băm XML mô hình dừng lệnh với mã 6 khi không có cờ chấp nhận.
- FR-012: Đối chiếu mô hình và cảnh báo liên tục khi bật cờ --allow-model-mismatch.
- FR-018: Định dạng thông báo lỗi tiếng Việt nêu cả hai mã băm và ngữ cảnh cụ thể.
- INV-001: Ngăn chặn phát lại sai ngầm; từ chối mọi mô hình không tương thích cấu trúc.
- CMD-VIS-0001: Điểm vào dòng lệnh python -m mma_ai.visualization.cli và mã thoát 6.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

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


def _get_clean_env() -> dict[str, str]:
    """Tạo bản sao biến môi trường đã loại bỏ DISPLAY và WAYLAND_DISPLAY."""
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    return env


def _create_mismatch_episode(
    file_path: Path,
    *,
    sha256: str = "f" * 64,
    nq: int = 1,
    nv: int = 1,
    muscle_names: list[str] | None = None,
) -> Path:
    """Tạo tệp episode mẫu với mã băm hoặc cấu trúc tuỳ biến để kiểm tra lệch mô hình."""
    names = muscle_names or ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"]
    dt = 0.04

    frames = [
        Frame(
            t_s=0.0,
            qpos=[0.0] * nq,
            qvel=[0.0] * nv,
            activation=[0.1] * 6,
            excitation=None,
            fingertip_position_m=(-0.21, -0.106, 1.12),
            distance_m=0.15,
            reward=0.0,
        ),
        Frame(
            t_s=0.04,
            qpos=[0.2] * nq,
            qvel=[0.05] * nv,
            activation=[0.2] * 6,
            excitation=[0.2] * 6,
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
            sha256=sha256,
            source="myo_sim/elbow/myoelbow_1dof6muscles.xml",
            muscle_names=names,
            nq=nq,
            nv=nv,
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
            n_actions=1,
            final_distance_m=0.05,
        ),
        library_versions={"mujoco": "3.15.0", "numpy": "1.26.0"},
        frames=frames,
        source=None,
    )

    write_episode(episode, file_path)
    return file_path


def test_mismatch_stops_names_both_hashes(tmp_path: Path) -> None:
    """005 AC-4, FR-012, FR-018, INV-001: Lệch mã băm XML dừng lệnh với mã 6 và nêu cả hai hash."""
    mismatch_sha = "a" * 64
    ep_file = _create_mismatch_episode(tmp_path / "mismatch_ep.json", sha256=mismatch_sha)
    clean_env = _get_clean_env()
    current_model_sha = load_muscle_model("myoelbow").info.sha256

    proc = subprocess.run(
        [sys.executable, "-m", "mma_ai.visualization.cli", "--episode", str(ep_file)],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )

    # CMD-VIS-0001, INV-001: Mã thoát phải là 6
    assert proc.returncode == 6, (
        f"Kỳ vọng mã thoát 6 khi lệch mô hình nhưng nhận {proc.returncode}.\n"
        f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    )

    # FR-012, FR-018: Stderr phải nêu rõ cả hai mã băm SHA-256
    assert mismatch_sha in proc.stderr, (
        f"Stderr không chứa mã băm của episode '{mismatch_sha}': {proc.stderr}"
    )
    assert current_model_sha in proc.stderr, (
        f"Stderr không chứa mã băm của mô hình hiện tại '{current_model_sha}': {proc.stderr}"
    )

    # FR-018: Thông báo lỗi bằng tiếng Việt rõ ràng
    stderr_lower = proc.stderr.lower()
    assert "lệch" in stderr_lower or "mismatch" in stderr_lower, (
        f"Stderr thiếu giải thích lỗi lệch mô hình: {proc.stderr}"
    )
    assert "--allow-model-mismatch" in proc.stderr, (
        f"Stderr thiếu gợi ý sử dụng cờ '--allow-model-mismatch': {proc.stderr}"
    )


def test_mismatch_allowed_warns_persistently(tmp_path: Path) -> None:
    """005 AC-4, FR-012, INV-001: Cho phép lệch mô hình với cờ, cảnh báo liên tục."""
    mismatch_sha = "b" * 64
    ep_file = _create_mismatch_episode(tmp_path / "mismatch_allowed_ep.json", sha256=mismatch_sha)
    clean_env = _get_clean_env()

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(ep_file),
            "--allow-model-mismatch",
            "--headless",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=20.0,
        check=False,
    )

    assert proc.returncode == 0, (
        f"Lệnh CLI thất bại với mã {proc.returncode}.\n"
        f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    )

    # 1. Kiểm tra cấu trúc bản ghi tóm tắt JSON từ stdout
    assert len(proc.stdout.strip()) > 0, "Chế độ --headless không xuất dữ liệu ra stdout"
    summary_data: dict[str, Any] = json.loads(proc.stdout)

    # 2. Xác thực với JSON Schema chuẩn của hợp đồng
    schema_path = _get_contracts_dir() / "replay-summary.schema.json"
    assert schema_path.is_file(), f"Không tìm thấy lược đồ hợp đồng: {schema_path}"
    schema_dict = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema_dict)
    validator.validate(summary_data)

    # 3. FR-012, INV-001: model_check phản ánh match=false nhưng compatible=true
    model_chk = summary_data["model_check"]
    assert model_chk["match"] is False, "Kỳ vọng model_check.match là False khi mã băm lệch"
    assert model_chk["compatible"] is True, "Kỳ vọng compatible là True khi cấu trúc khớp"
    assert model_chk["episode_sha256"] == mismatch_sha

    # 4. Cảnh báo lệch mô hình phải nằm trong danh sách warnings của tóm tắt
    warnings_list: list[str] = summary_data.get("warnings", [])
    has_mismatch_warning = any(
        "lệch" in str(w).lower() or "mismatch" in str(w).lower() for w in warnings_list
    )
    assert has_mismatch_warning, (
        f"Danh sách cảnh báo warnings thiếu thông tin lệch mô hình: {warnings_list}"
    )


def test_incompatible_structure_always_refused(tmp_path: Path) -> None:
    """005 AC-4, FR-012, INV-001: Cấu trúc không tương thích luôn bị từ chối với mã 6."""
    clean_env = _get_clean_env()

    # Ca 1: Số toạ độ suy rộng nq không khớp (nq=2 so với nq=1 của myoelbow)
    ep_nq_mismatch = _create_mismatch_episode(
        tmp_path / "nq_mismatch.json",
        sha256="c" * 64,
        nq=2,
    )
    proc_nq = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(ep_nq_mismatch),
            "--allow-model-mismatch",
            "--headless",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )

    assert proc_nq.returncode == 6, (
        f"Kỳ vọng mã thoát 6 khi nq không tương thích nhưng nhận {proc_nq.returncode}.\n"
        f"Stderr: {proc_nq.stderr}"
    )
    assert "không tương thích" in proc_nq.stderr.lower() or "cấu trúc" in proc_nq.stderr.lower()
    assert "nq" in proc_nq.stderr.lower()

    # Ca 2: Danh sách tên cơ bắp không khớp (thay đổi tên một cơ)
    alt_muscles = ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "DIFFERENT_NAME"]
    ep_muscle_mismatch = _create_mismatch_episode(
        tmp_path / "muscle_mismatch.json",
        sha256="d" * 64,
        muscle_names=alt_muscles,
    )
    proc_muscle = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(ep_muscle_mismatch),
            "--allow-model-mismatch",
            "--headless",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )

    assert proc_muscle.returncode == 6, (
        f"Kỳ vọng mã thoát 6 khi tên cơ không tương thích nhưng nhận {proc_muscle.returncode}.\n"
        f"Stderr: {proc_muscle.stderr}"
    )
    assert "không tương thích" in proc_muscle.stderr.lower() or "cơ" in proc_muscle.stderr.lower()
