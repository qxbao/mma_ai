"""Kiểm thử tích hợp cấu hình mạng actor-critic qua cấu hình mặc định và hồ sơ.

Tệp: test_network_config.py. Hiện thực và kiểm chứng các yêu cầu và bất biến theo T335 (US6/AC-6):
- FR-002, SC-006, AC-6: Chính sách học tăng cường (reinforcement learning - RL) PPO gồm
  mạng diễn viên (actor network) MLP 2 lớp ẩn × 256 và mạng đánh giá (critic network)
  MLP 2 lớp ẩn × 256 từ cấu hình mặc định đóng gói (train_elbow.yaml); cấu trúc mạng đọc từ
  cấu hình, không rải hằng số trong mã nguồn.
- FR-003, AC-6, INV-004: Bộ chuẩn hoá quan sát (observation normalizer) ước lượng thống kê
  trong lúc huấn luyện và được lưu trữ đầy đủ trong trạng thái điểm kiểm tra (checkpoint).
- FR-004, AC-6: Cắt ngắn gradient (gradient clipping) được áp dụng tại mỗi bước cập nhật với
  ngưỡng cấu hình được; chuẩn gradient sau clipping không vượt quá max_grad_norm ngay cả khi
  gradient lớn cố ý.
- SC-006, AC-6: Cấu hình khai độ rộng hoặc số lớp khác tạo ra mạng thực tế đúng cấu hình,
  và hồ sơ thí nghiệm lượt chạy (run manifest) ghi nhận chính xác cấu trúc mạng đã sử dụng.
- INV-002: Hành động đưa vào môi trường luôn nằm trong khoảng mở (0, 1)^6; tuyệt đối không có
  đường điều khiển trực tiếp lực hay toạ độ tay.
"""

from __future__ import annotations

import importlib.resources
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from jsonschema import Draft202012Validator
from train_fixtures import (
    list_runs,
    load_manifest,
    load_schema_registry,
    run_train_cli,
    sample_observations,
    smoke_config,
)

from mma_ai.learning.errors import TrainConfigError
from mma_ai.learning.train_config import TrainConfig


def _torch() -> Any:
    """Nạp thư viện torch hoặc bỏ qua kiểm thử nếu thiếu phụ thuộc tuỳ chọn."""
    return pytest.importorskip(
        "torch",
        reason="Cần phụ thuộc rl (torch) để kiểm thử mạng actor-critic",
    )


def _load_manifest_schema() -> dict[str, Any]:
    """Nạp tệp JSON Schema của run-manifest.schema.json từ thư mục contracts."""
    candidate_paths = [
        Path.cwd() / "specs/003-ppo-train-repro/contracts/run-manifest.schema.json",
        Path(__file__).resolve().parents[2]
        / "specs/003-ppo-train-repro/contracts/run-manifest.schema.json",
    ]
    for p in candidate_paths:
        if p.is_file():
            loaded = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                return loaded
    raise FileNotFoundError("Không tìm thấy tệp run-manifest.schema.json trong thư mục contracts")


