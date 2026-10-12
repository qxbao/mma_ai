"""Kiểm thử tạo thư mục lần chạy và bất biến INV-001."""

import re
from pathlib import Path
from typing import Any

import pytest

from mma_ai.learning import run_dir
from mma_ai.learning.errors import RunDirError

_REAL_DATETIME: Any = getattr(run_dir, "datetime")


def test_003_inv_001_unique_dirs_no_overwrite(tmp_path: Path, monkeypatch: Any) -> None:
    """FR-011 INV-001: hai lần gọi cùng giây không ghi đè dữ liệu cũ."""
    class FixedDateTime:
        @classmethod
        def now(cls: Any, tz: Any = None) -> Any:
            return _REAL_DATETIME(2026, 10, 9, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(run_dir, "datetime", FixedDateTime)
    first = run_dir.create_run_dir(tmp_path, "elbow", 42)
    (first.path / "marker").write_text("giữ nguyên", encoding="utf-8")
    second = run_dir.create_run_dir(tmp_path, "elbow", 42)
    assert first.path != second.path
    assert (first.path / "marker").read_text(encoding="utf-8") == "giữ nguyên"
    assert (second.path / "checkpoints").is_dir()
    assert (second.path / "tb").is_dir()


def test_003_inv_001_collision_suffix_and_limit(tmp_path: Path, monkeypatch: Any) -> None:
    class FixedDateTime:
        @classmethod
        def now(cls: Any, tz: Any = None) -> Any:
            return _REAL_DATETIME(2026, 10, 9, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(run_dir, "datetime", FixedDateTime)
    for suffix in range(0, 101):
        name = "20261009T120000Z_elbow_s42" + ("" if suffix == 0 else f"-{suffix + 1}")
        (tmp_path / name).mkdir()
    with pytest.raises(RunDirError):
        run_dir.create_run_dir(tmp_path, "elbow", 42)


def test_003_fr_011_run_id_format(tmp_path: Path, monkeypatch: Any) -> None:
    class FixedDateTime:
        @classmethod
        def now(cls: Any, tz: Any = None) -> Any:
            return _REAL_DATETIME(2026, 10, 9, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(run_dir, "datetime", FixedDateTime)
    result = run_dir.create_run_dir(tmp_path, "elbow", 42)
    assert re.fullmatch(r"\d{8}T\d{6}Z_elbow_s42(?:-\d+)?", result.run_id)
    assert result.relative_path == result.path.relative_to(tmp_path)


def test_006_inv_004_long_path_error_cleans_partial_run(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """006 INV-004: lỗi đường dẫn dài có hướng dẫn và dọn thư mục tạo dở."""
    from mma_ai.compat.capabilities import Capability

    class FixedDateTime:
        @classmethod
        def now(cls: Any, tz: Any = None) -> Any:
            return _REAL_DATETIME(2026, 10, 9, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(run_dir, "datetime", FixedDateTime)
    monkeypatch.setattr(
        run_dir, "long_paths_enabled", lambda *_args: Capability(False, "tắt"), raising=False
    )
    root = tmp_path / ("r" * 235)
    real_mkdir = Path.mkdir
    attempted: list[Path] = []

    def fail_after_create(path: Path, *args: Any, **kwargs: Any) -> None:
        real_mkdir(path, *args, **kwargs)
        if path.parent == root:
            attempted.append(path)
            raise OSError("File name too long")

    monkeypatch.setattr(Path, "mkdir", fail_after_create)
    with pytest.raises(RunDirError, match=r"260|đường dẫn dài") as error:
        run_dir.create_run_dir(root, "elbow", 42)
    assert "Windows" in str(error.value)
    assert attempted and not attempted[0].exists()


def test_006_inv_001_run_id_is_portable_and_casefold_unique(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """006 INV-001: tên chạy tương thích Windows, Linux, macOS."""
    class FixedDateTime:
        @classmethod
        def now(cls: Any, tz: Any = None) -> Any:
            return _REAL_DATETIME(2026, 10, 9, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(run_dir, "datetime", FixedDateTime)
    first = run_dir.create_run_dir(tmp_path, "elbow", 42)
    second = run_dir.create_run_dir(tmp_path, "elbow", 42)
    assert re.fullmatch(r"[A-Za-z0-9_-]+", first.run_id)
    assert re.fullmatch(r"[A-Za-z0-9_-]+", second.run_id)
    assert first.run_id.casefold() != second.run_id.casefold()
