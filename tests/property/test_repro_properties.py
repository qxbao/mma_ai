"""Kiểm thử thuộc tính cho mô-đun tái lập."""

from __future__ import annotations

import numpy as np


def test_inv_004_relative_tolerance_property() -> None:
    """INV-004, NFR-REPRO-001: Mẫu trong dung sai luôn tương đương."""
    from mma_ai.learning.repro import compare_manifests

    generator = np.random.default_rng(20261010)
    tolerance = 1e-6
    for _ in range(150):
        baseline = generator.uniform(-1_000.0, 1_000.0, size=7)
        scale = np.maximum(np.abs(baseline), 1.0)
        delta = generator.uniform(-0.9, 0.9, size=7) * tolerance * scale
        first = {
            "reward_metrics": {"head_mean_return": baseline.tolist()},
            "reproducibility": {"rel_tolerance": tolerance, "torch_threads": 1},
            "device": {"kind": "cpu"},
            "library_versions": {"torch": "2.0", "numpy": "1.0"},
        }
        second = {
            **first,
            "reward_metrics": {"head_mean_return": (baseline + delta).tolist()},
        }
        report = compare_manifests(first, second)
        assert report.comparable is True
        assert report.matches is True


def teardown_module() -> None:
    """Dọn dẹp các mô-đun trì hoãn để bảo vệ ranh giới kiểm thử."""
    import sys

    sys.modules.pop("mma_ai.learning.repro", None)
    sys.modules.pop("mma_ai.learning", None)

