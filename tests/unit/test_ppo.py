"""Kiểm thử đơn vị cho cập nhật PPO."""

from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from typing import Any

import pytest


def test_regress_tdd_red_ppo_module_is_present() -> None:
    """FR-002: mô-đun PPO phải được đóng gói."""
    assert importlib.util.find_spec("mma_ai.learning.ppo") is not None


def _torch() -> Any:
    return pytest.importorskip("torch")


def test_gae_matches_hand_computed() -> None:
    """FR-002: GAE khớp phép tính tay khi episode kết thúc ở bước cuối."""
    torch = _torch()
    from mma_ai.learning.ppo import compute_gae

    rewards = torch.tensor([1.0, 1.0])
    values = torch.tensor([0.5, 0.25])
    dones = torch.tensor([False, True])

    advantages = compute_gae(rewards, values, dones, last_value=0.9, gamma=0.99, gae_lambda=0.95)

    assert torch.allclose(advantages, torch.tensor([1.452875, 0.75]), atol=1e-6)


def test_clip_objective_matches_reference() -> None:
    """FR-002: objective PPO dùng đúng nhánh clip cho advantage dương và âm."""
    torch = _torch()
    from mma_ai.learning.ppo import clipped_policy_loss

    loss = clipped_policy_loss(
        torch.log(torch.tensor([2.0, 0.5, 4.0])),
        torch.zeros(3),
        torch.tensor([1.0, 1.0, -1.0]),
        clip_range=0.2,
    )

    assert loss.item() == pytest.approx(2.3 / 3.0)


def _batch(
    agent: Any, observation_dim: int, count: int, advantage_scale: float = 1.0
) -> dict[str, Any]:
    torch = _torch()
    observations = torch.zeros((count, observation_dim))
    with torch.no_grad():
        actions, old_log_probs, values = agent.model.act(observations, deterministic=False)
    return {
        "observations": observations,
        "actions": actions,
        "old_log_probs": old_log_probs,
        "returns": values + 1.0,
        "advantages": torch.full((count,), advantage_scale),
    }


def test_grad_norm_after_clip_le_threshold() -> None:
    """FR-004, AC-6: chuẩn gradient sau clipping không vượt ngưỡng cấu hình."""
    torch = _torch()
    from mma_ai.learning.networks import ActorCritic
    from mma_ai.learning.ppo import PPOAgent
    from mma_ai.learning.train_config import TrainConfig

    config = TrainConfig.load()
    model = ActorCritic(obs_dim=3, act_dim=2, cfg=config)
    agent = PPOAgent(model, config)

    stats = agent.update(_batch(agent, observation_dim=3, count=16, advantage_scale=1_000_000.0))

    assert stats.grad_norm <= config.ppo.max_grad_norm + 1e-6
    assert torch.isfinite(torch.tensor(stats.grad_norm))


def test_update_stats_finite() -> None:
    """NFR-REL-001: thống kê loss và đếm NaN/Inf sau cập nhật hữu hạn."""
    torch = _torch()
    from mma_ai.learning.networks import ActorCritic
    from mma_ai.learning.ppo import PPOAgent
    from mma_ai.learning.train_config import TrainConfig

    config = TrainConfig.load()
    agent = PPOAgent(ActorCritic(obs_dim=3, act_dim=2, cfg=config), config)

    stats = agent.update(_batch(agent, observation_dim=3, count=16))

    assert torch.isfinite(torch.tensor([stats.policy_loss, stats.value_loss, stats.entropy])).all()
    assert stats.nan_count == 0
    assert stats.inf_count == 0


class _ToyActivationEnv:
    """Môi trường Gymnasium tối giản có reward theo kích thích đầu tiên."""

    def reset(self) -> tuple[Any, dict[str, Any]]:
        torch = _torch()
        return torch.zeros(3), {}

    def step(self, action: Any) -> tuple[Any, float, bool, bool, dict[str, Any]]:
        torch = _torch()
        reward = float(action[0].item())
        return torch.zeros(3), reward, True, False, {}


def _toy_batches(agent: Any) -> Iterator[dict[str, Any]]:
    torch = _torch()
    for _ in range(8):
        observations = torch.zeros((32, 3))
        actions = torch.full((32, 2), 0.9)
        raw_actions = torch.logit(actions)
        with torch.no_grad():
            mean = agent.model.actor(observations)
            std = agent.model.log_std.exp().expand_as(mean)
            old_log_probs = torch.distributions.Normal(mean, std).log_prob(raw_actions).sum(dim=-1)
        yield {
            "observations": observations,
            "actions": actions,
            "old_log_probs": old_log_probs,
            "returns": torch.ones(32),
            "advantages": torch.ones(32),
        }


def test_learns_toy_env() -> None:
    """FR-002: PPO tăng reward trên môi trường Gymnasium đồ chơi tất định."""
    torch = _torch()
    from mma_ai.learning.networks import ActorCritic
    from mma_ai.learning.ppo import PPOAgent
    from mma_ai.learning.train_config import TrainConfig

    torch.manual_seed(7)
    environment = _ToyActivationEnv()
    config = TrainConfig.load()
    agent = PPOAgent(ActorCritic(obs_dim=3, act_dim=2, cfg=config), config)
    observation, _ = environment.reset()
    with torch.no_grad():
        before, _, _ = agent.model.act(observation.unsqueeze(0), deterministic=True)
    for batch in _toy_batches(agent):
        agent.update(batch)
    with torch.no_grad():
        after, _, _ = agent.model.act(observation.unsqueeze(0), deterministic=True)

    assert environment.step(after[0])[1] > environment.step(before[0])[1]
