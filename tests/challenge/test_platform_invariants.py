"""Thử thách bất biến (challenge) đa nền tảng INV-003..INV-007 của feature 006 (T639).

Mỗi test nhắm một bất biến của sản phẩm qua đầu vào mà người dùng/hệ thống gặp được: tiêm lỗi
(fault injection) ở từng bước ghi, ngoại lệ lạ của GLFW/Registry/ctypes, chuỗi đường dẫn ngẫu nhiên
có hạt giống cố định, và chạy `pytest` con để soi cổng năng lực. Ca đỏ (finding) KHÔNG nằm ở đây vì
INV-006 cấm thêm dấu bỏ qua mới trong bộ test; chúng ở `poc_inv006_xdist_report.py` (chạy tay).

- INV-003: đích hoặc là bản cũ nguyên vẹn hoặc là bản mới đầy đủ; tệp tạm cùng thư mục, được dọn.
- INV-004: không xác định được năng lực ⇒ không khả dụng kèm lý do tiếng Việt, không ném/treo.
- INV-005: văn bản UTF-8 không BOM, LF; đường dẫn bản ghi tương đối, dùng `/`.
- INV-006: mọi test bị loại theo năng lực đều có dấu, lý do và có mặt trong báo cáo.
- INV-007: RAM đỉnh quy đổi đúng công thức, không đo được là `None` (không phải 0).
"""

from __future__ import annotations

import errno
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from mma_ai.compat import fsio
from mma_ai.compat.capabilities import (
    long_paths_enabled,
    ram_probe,
    symlink_supported,
)
from mma_ai.compat.display import probe_display
from mma_ai.compat.fsio import AtomicWriteError, write_bytes_atomic, write_text_atomic
from mma_ai.compat.memory import peak_ram_mb, ram_mib_from_raw
from mma_ai.compat.pathrules import is_absolute_any_os, to_record_path
from mma_ai.compat.platform_info import PlatformProfile, detect_platform

ROOT = Path(__file__).resolve().parents[2]
OLD_TEXT = "bản cũ nguyên vẹn\n" * 50
NEW_TEXT = "bản mới đầy đủ\n" * 80
OLD_BYTES = bytes(range(256)) * 20
NEW_BYTES = bytes(reversed(range(256))) * 30
_KINDS = ("windows", "linux", "wsl2", "macos")


def _profile(kind: str) -> PlatformProfile:
    return PlatformProfile(
        kind=cast(Any, kind),
        release="test",
        machine="x86_64",
        python_version=(3, 12, 0),
        is_wsl=kind == "wsl2",
        tested=True,
    )


# --------------------------------------------------------------------------- INV-003


class _Shim:
    """Bọc một mô-đun, cho ghi đè vài thuộc tính mà vẫn chuyển tiếp phần còn lại."""

    def __init__(self, inner: Any, **overrides: Any) -> None:
        self._inner = inner
        self._overrides = overrides

    def __getattr__(self, name: str) -> Any:
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._inner, name)


class _FaultyStream:
    """Luồng ghi thật nhưng hỏng ở bước `fail_on`, sau khi đã ghi dở một nửa dữ liệu."""

    def __init__(self, inner: Any, fail_on: str) -> None:
        self._inner = inner
        self._fail_on = fail_on

    def __enter__(self) -> _FaultyStream:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._inner.close()
        if self._fail_on == "close" and exc_info[0] is None:
            raise OSError(errno.EIO, "đóng tệp thất bại")

    def write(self, data: Any) -> int:
        half = len(data) // 2
        if self._fail_on == "write":
            self._inner.write(data[:half])
            raise OSError(errno.ENOSPC, "đĩa đầy giữa chừng")
        if self._fail_on == "interrupt_write":
            self._inner.write(data[:half])
            raise KeyboardInterrupt
        return int(self._inner.write(data))

    def flush(self) -> None:
        if self._fail_on == "flush":
            raise OSError(errno.EIO, "flush thất bại")
        self._inner.flush()

    def fileno(self) -> int:
        return int(self._inner.fileno())


_FAULT_STEPS = (
    "mkstemp",
    "fdopen",
    "write",
    "flush",
    "fsync",
    "close",
    "replace",
    "interrupt_write",
    "interrupt_replace",
)


def _open_fd_count() -> int | None:
    fd_dir = Path("/proc/self/fd")
    return len(os.listdir(fd_dir)) if fd_dir.is_dir() else None


