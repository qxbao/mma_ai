"""Kiểm thử đơn vị cho phân hệ chính sách đánh giá (mma_ai.evaluation.policies).

Bao phủ các yêu cầu và bất biến theo hợp đồng:
- 004 FR-003, 004 AC-1, 004 API-EVL-0004: Giao diện chung act(obs_raw) -> np.ndarray[6].
- 004 INV-003: Mọi hành động kích thích cơ u nằm trong [0, 1]^6, không điều khiển lực/toạ độ.
- 004 INV-007, NFR-REPRO-001: RandomPolicy tái lập tất định theo seed và dùng duy nhất một bộ sinh.
- 004 AC-5: LearnedPolicy ném CheckpointUnusable khi checkpoint không dùng được (mã thoát 4).
"""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from mma_ai.evaluation.errors import CheckpointUnusable
from mma_ai.evaluation.policies import BasePolicy, LearnedPolicy, Policy, RandomPolicy


def _torch() -> Any:
    """Nạp torch hoặc bỏ qua test một cách nhẹ nhàng nếu thiếu phụ thuộc rl."""
    return pytest.importorskip("torch")


def _make_valid_checkpoint(tmp_path: Path) -> Path:
    """Tạo tệp điểm kiểm tra (checkpoint) hợp lệ cho kiểm thử đơn vị."""
    torch = _torch()
    from mma_ai.learning.checkpoint import save_checkpoint
    from mma_ai.learning.networks import ActorCritic
    from mma_ai.learning.normalizer import RunningNorm
    from mma_ai.learning.train_config import TrainConfig

    class _DummyAgent:
        def __init__(self) -> None:
            self.cfg = TrainConfig.load()
            self.model = ActorCritic(obs_dim=14, act_dim=6, cfg=self.cfg)
            self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)

        def state_dict(self) -> dict[str, Any]:
            return {
                "actor": self.model.actor.state_dict(),
                "critic": self.model.critic.state_dict(),
                "log_std": self.model.log_std.detach().clone(),
                "optimizer": self.optimizer.state_dict(),
            }

    agent = _DummyAgent()
    norm = RunningNorm()
    norm.update(np.ones((4, 14), dtype=np.float64))
    ctx = {
        "update_idx": 1,
        "env_steps": 2048,
        "model_sha256": "0" * 64,
        "seed": 42,
        "obs_normalizer": norm,
    }
    meta = save_checkpoint(agent, tmp_path, kind="periodic", ctx=ctx)
    return tmp_path / meta.path


def test_random_policy_seeded_and_in_unit_interval() -> None:
    """004 FR-003, 004 INV-003, 004 INV-007, 004 API-EVL-0004, 004 AC-1: tái lập và [0,1]^6."""
    policy1 = RandomPolicy(seed=12345, act_dim=6)
    policy2 = RandomPolicy(seed=12345, act_dim=6)

    obs = np.zeros(14, dtype=np.float64)

    actions1: list[np.ndarray] = []
    actions2: list[np.ndarray] = []

    for _ in range(50):
        a1 = policy1.act(obs)
        a2 = policy2.act(obs)

        assert isinstance(a1, np.ndarray), "Hành động phải là mảng numpy"
        assert a1.shape == (6,), "Hành động phải có kích thước đúng 6 chiều cơ"
        assert a1.dtype in (np.float32, np.float64), "Kiểu dữ liệu hành động phải là số thực"
        assert np.all(a1 >= 0.0) and np.all(a1 <= 1.0), "004 INV-003: Hành động thuộc [0, 1]^6"

        actions1.append(a1)
        actions2.append(a2)

    # 004 INV-007, NFR-REPRO-001: Cùng seed phải sinh chuỗi hành động giống hệt nhau
    for a1, a2 in zip(actions1, actions2, strict=True):
        np.testing.assert_array_equal(a1, a2)

    # Kiểm tra tính phân bố không cố định qua các bước (RNG tiến bước)
    assert not np.array_equal(actions1[0], actions1[1]), "Hai bước kế tiếp không được trùng giá trị"


