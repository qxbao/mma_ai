"""Mô-đun hiển thị 3D quan sát huấn luyện qua MuJoCo Passive Viewer (viewer3d.py).

Hiện thực và bảo vệ các yêu cầu:
- FR-022: Hiển thị 3D khuỷu tay chạy ở tiến trình riêng, bật/tắt được và mặc định tắt;
  huấn luyện mặc định không giao diện (headless); nạp chính sách (policy) mới nhất
  từ checkpoints/latest.json và chạy các tập (episode) trên bản sao môi trường tập train.
- INV-005: Giao diện chỉ-đọc (read-only); không được sửa hay ghi vào checkpoint, cấu hình
  hay tiến trình huấn luyện; không import learning.trainer hoặc learning.ppo.
- NFR-HEADLESS-001: Khi thiếu biến môi trường DISPLAY hoặc WAYLAND_DISPLAY, in "3D không khả dụng"
  ra stderr và thoát với mã 0 (exit 0), không ném lỗi làm gián đoạn chương trình.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

__all__: list[str] = ["View3D"]


class View3D:
    """Tiến trình hiển thị 3D tuỳ chọn cho MMA-AI (FR-022, INV-005)."""

    def __init__(
        self,
        run_dir: str | Path,
        poll_interval_s: float = 2.0,
    ) -> None:
        """Khởi tạo thành phần hiển thị 3D quan sát thư mục huấn luyện.

        Tham số:
            run_dir: Thư mục chứa tiến trình huấn luyện để đọc checkpoints/latest.json.
            poll_interval_s: Chu kỳ kiểm tra và nạp checkpoint mới tính bằng giây.
        """
        self.run_dir: Path = Path(run_dir).resolve()
        self.poll_interval_s: float = float(poll_interval_s)
        self._is_running: bool = False

    @property
    def is_running(self) -> bool:
        """Trạng thái tiến trình quan sát 3D có đang chạy vòng lặp hay không."""
        return self._is_running

    @staticmethod
    def has_display() -> bool:
        """Kiểm tra sự hiện diện của biến môi trường hiển thị DISPLAY hoặc WAYLAND_DISPLAY."""
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    def _try_load_latest_policy(self) -> Any:
        """Đọc tệp checkpoints/latest.json và nạp chính sách (policy) mới nhất chỉ-đọc."""
        latest_file = self.run_dir / "checkpoints" / "latest.json"
        if not latest_file.is_file():
            return None

        try:
            # Nhập hàm load_policy trễ để tránh phụ thuộc bắt buộc ở module level
            from mma_ai.learning.checkpoint import load_policy

            return load_policy(latest_file)
        except Exception:
            # Nếu tệp checkpoint đang ghi dở hoặc lỗi, không làm gián đoạn vòng hiển thị
            return None

    def run(
        self,
        env: Any = None,
        max_episodes: int | None = None,
        step_delay_s: float = 0.0,
    ) -> int:
        """Thực thi vòng lặp hiển thị 3D quan sát huấn luyện (FR-022, NFR-HEADLESS-001).

        Khi thiếu màn hình (DISPLAY hoặc WAYLAND_DISPLAY), in '3D không khả dụng' ra stderr
        và thoát với mã 0 mà không ném ngoại lệ.

        Tham số:
            env: Bản sao môi trường tuỳ biến (mặc định tạo make_env(split="train")).
            max_episodes: Số tập tối đa cần chạy (None nghĩa là chạy liên tục tới khi đóng).
            step_delay_s: Khoảng chờ giữa các bước mô phỏng để làm chậm chuyển động trực quan.

        Trả về:
            Mã thoát nguyên 0 khi hoàn thành hoặc khi không có màn hình.
        """
        if not self.has_display():
            sys.stderr.write("3D không khả dụng\n")
            sys.stderr.flush()
            return 0

        # Chỉ nhập mujoco.viewer bên trong hàm chạy khi có màn hình (NFR-HEADLESS-001)
        import mujoco.viewer
        import numpy as np

        from mma_ai.environment.single_agent import make_env

        self._is_running = True

        try:
            # 1. Khởi tạo bản sao môi trường ở tập train (INV-003, FR-022)
            active_env = env if env is not None else make_env(split="train")

            # 2. Sử dụng MjModel và MjData riêng cho passive viewer
            unwrapped = getattr(active_env, "unwrapped", active_env)
            mj_model = getattr(unwrapped, "model", None)
            mj_data = getattr(unwrapped, "data", None)

            # Khởi chạy passive viewer trên MjData riêng
            viewer = mujoco.viewer.launch_passive(mj_model, mj_data)

            current_policy = self._try_load_latest_policy()
            last_policy_check = time.time()
            episodes_done = 0

            try:
                while viewer.is_running():
                    if max_episodes is not None and episodes_done >= max_episodes:
                        break

                    # Kiểm tra và nạp chính sách mới nhất định kỳ mỗi poll_interval_s giây
                    now = time.time()
                    if now - last_policy_check >= self.poll_interval_s:
                        new_policy = self._try_load_latest_policy()
                        if new_policy is not None:
                            current_policy = new_policy
                        last_policy_check = now

                    # Chạy một tập thử nghiệm (episode) trên bản sao môi trường
                    obs, _ = active_env.reset()
                    done = False

                    while not done and viewer.is_running():
                        if current_policy is not None:
                            action = current_policy.act_deterministic(obs)
                        else:
                            action = np.zeros(active_env.action_space.shape, dtype=np.float32)

                        obs, _reward, terminated, truncated, _info = active_env.step(action)
                        done = terminated or truncated

                        viewer.sync()
                        if step_delay_s > 0:
                            time.sleep(step_delay_s)

                    episodes_done += 1

            finally:
                viewer.close()
                if env is None and hasattr(active_env, "close"):
                    active_env.close()

        except Exception as err:
            # Đóng giao diện giữa chừng không làm hỏng tiến trình huấn luyện (INV-005)
            sys.stderr.write(f"Cảnh báo giao diện 3D: {err}\n")
            sys.stderr.flush()
            return 0
        finally:
            self._is_running = False

        return 0


if __name__ == "__main__":
    target_run_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    viewer_instance = View3D(target_run_dir)
    sys.exit(viewer_instance.run())