def _inject(monkeypatch: pytest.MonkeyPatch, step: str, seen_dirs: list[str]) -> None:
    real_mkstemp = tempfile.mkstemp

    def mkstemp(*args: Any, **kwargs: Any) -> tuple[int, str]:
        seen_dirs.append(str(kwargs.get("dir")))
        if step == "mkstemp":
            raise OSError(errno.ENOSPC, "không tạo được tệp tạm")
        return real_mkstemp(*args, **kwargs)

    def fdopen(descriptor: int, mode: str, *args: Any, **kwargs: Any) -> Any:
        if step == "fdopen":
            raise OSError(errno.EMFILE, "quá nhiều tệp mở")
        return _FaultyStream(os.fdopen(descriptor, mode, *args, **kwargs), step)

    def fsync(descriptor: int) -> None:
        if step == "fsync":
            raise OSError(errno.EIO, "fsync thất bại")
        os.fsync(descriptor)

    def replace(src: Any, dst: Any) -> None:
        if step == "replace":
            raise OSError(errno.EXDEV, "thay thế thất bại")
        if step == "interrupt_replace":
            raise KeyboardInterrupt
        os.replace(src, dst)

    monkeypatch.setattr(fsio, "tempfile", _Shim(tempfile, mkstemp=mkstemp))
    monkeypatch.setattr(fsio, "os", _Shim(os, fdopen=fdopen, fsync=fsync))
    kwdefaults = fsio.replace_atomic.__kwdefaults__
    assert kwdefaults is not None
    monkeypatch.setitem(kwdefaults, "replace", replace)


def _write_old(destination: Path, as_text: bool, *, existing: bool) -> bytes | None:
    if not existing:
        return None
    old = OLD_TEXT.encode("utf-8") if as_text else OLD_BYTES
    destination.write_bytes(old)
    return old


@pytest.mark.parametrize("existing", [True, False], ids=["co-ban-cu", "chua-co-dich"])  # type: ignore[untyped-decorator]
@pytest.mark.parametrize("as_text", [True, False], ids=["text", "bytes"])  # type: ignore[untyped-decorator]
@pytest.mark.parametrize("step", _FAULT_STEPS)  # type: ignore[untyped-decorator]
def test_inv003_fault_injection_never_leaves_partial_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, step: str, as_text: bool, existing: bool
) -> None:
    """Tiêm lỗi ở MỌI bước: đích giữ bản cũ nguyên vẹn (hoặc vắng), 0 tệp tạm, không rò fd."""
    directory = tmp_path / "out"
    directory.mkdir()
    destination = directory / "du_lieu.json"
    old = _write_old(destination, as_text, existing=existing)
    fds_before = _open_fd_count()
    seen_dirs: list[str] = []
    _inject(monkeypatch, step, seen_dirs)

    expected_error: type[BaseException] = (
        KeyboardInterrupt if step.startswith("interrupt") else AtomicWriteError
    )
    with pytest.raises(expected_error) as raised:
        if as_text:
            write_text_atomic(destination, NEW_TEXT, profile=_profile("linux"))
        else:
            write_bytes_atomic(destination, NEW_BYTES, profile=_profile("linux"))

    if expected_error is AtomicWriteError:
        assert isinstance(raised.value, AtomicWriteError)
        assert str(destination) in str(raised.value), "thông điệp lỗi phải nêu đích (ngữ cảnh)"
        assert raised.value.destination == destination
    if old is None:
        assert not destination.exists(), "đích chưa có thì thất bại không được tạo tệp dở"
    else:
        assert destination.read_bytes() == old, f"bước {step}: bản cũ bị hỏng"
    assert sorted(p.name for p in directory.iterdir()) == ([destination.name] if old else [])
    assert all(Path(d) == directory for d in seen_dirs), "tệp tạm phải cùng thư mục với đích"
    monkeypatch.undo()
    if fds_before is not None:
        assert _open_fd_count() == fds_before, f"bước {step} làm rò descriptor"


@pytest.mark.parametrize("kind", _KINDS)  # type: ignore[untyped-decorator]
def test_inv003_inv005_success_is_complete_lf_utf8_no_bom_same_bytes_all_os(
    tmp_path: Path, kind: str
) -> None:
    """Thành công ⇒ bản mới đầy đủ, UTF-8 không BOM, LF, cùng byte trên mọi hồ sơ OS."""
    payloads = [
        "",
        "a",
        "dòng 1\r\ndòng 2\rdòng 3\n",
        "日本語 é 😀\r\n",
        "\ufeffđã-có-BOM",
        "x" * 300_000,
    ]
    for index, payload in enumerate(payloads):
        destination = tmp_path / f"t{index}.txt"
        destination.write_text("cũ", encoding="utf-8")
        write_text_atomic(destination, payload, profile=_profile(kind))
        data = destination.read_bytes()
        expected = payload.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        assert data == expected
        assert b"\r" not in data
        if not payload.startswith("\ufeff"):
            assert not data.startswith(b"\xef\xbb\xbf"), "không được tự thêm BOM"
    blob = tmp_path / "blob.bin"
    write_bytes_atomic(blob, NEW_BYTES, profile=_profile(kind))
    assert blob.read_bytes() == NEW_BYTES
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]


def test_inv003_unencodable_text_keeps_old_file(tmp_path: Path) -> None:
    """Chuỗi có surrogate lẻ không mã hoá được UTF-8 ⇒ lỗi có ngữ cảnh, bản cũ còn nguyên."""
    destination = tmp_path / "cu.txt"
    destination.write_text("bản cũ", encoding="utf-8")
    with pytest.raises(AtomicWriteError):
        write_text_atomic(destination, "ổn\ud800hỏng", profile=_profile("linux"))
    assert destination.read_text(encoding="utf-8") == "bản cũ"
    assert [p.name for p in tmp_path.iterdir()] == ["cu.txt"]


