"""Bộ kiểm thử đơn vị cho mô-đun phát lại mô phỏng (playback).

Truy vết các yêu cầu kỹ thuật và hợp đồng API:
- FR-001: Phát lại chuỗi khung hình theo đúng thứ tự thời gian đã ghi (recorded order).
- FR-004: Điểm đánh dấu mục tiêu (target marker) hiển thị đúng vị trí đã ghi.
- FR-005: Hiển thị 6 giá trị kích hoạt cơ (muscle activation) tương ứng với từng khung hình.
- FR-006: Điều phối nhịp thời gian thực qua Pacer, hỗ trợ chế độ lặp (loop) và giữ khung cuối.
- FR-015: Không nhập mô-đun mujoco.viewer trong quá trình phát lại độc lập.
- INV-001: Cảnh báo lệch mô hình (model mismatch warning) được duy trì liên tục trên HUD nếu có.
- INV-006: Dữ liệu kích hoạt cơ trong khung hình được bảo toàn nguyên vẹn, chỉ làm tròn trên HUD.
- API-VIS-0009: Giao diện FrameSink và hàm điều phối phát lại play().
- AC-1: Kiểm tra phát lại 3D đúng thứ tự khung hình, vị trí mục tiêu và thông số HUD.
"""

from __future__ import annotations

import sys

import pytest

from mma_ai.visualization.episode import (
    Episode,
    Frame,
    ModelRecord,
    OutcomeRecord,
    TargetRecord,
    TimingRecord,
)
from mma_ai.visualization.pacing import Pacer
from mma_ai.visualization.playback import FrameSink, RecordingSink, play
from mma_ai.visualization.replay_config import (
    DemoConfig,
    HudConfig,
    PlaybackConfig,
    ReplayConfig,
    TargetMarkerConfig,
)


class FakeClock:
    """Đồng hồ giả lập (fake clock) phục vụ kiểm thử tất định."""

    def __init__(self, start_time: float = 0.0) -> None:
        self.current_time = start_time
        self.sleep_calls: list[float] = []

    def clock(self) -> float:
        """Đọc thời gian hiện tại."""
        return self.current_time

    def sleep(self, seconds: float) -> None:
        """Tạm dừng và tăng thời gian giả lập."""
        self.sleep_calls.append(seconds)
        self.current_time += seconds


def _create_sample_config(
    *,
    speed: float = 1.0,
    loop: bool = False,
    display_hz: int = 25,
    hold_after_end_s: float | None = 0.0,
    decimals: int = 3,
    bar_width: int = 10,
) -> ReplayConfig:
    """Tạo cấu hình phát lại phục vụ kiểm thử đơn vị."""
    return ReplayConfig(
        playback=PlaybackConfig(
            speed=speed,
            loop=loop,
            display_hz=display_hz,
            hold_after_end_s=hold_after_end_s,
        ),
        demo=DemoConfig(
            split="test",
            target_index=0,
            seed=42,
        ),
        hud=HudConfig(
            decimals=decimals,
            bar_width=bar_width,
        ),
        target_marker=TargetMarkerConfig(
            radius_m=0.02,
            rgba=(1.0, 0.2, 0.2, 0.6),
        ),
    )


def _create_sample_episode(
    frames: list[Frame],
    *,
    muscle_names: list[str] | None = None,
) -> Episode:
    """Tạo một đối tượng Episode mẫu với danh sách khung hình xác định."""
    names = muscle_names or ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"]
    return Episode(
        schema_version="1.0.0",
        created_utc="2026-10-09T10:00:00Z",
        seed=123,
        model=ModelRecord(
            sha256="384dcb555561287f000000000000000000000000000000000000000000000000",
            source="myo_sim/elbow/myoelbow_1dof6muscles.xml",
            muscle_names=names,
            nq=1,
            nv=1,
        ),
        target=TargetRecord(
            position_m=(-0.21, -0.106, 1.12),
            split="test",
            index=0,
            tolerance_m=0.02,
        ),
        source=None,
        library_versions={"mujoco": "3.15.0"},
        timing=TimingRecord(action_dt_s=0.04, physics_timestep_s=0.0025),
        outcome=OutcomeRecord(
            terminated=True,
            truncated=False,
            end_reason="reached",
            reached=True,
            n_actions=max(0, len(frames) - 1),
            final_distance_m=0.01,
        ),
        frames=frames,
    )


