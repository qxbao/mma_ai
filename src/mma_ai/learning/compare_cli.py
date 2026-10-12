"""Giao diện dòng lệnh so sánh hai lượt chạy huấn luyện (learning/compare_cli.py).

Hiện thực và đáp ứng các yêu cầu:
- CMD-TRN-0003: Lệnh so sánh hai lượt chạy: python scripts/compare_runs.py RUN_A RUN_B
- FR-014: So sánh tính tái lập (reproducibility) của hai lượt chạy dựa trên hồ sơ (run manifest);
  kiểm tra K điểm đầu của hàm phần thưởng (head_mean_return) theo dung sai tương đối,
  chỉ có ý nghĩa khi so sánh giữa hai lượt chạy cùng loại thiết bị (device kind).
- NFR-REPRO-001: Đảm bảo độ chính xác và tính tái lập xác định của thuật toán.
- Báo cáo kết quả bằng tiếng Việt kèm thuật ngữ song ngữ ở lần xuất hiện đầu tiên.
- Mã thoát (exit code):
  - 0: Trong dung sai tái lập (reproducibility tolerance).
  - 1: Ngoài dung sai tái lập hoặc không thể so sánh (comparable=False).
  - 2: Thiếu tham số, thiếu hoặc hỏng hồ sơ run manifest.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Sequence

from mma_ai.compat.stdio import ensure_utf8_stdio
from mma_ai.learning.manifest import read_manifest
from mma_ai.learning.repro import compare_runs

__all__: list[str] = ["main"]


def _calculate_max_relative_diff(
    first_returns: Sequence[float],
    second_returns: Sequence[float],
) -> float:
    """Tính độ lệch tương đối lớn nhất giữa hai chuỗi điểm phần thưởng đầu kỳ."""
    max_rel_diff = 0.0
    for exp, act in zip(first_returns, second_returns):
        expected = float(exp)
        actual = float(act)
        if not math.isfinite(expected) or not math.isfinite(actual):
            return float("inf")
        diff = abs(actual - expected)
        denom = max(abs(expected), 1e-9)
        rel_diff = diff / denom
        if rel_diff > max_rel_diff:
            max_rel_diff = rel_diff
    return max_rel_diff


def _build_parser() -> argparse.ArgumentParser:
    """Xây dựng bộ phân tích cú pháp dòng lệnh cho CMD-TRN-0003."""
    parser = argparse.ArgumentParser(
        prog="compare_runs",
        description=(
            "So sánh tính tái lập (reproducibility) của hai lượt chạy huấn luyện (CMD-TRN-0003)"
        ),
    )
    parser.add_argument(
        "run_a",
        type=str,
        help="Đường dẫn thư mục lượt chạy thứ nhất (run A)",
    )
    parser.add_argument(
        "run_b",
        type=str,
        help="Đường dẫn thư mục lượt chạy thứ hai (run B)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Điểm vào chính của CLI so sánh lượt chạy (CMD-TRN-0003).

    Tham số:
        argv: Danh sách tham số dòng lệnh (mặc định lấy từ sys.argv[1:]).

    Trả về:
        Mã thoát nguyên:
        - 0 khi trong dung sai tái lập.
        - 1 khi ngoài dung sai hoặc không thể so sánh được.
        - 2 khi tham số không hợp lệ, thiếu hoặc hỏng hồ sơ run manifest.
    """
    ensure_utf8_stdio()
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as err:
        # Khi parse_args thất bại (ví dụ thiếu tham số hoặc --help),
        # nếu thoát với mã khác 0 thì trả về mã 2 theo quy ước CMD-TRN-0003.
        return 2 if err.code != 0 else 0

    run_a_path = Path(args.run_a)
    run_b_path = Path(args.run_b)

    # Đọc và kiểm tra hồ sơ thí nghiệm (run manifest) của cả hai lượt chạy
    try:
        manifest_a = read_manifest(run_a_path)
    except Exception as err:
        sys.stderr.write(
            f"Lỗi đọc hồ sơ lượt chạy A tại '{run_a_path}': {err}\n"
        )
        sys.stderr.flush()
        return 2

    try:
        manifest_b = read_manifest(run_b_path)
    except Exception as err:
        sys.stderr.write(
            f"Lỗi đọc hồ sơ lượt chạy B tại '{run_b_path}': {err}\n"
        )
        sys.stderr.flush()
        return 2

    # Trích xuất thông tin thiết bị và dung sai từ hồ sơ
    repro_a = manifest_a.get("reproducibility", {})
    if not isinstance(repro_a, Mapping):
        repro_a = {}
    device_a = manifest_a.get("device", {})
    if not isinstance(device_a, Mapping):
        device_a = {}

    device_kind = repro_a.get("device_kind") or device_a.get("kind", "không xác định")
    tolerance = repro_a.get("rel_tolerance", 1e-6)

    returns_a = (
        manifest_a.get("reward_metrics", {}).get("head_mean_return")
        if isinstance(manifest_a.get("reward_metrics"), Mapping)
        else None
    )
    returns_b = (
        manifest_b.get("reward_metrics", {}).get("head_mean_return")
        if isinstance(manifest_b.get("reward_metrics"), Mapping)
        else None
    )

    k_points = (
        min(len(returns_a), len(returns_b))
        if isinstance(returns_a, list) and isinstance(returns_b, list)
        else 0
    )

    # Thực hiện so sánh qua hàm lõi thuần (pure core) compare_runs
    try:
        report = compare_runs(run_a_path, run_b_path)
    except Exception as err:
        sys.stderr.write(f"Lỗi trong quá trình so sánh: {err}\n")
        sys.stderr.flush()
        return 2

    # Trường hợp 1: Không thể so sánh được (ví dụ khác loại thiết bị, thư viện, luồng)
    if not report.comparable:
        sys.stdout.write(
            f"Kết quả so sánh: Không thể so sánh (incomparable)\n"
            f"Lý do: {report.reason or 'Không xác định'}\n"
            f"Loại thiết bị (device kind): {device_kind}\n"
        )
        sys.stdout.flush()
        return 1

    # Tính toán độ lệch tương đối lớn nhất nếu có dữ liệu hợp lệ
    max_rel_diff = 0.0
    if isinstance(returns_a, list) and isinstance(returns_b, list) and k_points > 0:
        max_rel_diff = _calculate_max_relative_diff(returns_a[:k_points], returns_b[:k_points])

    # Trường hợp 2: Có thể so sánh được nhưng lệch vượt dung sai
    if report.matches is False:
        sys.stdout.write(
            f"Kết quả so sánh: Ngoài dung sai tái lập (outside tolerance)\n"
            f"Số điểm đầu (K): {k_points}\n"
            f"Dung sai tương đối (relative tolerance): {tolerance:g}\n"
            f"Loại thiết bị (device kind): {device_kind}\n"
            f"Độ lệch tương đối lớn nhất: {max_rel_diff:g}\n"
            f"Chi tiết: {report.reason or 'Dữ liệu không khớp'}\n"
        )
        sys.stdout.flush()
        return 1

    # Trường hợp 3: Trong dung sai tái lập (thành công)
    sys.stdout.write(
        f"Kết quả so sánh: Trong dung sai tái lập (within tolerance)\n"
        f"Số điểm đầu (K): {k_points}\n"
        f"Dung sai tương đối (relative tolerance): {tolerance:g}\n"
        f"Loại thiết bị (device kind): {device_kind}\n"
        f"Độ lệch tương đối lớn nhất: {max_rel_diff:g}\n"
        f"Trạng thái: Hai lượt chạy tái lập thành công.\n"
    )
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
