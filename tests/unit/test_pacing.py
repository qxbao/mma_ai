"""Bộ kiểm thử đơn vị cho bộ lập nhịp thời gian thực và nội suy (pacing).

Truy vết các yêu cầu kỹ thuật và hợp đồng API:
- FR-006: Duy trì tốc độ thời gian thực, hệ số tốc độ, lặp và báo cáo tỷ lệ.
- NFR-PERF-001: Ở tốc độ 1.0, tỷ lệ phát / mô phỏng ∈ [0.95 ; 1.05] trên episode 0.2–4.0 s.
- API-VIS-0007: Pacer(clock, sleep), run(...) và frame_at(episode, t_sim_s).
- AC-1: Kiểm tra nhịp phát lại và nội suy mượt mà trong phiên phát lại 3D.
"""

from __future__ import annotations

from typing import Any

import pytest

from mma_ai.visualization.episode import (
    Episode,
    Frame,
    ModelRecord,
    OutcomeRecord,
    TargetRecord,
    TimingRecord,
)
from mma_ai.visualization.pacing import Pacer, PlaybackStats, frame_at


class FakeClock:
    """Đồng hồ giả lập (fake clock) phục vụ kiểm thử tất định (deterministic testing)."""

    def __init__(self, start_time: float = 0.0) -> None:
        self.current_time = start_time
        self.sleep_calls: list[float] = []

    def clock(self) -> float:
        """Đọc thời gian hiện tại của đồng hồ giả lập."""
        return self.current_time

    def sleep(self, seconds: float) -> None:
        """Tạm dừng và dịch chuyển thời gian của đồng hồ giả lập."""
        self.sleep_calls.append(seconds)
        self.current_time += seconds

    def advance(self, seconds: float) -> None:
        """Chủ động đẩy thời gian tiến lên để mô phỏng tải xử lý chậm."""
        self.current_time += seconds


def _make_sample_episode(frames: list[Frame]) -> Episode:
    """Tạo đối tượng Episode tối thiểu phục vụ kiểm thử."""
    return Episode(
        schema_version="1.0.0",
        created_utc="2026-10-09T08:00:00Z",
        seed=42,
        model=ModelRecord(
            sha256="384dcb555561287f000000000000000000000000000000000000000000000000",
            source="myo_sim/elbow/myoelbow_1dof6muscles.xml",
            muscle_names=["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"],
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
            n_actions=len(frames) - 1,
            final_distance_m=0.01,
        ),
        frames=frames,
    )


def test_ratio_within_5pct_at_speed_1() -> None:
    """Kiểm tra tỷ lệ phát / mô phỏng ∈ [0.95 ; 1.05] trên episode 0.2–4.0 s (NFR-PERF-001)."""
    test_durations = [0.2, 0.35, 0.5, 1.0, 2.5, 4.0]

    for duration in test_durations:
        fake = FakeClock()
        pacer = Pacer(clock=fake.clock, sleep=fake.sleep)

        ticks: list[float] = []

        def on_tick(t_sim_s: float) -> None:
            ticks.append(t_sim_s)

        stats = pacer.run(
            duration_sim_s=duration,
            speed=1.0,
            display_hz=60.0,
            on_tick=on_tick,
        )

        assert stats.ratio is not None, f"Tỷ lệ không được None khi thời lượng {duration} s > 0"
        assert 0.95 <= stats.ratio <= 1.05, (
            f"Tỷ lệ {stats.ratio} vi phạm ngưỡng [0.95, 1.05] tại thời lượng {duration} s"
        )
        assert stats.frames_late == 0, f"Không được có trễ tại {duration} s"
        assert stats.sim_s == pytest.approx(duration), f"sim_s không khớp {duration}"
        assert len(ticks) > 0, "on_tick phải được gọi ít nhất 1 lần"
        assert ticks[0] == pytest.approx(0.0), "Khung đầu tiên phải tại t_sim = 0"
        assert ticks[-1] == pytest.approx(duration), f"Khung cuối phải tại t_sim = {duration}"


