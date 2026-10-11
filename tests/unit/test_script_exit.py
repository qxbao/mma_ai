"""Kiểm thử đơn vị cho cơ chế thoát tiến trình của CLI phát lại (tests/unit/test_script_exit.py).

Truy vết các yêu cầu kỹ thuật và hợp đồng:
- FR-014: Thoát an toàn không phụ thuộc bước dọn dẹp tài nguyên đồ hoạ (graphics teardown).
- CMD-VIS-0001: Hợp đồng dòng lệnh phát lại mô phỏng và demo 3D.
- CLI-005: Quy tắc thoát tiến trình dòng lệnh qua os._exit khi MuJoCo Viewer đã mở.
- AC-1: Phiên phát lại hoàn thành sạch sẽ, không sập lỗi phân đoạn (segmentation fault).
- AC-5: Xử lý đúng mã thoát (exit code) cho mọi trường hợp tham số và phiên chạy.
- INV-004: Thoát mã lỗi tương ứng khi gặp sự cố, dọn dẹp tài nguyên trước khi thoát.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

from mma_ai.physics.body_model import load_muscle_model
from mma_ai.visualization.cli import main
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
from mma_ai.visualization.pacing import PlaybackStats
from mma_ai.visualization.playback import RecordingSink


def _get_current_model_hash() -> str:
    """Lấy mã băm SHA-256 thực tế của mô hình khuỷu tay myoelbow."""
    return load_muscle_model("myoelbow").info.sha256


def _create_valid_episode_file(
    file_path: Path,
    *,
    sha256: str | None = None,
    nq: int = 1,
    nv: int = 1,
    n_frames: int = 2,
) -> Path:
    """Tạo tệp episode JSON hợp lệ tuân thủ các luật định dạng để phục vụ kiểm thử."""
    names = ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"]
    model_sha = sha256 if sha256 is not None else _get_current_model_hash()
    dt = 0.04

    frames: list[Frame] = []
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


def test_os_exit_only_when_viewer_opened(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-014, CLI-005: os._exit chỉ được gọi khi MuJoCo Viewer thực sự được mở."""
    exit_calls: list[int] = []

    def fake_os_exit(code: int) -> None:
        exit_calls.append(code)

    # Chặn os._exit thông qua monkeypatch để ghi nhận hành vi gọi hàm
    monkeypatch.setattr(os, "_exit", fake_os_exit)

    # 1. Nhánh lỗi tham số dòng lệnh (mã thoát 2) -> Viewer KHÔNG mở -> Không gọi os._exit
    code_invalid_args = main([])
    assert code_invalid_args == 2
    assert len(exit_calls) == 0, (
        "Đường lỗi tham số không mở viewer nhưng lại gọi os._exit trái quy tắc"
    )

    # 2. Nhánh tệp episode không tồn tại (mã thoát 5) -> Viewer KHÔNG mở -> Không gọi os._exit
    code_missing_file = main(["--episode", str(tmp_path / "khong_ton_tai.json")])
    assert code_missing_file == 5
    assert len(exit_calls) == 0, (
        "Đường lỗi tệp không tồn tại không mở viewer nhưng lại gọi os._exit trái quy tắc"
    )

    # 3. Nhánh không màn hình (--headless, mã thoát 0) -> Viewer KHÔNG mở -> Không gọi os._exit
    ep_file = _create_valid_episode_file(tmp_path / "ep_test.json")
    code_headless = main(["--episode", str(ep_file), "--headless"])
    assert code_headless == 0
    assert len(exit_calls) == 0, (
        "Đường --headless không bao giờ mở viewer nhưng lại gọi os._exit trái quy tắc"
    )

    # 4. Nhánh có mở Viewer hiển thị đồ hoạ -> Viewer ĐÃ MỞ -> Bắt buộc gọi os._exit
    monkeypatch.setattr(
        "mma_ai.visualization.display.display_available",
        lambda: DisplayStatus(available=True, reason="Màn hình sẵn sàng."),
    )
    monkeypatch.setattr(
        "mma_ai.visualization.viewer.ViewerSink",
        lambda *args, **kwargs: RecordingSink(),
    )
    monkeypatch.setattr(
        "mma_ai.visualization.playback.play",
        lambda *args, **kwargs: PlaybackStats(wall_s=0.08, sim_s=0.04, ratio=0.5, frames_late=0),
    )

    code_viewer = main(["--episode", str(ep_file)])
    assert code_viewer == 0
    assert len(exit_calls) == 1, (
        "Đường có mở viewer bắt buộc phải gọi os._exit để tránh sập lỗi đồ hoạ (FR-014)"
    )
    assert exit_calls[0] == 0, "Mã thoát gửi vào os._exit phải là 0 khi phiên chạy thành công"


