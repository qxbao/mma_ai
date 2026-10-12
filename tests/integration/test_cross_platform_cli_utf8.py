"""Kiểm tra đầu ra CLI và tệp văn bản theo hợp đồng đa nền tảng."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from train_fixtures import smoke_config

_CLI_MODULES = (
    "mma_ai.learning.cli",
    "mma_ai.learning.benchmark",
    "mma_ai.learning.compare_cli",
    "mma_ai.monitoring.cli",
    "mma_ai.evaluation.cli",
    "mma_ai.visualization.cli",
)
_TEXT_SUFFIXES = {".json", ".jsonl", ".yaml", ".yml", ".md"}


def test_inv_005_ac_4_clis_survive_legacy_stdio_encoding() -> None:
    """INV-005, NFR-ENC-001, AC-4: CLI vẫn chạy với mã hóa luồng cũ."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    env["MMA_AI_FORCE_NO_DISPLAY"] = "1"
    for module in _CLI_MODULES:
        result = subprocess.run(
            [sys.executable, "-m", module, "--help"],
            capture_output=True,
            env=env,
            timeout=30,
            check=False,
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, (module, output.decode("utf-8", errors="replace"))
        assert b"UnicodeEncodeError" not in output, module
        assert any(byte > 127 for byte in output), module
        output.decode("utf-8")


def test_inv_005_ac_4_written_text_files_have_no_cr_or_bom(tmp_path: Path) -> None:
    """INV-005, NFR-ENC-001, AC-4: tệp văn bản được ghi là UTF-8 không BOM/LF."""
    smoke_config(tmp_path, total_timesteps=4096)
    text_files = [
        path
        for path in tmp_path.rglob("*")
        if path.is_file() and path.suffix.lower() in _TEXT_SUFFIXES
    ]
    assert text_files
    for path in text_files:
        raw = path.read_bytes()
        assert b"\r" not in raw, f"Có CR trong {path.name}"
        assert not raw.startswith(b"\xef\xbb\xbf"), f"Có BOM trong {path.name}"
        raw.decode("utf-8")