def test_network_config_contract_independent_assertion() -> None:
    """FR-002, FR-003, FR-004, SC-006, AC-6: Khẳng định độc lập trên base về cấu hình mạng.

    Đảm bảo kiểm thử không bị bỏ qua toàn bộ khi môi trường thiếu phụ thuộc tuỳ chọn torch.
    Xác minh các mô-đun cốt lõi, tệp cấu hình mặc định đóng gói và các bất biến hợp đồng.
    """
    # 1. Xác minh sự tồn tại của các mô-đun cốt lõi trên hệ thống
    required_modules = [
        "mma_ai.learning.train_config",
        "mma_ai.learning.networks",
        "mma_ai.learning.normalizer",
        "mma_ai.learning.ppo",
        "mma_ai.learning.checkpoint",
        "mma_ai.learning.manifest",
    ]
    for mod in required_modules:
        assert importlib.util.find_spec(mod) is not None, f"Thiếu mô-đun {mod} trên base"

    # 2. Xác minh tệp cấu hình mặc định đóng gói train_elbow.yaml
    default_res = importlib.resources.files("mma_ai.learning").joinpath("train_elbow.yaml")
    assert default_res.is_file(), "Thiếu tệp cấu hình train_elbow.yaml đóng gói"
    raw_cfg = yaml.safe_load(default_res.read_text(encoding="utf-8"))
    assert isinstance(raw_cfg, dict), "Cấu hình YAML phải là ánh xạ (mapping)"

    # 3. Xác minh cấu trúc mạng mặc định theo master plan 9.1 và FR-002: 2 lớp ẩn × 256
    network_section = raw_cfg.get("network", {})
    assert network_section.get("actor_hidden") == [256, 256], (
        f"Kỳ vọng actor_hidden mặc định là [256, 256], nhận {network_section.get('actor_hidden')}"
    )
    assert network_section.get("critic_hidden") == [256, 256], (
        f"Kỳ vọng critic_hidden mặc định là [256, 256], nhận {network_section.get('critic_hidden')}"
    )
    assert network_section.get("activation") == "tanh", "Kỳ vọng hàm kích hoạt là tanh"
    assert network_section.get("log_std_init") == -0.5, "Kỳ vọng log_std_init mặc định là -0.5"

    # 4. Xác minh chuẩn hoá quan sát và cắt ngắn gradient trong cấu hình
    norm_section = raw_cfg.get("normalization", {})
    assert norm_section.get("normalize_obs") is True, "Kỳ vọng normalize_obs mặc định bật (True)"
    ppo_section = raw_cfg.get("ppo", {})
    assert ppo_section.get("max_grad_norm") == 0.5, "Kỳ vọng max_grad_norm mặc định là 0.5"

    # 5. Nạp cấu hình qua TrainConfig.load() để kiểm tra việc phân giải và thẩm định
    cfg = TrainConfig.load()
    assert cfg.network.actor_hidden == (256, 256)
    assert cfg.network.critic_hidden == (256, 256)
    assert cfg.network.activation == "tanh"
    assert cfg.normalization.normalize_obs is True
    assert cfg.ppo.max_grad_norm == 0.5

    # 6. INV-002: Không tồn tại trường điều khiển lực hay toạ độ tay trong cấu hình
    all_keys = set(raw_cfg.keys())
    for section in raw_cfg.values():
        if isinstance(section, dict):
            all_keys.update(section.keys())
    forbidden_terms = {"force", "torque", "hand_pos", "hand_coord", "direct_action"}
    for k in all_keys:
        for forbidden in forbidden_terms:
            assert forbidden not in k.lower(), f"Phát hiện trường cấm '{k}' vi phạm INV-002"


