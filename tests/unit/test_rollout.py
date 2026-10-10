"""Kiểm thử đơn vị (unit test) cho vòng chạy rollout và bản ghi episode (EpisodeRecord).

Hiện thực các yêu cầu chức năng (functional requirements), bất biến (invariants) và hợp đồng:
- 004 FR-002, 004 INV-002, 004 AC-1: Hai chính sách (policy) được chạy trên cùng danh sách mục tiêu
  theo cùng thứ tự, cùng hạt giống (seed) đếm tuần tự.
- 004 FR-003, 004 INV-003, 004 AC-1: Mọi hành động là kích thích cơ trong [0, 1]^6; hành động chứa
  NaN/Inf hoặc ngoài [0, 1] bị chặn ngay trước env.step.
- 004 FR-016, 004 AC-1: Mất ổn định vật lý (PhysicsInstabilityError) hoặc hành động bất thường được
  đếm vào tỷ lệ bất thường (abnormal), tính là không tới mục tiêu, không làm dừng lượt đánh giá.
- 004 API-EVL-0005: run_policy_on_targets(env, policy, n_targets, repeats, seed_base)
  trả về danh sách EpisodeRecord.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from mma_ai.environment.errors import PhysicsInstabilityError
from mma_ai.environment.single_agent import ElbowReachEnv
from mma_ai.evaluation.policies import BasePolicy, RandomPolicy
from mma_ai.evaluation.rollout import EpisodeRecord, run_policy_on_targets


class ConstantActionPolicy(BasePolicy):
    """Chính sách hành động hằng số phục vụ kiểm thử."""

    def __init__(self, value: float = 0.5, act_dim: int = 6) -> None:
        self.value = float(value)
        self.act_dim = act_dim
        self.name = "constant"

    def act(self, obs_raw: Any = None) -> np.ndarray:
        return np.full(self.act_dim, self.value, dtype=np.float32)


class BadActionPolicy(BasePolicy):
    """Chính sách sinh hành động lỗi phục vụ kiểm thử chặn biên."""

    def __init__(self, bad_action: np.ndarray, name: str = "bad_policy") -> None:
        self.bad_action = bad_action
        self.name = name

    def act(self, obs_raw: Any = None) -> np.ndarray:
        return self.bad_action


def test_each_target_once_per_repeat_same_order_for_two_policies() -> None:
    """Kiểm tra mỗi mục tiêu chạy đúng một lần trên mỗi lần lặp và cùng thứ tự cho 2 policy.

    Truy vết: 004 FR-002, 004 INV-002, 004 API-EVL-0005, 004 AC-1.
    """
    env = ElbowReachEnv()
    n_targets = 3
    repeats = 2
    seed_base = 2000

    policy1 = RandomPolicy(seed=42)
    policy2 = ConstantActionPolicy(value=0.2)

    records1 = run_policy_on_targets(
        env, policy1, n_targets=n_targets, repeats=repeats, seed_base=seed_base
    )
    records2 = run_policy_on_targets(
        env, policy2, n_targets=n_targets, repeats=repeats, seed_base=seed_base
    )

    expected_total = n_targets * repeats
    assert len(records1) == expected_total
    assert len(records2) == expected_total

    # Kiểm tra từng episode: cùng target_index, cùng seed tuần tự, cùng thứ tự
    for k in range(expected_total):
        rec1 = records1[k]
        rec2 = records2[k]

        expected_target_idx = k % n_targets
        expected_seed = seed_base + k

        assert rec1.episode == k
        assert rec2.episode == k

        assert rec1.target_index == expected_target_idx
        assert rec2.target_index == expected_target_idx

        assert rec1.seed == expected_seed
        assert rec2.seed == expected_seed

        # Cả hai policy có cùng thứ tự ghép cặp (paired) theo mục tiêu
        assert rec1.target_index == rec2.target_index
        assert rec1.seed == rec2.seed

        # Các chỉ số không bị bất thường trong lượt chạy hợp lệ
        assert not rec1.abnormal
        assert not rec2.abnormal
        assert rec1.final_distance_m is not None
        assert rec2.final_distance_m is not None
        assert rec1.n_steps > 0
        assert rec2.n_steps > 0
        assert rec1.nan_count == 0
        assert rec1.inf_count == 0


def test_nan_action_blocked_before_step(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra hành động chứa NaN bị chặn ngay trước env.step và ghi nhận bất thường (abnormal).

    Truy vết: 004 FR-003, 004 FR-016, 004 INV-003, 004 AC-1.
    """
    env = ElbowReachEnv()
    step_called_with_nan = False
    original_step = env.step

    def spy_step(action: Any) -> Any:
        nonlocal step_called_with_nan
        act_arr = np.asarray(action)
        if np.isnan(act_arr).any():
            step_called_with_nan = True
        return original_step(action)

    monkeypatch.setattr(env, "step", spy_step)

    # Hành động chứa 2 giá trị NaN
    nan_action = np.array([0.5, np.nan, 0.2, np.nan, 0.1, 0.9], dtype=np.float32)
    bad_policy = BadActionPolicy(nan_action, name="nan_policy")

    records = run_policy_on_targets(
        env, bad_policy, n_targets=2, repeats=1, seed_base=12345
    )

    assert len(records) == 2
    assert not step_called_with_nan, "env.step tuyệt đối KHÔNG được gọi với hành động chứa NaN!"

    for rec in records:
        assert rec.abnormal is True
        assert rec.reached is False
        assert rec.final_distance_m is None
        assert rec.nan_count == 2
        assert rec.end_reason in ("abnormal_action", "abnormal")