def test_late_frames_reported_not_dropped() -> None:
    """Kiểm tra khung hình chậm nhịp được đếm và báo cáo, không bị bỏ qua (FR-006)."""
    fake = FakeClock()
    pacer = Pacer(clock=fake.clock, sleep=fake.sleep)

    duration = 0.2
    hz = 60.0
    dt_display = 1.0 / hz

    ticks: list[float] = []

    def slow_on_tick(t_sim_s: float) -> None:
        ticks.append(t_sim_s)
        # Giả lập xử lý đồ họa nặng gây trễ nhịp (vượt quá chu kỳ 16.7 ms của 60 Hz)
        fake.advance(dt_display * 2.5)

    stats = pacer.run(duration_sim_s=duration, speed=1.0, display_hz=hz, on_tick=slow_on_tick)

    # Đảm bảo số lượng khung hình không bị bỏ rơi âm thầm
    assert len(ticks) == stats.frames_shown
    assert stats.frames_late > 0, "Khung hình bị trễ phải được ghi nhận"
    assert stats.max_late_ms > 0, "Độ trễ tối đa phải lớn hơn 0"
    assert stats.ratio is not None and stats.ratio > 1.0, "Tỷ lệ thực tế phải > 1.0 khi chậm"


def test_single_frame_episode_no_zero_division() -> None:
    """Kiểm tra episode chỉ có 1 khung không gặp lỗi chia cho 0 (FR-006, API-VIS-0007)."""
    fake = FakeClock()
    pacer = Pacer(clock=fake.clock, sleep=fake.sleep)

    ticks: list[float] = []

    def on_tick(t_sim_s: float) -> None:
        ticks.append(t_sim_s)

    stats = pacer.run(duration_sim_s=0.0, speed=1.0, display_hz=60.0, on_tick=on_tick)

    assert stats.sim_s == 0.0
    assert stats.ratio is None, "Khi sim_s = 0, tỷ lệ ratio phải là None theo lược đồ"
    assert stats.frames_shown == 1
    assert stats.frames_late == 0
    assert ticks == [0.0]

    # Kiểm tra frame_at với episode chỉ có 1 khung hình duy nhất
    single_frame = Frame(
        t_s=0.0,
        qpos=[0.12],
        qvel=[0.0],
        activation=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        excitation=None,
        fingertip_position_m=(-0.21, -0.106, 1.12),
        distance_m=0.05,
        reward=1.0,
    )
    single_episode = _make_sample_episode([single_frame])
    interpolated = frame_at(single_episode, 0.0)
    assert interpolated == single_frame
    # Yêu cầu mốc thời gian bất kỳ ngoài phạm vi vẫn trả về khung hình duy nhất
    assert frame_at(single_episode, 1.0) == single_frame


def test_loop_repeats_until_sink_closed() -> None:
    """Kiểm tra chế độ lặp phát lại (loop) lặp tuần hoàn tới khi sink đóng (FR-006)."""
    fake = FakeClock()
    pacer = Pacer(clock=fake.clock, sleep=fake.sleep)

    call_count = 0
    max_calls = 25  # Một vòng phát ~ 13 khung; 25 cuộc gọi chứng minh đã lặp chu kỳ 2

    def on_tick_with_sink_close(t_sim_s: float) -> bool:
        nonlocal call_count
        call_count += 1
        if call_count >= max_calls:
            return False  # Giả lập sink đóng cửa sổ
        return True

    stats = pacer.run(
        duration_sim_s=0.2,
        speed=1.0,
        display_hz=60.0,
        on_tick=on_tick_with_sink_close,
        loop=True,
    )

    assert call_count == max_calls
    assert stats.frames_shown == max_calls
    assert stats.wall_s > 0


