"""Kiểm thử thuộc tính của mạng actor-critic."""

from __future__ import annotations

import random

import pytest

torch = pytest.importorskip("torch")


def test_inv_002_generated_observations_always_produce_open_unit_actions() -> None:
    """INV-002: 100 lô observation hữu hạn luôn sinh action nằm trong khoảng mở đơn vị."""
    from mma_ai.learning.networks import ActorCritic
    from mma_ai.learning.train_config import TrainConfig

    generator = random.Random(20261010)
    model = ActorCritic(obs_dim=4, act_dim=6, cfg=TrainConfig.load())
    observations = torch.tensor(
        [[generator.uniform(-1_000.0, 1_000.0) for _ in range(4)] for _ in range(100)]
    )

    action, log_prob, value = model.act(observations, deterministic=False)

    assert action.shape == (100, 6)
    assert torch.all(action > 0)
    assert torch.all(action < 1)
    assert torch.isfinite(log_prob).all()
    assert torch.isfinite(value).all()