def test_inv003_destination_is_directory_or_parent_missing(tmp_path: Path) -> None:
    """Đích là thư mục / thư mục cha không tồn tại ⇒ AtomicWriteError, không để rác."""
    directory_target = tmp_path / "la_thu_muc"
    directory_target.mkdir()
    (directory_target / "giu").write_text("còn", encoding="utf-8")
    with pytest.raises(AtomicWriteError):
        write_text_atomic(directory_target, "x", profile=_profile("linux"))
    assert (directory_target / "giu").read_text(encoding="utf-8") == "còn"
    with pytest.raises(AtomicWriteError):
        write_bytes_atomic(tmp_path / "khong" / "co" / "f.bin", b"x", profile=_profile("linux"))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["la_thu_muc"]


def _patch_replace(
    monkeypatch: pytest.MonkeyPatch, replace: Callable[[Any, Any], None]
) -> list[float]:
    sleeps: list[float] = []
    kwdefaults = fsio.replace_atomic.__kwdefaults__
    assert kwdefaults is not None
    monkeypatch.setitem(kwdefaults, "replace", replace)
    monkeypatch.setitem(kwdefaults, "sleep", sleeps.append)
    return sleeps


def test_inv003_windows_locked_destination_bounded_retry_then_old_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Đích bị giữ mãi (PermissionError): thử lại có giới hạn rồi báo lỗi, bản cũ còn, tạm sạch."""
    destination = tmp_path / "bi_giu.json"
    destination.write_bytes(OLD_BYTES)
    calls: list[int] = []

    def locked(src: Any, dst: Any) -> None:
        calls.append(1)
        raise PermissionError(errno.EACCES, "WinError 32: tệp đang được tiến trình khác dùng")

    sleeps = _patch_replace(monkeypatch, locked)
    with pytest.raises(AtomicWriteError):
        write_bytes_atomic(destination, NEW_BYTES, profile=_profile("windows"))
    assert len(calls) == 5 and len(sleeps) == 4, "thử lại có trần (5 lần, 4 lần chờ)"
    assert all(math.isfinite(s) and 0 <= s <= 1 for s in sleeps)
    assert destination.read_bytes() == OLD_BYTES
    assert [p.name for p in tmp_path.iterdir()] == ["bi_giu.json"]


@pytest.mark.parametrize("failures", [1, 2, 3, 4])  # type: ignore[untyped-decorator]
def test_inv003_windows_transient_lock_ends_with_complete_new_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failures: int
) -> None:
    """Khoá tạm thời (≤ 4 lần): cuối cùng đích là bản mới ĐẦY ĐỦ, không tệp tạm."""
    destination = tmp_path / "tam_thoi.json"
    destination.write_bytes(OLD_BYTES)
    state = {"left": failures}

    def flaky(src: Any, dst: Any) -> None:
        if state["left"]:
            state["left"] -= 1
            raise PermissionError(errno.EACCES, "bị giữ")
        os.replace(src, dst)

    _patch_replace(monkeypatch, flaky)
    write_bytes_atomic(destination, NEW_BYTES, profile=_profile("windows"))
    assert destination.read_bytes() == NEW_BYTES
    assert [p.name for p in tmp_path.iterdir()] == ["tam_thoi.json"]


@pytest.mark.parametrize("kind", ["linux", "wsl2", "macos"])  # type: ignore[untyped-decorator]
def test_inv003_permission_error_never_retried_off_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Ngoài Windows không thử lại (không treo vô ích): đúng 1 lần gọi, 0 lần chờ."""
    destination = tmp_path / "d.bin"
    destination.write_bytes(OLD_BYTES)
    calls: list[int] = []

    def locked(src: Any, dst: Any) -> None:
        calls.append(1)
        raise PermissionError(errno.EACCES, "không có quyền")

    sleeps = _patch_replace(monkeypatch, locked)
    with pytest.raises(AtomicWriteError):
        write_bytes_atomic(destination, NEW_BYTES, profile=_profile(kind))
    assert len(calls) == 1 and sleeps == []
    assert destination.read_bytes() == OLD_BYTES


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "bad_waits", [[float("nan")], [float("inf")], [-1.0], [0.1, float("-inf")]]
)
def test_inv003_retry_policy_rejects_non_finite_waits_before_touching_files(
    tmp_path: Path, bad_waits: list[float]
) -> None:
    """Thời gian chờ không hợp lệ bị từ chối sớm, không động vào đích."""
    source = tmp_path / "nguon"
    destination = tmp_path / "dich"
    source.write_bytes(b"moi")
    destination.write_bytes(b"cu")
    with pytest.raises(ValueError):
        fsio.replace_atomic(source, destination, waits=bad_waits, profile=_profile("windows"))
    assert destination.read_bytes() == b"cu"


