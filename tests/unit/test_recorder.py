"""Bộ kiểm thử đơn vị cho mô-đun thu bản ghi episode (mma_ai.visualization.recorder).

Truy vết các yêu cầu kỹ thuật và bất biến:
- FR-002: Chạy demo một episode trên môi trường khuỷu tay và ghi lại dữ liệu phát lại 3D.
- FR-003: Chỉ kích thích cơ bắp u in [0, 1]^6 được đưa vào mô phỏng; kiểm tra trước khi step.
- FR-015: Replay chạy tiến trình riêng, không nhập mã huấn luyện (learning.trainer/learning.ppo).
- FR-016: Demo cho phép chọn mục tiêu theo chỉ số (target_index) và phân tách (split).
- INV-002: Đường điều khiển duy nhất là kích thích cơ; recorder chỉ đọc trạng thái
  qua env.read_state(), không can thiệp hoặc ghi đè MjData của môi trường mô phỏng.
- NFR-REPRO-001: Tính tái lập của demo theo seed — cùng checkpoint/policy, seed và mục tiêu
  cho chuỗi hành động và trạng thái hoàn toàn đồng nhất (sai lệch số học <= 1e-6).
- API-VIS-0004: record_episode(env, policy, *, split, target_index, seed, source) -> Episode.
- AC-2: Demo chạy policy trên môi trường khuỷu tay và ghi nhận chính xác 6 giá trị activation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from mma_ai.environment.errors import PhysicsInstabilityError
from mma_ai.environment.single_agent import make_env
from mma_ai.visualization.episode import Episode, SourceRecord, validate_episode_dict
from mma_ai.visualization.errors import DemoUnstable
from mma_ai.visualization.recorder import record_episode, resolve_source

try:
    import jsonschema
except ImportError:
    jsonschema = None

SCHEMA_PATH = Path("specs/005-replay-3d-muscle-demo/contracts/episode.schema.json")


class ScriptedPolicy:
    """Chính sách điều khiển kịch bản phục vụ kiểm thử tất định (deterministic test policy)."""

    def __init__(
        self,
        actions: list[list[float]] | None = None,
        default_action: list[float] | None = None,
    ) -> None:
        self.actions: list[list[float]] = list(actions) if actions is not None else []
        self.default_action: list[float] = default_action or [0.1, 0.2, 0.15, 0.25, 0.05, 0.3]
        self.step_idx: int = 0
        self.observed_states: list[np.ndarray] = []

    def act_deterministic(self, obs: np.ndarray) -> list[float]:
        """Trả về hành động xác định theo kịch bản."""
        self.observed_states.append(obs.copy())
        if self.step_idx < len(self.actions):
            act = self.actions[self.step_idx]
        else:
            act = self.default_action
        self.step_idx += 1
        return act


@pytest.fixture  # type: ignore[untyped-decorator]
def episode_schema() -> dict[str, Any]:
    """Nạp lược đồ JSON Schema chuẩn của Episode."""
    assert SCHEMA_PATH.is_file(), f"Không tìm thấy lược đồ tại {SCHEMA_PATH}"
    return cast(dict[str, Any], json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_api_vis_0004_record_basic_episode() -> None:
    """API-VIS-0004, FR-002: Kiểm tra ghi nhận một episode thành công với policy kịch bản."""
    env = make_env(split="test")
    policy = ScriptedPolicy(
        actions=[
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            [0.2, 0.1, 0.4, 0.3, 0.6, 0.5],
        ]
    )

    episode = record_episode(
        env,
        policy,
        split="test",
        target_index=0,
        seed=42,
        source=None,
    )

    assert isinstance(episode, Episode)
    assert episode.seed == 42
    assert episode.target.split == "test"
    assert episode.target.index == 0
    assert episode.source is None
    assert len(episode.frames) >= 2
    # Khung đầu tiên excitation phải là None theo R4
    assert episode.frames[0].excitation is None
    # Khung thứ hai phải mang hành động kích thích cơ thứ nhất
    assert episode.frames[1].excitation == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]


def test_fr_003_inv_002_actions_checked_before_step() -> None:
    """FR-003, INV-002: Hành động được kiểm tra hữu hạn và [0,1]^6 ngay trước env.step.

    Khi vi phạm, hành động bị chặn tại biên, episode kết thúc bất thường (abnormal),
    và env.step tuyệt đối không được gọi với giá trị sai.
    """
    env = make_env(split="test")
    original_step = env.step
    called_actions: list[Any] = []

    def tracking_step(action: Any) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        called_actions.append(action)
        return original_step(action)

    env.step = tracking_step  # type: ignore[method-assign]

    # Policy trả về hành động NaN ở bước đầu tiên
    bad_policy = ScriptedPolicy(actions=[[float("nan"), 0.1, 0.2, 0.3, 0.4, 0.5]])

    episode = record_episode(
        env,
        bad_policy,
        split="test",
        target_index=0,
        seed=42,
    )

    # env.step không được gọi với hành động NaN
    assert len(called_actions) == 0, "env.step không được gọi khi hành động không hợp lệ"
    assert episode.outcome.end_reason == "abnormal"
    assert episode.outcome.reached is False
    assert episode.outcome.terminated is False
    assert episode.outcome.truncated is False
    assert episode.outcome.n_actions == 0
    assert len(episode.frames) == 1  # Chỉ có khung ban đầu sau reset


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "invalid_action",
    [
        [float("nan")] * 6,
        [float("inf")] * 6,
        [-0.1, 0.2, 0.3, 0.4, 0.5, 0.6],  # Dưới 0
        [1.05, 0.2, 0.3, 0.4, 0.5, 0.6],  # Trên 1.0
        [0.5] * 5,  # Thiếu chiều (5 phần tử)
        [0.5] * 7,  # Thừa chiều (7 phần tử)
        [True, 0.2, 0.3, 0.4, 0.5, 0.6],  # Kiểu bool
    ],
)
def test_fr_003_action_out_of_bounds_blocked_at_boundary(invalid_action: list[Any]) -> None:
    """FR-003, INV-002: Kiểm tra các trường hợp giá trị hành động ngoài biên [0, 1] hoặc phi số."""
    env = make_env(split="test")
    policy = ScriptedPolicy(actions=[invalid_action])

    episode = record_episode(
        env,
        policy,
        split="test",
        target_index=0,
        seed=42,
    )

    assert episode.outcome.end_reason == "abnormal"
    assert episode.outcome.reached is False
    assert episode.outcome.terminated is False
    assert episode.outcome.truncated is False
    assert len(episode.frames) == 1


def test_inv_002_recorder_never_writes_env_state() -> None:
    """INV-002: Quá trình ghi nhận hoàn toàn chỉ-đọc (read-only), không làm sai lệch trạng thái."""
    env1 = make_env(split="test")
    env2 = make_env(split="test")

    action_seq = [
        [0.2, 0.1, 0.3, 0.4, 0.2, 0.1],
        [0.3, 0.2, 0.1, 0.5, 0.1, 0.2],
        [0.1, 0.4, 0.2, 0.3, 0.3, 0.1],
    ]

    # Nhánh 1: Chạy trực tiếp qua env1.step
    env1.reset(seed=100, options={"split": "test", "target_index": 0})
    traj_direct: list[dict[str, Any]] = []
    traj_direct.append({
        "qpos": env1.read_state().qpos.copy(),
        "qvel": env1.read_state().qvel.copy(),
        "act": env1.read_state().act.copy(),
    })
    for act in action_seq:
        _, _, term, trunc, _ = env1.step(np.array(act, dtype=np.float32))
        st = env1.read_state()
        traj_direct.append({
            "qpos": st.qpos.copy(),
            "qvel": st.qvel.copy(),
            "act": st.act.copy(),
        })
        if term or trunc:
            break

    # Nhánh 2: Chạy qua record_episode trên env2
    policy = ScriptedPolicy(actions=action_seq)
    episode = record_episode(
        env2,
        policy,
        split="test",
        target_index=0,
        seed=100,
    )

    # So sánh từng khung hình giữa hai nhánh
    assert len(episode.frames) == len(traj_direct)
    for k in range(len(traj_direct)):
        np.testing.assert_allclose(episode.frames[k].qpos, traj_direct[k]["qpos"], atol=1e-9)
        np.testing.assert_allclose(episode.frames[k].qvel, traj_direct[k]["qvel"], atol=1e-9)
        np.testing.assert_allclose(episode.frames[k].activation, traj_direct[k]["act"], atol=1e-9)


def test_fr_016_target_selection_by_index_and_split() -> None:
    """FR-016: Chọn mục tiêu chính xác theo chỉ số target_index và tập phân tách split."""
    env = make_env(split="test")
    policy = ScriptedPolicy(default_action=[0.1] * 6)

    # Kiểm tra với target_index=1 trong tập test
    ep_test1 = record_episode(
        env,
        policy,
        split="test",
        target_index=1,
        seed=77,
    )
    assert ep_test1.target.split == "test"
    assert ep_test1.target.index == 1
    expected_pos_test1 = env.targets.test.targets[1].position_m
    np.testing.assert_allclose(ep_test1.target.position_m, expected_pos_test1, atol=1e-7)

    # Kiểm tra với target_index=0 trong tập train
    ep_train0 = record_episode(
        env,
        policy,
        split="train",
        target_index=0,
        seed=77,
    )
    assert ep_train0.target.split == "train"
    assert ep_train0.target.index == 0
    expected_pos_train0 = env.targets.train.targets[0].position_m
    np.testing.assert_allclose(ep_train0.target.position_m, expected_pos_train0, atol=1e-7)


def test_physics_instability_raises_demo_unstable() -> None:
    """API-VIS-0004: Mất ổn định vật lý đóng gói abnormal và ném DemoUnstable."""
    env = make_env(split="test")
    policy = ScriptedPolicy(
        actions=[
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
        ]
    )

    original_step = env.step
    call_count = 0

    def faulty_step(action: Any) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise PhysicsInstabilityError("Mô phỏng phát hiện gia tốc vô hạn (NaN/Inf)")
        return original_step(action)

    env.step = faulty_step  # type: ignore[method-assign]

    with pytest.raises(DemoUnstable) as exc_info:
        record_episode(
            env,
            policy,
            split="test",
            target_index=0,
            seed=42,
        )

    # Kiểm tra ngoại lệ chứa thông tin episode dở dang đã đóng gói
    err = exc_info.value
    assert hasattr(err, "episode")
    partial_ep = err.episode
    assert isinstance(partial_ep, Episode)
    assert partial_ep.outcome.end_reason == "abnormal"
    assert partial_ep.outcome.reached is False
    assert partial_ep.outcome.terminated is False
    assert partial_ep.outcome.truncated is False
    # Đã chạy thành công 1 bước trước khi lỗi ở bước 2 -> có 2 frames (frame 0 và frame 1)
    assert len(partial_ep.frames) == 2
    assert partial_ep.outcome.n_actions == 1


def test_nfr_repro_001_reproducibility_same_seed() -> None:
    """NFR-REPRO-001: Tính tái lập của demo khi cùng checkpoint/policy, seed và mục tiêu."""
    env = make_env(split="test")
    policy1 = ScriptedPolicy(
        actions=[
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            [0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
            [0.05, 0.15, 0.25, 0.35, 0.45, 0.55],
        ]
    )
    policy2 = ScriptedPolicy(
        actions=[
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            [0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
            [0.05, 0.15, 0.25, 0.35, 0.45, 0.55],
        ]
    )

    ep1 = record_episode(env, policy1, split="test", target_index=2, seed=999)
    ep2 = record_episode(env, policy2, split="test", target_index=2, seed=999)

    assert len(ep1.frames) == len(ep2.frames)
    assert ep1.outcome.n_actions == ep2.outcome.n_actions
    assert ep1.outcome.end_reason == ep2.outcome.end_reason

    for f1, f2 in zip(ep1.frames, ep2.frames):
        assert abs(f1.t_s - f2.t_s) <= 1e-6
        np.testing.assert_allclose(f1.qpos, f2.qpos, atol=1e-6)
        np.testing.assert_allclose(f1.qvel, f2.qvel, atol=1e-6)
        np.testing.assert_allclose(f1.activation, f2.activation, atol=1e-6)
        if f1.excitation is not None:
            assert f2.excitation is not None
            np.testing.assert_allclose(f1.excitation, f2.excitation, atol=1e-6)
        np.testing.assert_allclose(f1.fingertip_position_m, f2.fingertip_position_m, atol=1e-6)
        assert abs(f1.distance_m - f2.distance_m) <= 1e-6
        assert abs(f1.reward - f2.reward) <= 1e-6


def test_source_provenance_preserved() -> None:
    """FR-007, INV-003: Lưu trữ chính xác hồ sơ nguồn checkpoint hoặc null."""
    env = make_env(split="test")
    policy = ScriptedPolicy(actions=[[0.2] * 6])

    # Ca 1: source = None
    ep_none = record_episode(env, policy, split="test", target_index=0, seed=1, source=None)
    assert ep_none.source is None

    # Ca 2: source là đối tượng SourceRecord
    src_record = SourceRecord(
        checkpoint_path="runs/exp_01/checkpoints/best.pt",
        checkpoint_sha256="c" * 64,
        run_id="exp_01",
        update_idx=50,
    )
    ep_with_src = record_episode(
        env,
        policy,
        split="test",
        target_index=0,
        seed=1,
        source=src_record,
    )
    assert ep_with_src.source is not None
    assert ep_with_src.source.checkpoint_path == "runs/exp_01/checkpoints/best.pt"
    assert ep_with_src.source.checkpoint_sha256 == "c" * 64
    assert ep_with_src.source.run_id == "exp_01"
    assert ep_with_src.source.update_idx == 50

    # Ca 3: source là dict
    src_dict = {
        "checkpoint_path": "runs/exp_02/checkpoints/latest.pt",
        "checkpoint_sha256": "d" * 64,
        "run_id": "exp_02",
        "update_idx": 100,
    }
    ep_dict_src = record_episode(
        env,
        policy,
        split="test",
        target_index=0,
        seed=1,
        source=src_dict,
    )
    assert ep_dict_src.source is not None
    assert ep_dict_src.source.checkpoint_path == "runs/exp_02/checkpoints/latest.pt"


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "path",
    [r"C:\runs\exp_01\checkpoints\best.pt", "C:/runs/exp_01/checkpoints/best.pt"],
)
def test_inv_005_windows_absolute_checkpoint_records_filename(path: str) -> None:
    """INV-005: Đường dẫn checkpoint tuyệt đối kiểu Windows chỉ lộ tên tệp."""
    source = resolve_source(path)

    assert source is not None
    assert source.checkpoint_path == "best.pt"


def test_recorded_episode_validates_against_schema(episode_schema: dict[str, Any]) -> None:
    """FR-007, FR-009, NFR-REL-001: Bản ghi tạo ra thoả mãn schema và luật nhất quán R1-R7."""
    env = make_env(split="test")
    # Cho policy kích hoạt mạnh để episode tiến tới hoặc hết số bước
    policy = ScriptedPolicy(default_action=[0.5, 0.0, 0.0, 0.8, 0.9, 0.7])

    episode = record_episode(
        env,
        policy,
        split="test",
        target_index=0,
        seed=123,
    )

    data = episode.to_dict()

    # Kiểm tra JSON Schema hợp đồng
    if jsonschema is not None:
        jsonschema.validate(instance=data, schema=episode_schema)

    # Kiểm tra các quy tắc nhất quán (R1 - R7) của domain model
    validate_episode_dict(data)


def test_fr_015_visualization_has_no_training_imports() -> None:
    """FR-015: Khẳng định phân hệ visualization không nhập learning.trainer hoặc learning.ppo."""
    # Xoá nếu đã có trong sys.modules để kiểm tra nhập sạch
    for mod in ["mma_ai.learning.trainer", "mma_ai.learning.ppo"]:
        sys.modules.pop(mod, None)

    import mma_ai.visualization.recorder as rec_mod

    assert "mma_ai.learning.trainer" not in sys.modules
    assert "mma_ai.learning.ppo" not in sys.modules
    assert hasattr(rec_mod, "record_episode")
