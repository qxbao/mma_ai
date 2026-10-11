"""Kiểm thử đơn vị (unit test) cho tuỳ chọn target_index trong ElbowReachEnv.reset.

Hiện thực các yêu cầu và bất biến theo hợp đồng:
- FR-002, AC-1: Hai policy được đánh giá trên cùng danh sách mục tiêu theo cùng thứ tự.
- INV-002: Đảm bảo cùng tập mục tiêu và thứ tự đánh giá nhất quán qua options target_index.
- API-EVL-0005: Cho phép reset options={"split": "test", "target_index": i} chọn đúng mục tiêu i.
"""

from __future__ import annotations

import numpy as np
import pytest

from mma_ai.environment.single_agent import ElbowReachEnv


def test_target_index_selects_ith_test_target() -> None:
    """Kiểm tra options target_index chọn đúng mục tiêu thứ i trong tập test.

    Truy vết: FR-002, INV-002, API-EVL-0005, AC-1.
    """
    env = ElbowReachEnv()
    test_targets = env.targets.test.targets
    n_test = len(test_targets)
    assert n_test >= 2, f"Kỳ vọng tập kiểm thử có ít nhất 2 mục tiêu, nhận được {n_test}"

    # Kiểm tra với các chỉ mục: đầu (0), giữa (1), cuối (n_test - 1)
    indices_to_test = [0, 1, n_test - 1]
    for idx in indices_to_test:
        expected_target = test_targets[idx]
        # Thử với các seed khác nhau, target được chọn phải luôn là mục tiêu thứ idx
        for test_seed in (12345, 42, 9999):
            obs, info = env.reset(seed=test_seed, options={"split": "test", "target_index": idx})

            assert info["target_index"] == idx
            assert info["target_split"] == "test"
            assert np.allclose(info["target_position_m"], expected_target.position_m)
            assert env._current_target == expected_target

            # Kiểm tra khoảng cách ban đầu trong info khớp với vị trí mục tiêu thứ idx
            wrist_pos = np.array(env.data.site_xpos[env.fingertip_site_id], dtype=np.float64)
            expected_dist = float(np.linalg.norm(wrist_pos - np.array(expected_target.position_m)))
            assert np.isclose(info["initial_distance_m"], expected_dist, atol=1e-6)

    # Kiểm tra bổ sung cho tập huấn luyện (train set)
    train_targets = env.targets.train.targets
    obs_train, info_train = env.reset(seed=123, options={"split": "train", "target_index": 0})
    assert info_train["target_index"] == 0
    assert info_train["target_split"] == "train"
    assert env._current_target == train_targets[0]


def test_default_reset_unchanged() -> None:
    """Kiểm tra hành vi đặt lại mặc định (default reset) giữ nguyên khi không có target_index.

    Truy vết: FR-002, INV-002, AC-1.
    Khi options không chứa target_index hoặc options là None, với cùng seed thì
    mục tiêu, quan sát ban đầu và quỹ đạo qua các bước step phải hoàn toàn đồng nhất.
    """
    env1 = ElbowReachEnv()
    env2 = ElbowReachEnv()

    # 1. Đặt lại mặc định options=None với cùng seed
    obs1, info1 = env1.reset(seed=42)
    obs2, info2 = env2.reset(seed=42)

    assert info1["target_index"] == info2["target_index"]
    assert info1["target_split"] == info2["target_split"]
    assert np.allclose(info1["target_position_m"], info2["target_position_m"])
    assert np.allclose(obs1, obs2)

    # 2. Đặt lại với options={"split": "test"} nhưng không truyền target_index
    obs_t1, info_t1 = env1.reset(seed=777, options={"split": "test"})
    obs_t2, info_t2 = env2.reset(seed=777, options={"split": "test"})

    assert info_t1["target_index"] == info_t2["target_index"]
    assert info_t1["target_split"] == "test"
    assert np.allclose(info_t1["target_position_m"], info_t2["target_position_m"])
    assert np.allclose(obs_t1, obs_t2)

    # 3. Quỹ đạo và phần thưởng (reward) khi bước step với cùng hành động phải giống hệt nhau
    dummy_action = np.full(6, 0.5, dtype=np.float32)
    step1 = env1.step(dummy_action)
    step2 = env2.step(dummy_action)

    # obs, reward, terminated, truncated, info
    assert np.allclose(step1[0], step2[0])
    assert np.isclose(step1[1], step2[1], atol=1e-6)
    assert step1[2] == step2[2]
    assert step1[3] == step2[3]
    assert step1[4] == step2[4]


def test_out_of_range_raises() -> None:
    """Kiểm tra chỉ mục ngoài phạm vi hoặc sai kiểu dữ liệu ném ngoại lệ ValueError.

    Truy vết: FR-002, INV-002, API-EVL-0005.
    Thông điệp lỗi phải nêu rõ chỉ mục và kích thước tập (set size).
    """
    env = ElbowReachEnv()
    n_test = len(env.targets.test.targets)
    n_train = len(env.targets.train.targets)

    # 1. Chỉ mục âm trong tập kiểm thử (test)
    with pytest.raises(ValueError) as exc_info:
        env.reset(options={"split": "test", "target_index": -1})
    err_msg = str(exc_info.value)
    assert "-1" in err_msg, f"Thông điệp phải chứa chỉ mục vi phạm: {err_msg}"
    assert str(n_test) in err_msg, f"Thông điệp phải chứa kích thước tập {n_test}: {err_msg}"

    # 2. Chỉ mục vượt quá biên trên trong tập kiểm thử (test)
    with pytest.raises(ValueError) as exc_info:
        env.reset(options={"split": "test", "target_index": n_test})
    err_msg = str(exc_info.value)
    assert str(n_test) in err_msg, f"Thông điệp phải chứa chỉ mục và kích thước tập: {err_msg}"

    # 3. Chỉ mục quá lớn ngoài phạm vi
    with pytest.raises(ValueError) as exc_info:
        env.reset(options={"split": "test", "target_index": n_test + 100})
    err_msg = str(exc_info.value)
    assert str(n_test + 100) in err_msg
    assert str(n_test) in err_msg

    # 4. Chỉ mục ngoài phạm vi trong tập huấn luyện (train)
    with pytest.raises(ValueError) as exc_info:
        env.reset(options={"split": "train", "target_index": n_train})
    err_msg = str(exc_info.value)
    assert str(n_train) in err_msg

    # 5. Kiểu dữ liệu không phải số nguyên (float, chuỗi, bool)
    with pytest.raises(ValueError) as exc_info:
        env.reset(options={"split": "test", "target_index": "invalid"})
    assert "invalid" in str(exc_info.value)
    assert str(n_test) in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        env.reset(options={"split": "test", "target_index": 2.5})
    assert "2.5" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        env.reset(options={"split": "test", "target_index": True})
    assert str(n_test) in str(exc_info.value)