def test_inv003_concurrent_writers_reader_never_sees_partial_file(tmp_path: Path) -> None:
    """Nhiều luồng ghi cùng đích; luồng đọc chỉ thấy bản đầy đủ (một trong các tải trọng)."""
    size = 300_000
    destination = tmp_path / "chung.bin"
    old = b"O" * size
    destination.write_bytes(old)
    payloads = {bytes([65 + i]) * size for i in range(4)}
    stop = threading.Event()
    problems: list[str] = []

    def reader() -> None:
        while not stop.is_set():
            try:
                data = destination.read_bytes()
            except PermissionError:
                if sys.platform == "win32":
                    continue
                problems.append("PermissionError khi đọc")
                return
            if len(data) != size or len(set(data)) != 1:
                problems.append(f"đọc thấy bản dở: {len(data)} byte")
                return

    def writer(payload: bytes) -> None:
        for _ in range(15):
            try:
                write_bytes_atomic(destination, payload, profile=_profile("linux"))
            except AtomicWriteError as error:
                problems.append(f"ghi lỗi: {error}")
                return

    reading = threading.Thread(target=reader)
    writers = [threading.Thread(target=writer, args=(p,)) for p in sorted(payloads)]
    reading.start()
    for thread in writers:
        thread.start()
    for thread in writers:
        thread.join(60)
    stop.set()
    reading.join(60)
    assert problems == []
    assert destination.read_bytes() in payloads
    assert [p.name for p in tmp_path.iterdir()] == ["chung.bin"]


_NAME_ALPHABET = [
    "a",
    "Z",
    "0",
    " ",
    ".",
    "-",
    "_",
    "é",
    "日",
    "😀",
    "~",
    "$",
    "'",
    "(",
    ")",
    "#",
    "%",
]


def test_inv003_path_rules_odd_legal_file_names_round_trip(tmp_path: Path) -> None:
    """Tên tệp lạ nhưng hợp lệ trên POSIX (khoảng trắng, `~`, Unicode, bắt đầu bằng `.`)."""
    rnd = random.Random(20261012)
    names = {"~", "-x", ".an", "a b", "tên tệp.json", "😀.txt", " dau-cach", "$HOME", "x" * 200}
    while len(names) < 60:
        name = "".join(rnd.choice(_NAME_ALPHABET) for _ in range(rnd.randint(1, 40)))
        if name not in (".", ".."):
            names.add(name)
    for index, name in enumerate(sorted(names)):
        text_target = tmp_path / name
        write_text_atomic(text_target, f"nội dung {index}\n", profile=_profile("linux"))
        assert text_target.read_text(encoding="utf-8") == f"nội dung {index}\n"
        write_bytes_atomic(text_target, b"\x00\xff" + bytes([index]), profile=_profile("linux"))
        assert text_target.read_bytes() == b"\x00\xff" + bytes([index])
    assert {p.name for p in tmp_path.iterdir()} == names, "không được có tệp tạm hay tên lạ nào sót"


def test_inv003_dot_segments_and_literal_tilde_dir_stay_in_place(tmp_path: Path) -> None:
    """`./x`, `a/../x` và thư mục tên `~` literal: ghi đúng chỗ, không nở `~` thành HOME."""
    (tmp_path / "~").mkdir()
    (tmp_path / "sub").mkdir()
    write_text_atomic(tmp_path / "~" / "f.txt", "tilde", profile=_profile("linux"))
    write_text_atomic(tmp_path / "sub" / ".." / "g.txt", "dotdot", profile=_profile("linux"))
    write_text_atomic(
        Path(os.path.join(str(tmp_path), ".", "h.txt")), "dot", profile=_profile("linux")
    )
    assert (tmp_path / "~" / "f.txt").read_text(encoding="utf-8") == "tilde"
    assert (tmp_path / "g.txt").read_text(encoding="utf-8") == "dotdot"
    assert (tmp_path / "h.txt").read_text(encoding="utf-8") == "dot"
    assert not [p for p in tmp_path.rglob("*") if p.name.endswith(".tmp")]


# --------------------------------------------------------------------------- INV-004


class _ExoticError(Exception):
    """Ngoại lệ lạ với `str()` rỗng."""

    def __str__(self) -> str:
        return ""


_EXOTIC_FACTORIES: list[Callable[[], BaseException]] = [
    lambda: RuntimeError("GLFW: lỗi lạ"),
    lambda: OSError(errno.EIO, "I/O"),
    lambda: ImportError("không nạp được glfw"),
    lambda: OverflowError("tràn số"),
    lambda: MemoryError(),
    lambda: UnicodeDecodeError("utf-8", b"\xff", 0, 1, "sai mã"),
    lambda: KeyError("DISPLAY"),
    lambda: AttributeError("module 'glfw' has no attribute 'init'"),
    lambda: AssertionError(),
    lambda: _ExoticError(),
    lambda: ValueError("chi tiết " + "x" * 50_000),
]


