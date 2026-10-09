"""Kiểm thử logger chỉ số."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

EventAccumulator = pytest.importorskip(
    "tensorboard.backend.event_processing.event_accumulator"
).EventAccumulator


_SIX_MUSCLES = ("TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA")


def _logger(run_dir: Path) -> Any:
    from mma_ai.learning.metrics_log import MetricsLogger

    return MetricsLogger(run_dir, _SIX_MUSCLES)


def _log_one_update(logger: Any) -> None:
    logger.log_update(
        update=3,
        env_steps=6144,
        policy_loss=0.12,
        value_loss=0.34,
        entropy=0.56,
        mean_return=7.8,
        activations=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6),
        env_steps_per_second=42.0,
    )


def test_fr_010_nfr_rel_001_writes_tfevents_and_jsonl_lines(tmp_path: Path) -> None:
    """FR-010, NFR-REL-001: mỗi lượt có đủ bản ghi TensorBoard và JSONL."""
    logger = _logger(tmp_path)
    _log_one_update(logger)
    logger.close()

    record = json.loads((tmp_path / "metrics.jsonl").read_text(encoding="utf-8"))
    assert record["update"] == 3
    assert record["env_steps"] == 6144
    assert record["loss/policy"] == 0.12
    assert record["throughput/env_steps_per_second"] == 42.0

    accumulator = EventAccumulator(str(tmp_path / "tb"))
    accumulator.Reload()
    assert {
        "loss/policy",
        "loss/value",
        "loss/entropy",
        "reward/mean_return",
        "throughput/env_steps_per_second",
    }.issubset(accumulator.Tags()["scalars"])


def test_fr_010_activation_tags_for_six_muscles(tmp_path: Path) -> None:
    """FR-010: logger dùng đúng sáu tên cơ do hồ sơ mô hình cung cấp."""
    logger = _logger(tmp_path)
    _log_one_update(logger)
    logger.close()

    accumulator = EventAccumulator(str(tmp_path / "tb"))
    accumulator.Reload()
    assert {f"activation/{name}" for name in _SIX_MUSCLES}.issubset(
        accumulator.Tags()["scalars"]
    )


def test_inv_004_nonfinite_scalar_rejected_without_partial_write(tmp_path: Path) -> None:
    """INV-004: NaN/Inf bị từ chối trước mọi ghi cho lượt cập nhật đó."""
    from mma_ai.learning.errors import NonFiniteError

    logger = _logger(tmp_path)
    _log_one_update(logger)
    with pytest.raises(NonFiniteError, match="loss/policy"):
        logger.log_update(
            update=4,
            env_steps=8192,
            policy_loss=float("nan"),
            value_loss=0.34,
            entropy=0.56,
            mean_return=7.8,
            activations=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6),
            env_steps_per_second=42.0,
        )
    logger.close()

    assert len((tmp_path / "metrics.jsonl").read_text(encoding="utf-8").splitlines()) == 1
