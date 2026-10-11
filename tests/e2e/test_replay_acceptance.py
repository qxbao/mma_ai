"""Kiểm thử đầu-cuối cho CLI thật."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from mma_ai.physics.body_model import load_muscle_model
from mma_ai.visualization.episode import read_episode
from tests.integration.test_demo_cli import _create_test_checkpoint
from tests.integration.test_replay_headless import _create_test_episode

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _environment() -> dict[str, str]:
    """Tạo môi trường không màn hình (headless) cho tiến trình entrypoint."""
    environment = os.environ.copy()
    environment.pop("DISPLAY", None)
    environment.pop("WAYLAND_DISPLAY", None)
    return environment


def _run_cli(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """Gọi CLI thật ở tiến trình độc lập, không dựng trực tiếp ứng dụng."""
    return subprocess.run(
        [sys.executable, "-m", "mma_ai.visualization.cli", *arguments],
        cwd=PROJECT_ROOT,
        env=_environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=40.0,
        check=False,
    )


def test_ac_1_replay_episode(tmp_path: Path) -> None:
    """AC-1, FR-001, FR-010, SC-001: episode hợp lệ hoàn tất headless mã 0."""
    episode = _create_test_episode(tmp_path / "episode.json")
    result = _run_cli(["--episode", str(episode), "--headless"])
    assert result.returncode == 0, result.stderr
    summary: dict[str, Any] = json.loads(result.stdout)
    assert summary["mode"] == "episode" and summary["headless"] is True
    assert summary["model_check"]["match"] is True


def test_ac_2_demo_from_checkpoint(tmp_path: Path) -> None:
    """AC-2, FR-002, FR-003, FR-008, SC-002: demo lưu và đọc lại episode sáu cơ."""
    saved_episode = tmp_path / "demo.json"
    checkpoint = _create_test_checkpoint(tmp_path / "run")
    result = _run_cli(
        [
            "--checkpoint",
            str(checkpoint),
            "--headless",
            "--save-episode",
            str(saved_episode),
            "--seed",
            "42",
        ]
    )
    assert result.returncode == 0, result.stderr
    episode = read_episode(saved_episode)
    assert len(episode.model.muscle_names) == len(set(episode.model.muscle_names)) == 6
    for frame in episode.frames[1:]:
        assert frame.excitation is not None and len(frame.excitation) == 6
        assert all(0.0 <= value <= 1.0 for value in frame.excitation)


def test_ac_3_no_display(tmp_path: Path) -> None:
    """AC-3, FR-010, FR-011, NFR-HEADLESS-001, SC-003: nhánh không màn hình thoát nhanh."""
    episode = _create_test_episode(tmp_path / "episode.json")
    started = time.perf_counter()
    no_display = _run_cli(["--episode", str(episode)])
    elapsed = time.perf_counter() - started
    headless = _run_cli(["--episode", str(episode), "--headless"])
    assert elapsed <= 5.0, f"CLI chờ màn hình quá {elapsed:.2f} giây"
    assert no_display.returncode == 7 and "--headless" in no_display.stderr
    assert headless.returncode == 0, headless.stderr


def test_ac_4_model_mismatch(tmp_path: Path) -> None:
    """AC-4, FR-012, INV-001, SC-004: lệch XML bị từ chối."""
    del tmp_path
    episode = (
        PROJECT_ROOT
        / "specs/005-replay-3d-muscle-demo/contracts/examples/episode.from-checkpoint-reached.json"
    )
    result = _run_cli(["--episode", str(episode)])
    assert result.returncode == 6
    assert "Lệch mã băm XML" in result.stderr
    assert load_muscle_model("myoelbow").info.sha256 in result.stderr


def test_ac_5_missing_path(tmp_path: Path) -> None:
    """AC-5, FR-013, INV-004, SC-005: đường dẫn vắng mặt không mở viewer hay sinh tệp."""
    missing = tmp_path / "khong-ton-tai.json"
    result = _run_cli(["--episode", str(missing)])
    assert result.returncode == 5 and not missing.exists()
    assert "không tìm thấy" in result.stderr.lower()