def test_actor_critic_2x256_from_default_config() -> None:
    """FR-002, SC-006, AC-6, INV-002: Dựng mạng actor-critic 2 lớp ẩn × 256 từ cấu hình mặc định.

    Xác minh:
    - Mạng diễn viên (actor) và mạng đánh giá (critic) đều có cấu trúc 2 lớp ẩn × 256.
    - Hàm kích hoạt giữa các lớp ẩn là Tanh.
    - Kích thước tham số log_std khớp số lượng cơ (6 cơ).
    - Phương thức act sinh hành động kích thích cơ luôn nằm trong khoảng mở (0, 1)^6.
    """
    torch = _torch()
    from mma_ai.learning.networks import ActorCritic

    # Nạp cấu hình mặc định đóng gói
    cfg = TrainConfig.load()
    obs_dim = 14  # Không gian quan sát 14 chiều của mô hình khuỷu tay
    act_dim = 6   # Không gian hành động kích thích 6 cơ bắp

    model = ActorCritic(obs_dim=obs_dim, act_dim=act_dim, cfg=cfg)

    # 1. Thẩm định kiến trúc mạng diễn viên (actor network)
    actor_linears = [layer for layer in model.actor if isinstance(layer, torch.nn.Linear)]
    assert len(actor_linears) == 3, (
        f"Kỳ vọng 3 lớp tuyến tính (2 ẩn + 1 ra), nhận {len(actor_linears)}"
    )
    expected_actor_shapes = [
        (obs_dim, 256),   # Lớp vào -> lớp ẩn 1 (256 chiều)
        (256, 256),       # Lớp ẩn 1 -> lớp ẩn 2 (256 chiều)
        (256, act_dim),   # Lớp ẩn 2 -> lớp đầu ra hành động (6 cơ)
    ]
    actual_actor_shapes = [(layer.in_features, layer.out_features) for layer in actor_linears]
    assert actual_actor_shapes == expected_actor_shapes, (
        f"Kích thước lớp actor không khớp: kỳ vọng {expected_actor_shapes}, "
        f"nhận {actual_actor_shapes}"
    )

    # Kiểm tra các hàm kích hoạt giữa các lớp ẩn
    actor_activations = [layer for layer in model.actor if isinstance(layer, torch.nn.Tanh)]
    assert len(actor_activations) == 2, "Kỳ vọng 2 lớp kích hoạt Tanh giữa 2 lớp ẩn của actor"

    # 2. Thẩm định kiến trúc mạng đánh giá (critic network)
    critic_linears = [layer for layer in model.critic if isinstance(layer, torch.nn.Linear)]
    assert len(critic_linears) == 3, (
        f"Kỳ vọng 3 lớp tuyến tính (2 ẩn + 1 ra), nhận {len(critic_linears)}"
    )
    expected_critic_shapes = [
        (obs_dim, 256),   # Lớp vào -> lớp ẩn 1 (256 chiều)
        (256, 256),       # Lớp ẩn 1 -> lớp ẩn 2 (256 chiều)
        (256, 1),         # Lớp ẩn 2 -> lớp đầu ra giá trị vô hướng (scalar value)
    ]
    actual_critic_shapes = [(layer.in_features, layer.out_features) for layer in critic_linears]
    assert actual_critic_shapes == expected_critic_shapes, (
        f"Kích thước lớp critic không khớp: kỳ vọng {expected_critic_shapes}, "
        f"nhận {actual_critic_shapes}"
    )

    critic_activations = [layer for layer in model.critic if isinstance(layer, torch.nn.Tanh)]
    assert len(critic_activations) == 2, "Kỳ vọng 2 lớp kích hoạt Tanh giữa 2 lớp ẩn của critic"

    # 3. Thẩm định tham số độ lệch chuẩn logarit (log_std)
    assert model.log_std.shape == (act_dim,), "log_std phải có số chiều bằng số cơ bắp (6)"
    assert torch.allclose(model.log_std, torch.full((act_dim,), cfg.network.log_std_init)), (
        f"Giá trị khởi tạo log_std phải bằng {cfg.network.log_std_init}"
    )

    # 4. INV-002: Kiểm tra hành vi suy luận tất định và ngẫu nhiên với dữ liệu quan sát giả lập
    batch_size = 16
    dummy_obs = torch.randn(batch_size, obs_dim)

    # Chế độ tất định (deterministic inference)
    det_action, det_log_prob, det_val = model.act(dummy_obs, deterministic=True)
    assert det_action.shape == (batch_size, act_dim)
    assert det_val.shape == (batch_size,)
    assert bool(torch.isfinite(det_action).all())
    assert bool(torch.isfinite(det_val).all())
    # Bất biến INV-002: Hành động luôn thuộc khoảng mở (0, 1)^6
    assert bool(torch.all(det_action > 0.0))
    assert bool(torch.all(det_action < 1.0))

    # Chế độ ngẫu nhiên (stochastic exploration)
    stoch_action, stoch_log_prob, stoch_val = model.act(dummy_obs, deterministic=False)
    assert stoch_action.shape == (batch_size, act_dim)
    assert bool(torch.all(stoch_action > 0.0))
    assert bool(torch.all(stoch_action < 1.0))
    assert bool(torch.isfinite(stoch_log_prob).all())


