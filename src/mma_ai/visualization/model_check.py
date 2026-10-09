"""Mô-đun đối chiếu tính tương thích mô hình vật lý (mma_ai.visualization.model_check).

Cung cấp cấu trúc dữ liệu và hàm nghiệp vụ theo hợp đồng API:
- FR-012: Đối chiếu mô hình (model check) giữa bản ghi episode và môi trường hiện tại.
- INV-001: Ngăn chặn phát lại sai ngầm, dừng lệnh hoặc cảnh báo rõ khi mô hình khác biệt.
- API-VIS-0005: check_model(episode, model_info) -> ModelCheck và enforce(check, allow_mismatch).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any, Mapping

from mma_ai.visualization.errors import ModelMismatch


@dataclass(frozen=True)
class MuscleModelInfo:
    """Thông tin mô hình cơ bắp (muscle model info) hiện tại của môi trường mô phỏng."""

    sha256: str
    muscle_names: list[str]
    nq: int
    nv: int


@dataclass(frozen=True)
class ModelCheck:
    """Kết quả kiểm tra đối chiếu mô hình (model check) giữa episode và môi trường."""

    match: bool
    compatible: bool
    episode_sha256: str
    current_sha256: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Xuất kết quả kiểm tra thành từ điển tương thích lược đồ replay-summary."""
        return {
            "match": self.match,
            "compatible": self.compatible,
            "episode_sha256": self.episode_sha256,
            "current_sha256": self.current_sha256,
            "reasons": list(self.reasons),
        }


def _extract_model_fields(obj: Any) -> tuple[str, int, int, list[str]]:
    """Trích xuất mã băm sha256, nq, nv và tên cơ từ đối tượng hoặc từ điển."""
    if hasattr(obj, "model"):
        obj = getattr(obj, "model")
    elif isinstance(obj, Mapping) and "model" in obj:
        obj = obj["model"]

    if isinstance(obj, Mapping):
        sha256 = str(obj["sha256"])
        nq = int(obj["nq"])
        nv = int(obj["nv"])
        muscle_names = [str(name) for name in obj["muscle_names"]]
        return sha256, nq, nv, muscle_names

    sha256 = str(getattr(obj, "sha256"))
    nq = int(getattr(obj, "nq"))
    nv = int(getattr(obj, "nv"))
    raw_muscles = getattr(obj, "muscle_names")
    muscle_names = [str(name) for name in raw_muscles]
    return sha256, nq, nv, muscle_names


def check_model(episode: Any, model_info: Any) -> ModelCheck:
    """Đối chiếu SHA-256 XML và cấu trúc mô hình (API-VIS-0005, FR-012)."""
    ep_sha256, ep_nq, ep_nv, ep_muscles = _extract_model_fields(episode)
    curr_sha256, curr_nq, curr_nv, curr_muscles = _extract_model_fields(model_info)

    reasons: list[str] = []

    sha_matches = ep_sha256 == curr_sha256
    if not sha_matches:
        reasons.append(
            f"Mã băm SHA-256 XML không khớp: episode có '{ep_sha256}', "
            f"mô hình hiện tại có '{curr_sha256}'."
        )

    struct_matches = True
    if ep_nq != curr_nq:
        struct_matches = False
        reasons.append(
            f"Số tọa độ suy rộng nq không khớp: episode có {ep_nq}, mô hình hiện tại có {curr_nq}."
        )

    if ep_nv != curr_nv:
        struct_matches = False
        reasons.append(
            f"Số bậc tự do vận tốc nv không khớp: episode có {ep_nv}, "
            f"mô hình hiện tại có {curr_nv}."
        )

    if len(ep_muscles) != len(curr_muscles):
        struct_matches = False
        reasons.append(
            f"Số lượng cơ không khớp: episode có {len(ep_muscles)}, "
            f"mô hình hiện tại có {len(curr_muscles)}."
        )
    elif ep_muscles != curr_muscles:
        struct_matches = False
        reasons.append(
            f"Thứ tự hoặc danh sách tên cơ không khớp: episode có {ep_muscles}, "
            f"mô hình hiện tại có {curr_muscles}."
        )

    return ModelCheck(
        match=sha_matches,
        compatible=struct_matches,
        episode_sha256=ep_sha256,
        current_sha256=curr_sha256,
        reasons=reasons,
    )


def enforce(check: ModelCheck, allow_mismatch: bool = False) -> None:
    """Thực thi bất biến mô hình, ném lỗi hoặc cảnh báo (INV-001, FR-012, API-VIS-0005)."""
    if not check.compatible:
        detail = "; ".join(check.reasons)
        raise ModelMismatch(
            f"Cấu trúc mô hình không tương thích (incompatible structure): {detail}"
        )

    if not check.match:
        if not allow_mismatch:
            raise ModelMismatch(
                f"Lệch mã băm XML mô hình: episode có '{check.episode_sha256}', "
                f"mô hình hiện tại có '{check.current_sha256}'. "
                "Cần bật cờ cho phép lệch mô hình (--allow-model-mismatch) để tiếp tục."
            )
        warnings.warn(
            f"Cảnh báo: Mô hình lệch (model mismatch)! Mã băm XML của episode "
            f"'{check.episode_sha256}' khác mô hình hiện tại '{check.current_sha256}'. "
            "Đang tiếp tục vì có cờ allow_mismatch.",
            category=UserWarning,
            stacklevel=2,
        )


__all__: list[str] = [
    "ModelCheck",
    "MuscleModelInfo",
    "check_model",
    "enforce",
]
