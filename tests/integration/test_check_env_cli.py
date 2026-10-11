"""Kiểm CLI (giao diện dòng lệnh) check-env chạy qua tiến trình con, AC-5."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parents[2]


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    source_path = str(PROJECT_ROOT / "src")
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (source_path, environment.get("PYTHONPATH")))
    )
    environment["MMA_AI_FORCE_NO_DISPLAY"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "mma_ai.compat.env_report", *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _json_run() -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    result = _run_cli("--json")
    return result, json.loads(result.stdout)


def _detected_platform_kind() -> str:
    platform_info = importlib.import_module("mma_ai.compat.platform_info")
    return str(platform_info.detect_platform().kind)


def test_ac_5_json_output_valid_and_exit_matches_overall() -> None:
    """AC-5 / NFR-ENV-001: JSON từ tiến trình thật hợp lệ và mã thoát nhất quán."""
    result, report = _json_run()

    assert isinstance(report, dict)
    assert report["overall"] in {"ok", "fail"}
    assert result.returncode == (1 if report["overall"] == "fail" else 0)
    assert result.stderr.strip()


def test_ac_5_text_output_vietnamese_one_line_per_check() -> None:
    """AC-5: chế độ chữ có một dòng tiếng Việt cho mỗi phép kiểm."""
    result = _run_cli()
    json_result, report = _json_run()

    assert result.returncode == json_result.returncode
    check_lines = [
        line
        for line in result.stdout.splitlines()
        if line.startswith(("[ok]", "[CẢNH BÁO]", "[LỖI]"))
    ]
    assert len(check_lines) == len(report["checks"])
    assert "Môi trường " in result.stdout
    assert all(": " in line for line in check_lines)


def test_ac_5_unknown_flag_exits_2() -> None:
    """AC-5: cờ lạ bị từ chối với mã thoát 2."""
    result = _run_cli("--unknown")

    assert result.returncode == 2
    assert "Cờ không được hỗ trợ" in result.stderr


def test_ac_5_report_os_kind_matches_detect_platform() -> None:
    """AC-5: loại hệ điều hành báo cáo khớp bộ phát hiện nền tảng."""
    _, report = _json_run()

    assert report["os"]["kind"] == _detected_platform_kind()


def test_ac_5_exit_code_matches_overall() -> None:
    """AC-5 / FR-017 / FR-024: kết quả tổng thể quyết định mã thoát CLI."""
    result, report = _json_run()

    expected_exit = 1 if report["overall"] == "fail" else 0
    assert result.returncode == expected_exit
