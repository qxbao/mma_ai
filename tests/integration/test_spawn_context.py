from __future__ import annotations

import multiprocessing
from pathlib import Path

import pytest

from mma_ai.monitoring.cli import _run_viewer3d_process


def test_fr_015_fr_023_inv_002_ac_1_viewer3d_process_target_runs_under_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MMA_AI_FORCE_NO_DISPLAY", "1")
    context = multiprocessing.get_context("spawn")
    process = context.Process(
        target=_run_viewer3d_process,
        args=(str(tmp_path),),
    )
    process.start()
    process.join(timeout=15)

    if process.is_alive():
        process.terminate()
        process.join(timeout=5)
    assert not process.is_alive(), "Tiến trình spawn không kết thúc trong 15 giây."
    assert process.exitcode == 0
