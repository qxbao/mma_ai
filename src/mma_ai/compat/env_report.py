"""Trace: CMD-PLT-0001 / API-PLT-0008 / FR-017 / FR-024 / AC-5."""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any

from mma_ai.compat.capabilities import (
    Capability,
    long_paths_enabled,
    ram_probe,
    symlink_supported,
    utf8_stdio_ok,
)
from mma_ai.compat.display import probe_display
from mma_ai.compat.platform_info import PlatformProfile, detect_platform
from mma_ai.compat.stdio import ensure_utf8_stdio

_REQUIRED_RANGE = ">=3.11,<3.13"
_PACKAGES = {
    "mujoco": "mujoco",
    "myo_sim": "myo-sim",
    "gymnasium": "gymnasium",
    "numpy": "numpy",
    "torch": "torch",
}
_LABELS = {
    "python_version": "Phiên bản Python",
    "package_mujoco": "Gói mujoco",
    "package_myo_sim": "Gói myo-sim",
    "package_gymnasium": "Gói gymnasium",
    "package_numpy": "Gói numpy",
    "package_torch": "Gói torch",
    "tested_configuration": "Cấu hình đã kiểm",
    "display": "Màn hình hiển thị",
    "symlink": "Tạo symlink",
    "long_paths": "Đường dẫn dài",
    "ram_peak": "Đo RAM đỉnh",
    "utf8_stdio": "Đầu ra UTF-8",
    "wsl_windows_drive": "Thư mục run trên ổ Windows gắn vào WSL2",
}


def _package_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None
    except Exception:
        return None


def _capability(value: Any, fallback: str) -> dict[str, bool | str | None]:
    try:
        available = bool(value.available)
        reason = value.reason
        if available:
            return {"available": True, "reason": None}
        if not isinstance(reason, str) or not reason.strip():
            reason = fallback
        reason = re.sub(r"(?<![\w:])/(?:[^\s,;]+)", "[đường dẫn]", reason)
        reason = re.sub(r"\b[A-Za-z]:\\(?:[^\s,;]+)", "[đường dẫn]", reason)
        return {"available": False, "reason": reason}
    except Exception:
        return {"available": False, "reason": fallback}


def _check(check_id: str, status: str, message: str) -> dict[str, str]:
    return {"id": check_id, "status": status, "message": message}


def _probe_capabilities(profile: PlatformProfile) -> dict[str, Capability]:
    functions: dict[str, Any] = {
        "display": probe_display,
        "symlink": symlink_supported,
        "long_paths": long_paths_enabled,
        "ram_peak": ram_probe,
        "utf8_stdio": utf8_stdio_ok,
    }
    results: dict[str, Capability] = {}
    for key, function in functions.items():
        try:
            results[key] = (
                function(profile)
                if key in {"display", "long_paths", "ram_peak"}
                else function()
            )
        except Exception as error:
            results[key] = Capability(False, f"Không thể kiểm tra năng lực: {error}")
    return results


def _torch_device(version: str | None, injected: Any = None) -> dict[str, str | None] | None:
    if version is None:
        return None
    try:
        torch = injected if injected is not None else importlib.import_module("torch")
        if bool(torch.cuda.is_available()):
            return {"kind": "cuda", "name": str(torch.cuda.get_device_name(0))}
        return {"kind": "cpu", "name": None}
    except Exception:
        return None


