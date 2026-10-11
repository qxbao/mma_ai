from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest

from mma_ai.compat.capabilities import (
    long_paths_enabled,
    ram_probe,
    symlink_supported,
    utf8_stdio_ok,
)
from mma_ai.compat.platform_info import PlatformProfile


def _profile(kind: Literal["windows", "linux", "wsl2", "macos"]) -> PlatformProfile:
    return PlatformProfile(
        kind=kind,
        release="test",
        machine="test",
        python_version=(3, 12, 0),
        is_wsl=kind == "wsl2",
        tested=True,
    )


def test_inv_004_symlink_probe_reflects_real_os_support(tmp_path: Path) -> None:
    result = symlink_supported(tmp_path)

    assert result.available is (result.reason is None)


def test_inv_004_symlink_probe_reports_oserror_in_vietnamese(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fail_symlink(*args: object, **kwargs: object) -> None:
        raise OSError("permission denied")

    monkeypatch.setattr("pathlib.Path.symlink_to", fail_symlink)

    result = symlink_supported(tmp_path)

    assert result.available is False
    assert result.reason and "symlink" in result.reason.lower()


def test_ac_4_symlink_probe_cleans_up_temporary_entries(tmp_path: Path) -> None:
    result = symlink_supported(tmp_path)

    assert result.available is (result.reason is None)
    assert list(tmp_path.iterdir()) == []


def test_ac_4_long_paths_are_available_off_windows() -> None:
    for kind in ("linux", "wsl2", "macos"):
        result = long_paths_enabled(_profile(kind))

        assert result.available is True
        assert result.reason is None


def test_ac_4_long_paths_reads_windows_registry_value() -> None:
    observed: list[str] = []

    def read_registry(path: str, name: str) -> int:
        observed.append(f"{path}:{name}")
        return 1

    result = long_paths_enabled(_profile("windows"), registry_reader=read_registry)

    assert result.available is True
    assert result.reason is None
    assert observed == [r"SYSTEM\CurrentControlSet\Control\FileSystem:LongPathsEnabled"]


def test_ac_4_windows_long_paths_disabled_is_unavailable() -> None:
    result = long_paths_enabled(_profile("windows"), registry_reader=lambda *_: 0)

    assert result.available is False
    assert result.reason


def test_ac_4_windows_long_paths_unknown_is_unavailable() -> None:
    result = long_paths_enabled(_profile("windows"), registry_reader=lambda *_: None)

    assert result.available is False
    assert result.reason


def test_ac_4_ram_probe_returns_unavailable_when_measurement_fails() -> None:
    result = ram_probe(_profile("linux"), peak_ram_source=lambda: None)

    assert result.available is False
    assert result.reason


def test_ac_4_utf8_stdio_reports_non_utf8_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    class Stream:
        encoding = "cp1252"

    monkeypatch.setattr("sys.stdout", Stream())
    monkeypatch.setattr("sys.stderr", Stream())

    result = utf8_stdio_ok()

    assert result.available is False
    assert result.reason