def test_random_ignores_observation() -> None:
    """004 FR-003, 004 INV-003, 004 API-EVL-0004, 004 AC-1: bỏ qua hoàn toàn quan sát."""
    p_baseline = RandomPolicy(seed=999)
    p_perturbed = RandomPolicy(seed=999)

    # Quan sát chuẩn
    obs_zero = np.zeros(14, dtype=np.float64)
    # Các quan sát dị biệt: giá trị cực đoan, NaN, Inf, None
    obs_extreme = np.full(14, 1e6, dtype=np.float64)
    obs_nan = np.full(14, np.nan, dtype=np.float64)

    actions_base = [
        p_baseline.act(obs_zero),
        p_baseline.act(obs_zero),
        p_baseline.act(obs_zero),
        p_baseline.act(obs_zero),
    ]

    actions_perturbed = [
        p_perturbed.act(obs_extreme),
        p_perturbed.act(obs_nan),
        p_perturbed.act(None),
        p_perturbed.act(np.ones(14)),
    ]

    for a_base, a_pert in zip(actions_base, actions_perturbed, strict=True):
        np.testing.assert_array_equal(a_base, a_pert)


def test_diff_seed_diff_actions() -> None:
    """004 FR-003, 004 INV-007, 004 API-EVL-0004, 004 AC-1: khác seed sinh chuỗi khác nhau."""
    p1 = RandomPolicy(seed=12345)
    p2 = RandomPolicy(seed=54321)

    obs = np.zeros(14, dtype=np.float64)
    a1 = p1.act(obs)
    a2 = p2.act(obs)

    assert not np.array_equal(a1, a2), "004 INV-007: Khác seed phải sinh hành động khác nhau"


def test_learned_policy_deterministic_for_same_obs(tmp_path: Path) -> None:
    """004 FR-003, 004 INV-003, 004 API-EVL-0004, 004 AC-1: hành động xác định cho cùng quan sát."""
    ckpt_path = _make_valid_checkpoint(tmp_path)
    policy = LearnedPolicy(ckpt_path)

    obs = np.array([0.1 * i for i in range(14)], dtype=np.float64)

    # Gọi nhiều lần với cùng một quan sát
    first_act = policy.act(obs)
    assert isinstance(first_act, np.ndarray)
    assert first_act.shape == (6,)
    assert np.all(first_act >= 0.0) and np.all(first_act <= 1.0), "004 INV-003: u thuộc [0, 1]^6"

    for _ in range(10):
        next_act = policy.act(obs)
        np.testing.assert_array_equal(first_act, next_act)


def test_learned_policy_raises_checkpoint_unusable_on_missing_file(tmp_path: Path) -> None:
    """004 AC-5, 004 API-EVL-0004: LearnedPolicy ném CheckpointUnusable khi tệp không tồn tại."""
    non_existent = tmp_path / "non_existent_model.pt"

    with pytest.raises(CheckpointUnusable) as exc_info:
        LearnedPolicy(non_existent)

    assert exc_info.value.exit_code == 4, "Mã thoát phải là 4 theo contracts/cli.md"
    assert "non_existent_model.pt" in str(exc_info.value) or "không tồn tại" in str(exc_info.value)


def test_learned_policy_raises_checkpoint_unusable_on_corrupt_file(tmp_path: Path) -> None:
    """004 AC-5, 004 API-EVL-0004: LearnedPolicy ném CheckpointUnusable khi tệp hỏng."""
    corrupt_file = tmp_path / "corrupted.pt"
    corrupt_file.write_bytes(b"garbage payload not a torch file")

    with pytest.raises(CheckpointUnusable) as exc_info:
        LearnedPolicy(corrupt_file)

    assert exc_info.value.exit_code == 4, "Mã thoát phải là 4 theo contracts/cli.md"


