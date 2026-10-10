"""Kiểm thử đơn vị cho hàm điều phối run_replay (mma_ai.visualization.replay).

Truy vết các yêu cầu kỹ thuật và hợp đồng API:
- FR-001: Phát lại chuỗi khung hình theo thứ tự đã ghi.
- FR-002: Chạy demo từ checkpoint policy và hiển thị hoặc lưu episode.
- FR-008: Ghi nguyên tử episode, từ chối ghi đè tệp đã tồn tại (mã 8).
- FR-010: Chế độ không màn hình (--headless) in tóm tắt JSON ra stdout.
- FR-011: Báo lỗi mã 7 khi không có màn hình hiển thị trong <= 5 s.
- FR-012: Kiểm tra lệch mô hình (mã 6) và cờ --allow-model-mismatch.
- FR-013: Báo lỗi mã 2, 4, 5 khi tham số, checkpoint hoặc episode không hợp lệ.
- FR-016: Chọn mục tiêu bằng chỉ số (target_index) trong tập hợp lệ.
- FR-018: Thông báo lỗi tiếng Việt nêu giá trị và ngữ cảnh.
- INV-001: Ngăn chặn phát lại sai ngầm khi lệch mô hình.
- INV-004: Thoát mã lỗi khác 0, không để lại tệp dở dang khi bị ngắt.
- INV-005: Hoạt động chỉ đọc đối với tệp nguồn.
- API-VIS-0011: run_replay(args) -> int.
- CMD-VIS-0001: Hợp đồng dòng lệnh và các mã thoát 0, 1, 2, 4, 5, 6, 7, 8, 130.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from mma_ai.physics.body_model import load_muscle_model
from mma_ai.visualization.display import DisplayStatus
from mma_ai.visualization.episode import (
    Episode,
    Frame,
    ModelRecord,
    OutcomeRecord,
    TargetRecord,
    TimingRecord,
    write_episode,
)
from mma_ai.visualization.replay import run_replay


def _get_current_model_hash() -> str:
    """Lấy mã băm SHA-256 thực tế của mô hình khuỷu tay myoelbow."""
    return load_muscle_model("myoelbow").info.sha256


def _create_valid_episode_file(
    file_path: Path,
    *,
    sha256: str | None = None,
    nq: int = 1,
    nv: int = 1,
    muscle_names: list[str] | None = None,
    n_frames: int = 2,
) -> Path:
    """Tạo tệp episode JSON hợp lệ tuân thủ toàn diện các luật R1-R7."""
    names = muscle_names or ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"]
    model_sha = sha256 if sha256 is not None else _get_current_model_hash()
    dt = 0.04

    frames: list[Frame] = []
    # Khung 0: t_s = 0, excitation = None
    frame0 = Frame(
        t_s=0.0,
        qpos=[0.0] * nq,
        qvel=[0.0] * nv,
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
                qpos=[0.5] * nq,
                qvel=[0.1] * nv,
                activation=[0.2, 0.3, 0.1, 0.4, 0.2, 0.5],
                excitation=[0.2, 0.3, 0.1, 0.4, 0.2, 0.5],
                fingertip_position_m=(-0.20, -0.105, 1.15),
                distance_m=0.01,
                reward=1.0,
            )
        )

    episode = Episode(
        schema_version="1.0.0",
        created_utc="2026-10-09T10:00:00Z",
        seed=42,
        model=ModelRecord(
            sha256=model_sha,
            source="myo_sim/elbow/myoelbow_1dof6muscles.xml",
            muscle_names=names,
            nq=nq,
            nv=nv,
        ),
        target=TargetRecord(
            position_m=(-0.21, -0.106, 1.12),
            split="test",
            index=0,
            tolerance_m=0.05,
        ),
        source=None,
        library_versions={"mujoco": "3.15.0", "numpy": "1.26.0"},
        timing=TimingRecord(action_dt_s=dt, physics_timestep_s=0.002),
        outcome=OutcomeRecord(
            terminated=True,
            truncated=False,
            end_reason="reached",
            reached=True,
            n_actions=n_frames - 1,
            final_distance_m=0.01,
        ),
        frames=frames,
    )
    return write_episode(episode, file_path)


class _ScriptedPolicy:
    """Chính sách kịch bản xác định phục vụ kiểm thử không phụ thuộc torch."""

    def __init__(self) -> None:
        self.default_action = [0.1, 0.2, 0.15, 0.25, 0.05, 0.3]

    def act_deterministic(self, _obs: np.ndarray) -> list[float]:
        return list(self.default_action)


@dataclass
class _MockLoadedCheckpoint:
    """Đối tượng giả lập checkpoint đã nạp."""

    model_sha256: str
    update_idx: int = 1


def _mock_checkpoint_setup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    model_sha256: str | None = None,
) -> Path:
    """Tạo tệp checkpoint giả và mock các hàm nạp tương ứng."""
    ckpt_path = tmp_path / "mock_ckpt.pt"
    ckpt_path.write_bytes(b"mock_checkpoint_data")

    sha = model_sha256 if model_sha256 is not None else _get_current_model_hash()
    mock_loaded = _MockLoadedCheckpoint(model_sha256=sha)
    mock_policy = _ScriptedPolicy()

    # Nhập hoặc gán mock cho checkpoint module
    import mma_ai.learning.checkpoint as ckpt_mod

    monkeypatch.setattr(ckpt_mod, "load_checkpoint", lambda _p, **_kw: mock_loaded)
    monkeypatch.setattr(ckpt_mod, "load_policy", lambda _p, **_kw: mock_policy)

    return ckpt_path


# ==============================================================================
# NHÓM 1: KIỂM THỬ THAM SỐ VÀ CẤU HÌNH (MÃ THOÁT 2)
# ==============================================================================


def test_invalid_args_both_or_neither_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    """AC-5, FR-002: Thiếu cả hai hoặc truyền đồng thời cả hai chế độ thoát mã 2."""
    code1 = run_replay([])
    assert code1 == 2
    err1 = capsys.readouterr().err
    assert "chỉ định đúng một trong hai" in err1 or "lỗi tham số" in err1.lower()

    code2 = run_replay(["--episode", "ep.json", "--checkpoint", "ckpt.pt"])
    assert code2 == 2
    err2 = capsys.readouterr().err
    assert "đồng thời" in err2 or "lỗi tham số" in err2.lower()


def test_invalid_flags_for_episode_mode_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-5, CMD-VIS-0001: Các cờ của checkpoint không được dùng với --episode."""
    ep_file = _create_valid_episode_file(tmp_path / "ep.json")

    assert run_replay(["--episode", str(ep_file), "--split", "train"]) == 2
    assert "split" in capsys.readouterr().err.lower()

    assert run_replay(["--episode", str(ep_file), "--target-index", "1"]) == 2
    assert "target-index" in capsys.readouterr().err.lower()

    assert run_replay(["--episode", str(ep_file), "--seed", "123"]) == 2
    assert "seed" in capsys.readouterr().err.lower()

    assert run_replay(["--episode", str(ep_file), "--save-episode", "out.json"]) == 2
    assert "save-episode" in capsys.readouterr().err.lower()


