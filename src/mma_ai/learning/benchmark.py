"""Chuẩn đo hiệu năng chi phí giao diện quan sát huấn luyện (learning/benchmark.py).

Hiện thực tiêu chuẩn CMD-TRN-0004 và các yêu cầu:
- FR-023: Đo đạc chi phí tài nguyên (CPU/RAM/GPU/VRAM) của giao diện quan sát (monitoring UI).
- NFR-PERF-001: Chi phí giao diện không làm giảm thông lượng quá 10% (ratio_median >= 0.90).
- CMD-TRN-0004: Giao diện dòng lệnh benchmark_train chạy xen kẽ các lượt smoke bật/tắt giao diện.
- INV-005: Giao diện quan sát chỉ đọc và hoàn toàn độc lập với luồng huấn luyện cốt lõi.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__: list[str] = [
    "build_benchmark_report",
    "calculate_median",
    "calculate_ratio_median",
    "calculate_ui_cost",
    "evaluate_pass",
    "evaluate_view3d_status",
    "main",
    "run_benchmark",
    "write_benchmark_report",
]


def calculate_median(values: Sequence[float]) -> float:
    """Tính trung vị (median) của chuỗi thông lượng env steps/s.

    Tham số:
        values: Danh sách các giá trị số thực đại diện cho thông lượng bước môi trường trên giây.

    Trả về:
        Giá trị trung vị kiểu float >= 0.
    """
    if not values:
        raise ValueError("Không thể tính trung vị cho chuỗi rỗng")
    clean_vals = [float(x) for x in values]
    return float(statistics.median(clean_vals))


def calculate_ratio_median(ui_on_median: float, ui_off_median: float) -> float:
    """Tính tỷ lệ trung vị (ratio median) giữa lượt bật và tắt giao diện.

    Quy tắc:
        ratio_median = median(ui_on) / median(ui_off)

    Tham số:
        ui_on_median: Giá trị trung vị thông lượng khi bật giao diện quan sát.
        ui_off_median: Giá trị trung vị thông lượng khi tắt giao diện quan sát.

    Trả về:
        Tỷ lệ số thực làm tròn 4 chữ số thập phân.
    """
    if ui_off_median <= 0.0:
        raise ValueError(
            f"Giá trị trung vị của lượt tắt giao diện phải lớn hơn 0 (nhận {ui_off_median})"
        )
    ratio = float(ui_on_median) / float(ui_off_median)
    return float(round(ratio, 4))


def evaluate_pass(ratio_median: float, threshold: float = 0.9) -> bool:
    """Đánh giá quy tắc đạt chuẩn (pass rule) theo ngưỡng hiệu năng (NFR-PERF-001).

    Đạt chuẩn khi và chỉ khi tỷ lệ trung vị không nhỏ hơn ngưỡng (mặc định 0.90, tức giảm <= 10%).
    """
    return bool(ratio_median >= threshold)


def _extract_metric_values(
    res_list: Sequence[Mapping[str, Any] | None],
    key: str,
) -> list[float]:
    """Trích xuất danh sách giá trị số thực hợp lệ cho một khoá tài nguyên."""
    results: list[float] = []
    for r in res_list:
        if r is not None and key in r and r[key] is not None:
            try:
                results.append(float(r[key]))
            except (ValueError, TypeError):
                pass
    return results


def calculate_ui_cost(
    ui_on_resources: Sequence[Mapping[str, Any] | None] | Mapping[str, Any] | None,
    ui_off_resources: Sequence[Mapping[str, Any] | None] | Mapping[str, Any] | None,
) -> dict[str, float | None]:
    """Tính toán chi phí tài nguyên (resource delta) phát sinh do giao diện quan sát (FR-023).

    Tính độ chênh lệch trung bình giữa lượt bật và tắt giao diện cho các đại lượng:
    - cpu_utilization_pct_delta: % CPU chênh lệch
    - ram_peak_mb_delta: RAM đỉnh (MB) chênh lệch
    - vram_peak_mb_delta: VRAM đỉnh (MB) chênh lệch khi có GPU CUDA (null khi không có)
    """
    on_seq: Sequence[Mapping[str, Any] | None] = (
        [ui_on_resources] if isinstance(ui_on_resources, Mapping) else (ui_on_resources or [])
    )
    off_seq: Sequence[Mapping[str, Any] | None] = (
        [ui_off_resources] if isinstance(ui_off_resources, Mapping) else (ui_off_resources or [])
    )

    deltas: dict[str, float | None] = {
        "cpu_utilization_pct_delta": None,
        "ram_peak_mb_delta": None,
        "vram_peak_mb_delta": None,
    }

    key_map = [
        ("cpu_utilization_pct", "cpu_utilization_pct_delta"),
        ("ram_peak_mb", "ram_peak_mb_delta"),
        ("vram_peak_mb", "vram_peak_mb_delta"),
    ]

    for raw_key, delta_key in key_map:
        on_vals = _extract_metric_values(on_seq, raw_key)
        off_vals = _extract_metric_values(off_seq, raw_key)

        if on_vals and off_vals:
            mean_on = statistics.mean(on_vals)
            mean_off = statistics.mean(off_vals)
            deltas[delta_key] = float(round(mean_on - mean_off, 2))
        else:
            deltas[delta_key] = None

    return deltas


def evaluate_view3d_status(has_display: bool | None = None) -> dict[str, Any]:
    """Đánh giá trạng thái đo đạc khung nhìn 3D (FR-022, FR-023, NFR-HEADLESS-001).

    Khi không phát hiện màn hình (DISPLAY hoặc WAYLAND_DISPLAY chưa đặt), ghi nhận
    measured: false kèm lý do rõ ràng để tuân thủ kiểm định không cần giao diện đồ hoạ.
    """
    if has_display is None:
        has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    if not has_display:
        return {
            "measured": False,
            "reason": "không có màn hình (DISPLAY chưa đặt)",
        }
    return {
        "measured": False,
        "reason": "chế độ hiển thị 3D tắt mặc định trong lượt đo benchmark",
    }


def build_benchmark_report(
    seed: int,
    env_steps_per_run: int,
    repeats: int,
    ui_off_steps: Sequence[float],
    ui_on_steps: Sequence[float],
    ui_cost: Mapping[str, Any],
    view3d: Mapping[str, Any],
    threshold: float = 0.9,
    created_utc: str | None = None,
) -> dict[str, Any]:
    """Dựng đối tượng báo cáo benchmark theo đúng JSON Schema hợp đồng.

    Tuân thủ train-benchmark.schema.json, lõi tính thuần túy bảo đảm khớp cấu trúc.
    """
    median_off = calculate_median(ui_off_steps)
    median_on = calculate_median(ui_on_steps)
    ratio_median = calculate_ratio_median(median_on, median_off)
    passed = evaluate_pass(ratio_median, threshold)

    if created_utc is None:
        created_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "schema_version": "1.0.0",
        "created_utc": str(created_utc),
        "seed": int(seed),
        "env_steps_per_run": int(env_steps_per_run),
        "repeats": int(repeats),
        "ui_off": {
            "env_steps_per_second": [float(x) for x in ui_off_steps],
            "median": float(median_off),
        },
        "ui_on": {
            "env_steps_per_second": [float(x) for x in ui_on_steps],
            "median": float(median_on),
        },
        "ratio_median": float(ratio_median),
        "threshold": float(threshold),
        "passed": bool(passed),
        "ui_cost": {
            "cpu_utilization_pct_delta": ui_cost.get("cpu_utilization_pct_delta"),
            "ram_peak_mb_delta": ui_cost.get("ram_peak_mb_delta"),
            "vram_peak_mb_delta": ui_cost.get("vram_peak_mb_delta"),
        },
        "view3d": {
            "measured": bool(view3d.get("measured", False)),
            "reason": view3d.get("reason"),
        },
    }


def write_benchmark_report(
    output_path: Path | str,
    report: Mapping[str, Any],
) -> Path:
    """Ghi báo cáo benchmark nguyên tử xuống đĩa bằng tệp tạm và thay thế (os.replace)."""
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = out_file.with_suffix(f"{out_file.suffix}.tmp")

    data_str = json.dumps(dict(report), indent=2, ensure_ascii=False)
    tmp_file.write_text(data_str + "\n", encoding="utf-8")
    os.replace(tmp_file, out_file)
    return out_file


def _default_runner(
    seed: int,
    ui_mode: str,
    runs_dir: Path,
    config_path: Path | None = None,
    total_steps: int | None = None,
) -> dict[str, Any]:
    """Thực thi một lượt huấn luyện thông qua dòng lệnh mma_ai.learning.cli."""
    runs_dir.mkdir(parents=True, exist_ok=True)
    existing_dirs = {p.name for p in runs_dir.iterdir() if p.is_dir()}

    cmd = [
        sys.executable,
        "-m",
        "mma_ai.learning.cli",
        "--stage",
        "elbow",
        "--seed",
        str(seed),
        "--ui",
        str(ui_mode),
        "--runs-dir",
        str(runs_dir),
    ]
    if config_path is not None:
        cmd.extend(["--config", str(config_path)])
    if total_steps is not None:
        cmd.extend(["--total-steps", str(total_steps)])

    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(
            f"Lượt huấn luyện thất bại với mã {res.returncode}: {res.stderr.strip()}"
        )

    # Xác định thư mục lượt chạy mới tạo
    new_dirs = [p for p in runs_dir.iterdir() if p.is_dir() and p.name not in existing_dirs]
    if not new_dirs:
        all_dirs = sorted(
            [p for p in runs_dir.iterdir() if p.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not all_dirs:
            raise FileNotFoundError(f"Không tìm thấy thư mục lượt chạy nào trong '{runs_dir}'")
        target_dir = all_dirs[0]
    else:
        target_dir = new_dirs[0]

    manifest_file = target_dir / "manifest.json"
    if not manifest_file.is_file():
        raise FileNotFoundError(f"Không tìm thấy manifest.json tại '{target_dir}'")

    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    return {
        "throughput": data.get("throughput", {}),
        "resources": data.get("resources", {}),
    }


def run_benchmark(
    seed: int = 42,
    repeats: int = 5,
    config_path: Path | str | None = None,
    total_steps: int | None = None,
    output_path: Path | str = "logs/m1/benchmark_train.json",
    runs_dir: Path | str | None = None,
    threshold: float = 0.9,
    runner: Any = None,
) -> tuple[dict[str, Any], bool]:
    """Điều phối toàn bộ quy trình đo đạc hiệu năng xen kẽ (interleaved benchmarking).

    Chạy xen kẽ `repeats` lần lượt chạy smoke mở rộng:
    ui_off (chế độ none) và ui_on (chế độ web) trên cùng máy và seed để giảm thiểu nhiễu nhiệt.

    Tham số:
        seed: Hạt giống ngẫu nhiên (mặc định 42).
        repeats: Số lần lặp xen kẽ (tối thiểu 5).
        config_path: Đường dẫn tệp cấu hình huấn luyện tuỳ chọn.
        total_steps: Tổng số bước môi trường cho lượt smoke mở rộng (mặc định 8192).
        output_path: Đường dẫn lưu tệp kết quả JSON.
        runs_dir: Thư mục chứa các lượt chạy tạm thời.
        threshold: Ngưỡng tỷ lệ trung vị đạt chuẩn (mặc định 0.90).
        runner: Hàm thực thi một lượt chạy (phục vụ kiểm thử giả lập hoặc chạy mặc định).

    Trả về:
        Bộ (báo cáo từ điển hợp chuẩn JSON Schema, trạng thái đạt chuẩn boolean).
    """
    if repeats < 5:
        msg = f"Số lần lặp (repeats) phải tối thiểu 5 theo quy định hợp đồng (nhận {repeats})"
        raise ValueError(msg)

    resolved_runs_dir = (
        Path(runs_dir) if runs_dir is not None else Path("runs/benchmark_scratch")
    )
    resolved_config = Path(config_path) if config_path is not None else None
    resolved_total_steps = total_steps if total_steps is not None else 8192
    active_runner = runner or _default_runner

    ui_off_steps: list[float] = []
    ui_on_steps: list[float] = []
    ui_off_resources: list[dict[str, Any]] = []
    ui_on_resources: list[dict[str, Any]] = []
    env_steps_recorded: int = resolved_total_steps

    # Thực thi xen kẽ (interleaved)
    for _ in range(repeats):
        # Thu thập số liệu khi tắt giao diện quan sát
        res_off = active_runner(
            seed=seed,
            ui_mode="none",
            runs_dir=resolved_runs_dir,
            config_path=resolved_config,
            total_steps=resolved_total_steps,
        )
        tp_off = float(res_off.get("throughput", {}).get("env_steps_per_second", 0.0))
        ui_off_steps.append(tp_off)
        ui_off_resources.append(dict(res_off.get("resources", {})))
        if "env_steps" in res_off.get("throughput", {}):
            env_steps_recorded = int(res_off["throughput"]["env_steps"])

        # Thu thập số liệu khi bật giao diện quan sát
        res_on = active_runner(
            seed=seed,
            ui_mode="web",
            runs_dir=resolved_runs_dir,
            config_path=resolved_config,
            total_steps=resolved_total_steps,
        )
        tp_on = float(res_on.get("throughput", {}).get("env_steps_per_second", 0.0))
        ui_on_steps.append(tp_on)
        ui_on_resources.append(dict(res_on.get("resources", {})))

    ui_cost = calculate_ui_cost(ui_on_resources, ui_off_resources)
    view3d = evaluate_view3d_status()

    report = build_benchmark_report(
        seed=seed,
        env_steps_per_run=env_steps_recorded,
        repeats=repeats,
        ui_off_steps=ui_off_steps,
        ui_on_steps=ui_on_steps,
        ui_cost=ui_cost,
        view3d=view3d,
        threshold=threshold,
    )

    write_benchmark_report(output_path, report)
    return report, bool(report["passed"])


def _build_parser() -> argparse.ArgumentParser:
    """Xây dựng bộ phân tích cú pháp tham số dòng lệnh cho CMD-TRN-0004."""
    parser = argparse.ArgumentParser(
        prog="benchmark_train",
        description="Đo đạc chi phí hiệu năng của giao diện quan sát huấn luyện (CMD-TRN-0004)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Hạt giống ngẫu nhiên (random seed) cho tính tái lập",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
        help="Số lần lặp xen kẽ bật/tắt (tối thiểu 5 theo NFR-PERF-001)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Đường dẫn tệp cấu hình huấn luyện YAML",
    )
    parser.add_argument(
        "--total-steps",
        type=int,
        default=None,
        help="Tổng số bước môi trường cho mỗi lượt chạy smoke mở rộng",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="logs/m1/benchmark_train.json",
        help="Đường dẫn tệp kết quả JSON (mặc định logs/m1/benchmark_train.json)",
    )
    parser.add_argument(
        "--runs-dir",
        type=str,
        default=None,
        help="Thư mục lưu trữ các lượt chạy tạm thời",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.9,
        help="Ngưỡng tỷ lệ trung vị đạt chuẩn (mặc định 0.90)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Điểm vào chính của CLI đo đạc hiệu năng giao diện (CMD-TRN-0004).

    Mã thoát:
    - 0: Đạt chuẩn hiệu năng (passed = True, ratio_median >= 0.90).
    - 1: Không đạt chuẩn hiệu năng hoặc xảy ra lỗi huấn luyện trong quá trình đo.
    - 2: Tham số dòng lệnh không hợp lệ (repeats < 5, seed < 0, ...).
    """
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as err:
        return 2 if err.code != 0 else 0

    # Kiểm định hợp lệ tham số
    if args.repeats < 5:
        sys.stderr.write(
            f"Lỗi tham số: số lần lặp (--repeats) phải tối thiểu 5 (nhận {args.repeats})\n"
        )
        sys.stderr.flush()
        return 2

    if args.seed < 0:
        sys.stderr.write(
            f"Lỗi tham số: hạt giống (--seed) không được là số âm (nhận {args.seed})\n"
        )
        sys.stderr.flush()
        return 2

    if args.threshold <= 0:
        sys.stderr.write(
            f"Lỗi tham số: ngưỡng (--threshold) phải lớn hơn 0 (nhận {args.threshold})\n"
        )
        sys.stderr.flush()
        return 2

    if args.config is not None and not Path(args.config).is_file():
        sys.stderr.write(
            f"Lỗi tham số: tệp cấu hình không tồn tại: '{args.config}'\n"
        )
        sys.stderr.flush()
        return 2

    try:
        report, passed = run_benchmark(
            seed=args.seed,
            repeats=args.repeats,
            config_path=args.config,
            total_steps=args.total_steps,
            output_path=args.output,
            runs_dir=args.runs_dir,
            threshold=args.threshold,
        )
    except Exception as run_err:
        sys.stderr.write(f"Lỗi thực thi benchmark: {run_err}\n")
        sys.stderr.flush()
        return 1

    # In báo cáo kết quả tổng hợp bằng tiếng Việt kèm thuật ngữ song ngữ
    summary = (
        f"\n=== Báo cáo chuẩn đo hiệu năng (Benchmark Report) ===\n"
        f"- Hạt giống ngẫu nhiên (seed): {report['seed']}\n"
        f"- Số lần lặp xen kẽ (repeats): {report['repeats']}\n"
        f"- Số bước mỗi lượt (env_steps_per_run): {report['env_steps_per_run']}\n"
        f"- Trung vị giao diện tắt (UI off median): {report['ui_off']['median']:.2f} bước/giây\n"
        f"- Trung vị giao diện bật (UI on median): {report['ui_on']['median']:.2f} bước/giây\n"
        f"- Tỷ lệ trung vị (ratio median): {report['ratio_median']:.4f}\n"
        f"- Ngưỡng yêu cầu (threshold): {report['threshold']:.2f}\n"
        f"- Kết quả đánh giá: {'ĐẠT (PASSED)' if passed else 'KHÔNG ĐẠT (FAILED)'}\n"
        f"- Tệp kết quả: {args.output}\n"
    )
    sys.stdout.write(summary)
    sys.stdout.flush()

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