def test_learned_policy_raises_checkpoint_unusable_on_missing_components(tmp_path: Path) -> None:
    """004 AC-5, 004 API-EVL-0004: LearnedPolicy ném CheckpointUnusable khi thiếu thành phần."""
    torch = _torch()

    partial_file = tmp_path / "partial.pt"
    torch.save({"actor": {}, "seed": 42}, partial_file)

    with pytest.raises(CheckpointUnusable) as exc_info:
        LearnedPolicy(partial_file)

    assert exc_info.value.exit_code == 4, "Mã thoát phải là 4 theo contracts/cli.md"
    assert "thiếu" in str(exc_info.value).lower() or "thành phần" in str(exc_info.value).lower()


def test_learned_policy_raises_checkpoint_unusable_on_architecture_mismatch(tmp_path: Path) -> None:
    """004 AC-5, 004 API-EVL-0004: LearnedPolicy ném CheckpointUnusable khi cấu trúc không khớp."""
    torch = _torch()

    mismatch_file = tmp_path / "mismatch.pt"
    # Giả lập state_dict có obs_dim sai (ví dụ 10 thay vì 14) nhưng đủ thành phần
    weight = torch.randn(64, 10)
    torch.save(
        {
            "actor": {"fc.weight": weight},
            "critic": {},
            "obs_normalizer": {},
            "optimizer": {},
            "seed": 42,
            "rng_state": {},
        },
        mismatch_file,
    )

    with pytest.raises(CheckpointUnusable) as exc_info:
        LearnedPolicy(mismatch_file)

    assert exc_info.value.exit_code == 4, "Mã thoát phải là 4 theo contracts/cli.md"


def test_policies_has_no_trainer_or_ppo_imports() -> None:
    """004 API-EVL-0004: policies.py chỉ import learning.checkpoint, cấm trainer/ppo."""
    pkg_dir = Path(__file__).resolve().parent.parent.parent / "src" / "mma_ai" / "evaluation"
    policies_path = pkg_dir / "policies.py"
    tree = ast.parse(policies_path.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "learning.trainer" not in alias.name, "Cấm import learning.trainer"
                assert "learning.ppo" not in alias.name, "Cấm import learning.ppo"
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert "learning.trainer" not in mod, "Cấm import from learning.trainer"
            assert "learning.ppo" not in mod, "Cấm import from learning.ppo"

    # Kiểm tra ranh giới nạp sys.modules khi import policies
    forbidden = ["mma_ai.learning.trainer", "mma_ai.learning.ppo"]
    for f in forbidden:
        assert f not in sys.modules, f"Module {f} không được nạp tự động trong sys.modules"


def test_policy_interface_hierarchy_and_signatures() -> None:
    """004 API-EVL-0004: Khẳng định phân cấp lớp và chữ ký hàm act(obs_raw) -> np.ndarray[6]."""
    assert issubclass(RandomPolicy, BasePolicy), "RandomPolicy phải kế thừa BasePolicy"
    assert issubclass(LearnedPolicy, BasePolicy), "LearnedPolicy phải kế thừa BasePolicy"
    assert Policy is BasePolicy, "Policy phải là alias của BasePolicy"

    # Chữ ký phương thức act
    for cls in (BasePolicy, RandomPolicy, LearnedPolicy):
        sig = inspect.signature(cls.act)
        params = list(sig.parameters.keys())
        assert "obs_raw" in params, f"{cls.__name__}.act phải nhận tham số obs_raw"


def test_random_policy_invalid_act_dim() -> None:
    """004 FR-003, 004 INV-003: RandomPolicy từ chối act_dim không hợp lệ (<= 0)."""
    with pytest.raises(ValueError, match="act_dim"):
        RandomPolicy(seed=42, act_dim=0)
    with pytest.raises(ValueError, match="act_dim"):
        RandomPolicy(seed=42, act_dim=-1)


def teardown_module() -> None:
    """Dọn dẹp các module đã nạp để cô lập và bảo đảm tính độc lập cho các test khác."""
    sys.modules.pop("mma_ai.evaluation.policies", None)