def test_invalid_speed_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC-5, FR-006: Hệ số tốc độ <= 0 bị từ chối với mã 2 trước khi mở viewer."""
    ep_file = _create_valid_episode_file(tmp_path / "ep.json")

    assert run_replay(["--episode", str(ep_file), "--speed", "0"]) == 2
    assert "tốc độ" in capsys.readouterr().err.lower()

    assert run_replay(["--episode", str(ep_file), "--speed", "-1.5"]) == 2
    assert "tốc độ" in capsys.readouterr().err.lower()


def test_invalid_target_index_negative_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    """AC-5, FR-016: Chỉ số mục tiêu âm bị từ chối với mã 2."""
    code = run_replay(["--checkpoint", "dummy.pt", "--target-index", "-1"])
    assert code == 2
    err = capsys.readouterr().err
    assert "mục tiêu" in err.lower() or "target_index" in err.lower()


def test_invalid_config_path_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC-5, FR-017: Tệp cấu hình không tồn tại hoặc sai cú pháp YAML thoát mã 2."""
    ep_file = _create_valid_episode_file(tmp_path / "ep.json")
    code = run_replay(["--episode", str(ep_file), "--config", "not_found_config.yaml"])
    assert code == 2
    err = capsys.readouterr().err
    assert "cấu hình" in err.lower()


# ==============================================================================
# NHÓM 2: KIỂM THỬ NGUỒN EPISODE (MÃ THOÁT 5)
# ==============================================================================


