"""Kiểm thử tích hợp cho tính bất biến chỉ đọc (read-only invariant) của phiên replay và demo.

Truy vết các yêu cầu kỹ thuật và tiêu chí chấp nhận (acceptance criteria):
- 005 AC-2: Phiên demo chạy và lưu episode mà không làm ảnh hưởng tính toàn vẹn của thư mục run.
- FR-002: Chạy demo từ checkpoint điều khiển khuỷu tay mà không thay đổi dữ liệu checkpoint.
- FR-008: Ghi nguyên tử episode demo, không để lại tệp tạm khi gặp lỗi ghi đĩa.
- FR-015: Replay chỉ đọc mọi dữ liệu của run; không sửa đổi bất kỳ tệp huấn luyện nào.
- INV-002: Đường điều khiển duy nhất là kích thích cơ; không can thiệp trạng thái mô phỏng.
- INV-005: Hoạt động chỉ đọc (read-only) — không sửa, xoá hay thêm tệp trong thư mục run.
- CMD-VIS-0001: Điểm vào dòng lệnh python -m mma_ai.visualization.cli.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

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


def _get_clean_env() -> dict[str, str]:
    """Tạo bản sao biến môi trường đã loại bỏ DISPLAY và WAYLAND_DISPLAY."""
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    return env


def _compute_file_sha256(path: Path) -> str:
    """Tính toán mã băm SHA-256 của nội dung tệp tin."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _snapshot_directory(root: Path) -> dict[str, str]:
    """Tạo bản đồ ánh xạ đường dẫn tương đối sang mã băm SHA-256 cho toàn bộ tệp trong thư mục."""
    snapshot: dict[str, str] = {}
    for p in root.rglob("*"):
        if p.is_file():
            rel_path = str(p.relative_to(root))
            snapshot[rel_path] = _compute_file_sha256(p)
    return snapshot


