"""Giao diện dòng lệnh mỏng cho phát lại mô phỏng 3D và phiên demo (mma_ai.visualization.cli).

Hiện thực hợp đồng CLI-005 và điểm vào dòng lệnh CMD-VIS-0001:
- FR-014: Thoát an toàn không phụ thuộc bước dọn dẹp tài nguyên đồ hoạ (graphics teardown).
- CMD-VIS-0001: Điểm vào dòng lệnh tiếp nhận các cờ cấu hình phát lại và chạy demo.
- CLI-005: Quy tắc thoát tiến trình dòng lệnh thông qua os._exit khi MuJoCo Viewer đã mở.
"""

from __future__ import annotations

import contextlib
import os
import sys
from collections.abc import Sequence

from mma_ai.visualization.replay import (
    get_active_viewer_sink,
    run_replay,
    was_viewer_opened,
)

__all__: list[str] = ["main"]


def main(argv: Sequence[str] | None = None) -> int:
    """Điểm vào chính của giao diện dòng lệnh phát lại mô phỏng và demo 3D (CLI-005).

    Nhận các cờ dòng lệnh (--episode, --checkpoint, --headless, --save-episode,
    --speed, --loop, --allow-model-mismatch, --split, --target-index, --seed, --config),
    điều phối thực thi thông qua run_replay và quản lý mã thoát (exit code) an toàn.

    Args:
        argv: Danh sách tham số dòng lệnh tuỳ chọn (mặc định lấy từ sys.argv[1:]).

    Returns:
        Mã thoát nguyên tương ứng theo hợp đồng CMD-VIS-0001.
    """
    effective_argv = list(argv) if argv is not None else sys.argv[1:]

    try:
        exit_code = run_replay(effective_argv)
    except KeyboardInterrupt:
        exit_code = 130
    except Exception as err:
        sys.stderr.write(f"Lỗi không lường trước tại điểm vào CLI: {err}\n")
        exit_code = 1

    # Luôn xả bộ đệm xuất nhập chuẩn để không thất thoát thông tin tóm tắt và thông báo
    sys.stdout.flush()
    sys.stderr.flush()

    # Chỉ gọi os._exit khi viewer đã mở để tránh lỗi phân đoạn (SIGSEGV)
    # phát sinh từ bộ dọn dẹp đồ hoạ MuJoCo C
    if was_viewer_opened():
        active_sink = get_active_viewer_sink()
        if active_sink is not None and hasattr(active_sink, "close"):
            with contextlib.suppress(Exception):
                active_sink.close()

        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(exit_code)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
