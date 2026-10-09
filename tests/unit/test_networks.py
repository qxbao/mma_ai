"""Kiểm thử mạng actor-critic của PPO."""

from __future__ import annotations

import importlib.util
from dataclasses import replace
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from mma_ai.learning.train_config import TrainConfig


def _config() -> TrainConfig:
    from mma_ai.learning.train_config import TrainConfig

    return TrainConfig.load()


def _torch() -> Any:
    return pytest.importorskip("torch")


def test_regress_tdd_red_network_module_is_present() -> None:
    """FR-002: mô-đun mạng phải được đóng gói để PPO có implementation thực."""
    assert importlib.util.find_spec("mma_ai.learning.networks") is not None


def test_actor_critic_2x256() -> None:
    """FR-002: mạng mặc định có hai lớp ẩn rộng 256 ở mỗi nhánh."""
    torch = _torch()
    from mma_ai.learning.networks import ActorCritic
    model = ActorCritic(obs_dim=11, act_dim=6, cfg=_config())

    for branch in (model.actor, model.critic):
        layers = [layer for layer in branch if isinstance(layer, torch.nn.Linear)]
        assert [(layer.in_features, layer.out_features) for layer in layers] == [
            (11, 256),
            (256, 256),
            (256, 6 if branch is model.actor else 1),
        ]
    assert model.log_std.shape == (6,)


def test_custom_structure_follows_config() -> None:
    """FR-002: độ rộng từng nhánh lấy từ cấu hình, không hằng số rải trong mã."""
    torch = _torch()
    from mma_ai.learning.networks import ActorCritic
    cfg = _config()
    network = replace(cfg.network, actor_hidden=(7, 3, 2), critic_hidden=(5,))
    model = ActorCritic(obs_dim=4, act_dim=6, cfg=replace(cfg, network=network))

    actor_layers = [layer for layer in model.actor if isinstance(layer, torch.nn.Linear)]
    critic_layers = [layer for layer in model.critic if isinstance(layer, torch.nn.Linear)]
    assert [(layer.in_features, layer.out_features) for layer in actor_layers] == [
        (4, 7),
        (7, 3),
        (3, 2),
        (2, 6),
    ]
    assert [(layer.in_features, layer.out_features) for layer in critic_layers] == [(4, 5), (5, 1)]


def test_action_always_in_unit_interval() -> None:
    """INV-002: logits cực trị vẫn tạo kích thích cơ trong khoảng mở đơn vị."""
    torch = _torch()
    from mma_ai.learning.networks import ActorCritic
    model = ActorCritic(obs_dim=3, act_dim=6, cfg=_config())
    for parameter in model.actor.parameters():
        parameter.data.zero_()
    final_layer = [layer for layer in model.actor if isinstance(layer, torch.nn.Linear)][-1]
    final_layer.bias.data.copy_(torch.tensor([1e6, -1e6, 1e6, -1e6, 1e6, -1e6]))

    action, _, _ = model.act(torch.zeros(2, 3), deterministic=True)

    assert torch.all(action > 0)
    assert torch.all(action < 1)


def test_deterministic_action_is_sigmoid_of_mean() -> None:
    """FR-005: chế độ xác định dùng mean thô rồi biến đổi sigmoid."""
    torch = _torch()
    from mma_ai.learning.networks import ActorCritic
    model = ActorCritic(obs_dim=3, act_dim=6, cfg=_config())
    observation = torch.tensor([[0.25, -0.5, 0.75]])
    expected = torch.sigmoid(model.actor(observation))

    action, _, value = model.act(observation, deterministic=True)

    assert torch.allclose(action, expected)
    assert value.shape == (1,)


def test_nonfinite_raw_network_output_raises() -> None:
    """FR-005: đầu ra thô NaN không được chuyển thành action hợp lệ."""
    torch = _torch()
    from mma_ai.learning.errors import NonFiniteError
    from mma_ai.learning.networks import ActorCritic

    model = ActorCritic(obs_dim=3, act_dim=6, cfg=_config())
    final_layer = [layer for layer in model.actor if isinstance(layer, torch.nn.Linear)][-1]
    final_layer.bias.data.fill_(float("nan"))

    with pytest.raises(NonFiniteError):
        model.act(torch.zeros(1, 3), deterministic=True)