def test_exit_code_is_result_not_teardown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-014, CLI-005, AC-1: Mã thoát vào os._exit là kết quả phiên chạy, không phải teardown."""
    exit_calls: list[int] = []
    flushed_streams: list[str] = []

    def fake_os_exit(code: int) -> None:
        exit_calls.append(code)

    def fake_stdout_flush() -> None:
        flushed_streams.append("stdout")

    def fake_stderr_flush() -> None:
        flushed_streams.append("stderr")

    monkeypatch.setattr(os, "_exit", fake_os_exit)
    monkeypatch.setattr(sys.stdout, "flush", fake_stdout_flush)
    monkeypatch.setattr(sys.stderr, "flush", fake_stderr_flush)

    monkeypatch.setattr(
        "mma_ai.visualization.display.display_available",
        lambda: DisplayStatus(available=True, reason="Màn hình khả dụng."),
    )

    fake_sink = RecordingSink()
    monkeypatch.setattr(
        "mma_ai.visualization.viewer.ViewerSink",
        lambda *args, **kwargs: fake_sink,
    )

    # Trường hợp 1: Phiên chạy thành công (mã kết quả 0)
    monkeypatch.setattr(
        "mma_ai.visualization.playback.play",
        lambda *args, **kwargs: PlaybackStats(wall_s=0.1, sim_s=0.08, ratio=0.8, frames_late=0),
    )

    ep_file = _create_valid_episode_file(tmp_path / "ep_result_0.json")
    code_0 = main(["--episode", str(ep_file)])

    assert code_0 == 0
    assert len(exit_calls) == 1
    assert exit_calls[-1] == 0, (
        "Mã thoát trong os._exit phải bảo toàn chính xác mã kết quả 0 của phiên chạy"
    )
    assert "stdout" in flushed_streams, "stdout phải được xả sạch trước khi gọi os._exit"
    assert "stderr" in flushed_streams, "stderr phải được xả sạch trước khi gọi os._exit"

    # Trường hợp 2: Phiên phát lại gặp lỗi runtime (mã kết quả 1) trong khi viewer đã mở
    exit_calls.clear()
    flushed_streams.clear()

    def raise_runtime_in_play(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Lỗi bất ngờ trong vòng lặp phát lại")

    monkeypatch.setattr("mma_ai.visualization.playback.play", raise_runtime_in_play)

    ep_file_err = _create_valid_episode_file(tmp_path / "ep_result_1.json")
    code_1 = main(["--episode", str(ep_file_err)])

    assert code_1 == 1
    assert len(exit_calls) == 1
    assert exit_calls[-1] == 1, (
        "Mã thoát trong os._exit phải phản ánh mã lỗi 1 của phiên chạy, "
        "không bị che lấp bởi teardown"
    )


def test_cli_reads_sys_argv_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CMD-VIS-0001: Hàm main tự động đọc sys.argv khi tham số argv=None."""
    monkeypatch.setattr(sys, "argv", ["mma_ai.visualization.cli", "--help"])
    exit_code = main(None)
    assert exit_code == 0


def test_cli_handles_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-004: Xử lý ngắt tín hiệu KeyboardInterrupt (Ctrl-C), trả về mã 130."""
    monkeypatch.setattr(
        "mma_ai.visualization.cli.run_replay",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    exit_code = main(["--episode", "any.json", "--headless"])
    assert exit_code == 130


def test_cli_active_sink_closed_before_os_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI-005: Đảm bảo active_sink được gọi close() trước khi os._exit."""
    close_called = False
    exit_called = False

    class DummySink:
        def close(self) -> None:
            nonlocal close_called
            close_called = True

    monkeypatch.setattr("mma_ai.visualization.cli.was_viewer_opened", lambda: True)
    monkeypatch.setattr("mma_ai.visualization.cli.get_active_viewer_sink", lambda: DummySink())
    monkeypatch.setattr("mma_ai.visualization.cli.run_replay", lambda *args, **kwargs: 0)

    def fake_exit(code: int) -> None:
        nonlocal exit_called
        assert close_called is True, "sink.close() phải được gọi trước khi os._exit"
        exit_called = True

    monkeypatch.setattr(os, "_exit", fake_exit)

    main(["--episode", "any.json"])
    assert exit_called is True

