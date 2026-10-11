"""Trace: API-PLT-0005 / INV-003 / INV-005 / AC-4."""

from __future__ import annotations

import os
from importlib import import_module, util
from pathlib import Path
from typing import Any

import pytest

from mma_ai.compat.platform_info import PlatformProfile


def _fsio() -> Any:
    module_spec = util.find_spec("mma_ai.compat.fsio")
    assert module_spec is not None, "Thiếu mô-đun fsio cho AC-4"
    return import_module("mma_ai.compat.fsio")


def _profile(kind: str) -> PlatformProfile:
    return PlatformProfile(
        kind=kind,  # type: ignore[arg-type]
        release="test",
        machine="test",
        python_version=(3, 12, 0),
        is_wsl=kind == "wsl2",
        tested=True,
    )


def test_inv_003_atomic_write_replaces_full_destination_and_cleans_temp(tmp_path: Path) -> None:
    fsio = _fsio()
    destination = tmp_path / "record.json"
    destination.write_bytes(b"old")

    fsio.write_bytes_atomic(destination, b'{"ok":true}')

    assert destination.read_bytes() == b'{"ok":true}'
    assert list(tmp_path.iterdir()) == [destination]


def test_inv_005_text_is_utf8_without_bom_and_uses_lf(tmp_path: Path) -> None:
    destination = tmp_path / "record.jsonl"

    _fsio().write_text_atomic(destination, "á\r\nb\rc\n")

    content = destination.read_bytes()
    assert content == "á\nb\nc\n".encode("utf-8")
    assert not content.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in content


def test_inv_003_temp_file_is_in_destination_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fsio = _fsio()
    destination = tmp_path / "nested" / "record.bin"
    destination.parent.mkdir()
    real_replace_atomic = fsio.replace_atomic
    observed: list[tuple[Path, Path]] = []

    def capture(
        source: str | os.PathLike[str],
        target: str | os.PathLike[str],
        **kwargs: object,
    ) -> None:
        observed.append((Path(source).parent, Path(target).parent))
        real_replace_atomic(source, target, **kwargs)

    monkeypatch.setattr(fsio, "replace_atomic", capture)

    fsio.write_bytes_atomic(destination, b"new")

    assert observed == [(destination.parent, destination.parent)]


def test_inv_003_windows_retries_permission_error_then_succeeds(tmp_path: Path) -> None:
    fsio = _fsio()
    source = tmp_path / "source.tmp"
    destination = tmp_path / "destination.bin"
    source.write_bytes(b"new")
    destination.write_bytes(b"old")
    calls = 0
    waits: list[float] = []

    def replace(
        source_path: str | os.PathLike[str],
        destination_path: str | os.PathLike[str],
    ) -> None:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise PermissionError("locked")
        os.replace(source_path, destination_path)

    fsio.replace_atomic(
        source,
        destination,
        sleep=waits.append,
        replace=replace,
        profile=_profile("windows"),
    )

    assert calls == 3
    assert waits == [0.05, 0.10]
    assert destination.read_bytes() == b"new"


def test_inv_003_posix_does_not_retry_permission_error(tmp_path: Path) -> None:
    fsio = _fsio()
    source = tmp_path / "source.tmp"
    destination = tmp_path / "destination.bin"
    source.write_bytes(b"new")
    destination.write_bytes(b"old")
    calls = 0

    def fail_replace(*_: object) -> None:
        nonlocal calls
        calls += 1
        raise PermissionError("locked")

    with pytest.raises(fsio.AtomicWriteError, match="destination.bin"):
        fsio.replace_atomic(
            source, destination, replace=fail_replace, profile=_profile("linux")
        )

    assert calls == 1
    assert destination.read_bytes() == b"old"
    assert not source.exists()


def test_inv_003_write_failures_preserve_old_bytes_and_remove_temp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fsio = _fsio()
    for failure in ("temp-create", "fsync", "replace"):
        destination = tmp_path / f"{failure}.bin"
        destination.write_bytes(b"old")
        with monkeypatch.context() as patcher:
            if failure == "temp-create":
                def fail_create(*_: object, **__: object) -> Any:
                    raise PermissionError("directory is not writable")

                patcher.setattr(fsio.tempfile, "mkstemp", fail_create)
            elif failure == "fsync":
                def fail_sync(*_: object) -> None:
                    raise OSError("interrupted after writing temporary file")

                patcher.setattr(fsio.os, "fsync", fail_sync)
            else:
                def fail_replace(*_: object, **__: object) -> None:
                    raise OSError("replace failed")

                patcher.setattr(fsio, "replace_atomic", fail_replace)

            with pytest.raises(fsio.AtomicWriteError, match=destination.name):
                fsio.write_bytes_atomic(destination, b"new")

        assert destination.read_bytes() == b"old"
        assert [path for path in tmp_path.iterdir() if path.suffix == ".tmp"] == []


def test_inv_003_windows_retry_exhaustion_keeps_destination_and_reports_root_cause(
    tmp_path: Path,
) -> None:
    fsio = _fsio()
    source = tmp_path / "source.tmp"
    destination = tmp_path / "destination.bin"
    source.write_bytes(b"new")
    destination.write_bytes(b"old")
    waits: list[float] = []
    calls = 0

    def fail_replace(*_: object) -> None:
        nonlocal calls
        calls += 1
        raise PermissionError("destination is locked")

    with pytest.raises(
        fsio.AtomicWriteError, match="destination.bin.*destination is locked"
    ) as failure:
        fsio.replace_atomic(
            source,
            destination,
            sleep=waits.append,
            replace=fail_replace,
            profile=_profile("windows"),
        )

    assert calls == 5
    assert sum(waits) <= 1.0
    assert destination.read_bytes() == b"old"
    assert not source.exists()
    assert isinstance(failure.value.__cause__, PermissionError)


def test_inv_003_windows_long_path_error_suggests_enabling_support(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fsio = _fsio()
    source = tmp_path / "source.tmp"
    destination = tmp_path / ("d" * 260)
    source.write_bytes(b"new")
    monkeypatch.setattr(
        fsio,
        "long_paths_enabled",
        lambda *_args, **_kwargs: type("Capability", (), {"available": False})(),
    )

    with pytest.raises(fsio.AtomicWriteError) as error:
        fsio.replace_atomic(
            source,
            destination,
            replace=lambda *_: (_ for _ in ()).throw(OSError("failure")),
            profile=_profile("windows"),
        )

    assert str(len(str(destination))) in str(error.value)
    assert "đường dẫn dài" in str(error.value).lower()
    assert not source.exists()
