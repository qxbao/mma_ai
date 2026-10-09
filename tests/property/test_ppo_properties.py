"""Kiểm thử thuộc tính cho lõi số học PPO."""

from __future__ import annotations

import importlib.util
import random

import pytest


def test_regress_tdd_red_ppo_module_is_present() -> None:
    """FR-002: property suite kiểm mô-đun PPO đã tồn tại."""
    assert importlib.util.find_spec("mma_ai.learning.ppo") is not None


def test_inv_004_gae_generated_values() -> None:
    """INV-004: GAE bảo toàn định dạng rollout hữu hạn."""
    torch = pytest.importorskip("torch")
    from mma_ai.learning.ppo import compute_gae

    generator = random.Random(20261010)
    rewards = [generator.uniform(-3.0, 3.0) for _ in range(100)]
    values = [generator.uniform(-2.0, 2.0) for _ in range(100)]
    dones = [generator.choice((False, False, True)) for _ in range(100)]
    actual = compute_gae(
        torch.tensor(rewards), torch.tensor(values), torch.tensor(dones), 0.0, 0.97, 0.91
    )
    reference = [0.0] * 100
    carry = 0.0
    for index in range(99, -1, -1):
        successor = 0.0 if index == 99 else values[index + 1]
        alive = 0.0 if dones[index] else 1.0
        delta = rewards[index] + 0.97 * successor * alive - values[index]
        carry = delta + 0.97 * 0.91 * alive * carry
        reference[index] = carry
    assert torch.allclose(actual, torch.tensor(reference), atol=1e-5)