def build_environment_report(
    profile: PlatformProfile | None = None,
    *,
    probes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Tạo báo cáo tương thích môi trường mà không để lỗi phép dò thoát ra ngoài."""
    selected = profile if profile is not None else detect_platform()
    injected = probes or {}
    packages_in = injected.get("packages", {})
    packages: dict[str, str | None] = {}
    for key, distribution in _PACKAGES.items():
        try:
            value = packages_in[key] if key in packages_in else _package_version(distribution)
            packages[key] = str(value) if value is not None else None
        except Exception:
            packages[key] = None

    caps_in = injected.get("capabilities", injected)
    detected: dict[str, Any] = {}
    defaults = _probe_capabilities(selected) if probes is None else {}
    for key in ("display", "symlink", "long_paths", "ram_peak", "utf8_stdio"):
        raw = caps_in.get(
            key, defaults.get(key, Capability(False, "Không kiểm tra được năng lực này."))
        )
        detected[key] = _capability(raw, "Không xác định được trạng thái năng lực.")

    major, minor, micro = selected.python_version
    version = f"{major}.{minor}.{micro}"
    supported = (3, 11) <= (major, minor) < (3, 13)
    checks = [
        _check(
            "python_version",
            "ok" if supported else "fail",
            f"Python {version} nằm trong khoảng yêu cầu {_REQUIRED_RANGE}."
            if supported
            else f"Python {version} nằm ngoài khoảng yêu cầu {_REQUIRED_RANGE}.",
        )
    ]
    for key, distribution in _PACKAGES.items():
        value = packages[key]
        check_id = f"package_{key}"
        if value is not None:
            status = "ok"
            message = f"{distribution} {value}."
        elif key == "torch":
            status = "warn"
            message = (
                "Chưa cài torch (extra rl): không huấn luyện được; cài bằng uv sync --extra rl."
            )
        elif key == "myo_sim":
            status = "fail"
            message = "Chưa cài myo-sim; cài các phụ thuộc dự án trước khi chạy mô phỏng."
        else:
            status = "fail"
            message = f"Chưa cài {distribution}; cài các phụ thuộc dự án trước khi chạy."
        checks.append(_check(check_id, status, message))
    if not selected.tested:
        checks.append(
            _check(
                "tested_configuration",
                "warn",
                "Cấu hình OS/kiến trúc này chưa thuộc cấu hình đã kiểm.",
            )
        )
    for key, value in detected.items():
        status = "ok" if value["available"] else "warn"
        message = "Năng lực khả dụng." if value["available"] else str(value["reason"])
        checks.append(_check(key, status, message))
    cwd = str(injected.get("cwd", os.getcwd()))
    if (
        selected.kind == "wsl2"
        and len(cwd) >= 6
        and cwd[:5].lower() == "/mnt/"
        and cwd[5:6].isalpha()
    ):
        checks.append(
            _check(
                "wsl_windows_drive",
                "warn",
                "Thư mục làm việc nằm trên ổ Windows gắn vào WSL2; thao tác tệp có thể chậm.",
            )
        )
    torch_device = _torch_device(packages["torch"], injected.get("torch"))
    if packages["torch"] is not None and torch_device is None:
        checks.append(
            _check("package_torch", "warn", "Đã cài torch nhưng không đọc được thiết bị tính toán.")
        )
    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "os": {
            "kind": selected.kind,
            "release": selected.release or "unknown",
            "machine": selected.machine or "unknown",
            "is_wsl": selected.is_wsl,
            "tested": selected.tested,
        },
        "python": {"version": version, "supported": supported, "required_range": _REQUIRED_RANGE},
        "packages": packages,
        "torch_device": torch_device,
        "capabilities": detected,
        "checks": checks,
        "overall": "fail" if any(check["status"] == "fail" for check in checks) else "ok",
    }
    return report


def render_text(report: Mapping[str, Any]) -> str:
    """Định dạng báo cáo thành các dòng tiếng Việt cho người vận hành."""
    lines: list[str] = []
    for check in report["checks"]:
        status = check["status"]
        prefix = {"ok": "[ok]", "warn": "[CẢNH BÁO]", "fail": "[LỖI]"}[status]
        label = _LABELS.get(check["id"], check["id"])
        lines.append(f"{prefix} {label}: {check['message']}")
    conclusion = (
        "Môi trường đạt yêu cầu." if report["overall"] == "ok" else "Môi trường chưa đạt yêu cầu."
    )
    lines.append(conclusion)
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Chạy lệnh kiểm môi trường ở biên I/O."""
    ensure_utf8_stdio()
    arguments = list(sys.argv[1:] if argv is None else argv)
    unknown = [argument for argument in arguments if argument != "--json"]
    if unknown:
        print(f"Cờ không được hỗ trợ: {unknown[0]}", file=sys.stderr)
        return 2
    report = build_environment_report()
    if "--json" in arguments:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
        print("Đã hoàn tất kiểm tra môi trường.", file=sys.stderr)
    else:
        print(render_text(report), end="")
    return 1 if report["overall"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
