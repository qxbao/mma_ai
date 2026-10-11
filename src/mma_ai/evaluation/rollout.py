"""Vòng chạy thu thập quỹ đạo đánh giá và bản ghi episode (EpisodeRecord).

Hiện thực các yêu cầu và bất biến theo hợp đồng phân hệ đánh giá:
- 004 FR-002, 004 INV-002, 004 AC-1: Chạy chính sách trên cùng danh sách mục tiêu
  theo cùng thứ tự, cùng hạt giống (seed) đếm tuần tự.
- 004 FR-003, 004 INV-003, 004 AC-1: Kiểm tra hành động hữu hạn và trong [0, 1]^6
  ngay trước env.step; chặn tại biên nếu vi phạm.
- 004 FR-016, 004 AC-1: Bắt lỗi mất ổn định vật lý (PhysicsInstabilityError),
  đếm vào tỷ lệ bất thường (abnormal), tính là không tới mục tiêu, không dừng lượt.
- 004 API-EVL-0005: run_policy_on_targets(env, policy, n_targets, repeats, seed_base)
  trả về danh sách EpisodeRecord.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from mma_ai.environment.errors import PhysicsInstabilityError
from mma_ai.evaluation.policies import LearnedPolicy, RandomPolicy


@dataclass(frozen=True)
class EpisodeRecord:
    """Bản ghi chi tiết kết quả của một tập phim (episode) trong lượt đánh giá.

    Lưu trữ đầy đủ các chỉ số của episode phục vụ tính toán thống kê và ghi tệp episodes.csv:
    - policy: Tên hoặc định danh của chính sách điều khiển.
    - episode: Chỉ số thứ tự episode trong lượt đánh giá (0-indexed).
    - target_index: Chỉ số mục tiêu kiểm thử trong tập test (target_index).
    - seed: Hạt giống ngẫu nhiên dùng để đặt lại môi trường.
    - reached: Cờ thành công (đạt mục tiêu khoảng cách <= dung sai).
    - end_reason: Lý do kết thúc episode (ví dụ: 'reached', 'max_actions', 'instability').
    - abnormal: Cờ đánh dấu episode kết thúc bất thường do lỗi số học hoặc vật lý.
    - final_distance_m: Khoảng cách cuối cùng tới mục tiêu tính bằng mét (None nếu abnormal).
    - return_: Tổng phần thưởng (cumulative return) của episode.
    - effort: Nỗ lực trung bình (trung bình theo bước của trung bình kích hoạt 6 cơ).
    - act_m0..act_m5: Mức kích hoạt trung bình của từng cơ bắp m0 đến m5.
    - n_steps: Số bước mô phỏng hợp lệ thực hiện trong episode.
    - nan_count: Số lượng giá trị NaN phát hiện trong hành động của episode.
    - inf_count: Số lượng giá trị vô cực (Inf) phát hiện trong hành động của episode.
    """

    policy: str
    episode: int
    target_index: int
    seed: int
    reached: bool
    end_reason: str | None
    abnormal: bool
    final_distance_m: float | None
    return_: float
    effort: float
    act_m0: float
    act_m1: float
    act_m2: float
    act_m3: float
    act_m4: float
    act_m5: float
    n_steps: int
    nan_count: int
    inf_count: int

    @property
    def episode_return(self) -> float:
        """Thuộc tính đọc tổng phần thưởng của episode."""
        return self.return_

    @property
    def return_val(self) -> float:
        """Thuộc tính đọc giá trị phần thưởng thuận tiện."""
        return self.return_

    def __getattr__(self, name: str) -> Any:
        """Hỗ trợ truy cập thuộc tính 'return' (từ khoá trong Python) như một trường dữ liệu."""
        if name == "return":
            return self.return_
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def to_dict(self) -> dict[str, Any]:
        """Chuyển đổi bản ghi sang định dạng từ điển tương thích với episodes.csv."""
        return {
            "policy": self.policy,
            "episode": self.episode,
            "target_index": self.target_index,
            "seed": self.seed,
            "reached": self.reached,
            "end_reason": self.end_reason,
            "abnormal": self.abnormal,
            "final_distance_m": self.final_distance_m,
            "return": self.return_,
            "effort": self.effort,
            "act_m0": self.act_m0,
            "act_m1": self.act_m1,
            "act_m2": self.act_m2,
            "act_m3": self.act_m3,
            "act_m4": self.act_m4,
            "act_m5": self.act_m5,
            "n_steps": self.n_steps,
            "nan_count": self.nan_count,
            "inf_count": self.inf_count,
        }


def _infer_policy_name(policy: Any, explicit_name: str | None = None) -> str:
    """Xác định tên định danh cho chính sách điều khiển."""
    if explicit_name is not None:
        return str(explicit_name)
    if hasattr(policy, "name") and isinstance(getattr(policy, "name"), str):
        return str(getattr(policy, "name"))
    if hasattr(policy, "kind") and isinstance(getattr(policy, "kind"), str):
        return str(getattr(policy, "kind"))
    if isinstance(policy, RandomPolicy):
        return "random"
    if isinstance(policy, LearnedPolicy):
        return "learned"
    return str(getattr(policy, "__class__", type(policy)).__name__)


def _run_single_episode(
    env: Any,
    policy: Any,
    pol_name: str,
    episode_idx: int,
    target_idx: int,
    current_seed: int,
) -> EpisodeRecord:
    """Thực thi một episode duy nhất và trả về bản ghi EpisodeRecord."""
    # 1. Đặt lại môi trường với mục tiêu và hạt giống xác định (004 FR-002, 004 INV-002)
    try:
        obs, _ = env.reset(
            seed=current_seed,
            options={"split": "test", "target_index": target_idx},
        )
    except PhysicsInstabilityError:
        return EpisodeRecord(
            policy=pol_name,
            episode=episode_idx,
            target_index=target_idx,
            seed=current_seed,
            reached=False,
            end_reason="instability",
            abnormal=True,
            final_distance_m=None,
            return_=0.0,
            effort=0.0,
            act_m0=0.0,
            act_m1=0.0,
            act_m2=0.0,
            act_m3=0.0,
            act_m4=0.0,
            act_m5=0.0,
            n_steps=0,
            nan_count=0,
            inf_count=0,
        )

    step_count = 0
    total_reward = 0.0
    ctrl_sum = np.zeros(6, dtype=np.float64)
    nan_count = 0
    inf_count = 0
    final_distance: float | None = None
    reached = False
    end_reason: str | None = None
    abnormal = False

    # 2. Vòng lặp các bước tương tác trong episode
    while True:
        # Lấy hành động kích thích cơ từ chính sách
        raw_action = policy.act(obs)

        # Chặn tại biên và thẩm định hành động ngay trước env.step (004 FR-003, 004 INV-003)
        try:
            raw_arr = np.asarray(raw_action)
            # Kiểm tra nếu hành động có chứa kiểu số phức (INV-003: hành động phải là số thực)
            if np.iscomplexobj(raw_arr):
                n_nans = int(np.isnan(raw_arr).sum())
                n_infs = int(np.isinf(raw_arr).sum())
                if n_nans > 0 or n_infs > 0:
                    nan_count += n_nans
                    inf_count += n_infs
                abnormal = True
                end_reason = "abnormal_action"
                break

            if raw_arr.dtype == object:
                # Kiểm tra từng phần tử nếu mảng là kiểu đối tượng (object chứa complex)
                for item in raw_arr.flat:
                    if isinstance(item, complex):
                        if math.isnan(item.real) or math.isnan(item.imag):
                            nan_count += 1
                        if math.isinf(item.real) or math.isinf(item.imag):
                            inf_count += 1
                        abnormal = True
                if abnormal:
                    end_reason = "abnormal_action"
                    break

            act_arr = raw_arr.astype(np.float64).reshape(-1)
        except Exception:
            abnormal = True
            end_reason = "abnormal_action"
            break

        if act_arr.shape != (6,):
            abnormal = True
            end_reason = "abnormal_action"
            break

        n_nans = int(np.isnan(act_arr).sum())
        n_infs = int(np.isinf(act_arr).sum())

        if n_nans > 0 or n_infs > 0:
            nan_count += n_nans
            inf_count += n_infs
            abnormal = True
            end_reason = "abnormal_action"
            break

        if np.any(act_arr < 0.0) or np.any(act_arr > 1.0):
            abnormal = True
            end_reason = "abnormal_action"
            break

        # Tiến bước mô phỏng an toàn khi hành động hoàn toàn hợp lệ
        try:
            next_obs, step_reward, terminated, truncated, step_info = env.step(act_arr)
        except PhysicsInstabilityError:
            abnormal = True
            end_reason = "instability"
            break

        step_count += 1
        total_reward += float(step_reward)

        # Trích xuất số liệu từ info (004 INV-003: không truy cập trạng thái ngoài info)
        ctrl_eff = np.asarray(
            step_info.get("ctrl_effective", act_arr),
            dtype=np.float64,
        ).reshape(-1)
        ctrl_sum += ctrl_eff

        final_distance = float(step_info.get("distance_m", 0.0))
        reached = bool(step_info.get("reached", False))
        end_reason = step_info.get("end_reason")

        obs = next_obs
        if terminated or truncated:
            break

    # 3. Tổng hợp kết quả và xử lý trường hợp bất thường
    if abnormal:
        reached = False
        final_distance_m = None
    else:
        final_distance_m = final_distance

    if step_count > 0:
        act_muscles = ctrl_sum / float(step_count)
        effort = float(np.mean(act_muscles))
    else:
        act_muscles = np.zeros(6, dtype=np.float64)
        effort = 0.0

    return EpisodeRecord(
        policy=pol_name,
        episode=episode_idx,
        target_index=target_idx,
        seed=current_seed,
        reached=reached,
        end_reason=end_reason,
        abnormal=abnormal,
        final_distance_m=final_distance_m,
        return_=float(total_reward),
        effort=float(effort),
        act_m0=float(act_muscles[0]),
        act_m1=float(act_muscles[1]),
        act_m2=float(act_muscles[2]),
        act_m3=float(act_muscles[3]),
        act_m4=float(act_muscles[4]),
        act_m5=float(act_muscles[5]),
        n_steps=int(step_count),
        nan_count=int(nan_count),
        inf_count=int(inf_count),
    )


def run_policy_on_targets(
    env: Any,
    policy: Any,
    n_targets: int,
    repeats: int = 1,
    seed_base: int = 12345,
    policy_name: str | None = None,
) -> list[EpisodeRecord]:
    """Chạy chính sách điều khiển trên tập mục tiêu kiểm thử (004 API-EVL-0005).

    Args:
        env: Môi trường mô phỏng (ElbowReachEnv).
        policy: Chính sách điều khiển cung cấp hàm act(obs).
        n_targets: Số lượng mục tiêu kiểm thử cần đánh giá.
        repeats: Số lần lặp lại cho mỗi mục tiêu (mặc định 1).
        seed_base: Hạt giống khởi đầu cho chuỗi episode (mặc định 12345).
        policy_name: Tên chính sách tuỳ chọn ghi vào bản ghi.

    Returns:
        list[EpisodeRecord]: Danh sách các bản ghi episode của lượt chạy.

    Raises:
        ValueError: Khi n_targets <= 0 hoặc repeats <= 0.
    """
    if n_targets <= 0:
        raise ValueError(
            f"Số lượng mục tiêu (n_targets) phải là số nguyên dương > 0, nhận: {n_targets}"
        )
    if repeats <= 0:
        raise ValueError(
            f"Số lần lặp (repeats) phải là số nguyên dương > 0, nhận: {repeats}"
        )

    pol_name = _infer_policy_name(policy, explicit_name=policy_name)
    records: list[EpisodeRecord] = []
    episode_idx = 0

    for _rep in range(repeats):
        for target_idx in range(n_targets):
            current_seed = seed_base + episode_idx
            rec = _run_single_episode(
                env=env,
                policy=policy,
                pol_name=pol_name,
                episode_idx=episode_idx,
                target_idx=target_idx,
                current_seed=current_seed,
            )
            records.append(rec)
            episode_idx += 1

    return records


__all__: list[str] = [
    "EpisodeRecord",
    "run_policy_on_targets",
]