@pytest.mark.parametrize("kind", _KINDS)  # type: ignore[untyped-decorator]
def test_inv004_unknown_capability_is_unavailable_never_hangs(kind: str) -> None:
    """GLFW ném ngoại lệ lạ ⇒ không khả dụng, lý do tiếng Việt không rỗng, nhanh, không ném."""
    environ = {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"}
    started = time.monotonic()
    for make in _EXOTIC_FACTORIES:

        def boom(make: Callable[[], BaseException] = make) -> bool:
            raise make()

        result = probe_display(_profile(kind), environ=environ, glfw_init=boom)
        assert result.available is False
        assert result.reason.strip(), "lý do không được rỗng"
        assert "màn hình" in result.reason
    assert time.monotonic() - started <= 5


@pytest.mark.parametrize("returned", [None, 0, "", [], 0.0, False])  # type: ignore[untyped-decorator]
def test_inv004_falsy_probe_result_is_unavailable_with_reason(returned: Any) -> None:
    result = probe_display(
        _profile("windows"),
        environ={},
        glfw_init=lambda: returned,
    )
    assert result.available is False and result.reason.strip()


@pytest.mark.parametrize("kind", ["linux", "wsl2"])  # type: ignore[untyped-decorator]
def test_inv004_linux_without_display_never_calls_glfw(kind: str) -> None:
    """WSL2 không WSLg / Linux không màn hình: không gọi GLFW (tránh nửa vời), gợi ý --headless."""

    def must_not_run() -> bool:
        raise AssertionError("không được khởi tạo GLFW khi không có DISPLAY/WAYLAND_DISPLAY")

    for environ in ({}, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}):
        result = probe_display(_profile(kind), environ=environ, glfw_init=must_not_run)
        assert result.available is False
        assert "--headless" in result.reason


@pytest.mark.parametrize("forced", ["1", "true", "yes", "2", " "])  # type: ignore[untyped-decorator]
def test_inv004_force_no_display_overrides_a_working_display(forced: str) -> None:
    result = probe_display(
        _profile("linux"),
        environ={"DISPLAY": ":0", "MMA_AI_FORCE_NO_DISPLAY": forced},
        glfw_init=lambda: True,
    )
    assert result.available is False and result.reason.strip()


@pytest.mark.parametrize("not_forced", ["", "0"])  # type: ignore[untyped-decorator]
def test_inv004_force_flag_off_values_do_not_block_probe(not_forced: str) -> None:
    result = probe_display(
        _profile("macos"),
        environ={"MMA_AI_FORCE_NO_DISPLAY": not_forced},
        glfw_init=lambda: True,
    )
    assert result.available is True


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "reader_result",
    [None, 2, -1, 10**30, "1", b"1", 0.5, [1], object()],
)
def test_inv004_long_paths_unknown_value_is_unavailable(reader_result: Any) -> None:
    capability = long_paths_enabled(
        _profile("windows"),
        registry_reader=lambda key, value: reader_result,
    )
    assert capability.available is False
    assert capability.reason is not None and capability.reason.strip()


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "exc",
    [
        FileNotFoundError("khoá không có"),
        PermissionError("từ chối"),
        OSError(5, "I/O"),
        ImportError("winreg"),
        ValueError("x"),
        OverflowError("y"),
    ],
)
def test_inv004_long_paths_registry_error_is_unavailable_with_detail(exc: Exception) -> None:
    def reader(key: str, value: str) -> int | None:
        raise exc

    capability = long_paths_enabled(_profile("windows"), registry_reader=reader)
    assert capability.available is False
    assert capability.reason is not None and "đường dẫn dài" in capability.reason


def test_inv004_long_paths_only_exact_one_is_available_and_other_os_needs_no_flag() -> None:
    assert long_paths_enabled(_profile("windows"), registry_reader=lambda k, v: 1).available
    assert not long_paths_enabled(_profile("windows"), registry_reader=lambda k, v: 0).available
    for kind in ("linux", "wsl2", "macos"):

        def must_not_read(key: str, value: str) -> int | None:
            raise AssertionError("OS khác không được đọc Registry")

        assert long_paths_enabled(_profile(kind), registry_reader=must_not_read).available


def test_inv004_symlink_probe_bad_directory_is_unavailable_and_leaves_no_residue(
    tmp_path: Path,
) -> None:
    """Thư mục dò không tồn tại / là tệp ⇒ không khả dụng kèm lý do; dò xong không để rác."""
    a_file = tmp_path / "la_tep"
    a_file.write_text("x", encoding="utf-8")
    for bad in (tmp_path / "khong_co" / "sau", a_file, str(a_file) + "\x00"):
        capability = symlink_supported(bad)
        assert capability.available is False
        assert capability.reason is not None and capability.reason.strip()
    real_dir = tmp_path / "that"
    real_dir.mkdir()
    symlink_supported(real_dir)
    assert list(real_dir.iterdir()) == [], "phép dò phải dọn thư mục/symlink tạm"


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "value",
    [
        None,
        float("nan"),
        float("inf"),
        float("-inf"),
        -1.0,
        -1e-9,
        "12",
        object(),
        [1],
        b"x",
        1 + 2j,
    ],
)
def test_inv004_ram_probe_garbage_is_unavailable_never_raises(value: Any) -> None:
    capability = ram_probe(_profile("linux"), peak_ram_source=lambda: value)
    assert capability.available is False
    assert capability.reason is not None and capability.reason.strip()


