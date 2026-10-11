"""Phần mở rộng pytest (pytest plugin) loại test không phù hợp với máy đang chạy."""

from __future__ import annotations

import importlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import pytest

_MARKERS = (
    "display",
    "requires_display",
    "requires_cuda",
    "requires_symlink",
    "windows_only",
    "posix_only",
    "linux_only",
    "macos_only",
)
def _deselection_ratio(deselected: int, collected: int) -> float:
    """Tính tỷ lệ bị loại trên tổng số test đã thu thập."""
    return deselected / collected if collected else 0.0


def _ratio_argument(value: str) -> float:
    try:
        ratio = float(value)
    except ValueError as error:
        raise pytest.UsageError("--capability-max-ratio phải là số từ 0 đến 1") from error
    if not math.isfinite(ratio) or not 0 <= ratio <= 1:
        raise pytest.UsageError("--capability-max-ratio phải là số từ 0 đến 1")
    return ratio


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("cổng năng lực")
    group.addoption(
        "--capability-report",
        metavar="TỆP",
        help="Ghi báo cáo JSON về các test bị loại theo năng lực.",
    )
    group.addoption(
        "--capability-max-ratio",
        type=_ratio_argument,
        default=0.05,
        metavar="TỶ_LỆ",
        help="Tỷ lệ test tối đa được loại, mặc định là 0.05.",
    )


def pytest_configure(config: pytest.Config) -> None:
    descriptions = {
        "display": "Yêu cầu màn hình hiển thị.",
        "requires_display": "Yêu cầu màn hình hiển thị.",
        "requires_cuda": "Yêu cầu CUDA khả dụng.",
        "requires_symlink": "Yêu cầu hệ điều hành hỗ trợ liên kết tượng trưng (symbolic link).",
        "windows_only": "Chỉ chạy trên Windows.",
        "posix_only": "Chỉ chạy trên hệ điều hành POSIX.",
        "linux_only": "Chỉ chạy trên Linux.",
        "macos_only": "Chỉ chạy trên macOS.",
    }
    for marker in _MARKERS:
        config.addinivalue_line("markers", f"{marker}: {descriptions[marker]}")


def _platform_kind() -> str:
    from mma_ai.compat.platform_info import detect_platform

    return detect_platform().kind


def _capability_available(marker: str) -> bool:
    if marker == "requires_display":
        from mma_ai.compat.display import probe_display

        return probe_display().available
    if marker == "requires_cuda":
        try:
            torch = importlib.import_module("torch")
            return bool(torch.cuda.is_available())
        except Exception:
            return False
    if marker == "requires_symlink":
        from mma_ai.compat.capabilities import symlink_supported

        return symlink_supported().available

    kind = _platform_kind()
    return {
        "windows_only": kind == "windows",
        "posix_only": kind in {"linux", "wsl2", "macos"},
        "linux_only": kind in {"linux", "wsl2"},
        "macos_only": kind == "macos",
    }[marker]


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    unavailable: list[tuple[pytest.Item, str, str]] = []
    availability: dict[str, bool] = {}
    for item in items:
        markers = [marker for marker in _MARKERS if item.get_closest_marker(marker)]
        for marker_name in markers:
            marker = item.get_closest_marker(marker_name)
            assert marker is not None
            reason = marker.kwargs.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise pytest.UsageError(
                    f"Marker {marker_name!r} trên {item.nodeid} cần lý do (reason) "
                    "tiếng Việt không rỗng."
                )
            if marker_name == "display":
                continue
            if marker_name not in availability:
                availability[marker_name] = _capability_available(marker_name)
            if not availability[marker_name]:
                unavailable.append((item, marker_name, reason.strip()))
                break

    deselected = [item for item, _, _ in unavailable]
    if deselected:
        config.hook.pytest_deselected(items=deselected)
    items[:] = [item for item in items if item not in deselected]
    collected = len(items) + len(deselected)
    report: dict[str, Any] = {
        "collected": collected,
        "deselected": len(deselected),
        "ratio": _deselection_ratio(len(deselected), collected),
        "items": [
            {"nodeid": item.nodeid, "marker": marker, "reason": reason}
            for item, marker, reason in unavailable
        ],
    }
    setattr(config, "_capability_gate_report", report)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    report = getattr(session.config, "_capability_gate_report", None)
    if report is None:
        return

    report_path = session.config.getoption("--capability-report")
    if report_path:
        try:
            Path(report_path).write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        except OSError as error:
            sys.stderr.write(
                f"CẢNH BÁO: Không ghi được báo cáo năng lực {report_path!r}: {error}\n"
            )
            session.exitstatus = pytest.ExitCode.TESTS_FAILED

    maximum = session.config.getoption("--capability-max-ratio")
    if report["ratio"] > maximum:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: pytest.Config) -> None:
    report = getattr(config, "_capability_gate_report", None)
    if report is None:
        return
    terminalreporter.write_line(
        "Kiểm thử bị loại theo năng lực: "
        f"{report['deselected']}/{report['collected']} "
        f"({report['ratio']:.1%}; giới hạn {config.getoption('--capability-max-ratio'):.1%})."
    )
    for item in report["items"]:
        terminalreporter.write_line(
            f"  {item['nodeid']} [{item['marker']}]: {item['reason']}"
        )
    if report["ratio"] > config.getoption("--capability-max-ratio"):
        terminalreporter.write_line("Tỷ lệ test bị loại vượt ngưỡng cho phép.")