def test_normalizer_and_clipping_present(tmp_path: Path) -> None:
    """FR-003, FR-004, SC-006, AC-6, INV-004: Thẩm định chuẩn hoá trong checkpoint và cắt gradient.

    Xác minh:
    - Thống kê bộ chuẩn hoá quan sát (RunningNorm) được lưu và khôi phục toàn vẹn trong checkpoint.
    - Chính sách (Policy) đã nạp tự động áp dụng bộ chuẩn hoá trước khi suy luận hành động.
    - Một bước cập nhật PPO với gradient lớn cố ý có chuẩn gradient sau clipping <= max_grad_norm.
    """
    torch = _torch()
    from mma_ai.learning.checkpoint import load_checkpoint, load_policy, save_checkpoint
    from mma_ai.learning.networks import ActorCritic
    from mma_ai.learning.normalizer import RunningNorm
    from mma_ai.learning.ppo import PPOAgent

    cfg = TrainConfig.load()
    obs_dim = 14
    act_dim = 6

    # -------------------------------------------------------------------------
    # PHẦN 1: Thẩm định bộ chuẩn hoá quan sát có mặt trong checkpoint (FR-003, INV-004)
    # -------------------------------------------------------------------------
    normalizer = RunningNorm(clip_obs=cfg.normalization.clip_obs)
    # Thu thập thống kê quan sát chạy (running statistics) với lô mẫu 64 điểm
    raw_samples = sample_observations(n=64)
    normalizer.update(raw_samples)
    norm_state_before = normalizer.state_dict()
    assert norm_state_before["count"] == 64
    assert norm_state_before["mean"].shape == (obs_dim,)

    # Khởi tạo mô hình và tác tử PPO
    model = ActorCritic(obs_dim=obs_dim, act_dim=act_dim, cfg=cfg)
    agent = PPOAgent(model=model, cfg=cfg)

    # Lưu điểm kiểm tra với ngữ cảnh chứa bộ chuẩn hoá
    checkpoint_ctx = {
        "obs_normalizer": normalizer,
        "update_idx": 1,
        "env_steps": 2048,
        "seed": cfg.seed,
        "model_sha256": "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f",
        "config": cfg,
    }
    meta = save_checkpoint(agent=agent, run_dir=tmp_path, kind="periodic", ctx=checkpoint_ctx)
    assert "obs_normalizer" in meta.components, (
        "Điểm kiểm tra phải công bố thành phần obs_normalizer"
    )

    # Nạp lại điểm kiểm tra bằng load_checkpoint
    latest_path = tmp_path / "checkpoints" / "latest.json"
    loaded = load_checkpoint(latest_path)
    assert loaded.obs_normalizer_state_dict is not None, "Trạng thái normalizer không được là None"
    assert loaded.obs_normalizer_state_dict["count"] == 64
    np.testing.assert_allclose(
        loaded.obs_normalizer_state_dict["mean"].detach().cpu().numpy(),
        norm_state_before["mean"],
        rtol=1e-6,
        atol=1e-6,
        err_msg="Giá trị trung bình của bộ chuẩn hoá nạp lại không khớp",
    )

    # Nạp chính sách thực thi chỉ-đọc qua load_policy và kiểm tra tính năng chuẩn hoá
    policy = load_policy(latest_path)
    assert isinstance(policy.normalizer, RunningNorm)
    test_obs = np.ones(obs_dim, dtype=np.float64)
    computed_action = policy.act_deterministic(test_obs)
    assert computed_action.shape == (act_dim,)
    assert np.all(computed_action > 0.0) and np.all(computed_action < 1.0)

    # -------------------------------------------------------------------------
    # PHẦN 2: Thẩm định cắt ngắn gradient (gradient clipping) (FR-004, AC-6)
    # -------------------------------------------------------------------------
    batch_count = 16
    observations = torch.randn(batch_count, obs_dim)
    with torch.no_grad():
        actions, old_log_probs, values = agent.model.act(observations, deterministic=False)

    # Cố ý tạo độ lệch ưu thế (advantage) cực đại 1_000_000.0 để sinh ra gradient khổng lồ
    huge_advantage_batch = {
        "observations": observations,
        "actions": actions,
        "old_log_probs": old_log_probs,
        "returns": values + 1000.0,
        "advantages": torch.full((batch_count,), 1_000_000.0),
    }

    # Thực hiện bước cập nhật PPO
    update_stats = agent.update(huge_advantage_batch)

    # Chuẩn gradient sau clipping phải không vượt quá max_grad_norm đã cấu hình
    max_threshold = cfg.ppo.max_grad_norm + 1e-6
    assert update_stats.grad_norm <= max_threshold, (
        f"Chuẩn gradient sau clipping ({update_stats.grad_norm}) vượt quá "
        f"ngưỡng cho phép ({max_threshold})"
    )
    assert bool(torch.isfinite(torch.tensor(update_stats.grad_norm))), (
        "Chuẩn gradient phải hữu hạn"
    )
    assert update_stats.nan_count == 0, "Không được xuất hiện giá trị NaN trong quá trình cập nhật"
    assert update_stats.inf_count == 0, "Không được xuất hiện giá trị Inf trong quá trình cập nhật"