def test_inv004_ram_probe_source_exception_is_unavailable_with_detail() -> None:
    def boom() -> float | None:
        raise OSError(errno.EIO, "API đo RAM thất bại")

    capability = ram_probe(_profile("windows"), peak_ram_source=boom)
    assert capability.available is False
    assert capability.reason is not None and "RAM" in capability.reason


# --------------------------------------------------------------------------- INV-007


@pytest.mark.parametrize("kind", ["linux", "wsl2", "macos", "windows"])  # type: ignore[untyped-decorator]
@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "bad",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        -1.0,
        "không phải số",
        None,
        object(),
        [1],
        10**400,
    ],
)
def test_inv007_null_not_zero_when_source_returns_garbage(kind: str, bad: object) -> None:
    sources: dict[str, Any] = {
        "linux_source": lambda: bad,
        "macos_source": lambda: bad,
        "windows_source": lambda: bad,
    }
    assert peak_ram_mb(_profile(kind), **sources) is None


@pytest.mark.parametrize("kind", ["linux", "wsl2", "macos", "windows"])  # type: ignore[untyped-decorator]
@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "error",
    [
        OSError(errno.EIO, "API thất bại"),
        RuntimeError("lạ"),
        AttributeError("WinDLL"),
        ValueError("x"),
        OverflowError("y"),
        MemoryError(),
        ZeroDivisionError(),
    ],
)
def test_inv007_null_not_zero_when_source_raises(kind: str, error: Exception) -> None:
    def boom() -> float:
        raise error

    result = peak_ram_mb(_profile(kind), linux_source=boom, macos_source=boom, windows_source=boom)
    assert result is None


def test_inv007_unknown_os_kind_is_none_not_zero() -> None:
    assert peak_ram_mb(_profile("freebsd")) is None
    with pytest.raises(ValueError):
        ram_mib_from_raw(1.0, "freebsd")


def test_inv007_linux_formula_unchanged_and_other_os_bytes() -> None:
    """Công thức Linux KiB/1024 không đổi (run cũ so sánh được); macOS/Windows byte/1048576."""
    rnd = random.Random(7)
    for _ in range(500):
        raw = rnd.uniform(0, 2e9)
        assert ram_mib_from_raw(raw, "linux") == raw / 1024.0
        assert ram_mib_from_raw(raw, "wsl2") == raw / 1024.0
        assert ram_mib_from_raw(raw, "macos") == raw / (1024 * 1024)
        assert ram_mib_from_raw(raw, "windows") == raw / (1024 * 1024)
    assert ram_mib_from_raw(2048, "linux") == 2.0
    assert ram_mib_from_raw(3 * 1024 * 1024, "windows") == 3.0


def test_inv007_real_measure_is_positive_finite_or_none_never_zero() -> None:
    value = peak_ram_mb(detect_platform())
    assert value is None or (math.isfinite(value) and value > 0)


def test_inv007_windows_profile_on_non_windows_host_is_none_not_zero() -> None:
    """Hồ sơ Windows trên máy không có `ctypes.WinDLL`: không đo được ⇒ None, không 0, không ném."""
    value = peak_ram_mb(_profile("windows"))
    if sys.platform != "win32":
        assert value is None
    else:
        assert value is None or value > 0


# ------------------------------------------------------------------- INV-005 / luật đường dẫn

_REL_SEGMENTS = [
    "a",
    "b",
    "dữ liệu",
    "日本",
    "x y",
    "é",
    ".",
    "..",
    "~",
    "$HOME",
    "*",
    "a.b",
    "😀",
    "run 1",
]
_ABS_SEGMENTS = [s for s in _REL_SEGMENTS if s not in (".", "..")]
_DRIVE_LETTER = re.compile(r"^[A-Za-z]:")


def _separators(rnd: random.Random, segments: list[str]) -> str:
    joined = segments[0]
    for segment in segments[1:]:
        joined += rnd.choice(["/", "\\", "//", "\\\\", "/\\"]) + segment
    return joined


def _windows_absolute_forms(rnd: random.Random) -> str:
    segments = [rnd.choice(_ABS_SEGMENTS) for _ in range(rnd.randint(1, 5))]
    body = _separators(rnd, segments)
    form = rnd.randrange(5)
    if form == 0:
        return rnd.choice(["C:", "d:", "Z:"]) + rnd.choice(["\\", "/"]) + body
    if form == 1:
        return (
            "\\\\"
            + rnd.choice(["server", "srv-1", "máy"])
            + "\\"
            + rnd.choice(["share", "d$"])
            + "\\"
            + body
        )
    if form == 2:
        return "\\" + body
    if form == 3:
        return "\\\\?\\" + rnd.choice(["C:", "e:"]) + "\\" + body
    return rnd.choice(["C:", "x:"]) + body


