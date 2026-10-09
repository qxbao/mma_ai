"""Giao diện dòng lệnh huấn luyện cánh tay khuỷu (learning/cli.py).

Hiện thực điểm vào dòng lệnh huấn luyện CMD-TRN-0001 và các yêu cầu:
- FR-001: Huấn luyện thuật toán PPO trên mô hình cánh tay cơ bắp (ElbowReachEnv).
- FR-009: Tiếp tục huấn luyện từ điểm kiểm tra (checkpoint resume).
- FR-013: Báo cáo thông lượng môi trường (env steps/second) và thời gian thực (wall-clock).
- FR-015: Quản lý mã thoát dòng lệnh (exit codes) chuẩn mực theo hợp đồng cli.md.
- FR-018: Quản lý cấu hình huấn luyện và áp dụng ghi đè (overrides) tham số dòng lệnh.
- FR-020: Khởi chạy giao diện quan sát tiến trình huấn luyện ở tiến trình riêng biệt.
- FR-022: Tuỳ chọn hiển thị 3D độc lập (headless mặc định).
- FR-023: Khả năng cấu hình phục vụ đo đạc hiệu năng.
- INV-002: Bất biến không gian hành động — nghiêm cấm cờ nhận lực hay toạ độ tay từ người dùng.
- INV-005: Độc lập giữa tiến trình quan sát và tiến trình huấn luyện lõi.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from mma_ai.environment.errors import PhysicsInstabilityError
from mma_ai.environment.single_agent import make_env
from mma_ai.learning.errors import (
    CheckpointError,
    CheckpointIOError,
    NonFiniteError,
    RunDirError,
    TrainConfigError,
    TrainError,
)
from mma_ai.learning.run_dir import create_run_dir
from mma_ai.learning.train_config import TrainConfig

# Điểm móc phụ thuộc tuỳ chọn phục vụ kiểm thử và trì hoãn nhập thư viện nặng (deferred import)
Trainer: Any = None
load_checkpoint: Any = None

__all__: list[str] = [
    "Trainer",
    "create_run_dir",
    "load_checkpoint",
    "main",
    "make_env",
]


def _build_parser() -> argparse.ArgumentParser:
    """Xây dựng bộ phân tích cú pháp tham số dòng lệnh cho CMD-TRN-0001.

    Bảo vệ bất biến INV-002: Tuyệt đối không thêm các cờ nhận hành động thô,
    lực co cơ hay toạ độ mục tiêu từ người dùng.
    """
    parser = argparse.ArgumentParser(
        prog="train",
        description="Giao diện dòng lệnh huấn luyện PPO trên cánh tay khuỷu (CMD-TRN-0001)",
    )
    parser.add_argument(
        "--stage",
        type=str,
        default="elbow",
        help="Giai đoạn huấn luyện (M1 chỉ hỗ trợ 'elbow')",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Hạt giống ngẫu nhiên (random seed) cho tính tái lập",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Đường dẫn tệp cấu hình huấn luyện YAML tuỳ biến",
    )
    parser.add_argument(
        "--total-steps",
        type=int,
        default=None,
        help="Tổng số bước môi trường (total timesteps) cần huấn luyện",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Đường dẫn điểm kiểm tra (.pt) hoặc latest.json để tiếp tục huấn luyện",
    )
    parser.add_argument(
        "--runs-dir",
        type=str,
        default=None,
        help="Thư mục gốc lưu trữ các lần chạy huấn luyện",
    )
    parser.add_argument(
        "--ui",
        type=str,
        default="web",
        choices=["web", "none"],
        help="Chế độ giao diện quan sát: 'web' (mặc định) hoặc 'none'",
    )
    parser.add_argument(
        "--ui-port",
        type=int,
        default=None,
        help="Cổng mạng (port) lắng nghe cho giao diện quan sát (0 = hệ điều hành cấp)",
    )
    parser.add_argument(
        "--view3d",
        action="store_true",
        default=False,
        help="Bật hiển thị 3D MuJoCo ở tiến trình riêng biệt (mặc định tắt)",
    )
    return parser


def _extract_overrides(args: argparse.Namespace) -> dict[str, Any]:
    """Trích xuất từ điển ghi đè (overrides) cấu hình từ các cờ dòng lệnh (FR-018)."""
    overrides: dict[str, Any] = {}
    if args.seed is not None:
        overrides["seed"] = int(args.seed)
    if args.total_steps is not None:
        overrides["schedule.total_timesteps"] = int(args.total_steps)
    if args.runs_dir is not None:
        overrides["paths.runs_dir"] = str(args.runs_dir)
    if args.ui is not None:
        overrides["ui.mode"] = str(args.ui)
    if args.ui_port is not None:
        overrides["ui.port"] = int(args.ui_port)
    if args.view3d:
        overrides["ui.view3d"] = True
    return overrides


def _spawn_ui_process(
    run_dir_path: Path,
    port: int | None,
    view3d: bool,
) -> tuple[subprocess.Popen[Any] | None, str]:
    """Khởi chạy giao diện quan sát ở tiến trình riêng biệt (FR-020, INV-005).

    Nếu khởi chạy thất bại, ghi cảnh báo ra stderr và trả về URL không khả dụng;
    tiến trình huấn luyện cốt lõi vẫn tiếp tục hoạt động an toàn.
    """
    cmd = [
        sys.executable,
        "-m",
        "mma_ai.monitoring.cli",
        "--run",
        str(run_dir_path),
    ]
    if port is not None and port != 0:
        cmd.extend(["--port", str(port)])
    if view3d:
        cmd.append("--view3d")

    ui_proc: subprocess.Popen[Any] | None = None
    ui_url = "không khả dụng"
    try:
        ui_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as spawn_err:
        sys.stderr.write(
            f"Cảnh báo: Không thể khởi chạy giao diện quan sát (monitoring UI): {spawn_err}\n"
        )
        sys.stderr.flush()
        return None, ui_url

    # Chờ tối đa 2.0 giây để tệp ui.json xuất hiện hoặc phát hiện tiến trình dừng sớm
    ui_json_file = run_dir_path / "ui.json"
    deadline = time.time() + 2.0
    while time.time() < deadline:
        if ui_proc.poll() is not None:
            err_output = ""
            if ui_proc.stderr:
                try:
                    err_output = ui_proc.stderr.read().strip()
                except Exception:
                    pass
            msg = (
                f"Cảnh báo: Tiến trình giao diện quan sát dừng sớm với mã "
                f"{ui_proc.returncode}. {err_output}\n"
            )
            sys.stderr.write(msg)
            sys.stderr.flush()
            return ui_proc, ui_url

        if ui_json_file.exists():
            try:
                data = json.loads(ui_json_file.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "url" in data:
                    ui_url = str(data["url"])
                    return ui_proc, ui_url
            except Exception:
                pass
        time.sleep(0.05)

    return ui_proc, ui_url


def main(argv: Sequence[str] | None = None) -> int:
    """Điểm vào chính của dòng lệnh huấn luyện cánh tay khuỷu (CMD-TRN-0001).

    Tham số:
        argv: Danh sách tham số dòng lệnh tuỳ chọn (mặc định sys.argv[1:]).

    Trả về:
        Mã thoát nguyên (exit code):
        - 0: Huấn luyện hoàn thành thành công.
        - 1: Lỗi số học (NaN/Inf), mất ổn định vật lý hoặc lỗi nhập xuất checkpoint.
        - 2: Tham số dòng lệnh hoặc cấu hình không hợp lệ.
        - 3: Giai đoạn (stage) chưa triển khai.
        - 4: Điểm kiểm tra (checkpoint) hỏng hoặc không thể nạp.
        - 130: Bị ngắt bởi người dùng (Ctrl-C / KeyboardInterrupt).
    """
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as err:
        return 2 if err.code != 0 else 0

    # 1. Kiểm tra giai đoạn (stage) — chỉ hỗ trợ duy nhất 'elbow' trong M1 (AC-5)
    if args.stage != "elbow":
        sys.stderr.write(
            f"chưa triển khai: stage '{args.stage}' (M1 chỉ hỗ trợ 'elbow')\n"
        )
        sys.stderr.flush()
        return 3

    # 2. Xử lý ghi đè và nạp cấu hình huấn luyện (FR-018, mã 2 trước khi tạo run)
    overrides = _extract_overrides(args)
    try:
        cfg = TrainConfig.load(path=args.config, overrides=overrides)
    except TrainConfigError as config_err:
        sys.stderr.write(f"Cấu hình huấn luyện không hợp lệ: {config_err}\n")
        sys.stderr.flush()
        return 2
    except Exception as generic_config_err:
        sys.stderr.write(f"Lỗi nạp cấu hình huấn luyện: {generic_config_err}\n")
        sys.stderr.flush()
        return 2

    # 3. Kiểm tra tính hợp lệ của checkpoint nếu có cờ --resume trước khi tạo run (FR-009, mã 4)
    if args.resume is not None:
        resume_target = Path(args.resume)
        if not resume_target.exists():
            sys.stderr.write(
                f"Lỗi: Điểm kiểm tra (checkpoint) không tồn tại: '{args.resume}'\n"
            )
            sys.stderr.flush()
            return 4
        # Trì hoãn nạp hàm nạp checkpoint chỉ khi cần kiểm tra tệp checkpoint hợp lệ
        active_load_checkpoint = load_checkpoint
        if active_load_checkpoint is None:
            from mma_ai.learning.checkpoint import load_checkpoint as resolved_load_checkpoint

            active_load_checkpoint = resolved_load_checkpoint
        try:
            # Xác nhận tính toàn vẹn và khớp cấu hình trước khi khởi chạy
            active_load_checkpoint(resume_target, for_training=True, expected_cfg=cfg)
        except CheckpointError as ckpt_err:
            sys.stderr.write(f"Lỗi điểm kiểm tra (checkpoint error): {ckpt_err}\n")
            sys.stderr.flush()
            return 4
        except Exception as ckpt_read_err:
            sys.stderr.write(f"Không thể đọc điểm kiểm tra: {ckpt_read_err}\n")
            sys.stderr.flush()
            return 4

    # 4. Tạo thư mục lượt chạy mới (run directory) loại trừ (FR-011, INV-001)
    try:
        run_dir = create_run_dir(
            runs_dir=cfg.paths.runs_dir,
            stage=cfg.stage,
            seed=cfg.seed,
        )
    except RunDirError as run_dir_err:
        sys.stderr.write(f"Lỗi tạo thư mục lượt chạy: {run_dir_err}\n")
        sys.stderr.flush()
        return 1
    except Exception as dir_err:
        sys.stderr.write(f"Không thể tạo thư mục lượt chạy: {dir_err}\n")
        sys.stderr.flush()
        return 1

    # 5. Khởi tạo môi trường mô phỏng cánh tay khuỷu ở tập huấn luyện (INV-003)
    try:
        env = make_env(split="train")
    except Exception as env_err:
        sys.stderr.write(f"Lỗi khởi tạo môi trường mô phỏng: {env_err}\n")
        sys.stderr.flush()
        return 1

    # 6. Khởi chạy giao diện quan sát ở tiến trình riêng biệt khi bật tuỳ chọn web (FR-020, INV-005)
    ui_proc: subprocess.Popen[Any] | None = None
    ui_url = "đã tắt"
    if cfg.ui.mode == "web":
        ui_proc, ui_url = _spawn_ui_process(
            run_dir_path=run_dir.path,
            port=cfg.ui.port,
            view3d=cfg.ui.view3d,
        )

    # Trì hoãn nạp Trainer cho đến khi thực sự cần chạy huấn luyện
    active_trainer_cls = Trainer
    if active_trainer_cls is None:
        from mma_ai.learning.trainer import Trainer as resolved_trainer_cls

        active_trainer_cls = resolved_trainer_cls

    # 7. Khởi tạo và thực thi quy trình điều phối huấn luyện Trainer (FR-001)
    try:
        trainer = active_trainer_cls(
            cfg=cfg,
            env=env,
            run_dir=run_dir,
            resume_checkpoint=args.resume,
        )
        result = trainer.run()

        # In báo cáo thông lượng môi trường và thời gian chạy thực ra stdout (FR-013, AC-3)
        sys.stdout.write(
            f"Huấn luyện hoàn tất thành công.\n"
            f"Mã lượt chạy (run ID): {result.run_id}\n"
            f"Thông lượng môi trường (env steps/second): {result.env_steps_per_second:.2f}\n"
            f"Thời gian chạy thực (wall-clock): {result.wall_clock_seconds:.2f} s\n"
            f"Giao diện quan sát (monitoring URL): {ui_url}\n"
        )
        sys.stdout.flush()
        return 0

    except NonFiniteError as non_finite_err:
        sys.stderr.write(
            f"Lỗi huấn luyện: Phát hiện giá trị không hữu hạn (non-finite): {non_finite_err}\n"
        )
        sys.stderr.flush()
        return 1
    except PhysicsInstabilityError as physics_err:
        sys.stderr.write(
            f"Lỗi huấn luyện: Môi trường mất ổn định vật lý (physics instability): {physics_err}\n"
        )
        sys.stderr.flush()
        return 1
    except CheckpointIOError as io_err:
        sys.stderr.write(
            f"Lỗi huấn luyện: Lỗi nhập xuất điểm kiểm tra (checkpoint I/O error): {io_err}\n"
        )
        sys.stderr.flush()
        return 1
    except CheckpointError as ckpt_runtime_err:
        sys.stderr.write(
            f"Lỗi huấn luyện: Điểm kiểm tra không hợp lệ: {ckpt_runtime_err}\n"
        )
        sys.stderr.flush()
        return 4
    except KeyboardInterrupt:
        sys.stderr.write("Huấn luyện bị ngắt bởi người dùng (Ctrl-C).\n")
        sys.stderr.flush()
        return 130
    except TrainError as train_err:
        sys.stderr.write(f"Lỗi huấn luyện: {train_err}\n")
        sys.stderr.flush()
        return getattr(train_err, "exit_code", 1)
    except Exception as unexpected_err:
        sys.stderr.write(f"Lỗi không xác định trong quá trình huấn luyện: {unexpected_err}\n")
        sys.stderr.flush()
        return 1


if __name__ == "__main__":
    sys.exit(main())
