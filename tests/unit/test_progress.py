"""Kiểm thử ghi ảnh chụp tiến trình cho giao diện chỉ đọc."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator, FormatChecker


def _snapshot(*, history_size: int = 4) -> dict[str, Any]:
    """Tạo ảnh chụp hoàn chỉnh nhưng chưa có mốc thời gian do writer sở hữu."""
    return {
        "schema_version": "1.0.0",
        "run_id": "20261010T010101Z_elbow_s42",
        "stage": "elbow",
        "seed": 42,
        "status": "running",
        "update_idx": 1,
        "env_steps": 2048,
        "total_steps": 4096,
        "env_steps_per_second": 25.0,
        "mean_return": None,
        "loss": None,
        "activation": None,
        "checkpoint": {
            "count": 0,
            "every_updates": 1,
            "last_path": None,
            "last_update_idx": None,
        },
        "history": {
            "env_steps": list(range(history_size)),
            "mean_return": [None if item == 0 else float(item) for item in range(history_size)],
            "value_loss": [None if item == 0 else float(item) / 10 for item in range(history_size)],
        },
    }


def _writer(run_dir: Path, *, interval: float = 1.0, points: int = 3, clock: Any = None) -> Any:
    from mma_ai.learning.progress import ProgressWriter

    return ProgressWriter(run_dir, snapshot_interval_s=interval, history_points=points, clock=clock)


def _schema() -> dict[str, Any]:
    path = (
        Path(__file__).parents[2]
        / "specs/003-ppo-train-repro/contracts/progress-snapshot.schema.json"
    )
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_fr_020_nfr_perf_002_snapshot_atomic_and_schema(tmp_path: Path) -> None:
    """FR-020, NFR-PERF-002: tệp công khai luôn là JSON hoàn chỉnh đúng schema."""
    writer = _writer(tmp_path, interval=0.0)
    assert writer.write(_snapshot()) is True

    target = tmp_path / "progress.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    Draft202012Validator(_schema(), format_checker=FormatChecker()).validate(payload)
    assert not (tmp_path / "progress.json.tmp").exists()


def test_fr_020_min_interval_respected(tmp_path: Path) -> None:
    """FR-020: ảnh chụp trung gian trong khoảng tối thiểu không thay thế tệp."""
    moments = iter((100.0, 100.2, 101.0))
    writer = _writer(tmp_path, interval=1.0, clock=lambda: next(moments))
    assert writer.write(_snapshot()) is True
    first = (tmp_path / "progress.json").read_bytes()
    assert writer.write(_snapshot()) is False
    assert (tmp_path / "progress.json").read_bytes() == first
    assert writer.write(_snapshot()) is True


def test_fr_020_history_truncated(tmp_path: Path) -> None:
    """FR-020: các chuỗi history đồng bộ và chỉ giữ các điểm mới nhất."""
    writer = _writer(tmp_path, interval=0.0, points=3)
    writer.write(_snapshot(history_size=6))

    history = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))["history"]
    assert history["env_steps"] == [3, 4, 5]
    assert history["mean_return"] == [3.0, 4.0, 5.0]
    assert history["value_loss"] == [0.3, 0.4, 0.5]


def test_fr_020_timestamp_monotonic_when_clock_moves_backwards(tmp_path: Path) -> None:
    """FR-020: timestamp_utc không giảm dù đồng hồ hệ điều hành bị lùi."""
    moments = iter((200.0, 100.0))
    writer = _writer(tmp_path, interval=0.0, clock=lambda: next(moments))
    writer.write(_snapshot())
    first = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))["timestamp_utc"]
    writer.write(_snapshot())
    second = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))["timestamp_utc"]
    assert second >= first


def test_fr_020_final_snapshot_always_written(tmp_path: Path) -> None:
    """FR-020: ảnh chụp cuối vượt qua giới hạn khoảng cách ghi."""
    writer = _writer(tmp_path, interval=1000.0, clock=lambda: 100.0)
    assert writer.write(_snapshot()) is True
    final = _snapshot()
    final["status"] = "done"
    assert writer.write(final, final=True) is True
    assert json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))["status"] == "done"
