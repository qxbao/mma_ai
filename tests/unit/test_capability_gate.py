"""AC-6, INV-006: kiểm tra loại test theo năng lực bằng giao diện thật của pytest."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[2]


def _run_pytest(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "test_example.py").write_text(
        "import pytest\n"
        "@pytest.mark.requires_cuda(reason='Máy không có CUDA')\n"
        "def test_cuda(): assert True\n"
        + "".join(f"def test_general_{index}(): assert True\n" for index in range(19)),
        encoding="utf-8",
    )
    (tmp_path / "torch.py").write_text(
        "class _Cuda:\n"
        "    @staticmethod\n"
        "    def is_available(): return False\n"
        "cuda = _Cuda()\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(tmp_path), str(_ROOT / "tests" / "unit"), str(_ROOT / "src")]
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "capability_gate",
            "-q",
            "-p",
            "no:cacheprovider",
            *args,
            str(tmp_path),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_inv_006_unsatisfied_marker_is_deselected_not_skipped(tmp_path: Path) -> None:
    """INV-006, AC-6: thiếu năng lực phải loại lúc thu thập, giữ test thường chạy."""
    result = _run_pytest(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "19 passed" in result.stdout
    assert "1 deselected" in result.stdout
    assert "test_cuda" in result.stdout
    assert "requires_cuda" in result.stdout
    assert "Máy không có CUDA" in result.stdout


def test_inv_006_missing_reason_is_collection_error(tmp_path: Path) -> None:
    """INV-006, AC-6: marker thiếu reason phải dừng thu thập với UsageError."""
    (tmp_path / "test_missing_reason.py").write_text(
        "import pytest\n"
        "@pytest.mark.requires_cuda\n"
        "def test_cuda(): assert True\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(_ROOT / "tests" / "unit"), str(_ROOT / "src")]
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "capability_gate", "-q", str(tmp_path)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "requires_cuda" in result.stdout + result.stderr
    assert "reason" in (result.stdout + result.stderr).lower()
    assert "no tests ran" in result.stdout
    assert "ERROR:" in result.stderr


def test_inv_006_ratio_over_limit_fails_session(tmp_path: Path) -> None:
    """INV-006, AC-6: tỷ lệ bị loại vượt ngưỡng phải làm phiên pytest thất bại."""
    result = _run_pytest(tmp_path, "--capability-max-ratio=0.04")

    assert result.returncode != 0
    assert "vượt ngưỡng" in result.stdout + result.stderr


def test_inv_006_report_lists_each_deselected_with_reason(tmp_path: Path) -> None:
    """INV-006, AC-6: báo cáo JSON ghi đủ nodeid, marker và lý do từng test bị loại."""
    report_path = tmp_path / "capabilities.json"
    result = _run_pytest(tmp_path, f"--capability-report={report_path}")

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["collected"] == 20
    assert report["deselected"] == 1
    assert report["ratio"] == pytest.approx(0.05)
    assert report["items"] == [
        {
            "nodeid": "test_example.py::test_cuda",
            "marker": "requires_cuda",
            "reason": "Máy không có CUDA",
        }
    ]


def test_inv_006_all_required_markers_are_registered(tmp_path: Path) -> None:
    """AC-6: plugin đăng ký đủ marker mà không cần khai báo trong pyproject.toml."""
    (tmp_path / "test_registered.py").write_text(
        "import pytest\n"
        "@pytest.mark.display(reason='Màn hình cần cho test')\n"
        "def test_display(): assert True\n"
        "@pytest.mark.requires_display(reason='Cần màn hình')\n"
        "def test_requires_display(): assert True\n"
        "@pytest.mark.requires_symlink(reason='Cần symlink')\n"
        "def test_symlink(): assert True\n"
        "@pytest.mark.requires_cuda(reason='Cần CUDA')\n"
        "def test_cuda(): assert True\n"
        "@pytest.mark.requires_xdist(reason='Cần pytest-xdist')\n"
        "def test_xdist(): assert True\n"
        "@pytest.mark.posix_only(reason='Chỉ POSIX')\n"
        "def test_posix(): assert True\n"
        "@pytest.mark.linux_only(reason='Chỉ Linux')\n"
        "def test_linux(): assert True\n"
        "@pytest.mark.windows_only(reason='Chỉ Windows')\n"
        "def test_windows(): assert True\n"
        "@pytest.mark.macos_only(reason='Chỉ macOS')\n"
        "def test_macos(): assert True\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(tmp_path), str(_ROOT / "tests" / "unit"), str(_ROOT / "src")]
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "capability_gate",
            "--collect-only",
            "-q",
            "--capability-max-ratio=1",
            str(tmp_path),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PytestUnknownMarkWarning" not in result.stdout + result.stderr


@pytest.mark.requires_xdist(reason="Máy không có pytest-xdist")  # type: ignore[untyped-decorator]
def test_regress_f_001_xdist_reports_deselected_and_enforces_ratio(tmp_path: Path) -> None:
    """F-001, INV-006, AC-6, NFR-CI-001: xdist phải giữ báo cáo và ngưỡng loại test."""
    report_path = tmp_path / "capabilities.json"
    result = _run_pytest(
        tmp_path,
        "-n",
        "2",
        "--capability-max-ratio=0.04",
        f"--capability-report={report_path}",
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "Kiểm thử bị loại theo năng lực: 1/20 (5.0%; giới hạn 4.0%)." in output
    assert "test_example.py::test_cuda" in output
    assert "Máy không có CUDA" in output
    assert "vượt ngưỡng" in output
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["collected"] == 20
    assert report["deselected"] == 1



def test_ac1_git_history_probe_true_when_git_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-1, FR-001, INV-001: phép dò nhận diện git khi lệnh thành công."""
    import capability_gate

    monkeypatch.setattr(
        getattr(capability_gate, "subprocess"),
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0),
    )

    assert capability_gate._capability_available("requires_git_history") is True