def test_path_rules_fuzz_never_raises_and_never_leaks_backslash() -> None:
    """Chuỗi ngẫu nhiên gồm `\\`, `/`, `:`, UNC, Unicode, NUL, rỗng: không ném; bản ghi sạch."""
    rnd = random.Random(20261012)
    tokens = [
        "\\",
        "/",
        "//",
        "\\\\",
        ":",
        "C:",
        "c:",
        "a",
        "b",
        "x y",
        " ",
        ".",
        "..",
        "é",
        "日本",
        "\x00",
        "~",
        "?",
        "*",
        "\u202e",
        "server",
        "share",
        "\\\\?\\",
        "CON",
        "\ud800",
        "😀",
    ]
    for _ in range(20_000):
        text = "".join(rnd.choice(tokens) for _ in range(rnd.randint(0, 8)))
        verdict = is_absolute_any_os(text)
        assert isinstance(verdict, bool)
        # Hoán đổi `/` ↔ `\` không đổi kết luận tuyệt đối/tương đối (không phụ thuộc OS).
        assert is_absolute_any_os(text.replace("/", "\\")) == is_absolute_any_os(
            text.replace("\\", "/")
        ), repr(text)
        assert isinstance(to_record_path(text), str)
    assert is_absolute_any_os("") is False
    assert is_absolute_any_os("a" * 100_000) is False
    assert is_absolute_any_os("/" + "a" * 100_000) is True


def test_path_rules_five_absolute_forms_and_relative_forms_any_os() -> None:
    for absolute in (
        "/etc/x",
        "\\etc\\x",
        "\\\\srv\\share\\x",
        "C:\\x",
        "C:x",
        "c:/x",
        "\\\\?\\C:\\x",
    ):
        assert is_absolute_any_os(absolute) is True, absolute
    for relative in ("a", "a/b", "a\\b", "./a", ".\\a", "../a", "~", "~/a", "a b/c", "", "."):
        assert is_absolute_any_os(relative) is False, relative


def test_path_rules_fuzz_windows_absolute_record_path_is_clean() -> None:
    """Dạng tuyệt đối kiểu Windows hợp lệ ⇒ bản ghi tương đối, `/`, không ổ đĩa, không theo cwd."""
    rnd = random.Random(99)
    original_cwd = Path.cwd()
    try:
        for index in range(5_000):
            text = _windows_absolute_forms(rnd)
            assert is_absolute_any_os(text), repr(text)
            record = to_record_path(text)
            assert "\\" not in record, (text, record)
            assert not _DRIVE_LETTER.match(record), (text, record)
            assert not is_absolute_any_os(record), (text, record)
            assert record, (text, record)
            assert "//" not in record, (text, record)
            if index % 500 == 0:
                os.chdir(tempfile.gettempdir())
                assert to_record_path(text) == record, "bản ghi không được phụ thuộc cwd"
                os.chdir(original_cwd)
    finally:
        os.chdir(original_cwd)


def test_path_rules_fuzz_relative_record_path_is_clean_and_stable() -> None:
    rnd = random.Random(5)
    for _ in range(5_000):
        segments = [rnd.choice(_REL_SEGMENTS) for _ in range(rnd.randint(1, 6))]
        text = rnd.choice(["", "./", ".\\"]) + _separators(rnd, segments)
        record = to_record_path(text)
        assert "\\" not in record, (text, record)
        assert not is_absolute_any_os(record), (text, record)
        assert to_record_path(record) == record, (text, record)


def test_path_rules_fuzz_base_relative_round_trip() -> None:
    rnd = random.Random(11)
    for _ in range(2_000):
        rel_parts = [rnd.choice(_ABS_SEGMENTS) for _ in range(rnd.randint(1, 4))]
        expected = "/".join(rel_parts)
        posix_base = "/" + "/".join(rnd.choice(_ABS_SEGMENTS) for _ in range(rnd.randint(1, 3)))
        assert to_record_path(posix_base + "/" + expected, posix_base) == expected
        windows_base = "C:\\" + "\\".join(
            rnd.choice(_ABS_SEGMENTS) for _ in range(rnd.randint(1, 3))
        )
        assert to_record_path(windows_base + "\\" + "\\".join(rel_parts), windows_base) == expected
    # Hệ tệp không phân biệt hoa/thường: ổ đĩa và gốc khác hoa/thường vẫn tương đối đúng.
    assert to_record_path("c:\\Base\\A\\b", "C:\\base") == "A/b"


# --------------------------------------------------------------------------- INV-006


def _run_pytest_child(
    workdir: Path, *args: str, env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(ROOT / "tests" / "unit"), str(ROOT / "src")]),
        "MMA_AI_FORCE_NO_DISPLAY": "1",
        "PYTHONIOENCODING": "utf-8",
        **(env_extra or {}),
    }
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("PYTEST_XDIST_WORKER", None)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "capability_gate",
            "--rootdir",
            str(workdir),
            *args,
        ],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