def test_frames_in_recorded_order() -> None:
    """Kiểm tra các khung hình được đưa vào sink theo đúng thứ tự đã ghi (FR-001, AC-1)."""
    f0 = Frame(
        t_s=0.0,
        qpos=[0.0],
        qvel=[0.0],
        activation=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        excitation=None,
        fingertip_position_m=(-0.1, -0.1, 1.0),
        distance_m=0.15,
        reward=0.0,
    )
    f1 = Frame(
        t_s=0.04,
        qpos=[0.2],
        qvel=[0.5],
        activation=[0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
        excitation=[0.3] * 6,
        fingertip_position_m=(-0.15, -0.1, 1.05),
        distance_m=0.08,
        reward=1.0,
    )
    f2 = Frame(
        t_s=0.08,
        qpos=[0.4],
        qvel=[0.8],
        activation=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        excitation=[0.4] * 6,
        fingertip_position_m=(-0.21, -0.106, 1.12),
        distance_m=0.01,
        reward=5.0,
    )
    ep = _create_sample_episode([f0, f1, f2])

    fake = FakeClock()
    pacer = Pacer(clock=fake.clock, sleep=fake.sleep)
    sink = RecordingSink()
    cfg = _create_sample_config(speed=1.0, display_hz=25, hold_after_end_s=0.0)

    stats = play(ep, cfg, sink, pacer)

    assert len(sink.frames) == 3
    times = [f.t_s for f in sink.frames]
    assert times == [pytest.approx(0.0), pytest.approx(0.04), pytest.approx(0.08)]
    assert sink.frames[0].qpos == [pytest.approx(0.0)]
    assert sink.frames[1].qpos == [pytest.approx(0.2)]
    assert sink.frames[2].qpos == [pytest.approx(0.4)]
    assert stats.frames_shown == 3


def test_target_marker_at_recorded_position() -> None:
    """Kiểm tra điểm đánh dấu mục tiêu được truyền đúng vị trí đã ghi (FR-004, AC-1)."""
    f0 = Frame(
        t_s=0.0,
        qpos=[0.0],
        qvel=[0.0],
        activation=[0.1] * 6,
        excitation=None,
        fingertip_position_m=(0.0, 0.0, 1.0),
        distance_m=0.2,
        reward=0.0,
    )
    ep = _create_sample_episode([f0])

    fake = FakeClock()
    pacer = Pacer(clock=fake.clock, sleep=fake.sleep)
    sink = RecordingSink()
    assert isinstance(sink, FrameSink)
    cfg = _create_sample_config(hold_after_end_s=0.0)

    play(ep, cfg, sink, pacer)

    assert sink.target_position_m == ep.target.position_m
    assert sink.target_position_m == (-0.21, -0.106, 1.12)


def test_hud_shows_recorded_activation_each_frame() -> None:
    """Kiểm tra HUD hiển thị đúng 6 giá trị kích hoạt cơ của từng khung hình (FR-005, AC-1)."""
    f0 = Frame(
        t_s=0.0,
        qpos=[0.0],
        qvel=[0.0],
        activation=[0.111, 0.222, 0.333, 0.444, 0.555, 0.666],
        excitation=None,
        fingertip_position_m=(0.0, 0.0, 1.0),
        distance_m=0.2,
        reward=0.0,
    )
    f1 = Frame(
        t_s=0.04,
        qpos=[0.1],
        qvel=[0.2],
        activation=[0.999, 0.888, 0.777, 0.666, 0.555, 0.444],
        excitation=[0.5] * 6,
        fingertip_position_m=(0.1, 0.1, 1.0),
        distance_m=0.1,
        reward=1.0,
    )
    ep = _create_sample_episode([f0, f1])

    fake = FakeClock()
    pacer = Pacer(clock=fake.clock, sleep=fake.sleep)
    sink = RecordingSink()
    cfg = _create_sample_config(display_hz=25, hold_after_end_s=0.0, decimals=3)

    play(ep, cfg, sink, pacer)

    assert len(sink.hud_records) == 2

    hud0 = sink.hud_records[0]
    assert any("TRIlong: 0.111" in line for line in hud0)
    assert any("BRA: 0.666" in line for line in hud0)

    hud1 = sink.hud_records[1]
    assert any("TRIlong: 0.999" in line for line in hud1)
    assert any("BRA: 0.444" in line for line in hud1)


def test_hud_names_match_muscle_names() -> None:
    """Kiểm tra tên trên HUD khớp chính xác muscle_names của mô hình (FR-005, INV-006)."""
    custom_muscles = ["M1_tri", "M2_tri", "M3_tri", "M4_bic", "M5_bic", "M6_bra"]
    f0 = Frame(
        t_s=0.0,
        qpos=[0.0],
        qvel=[0.0],
        activation=[0.2] * 6,
        excitation=None,
        fingertip_position_m=(0.0, 0.0, 1.0),
        distance_m=0.2,
        reward=0.0,
    )
    ep = _create_sample_episode([f0], muscle_names=custom_muscles)

    fake = FakeClock()
    pacer = Pacer(clock=fake.clock, sleep=fake.sleep)
    sink = RecordingSink()
    cfg = _create_sample_config(hold_after_end_s=0.0)

    play(ep, cfg, sink, pacer)

    hud_lines_shown = sink.hud_records[0]
    for muscle in custom_muscles:
        assert any(line.startswith(f"{muscle}:") for line in hud_lines_shown)


def test_play_stops_when_sink_is_closed() -> None:
    """Kiểm tra phiên phát dừng ngay khi sink.is_open() trả về False (FR-001, FR-006)."""
    frames = [
        Frame(
            t_s=i * 0.04,
            qpos=[i * 0.1],
            qvel=[0.0],
            activation=[0.1] * 6,
            excitation=None,
            fingertip_position_m=(0.0, 0.0, 1.0),
            distance_m=0.2,
            reward=0.0,
        )
        for i in range(10)
    ]
    ep = _create_sample_episode(frames)

    fake = FakeClock()
    pacer = Pacer(clock=fake.clock, sleep=fake.sleep)
    sink = RecordingSink(max_frames=3)
    cfg = _create_sample_config(display_hz=25, hold_after_end_s=0.0)

    stats = play(ep, cfg, sink, pacer)

    assert len(sink.frames) == 3
    assert stats.frames_shown == 3


def test_play_loop_repeats_until_sink_closed() -> None:
    """Kiểm tra chế độ lặp loop=True lặp tuần hoàn đến khi sink đóng (FR-006, AC-1)."""
    f0 = Frame(
        t_s=0.0,
        qpos=[0.0],
        qvel=[0.0],
        activation=[0.1] * 6,
        excitation=None,
        fingertip_position_m=(0.0, 0.0, 1.0),
        distance_m=0.2,
        reward=0.0,
    )
    f1 = Frame(
        t_s=0.04,
        qpos=[0.5],
        qvel=[0.0],
        activation=[0.5] * 6,
        excitation=None,
        fingertip_position_m=(0.0, 0.0, 1.0),
        distance_m=0.2,
        reward=0.0,
    )
    ep = _create_sample_episode([f0, f1])

    fake = FakeClock()
    pacer = Pacer(clock=fake.clock, sleep=fake.sleep)
    sink = RecordingSink(max_frames=5)
    cfg = _create_sample_config(display_hz=25, loop=True, hold_after_end_s=0.0)

    stats = play(ep, cfg, sink, pacer)

    assert len(sink.frames) == 5
    assert stats.frames_shown == 5


def test_play_single_frame_episode_no_zero_division() -> None:
    """Kiểm tra episode 1 khung phát thành công và không bị chia cho 0 (FR-006, AC-1)."""
    f0 = Frame(
        t_s=0.0,
        qpos=[0.15],
        qvel=[0.0],
        activation=[0.3] * 6,
        excitation=None,
        fingertip_position_m=(0.0, 0.0, 1.0),
        distance_m=0.2,
        reward=0.0,
    )
    ep = _create_sample_episode([f0])

    fake = FakeClock()
    pacer = Pacer(clock=fake.clock, sleep=fake.sleep)
    sink = RecordingSink()
    cfg = _create_sample_config(hold_after_end_s=0.0)

    stats = play(ep, cfg, sink, pacer)

    assert len(sink.frames) == 1
    assert stats.sim_s == 0.0
    assert stats.ratio is None
    assert stats.frames_shown == 1


def test_play_model_mismatch_warning_persistent() -> None:
    """Kiểm tra cảnh báo lệch mô hình luôn hiện liên tục trên HUD ở mọi khung (INV-001)."""
    f0 = Frame(
        t_s=0.0,
        qpos=[0.0],
        qvel=[0.0],
        activation=[0.1] * 6,
        excitation=None,
        fingertip_position_m=(0.0, 0.0, 1.0),
        distance_m=0.2,
        reward=0.0,
    )
    f1 = Frame(
        t_s=0.04,
        qpos=[0.1],
        qvel=[0.0],
        activation=[0.2] * 6,
        excitation=None,
        fingertip_position_m=(0.0, 0.0, 1.0),
        distance_m=0.2,
        reward=0.0,
    )
    ep = _create_sample_episode([f0, f1])

    fake = FakeClock()
    pacer = Pacer(clock=fake.clock, sleep=fake.sleep)
    sink = RecordingSink()
    cfg = _create_sample_config(display_hz=25, hold_after_end_s=0.0)

    play(ep, cfg, sink, pacer, warning="MÔ HÌNH LỆCH")

    assert len(sink.hud_records) == 2
    for hud_lines_list in sink.hud_records:
        assert "MÔ HÌNH LỆCH" in hud_lines_list


def test_play_rounding_only_in_display() -> None:
    """Kiểm tra làm tròn chỉ ở hiển thị HUD, dữ liệu trong Frame không bị làm tròn (INV-006)."""
    precise_act = [0.123456, 0.234567, 0.345678, 0.456789, 0.567890, 0.678901]
    f0 = Frame(
        t_s=0.0,
        qpos=[0.0],
        qvel=[0.0],
        activation=precise_act,
        excitation=None,
        fingertip_position_m=(0.0, 0.0, 1.0),
        distance_m=0.2,
        reward=0.0,
    )
    ep = _create_sample_episode([f0])

    fake = FakeClock()
    pacer = Pacer(clock=fake.clock, sleep=fake.sleep)
    sink = RecordingSink()
    cfg = _create_sample_config(hold_after_end_s=0.0, decimals=2)

    play(ep, cfg, sink, pacer)

    shown_frame = sink.frames[0]
    assert shown_frame.activation == precise_act

    hud_lines_shown = sink.hud_records[0]
    assert any("TRIlong: 0.12" in line for line in hud_lines_shown)


def test_play_empty_episode_raises_value_error() -> None:
    """Kiểm tra play từ chối episode không có khung hình nào và ném lỗi tiếng Việt (FR-018)."""
    ep = _create_sample_episode([])
    cfg = _create_sample_config()
    sink = RecordingSink()

    with pytest.raises(ValueError, match="khung hình"):
        play(ep, cfg, sink)


def test_no_mujoco_viewer_import() -> None:
    """Kiểm tra mma_ai.visualization.playback tuyệt đối không nhập mujoco.viewer (FR-015)."""
    import mma_ai.visualization.playback as pb

    assert "mujoco.viewer" not in sys.modules or (
        "mujoco.viewer" not in getattr(pb, "__dict__", {})
    )
    # Kiểm tra mã nguồn tệp không chứa lệnh nhập mujoco.viewer
    with open(pb.__file__, "r", encoding="utf-8") as f:
        content = f.read()
    assert "import mujoco.viewer" not in content
    assert "from mujoco import viewer" not in content


def test_hold_final_frame_until_sink_closed() -> None:
    """Kiểm tra khung cuối được giữ cho đến khi sink đóng hoặc hết thời gian chờ (FR-006, AC-1)."""
    f0 = Frame(
        t_s=0.0,
        qpos=[0.0],
        qvel=[0.0],
        activation=[0.1] * 6,
        excitation=None,
        fingertip_position_m=(0.0, 0.0, 1.0),
        distance_m=0.2,
        reward=0.0,
    )
    f1 = Frame(
        t_s=0.04,
        qpos=[0.3],
        qvel=[0.1],
        activation=[0.4] * 6,
        excitation=None,
        fingertip_position_m=(0.1, 0.0, 1.0),
        distance_m=0.1,
        reward=1.0,
    )
    ep = _create_sample_episode([f0, f1])

    fake = FakeClock()
    pacer = Pacer(clock=fake.clock, sleep=fake.sleep)

    class ControlledHoldSink(RecordingSink):
        def __init__(self, hold_limit: int = 3) -> None:
            super().__init__(auto_close_on_hold=False)
            self.hold_count = 0
            self.hold_limit = hold_limit

        def show(self, frame: Frame, hud: list[str]) -> None:
            super().show(frame, hud)
            # Sau khi đã nhận 2 khung phát chính, đếm số lần khung cuối được hiển thị trong pha hold
            if len(self.frames) > 2:
                self.hold_count += 1
                if self.hold_count >= self.hold_limit:
                    self._is_open = False

    sink = ControlledHoldSink(hold_limit=3)
    cfg = _create_sample_config(display_hz=25, hold_after_end_s=None)

    stats = play(ep, cfg, sink, pacer)

    assert stats.frames_shown == 2
    # Tổng số khung gọi show là 2 khung ban đầu + 3 lần giữ khung cuối
    assert len(sink.frames) == 5
    assert sink.frames[-1].t_s == pytest.approx(0.04)
    assert sink.frames[-1].qpos == [pytest.approx(0.3)]