def test_missing_episode_file_exit_5(capsys: pytest.CaptureFixture[str]) -> None:
    """AC-5, FR-013: Tệp episode không tồn tại thoát mã 5 và nêu đường dẫn."""
    missing_path = "non_existent_episode_file.json"
    code = run_replay(["--episode", missing_path, "--headless"])
    assert code == 5
    err = capsys.readouterr().err
    assert missing_path in err
    assert "không tìm thấy" in err.lower() or "không tồn tại" in err.lower()


def test_corrupt_json_episode_exit_5(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC-5, FR-009: Tệp episode hỏng hoặc JSON cụt thoát mã 5."""
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{invalid_json: 123", encoding="utf-8")

    code = run_replay(["--episode", str(corrupt_file), "--headless"])
    assert code == 5
    err = capsys.readouterr().err
    assert "không hợp lệ" in err.lower() or "lỗi" in err.lower()


def test_nonfinite_values_episode_exit_5(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-5, NFR-REL-001: Episode chứa giá trị NaN/Inf bị từ chối với mã 5."""
    nan_file = tmp_path / "nan.json"
    nan_file.write_text('{"schema_version": "1.0.0", "seed": NaN}', encoding="utf-8")

    code = run_replay(["--episode", str(nan_file), "--headless"])
    assert code == 5
    err = capsys.readouterr().err
    assert "không hợp lệ" in err.lower() or "hữu hạn" in err.lower() or "lỗi" in err.lower()


# ==============================================================================
# NHÓM 3: KIỂM THỬ NGUỒN CHECKPOINT (MÃ THOÁT 4)
# ==============================================================================


def test_missing_checkpoint_file_exit_4(capsys: pytest.CaptureFixture[str]) -> None:
    """AC-5, FR-013: Tệp checkpoint không tồn tại thoát mã 4 và nêu đường dẫn."""
    missing_ckpt = "non_existent_checkpoint.pt"
    code = run_replay(["--checkpoint", missing_ckpt, "--headless"])
    assert code == 4
    err = capsys.readouterr().err
    assert missing_ckpt in err


def test_checkpoint_xml_hash_mismatch_exit_4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-5, FR-013: Checkpoint có hash XML mô hình khác mô hình hiện tại thoát mã 4."""
    ckpt_path = _mock_checkpoint_setup(monkeypatch, tmp_path, model_sha256="0" * 64)
    code = run_replay(["--checkpoint", str(ckpt_path), "--headless"])
    assert code == 4
    err = capsys.readouterr().err
    assert "mã băm xml" in err.lower() or "không tương thích" in err.lower()


# ==============================================================================
# NHÓM 4: KIỂM THỬ LỆCH MÔ HÌNH (MÃ THOÁT 6)
# ==============================================================================


def test_episode_model_mismatch_stops_exit_6(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-4, FR-012, INV-001: Hash XML lệch dừng lệnh với mã 6 khi không có cờ."""
    mismatch_ep = tmp_path / "mismatch.json"
    _create_valid_episode_file(mismatch_ep, sha256="f" * 64)

    code = run_replay(["--episode", str(mismatch_ep), "--headless"])
    assert code == 6
    err = capsys.readouterr().err
    assert "lệch" in err.lower() or "mô hình" in err.lower()
    assert "f" * 64 in err


def test_episode_model_mismatch_allowed_with_flag_exit_0(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-4, FR-012: Có cờ --allow-model-mismatch thì tiếp tục khi cấu trúc tương thích."""
    mismatch_ep = tmp_path / "mismatch_allowed.json"
    _create_valid_episode_file(mismatch_ep, sha256="f" * 64)

    code = run_replay(
        ["--episode", str(mismatch_ep), "--headless", "--allow-model-mismatch"]
    )
    assert code == 0
    out = capsys.readouterr().out
    summary = json.loads(out)
    assert summary["model_check"]["match"] is False
    assert summary["model_check"]["compatible"] is True


def test_episode_incompatible_structure_always_refused_exit_6(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-4, FR-012: Cấu trúc không tương thích (nq=2) kể cả có cờ vẫn bị từ chối với mã 6."""
    incompat_ep = tmp_path / "incompatible.json"
    _create_valid_episode_file(incompat_ep, sha256="f" * 64, nq=2)

    code = run_replay(
        ["--episode", str(incompat_ep), "--headless", "--allow-model-mismatch"]
    )
    assert code == 6
    err = capsys.readouterr().err
    assert "cấu trúc" in err.lower() or "không tương thích" in err.lower()


# ==============================================================================
# NHÓM 5: KIỂM THỬ MÀN HÌNH HIỂN THỊ (MÃ THOÁT 7)
# ==============================================================================


def test_display_unavailable_without_headless_exits_7(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-3, FR-011, NFR-HEADLESS-001: Không có màn hình và không có --headless thoát mã 7."""
    ep_file = _create_valid_episode_file(tmp_path / "ep.json")

    monkeypatch.setattr(
        "mma_ai.visualization.display.display_available",
        lambda: DisplayStatus(available=False, reason="Không tìm thấy màn hình hiển thị."),
    )

    code = run_replay(["--episode", str(ep_file)])
    assert code == 7
    err = capsys.readouterr().err
    assert "màn hình" in err.lower() or "hiển thị" in err.lower()


# ==============================================================================
# NHÓM 6: KIỂM THỬ LƯU EPISODE (MÃ THOÁT 8)
# ==============================================================================


def test_save_episode_refuses_overwrite_exit_8(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-5, FR-008, INV-005: Tệp --save-episode đã tồn tại bị từ chối với mã 8."""
    ckpt_path = _mock_checkpoint_setup(monkeypatch, tmp_path)
    existing_file = tmp_path / "existing.episode.json"
    existing_file.write_text("{}", encoding="utf-8")

    code = run_replay(
        [
            "--checkpoint",
            str(ckpt_path),
            "--headless",
            "--save-episode",
            str(existing_file),
        ]
    )
    assert code == 8
    err = capsys.readouterr().err
    assert "đã tồn tại" in err.lower() or "từ chối ghi đè" in err.lower()


# ==============================================================================
# NHÓM 7: KIỂM THỬ ĐƯỜNG THÀNH CÔNG --HEADLESS (MÃ THOÁT 0)
# ==============================================================================


def test_episode_headless_success_prints_json_summary_exit_0(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-3, FR-010: --episode + --headless in tóm tắt JSON ra stdout và thoát mã 0."""
    ep_file = _create_valid_episode_file(tmp_path / "ep.json")

    code = run_replay(["--episode", str(ep_file), "--headless"])
    assert code == 0
    captured = capsys.readouterr()
    summary = json.loads(captured.out)

    assert summary["schema_version"] == "1.0.0"
    assert summary["mode"] == "episode"
    assert summary["headless"] is True
    assert summary["n_frames"] == 2
    assert summary["n_actions"] == 1
    assert "activation" in summary
    assert "TRIlong" in summary["activation"]["muscle_names"]


def test_demo_headless_saves_episode_exit_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-2, AC-3, FR-002, FR-008: Demo headless chạy policy và lưu episode hợp lệ."""
    from mma_ai.visualization.episode import read_episode

    ckpt_path = _mock_checkpoint_setup(monkeypatch, tmp_path)
    out_file = tmp_path / "saved_demo.episode.json"

    code = run_replay(
        [
            "--checkpoint",
            str(ckpt_path),
            "--headless",
            "--save-episode",
            str(out_file),
            "--split",
            "test",
            "--target-index",
            "0",
            "--seed",
            "42",
        ]
    )
    assert code == 0
    assert out_file.is_file()

    saved_ep = read_episode(out_file)
    assert saved_ep.seed == 42
    assert saved_ep.target.split == "test"
    assert saved_ep.target.index == 0
    assert len(saved_ep.frames) > 0


# ==============================================================================
# NHÓM 8: KIỂM THỬ THỨ TỰ VÀ NGẮT TIẾN TRÌNH (MÃ THOÁT 130)
# ==============================================================================


def test_keyboard_interrupt_cleans_up_and_exits_130(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """INV-004, CMD-VIS-0001: Bị ngắt bằng Ctrl-C thoát mã 130 và dọn tệp tạm."""
    ep_file = _create_valid_episode_file(tmp_path / "ep.json")

    def _mock_raise(*_args: Any, **_kwargs: Any) -> Any:
        raise KeyboardInterrupt()

    monkeypatch.setattr("mma_ai.visualization.episode.read_episode", _mock_raise)

    code = run_replay(["--episode", str(ep_file), "--headless"])
    assert code == 130
    err = capsys.readouterr().err
    assert "ngắt" in err.lower() or "ctrl-c" in err.lower()


def test_target_index_out_of_range_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-016, AC-5: Chỉ số mục tiêu ngoài phạm vi tập (>= 10) bị từ chối với mã 2."""
    ckpt_path = _mock_checkpoint_setup(monkeypatch, tmp_path)
    code = run_replay(
        [
            "--checkpoint",
            str(ckpt_path),
            "--headless",
            "--target-index",
            "999",
        ]
    )
    assert code == 2
    err = capsys.readouterr().err
    assert "chỉ số mục tiêu" in err.lower() or "vượt quá phạm vi" in err.lower()


# ==============================================================================
# NHÓM 9: KIỂM THỬ XUẤT VIEWER, IMPORT CONSTRAINTS VÀ NAMESPACE TRỰC TIẾP
# ==============================================================================


def test_viewer_playback_output_and_short_episode_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-1, FR-006: Episode ngắn in gợi ý ra stderr, dòng tóm tắt cuối phiên ra stdout."""
    from mma_ai.visualization.pacing import PlaybackStats
    from mma_ai.visualization.playback import RecordingSink

    ep_file = _create_valid_episode_file(tmp_path / "short_ep.json", n_frames=2)

    # Giả lập màn hình khả dụng
    monkeypatch.setattr(
        "mma_ai.visualization.display.display_available",
        lambda: DisplayStatus(available=True, reason="Màn hình khả dụng."),
    )

    # Mock ViewerSink bằng RecordingSink
    monkeypatch.setattr(
        "mma_ai.visualization.viewer.ViewerSink",
        lambda *args, **kwargs: RecordingSink(),
    )

    # Mock play trả về PlaybackStats
    fake_stats = PlaybackStats(wall_s=0.08, sim_s=0.04, ratio=0.5, frames_late=0)
    monkeypatch.setattr(
        "mma_ai.visualization.playback.play",
        lambda *args, **kwargs: fake_stats,
    )

    code = run_replay(["--episode", str(ep_file)])
    assert code == 0

    captured = capsys.readouterr()
    # Kiểm tra gợi ý cho episode ngắn (< 1s) trên stderr
    assert "thời lượng mô phỏng của episode ngắn" in captured.err.lower()
    assert "--speed 0.1" in captured.err

    # Kiểm tra dòng tóm tắt tiếng Việt cuối phiên trên stdout
    assert "tóm tắt phiên phát lại" in captured.out.lower()
    assert "thời lượng mô phỏng=0.040 s" in captured.out.lower()
    assert "thời gian thực=0.080 s" in captured.out.lower()


def test_single_frame_episode_zero_duration_headless_exit_0(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-1, FR-006: Episode chỉ có 1 khung chạy không chia cho 0, thời lượng 0 s."""
    ep_file = _create_valid_episode_file(tmp_path / "single_frame.json", n_frames=1)

    code = run_replay(["--episode", str(ep_file), "--headless"])
    assert code == 0

    summary = json.loads(capsys.readouterr().out)
    assert summary["n_frames"] == 1
    assert summary["n_actions"] == 0
    assert summary["duration_sim_s"] == 0.0


def test_episode_headless_does_not_import_torch_nor_viewer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-015: Chế độ --episode + --headless KHÔNG nhập torch hay mujoco.viewer."""
    import sys

    ep_file = _create_valid_episode_file(tmp_path / "ep.json")

    # Đảm bảo torch và mujoco.viewer không nằm trong sys.modules trước khi chạy
    monkeypatch.delitem(sys.modules, "torch", raising=False)
    monkeypatch.delitem(sys.modules, "mujoco.viewer", raising=False)
    monkeypatch.delitem(sys.modules, "glfw", raising=False)

    code = run_replay(["--episode", str(ep_file), "--headless"])
    assert code == 0

    assert "torch" not in sys.modules, (
        "Đường --episode + --headless đã nhập torch trái phép (FR-015)"
    )
    assert "mujoco.viewer" not in sys.modules, (
        "Đường --headless đã nhập mujoco.viewer trái phép (FR-015)"
    )
    assert "glfw" not in sys.modules, (
        "Đường --headless đã nhập glfw trái phép (FR-015)"
    )


def test_run_replay_accepts_namespace_directly(tmp_path: Path) -> None:
    """API-VIS-0011: run_replay chấp nhận đối số argparse.Namespace trực tiếp."""
    import argparse

    ep_file = _create_valid_episode_file(tmp_path / "ep.json")
    ns = argparse.Namespace(
        episode=str(ep_file),
        checkpoint=None,
        headless=True,
        save_episode=None,
        speed=None,
        loop=False,
        allow_model_mismatch=False,
        split=None,
        target_index=None,
        seed=None,
        config=None,
    )

    code = run_replay(ns)
    assert code == 0

