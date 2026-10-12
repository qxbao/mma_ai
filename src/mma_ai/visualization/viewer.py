"""Mô-đun hiện thực bộ nhận khung hình giao diện MuJoCo Viewer (ViewerSink).

Định danh mô-đun: mma_ai.visualization.viewer.

Hiện thực các yêu cầu kỹ thuật và hợp đồng API:
- FR-001: Phát lại chuỗi khung hình theo thứ tự thời gian đã ghi trong MuJoCo Viewer.
- FR-004: Hiển thị điểm đánh dấu mục tiêu (target marker) tại vị trí đã ghi.
- FR-005: Hiển thị 6 giá trị kích hoạt cơ (muscle activation) tương ứng qua set_texts.
- FR-015: Nhập lười (lazy import) mujoco.viewer trong ViewerSink để đường không đồ hoạ an toàn.
- INV-002: Replay chỉ đặt lại trạng thái đã ghi (qpos/act) và mj_forward, không điều khiển cơ.
- API-VIS-0010: Cung cấp lớp ViewerSink(model, data, cfg) hiện thực giao diện FrameSink.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, Sequence

import numpy as np

from mma_ai.compat.display import viewer_launch_hint
from mma_ai.compat.platform_info import detect_platform
from mma_ai.visualization.errors import DisplayUnavailable

if TYPE_CHECKING:
    import mujoco

    from mma_ai.visualization.episode import Frame
    from mma_ai.visualization.replay_config import ReplayConfig


class ViewerSink:
    """Bộ nhận khung hình (frame sink) tích hợp với MuJoCo Viewer thụ động (passive viewer).

    Hiện thực hợp đồng API-VIS-0010 và tuân thủ giao diện FrameSink của hệ thống hiển thị.
    """

    def __init__(
        self,
        model: mujoco.MjModel,
        data: mujoco.MjData,
        cfg: ReplayConfig,
        *,
        handle: Any | None = None,
    ) -> None:
        """Khởi tạo bộ nhận khung hình và kết nối tới cửa sổ MuJoCo Viewer.

        Args:
            model: Mô hình vật lý MuJoCo (MjModel).
            data: Dữ liệu trạng thái mô phỏng MuJoCo (MjData).
            cfg: Cấu hình phát lại và demo (ReplayConfig).
            handle: Tay cầm điều khiển viewer tuỳ chọn (phục vụ kiểm thử cách ly hoặc tái dùng).
        """
        self.model = model
        self.data = data
        self.cfg = cfg
        self.auto_close_on_hold = False
        self._is_open = True
        self._target_position_m: tuple[float, float, float] | None = None

        # Nhập lười (lazy import) mujoco.viewer tại thời điểm khởi tạo thể hiện (FR-015)
        import mujoco.viewer

        if handle is not None:
            self._handle = handle
        else:
            profile = detect_platform()
            launch_hint = viewer_launch_hint(profile=profile)
            if launch_hint is not None:
                raise DisplayUnavailable(f"Lỗi hiển thị giao diện đồ hoạ: {launch_hint}")
            try:
                self._handle = mujoco.viewer.launch_passive(self.model, self.data)
            except Exception as error:
                launch_hint = viewer_launch_hint(error=str(error), profile=profile)
                if launch_hint is None:
                    raise
                raise DisplayUnavailable(
                    f"Lỗi hiển thị giao diện đồ hoạ: {launch_hint}"
                ) from error

    def set_target(
        self,
        position_m: tuple[float, float, float] | Sequence[float],
    ) -> None:
        """Thiết lập vị trí toạ độ điểm đánh dấu mục tiêu (target marker) trong không gian 3D.

        Args:
            position_m: Toạ độ 3 chiều (x, y, z) theo mét của mục tiêu.
        """
        self._target_position_m = (
            float(position_m[0]),
            float(position_m[1]),
            float(position_m[2]),
        )

    def set_target_marker(
        self,
        position_m: tuple[float, float, float] | Sequence[float],
    ) -> None:
        """Bí danh thiết lập vị trí mục tiêu tương thích với giao thức phát lại."""
        self.set_target(position_m)

    def set_target_position(
        self,
        position_m: tuple[float, float, float] | Sequence[float],
    ) -> None:
        """Bí danh thiết lập vị trí mục tiêu tương thích với giao thức phát lại."""
        self.set_target(position_m)

    def is_open(self) -> bool:
        """Kiểm tra cửa sổ viewer có đang mở và duy trì vòng lặp hay không."""
        if not self._is_open:
            return False
        if self._handle is not None and hasattr(self._handle, "is_running"):
            return bool(self._handle.is_running())
        return self._is_open

    def close(self) -> None:
        """Đóng cửa sổ viewer và giải phóng tài nguyên đồ hoạ liên quan."""
        self._is_open = False
        if self._handle is not None and hasattr(self._handle, "close"):
            self._handle.close()

    def show(self, frame: Frame, hud: list[str]) -> None:
        """Hiển thị một khung hình và cập nhật HUD trên MuJoCo Viewer (FR-001, FR-004, FR-005).

        Args:
            frame: Dữ liệu khung hình chứa toạ độ khớp, vận tốc và kích hoạt cơ.
            hud: Danh sách các dòng văn bản hiển thị lớp trên (heads-up display).
        """
        if not self.is_open():
            return

        import mujoco

        # Khoá cảnh để cập nhật trạng thái vật lý (qpos, act, mj_forward) và user_scn an toàn luồng
        lock_ctx = (
            self._handle.lock()
            if (self._handle is not None and hasattr(self._handle, "lock"))
            else contextlib.nullcontext()
        )

        with lock_ctx:
            # Gán trạng thái khớp qpos và vận tốc qvel (INV-002: replay chỉ đặt trạng thái đã ghi)
            if frame.qpos and hasattr(self.data, "qpos"):
                n_qpos = min(len(self.data.qpos), len(frame.qpos))
                self.data.qpos[:n_qpos] = frame.qpos[:n_qpos]

            if frame.qvel and hasattr(self.data, "qvel"):
                n_qvel = min(len(self.data.qvel), len(frame.qvel))
                self.data.qvel[:n_qvel] = frame.qvel[:n_qvel]

            # Gán trạng thái kích hoạt cơ (muscle activation) vào mảng act của MuJoCo
            if hasattr(self.model, "na") and self.model.na > 0 and hasattr(self.data, "act"):
                if frame.activation:
                    n_act = min(self.model.na, len(frame.activation))
                    self.data.act[:n_act] = frame.activation[:n_act]

            # Cập nhật thời gian mô phỏng tương ứng của khung hình
            if hasattr(self.data, "time"):
                self.data.time = float(frame.t_s)

            # Tính toán động học thuận (forward kinematics) để đồng bộ hình học các phân đoạn cơ thể
            mujoco.mj_forward(self.model, self.data)

            # Cập nhật hình cầu đánh dấu mục tiêu 3D trong user_scn (FR-004)
            scn = getattr(self._handle, "user_scn", None)
            if scn is not None:
                if self._target_position_m is not None and getattr(scn, "maxgeom", 0) > 0:
                    geoms = getattr(scn, "geoms", None)
                    if geoms is not None and len(geoms) > 0:
                        radius = float(self.cfg.target_marker.radius_m)
                        size = np.array([radius, 0.0, 0.0], dtype=np.float64)
                        pos = np.array(self._target_position_m, dtype=np.float64)
                        mat = np.eye(3, dtype=np.float64).flatten()
                        rgba = np.array(self.cfg.target_marker.rgba, dtype=np.float32)

                        mujoco.mjv_initGeom(
                            geoms[0],
                            mujoco.mjtGeom.mjGEOM_SPHERE,
                            size,
                            pos,
                            mat,
                            rgba,
                        )
                        scn.ngeom = 1
                else:
                    scn.ngeom = 0

        # Cập nhật bảng thông số HUD qua set_texts/clear_texts ở ngoài khối khoá cảnh (FR-005)
        # Tránh tranh chấp khoá với luồng kết xuất đồ hoạ hoặc vòng lặp sự kiện giao diện
        if self._handle is not None:
            if hud:
                hud_combined = "\n".join(hud)
                if hasattr(self._handle, "set_texts"):
                    self._handle.set_texts([(None, None, hud_combined, "")])
            else:
                if hasattr(self._handle, "clear_texts"):
                    self._handle.clear_texts()
                elif hasattr(self._handle, "set_texts"):
                    self._handle.set_texts([])

        # Đồng bộ hoá khung hình tới cửa sổ hiển thị
        if self._handle is not None and hasattr(self._handle, "sync"):
            self._handle.sync()

    def __enter__(self) -> ViewerSink:
        """Hỗ trợ cú pháp quản lý ngữ cảnh (context manager)."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Đóng viewer khi kết thúc khối ngữ cảnh."""
        self.close()
