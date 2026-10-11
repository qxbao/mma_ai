"""Bộ kiểm thử đơn vị cho lớp nhận diện nền tảng (platform detection).

Kiểm chứng các hợp đồng và yêu cầu:
- API-PLT-0001: Hợp đồng detect_platform() trả về PlatformProfile bất biến.
- FR-002: Lớp tương thích duy nhất nhận diện windows, linux, wsl2, macos.
- INV-001: Tính nhất quán của đầu ra và mô hình dữ liệu trên mọi nền tảng.
- AC-1: Chạy được và tương thích đa nền tảng cho các lệnh CLI.
- AC-5: Cung cấp thông tin nền tảng chính xác phục vụ báo cáo môi trường check_env.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from mma_ai.compat.platform_info import PlatformProfile, detect_platform


def test_four_kinds_from_injected_inputs() -> None:
    """API-PLT-0001, FR-002, AC-1: Nhận diện đúng 4 loại nền tảng qua tham số tiêm.

    Kiểm tra nhận diện windows, linux, wsl2, macos mà không phụ thuộc vào hệ điều hành thực tế.
    """
    # 1. Hệ điều hành Windows (Windows OS)
    win_profile = detect_platform(
        sys_platform="win32",
        release="10.0.22631",
        machine="AMD64",
        environ={},
    )
    assert win_profile.kind == "windows"
    assert win_profile.is_wsl is False
    assert win_profile.tested is True
    assert win_profile.machine == "AMD64"
    assert win_profile.release == "10.0.22631"

    # Kiểm tra biến thể chuỗi "windows"
    win_alias = detect_platform(
        sys_platform="windows",
        release="10.0.22631",
        machine="x86_64",
        environ={},
    )
    assert win_alias.kind == "windows"
    assert win_alias.is_wsl is False
    assert win_alias.tested is True

    # 2. Hệ điều hành Linux chuẩn (Standard Linux)
    linux_profile = detect_platform(
        sys_platform="linux",
        release="5.15.0-generic",
        machine="x86_64",
        environ={},
    )
    assert linux_profile.kind == "linux"
    assert linux_profile.is_wsl is False
    assert linux_profile.tested is True
    assert linux_profile.machine == "x86_64"

    # 3. Môi trường WSL2 trên Windows (WSL2 environment)
    wsl_profile = detect_platform(
        sys_platform="linux",
        release="5.15.153.1-microsoft-standard-WSL2",
        machine="x86_64",
        environ={},
    )
    assert wsl_profile.kind == "wsl2"
    assert wsl_profile.is_wsl is True
    assert wsl_profile.tested is True

    # 4. Hệ điều hành macOS Apple Silicon (macOS on ARM64)
    macos_profile = detect_platform(
        sys_platform="darwin",
        release="23.4.0",
        machine="arm64",
        environ={},
    )
    assert macos_profile.kind == "macos"
    assert macos_profile.is_wsl is False
    assert macos_profile.tested is True
    assert macos_profile.machine == "arm64"


def test_wsl2_detected_by_release_or_distro_env() -> None:
    """API-PLT-0001, FR-002, AC-5: WSL2 nhận diện qua release hoặc biến WSL_DISTRO_NAME.

    Bảo đảm quy tắc nhất quán: os.kind == "wsl2" tương đương hai chiều với is_wsl.
    """
    # Nhận diện qua release chứa "microsoft"
    p_release_ms = detect_platform(
        sys_platform="linux",
        release="5.10.16.3-microsoft-standard-WSL2",
        environ={},
    )
    assert p_release_ms.kind == "wsl2"
    assert p_release_ms.is_wsl is True

    # Nhận diện qua release chứa "WSL"
    p_release_wsl = detect_platform(
        sys_platform="linux",
        release="6.6.36.6-WSL2-azure-x86_64",
        environ={},
    )
    assert p_release_wsl.kind == "wsl2"
    assert p_release_wsl.is_wsl is True

    # Nhận diện qua biến môi trường WSL_DISTRO_NAME khi release là nhân Linux chuẩn
    p_env = detect_platform(
        sys_platform="linux",
        release="5.15.0-generic",
        environ={"WSL_DISTRO_NAME": "Ubuntu-22.04"},
    )
    assert p_env.kind == "wsl2"
    assert p_env.is_wsl is True

    # Linux thuần không có release WSL hay biến WSL_DISTRO_NAME
    p_pure_linux = detect_platform(
        sys_platform="linux",
        release="5.15.0-generic",
        environ={},
    )
    assert p_pure_linux.kind == "linux"
    assert p_pure_linux.is_wsl is False

    # Khi sys_platform là Windows gốc, biến WSL_DISTRO_NAME không làm biến thành wsl2
    p_win_env = detect_platform(
        sys_platform="win32",
        release="10.0.22631",
        environ={"WSL_DISTRO_NAME": "Ubuntu-22.04"},
    )
    assert p_win_env.kind == "windows"
    assert p_win_env.is_wsl is False


def test_untested_configurations_flagged() -> None:
    """API-PLT-0001, AC-5: Gắn cờ tested=False cho Windows ARM64 và macOS Intel.

    Bảo đảm các kiến trúc không có wheel chính thức hoặc chưa kiểm nghiệm được đánh dấu rõ ràng.
    """
    # Windows trên kiến trúc ARM64 (Windows ARM64) -> tested=False
    p_win_arm64 = detect_platform(
        sys_platform="win32",
        machine="ARM64",
        environ={},
    )
    assert p_win_arm64.kind == "windows"
    assert p_win_arm64.tested is False

    p_win_aarch64 = detect_platform(
        sys_platform="win32",
        machine="aarch64",
        environ={},
    )
    assert p_win_aarch64.kind == "windows"
    assert p_win_aarch64.tested is False

    # macOS trên kiến trúc Intel (macOS x86_64) -> tested=False
    p_mac_intel = detect_platform(
        sys_platform="darwin",
        machine="x86_64",
        environ={},
    )
    assert p_mac_intel.kind == "macos"
    assert p_mac_intel.tested is False

    p_mac_amd64 = detect_platform(
        sys_platform="darwin",
        machine="amd64",
        environ={},
    )
    assert p_mac_amd64.kind == "macos"
    assert p_mac_amd64.tested is False

    # Cấu hình đã kiểm: Windows x86_64 / AMD64 và macOS Apple Silicon (arm64)
    p_win_x64 = detect_platform(
        sys_platform="win32",
        machine="AMD64",
        environ={},
    )
    assert p_win_x64.tested is True

    p_mac_arm = detect_platform(
        sys_platform="darwin",
        machine="arm64",
        environ={},
    )
    assert p_mac_arm.tested is True


def test_detect_never_raises() -> None:
    """API-PLT-0001, INV-001: Không ném ngoại lệ với đầu vào lạ, rơi về fallback an toàn.

    Khi gặp giá trị không xác định hoặc kiểu dữ liệu bất thường, trả về linux với tested=False.
    """
    # Đầu vào chuỗi hệ điều hành lạ (unknown OS string)
    p_unknown = detect_platform(
        sys_platform="freebsd",
        release="13.2-RELEASE",
        machine="amd64",
    )
    assert p_unknown.kind == "linux"
    assert p_unknown.is_wsl is False
    assert p_unknown.tested is False

    # Đầu vào rỗng (empty string)
    p_empty = detect_platform(sys_platform="", release="", machine="")
    assert p_empty.kind == "linux"
    assert p_empty.tested is False

    # Đầu vào các kiểu dữ liệu dị thường (unusual input types)
    weird_kwargs: dict[str, Any] = {
        "sys_platform": 12345,
        "release": ["strange", "list"],
        "machine": {"key": "val"},
        "environ": "not-a-mapping",
    }
    p_weird = detect_platform(**weird_kwargs)
    assert p_weird.kind == "linux"
    assert p_weird.is_wsl is False
    assert p_weird.tested is False
    assert isinstance(p_weird.release, str)
    assert isinstance(p_weird.machine, str)
    assert isinstance(p_weird.python_version, tuple)
    assert len(p_weird.python_version) == 3


def test_platform_profile_frozen_immutability() -> None:
    """INV-001: Đảm bảo PlatformProfile là đối tượng bất biến (frozen dataclass)."""
    profile = detect_platform(sys_platform="win32", machine="AMD64")
    with pytest.raises(FrozenInstanceError):
        # Thử thay đổi thuộc tính sau khi khởi tạo trên frozen dataclass
        profile.kind = "linux"  # type: ignore[misc]


def test_detect_platform_defaults_returns_valid_profile() -> None:
    """API-PLT-0001, FR-002: detect_platform() mặc định trả về hồ sơ hợp lệ từ hệ thống."""
    profile = detect_platform()
    assert isinstance(profile, PlatformProfile)
    assert profile.kind in {"windows", "linux", "wsl2", "macos"}
    assert isinstance(profile.release, str)
    assert isinstance(profile.machine, str)
    assert isinstance(profile.python_version, tuple)
    assert len(profile.python_version) == 3
    assert all(isinstance(v, int) for v in profile.python_version)
    assert profile.is_wsl == (profile.kind == "wsl2")
    assert isinstance(profile.tested, bool)