def test_frame_at_linear_interpolation() -> None:
    """Kiểm tra nội suy tuyến tính qpos và activation (API-VIS-0007, FR-006)."""
    f0 = Frame(
        t_s=0.0,
        qpos=[0.0],
        qvel=[0.0],
        activation=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        excitation=None,
        fingertip_position_m=(0.0, 0.0, 0.0),
        distance_m=0.10,
        reward=0.0,
    )
    f1 = Frame(
        t_s=0.04,
        qpos=[0.4],
        qvel=[1.0],
        activation=[1.0, 0.8, 0.6, 0.4, 0.2, 0.0],
        excitation=[0.5] * 6,
        fingertip_position_m=(0.2, 0.4, 0.6),
        distance_m=0.02,
        reward=2.0,
    )
    ep = _make_sample_episode([f0, f1])

    # Kiểm tra tại điểm chính giữa alpha = 0.5 (t = 0.02 s)
    mid = frame_at(ep, 0.02)
    assert mid.t_s == pytest.approx(0.02)
    assert mid.qpos[0] == pytest.approx(0.2)
    assert mid.activation[0] == pytest.approx(0.5)
    assert mid.activation[1] == pytest.approx(0.5)
    assert mid.activation[2] == pytest.approx(0.5)
    assert mid.fingertip_position_m[0] == pytest.approx(0.1)
    assert mid.distance_m == pytest.approx(0.06)
    assert mid.reward == pytest.approx(1.0)

    # Kiểm tra tại điểm 1/4 khoảng thời gian (alpha = 0.25, t = 0.01 s)
    quarter = frame_at(ep, 0.01)
    assert quarter.t_s == pytest.approx(0.01)
    assert quarter.qpos[0] == pytest.approx(0.1)
    assert quarter.activation[0] == pytest.approx(0.25)


def test_frame_at_boundary_frames_preserved() -> None:
    """Kiểm tra khung hình đầu và cuối được giữ nguyên ở biên hoặc ngoài biên (API-VIS-0007)."""
    f0 = Frame(
        t_s=0.0,
        qpos=[0.1],
        qvel=[0.0],
        activation=[0.1] * 6,
        excitation=None,
        fingertip_position_m=(0.1, 0.2, 0.3),
        distance_m=0.05,
        reward=0.0,
    )
    f1 = Frame(
        t_s=0.1,
        qpos=[0.9],
        qvel=[0.5],
        activation=[0.9] * 6,
        excitation=[0.8] * 6,
        fingertip_position_m=(0.3, 0.4, 0.5),
        distance_m=0.01,
        reward=10.0,
    )
    ep = _make_sample_episode([f0, f1])

    # Thời gian trước mốc đầu tiên
    assert frame_at(ep, -0.05) == f0
    assert frame_at(ep, 0.0) == f0

    # Thời gian sau mốc cuối cùng
    assert frame_at(ep, 0.1) == f1
    assert frame_at(ep, 0.25) == f1


def test_pacer_invalid_parameters_raise() -> None:
    """Kiểm tra Pacer.run từ chối tham số không hợp lệ và ném lỗi tiếng Việt (FR-018)."""
    pacer = Pacer()

    with pytest.raises(ValueError, match="duration_sim_s"):
        pacer.run(duration_sim_s=-1.0)

    with pytest.raises(ValueError, match="speed"):
        pacer.run(duration_sim_s=1.0, speed=0.0)

    with pytest.raises(ValueError, match="speed"):
        pacer.run(duration_sim_s=1.0, speed=-0.5)

    with pytest.raises(ValueError, match="display_hz"):
        pacer.run(duration_sim_s=1.0, display_hz=0.0)


def test_playback_stats_to_dict() -> None:
    """Kiểm tra PlaybackStats.to_dict tương thích khuôn tóm tắt (replay-summary.schema.json)."""
    stats = PlaybackStats(
        wall_s=1.05,
        sim_s=1.0,
        ratio=1.05,
        frames_late=2,
        speed=1.0,
        frames_shown=60,
        max_late_ms=18.5,
    )
    data: dict[str, Any] = stats.to_dict()

    expected_keys = {"speed", "frames_shown", "wall_s", "sim_s", "ratio", "frames_late"}
    assert set(data.keys()) == expected_keys
    assert data["speed"] == 1.0
    assert data["frames_shown"] == 60
    assert data["wall_s"] == 1.05
    assert data["sim_s"] == 1.0
    assert data["ratio"] == 1.05
    assert data["frames_late"] == 2
