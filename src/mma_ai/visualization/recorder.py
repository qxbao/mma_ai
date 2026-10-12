"""Mô-đun thu bản ghi một episode mô phỏng chuyển động cơ bắp (mma_ai.visualization.recorder).

Cung cấp hàm record_episode theo hợp đồng API-VIS-0004:
- FR-002: Chạy demo một episode trên môi trường khuỷu tay bằng policy xác định.
- FR-003: Chỉ cho phép vector kích thích cơ bắp u in [0, 1]^6 đi vào mô phỏng.
- FR-015: Replay chạy tiến trình riêng, không nhập mã huấn luyện (learning.trainer, learning.ppo);
  nhập lazy learning.checkpoint khi cần nạp thông tin điểm kiểm tra.
- FR-016: Chọn mục tiêu qua chỉ số (target_index) và phân tách (split).
- INV-002: Lớp hiển thị chỉ đọc trạng thái qua env.read_state(), không ghi vào MjData.
- NFR-REPRO-001: Tái lập hoàn toàn chuỗi hành động và trạng thái khi cùng seed và mục tiêu.
- API-VIS-0004: record_episode(env, policy, *, split, target_index, seed, source) -> Episode.
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

import mujoco
import numpy as np

from mma_ai.compat.pathrules import is_absolute_any_os
from mma_ai.environment.errors import PhysicsInstabilityError
from mma_ai.visualization.episode import (
    SUPPORTED_SCHEMA_VERSION,
    Episode,
    Frame,
    ModelRecord,
    OutcomeRecord,
    SourceRecord,
    TargetRecord,
    TimingRecord,
)
from mma_ai.visualization.errors import DemoUnstable


def validate_action(action: Any) -> tuple[bool, list[float] | None]:
    """Kiểm tra tính hợp lệ và biên độ của vector kích thích cơ bắp (FR-003, INV-002).

    Yêu cầu:
    - Đúng 6 chiều tương ứng 6 cơ bắp điều khiển.
    - Giá trị số hữu hạn (không NaN, không Inf).
    - Nằm trong đoạn đơn vị [0.0, 1.0].
    - Không chấp nhận giá trị kiểu bool.

    Returns:
        Bộ đôi (is_valid, clean_action_list). Trả về (False, None) nếu vi phạm.
    """
    if hasattr(action, "detach"):
        # Hỗ trợ PyTorch tensor nếu có mà không cần import torch
        action = action.detach().cpu().numpy()

    if isinstance(action, np.ndarray):
        action = action.flatten().tolist()

    if not isinstance(action, (list, tuple)) or len(action) != 6:
        return False, None

    clean_values: list[float] = []
    for val in action:
        if isinstance(val, bool) or not isinstance(val, (int, float, np.floating, np.integer)):
            return False, None
        num = float(val)
        if not math.isfinite(num) or num < 0.0 or num > 1.0:
            return False, None
        clean_values.append(num)

    return True, clean_values


def resolve_source(
    source: SourceRecord | dict[str, Any] | str | Path | None,
) -> SourceRecord | None:
    """Xử lý và chuẩn hoá hồ sơ nguồn gốc checkpoint (FR-007, FR-015).

    Nhập lười mô-đun learning.checkpoint khi đầu vào là đường dẫn tệp.
    """
    if source is None:
        return None

    if isinstance(source, SourceRecord):
        return source

    if isinstance(source, dict):
        return SourceRecord.from_dict(source)

    if isinstance(source, (str, Path)):
        target_path = Path(source)
        try:
            # Nhập lười learning.checkpoint (FR-015)
            from mma_ai.learning.checkpoint import load_checkpoint

            ckpt = load_checkpoint(target_path)
            ckpt_rel = str(target_path)
            if is_absolute_any_os(ckpt_rel):
                ckpt_rel = PureWindowsPath(ckpt_rel).name
            sha = (
                hashlib.sha256(target_path.read_bytes()).hexdigest()
                if target_path.is_file()
                else "0" * 64
            )
            return SourceRecord(
                checkpoint_path=ckpt_rel,
                checkpoint_sha256=sha,
                run_id=None,
                update_idx=int(ckpt.update_idx) if hasattr(ckpt, "update_idx") else None,
            )
        except Exception:
            ckpt_rel = str(target_path)
            if is_absolute_any_os(ckpt_rel):
                ckpt_rel = PureWindowsPath(ckpt_rel).name
            sha = (
                hashlib.sha256(target_path.read_bytes()).hexdigest()
                if target_path.is_file()
                else "0" * 64
            )
            return SourceRecord(
                checkpoint_path=ckpt_rel,
                checkpoint_sha256=sha,
                run_id=None,
                update_idx=None,
            )

    return None


def record_episode(
    env: Any,
    policy: Any,
    *,
    split: str = "test",
    target_index: int = 0,
    seed: int = 0,
    source: SourceRecord | dict[str, Any] | str | Path | None = None,
) -> Episode:
    """Chạy và thu bản ghi một episode từ môi trường và chính sách điều khiển (API-VIS-0004).

    Quy trình thực thi:
    1. Đặt lại môi trường qua env.reset(seed, options={"split", "target_index"}).
    2. Đọc ảnh chụp trạng thái ban đầu qua env.read_state() (chỉ-đọc, không ghi MjData).
    3. Tạo khung hình 0 với excitation = None (theo luật R4).
    4. Mỗi bước gọi policy.act_deterministic(obs), kiểm tra tính hữu hạn và [0, 1]^6
       ngay trước khi gọi env.step(). Nếu vi phạm, chặn tại biên và kết thúc abnormal.
    5. Sau mỗi bước thành công, đọc trạng thái qua env.read_state() và lưu khung hình.
    6. Nếu gặp PhysicsInstabilityError, đóng gói phần đã chạy với end_reason="abnormal"
       và ném ngoại lệ DemoUnstable.

    Args:
        env: Môi trường khuỷu tay MyoElbow (ElbowReachEnv).
        policy: Chính sách điều khiển hỗ trợ phương thức act_deterministic(obs).
        split: Phân tách mục tiêu ('train' hoặc 'test').
        target_index: Chỉ số mục tiêu cần tiếp cận trong tập đã chọn.
        seed: Seed ngẫu nhiên phục vụ tính tái lập.
        source: Thông tin nguồn gốc checkpoint hoặc None.

    Returns:
        Đối tượng Episode tự đủ theo lược đồ contracts/episode.schema.json.

    Raises:
        DemoUnstable: Khi mô phỏng MuJoCo mất ổn định vật lý (PhysicsInstabilityError).
    """
    # 1. Đặt lại môi trường theo cấu hình chỉ định (FR-016)
    reset_opts = {"split": split, "target_index": target_index}
    obs, reset_info = env.reset(seed=seed, options=reset_opts)

    # 2. Thu thập siêu dữ liệu mô hình và thời gian mô phỏng (FR-007, INV-003)
    if hasattr(env, "model_record"):
        m_rec = env.model_record()
        model_record = ModelRecord(
            sha256=str(m_rec["sha256"]),
            source=str(m_rec["source"]),
            muscle_names=list(m_rec["muscle_names"]),
            nq=int(getattr(env.model, "nq", 1)),
            nv=int(getattr(env.model, "nv", 1)),
        )
        physics_dt = float(m_rec["physics_timestep_s"])
    else:
        model_record = ModelRecord(
            sha256=str(getattr(env, "model_sha256", "0" * 64)),
            source="myo_sim/elbow/myoelbow_1dof6muscles.xml",
            muscle_names=list(getattr(env, "muscle_names", [])),
            nq=int(getattr(env.model, "nq", 1)),
            nv=int(getattr(env.model, "nv", 1)),
        )
        physics_dt = float(getattr(getattr(env.model, "opt", None), "timestep", 0.002))

    action_dt = float(getattr(getattr(env, "cfg", None), "action_dt_s", 0.04))
    timing_record = TimingRecord(
        action_dt_s=action_dt,
        physics_timestep_s=physics_dt,
    )

    # 3. Thu thập thông tin mục tiêu (TargetRecord)
    target_pos_raw = reset_info.get("target_position_m", [0.0, 0.0, 0.0])
    target_record = TargetRecord(
        position_m=(float(target_pos_raw[0]), float(target_pos_raw[1]), float(target_pos_raw[2])),
        split=reset_info.get("target_split", split),
        index=reset_info.get("target_index", target_index),
        tolerance_m=float(getattr(getattr(env, "cfg", None), "tolerance_m", 0.05)),
    )

    source_record = resolve_source(source)

    library_versions: dict[str, str] = {
        "mujoco": getattr(mujoco, "__version__", "3.15.0"),
        "numpy": str(np.__version__),
    }

    # 4. Đọc trạng thái ban đầu chỉ-đọc qua env.read_state() (INV-002)
    state0 = env.read_state()
    init_dist = float(
        reset_info.get(
            "initial_distance_m",
            np.linalg.norm(state0.fingertip_position_m - state0.target_position_m),
        )
    )

    frame0 = Frame(
        t_s=float(state0.time_s),
        qpos=[float(x) for x in state0.qpos],
        qvel=[float(x) for x in state0.qvel],
        activation=[float(x) for x in state0.act],
        excitation=None,
        fingertip_position_m=(
            float(state0.fingertip_position_m[0]),
            float(state0.fingertip_position_m[1]),
            float(state0.fingertip_position_m[2]),
        ),
        distance_m=init_dist,
        reward=0.0,
    )

    frames: list[Frame] = [frame0]
    terminated = False
    truncated = False
    end_reason: str | None = None
    reached = False

    # 5. Vòng lặp các bước mô phỏng
    while not (terminated or truncated):
        action_raw = policy.act_deterministic(obs)
        is_valid, action_clean = validate_action(action_raw)
        if not is_valid or action_clean is None:
            # Chặn tại biên trước khi gọi env.step() (FR-003, INV-002)
            end_reason = "abnormal"
            break

        action_arr = np.array(action_clean, dtype=np.float32)

        try:
            obs, reward, terminated, truncated, info = env.step(action_arr)
        except PhysicsInstabilityError as err:
            # Đóng gói phần đã chạy và ném ngoại lệ DemoUnstable
            partial_outcome = OutcomeRecord(
                terminated=False,
                truncated=False,
                end_reason="abnormal",
                reached=False,
                n_actions=len(frames) - 1,
                final_distance_m=frames[-1].distance_m,
            )
            partial_episode = Episode(
                schema_version=SUPPORTED_SCHEMA_VERSION,
                created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                seed=int(seed),
                model=model_record,
                target=target_record,
                source=source_record,
                library_versions=library_versions,
                timing=timing_record,
                outcome=partial_outcome,
                frames=frames,
            )
            raise DemoUnstable(
                f"Mô phỏng MuJoCo mất ổn định số học hoặc vật lý trong demo: {err}",
                episode=partial_episode,
            ) from err

        # Đọc trạng thái qua env.read_state() (INV-002)
        state = env.read_state()
        dist_m = float(
            info.get(
                "distance_m",
                np.linalg.norm(state.fingertip_position_m - state.target_position_m),
            )
        )

        frame_k = Frame(
            t_s=float(state.time_s),
            qpos=[float(x) for x in state.qpos],
            qvel=[float(x) for x in state.qvel],
            activation=[float(x) for x in state.act],
            excitation=action_clean,
            fingertip_position_m=(
                float(state.fingertip_position_m[0]),
                float(state.fingertip_position_m[1]),
                float(state.fingertip_position_m[2]),
            ),
            distance_m=dist_m,
            reward=float(reward),
        )
        frames.append(frame_k)

        if terminated:
            end_reason = "reached"
            reached = True
            break
        elif truncated:
            end_reason = "max_actions"
            break

    # 6. Đóng gói kết quả OutcomeRecord
    if end_reason == "abnormal":
        outcome_record = OutcomeRecord(
            terminated=False,
            truncated=False,
            end_reason="abnormal",
            reached=False,
            n_actions=len(frames) - 1,
            final_distance_m=frames[-1].distance_m,
        )
    else:
        outcome_record = OutcomeRecord(
            terminated=bool(terminated),
            truncated=bool(truncated),
            end_reason=end_reason,
            reached=bool(reached),
            n_actions=len(frames) - 1,
            final_distance_m=frames[-1].distance_m,
        )

    return Episode(
        schema_version=SUPPORTED_SCHEMA_VERSION,
        created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        seed=int(seed),
        model=model_record,
        target=target_record,
        source=source_record,
        library_versions=library_versions,
        timing=timing_record,
        outcome=outcome_record,
        frames=frames,
    )


__all__: list[str] = [
    "record_episode",
    "resolve_source",
    "validate_action",
]
