"""AC-6, INV-006: kiểm tra loại test theo năng lực bằng giao diện thật của pytest."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

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

