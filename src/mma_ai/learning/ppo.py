"""Lõi cập nhật PPO cho policy liên tục."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from torch import Tensor
from torch.nn import functional as functional

from mma_ai.learning.errors import NonFiniteError
from mma_ai.learning.networks import ActorCritic
from mma_ai.learning.train_config import TrainConfig


def compute_gae(
    rewards: Tensor,
    values: Tensor,
    dones: Tensor,
    last_value: float,
    gamma: float,
    gae_lambda: float,
) -> Tensor:
    advantages = torch.empty_like(rewards)
    carry = torch.zeros((), dtype=values.dtype, device=values.device)
    final_value = torch.tensor(last_value, dtype=values.dtype, device=values.device)
    for index in range(rewards.shape[0] - 1, -1, -1):
        next_value = final_value if index == rewards.shape[0] - 1 else values[index + 1]
        alive = (~dones[index].bool()).to(dtype=values.dtype)
        delta = rewards[index] + gamma * next_value * alive - values[index]
        carry = delta + gamma * gae_lambda * alive * carry
        advantages[index] = carry
    return advantages


def clipped_policy_loss(
    log_probs: Tensor, old_log_probs: Tensor, advantages: Tensor, clip_range: float
) -> Tensor:
    ratio = torch.exp(log_probs - old_log_probs)
    unclipped = ratio * advantages
    clipped = torch.clamp(ratio, 1 - clip_range, 1 + clip_range) * advantages
    return -torch.minimum(unclipped, clipped).mean()


@dataclass(frozen=True)
class UpdateStats:
    """Chỉ số số học của một lượt cập nhật PPO."""

    policy_loss: float
    value_loss: float
    entropy: float
    grad_norm: float
    nan_count: int
    inf_count: int


class PPOAgent:
    """Cập nhật Adam cho policy PPO theo cấu hình huấn luyện."""

    def __init__(self, model: ActorCritic, cfg: TrainConfig) -> None:
        self.model = model
        self.cfg = cfg
        self.optimizer = torch.optim.Adam(model.parameters(), lr=cfg.ppo.learning_rate)
        self._rng = np.random.default_rng(cfg.seed)

    def update(self, buffer: Mapping[str, Tensor]) -> UpdateStats:
        """Xáo minibatch seed cố định và thực hiện nhiều epoch PPO."""
        required = ("observations", "actions", "old_log_probs", "returns", "advantages")
        if any(key not in buffer for key in required):
            raise ValueError("Rollout PPO thiếu trường bắt buộc.")
        observations = buffer["observations"]
        actions = buffer["actions"]
        old_log_probs = buffer["old_log_probs"]
        returns = buffer["returns"]
        advantages = buffer["advantages"]
        _reject_nonfinite(
            (observations, actions, old_log_probs, returns, advantages), "rollout PPO"
        )
        if torch.any(actions <= 0) or torch.any(actions >= 1):
            raise ValueError("Action PPO phải nằm trong khoảng mở (0, 1).")
        losses: list[tuple[float, float, float]] = []
        norms: list[float] = []
        for _ in range(self.cfg.schedule.n_epochs):
            for indices in self._minibatches(observations.shape[0]):
                result, norm = self._update_one(
                    observations, actions, old_log_probs, returns, advantages, indices
                )
                losses.append(result)
                norms.append(norm)
        policy_loss, value_loss, entropy = np.mean(losses, axis=0).tolist()
        return UpdateStats(policy_loss, value_loss, entropy, max(norms), 0, 0)

    def _minibatches(self, size: int) -> list[np.ndarray[Any, Any]]:
        order = self._rng.permutation(size)
        width = self.cfg.schedule.batch_size
        return [order[start : start + width] for start in range(0, size, width)]

    def _update_one(
        self,
        observations: Tensor,
        actions: Tensor,
        old_log_probs: Tensor,
        returns: Tensor,
        advantages: Tensor,
        indices: np.ndarray[Any, Any],
    ) -> tuple[tuple[float, float, float], float]:
        index = torch.as_tensor(indices, dtype=torch.long, device=observations.device)
        observation_batch = observations.index_select(0, index)
        action_batch = actions.index_select(0, index)
        old_log_batch = old_log_probs.index_select(0, index)
        return_batch = returns.index_select(0, index)
        advantage_batch = advantages.index_select(0, index)
        mean = self.model.actor(observation_batch)
        values = self.model.critic(observation_batch).squeeze(-1)
        distribution = torch.distributions.Normal(mean, self.model.log_std.exp().expand_as(mean))
        new_log_probs = distribution.log_prob(torch.logit(action_batch)).sum(dim=-1)
        policy_loss = clipped_policy_loss(
            new_log_probs, old_log_batch, advantage_batch, self.cfg.ppo.clip_range
        )
        value_loss = functional.mse_loss(values, return_batch)
        entropy = distribution.entropy().sum(dim=-1).mean()
        loss = (
            policy_loss + self.cfg.ppo.value_coef * value_loss - self.cfg.ppo.entropy_coef * entropy
        )
        _reject_nonfinite((loss, policy_loss, value_loss, entropy), "loss PPO")
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.cfg.ppo.max_grad_norm)
        norm = _gradient_norm(self.model.parameters())
        self.optimizer.step()
        _reject_nonfinite(tuple(self.model.parameters()), "tham số PPO")
        return (
            float(policy_loss.detach()),
            float(value_loss.detach()),
            float(entropy.detach()),
        ), norm

    def state_dict(self) -> dict[str, Any]:
        """Xuất actor, critic, log_std và optimizer cho checkpoint."""
        return {
            "actor": self.model.actor.state_dict(),
            "critic": self.model.critic.state_dict(),
            "log_std": self.model.log_std.detach().clone(),
            "optimizer": self.optimizer.state_dict(),
        }

    def load_state_dict(self, state: Mapping[str, Any]) -> None:
        """Khôi phục trạng thái PPO đã được kiểm tra tại ranh giới checkpoint."""
        required = ("actor", "critic", "log_std", "optimizer")
        if any(key not in state for key in required):
            raise ValueError("Trạng thái PPO thiếu trường bắt buộc.")
        self.model.actor.load_state_dict(state["actor"])
        self.model.critic.load_state_dict(state["critic"])
        self.model.log_std.data.copy_(state["log_std"])
        self.optimizer.load_state_dict(state["optimizer"])
        _reject_nonfinite(tuple(self.model.parameters()), "tham số PPO đã nạp")


def _gradient_norm(parameters: Any) -> float:
    squares = [
        parameter.grad.detach().pow(2).sum()
        for parameter in parameters
        if parameter.grad is not None
    ]
    return 0.0 if not squares else float(torch.sqrt(torch.stack(squares).sum()))


def _reject_nonfinite(tensors: tuple[Tensor, ...], component: str) -> None:
    nan_count = sum(int(torch.isnan(tensor).sum()) for tensor in tensors)
    inf_count = sum(int(torch.isinf(tensor).sum()) for tensor in tensors)
    if nan_count or inf_count:
        raise NonFiniteError(f"{component} chứa {nan_count} NaN và {inf_count} giá trị vô cực.")
