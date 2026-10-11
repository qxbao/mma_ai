"""Mô-đun tóm tắt phiên phát và demo (mma_ai.visualization.summary).

Cung cấp cấu trúc và hàm tóm tắt máy đọc được theo hợp đồng API:
- FR-010: Tóm tắt không màn hình (--headless) theo contracts/replay-summary.schema.json.
- FR-018: Định dạng đường dẫn tương đối (relative path) và thông báo lỗi tiếng Việt.
- INV-006: Thống kê mức kích hoạt cơ (activation) không làm tròn số học.
- NFR-REL-001: Từ chối giá trị không hữu hạn (NaN, Infinity).
- API-VIS-0006: summarize_episode(
      episode, model_check, *, source, saved_episode=None, playback=None, warnings=()
  ) -> dict.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from mma_ai.visualization.errors import EpisodeInvalid

SUPPORTED_SCHEMA_VERSION = "1.0.0"


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    """Trích xuất giá trị trường từ đối tượng hoặc từ điển an toàn."""
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return default


def _to_relative_path(path_val: str | Path | None) -> str | None:
    """Chuyển đổi đường dẫn tuyệt đối hoặc chuỗi thành đường dẫn tương đối (FR-018)."""
    if path_val is None:
        return None
    raw_str = str(path_val).strip()
    if not raw_str:
        return None

    path_obj = Path(raw_str)
    if path_obj.is_absolute():
        try:
            rel = path_obj.relative_to(Path.cwd())
            return str(rel).replace("\\", "/")
        except ValueError:
            # Đường dẫn tuyệt đối nằm ngoài thư mục làm việc hiện tại
            rel_str = os.path.relpath(path_obj, Path.cwd())
            return rel_str.replace("\\", "/")

    return raw_str.replace("\\", "/")


def _check_finite(obj: Any, path: str = "summary") -> None:
    """Kiểm tra đệ quy tính hữu hạn của mọi số thực trong cấu trúc dữ liệu (NFR-REL-001)."""
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise EpisodeInvalid(f"Phát hiện giá trị không hữu hạn (non-finite) tại {path}: {obj}")
    elif isinstance(obj, (list, tuple)):
        for idx, item in enumerate(obj):
            _check_finite(item, f"{path}[{idx}]")
    elif isinstance(obj, dict):
        for key, val in obj.items():
            _check_finite(val, f"{path}.{key}")


def summarize_episode(
    episode: Any,
    model_check: Any,
    *,
    source: Any,
    saved_episode: str | Path | None = None,
    playback: Any = None,
    warnings: Sequence[str] = (),
    mode: str | None = None,
    headless: bool | None = None,
) -> dict[str, Any]:
    """Tổng hợp thông số phiên phát lại thành từ điển tóm tắt (API-VIS-0006).

    Tuân thủ lược đồ contracts/replay-summary.schema.json:
    - n_frames, n_actions, duration_sim_s (xử lý không chia 0 khi episode 1 khung).
    - Thống kê activation từng cơ (min, max, mean, final) không làm tròn (INV-006).
    - Chuẩn hoá mọi đường dẫn thành tương đối (FR-018).
    - Từ chối mọi giá trị NaN/Infinity (NFR-REL-001).
    """
    # 1. Trích xuất danh sách khung hình và kiểm tra số lượng khung
    frames = _get_val(episode, "frames")
    if not frames:
        raise EpisodeInvalid("Bản ghi episode không có khung hình (frames) nào.")

    n_frames = len(frames)
    first_frame = frames[0]
    last_frame = frames[-1]

    first_t_s = float(_get_val(first_frame, "t_s", 0.0))
    last_t_s = float(_get_val(last_frame, "t_s", 0.0))

    # Episode một khung kết thúc ngay sau reset, thời lượng bằng 0 s
    duration_sim_s = 0.0 if n_frames <= 1 else float(last_t_s - first_t_s)

    outcome_obj = _get_val(episode, "outcome")
    if outcome_obj is not None:
        n_actions = int(_get_val(outcome_obj, "n_actions", max(0, n_frames - 1)))
        reached = bool(_get_val(outcome_obj, "reached", False))
        end_reason = _get_val(outcome_obj, "end_reason")
        final_dist = _get_val(outcome_obj, "final_distance_m")
        final_distance_m = float(final_dist) if final_dist is not None else None
    else:
        n_actions = max(0, n_frames - 1)
        reached = False
        end_reason = None
        final_distance_m = None

    # 2. Trích xuất thông tin mục tiêu (target)
    target_obj = _get_val(episode, "target")
    if target_obj is None:
        raise EpisodeInvalid("Bản ghi episode thiếu thông tin mục tiêu (target).")

    pos = _get_val(target_obj, "position_m")
    if pos is None or len(pos) != 3:
        raise EpisodeInvalid("Toạ độ mục tiêu position_m phải có đúng 3 phần tử [x, y, z].")
    target_position_m = [float(pos[0]), float(pos[1]), float(pos[2])]
    target_split = _get_val(target_obj, "split")
    target_idx = _get_val(target_obj, "index")
    target_index = int(target_idx) if target_idx is not None else None

    # 3. Trích xuất tên cơ và tính thống kê activation (INV-006: không làm tròn)
    model_obj = _get_val(episode, "model")
    if model_obj is None:
        raise EpisodeInvalid("Bản ghi episode thiếu thông tin mô hình (model).")

    raw_muscle_names = _get_val(model_obj, "muscle_names")
    if not raw_muscle_names:
        raise EpisodeInvalid("Mô hình thiếu danh sách tên cơ bắp (muscle_names).")
    muscle_names = [str(name) for name in raw_muscle_names]
    n_muscles = len(muscle_names)

    min_acts: list[float] = []
    max_acts: list[float] = []
    mean_acts: list[float] = []
    final_acts: list[float] = []

    last_frame_act = _get_val(last_frame, "activation", [])

    for m_idx in range(n_muscles):
        m_values: list[float] = []
        for f in frames:
            act_list = _get_val(f, "activation")
            if act_list is None or len(act_list) <= m_idx:
                err_msg = f"Khung hình thiếu activation cho cơ {m_idx} ({muscle_names[m_idx]})."
                raise EpisodeInvalid(err_msg)
            m_values.append(float(act_list[m_idx]))

        min_acts.append(min(m_values))
        max_acts.append(max(m_values))
        # Không dùng round(), giữ nguyên độ chính xác số thực IEEE 754
        mean_acts.append(sum(m_values) / len(m_values))
        final_acts.append(float(last_frame_act[m_idx]))

    # 4. Xử lý model_check
    if hasattr(model_check, "to_dict"):
        model_check_dict = model_check.to_dict()
    elif isinstance(model_check, Mapping):
        model_check_dict = {
            "match": bool(model_check["match"]),
            "compatible": bool(model_check["compatible"]),
            "episode_sha256": str(model_check["episode_sha256"]),
            "current_sha256": str(model_check["current_sha256"]),
            "reasons": list(model_check.get("reasons", [])),
        }
    else:
        raise EpisodeInvalid("Tham số model_check không hợp lệ.")

    # 5. Xử lý source và xác định chế độ (mode)
    ep_path: str | None = None
    ckpt_path: str | None = None
    ckpt_sha256: str | None = None

    if isinstance(source, Mapping):
        ep_path = _to_relative_path(source.get("episode_path"))
        ckpt_path = _to_relative_path(source.get("checkpoint_path"))
        ckpt_sha256 = source.get("checkpoint_sha256")
    elif isinstance(source, (str, Path)):
        src_str = str(source)
        if src_str.endswith(".pt"):
            ckpt_path = _to_relative_path(src_str)
            ep_source = _get_val(episode, "source")
            if ep_source is not None:
                ckpt_sha256 = _get_val(ep_source, "checkpoint_sha256")
        else:
            ep_path = _to_relative_path(src_str)
    elif hasattr(source, "checkpoint_path"):
        ckpt_path = _to_relative_path(getattr(source, "checkpoint_path"))
        ckpt_sha256 = getattr(source, "checkpoint_sha256", None)

    if mode is None:
        if isinstance(source, Mapping) and "mode" in source:
            mode = str(source["mode"])
        elif ckpt_path is not None and ep_path is None:
            mode = "demo"
        else:
            mode = "episode"

    if mode not in ("episode", "demo"):
        err_mode = f"Chế độ tóm tắt mode={mode!r} không hợp lệ, phải là 'episode' hoặc 'demo'."
        raise EpisodeInvalid(err_mode)

    # Theo hợp đồng lược đồ, chế độ demo có episode_path là null
    if mode == "demo":
        ep_path = None

    # 6. Xử lý headless và playback
    playback_dict: dict[str, Any] | None = None
    if playback is not None:
        if hasattr(playback, "to_dict"):
            playback_dict = playback.to_dict()
        elif isinstance(playback, Mapping):
            playback_dict = {
                "speed": float(playback["speed"]),
                "frames_shown": int(playback["frames_shown"]),
                "wall_s": float(playback["wall_s"]),
                "sim_s": float(playback["sim_s"]),
                "ratio": float(playback["ratio"]) if playback.get("ratio") is not None else None,
                "frames_late": int(playback["frames_late"]),
            }

    if headless is None:
        headless = playback is None

    seed_val = int(_get_val(episode, "seed", 0))

    # 7. Xây dựng bản tóm tắt hoàn chỉnh theo schema
    summary_data: dict[str, Any] = {
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "mode": mode,
        "headless": bool(headless),
        "source": {
            "episode_path": ep_path,
            "checkpoint_path": ckpt_path,
            "checkpoint_sha256": str(ckpt_sha256) if ckpt_sha256 is not None else None,
        },
        "model_check": {
            "match": bool(model_check_dict["match"]),
            "compatible": bool(model_check_dict["compatible"]),
            "episode_sha256": str(model_check_dict["episode_sha256"]),
            "current_sha256": str(model_check_dict["current_sha256"]),
            "reasons": list(model_check_dict["reasons"]),
        },
        "n_frames": n_frames,
        "n_actions": n_actions,
        "duration_sim_s": duration_sim_s,
        "seed": seed_val,
        "target": {
            "position_m": target_position_m,
            "split": str(target_split) if target_split is not None else None,
            "index": target_index,
        },
        "outcome": {
            "end_reason": str(end_reason) if end_reason is not None else None,
            "reached": reached,
            "final_distance_m": final_distance_m,
        },
        "activation": {
            "muscle_names": muscle_names,
            "min": min_acts,
            "max": max_acts,
            "mean": mean_acts,
            "final": final_acts,
        },
        "saved_episode": _to_relative_path(saved_episode),
        "playback": playback_dict,
        "warnings": [str(w) for w in warnings],
    }

    # 8. Kiểm tra tính hữu hạn (NFR-REL-001: 0 giá trị NaN/Infinity)
    _check_finite(summary_data)

    return summary_data


__all__: list[str] = ["SUPPORTED_SCHEMA_VERSION", "summarize_episode"]
