"""Mạng actor-critic cho policy PPO liên tục."""

# mypy: disable-error-code=misc

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, cast

import torch
from torch import Tensor, nn

from mma_ai.learning.errors import NonFiniteError
from mma_ai.learning.train_config import TrainConfig


def _make_mlp(input_dim: int, hidden_dims: Sequence[int], output_dim: int) -> nn.Sequential:
    layers: list[nn.Module] = []
    previous_dim = input_dim
    for hidden_dim in hidden_dims:
        layers.extend((nn.Linear(previous_dim, hidden_dim), nn.Tanh()))
        previous_dim = hidden_dim
    layers.append(nn.Linear(previous_dim, output_dim))
    return nn.Sequential(*layers)


class _Distribution(Protocol):
    def log_prob(self, value: Tensor) -> Tensor: ...

    def rsample(self) -> Tensor: ...


class ActorCritic(nn.Module):
    """Policy Gaussian với action kích thích cơ được giới hạn trong khoảng đơn vị."""

    def __init__(self, obs_dim: int, act_dim: int, cfg: TrainConfig) -> None:
        super().__init__()
        self.actor = _make_mlp(obs_dim, cfg.network.actor_hidden, act_dim)
        self.critic = _make_mlp(obs_dim, cfg.network.critic_hidden, 1)
        self.log_std = nn.Parameter(torch.full((act_dim,), cfg.network.log_std_init))

    def act(self, obs: Tensor, deterministic: bool) -> tuple[Tensor, Tensor, Tensor]:
        """Sinh action, log-probability của biến Gaussian thô và giá trị critic."""
        mean = self.actor(obs)
        value = self.critic(obs).squeeze(-1)
        if not torch.isfinite(mean).all() or not torch.isfinite(value).all():
            raise NonFiniteError("Đầu ra thô của actor hoặc critic chứa NaN hay vô cực.")

        std = self.log_std.exp().expand_as(mean)
        if not torch.isfinite(std).all():
            raise NonFiniteError("Độ lệch chuẩn của policy chứa NaN hay vô cực.")
        distribution = cast(_Distribution, torch.distributions.Normal(mean, std))
        raw_action = mean if deterministic else distribution.rsample()
        if not torch.isfinite(raw_action).all():
            raise NonFiniteError("Action thô của policy chứa NaN hay vô cực.")

        action = torch.sigmoid(raw_action)
        lower_bound = torch.nextafter(torch.zeros_like(action), torch.ones_like(action))
        upper_bound = torch.nextafter(torch.ones_like(action), torch.zeros_like(action))
        action = torch.maximum(torch.minimum(action, upper_bound), lower_bound)
        log_prob = distribution.log_prob(raw_action).sum(dim=-1)
        if not torch.isfinite(log_prob).all():
            raise NonFiniteError("Log-probability của policy chứa NaN hay vô cực.")
        return action, log_prob, value
