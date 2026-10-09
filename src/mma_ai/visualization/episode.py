"""Mô-đun quản lý dữ liệu và đọc ghi bản ghi episode (mma_ai.visualization.episode).

Cung cấp các lớp dữ liệu bất biến và các hàm giao tiếp chuẩn theo hợp đồng API:
- FR-007: Định dạng dữ liệu episode tự đủ (self-contained) phục vụ phát lại 3D.
- FR-008: Ghi episode nguyên tử (atomic write) qua tệp tạm và từ chối ghi đè tệp đã tồn tại.
- FR-009: Kiểm tra cấu trúc và tính nhất quán (consistency) theo luật R1–R7 khi đọc.
- INV-003: Bản ghi episode tự đủ (seed, hash XML, 6 tên cơ, phiên bản, giá trị null tường minh).
- INV-004: Xử lý ngoại lệ chuẩn, dọn dẹp tệp tạm khi ngắt quãng, không để lại tệp dở dang.
- INV-005: Hoạt động chỉ đọc đối với tệp nguồn, không ghi đè tệp đích đã tồn tại.
- NFR-REL-001: Độ tin cậy số học, từ chối các giá trị không hữu hạn (non-finite: NaN, Inf).
- API-VIS-0002: read_episode(path) -> Episode.
- API-VIS-0003: write_episode(episode, path) -> Path.
"""

from __future__ import annotations

import copy
import json
import math
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mma_ai.visualization.errors import (
    EpisodeInvalid,
    EpisodeNotFound,
    EpisodeWriteError,
)

