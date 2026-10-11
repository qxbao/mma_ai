"""Mô-đun nhận diện hồ sơ nền tảng (platform profile detection).

Cung cấp PlatformProfile và detect_platform() theo hợp đồng API-006:
- API-PLT-0001: Hàm detect_platform() trả về PlatformProfile bất biến.
- FR-002: Lớp tương thích (compatibility layer) duy nhất phân loại hệ điều hành.
- FR-003: Không nhập thư viện gắn riêng từng hệ điều hành ở mức mô-đun.
- INV-001: Đảm bảo tính nhất quán của dữ liệu trên mọi môi trường.
- AC-1, AC-5: Hỗ trợ vận hành đa nền tảng và kiểm tra môi trường check_env.
"""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from typing import Any, Literal, Mapping

PlatformKind = Literal["windows", "linux", "wsl2", "macos"]


@dataclass(frozen=True)
class PlatformProfile:
    """Hồ sơ nền tảng bất biến (immutable platform profile).

    Được đóng băng (frozen) để bảo vệ bất biến INV-001, ngăn ngừa sửa đổi
    trạng thái cấu hình sau khi nhận diện.
    """

    kind: PlatformKind
    release: str
    machine: str
    python_version: tuple[int, int, int]
    is_wsl: bool
    tested: bool


def detect_platform(
    *,
    sys_platform: str | None = None,
    release: str | None = None,
    machine: str | None = None,
    environ: Mapping[str, str] | None = None,
    **extra_kwargs: Any,
) -> PlatformProfile:
    """Nhận diện hệ điều hành và các thông số nền tảng (API-PLT-0001).

    Tham số được thiết kế dạng tiêm phụ thuộc (dependency injection) để kiểm thử
    mọi nhánh hệ điều hành trên bất kỳ môi trường nào (FR-023).

    Hàm bảo đảm không ném ngoại lệ với bất kỳ đầu vào lạ nào, tự động rơi về
    dự phòng an toàn (safe fallback) với kind='linux' và tested=False.
    """
    try:
        # Chuẩn hoá sys_platform
        raw_platform: str
        if sys_platform is None:
            raw_platform = sys.platform
        elif isinstance(sys_platform, str):
            raw_platform = sys_platform
        else:
            raw_platform = str(sys_platform)

        clean_plat = raw_platform.strip().lower()

        # Chuẩn hoá release
        raw_release: str
        if release is None:
            raw_release = platform.release()
        elif isinstance(release, str):
            raw_release = release
        else:
            raw_release = str(release)

        # Chuẩn hoá machine
        raw_machine: str
        if machine is None:
            raw_machine = platform.machine()
        elif isinstance(machine, str):
            raw_machine = machine
        else:
            raw_machine = str(machine)

        # Chuẩn hoá environ
        env: Mapping[str, str]
        if environ is None:
            env = os.environ
        elif isinstance(environ, Mapping):
            env = environ
        else:
            env = {}

        # Lấy python_version mặc định
        py_ver = (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)

        # 1. Nhánh Windows gốc
        if clean_plat in {"win32", "windows", "cygwin", "msys"} or clean_plat.startswith("win"):
            mach_clean = raw_machine.strip().lower()
            is_untested_win = mach_clean in {"arm64", "aarch64"}
            return PlatformProfile(
                kind="windows",
                release=raw_release,
                machine=raw_machine,
                python_version=py_ver,
                is_wsl=False,
                tested=not is_untested_win,
            )

        # 2. Nhánh macOS
        if clean_plat in {"darwin", "macos"} or clean_plat.startswith("darwin"):
            mach_clean = raw_machine.strip().lower()
            is_untested_mac = mach_clean in {"x86_64", "amd64", "i386", "x86", "i686"}
            return PlatformProfile(
                kind="macos",
                release=raw_release,
                machine=raw_machine,
                python_version=py_ver,
                is_wsl=False,
                tested=not is_untested_mac,
            )

        # 3. Nhánh Linux và WSL2
        if clean_plat in {"linux", "linux2"} or clean_plat.startswith("linux"):
            rel_lower = raw_release.lower()
            is_wsl = (
                "microsoft" in rel_lower
                or "wsl" in rel_lower
                or bool(env.get("WSL_DISTRO_NAME"))
            )
            return PlatformProfile(
                kind="wsl2" if is_wsl else "linux",
                release=raw_release,
                machine=raw_machine,
                python_version=py_ver,
                is_wsl=is_wsl,
                tested=True,
            )

        # 4. Dự phòng khi hệ điều hành lạ không nhận diện được
        return PlatformProfile(
            kind="linux",
            release=raw_release,
            machine=raw_machine,
            python_version=py_ver,
            is_wsl=False,
            tested=False,
        )

    except Exception:
        # Bắt mọi lỗi bất thường từ kiểu dữ liệu để tuân thủ hợp đồng cấm ném ngoại lệ
        return PlatformProfile(
            kind="linux",
            release=str(release) if release is not None else "",
            machine=str(machine) if machine is not None else "",
            python_version=(sys.version_info.major, sys.version_info.minor, sys.version_info.micro),
            is_wsl=False,
            tested=False,
        )


__all__ = ["PlatformKind", "PlatformProfile", "detect_platform"]