def test_out_of_range_action_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra hành động ngoài miền [0, 1]^6 bị chặn ngay trước env.step.

    Truy vết: 004 FR-003, 004 FR-016, 004 INV-003, 004 AC-1.
    """
    env = ElbowReachEnv()
    step_called = False
    original_step = env.step

    def spy_step(action: Any) -> Any:
        nonlocal step_called
        step_called = True
        return original_step(action)

    monkeypatch.setattr(env, "step", spy_step)

    # Hành động vượt ngưỡng trên (> 1.0) và dưới (< 0.0)
    out_of_range_action = np.array([-0.2, 0.5, 1.5, 0.8, 0.1, 0.3], dtype=np.float32)
    bad_policy = BadActionPolicy(out_of_range_action, name="out_of_range_policy")

    records = run_policy_on_targets(
        env, bad_policy, n_targets=2, repeats=1, seed_base=54321
    )

    assert len(records) == 2
    assert not step_called, "env.step không được gọi khi hành động ngoài phạm vi [0, 1]!"

    for rec in records:
        assert rec.abnormal is True
        assert rec.reached is False
        assert rec.final_distance_m is None
        assert rec.end_reason in ("abnormal_action", "abnormal")


def test_instability_counted_not_fatal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra mất ổn định vật lý (PhysicsInstabilityError) được đếm bất thường và không sập lượt.

    Truy vết: 004 FR-016, 004 API-EVL-0005, 004 AC-1.
    """
    env = ElbowReachEnv()
    original_step = env.step
    call_count = 0

    def mock_step_with_instability(action: Any) -> Any:
        nonlocal call_count
        call_count += 1
        # Gặp lỗi mất ổn định vật lý ở episode đầu tiên (bước 1)
        if call_count == 1:
            raise PhysicsInstabilityError(
                "Mô phỏng MuJoCo mất ổn định vật lý (PhysicsInstabilityError)!"
            )
        return original_step(action)

    monkeypatch.setattr(env, "step", mock_step_with_instability)

    policy = ConstantActionPolicy(value=0.5)
    n_targets = 2
    repeats = 1
    records = run_policy_on_targets(
        env, policy, n_targets=n_targets, repeats=repeats, seed_base=9999
    )

    assert len(records) == 2

    # Episode 0 bị mất ổn định
    rec0 = records[0]
    assert rec0.abnormal is True
    assert rec0.reached is False
    assert rec0.final_distance_m is None
    assert rec0.end_reason == "instability"

    # Episode 1 chạy bình thường không bị sập
    rec1 = records[1]
    assert rec1.abnormal is False
    assert rec1.final_distance_m is not None
    assert rec1.n_steps > 0


def test_inf_action_blocked_before_step(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra hành động chứa Inf bị chặn ngay trước env.step và ghi nhận inf_count.

    Truy vết: 004 FR-003, 004 FR-016, 004 INV-003, 004 AC-1.
    """
    env = ElbowReachEnv()
    step_called = False

    def spy_step(action: Any) -> Any:
        nonlocal step_called
        step_called = True
        return env.step(action)

    # Hành động chứa +inf và -inf
    inf_action = np.array([0.5, np.inf, 0.2, -np.inf, 0.1, 0.9], dtype=np.float32)
    bad_policy = BadActionPolicy(inf_action, name="inf_policy")

    records = run_policy_on_targets(
        env, bad_policy, n_targets=1, repeats=1, seed_base=7777
    )

    assert len(records) == 1
    rec = records[0]
    assert rec.abnormal is True
    assert rec.reached is False
    assert rec.final_distance_m is None
    assert rec.inf_count == 2
    assert rec.end_reason in ("abnormal_action", "abnormal")


def test_episode_record_fields_and_dict() -> None:
    """Kiểm tra đầy đủ thuộc tính và khả năng chuyển đổi dict của EpisodeRecord.

    Truy vết: 004 FR-004, 004 API-EVL-0005, 004 AC-1.
    """
    record = EpisodeRecord(
        policy="learned",
        episode=0,
        target_index=1,
        seed=12345,
        reached=True,
        end_reason="reached",
        abnormal=False,
        final_distance_m=0.015,
        return_=12.5,
        effort=0.45,
        act_m0=0.4,
        act_m1=0.5,
        act_m2=0.6,
        act_m3=0.3,
        act_m4=0.4,
        act_m5=0.5,
        n_steps=50,
        nan_count=0,
        inf_count=0,
    )

    assert record.policy == "learned"
    assert record.episode == 0
    assert record.target_index == 1
    assert record.seed == 12345
    assert record.reached is True
    assert record.final_distance_m == 0.015
    assert getattr(record, "return") == 12.5
    assert record.return_val == 12.5
    assert record.episode_return == 12.5

    data = record.to_dict()
    assert data["return"] == 12.5
    assert data["policy"] == "learned"
    assert data["effort"] == 0.45
    assert data["act_m0"] == 0.4
    assert data["n_steps"] == 50