def _create_sample_episode_file(dest: Path) -> Path:
    """Tạo tệp episode JSON hợp lệ mẫu trong thư mục run."""
    model_info = load_muscle_model("myoelbow").info
    names = list(model_info.muscle_names)

    frames = [
        Frame(
            t_s=0.0,
            qpos=[0.0],
            qvel=[0.0],
            activation=[0.05] * 6,
            excitation=None,
            fingertip_position_m=(-0.21, -0.106, 1.12),
            distance_m=0.15,
            reward=0.0,
        ),
        Frame(
            t_s=0.04,
            qpos=[0.1],
            qvel=[0.02],
            activation=[0.1] * 6,
            excitation=[0.1] * 6,
            fingertip_position_m=(-0.20, -0.105, 1.14),
            distance_m=0.10,
            reward=0.5,
        ),
    ]

    ep = Episode(
        schema_version="1.0.0",
        created_utc="2026-10-10T12:00:00Z",
        seed=42,
        model=ModelRecord(
            sha256=model_info.sha256,
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
        source=None,
        library_versions={"mujoco": "3.15.0", "numpy": "1.26.0"},
        timing=TimingRecord(action_dt_s=0.04, physics_timestep_s=0.002),
        outcome=OutcomeRecord(
            terminated=True,
            truncated=False,
            end_reason="reached",
            reached=True,
            n_actions=1,
            final_distance_m=0.05,
        ),
        frames=frames,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    write_episode(ep, dest)
    return dest


def _create_mock_run_directory(run_dir: Path) -> tuple[Path, Path]:
    """Dựng cấu trúc hoàn chỉnh của một thư mục run bao gồm cấu hình, tệp episode và checkpoint."""
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. Tệp cấu hình giả lập huấn luyện
    cfg_file = run_dir / "config.yaml"
    cfg_file.write_text(
        "run_id: run-test-readonly\nseed: 42\nenv:\n  split: train\n",
        encoding="utf-8",
    )

    # 2. Tệp hồ sơ run (manifest)
    manifest_file = run_dir / "manifest.json"
    manifest_file.write_text(
        json.dumps({"run_id": "run-test-readonly", "status": "completed"}, indent=2),
        encoding="utf-8",
    )

    # 3. Tệp episode đã ghi
    ep_file = _create_sample_episode_file(run_dir / "episodes" / "test_ep.json")

    # 4. Checkpoint hợp lệ phục vụ kiểm tra read-only cho demo
    from mma_ai.learning.checkpoint import save_checkpoint
    from mma_ai.learning.networks import ActorCritic
    from mma_ai.learning.normalizer import RunningNorm
    from mma_ai.learning.ppo import PPOAgent
    from mma_ai.learning.train_config import TrainConfig

    cfg = TrainConfig.load()
    norm = RunningNorm(clip_obs=cfg.normalization.clip_obs)
    norm.update(np.zeros((2, 14)))
    model = ActorCritic(obs_dim=14, act_dim=6, cfg=cfg)
    agent = PPOAgent(model=model, cfg=cfg)

    ctx = {
        "obs_normalizer": norm,
        "update_idx": 1,
        "env_steps": 128,
        "seed": 42,
        "model_sha256": load_muscle_model("myoelbow").info.sha256,
        "config": cfg,
    }
    save_checkpoint(agent=agent, run_dir=run_dir, kind="final", ctx=ctx)
    ckpt_file = run_dir / "checkpoints" / "ckpt_u000001_final.pt"
    assert ckpt_file.exists(), f"Không tìm thấy checkpoint tạo tại: {ckpt_file}"

    return ep_file, ckpt_file


def test_run_files_unchanged_by_replay_and_demo(tmp_path: Path) -> None:
    """INV-005, FR-015, AC-2: Replay và demo chỉ đọc dữ liệu của run; không thay đổi tệp nào."""
    run_dir = tmp_path / "run_readonly_test"
    ep_file, ckpt_file = _create_mock_run_directory(run_dir)
    clean_env = _get_clean_env()

    # Chụp ảnh mã băm (hash snapshot) toàn bộ thư mục run trước khi thực thi
    snapshot_initial = _snapshot_directory(run_dir)
    assert len(snapshot_initial) > 0, "Thư mục run phải có tệp dữ liệu ban đầu"

    # -------------------------------------------------------------------------
    # GIAI ĐOẠN 1: Chạy phát lại (replay) trên episode trong thư mục run
    # -------------------------------------------------------------------------
    proc_replay = subprocess.run(
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
        timeout=30.0,
        check=False,
    )
    assert proc_replay.returncode == 0, f"Replay thất bại: {proc_replay.stderr}"

    # Xác nhận toàn bộ thư mục run hoàn toàn không bị thay đổi sau replay
    snapshot_after_replay = _snapshot_directory(run_dir)
    assert snapshot_after_replay == snapshot_initial, (
        f"Thư mục run bị biến đổi sau khi chạy replay:\n"
        f"Mới: {set(snapshot_after_replay) - set(snapshot_initial)}\n"
        f"Mất: {set(snapshot_initial) - set(snapshot_after_replay)}"
    )

    # -------------------------------------------------------------------------
    # GIAI ĐOẠN 2: Chạy demo từ checkpoint trong thư mục run
    # -------------------------------------------------------------------------
    assert ckpt_file.exists(), "Tệp checkpoint phải tồn tại để thực thi demo"
    external_out = tmp_path / "external_output" / "demo_save.json"
    proc_demo = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--checkpoint",
            str(ckpt_file),
            "--headless",
            "--save-episode",
            str(external_out),
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=30.0,
        check=False,
    )
    assert proc_demo.returncode == 0, f"Demo thất bại: {proc_demo.stderr}"
    assert external_out.exists(), "Tệp episode ngoài phải được lưu thành công"

    # Xác nhận toàn bộ thư mục run hoàn toàn không bị thay đổi sau demo
    snapshot_after_demo = _snapshot_directory(run_dir)
    assert snapshot_after_demo == snapshot_initial, (
        f"Thư mục run bị biến đổi sau khi chạy demo:\n"
        f"Mới: {set(snapshot_after_demo) - set(snapshot_initial)}\n"
        f"Mất: {set(snapshot_initial) - set(snapshot_after_demo)}"
    )

    # ---------------------------------------------------------------------
    # GIAI ĐOẠN 3: Chạy demo qua con trỏ checkpoints/latest.json
    # ---------------------------------------------------------------------
    latest_file = run_dir / "checkpoints" / "latest.json"
    if latest_file.exists():
        proc_latest = subprocess.run(
            [
                sys.executable,
                "-m",
                "mma_ai.visualization.cli",
                "--checkpoint",
                str(latest_file),
                "--headless",
            ],
            capture_output=True,
            text=True,
            env=clean_env,
            timeout=30.0,
            check=False,
        )
        assert proc_latest.returncode == 0, f"Demo latest.json thất bại: {proc_latest.stderr}"

        snapshot_after_latest = _snapshot_directory(run_dir)
        assert snapshot_after_latest == snapshot_initial, (
            "Thư mục run bị biến đổi sau khi chạy demo qua con trỏ latest.json"
        )


def test_demo_atomic_write_disk_error_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-008, INV-004, AC-5: Tiêm lỗi ghi đĩa bảo đảm không để lại tệp dở dang."""
    from mma_ai.visualization import replay as replay_mod
    from mma_ai.visualization.errors import EpisodeWriteError

    target_dir = tmp_path / "readonly_dest"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "fail_demo.json"

    from mma_ai.visualization import episode as episode_mod

    # Gọi tên rõ ràng monkeypatch tiêm lỗi ghi đĩa vào write_episode
    def _mock_failing_write_episode(ep: Any, path: Path) -> Path:
        # Giả lập lỗi ghi đĩa ném EpisodeWriteError theo hợp đồng FR-008
        raise EpisodeWriteError(f"Mô phỏng lỗi ghi đĩa trên hệ thống tập tin tại '{path}'")

    monkeypatch.setattr(episode_mod, "write_episode", _mock_failing_write_episode)

    # Giả lập môi trường chạy demo với mock checkpoint
    from mma_ai.visualization.episode import (
        Episode,
        Frame,
        ModelRecord,
        OutcomeRecord,
        TargetRecord,
        TimingRecord,
    )

    dummy_ep = Episode(
        schema_version="1.0.0",
        created_utc="2026-10-10T12:00:00Z",
        seed=1,
        model=ModelRecord(
            sha256="a" * 64,
            source="myo_sim/elbow/myoelbow_1dof6muscles.xml",
            muscle_names=["m1", "m2", "m3", "m4", "m5", "m6"],
            nq=1,
            nv=1,
        ),
        target=TargetRecord(position_m=(0.0, 0.0, 0.0), split="test", index=0, tolerance_m=0.05),
        source=None,
        library_versions={},
        timing=TimingRecord(action_dt_s=0.04, physics_timestep_s=0.002),
        outcome=OutcomeRecord(
            terminated=True,
            truncated=False,
            end_reason="reached",
            reached=True,
            n_actions=1,
            final_distance_m=0.01,
        ),
        frames=[
            Frame(0.0, [0.0], [0.0], [0.1] * 6, None, (0.0, 0.0, 0.0), 0.1, 0.0),
            Frame(0.04, [0.1], [0.0], [0.1] * 6, [0.1] * 6, (0.0, 0.0, 0.0), 0.05, 1.0),
        ],
    )

    from mma_ai.visualization import recorder as recorder_mod

    monkeypatch.setattr(recorder_mod, "record_episode", lambda *a, **kw: dummy_ep)

    # Tạo tệp checkpoint giả và mock các hàm nạp
    ckpt_path = tmp_path / "dummy_ckpt.pt"
    ckpt_path.write_bytes(b"dummy")

    import mma_ai.learning.checkpoint as ckpt_mod

    class _MockLoaded:
        model_sha256 = load_muscle_model("myoelbow").info.sha256
        update_idx = 1

    monkeypatch.setattr(ckpt_mod, "load_checkpoint", lambda _p, **_kw: _MockLoaded())
    monkeypatch.setattr(ckpt_mod, "load_policy", lambda _p, **_kw: None)

    # Chạy run_replay trực tiếp với tham số demo và đường dẫn lưu lỗi
    exit_code = replay_mod.run_replay(
        [
            "--checkpoint",
            str(ckpt_path),
            "--headless",
            "--save-episode",
            str(target_file),
        ]
    )

    # Mã thoát 8 theo hợp đồng CMD-VIS-0001 (EpisodeWriteError)
    assert exit_code == 8, f"Kỳ vọng mã thoát 8 khi ghi đĩa thất bại nhưng nhận: {exit_code}"

    # Bảo đảm không tồn tại tệp đích cũng như tệp tạm thời (.tmp) trên đĩa
    assert not target_file.exists(), "Tệp đích không được tồn tại khi ghi thất bại"
    tmp_files = list(target_dir.glob("*.tmp"))
    assert not tmp_files, f"Phát hiện tệp tạm thời dở dang chưa được dọn dẹp: {tmp_files}"
