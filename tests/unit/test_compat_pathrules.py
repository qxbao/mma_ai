"""AC-4, AC-5, INV-005: kiểm tra đường dẫn tương thích trên mọi hệ điều hành."""

from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Literal

import pytest

from mma_ai.compat.platform_info import PlatformProfile


def _api() -> ModuleType:
    module = import_module("mma_ai.compat.pathrules")
    for name in ("is_absolute_any_os", "to_record_path", "venv_python"):
        assert callable(getattr(module, name, None)), f"Thiếu API {name}"
    return module


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "value",
    ("/var/tmp/run", r"\rooted\path", r"\\server\share", r"C:\work\run", "C:work"),
)
def test_inv_005_five_absolute_forms_rejected_on_every_os(value: str) -> None:
    assert _api().is_absolute_any_os(value) is True


@pytest.mark.parametrize("value", ("runs/one", "./runs/one", "folder\\run"))  # type: ignore[untyped-decorator]
def test_inv_005_relative_forms_are_accepted(value: str) -> None:
    assert _api().is_absolute_any_os(value) is False


def test_inv_005_record_path_is_relative_slash_separated_and_has_no_drive(tmp_path: Path) -> None:
    api = _api()
    base = tmp_path / "workspace"
    result = api.to_record_path(base / "runs" / "one", base=base)
    assert result == "runs/one"
    assert "\\" not in result
    assert ":" not in result
    assert not api.is_absolute_any_os(result)


def test_inv_005_windows_record_path_is_relative_to_windows_base() -> None:
    result = _api().to_record_path(r"C:\workspace\runs\one", base=r"C:\workspace")
    assert result == "runs/one"


def test_inv_005_posix_record_path_never_keeps_a_windows_base_drive() -> None:
    result = _api().to_record_path("/workspace/runs/one", base=r"C:\workspace")
    assert result == "workspace/runs/one"
    assert ":" not in result


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("kind", "expected"),
    (("windows", Path("venv/Scripts/python.exe")), ("linux", Path("venv/bin/python")),
     ("wsl2", Path("venv/bin/python")), ("macos", Path("venv/bin/python"))),
)
def test_venv_python_by_os(
    kind: Literal["windows", "linux", "wsl2", "macos"], expected: Path
) -> None:
    profile = PlatformProfile(kind, "release", "machine", (3, 12, 0), kind == "wsl2", True)
    assert _api().venv_python("venv", profile) == expected
