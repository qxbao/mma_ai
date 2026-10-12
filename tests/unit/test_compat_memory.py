"""Kiểm thử tương thích phép đo RAM (AC-2, INV-002, INV-007)."""

from __future__ import annotations

import pytest

from mma_ai.compat.memory import peak_ram_mb, ram_mib_from_raw
from mma_ai.compat.platform_info import PlatformKind, PlatformProfile


def _profile(kind: PlatformKind) -> PlatformProfile:
    return PlatformProfile(
        kind=kind, release="release", machine="machine",
        python_version=(3, 11, 0), is_wsl=kind == "wsl2", tested=True,
    )


def test_linux_kib_to_mib() -> None:
    """NFR-RAM-001: Linux đổi 262 144 KiB thành 256 MiB."""
    assert ram_mib_from_raw(262_144, "linux") == pytest.approx(256.0, abs=0.001)


def test_macos_bytes_to_mib() -> None:
    """NFR-RAM-001: macOS đổi 268 435 456 byte thành 256 MiB."""
    assert ram_mib_from_raw(268_435_456, "macos") == 256.0


def test_windows_bytes_to_mib() -> None:
    """NFR-RAM-001: Windows đổi 268 435 456 byte thành 256 MiB."""
    assert ram_mib_from_raw(268_435_456, "windows") == 256.0


def test_invalid_raw_raises() -> None:
    for raw in (-1.0, float("nan"), float("inf"), -float("inf")):
        with pytest.raises(ValueError, match="[0-9]|nan|inf"):
            ram_mib_from_raw(raw, "linux")


def test_failure_returns_none_not_zero() -> None:
    def fail() -> float:
        raise OSError("không đo được")

    assert peak_ram_mb(_profile("linux"), linux_source=fail) is None


def test_macos_peak_source_is_injectable() -> None:
    assert peak_ram_mb(
        _profile("macos"), macos_source=lambda: 268_435_456,
    ) == 256.0


def test_linux_formula_unchanged() -> None:
    assert ram_mib_from_raw(1_048_576, "linux") == 1024.0


def test_peak_does_not_import_resource_on_windows_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins
    from types import ModuleType

    original_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == "resource":
            raise AssertionError("Không được nạp resource trên Windows")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    assert peak_ram_mb(
        _profile("windows"), windows_source=lambda: 268_435_456,
    ) == 256.0


def test_inv_007_conversion_property_for_generated_values() -> None:
    """INV-007: quy đổi giữ đúng hệ số trên nhiều số đo hữu hạn được sinh."""
    import random

    rng = random.Random(602)
    for kind, scale in (("linux", 1024), ("macos", 1024 * 1024), ("windows", 1024 * 1024)):
        for _ in range(200):
            expected = rng.uniform(0.001, 10**12)
            assert ram_mib_from_raw(expected * scale, kind) == pytest.approx(expected, rel=1e-12)