SUPPORTED_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class ModelRecord:
    """Hồ sơ mô hình vật lý và cơ bắp lúc ghi episode."""

    sha256: str
    source: str
    muscle_names: list[str]
    nq: int
    nv: int

    def to_dict(self) -> dict[str, Any]:
        """Xuất thông tin mô hình thành từ điển."""
        return {
            "sha256": self.sha256,
            "source": self.source,
            "muscle_names": list(self.muscle_names),
            "nq": self.nq,
            "nv": self.nv,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelRecord:
        """Khởi tạo từ từ điển."""
        return cls(
            sha256=str(data["sha256"]),
            source=str(data["source"]),
            muscle_names=list(data["muscle_names"]),
            nq=int(data["nq"]),
            nv=int(data["nv"]),
        )


@dataclass(frozen=True)
class TargetRecord:
    """Thông tin vị trí mục tiêu (target) của episode."""

    position_m: tuple[float, float, float]
    split: str | None
    index: int | None
    tolerance_m: float | None

    def to_dict(self) -> dict[str, Any]:
        """Xuất thông tin mục tiêu thành từ điển."""
        return {
            "position_m": list(self.position_m),
            "split": self.split,
            "index": self.index,
            "tolerance_m": self.tolerance_m,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TargetRecord:
        """Khởi tạo từ từ điển."""
        pos = data["position_m"]
        return cls(
            position_m=(float(pos[0]), float(pos[1]), float(pos[2])),
            split=data.get("split"),
            index=data.get("index"),
            tolerance_m=float(data["tolerance_m"]) if data.get("tolerance_m") is not None else None,
        )


@dataclass(frozen=True)
class SourceRecord:
    """Hồ sơ checkpoint đã sinh ra episode (nếu có)."""

    checkpoint_path: str
    checkpoint_sha256: str
    run_id: str | None
    update_idx: int | None

    def to_dict(self) -> dict[str, Any]:
        """Xuất thông tin nguồn thành từ điển."""
        return {
            "checkpoint_path": self.checkpoint_path,
            "checkpoint_sha256": self.checkpoint_sha256,
            "run_id": self.run_id,
            "update_idx": self.update_idx,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceRecord:
        """Khởi tạo từ từ điển."""
        return cls(
            checkpoint_path=str(data["checkpoint_path"]),
            checkpoint_sha256=str(data["checkpoint_sha256"]),
            run_id=data.get("run_id"),
            update_idx=data.get("update_idx"),
        )


@dataclass(frozen=True)
class TimingRecord:
    """Thông tin thời gian mô phỏng giữa các bước và bước vật lý."""

    action_dt_s: float
    physics_timestep_s: float

    def to_dict(self) -> dict[str, Any]:
        """Xuất thông tin thời gian thành từ điển."""
        return {
            "action_dt_s": self.action_dt_s,
            "physics_timestep_s": self.physics_timestep_s,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimingRecord:
        """Khởi tạo từ từ điển."""
        return cls(
            action_dt_s=float(data["action_dt_s"]),
            physics_timestep_s=float(data["physics_timestep_s"]),
        )


@dataclass(frozen=True)
class OutcomeRecord:
    """Kết quả kết thúc của một episode."""

    terminated: bool
    truncated: bool
    end_reason: str | None
    reached: bool
    n_actions: int
    final_distance_m: float | None

    def to_dict(self) -> dict[str, Any]:
        """Xuất thông tin kết quả thành từ điển."""
        return {
            "terminated": self.terminated,
            "truncated": self.truncated,
            "end_reason": self.end_reason,
            "reached": self.reached,
            "n_actions": self.n_actions,
            "final_distance_m": self.final_distance_m,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OutcomeRecord:
        """Khởi tạo từ từ điển."""
        final_dist = data.get("final_distance_m")
        return cls(
            terminated=bool(data["terminated"]),
            truncated=bool(data["truncated"]),
            end_reason=data.get("end_reason"),
            reached=bool(data["reached"]),
            n_actions=int(data["n_actions"]),
            final_distance_m=float(final_dist) if final_dist is not None else None,
        )


@dataclass(frozen=True)
class Frame:
    """Một khung thời gian (frame) trong episode."""

    t_s: float
    qpos: list[float]
    qvel: list[float]
    activation: list[float]
    excitation: list[float] | None
    fingertip_position_m: tuple[float, float, float]
    distance_m: float
    reward: float

    def to_dict(self) -> dict[str, Any]:
        """Xuất thông tin khung thời gian thành từ điển."""
        return {
            "t_s": self.t_s,
            "qpos": list(self.qpos),
            "qvel": list(self.qvel),
            "activation": list(self.activation),
            "excitation": list(self.excitation) if self.excitation is not None else None,
            "fingertip_position_m": list(self.fingertip_position_m),
            "distance_m": self.distance_m,
            "reward": self.reward,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Frame:
        """Khởi tạo khung thời gian từ từ điển."""
        fingertip = data["fingertip_position_m"]
        exc = data.get("excitation")
        return cls(
            t_s=float(data["t_s"]),
            qpos=[float(x) for x in data["qpos"]],
            qvel=[float(x) for x in data["qvel"]],
            activation=[float(x) for x in data["activation"]],
            excitation=[float(x) for x in exc] if exc is not None else None,
            fingertip_position_m=(float(fingertip[0]), float(fingertip[1]), float(fingertip[2])),
            distance_m=float(data["distance_m"]),
            reward=float(data["reward"]),
        )


@dataclass(frozen=True)
class Episode:
    """Bản ghi hoàn chỉnh của một episode phát lại 3D (FR-007, INV-003)."""

    schema_version: str
    created_utc: str
    seed: int
    model: ModelRecord
    target: TargetRecord
    source: SourceRecord | None
    library_versions: dict[str, str]
    timing: TimingRecord
    outcome: OutcomeRecord
    frames: list[Frame]

    def to_dict(self) -> dict[str, Any]:
        """Xuất toàn bộ bản ghi episode thành từ điển tương thích JSON Schema."""
        return {
            "schema_version": self.schema_version,
            "created_utc": self.created_utc,
            "seed": self.seed,
            "model": self.model.to_dict(),
            "target": self.target.to_dict(),
            "source": self.source.to_dict() if self.source is not None else None,
            "library_versions": dict(self.library_versions),
            "timing": self.timing.to_dict(),
            "outcome": self.outcome.to_dict(),
            "frames": [f.to_dict() for f in self.frames],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Episode:
        """Khởi tạo đối tượng Episode từ từ điển đã qua kiểm tra hợp lệ."""
        validate_episode_dict(data)

        src_data = data.get("source")
        return cls(
            schema_version=str(data["schema_version"]),
            created_utc=str(data["created_utc"]),
            seed=int(data["seed"]),
            model=ModelRecord.from_dict(data["model"]),
            target=TargetRecord.from_dict(data["target"]),
            source=SourceRecord.from_dict(src_data) if src_data is not None else None,
            library_versions={str(k): str(v) for k, v in data["library_versions"].items()},
            timing=TimingRecord.from_dict(data["timing"]),
            outcome=OutcomeRecord.from_dict(data["outcome"]),
            frames=[Frame.from_dict(f) for f in data["frames"]],
        )


def _check_finite_numbers(obj: Any, path: str = "gốc") -> None:
    """Đệ quy kiểm tra tất cả các giá trị số trong cấu trúc phải hữu hạn (NFR-REL-001, R7)."""
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        if not math.isfinite(obj):
            raise EpisodeInvalid(
                f"Luật R7 vi phạm: giá trị số không hữu hạn tại trường '{path}': {obj}"
            )
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _check_finite_numbers(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for idx, val in enumerate(obj):
            _check_finite_numbers(val, f"{path}[{idx}]")


def validate_episode_dict(data: dict[str, Any]) -> None:
    """Kiểm tra toàn diện tính hợp lệ của dữ liệu episode theo lược đồ và luật R1–R7."""
    if not isinstance(data, dict):
        raise EpisodeInvalid(
            f"Dữ liệu episode phải là một mapping/dict, nhận: {type(data).__name__}"
        )

    # Luật R7: Mọi số phải hữu hạn
    _check_finite_numbers(data)

    # 1. Kiểm tra các trường cấp cao nhất bắt buộc
    required_top = [
        "schema_version",
        "created_utc",
        "seed",
        "model",
        "target",
        "source",
        "library_versions",
        "timing",
        "outcome",
        "frames",
    ]
    for key in required_top:
        if key not in data:
            raise EpisodeInvalid(f"Thiếu trường bắt buộc trong episode: '{key}'")

    # Kiểm tra phiên bản lược đồ
    ver = data["schema_version"]
    if ver != SUPPORTED_SCHEMA_VERSION:
        raise EpisodeInvalid(
            f"Phiên bản lược đồ '{ver}' không được hỗ trợ (kỳ vọng: '{SUPPORTED_SCHEMA_VERSION}')"
        )

    # Kiểm tra seed
    seed = data["seed"]
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise EpisodeInvalid(
            f"Trường 'seed' phải là số nguyên không âm (non-negative integer), nhận: {seed}"
        )

    # 2. Kiểm tra phần model
    model = data["model"]
    if not isinstance(model, dict):
        raise EpisodeInvalid(f"Trường 'model' phải là một dict, nhận: {type(model).__name__}")
    for k in ["sha256", "source", "muscle_names", "nq", "nv"]:
        if k not in model:
            raise EpisodeInvalid(f"Thiếu trường bắt buộc trong 'model': '{k}'")

    sha = model["sha256"]
    if not isinstance(sha, str) or not re.fullmatch(r"^[0-9a-f]{64}$", sha):
        raise EpisodeInvalid(
            f"Trường 'model.sha256' phải là chuỗi 64 ký tự hex hợp lệ, nhận: '{sha}'"
        )

    model_src = model["source"]
    if not isinstance(model_src, str) or not re.fullmatch(r"^[^/].*\.xml$", model_src):
        raise EpisodeInvalid(
            f"Trường 'model.source' phải là đường dẫn tương đối kết thúc bằng .xml, "
            f"nhận: '{model_src}'"
        )

    nq = model["nq"]
    if isinstance(nq, bool) or not isinstance(nq, int) or nq < 1:
        raise EpisodeInvalid(f"Trường 'model.nq' phải là số nguyên >= 1, nhận: {nq}")

    nv = model["nv"]
    if isinstance(nv, bool) or not isinstance(nv, int) or nv < 1:
        raise EpisodeInvalid(f"Trường 'model.nv' phải là số nguyên >= 1, nhận: {nv}")

    # Luật R5: muscle_names đủ 6 tên khác nhau, không có chuỗi rỗng sau khi cắt khoảng trắng
    muscle_names = model["muscle_names"]
    if not isinstance(muscle_names, list) or len(muscle_names) != 6:
        m_len = len(muscle_names) if isinstance(muscle_names, list) else type(muscle_names).__name__
        raise EpisodeInvalid(
            f"Luật R5 vi phạm: 'model.muscle_names' phải chứa đúng 6 tên cơ, nhận: {m_len}"
        )
    for idx, name in enumerate(muscle_names):
        if not isinstance(name, str) or not name.strip():
            raise EpisodeInvalid(
                f"Luật R5 vi phạm: tên cơ tại chỉ số {idx} rỗng hoặc chỉ có khoảng trắng: '{name}'"
            )
    if len(set(muscle_names)) != 6:
        raise EpisodeInvalid(
            f"Luật R5 vi phạm: danh sách 'model.muscle_names' chứa tên cơ trùng lặp: {muscle_names}"
        )

    # 3. Kiểm tra phần target
    target = data["target"]
    if not isinstance(target, dict):
        raise EpisodeInvalid(f"Trường 'target' phải là một dict, nhận: {type(target).__name__}")
    for k in ["position_m", "split", "index", "tolerance_m"]:
        if k not in target:
            raise EpisodeInvalid(f"Thiếu trường bắt buộc trong 'target': '{k}'")
    pos_m = target["position_m"]
    if not isinstance(pos_m, (list, tuple)) or len(pos_m) != 3:
        raise EpisodeInvalid(
            "Trường 'target.position_m' phải là danh sách gồm đúng 3 toạ độ [x, y, z]"
        )
    for val in pos_m:
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise EpisodeInvalid(f"Toạ độ trong 'target.position_m' phải là số thực, nhận: {val}")

    # 4. Kiểm tra phần source (hồ sơ checkpoint)
    source = data["source"]
    if source is not None:
        if not isinstance(source, dict):
            raise EpisodeInvalid(
                f"Trường 'source' phải là dict hoặc null, nhận: {type(source).__name__}"
            )
        for k in ["checkpoint_path", "checkpoint_sha256", "run_id", "update_idx"]:
            if k not in source:
                raise EpisodeInvalid(f"Thiếu trường bắt buộc trong 'source': '{k}'")
        ckpt_path = source["checkpoint_path"]
        if not isinstance(ckpt_path, str) or not re.fullmatch(r"^[^/].*", ckpt_path):
            raise EpisodeInvalid(
                f"Trường 'source.checkpoint_path' phải là đường dẫn tương đối, nhận: '{ckpt_path}'"
            )
        ckpt_sha = source["checkpoint_sha256"]
        if not isinstance(ckpt_sha, str) or not re.fullmatch(r"^[0-9a-f]{64}$", ckpt_sha):
            raise EpisodeInvalid(
                f"Trường 'source.checkpoint_sha256' phải là chuỗi 64 ký tự hex, nhận: '{ckpt_sha}'"
            )

    # 5. Kiểm tra library_versions
    lib_ver = data["library_versions"]
    if not isinstance(lib_ver, dict):
        raise EpisodeInvalid(
            f"Trường 'library_versions' phải là dict, nhận: {type(lib_ver).__name__}"
        )
    for req_lib in ["mujoco", "numpy"]:
        if req_lib not in lib_ver or not isinstance(lib_ver[req_lib], str):
            raise EpisodeInvalid(f"Thiếu thông tin phiên bản thư viện bắt buộc: '{req_lib}'")

    # 6. Kiểm tra timing
    timing = data["timing"]
    if not isinstance(timing, dict):
        raise EpisodeInvalid(f"Trường 'timing' phải là dict, nhận: {type(timing).__name__}")
    for k in ["action_dt_s", "physics_timestep_s"]:
        if k not in timing:
            raise EpisodeInvalid(f"Thiếu trường bắt buộc trong 'timing': '{k}'")
    action_dt_s = timing["action_dt_s"]
    if (
        isinstance(action_dt_s, bool)
        or not isinstance(action_dt_s, (int, float))
        or action_dt_s <= 0
    ):
        raise EpisodeInvalid(
            f"Trường 'timing.action_dt_s' phải là số thực > 0, nhận: {action_dt_s}"
        )

    physics_timestep_s = timing["physics_timestep_s"]
    if (
        isinstance(physics_timestep_s, bool)
        or not isinstance(physics_timestep_s, (int, float))
        or physics_timestep_s <= 0
    ):
        raise EpisodeInvalid(
            f"Trường 'timing.physics_timestep_s' phải là số thực > 0, nhận: {physics_timestep_s}"
        )

    # 7. Kiểm tra frames
    frames = data["frames"]
    if not isinstance(frames, list) or len(frames) < 1:
        raise EpisodeInvalid("Trường 'frames' phải là danh sách chứa ít nhất 1 khung hình (frame)")

    # 8. Kiểm tra outcome và luật R1, R6
    outcome = data["outcome"]
    if not isinstance(outcome, dict):
        raise EpisodeInvalid(f"Trường 'outcome' phải là dict, nhận: {type(outcome).__name__}")
    for k in ["terminated", "truncated", "end_reason", "reached", "n_actions", "final_distance_m"]:
        if k not in outcome:
            raise EpisodeInvalid(f"Thiếu trường bắt buộc trong 'outcome': '{k}'")

    term = outcome["terminated"]
    trunc = outcome["truncated"]
    reason = outcome["end_reason"]
    reached = outcome["reached"]
    n_actions = outcome["n_actions"]

    if not isinstance(term, bool):
        raise EpisodeInvalid(
            f"Trường 'outcome.terminated' phải là bool, nhận: {type(term).__name__}"
        )
    if not isinstance(trunc, bool):
        raise EpisodeInvalid(
            f"Trường 'outcome.truncated' phải là bool, nhận: {type(trunc).__name__}"
        )
    if not isinstance(reached, bool):
        raise EpisodeInvalid(
            f"Trường 'outcome.reached' phải là bool, nhận: {type(reached).__name__}"
        )
    if isinstance(n_actions, bool) or not isinstance(n_actions, int) or n_actions < 0:
        raise EpisodeInvalid(
            f"Trường 'outcome.n_actions' phải là số nguyên không âm, nhận: {n_actions}"
        )

    # Luật R1: outcome.n_actions = len(frames) - 1
    expected_n_actions = len(frames) - 1
    if n_actions != expected_n_actions:
        raise EpisodeInvalid(
            f"Luật R1 vi phạm: outcome.n_actions={n_actions} không khớp với số khung "
            f"({len(frames)} khung -> kỳ vọng {expected_n_actions})"
        )

    # Luật R6: reached / max_actions nhất quán
    if reason == "reached":
        if not reached or not term:
            raise EpisodeInvalid(
                f"Luật R6 vi phạm: outcome.end_reason='reached' nhưng reached={reached}, "
                f"terminated={term} (yêu cầu cả hai là True)"
            )
    if reached:
        if reason != "reached" or not term:
            raise EpisodeInvalid(
                f"Luật R6 vi phạm: outcome.reached=True nhưng end_reason='{reason}', "
                f"terminated={term} (yêu cầu end_reason='reached' và terminated=True)"
            )
    if reason == "max_actions":
        if not trunc:
            raise EpisodeInvalid(
                f"Luật R6 vi phạm: outcome.end_reason='max_actions' nhưng truncated={trunc} "
                f"(yêu cầu True)"
            )
    if trunc:
        if reason != "max_actions":
            raise EpisodeInvalid(
                f"Luật R6 vi phạm: outcome.truncated=True nhưng end_reason='{reason}' "
                f"(yêu cầu 'max_actions')"
            )

    # 9. Kiểm tra chi tiết từng khung hình (R2, R3, R4)
    req_frame_keys = [
        "t_s",
        "qpos",
        "qvel",
        "activation",
        "excitation",
        "fingertip_position_m",
        "distance_m",
        "reward",
    ]

    for idx, f in enumerate(frames):
        if not isinstance(f, dict):
            raise EpisodeInvalid(f"Khung {idx} phải là dict, nhận: {type(f).__name__}")
        for k in req_frame_keys:
            if k not in f:
                raise EpisodeInvalid(f"Khung {idx} thiếu trường bắt buộc: '{k}'")

        t_s = f["t_s"]
        if isinstance(t_s, bool) or not isinstance(t_s, (int, float)) or t_s < 0:
            raise EpisodeInvalid(
                f"Thời gian 't_s' tại khung {idx} phải là số thực >= 0, nhận: {t_s}"
            )

        # Luật R2: frames[0].t_s = 0; frames[k].t_s không giảm; hiệu hai khung liền kề ≈ action_dt_s
        if idx == 0:
            if abs(t_s - 0.0) > 1e-9:
                raise EpisodeInvalid(
                    f"Luật R2 vi phạm: khung 0 phải bắt đầu tại thời điểm t_s = 0.0 s, nhận: {t_s}"
                )
        else:
            prev_t_s = frames[idx - 1]["t_s"]
            if t_s < prev_t_s:
                raise EpisodeInvalid(
                    f"Luật R2 vi phạm: thời gian t_s giảm tại khung {idx} ({t_s} < {prev_t_s})"
                )
            dt = t_s - prev_t_s
            if abs(dt - action_dt_s) > 1e-6:
                raise EpisodeInvalid(
                    f"Luật R2 vi phạm: bước thời gian giữa khung {idx - 1} và {idx} là {dt} s, "
                    f"lệch quá dung sai 1e-6 s so với action_dt_s={action_dt_s} s"
                )

        # Luật R3: len(qpos) = model.nq, len(qvel) = model.nv
        qpos = f["qpos"]
        if not isinstance(qpos, (list, tuple)) or len(qpos) != nq:
            act_nq = len(qpos) if isinstance(qpos, (list, tuple)) else 0
            raise EpisodeInvalid(
                f"Luật R3 vi phạm: độ dài qpos tại khung {idx} là {act_nq}, không khớp nq={nq}"
            )
        qvel = f["qvel"]
        if not isinstance(qvel, (list, tuple)) or len(qvel) != nv:
            act_nv = len(qvel) if isinstance(qvel, (list, tuple)) else 0
            raise EpisodeInvalid(
                f"Luật R3 vi phạm: độ dài qvel tại khung {idx} là {act_nv}, không khớp nv={nv}"
            )

        # Luật R4: frames[0].excitation = null và frames[k>=1].excitation != null
        exc = f["excitation"]
        if idx == 0:
            if exc is not None:
                raise EpisodeInvalid(
                    f"Luật R4 vi phạm: khung 0 (sau reset) phải có excitation = null, nhận: {exc}"
                )
        else:
            if exc is None:
                raise EpisodeInvalid(
                    f"Luật R4 vi phạm: khung {idx} (sau hành động) phải có excitation khác null"
                )
            if not isinstance(exc, (list, tuple)) or len(exc) != 6:
                raise EpisodeInvalid(
                    f"Trường 'excitation' tại khung {idx} phải là danh sách đúng 6 phần tử, "
                    f"nhận: {exc}"
                )
            for m_idx, u_val in enumerate(exc):
                if (
                    isinstance(u_val, bool)
                    or not isinstance(u_val, (int, float))
                    or u_val < 0.0
                    or u_val > 1.0
                ):
                    raise EpisodeInvalid(
                        f"Giá trị excitation[{m_idx}] tại khung {idx} ngoài [0, 1]: {u_val}"
                    )

        # Kiểm tra activation
        act = f["activation"]
        if not isinstance(act, (list, tuple)) or len(act) != 6:
            raise EpisodeInvalid(
                f"Trường 'activation' tại khung {idx} phải là danh sách đúng 6 phần tử, nhận: {act}"
            )
        for m_idx, a_val in enumerate(act):
            if (
                isinstance(a_val, bool)
                or not isinstance(a_val, (int, float))
                or a_val < 0.0
                or a_val > 1.0
            ):
                raise EpisodeInvalid(
                    f"Giá trị activation[{m_idx}] tại khung {idx} nằm ngoài khoảng [0, 1]: {a_val}"
                )

        # Kiểm tra fingertip_position_m
        fingertip = f["fingertip_position_m"]
        if not isinstance(fingertip, (list, tuple)) or len(fingertip) != 3:
            raise EpisodeInvalid(
                f"Trường 'fingertip_position_m' tại khung {idx} phải gồm 3 toạ độ [x, y, z]"
            )

        # Kiểm tra distance_m
        dist_m = f["distance_m"]
        if isinstance(dist_m, bool) or not isinstance(dist_m, (int, float)) or dist_m < 0:
            raise EpisodeInvalid(
                f"Khoảng cách 'distance_m' tại khung {idx} phải là số thực >= 0, nhận: {dist_m}"
            )


def _reject_constant(val: str) -> None:
    """Từ chối giá trị số đặc biệt trong bộ phân tích cú pháp JSON (R7)."""
    raise EpisodeInvalid(f"Luật R7 vi phạm: tệp JSON chứa giá trị số không hợp lệ: '{val}'")


def read_episode(path: str | Path) -> Episode:
    """Đọc tệp episode JSON, kiểm tra hợp lệ và trả về đối tượng Episode (API-VIS-0002, FR-009).

    Ném EpisodeNotFound nếu tệp không tồn tại (mã thoát 5).
    Ném EpisodeInvalid nếu dữ liệu hỏng, sai lược đồ hoặc vi phạm các luật R1–R7 (mã thoát 5).
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise EpisodeNotFound(f"Không tìm thấy tệp episode đã lưu tại đường dẫn: {file_path}")

    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except Exception as err:
        raise EpisodeInvalid(f"Không thể đọc tệp episode tại '{file_path}': {err}") from err

    try:
        data = json.loads(raw_text, parse_constant=_reject_constant)
    except EpisodeInvalid:
        raise
    except Exception as err:
        raise EpisodeInvalid(
            f"Cú pháp JSON trong tệp episode '{file_path}' không hợp lệ: {err}"
        ) from err

    validate_episode_dict(data)
    return Episode.from_dict(data)


def write_episode(episode: Episode | dict[str, Any], path: str | Path) -> Path:
    """Ghi nguyên tử bản ghi episode ra tệp JSON và từ chối ghi đè (API-VIS-0003, FR-008).

    - Từ chối ghi đè nếu tệp đích đã tồn tại (INV-005) -> ném EpisodeWriteError (mã thoát 8).
    - Tạo tệp tạm thời .tmp và ghi dữ liệu ra đĩa với allow_nan=False (R7).
    - Hoán đổi nguyên tử (atomic replace) sang tệp đích.
    - Dọn sạch tệp tạm thời nếu gặp bất kỳ lỗi hoặc ngắt nào (INV-004).
    """
    dest_path = Path(path)
    if dest_path.exists():
        raise EpisodeWriteError(f"Tệp đích đã tồn tại, từ chối ghi đè: {dest_path}")

    if hasattr(episode, "to_dict"):
        raw_dict = episode.to_dict()
    elif isinstance(episode, dict):
        raw_dict = copy.deepcopy(episode)
    else:
        raise EpisodeWriteError(
            f"Tham số episode không hợp lệ, nhận kiểu: {type(episode).__name__}"
        )

    # Xác thực tính hợp lệ của dữ liệu trước khi ghi
    try:
        validate_episode_dict(raw_dict)
    except EpisodeInvalid as err:
        raise EpisodeWriteError(f"Không thể ghi episode do dữ liệu không hợp lệ: {err}") from err

    parent_dir = dest_path.parent
    try:
        parent_dir.mkdir(parents=True, exist_ok=True)
    except Exception as err:
        raise EpisodeWriteError(
            f"Không thể tạo thư mục cha '{parent_dir}' để ghi tệp: {err}"
        ) from err

    temp_path = parent_dir / f"{dest_path.name}.tmp.{os.getpid()}_{uuid.uuid4().hex[:8]}"

    try:
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(raw_dict, f, allow_nan=False, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, dest_path)
        return dest_path
    except BaseException as err:
        # Dọn dẹp tệp tạm trong mọi trường hợp lỗi hoặc ngắt quãng
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        if isinstance(err, (KeyboardInterrupt, SystemExit)):
            raise
        raise EpisodeWriteError(f"Gặp sự cố khi ghi tệp episode tại '{dest_path}': {err}") from err


__all__: list[str] = [
    "Episode",
    "Frame",
    "ModelRecord",
    "OutcomeRecord",
    "SourceRecord",
    "TargetRecord",
    "TimingRecord",
    "read_episode",
    "validate_episode_dict",
    "write_episode",
]