_CHILD_SUITE = textwrap.dedent(
    """
    import pytest

    def test_chay_duoc():
        assert len('ok') == 2

    @pytest.mark.windows_only(reason="Chỉ chạy trên Windows.")
    def test_cua_windows():
        raise AssertionError("test này không được phép chạy")

    @pytest.mark.requires_display(reason="Cần màn hình hiển thị.")
    @pytest.mark.requires_cuda(reason="Cần CUDA.")
    def test_hai_dau_nang_luc():
        raise AssertionError("test này không được phép chạy")

    @pytest.mark.requires_display(reason="Cần màn hình.")
    class TestCaLop:
        def test_mot(self):
            raise AssertionError("test này không được phép chạy")

        def test_hai(self):
            raise AssertionError("test này không được phép chạy")

    @pytest.mark.display(reason="Dùng màn hình thật nếu có.")
    def test_dau_display_khong_bi_loai():
        assert len('ok') == 2
    """
)


def test_inv006_deselect_always_reported(tmp_path: Path) -> None:
    """Mọi test bị loại đều có mặt ở báo cáo JSON và bản tóm tắt; không test nào bị bỏ ngầm."""
    (tmp_path / "test_child.py").write_text(_CHILD_SUITE, encoding="utf-8")
    report_path = tmp_path / "bao_cao.json"
    child = _run_pytest_child(
        tmp_path,
        "--capability-report",
        str(report_path),
        "--capability-max-ratio",
        "1.0",
        "test_child.py",
    )
    assert child.returncode == 0, child.stdout + child.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    reported = {item["nodeid"]: item for item in report["items"]}
    expected = {
        "test_child.py::test_cua_windows": "windows_only",
        "test_child.py::test_hai_dau_nang_luc": "requires_display",
        "test_child.py::TestCaLop::test_mot": "requires_display",
        "test_child.py::TestCaLop::test_hai": "requires_display",
    }
    if sys.platform == "win32":
        expected.pop("test_child.py::test_cua_windows")
    assert {node: item["marker"] for node, item in reported.items()} == expected
    assert report["deselected"] == len(expected) == len(report["items"])
    assert report["collected"] == 6
    assert all(item["reason"].strip() for item in reported.values())
    for node, item in reported.items():
        assert node in child.stdout, f"{node} bị loại nhưng không có trên bản tóm tắt"
        assert item["reason"] in child.stdout
    assert f"{len(expected)} deselected" in child.stdout
    assert "passed" in child.stdout and "failed" not in child.stdout


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "marker_line",
    [
        "@pytest.mark.requires_cuda",
        "@pytest.mark.requires_cuda()",
        '@pytest.mark.requires_cuda(reason="")',
        '@pytest.mark.requires_cuda(reason="   ")',
        "@pytest.mark.requires_cuda(reason=5)",
        "@pytest.mark.requires_cuda(reason=None)",
        '@pytest.mark.windows_only(why="sai tên đối số")',
    ],
)
def test_inv006_marker_without_reason_is_a_usage_error_not_silently_dropped(
    tmp_path: Path, marker_line: str
) -> None:
    """Dấu năng lực thiếu/rỗng/sai kiểu lý do ⇒ pytest dừng với UsageError, không loại âm thầm."""
    body = f"import pytest\n\n{marker_line}\ndef test_x():\n    assert len('ok') == 2\n"
    (tmp_path / "test_child.py").write_text(body, encoding="utf-8")
    child = _run_pytest_child(tmp_path, "test_child.py")
    assert child.returncode == 4, child.stdout + child.stderr
    assert "lý do" in child.stdout + child.stderr


@pytest.mark.parametrize("ratio", ["nan", "inf", "-0.1", "1.5", "abc", ""])  # type: ignore[untyped-decorator]
def test_inv006_invalid_ratio_option_is_rejected(tmp_path: Path, ratio: str) -> None:
    (tmp_path / "test_child.py").write_text(
        "def test_x():\n    assert len('ok') == 2\n", encoding="utf-8"
    )
    child = _run_pytest_child(tmp_path, "--capability-max-ratio", ratio, "test_child.py")
    assert child.returncode == 4, child.stdout + child.stderr


def test_inv006_over_ratio_fails_the_serial_run_even_when_all_tests_pass(tmp_path: Path) -> None:
    """Loại quá trần tỷ lệ ⇒ mã thoát 1 (không để việc loại hàng loạt che lỗi) khi chạy tuần tự."""
    (tmp_path / "test_child.py").write_text(_CHILD_SUITE, encoding="utf-8")
    child = _run_pytest_child(tmp_path, "test_child.py")
    assert child.returncode == 1, child.stdout + child.stderr
    assert "Tỷ lệ test bị loại vượt ngưỡng" in child.stdout


def test_inv006_unwritable_report_path_fails_loudly(tmp_path: Path) -> None:
    (tmp_path / "test_child.py").write_text(_CHILD_SUITE, encoding="utf-8")
    child = _run_pytest_child(
        tmp_path,
        "--capability-report",
        str(tmp_path / "khong_co" / "r.json"),
        "--capability-max-ratio",
        "1.0",
        "test_child.py",
    )
    assert child.returncode == 1, child.stdout + child.stderr
    assert "CẢNH BÁO" in child.stderr
