"""Mô-đun điều phối vòng phát lại mô phỏng và giao diện bộ nhận khung hình (playback).

Định danh mô-đun: mma_ai.visualization.playback.

Hiện thực các yêu cầu kỹ thuật và hợp đồng API:
- FR-001: Phát lại chuỗi khung hình theo đúng thứ tự thời gian đã ghi (recorded order).
- FR-004: Đảm bảo điểm đánh dấu mục tiêu (target marker) hiển thị đúng vị trí đã ghi.
- FR-005: Hiển thị 6 giá trị kích hoạt cơ (muscle activation) tương ứng với từng khung hình.
- FR-006: Điều phối nhịp thời gian thực qua Pacer, hỗ trợ chế độ lặp (loop) và giữ khung cuối.
- FR-015: Không nhập bộ xem trực quan MuJoCo Viewer trong mô-đun này.
- INV-001: Cảnh báo lệch mô hình (model mismatch warning) được duy trì liên tục trên HUD nếu có.
- INV-006: Dữ liệu kích hoạt cơ trong khung hình được bảo toàn nguyên vẹn, chỉ làm tròn trên HUD.
- API-VIS-0009: Giao diện FrameSink và hàm điều phối phát lại play().
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from mma_ai.visualization.hud import hud_lines
from mma_ai.visualization.pacing import Pacer, PlaybackStats, frame_at

if TYPE_CHECKING:
    from mma_ai.visualization.episode import Episode, Frame
    from mma_ai.visualization.replay_config import ReplayConfig


@runtime_checkable
class FrameSink(Protocol):
    """Giao diện trừu tượng cho thiết bị nhận và hiển thị khung hình (frame sink)."""

    def show(self, frame: Frame, hud: list[str]) -> None:
        """Hiển thị một khung hình và các dòng thông số HUD tương ứng."""
        ...

    def is_open(self) -> bool:
        """Kiểm tra thiết bị nhận khung hình có đang mở hay không."""
        ...

    def close(self) -> None:
        """Đóng thiết bị nhận khung hình và giải phóng tài nguyên."""
        ...


class RecordingSink:
    """Bộ nhận khung hình phục vụ kiểm thử và ghi nhận dữ liệu (recording sink)."""

    def __init__(
        self,
        *,
        max_frames: int | None = None,
        auto_close_on_hold: bool = True,
    ) -> None:
        self.frames: list[Frame] = []
        self.hud_records: list[list[str]] = []
        self.target_position_m: tuple[float, float, float] | None = None
        self.max_frames = max_frames
        self.auto_close_on_hold = auto_close_on_hold
        self._is_open = True
        self.closed = False

    def set_target(self, position_m: tuple[float, float, float]) -> None:
        """Ghi nhận vị trí điểm đánh dấu mục tiêu."""
        self.target_position_m = position_m

    def show(self, frame: Frame, hud: list[str]) -> None:
        """Ghi nhận khung hình và các dòng HUD."""
        if not self._is_open:
            return
        self.frames.append(frame)
        self.hud_records.append(list(hud))
        if self.max_frames is not None and len(self.frames) >= self.max_frames:
            self._is_open = False

    def is_open(self) -> bool:
        """Kiểm tra trạng thái mở."""
        return self._is_open

    def close(self) -> None:
        """Đóng sink."""
        self._is_open = False
        self.closed = True


def play(
    episode: Episode,
    cfg: ReplayConfig,
    sink: FrameSink,
    pacer: Pacer | None = None,
    *,
    warning: str | bool | None = None,
) -> PlaybackStats:
    """Điều phối phát lại một episode qua bộ nhận khung hình sink theo nhịp pacer (API-VIS-0009).

    Duy trì các bất biến và hợp đồng kỹ thuật:
    - FR-001: Duyệt qua các khung hình theo đúng trình tự thời gian đã ghi.
    - FR-004: Thiết lập vị trí điểm đánh dấu mục tiêu đúng theo episode.
    - FR-005: Chuyển giao 6 giá trị kích hoạt cơ của từng khung hình vào HUD.
    - FR-006: Điều phối nhịp thời gian thực qua Pacer, hỗ trợ lặp và giữ khung cuối.
    - INV-001: Hiển thị cảnh báo lệch mô hình liên tục trên HUD nếu có.
    - INV-006: Dữ liệu số học gốc trong Frame không bị làm tròn.

    Args:
        episode: Bản ghi episode hoàn chỉnh cần phát lại.
        cfg: Cấu hình phát lại (ReplayConfig).
        sink: Thiết bị nhận khung hình (FrameSink).
        pacer: Bộ lập nhịp thời gian thực (tuỳ chọn, mặc định Pacer()).
        warning: Cảnh báo lệch mô hình hiển thị trên HUD (tuỳ chọn).

    Returns:
        PlaybackStats chứa thống kê đo đạc thời gian thực của phiên phát lại.

    Raises:
        ValueError: Khi episode không chứa khung hình nào hoặc sink là None.
    """
    if not episode.frames:
        raise ValueError("Bản ghi episode không chứa khung hình nào để phát lại.")

    if sink is None:
        raise ValueError("Thiết bị nhận khung hình (FrameSink) không được là None.")

    # Chuyển giao vị trí mục tiêu cho sink nếu sink hỗ trợ thiết lập mục tiêu
    target_pos = episode.target.position_m
    if hasattr(sink, "set_target"):
        sink.set_target(target_pos)
    elif hasattr(sink, "set_target_marker"):
        sink.set_target_marker(target_pos)
    elif hasattr(sink, "set_target_position"):
        sink.set_target_position(target_pos)

    # Nếu sink đã bị đóng ngay từ đầu, kết thúc sớm phiên phát
    if not sink.is_open():
        return PlaybackStats(
            wall_s=0.0,
            sim_s=0.0,
            ratio=None,
            frames_late=0,
            speed=float(cfg.playback.speed),
            frames_shown=0,
            max_late_ms=0.0,
        )

    pacer_instance = pacer if pacer is not None else Pacer()
    speed = float(cfg.playback.speed)
    display_hz = float(cfg.playback.display_hz)
    loop = bool(cfg.playback.loop)
    muscle_names = episode.model.muscle_names

    t_start = episode.frames[0].t_s
    t_end = episode.frames[-1].t_s
    duration_sim_s = max(0.0, t_end - t_start)

    def on_tick(t_sim_s: float, frame_idx: int) -> bool:
        if not sink.is_open():
            return False

        t_current = t_start + t_sim_s
        frame = frame_at(episode, t_current)
        hud = hud_lines(frame.activation, muscle_names, cfg, warning=warning)

        sink.show(frame, hud)

        if not sink.is_open():
            return False
        return True

    stats = pacer_instance.run(
        duration_sim_s=duration_sim_s,
        speed=speed,
        display_hz=display_hz,
        on_tick=on_tick,
        loop=loop,
    )

    # Xử lý giữ khung hình cuối cùng (hold after end) khi không ở chế độ lặp
    if not loop and sink.is_open():
        final_frame = episode.frames[-1]
        final_hud = hud_lines(final_frame.activation, muscle_names, cfg, warning=warning)
        hold_s = cfg.playback.hold_after_end_s

        if hold_s is not None and hold_s <= 0.0:
            pass
        elif getattr(sink, "auto_close_on_hold", False):
            pass
        else:
            dt_hold = 1.0 / display_hz if display_hz > 0 else 0.016
            hold_start = pacer_instance._clock()
            while sink.is_open():
                if hold_s is not None and (pacer_instance._clock() - hold_start) >= hold_s:
                    break
                sink.show(final_frame, final_hud)
                pacer_instance._sleep(dt_hold)

    return stats