def test_ac2_git_history_probe_false_when_git_exits_128(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-2, FR-001, INV-001: phép dò từ chối mã lỗi git 128."""
    import capability_gate

    monkeypatch.setattr(
        getattr(capability_gate, "subprocess"),
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 128),
    )

    assert capability_gate._capability_available("requires_git_history") is False


def test_ac2_git_history_probe_false_on_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-2, FR-002, NFR-REL-001, INV-003: lỗi chạy git trả không khả dụng."""
    import capability_gate

    def raise_oserror(*args: Any, **kwargs: Any) -> None:
        raise OSError("git không khả dụng")

    monkeypatch.setattr(getattr(capability_gate, "subprocess"), "run", raise_oserror)

    assert capability_gate._capability_available("requires_git_history") is False


def test_ac2_git_history_probe_false_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-2, FR-003, 009/NFR-QUAL-001, INV-003: timeout git tối đa năm giây."""
    import capability_gate

    observed: dict[str, object] = {}

    def raise_timeout(*args: Any, **kwargs: Any) -> None:
        observed.update(kwargs)
        raise subprocess.TimeoutExpired(str(args[0]), float(kwargs["timeout"]))

    monkeypatch.setattr(getattr(capability_gate, "subprocess"), "run", raise_timeout)

    assert capability_gate._capability_available("requires_git_history") is False
    timeout = observed.get("timeout")
    assert isinstance(timeout, (int, float))
    assert 0 < timeout <= 5


def test_ac2_nfr_gate_001_requires_git_history_deselected_without_dot_git(
    tmp_path: Path,
) -> None:
    """AC-2, 009/AC-3, FR-004, NFR-GATE-001, INV-002, INV-006:
    test lịch sử của 008 bị loại trên archive; mã INV-002 ở đây là của 009.

    Test này không thay lần chạy ai-sdlc verify --branch ai-sdlc/integration của cổng máy.
    """
    plugin_root = tmp_path / "tests" / "unit"
    plugin_root.mkdir(parents=True)
    (plugin_root / "capability_gate.py").write_bytes(
        (_ROOT / "tests" / "unit" / "capability_gate.py").read_bytes()
    )
    test_root = tmp_path / "suite"
    test_root.mkdir()
    (test_root / "test_history.py").write_text(
        "import pytest\n"
        "@pytest.mark.requires_git_history(reason='Máy không có lịch sử git')\n"
        "def test_git_history(): assert True\n"
        + "".join(f"def test_general_{index}(): assert True\n" for index in range(19)),
        encoding="utf-8",
    )
    report_path = tmp_path / "capabilities.json"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(plugin_root), str(_ROOT / "src")]
    )
    for variable in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        environment.pop(variable, None)
    environment["GIT_CEILING_DIRECTORIES"] = str(tmp_path.parent)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "capability_gate",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--capability-report={report_path}",
            str(test_root),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "19 passed" in output
    assert "Kiểm thử bị loại theo năng lực: 1/20" in output
    assert "test_git_history" in output
    assert "requires_git_history" in output
    assert "Máy không có lịch sử git" in output
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["collected"] == 20
    assert report["deselected"] == 1
    assert report["ratio"] == pytest.approx(0.05)
    assert report["items"] == [
        {
            "nodeid": "suite/test_history.py::test_git_history",
            "marker": "requires_git_history",
            "reason": "Máy không có lịch sử git",
        }
    ]


def test_009_inv_002_project_dependency_files_unchanged() -> None:
    """009/INV-002: đặc tả yêu cầu không sửa pyproject.toml và uv.lock.

    Đây là kiểm tra trạng thái git cục bộ, khác INV-002 của 008 về tài liệu commit.
    """
    import subprocess

    changed_files = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "pyproject.toml", "uv.lock"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    assert changed_files == []
