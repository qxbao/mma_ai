"""Giao diện dòng lệnh đánh giá chính sách và so sánh đối chuẩn (CMD-EVL-0001, CLI-004).

Hiện thực điểm vào giao diện dòng lệnh (CLI - Command Line Interface) mỏng:
- FR-001, CMD-EVL-0001: Đánh giá chính sách đã học (learned policy) so sánh đối chuẩn
  với chính sách ngẫu nhiên (random policy).
- FR-007, INV-006: Tiêu chí kết luận cố định trong cấu hình, nghiêm cấm mọi cờ ghi đè.
- FR-015, AC-5: Checkpoint lỗi không in chỉ số giả mạo ra đầu ra tiêu chuẩn (stdout).
- FR-018: Quản lý tham số dòng lệnh và áp dụng ghi đè cấu hình (configuration overrides).
- INV-003: Không gian hành động chỉ là kích thích cơ (muscle excitation), cấm cờ nhận lực/toạ độ.
- INV-004: Xử lý ngoại lệ với mã thoát ổn định (exit codes), không để lại kết quả dở dang.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

from mma_ai.compat.stdio import ensure_utf8_stdio
from mma_ai.evaluation.errors import EvalError
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.runner import EvalResult, evaluate_checkpoint

__all__: list[str] = [
    "_build_parser",
    "main",
]


class _EvaluationArgumentParser(argparse.ArgumentParser):
    """Bộ phân tích cú pháp tuỳ biến xuất thông báo lỗi tiếng Việt và thoát mã 2."""

    def error(self, message: str) -> NoReturn:
        """Xử lý lỗi phân tích tham số dòng lệnh, xuất ra stderr và thoát mã 2."""
        sys.stderr.write(
            f"Lỗi tham số dòng lệnh (argument error): {message} "
            f"(tham số --checkpoint là bắt buộc).\n"
        )
        sys.stderr.flush()
        sys.exit(2)


def _build_parser() -> argparse.ArgumentParser:
    """Xây dựng bộ phân tích cú pháp tham số dòng lệnh cho CMD-EVL-0001.

    Bảo vệ các bất biến:
    - INV-006: Tuyệt đối không khai báo cờ ghi đè tiêu chí kết luận (criterion) hay mức tin cậy.
    - INV-003: Tuyệt đối không khai báo cờ nhận hành động thô hay toạ độ tay mục tiêu.
    """
    parser = _EvaluationArgumentParser(
        prog="evaluate",
        description=(
            "Đánh giá chính sách đã học (learned policy) so sánh đối chuẩn với "
            "chính sách ngẫu nhiên (random policy) trên tập mục tiêu kiểm thử (CMD-EVL-0001)."
        ),
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        required=True,
        help="Đường dẫn tệp điểm kiểm tra (.pt) hoặc con trỏ latest.json (bắt buộc)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Đường dẫn tệp cấu hình đánh giá YAML tuỳ biến",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Thư mục xuất kết quả đánh giá (bắt buộc khi checkpoint nằm ngoài thư mục run)",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=None,
        help="Số lần lặp lại (repeats) cho mỗi mục tiêu đánh giá (> 0)",
    )
    parser.add_argument(
        "--eval-seed",
        type=int,
        default=None,
        help="Hạt giống ngẫu nhiên cơ sở (seed base) cho các tập phim đánh giá (>= 0)",
    )
    parser.add_argument(
        "--runs-dir",
        type=str,
        default=None,
        help="Thư mục gốc lưu trữ các phiên chạy huấn luyện",
    )
    return parser


def _format_stat(stat_dict: dict[str, Any] | None, unit: str = "") -> str:
    """Định dạng số liệu thống kê kèm khoảng tin cậy (confidence interval)."""
    if not stat_dict or stat_dict.get("value") is None:
        reason = stat_dict.get("reason") if stat_dict else "không có dữ liệu"
        return f"null ({reason})"

    val = stat_dict["value"]
    ci_low = stat_dict.get("ci_low")
    ci_high = stat_dict.get("ci_high")
    unit_str = f" {unit}" if unit else ""

    if ci_low is not None and ci_high is not None:
        return f"{val:.4f}{unit_str} [95% CI: {ci_low:.4f} ; {ci_high:.4f}]"
    return f"{val:.4f}{unit_str}"


def _print_summary(result: EvalResult) -> None:
    """In tóm tắt kết quả đánh giá bằng tiếng Việt trên stdout (FR-001, CMD-EVL-0001)."""
    report = result.report
    comparison = report.get("comparison", {})
    policies = report.get("policies", {})
    learned = policies.get("learned", {})
    random_pol = policies.get("random", {})
    limits = report.get("limits", [])

    better = comparison.get("better", False)
    diff = comparison.get("difference", 0.0)
    ci_low = comparison.get("ci_low", 0.0)
    ci_high = comparison.get("ci_high", 0.0)
    conf_level = comparison.get("confidence_level", 0.95)

    verdict_text = (
        "Tốt hơn chính sách ngẫu nhiên (better than random)"
        if better
        else "Không tốt hơn chính sách ngẫu nhiên (not better than random)"
    )

    # Tính đường dẫn tương đối của thư mục kết quả
    try:
        rel_eval_dir = str(result.eval_dir.relative_to(Path.cwd())).replace("\\", "/")
    except ValueError:
        rel_eval_dir = str(result.eval_dir).replace("\\", "/")

    lines: list[str] = [
        "============================================================",
        "KẾT QUẢ ĐÁNH GIÁ CHÍNH SÁCH (POLICY EVALUATION SUMMARY)",
        f"Mã đánh giá (eval ID): {result.eval_id}",
        "============================================================",
        f"Kết luận (verdict): {verdict_text}",
        (
            f"Hiệu số tỷ lệ thành công (difference): {diff:+.4f} "
            f"[{conf_level * 100:.1f}% CI: {ci_low:.4f} ; {ci_high:.4f}]"
        ),
        "",
        "--- Chính sách đã học (Learned Policy) ---",
        f"  Tỷ lệ thành công (success rate): {_format_stat(learned.get('success_rate'))}",
        (
            "  Khoảng cách cuối (final distance): "
            f"{_format_stat(learned.get('final_distance_m'), 'm')}"
        ),
        f"  Phần thưởng trung bình (mean return): {_format_stat(learned.get('mean_return'))}",
        f"  Nỗ lực điều khiển (effort): {_format_stat(learned.get('effort'))}",
        f"  Tỷ lệ bất thường (abnormal rate): {_format_stat(learned.get('abnormal_rate'))}",
        "",
        "--- Chính sách ngẫu nhiên (Random Policy) ---",
        f"  Tỷ lệ thành công (success rate): {_format_stat(random_pol.get('success_rate'))}",
        (
            "  Khoảng cách cuối (final distance): "
            f"{_format_stat(random_pol.get('final_distance_m'), 'm')}"
        ),
        f"  Phần thưởng trung bình (mean return): {_format_stat(random_pol.get('mean_return'))}",
        f"  Nỗ lực điều khiển (effort): {_format_stat(random_pol.get('effort'))}",
        f"  Tỷ lệ bất thường (abnormal rate): {_format_stat(random_pol.get('abnormal_rate'))}",
        "",
        "--- Giới hạn kết luận (limits) ---",
    ]

    for limit in limits:
        lines.append(f"- {limit}")

    lines.extend(
        [
            "",
            f"Đường dẫn kết quả (output directory): {rel_eval_dir}",
            "============================================================",
        ]
    )

    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


def main(argv: Sequence[str] | None = None) -> int:
    """Điểm vào chính của giao diện dòng lệnh đánh giá chính sách (CMD-EVL-0001).

    Args:
        argv: Danh sách tham số dòng lệnh tuỳ chọn (mặc định lấy từ sys.argv[1:]).

    Returns:
        int: Mã thoát chuẩn CLI (0 nếu thành công, 1 lỗi không xác định, 2 lỗi tham số,
            4 checkpoint lỗi, 5 rò rỉ tập dữ liệu, 6 thiếu biểu đồ, 7 lỗi ghi đĩa, 130 Ctrl-C).
    """
    ensure_utf8_stdio()
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as err:
        return int(err.code) if err.code is not None else 2

    try:
        # Chuẩn bị từ điển ghi đè cấu hình hợp lệ (INV-006)
        overrides: dict[str, Any] = {}
        if args.repeats is not None:
            overrides["episodes.repeats"] = args.repeats
        if args.eval_seed is not None:
            overrides["seeds.episode_base"] = args.eval_seed
        if args.runs_dir is not None:
            overrides["paths.runs_dir"] = args.runs_dir

        # Nạp cấu hình đánh giá (FR-007, FR-018, API-EVL-0001)
        cfg = EvalConfig.load(
            path=args.config,
            overrides=overrides if overrides else None,
        )

        # Thực thi quy trình điều phối đánh giá 8 bước (API-EVL-0002)
        result = evaluate_checkpoint(
            checkpoint=args.checkpoint,
            cfg=cfg,
            out_dir=args.out,
        )

        # In tóm tắt kết quả thành công ra stdout
        _print_summary(result)

        # Xử lý trường hợp biểu đồ không hoàn tất (mã thoát 6)
        if result.exit_code == 6 or result.status == "done_charts_incomplete":
            chart_reason = result.report.get("charts", {}).get("reason") or "Biểu đồ chưa đầy đủ"
            sys.stderr.write(
                f"Cảnh báo: Đánh giá hoàn tất nhưng biểu đồ chưa hoàn chỉnh: {chart_reason}\n"
            )
            sys.stderr.flush()
            return 6

        return result.exit_code

    except KeyboardInterrupt:
        sys.stderr.write("Đánh giá bị ngắt bởi người dùng (Ctrl-C).\n")
        sys.stderr.flush()
        return 130
    except EvalError as eval_err:
        sys.stderr.write(f"Lỗi đánh giá ({eval_err.__class__.__name__}): {eval_err}\n")
        sys.stderr.flush()
        return eval_err.exit_code
    except Exception as unexpected_err:
        sys.stderr.write(
            f"Lỗi không xác định trong quá trình đánh giá: {unexpected_err}\n"
        )
        sys.stderr.flush()
        return 1


if __name__ == "__main__":
    sys.exit(main())
