"""Tiện ích tái lập (reproducibility) cho huấn luyện PPO."""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from mma_ai.learning.manifest import read_manifest


@dataclass(frozen=True)
class ReproReport:
    """Kết quả so sánh hai lượt huấn luyện."""

    comparable: bool
    matches: bool | None
    reason: str | None


def _reproducibility(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    value = manifest.get("reproducibility")
    if not isinstance(value, Mapping):
        raise ValueError("Hồ sơ thiếu thông tin tái lập.")
    return value


def _device_kind(manifest: Mapping[str, Any]) -> str:
    reproducibility = _reproducibility(manifest)
    value = reproducibility.get("device_kind")
    if isinstance(value, str):
        return value
    device = manifest.get("device")
    if isinstance(device, Mapping) and isinstance(device.get("kind"), str):
        return str(device["kind"])
    raise ValueError("Hồ sơ thiếu loại thiết bị.")


def _not_comparable(reason: str) -> ReproReport:
    return ReproReport(comparable=False, matches=None, reason=reason)


def compare_manifests(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> ReproReport:
    """So sánh các giá trị tái lập đã được parse từ hai hồ sơ."""
    first_repro = _reproducibility(first)
    second_repro = _reproducibility(second)

    if _device_kind(first) != _device_kind(second):
        return _not_comparable("Hai lượt chạy dùng loại thiết bị khác nhau.")
    if first.get("library_versions") != second.get("library_versions"):
        return _not_comparable("Hai lượt chạy dùng phiên bản thư viện khác nhau.")
    if first_repro.get("torch_threads") != second_repro.get("torch_threads"):
        return _not_comparable("Hai lượt chạy dùng số luồng Torch khác nhau.")

    tolerance = float(first_repro["rel_tolerance"])
    if tolerance <= 0.0 or not math.isfinite(tolerance):
        raise ValueError("Dung sai tương đối trong hồ sơ phải hữu hạn và dương.")

    first_metrics = first.get("reward_metrics")
    second_metrics = second.get("reward_metrics")
    if not isinstance(first_metrics, Mapping) or not isinstance(second_metrics, Mapping):
        raise ValueError("Hồ sơ thiếu số đo phần thưởng.")
    first_returns = first_metrics.get("head_mean_return")
    second_returns = second_metrics.get("head_mean_return")
    if not isinstance(first_returns, list) or not isinstance(second_returns, list):
        raise ValueError("Hồ sơ thiếu chuỗi head_mean_return.")
    if len(first_returns) != len(second_returns):
        return ReproReport(True, False, "Hai lượt chạy có số điểm đầu khác nhau.")

    for index, (first_value, second_value) in enumerate(zip(first_returns, second_returns)):
        expected = float(first_value)
        actual = float(second_value)
        if not math.isfinite(expected) or not math.isfinite(actual):
            return ReproReport(True, False, f"Điểm đầu {index} không hữu hạn.")
        if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=0.0):
            return ReproReport(
                True,
                False,
                f"Điểm đầu {index} vượt dung sai tương đối {tolerance:g}.",
            )
    return ReproReport(True, True, None)


def compare_runs(run_a: str | Path | Any, run_b: str | Path | Any) -> ReproReport:
    """Đọc hai hồ sơ rồi so sánh tính tái lập của chúng."""
    return compare_manifests(read_manifest(run_a), read_manifest(run_b))


def _torch_threads(cfg: Any) -> int:
    reproducibility = getattr(cfg, "reproducibility", cfg)
    threads = getattr(reproducibility, "torch_threads")
    if not isinstance(threads, int) or threads < 1:
        raise ValueError("Số luồng Torch phải là số nguyên dương.")
    return threads


def seed_everything(seed: int, cfg: Any) -> np.random.Generator:
    """Đặt seed gốc cho NumPy và Torch, rồi trả bộ sinh cho PPO."""
    if not isinstance(seed, int) or seed < 0:
        raise ValueError("Seed phải là số nguyên không âm.")

    import torch

    torch.manual_seed(seed)
    torch.set_num_threads(_torch_threads(cfg))
    torch.use_deterministic_algorithms(True)
    if torch.cuda.is_available():
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        torch.cuda.manual_seed_all(seed)
    return np.random.default_rng(seed)