def test_custom_network_recorded_in_manifest(tmp_path: Path) -> None:
    """FR-002, SC-006, AC-6: Mạng thực tế theo cấu hình tuỳ biến và hồ sơ run ghi nhận cấu trúc.

    Xác minh:
    - Cấu hình tuỳ biến độ rộng/số lớp ẩn ([128, 64] và [64, 32]) tạo ra mạng thực tế đúng cấu hình.
    - Lượt huấn luyện khói qua CLI ghi nhận cấu hình mạng tuỳ biến vào hồ sơ run (manifest.json).
    - Hồ sơ run thẩm định hợp lệ với lược đồ hợp đồng run-manifest.schema.json.
    - Điểm kiểm tra tạo ra chứa các trọng số khớp chính xác với cấu trúc tuỳ biến.
    """
    torch = _torch()
    from mma_ai.learning.checkpoint import load_checkpoint
    from mma_ai.learning.networks import ActorCritic

    # 1. Chuẩn bị cấu hình tuỳ biến mạng khác mặc định: actor [128, 64], critic [64, 32]
    custom_actor_hidden = [128, 64]
    custom_critic_hidden = [64, 32]
    config_file = smoke_config(
        tmp_path,
        network={
            "actor_hidden": custom_actor_hidden,
            "critic_hidden": custom_critic_hidden,
            "activation": "tanh",
            "log_std_init": -0.5,
        },
    )

    # 2. Xác minh việc nạp cấu hình và khởi tạo mạng trực tiếp
    custom_cfg = TrainConfig.load(config_file)
    assert custom_cfg.network.actor_hidden == tuple(custom_actor_hidden)
    assert custom_cfg.network.critic_hidden == tuple(custom_critic_hidden)

    obs_dim = 14
    act_dim = 6
    direct_model = ActorCritic(obs_dim=obs_dim, act_dim=act_dim, cfg=custom_cfg)

    # Kiểm tra kích thước lớp mạng diễn viên trực tiếp
    direct_actor_layers = [
        layer for layer in direct_model.actor if isinstance(layer, torch.nn.Linear)
    ]
    assert [(layer.in_features, layer.out_features) for layer in direct_actor_layers] == [
        (obs_dim, 128),
        (128, 64),
        (64, act_dim),
    ]

    # Kiểm tra kích thước lớp mạng đánh giá trực tiếp
    direct_critic_layers = [
        layer for layer in direct_model.critic if isinstance(layer, torch.nn.Linear)
    ]
    assert [(layer.in_features, layer.out_features) for layer in direct_critic_layers] == [
        (obs_dim, 64),
        (64, 32),
        (32, 1),
    ]

    # 3. Chạy lượt huấn luyện khói thực tế qua giao diện dòng lệnh (CLI integration)
    cli_result = run_train_cli(
        ["--stage", "elbow", "--config", str(config_file), "--seed", "42"],
        timeout=60.0,
    )
    assert cli_result.exit_code == 0, (
        f"Lượt chạy CLI thất bại với mã {cli_result.exit_code}.\n"
        f"Stderr: {cli_result.stderr}\nStdout: {cli_result.stdout}"
    )

    # 4. Thẩm định hồ sơ thí nghiệm (run manifest) được ghi nhận trong thư mục lượt chạy
    runs_dir = tmp_path / "runs"
    runs = list_runs(runs_dir)
    assert len(runs) == 1, f"Kỳ vọng 1 thư mục run, nhận {len(runs)}"
    run_dir = runs[0]

    manifest = load_manifest(run_dir)

    # Xác minh cấu trúc mạng đã sử dụng được lưu trung thực trong hồ sơ
    manifest_network = manifest.get("config", {}).get("network", {})
    assert manifest_network.get("actor_hidden") == custom_actor_hidden, (
        f"Hồ sơ run không ghi nhận đúng actor_hidden: {manifest_network.get('actor_hidden')}"
    )
    assert manifest_network.get("critic_hidden") == custom_critic_hidden, (
        f"Hồ sơ run không ghi nhận đúng critic_hidden: {manifest_network.get('critic_hidden')}"
    )

    # Thẩm định hồ sơ run theo JSON Schema của hợp đồng
    manifest_schema = _load_manifest_schema()
    registry = load_schema_registry()
    validator = Draft202012Validator(manifest_schema, registry=registry)
    schema_errors = list(validator.iter_errors(manifest))
    assert not schema_errors, (
        f"Hồ sơ run không hợp chuẩn run-manifest.schema.json: {[e.message for e in schema_errors]}"
    )

    # 5. Thẩm định điểm kiểm tra đã lưu phản ánh đúng hình dạng mạng tuỳ biến
    latest_pointer = run_dir / "checkpoints" / "latest.json"
    assert latest_pointer.is_file(), "Thiếu con trỏ latest.json trong thư mục checkpoints"
    loaded_ckpt = load_checkpoint(latest_pointer)

    # Kiểm tra kích thước tensor trọng số trong actor
    actor_weights = [v for k, v in loaded_ckpt.actor_state_dict.items() if "weight" in k]
    assert [w.shape for w in actor_weights] == [
        torch.Size([128, obs_dim]),
        torch.Size([64, 128]),
        torch.Size([act_dim, 64]),
    ], "Hình dạng trọng số actor trong checkpoint không khớp cấu hình tuỳ biến"

    # Kiểm tra kích thước tensor trọng số trong critic
    critic_weights = [v for k, v in loaded_ckpt.critic_state_dict.items() if "weight" in k]
    assert [w.shape for w in critic_weights] == [
        torch.Size([64, obs_dim]),
        torch.Size([32, 64]),
        torch.Size([1, 32]),
    ], "Hình dạng trọng số critic trong checkpoint không khớp cấu hình tuỳ biến"

    # Kiểm tra cấu hình đính kèm trong điểm kiểm tra
    assert loaded_ckpt.config["network"]["actor_hidden"] == custom_actor_hidden
    assert loaded_ckpt.config["network"]["critic_hidden"] == custom_critic_hidden


def test_invalid_network_structure_raises_config_error(tmp_path: Path) -> None:
    """FR-018, INV-005: Cấu hình mạng có số chiều không hợp lệ ném lỗi TrainConfigError.

    Xác minh tính bất biến của cấu hình: giá trị độ rộng lớp <= 0 hoặc rỗng bị từ chối
    trước khi khởi tạo tài nguyên hay bắt đầu huấn luyện.
    """
    # 1. Thử nghiệm độ rộng lớp ẩn <= 0
    with pytest.raises(TrainConfigError) as exc_info:
        smoke_config(tmp_path, network={"actor_hidden": [256, 0]})
        TrainConfig.load(tmp_path / "train_smoke.yaml")
    assert "network.actor_hidden" in str(exc_info.value) or "phải là số nguyên dương" in str(
        exc_info.value
    )

    # 2. Thử nghiệm danh sách lớp ẩn rỗng
    with pytest.raises(TrainConfigError) as exc_info_empty:
        smoke_config(tmp_path, network={"critic_hidden": []})
        TrainConfig.load(tmp_path / "train_smoke.yaml")
    assert "network.critic_hidden" in str(exc_info_empty.value) or "không được rỗng" in str(
        exc_info_empty.value
    )
