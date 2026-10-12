"""Giao diện dòng lệnh quan sát tiến trình huấn luyện MMA-AI (monitoring/cli.py).

Hiện thực và bảo vệ các yêu cầu:
- CMD-TRN-0002: Lệnh quan sát huấn luyện CLI với các cờ --run, --port, --view3d.
- FR-020: Khởi chạy máy chủ HTTP giao diện quan sát (monitoring dashboard) thời gian thực.
- FR-021: Giao diện chỉ-đọc; ui.json là tệp duy nhất được phép ghi vào thư mục run.
- FR-022: Tuỳ chọn hiển thị 3D (--view3d) chạy ở tiến trình riêng (separate process), mặc định tắt.
- INV-005: Giao diện chỉ đọc dữ liệu huấn luyện; nghiêm cấm nhập learning.trainer hoặc learning.ppo.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
import threading
import time
from pathlib import Path
from typing import Sequence

from mma_ai.compat.fsio import write_text_atomic
from mma_ai.compat.stdio import ensure_utf8_stdio
from mma_ai.monitoring.dashboard import serve

__all__: list[str] = ["main"]


def _run_viewer3d_process(target_dir: str) -> None:
    """Hàm đích thực thi hiển thị 3D trong tiến trình con độc lập (FR-022)."""
    from mma_ai.monitoring.viewer3d import View3D

    viewer = View3D(target_dir)
    viewer.run()


def _build_parser() -> argparse.ArgumentParser:
    """Xây dựng bộ phân tích cú pháp tham số dòng lệnh cho CMD-TRN-0002."""
    parser = argparse.ArgumentParser(
        description="Giao diện dòng lệnh quan sát tiến trình huấn luyện MMA-AI (CMD-TRN-0002)",
    )
    parser.add_argument(
        "--run",
        type=str,
        required=True,
        help="Đường dẫn thư mục run chứa dữ liệu huấn luyện (bắt buộc)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Cổng mạng (network port) lắng nghe (0 = hệ điều hành tự cấp phát)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Địa chỉ vòng lặp ngược (loopback) lắng nghe máy chủ",
    )
    parser.add_argument(
        "--view3d",
        action="store_true",
        default=False,
        help="Khởi chạy cửa sổ hiển thị 3D quan sát khuỷu tay trong tiến trình riêng",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stop_event: threading.Event | None = None,
) -> int:
    """Điểm vào chính của CLI quan sát huấn luyện (CMD-TRN-0002).

    Tham số:
        argv: Danh sách tham số dòng lệnh (mặc định lấy từ sys.argv[1:]).
        stop_event: Sự kiện dừng luồng dành cho kiểm thử và điều khiển tự động.

    Trả về:
        Mã thoát nguyên (0 khi hoàn tất/đóng sạch, khác 0 khi lỗi khởi động).
    """
    ensure_utf8_stdio()
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    run_path = Path(args.run).resolve()
    if not run_path.exists() or not run_path.is_dir():
        sys.stderr.write(
            f"Lỗi: Thư mục run '{args.run}' không tồn tại hoặc không phải là thư mục hợp lệ.\n"
        )
        sys.stderr.flush()
        return 1

    try:
        server = serve(
            run_dir=run_path,
            host=args.host,
            port=args.port,
        )
    except Exception as err:
        sys.stderr.write(
            f"Lỗi khởi động máy chủ quan sát trên cổng {args.port}: {err}\n"
        )
        sys.stderr.flush()
        return 1

    # In URL máy chủ ra đầu ra tiêu chuẩn để người dùng truy cập
    sys.stdout.write(f"Giao diện quan sát hoạt động tại: {server.url}\n")
    sys.stdout.flush()

    # Ghi tệp ui.json nguyên tử: đây là tệp DUY NHẤT tiến trình
    # giao diện được phép ghi vào thư mục run (INV-005, FR-021)
    ui_info = {
        "url": server.url,
        "pid": os.getpid(),
    }
    ui_path = run_path / "ui.json"
    try:
        write_text_atomic(
            ui_path,
            json.dumps(ui_info, ensure_ascii=False, indent=2),
        )
    except Exception as err:
        sys.stderr.write(f"Lỗi ghi tệp ui.json vào thư mục run: {err}\n")
        sys.stderr.flush()
        server.close()
        return 1

    viewer_process: multiprocessing.Process | None = None
    if args.view3d:
        viewer_process = multiprocessing.Process(
            target=_run_viewer3d_process,
            args=(str(run_path),),
            daemon=True,
            name="MMA-AI-View3D",
        )
        viewer_process.start()

    try:
        while True:
            if stop_event is not None and stop_event.is_set():
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        # Đóng nhẹ nhàng khi người dùng ngắt bằng Ctrl-C
        pass
    finally:
        if viewer_process is not None and viewer_process.is_alive():
            viewer_process.terminate()
            viewer_process.join(timeout=1.0)
        server.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
