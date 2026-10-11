"""Mô-đun điều phối nhịp thời gian thực và nội suy khung hình (pacing).

Cung cấp các thành phần theo hợp đồng API:
- FR-006: Duy trì tốc độ thời gian thực (real-time speed), hệ số tốc độ, lặp và báo cáo tỷ lệ.
- NFR-PERF-001: Tỷ lệ thời gian phát / thời gian mô phỏng trong khoảng [0,95 ; 1,05].
- API-VIS-0007: Bộ lập nhịp Pacer và hàm nội suy khung hình frame_at.
"""

from __future__ import annotations

import bisect
import inspect
import time
from dataclasses import dataclass
from typing import Any, Callable

from mma_ai.visualization.episode import Episode, Frame


@dataclass(frozen=True)
class PlaybackStats:
    """Thống kê chi tiết phiên phát lại (playback statistics).

    Lưu giữ các chỉ số đo đạc thời gian thực và độ trễ nhịp khung hình:
    - wall_s: Thời gian thực tế trôi qua (wall-clock seconds).
    - sim_s: Thời lượng mô phỏng (simulation seconds).
    - ratio: Tỷ lệ thời gian phát / thời gian mô phỏng đã chia tốc độ (null khi sim_s = 0).
    - frames_late: Số lượng khung hình bị trễ nhịp (late frames).
    - speed: Hệ số tốc độ phát lại (playback speed factor).
    - frames_shown: Tổng số khung hình đã hiển thị.
    - max_late_ms: Độ trễ tối đa ghi nhận được tính bằng mili-giây (milliseconds).
    """

    wall_s: float
    sim_s: float
    ratio: float | None
    frames_late: int
    speed: float = 1.0
    frames_shown: int = 0
    max_late_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Xuất thông tin thống kê thành từ điển tương thích khuôn tóm tắt."""
        return {
            "speed": self.speed,
            "frames_shown": self.frames_shown,
            "wall_s": self.wall_s,
            "sim_s": self.sim_s,
            "ratio": self.ratio,
            "frames_late": self.frames_late,
        }


def _invoke_on_tick(
    on_tick: Callable[..., Any],
    t_sim_s: float,
    frame_idx: int,
) -> bool:
    """Gọi hàm gọi lại (callback) on_tick với số lượng tham số tương thích (1 hoặc 2)."""
    try:
        sig = inspect.signature(on_tick)
        num_pos = sum(
            1
            for p in sig.parameters.values()
            if p.kind
            in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        )
        if num_pos >= 2:
            result = on_tick(t_sim_s, frame_idx)
        else:
            result = on_tick(t_sim_s)
    except (ValueError, TypeError):
        try:
            result = on_tick(t_sim_s)
        except TypeError:
            result = on_tick(t_sim_s, frame_idx)

    if result is False:
        return False
    return True


class Pacer:
    """Bộ điều phối nhịp thời gian thực (real-time pacer).

    Hỗ trợ đồng hồ tiêm vào (clock injection) để đảm bảo tính tất định khi kiểm thử:
    - clock: Hàm đọc thời gian đơn điệu, mặc định time.perf_counter.
    - sleep: Hàm tạm dừng thực thi, mặc định time.sleep.
    """

    def __init__(
        self,
        clock: Callable[[], float] = time.perf_counter,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._clock = clock
        self._sleep = sleep

    def run(
        self,
        duration_sim_s: float,
        speed: float = 1.0,
        display_hz: float = 60.0,
        on_tick: Callable[..., Any] | None = None,
        loop: bool = False,
    ) -> PlaybackStats:
        """Thực thi vòng lặp phát lại theo nhịp thời gian thực (real-time pacing)."""
        if duration_sim_s < 0:
            raise ValueError(
                f"Thời lượng mô phỏng (duration_sim_s) không được âm: {duration_sim_s}"
            )
        if speed <= 0:
            raise ValueError(f"Hệ số tốc độ (speed) phải lớn hơn 0: {speed}")
        if display_hz <= 0:
            raise ValueError(f"Tần số hiển thị (display_hz) phải lớn hơn 0: {display_hz}")

        start_wall = self._clock()

        if duration_sim_s == 0.0:
            if on_tick is not None:
                _invoke_on_tick(on_tick, 0.0, 0)
            end_wall = self._clock()
            wall_s = max(0.0, end_wall - start_wall)
            return PlaybackStats(
                wall_s=wall_s,
                sim_s=0.0,
                ratio=None,
                frames_late=0,
                speed=speed,
                frames_shown=1,
                max_late_ms=0.0,
            )

        dt_display = 1.0 / display_hz
        dt_sim = dt_display * speed

        frames_shown = 0
        frames_late = 0
        max_late_ms = 0.0
        total_sim_s = 0.0
        loop_idx = 0
        stopped_early = False

        while True:
            iteration_start_wall = start_wall + loop_idx * (
                (duration_sim_s / speed) + dt_display
            )
            k = 0

            while True:
                t_sim = k * dt_sim
                is_final_step = False
                if t_sim >= duration_sim_s:
                    t_sim = duration_sim_s
                    is_final_step = True

                target_time = iteration_start_wall + (t_sim / speed)
                now = self._clock()
                delay = now - target_time

                if delay > 1e-6:
                    frames_late += 1
                    max_late_ms = max(max_late_ms, delay * 1000.0)
                elif target_time > now:
                    self._sleep(target_time - now)

                if on_tick is not None:
                    cont = _invoke_on_tick(on_tick, t_sim, frames_shown)
                    if not cont:
                        frames_shown += 1
                        total_sim_s += t_sim
                        stopped_early = True
                        break

                frames_shown += 1

                if is_final_step:
                    total_sim_s += duration_sim_s
                    break

                k += 1

            if stopped_early or not loop:
                break

            loop_idx += 1

        end_wall = self._clock()
        wall_s = max(0.0, end_wall - start_wall)
        ratio = wall_s / (total_sim_s / speed) if total_sim_s > 0 else None

        return PlaybackStats(
            wall_s=wall_s,
            sim_s=total_sim_s,
            ratio=ratio,
            frames_late=frames_late,
            speed=speed,
            frames_shown=frames_shown,
            max_late_ms=max_late_ms,
        )


def frame_at(episode: Episode, t_sim_s: float) -> Frame:
    """Nội suy tuyến tính trạng thái khung hình tại thời điểm mô phỏng t_sim_s."""
    if not episode.frames:
        raise ValueError("Bản ghi episode không chứa khung hình nào")

    if len(episode.frames) == 1:
        return episode.frames[0]

    if t_sim_s <= episode.frames[0].t_s:
        return episode.frames[0]

    if t_sim_s >= episode.frames[-1].t_s:
        return episode.frames[-1]

    times = [f.t_s for f in episode.frames]
    idx = bisect.bisect_right(times, t_sim_s)
    f0 = episode.frames[idx - 1]
    f1 = episode.frames[idx]

    dt = f1.t_s - f0.t_s
    if dt <= 0:
        return f0

    alpha = (t_sim_s - f0.t_s) / dt
    if alpha <= 0.0:
        return f0
    if alpha >= 1.0:
        return f1

    qpos = [f0.qpos[j] + alpha * (f1.qpos[j] - f0.qpos[j]) for j in range(len(f0.qpos))]

    activation = [
        max(0.0, min(1.0, f0.activation[j] + alpha * (f1.activation[j] - f0.activation[j])))
        for j in range(len(f0.activation))
    ]

    qvel = [f0.qvel[j] + alpha * (f1.qvel[j] - f0.qvel[j]) for j in range(len(f0.qvel))]

    fingertip = (
        f0.fingertip_position_m[0]
        + alpha * (f1.fingertip_position_m[0] - f0.fingertip_position_m[0]),
        f0.fingertip_position_m[1]
        + alpha * (f1.fingertip_position_m[1] - f0.fingertip_position_m[1]),
        f0.fingertip_position_m[2]
        + alpha * (f1.fingertip_position_m[2] - f0.fingertip_position_m[2]),
    )

    distance_m = f0.distance_m + alpha * (f1.distance_m - f0.distance_m)
    reward = f0.reward + alpha * (f1.reward - f0.reward)

    excitation: list[float] | None = None
    if f0.excitation is not None and f1.excitation is not None:
        excitation = [
            max(0.0, min(1.0, f0.excitation[j] + alpha * (f1.excitation[j] - f0.excitation[j])))
            for j in range(len(f0.excitation))
        ]
    elif f0.excitation is not None:
        excitation = list(f0.excitation)
    elif f1.excitation is not None:
        excitation = list(f1.excitation)

    return Frame(
        t_s=float(t_sim_s),
        qpos=qpos,
        qvel=qvel,
        activation=activation,
        excitation=excitation,
        fingertip_position_m=fingertip,
        distance_m=float(distance_m),
        reward=float(reward),
    )
