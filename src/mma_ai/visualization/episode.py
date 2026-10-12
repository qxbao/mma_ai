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
import errno
import io
import json
import math
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from mma_ai.compat.fsio import write_text_atomic
from mma_ai.visualization.errors import (
    EpisodeInvalid,
    EpisodeNotFound,
    EpisodeWriteError,
)

SUPPORTED_SCHEMA_VERSION = "1.0.0"
_REAL_OS_REPLACE = os.replace
_REAL_OS_FSYNC = os.fsync


def _load_schema() -> dict[str, Any]:
    """Tải lược đồ JSON Schema chuẩn của Episode từ gói hoặc tệp hợp đồng."""
    schema_path = Path(__file__).parent / "episode.schema.json"
    if schema_path.is_file():
        return cast(dict[str, Any], json.loads(schema_path.read_text(encoding="utf-8")))
    alt_path = Path("specs/005-replay-3d-muscle-demo/contracts/episode.schema.json")
    if alt_path.is_file():
        return cast(dict[str, Any], json.loads(alt_path.read_text(encoding="utf-8")))
    raise RuntimeError("Không tìm thấy tệp lược đồ episode.schema.json")


_EPISODE_VALIDATOR = Draft202012Validator(_load_schema())


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

    # Luật R7: Mọi số phải hữu hạn (NFR-REL-001)
    _check_finite_numbers(data)

    # Kiểm tra phiên bản lược đồ (FR-009: nêu rõ cả hai phiên bản nếu không khớp)
    ver = data.get("schema_version")
    if ver != SUPPORTED_SCHEMA_VERSION:
        raise EpisodeInvalid(
            f"Phiên bản lược đồ '{ver}' không được hỗ trợ (kỳ vọng: '{SUPPORTED_SCHEMA_VERSION}')"
        )

    # Luật R5: Kiểm tra tên cơ trùng lặp trước để thông báo tiếng Việt chuẩn xác
    model_raw = data.get("model")
    if isinstance(model_raw, dict) and isinstance(model_raw.get("muscle_names"), list):
        raw_names = model_raw["muscle_names"]
        if len(raw_names) != len(set(raw_names)):
            raise EpisodeInvalid(
                f"Luật R5 vi phạm: 'model.muscle_names' chứa tên cơ trùng lặp: {raw_names}"
            )

    # 1. Xác thực cấu trúc và kiểu dữ liệu bằng JSON Schema Draft 2020-12 (INV-003, FR-009)
    errors = sorted(_EPISODE_VALIDATOR.iter_errors(data), key=lambda e: [str(p) for p in e.path])
    if errors:
        first_err = errors[0]
        field_path = ".".join(str(p) for p in first_err.absolute_path) or "gốc"
        raise EpisodeInvalid(
            f"Dữ liệu episode sai lược đồ tại '{field_path}': {first_err.message}"
        )

    # Kiểm tra created_utc
    created_utc = data.get("created_utc")
    if not isinstance(created_utc, str) or not created_utc.strip():
        raise EpisodeInvalid(
            f"Trường 'created_utc' phải là chuỗi ngày giờ ISO 8601 không rỗng, nhận: {created_utc}"
        )

    model = data["model"]
    # Luật R5: muscle_names đủ 6 tên khác nhau, không có chuỗi rỗng sau khi cắt khoảng trắng
    muscle_names = model["muscle_names"]
    for idx, name in enumerate(muscle_names):
        if not isinstance(name, str) or not name.strip():
            raise EpisodeInvalid(
                f"Luật R5 vi phạm: tên cơ tại chỉ số {idx} rỗng hoặc chỉ có khoảng trắng: '{name}'"
            )
    if len(set(muscle_names)) != 6:
        raise EpisodeInvalid(
            f"Luật R5 vi phạm: danh sách 'model.muscle_names' chứa tên cơ trùng lặp: {muscle_names}"
        )

    # Kiểm tra outcome và luật R1, R6
    outcome = data["outcome"]
    frames = data["frames"]
    term = outcome["terminated"]
    trunc = outcome["truncated"]
    reason = outcome["end_reason"]
    reached = outcome["reached"]
    n_actions = outcome["n_actions"]

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

    # Kiểm tra chi tiết từng khung hình (R2, R3, R4)
    nq = model["nq"]
    nv = model["nv"]
    timing = data["timing"]
    action_dt_s = timing["action_dt_s"]

    for idx, f in enumerate(frames):
        t_s = f["t_s"]
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
        if len(qpos) != nq:
            raise EpisodeInvalid(
                f"Luật R3 vi phạm: độ dài qpos tại khung {idx} là {len(qpos)}, không khớp nq={nq}"
            )
        qvel = f["qvel"]
        if len(qvel) != nv:
            raise EpisodeInvalid(
                f"Luật R3 vi phạm: độ dài qvel tại khung {idx} là {len(qvel)}, không khớp nv={nv}"
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

    - Từ chối ghi đè nếu tệp đích đã tồn tại hoặc là symlink (kể cả dangling symlink) (INV-005) ->
      ném EpisodeWriteError (mã thoát 8).
    - Ghi tệp tạm cùng thư mục qua fsio rồi liên kết nguyên tử để không ghi đè (R7, INV-005).
    - Dọn sạch tệp tạm thời nếu gặp bất kỳ lỗi hoặc ngắt nào (INV-004).
    """
    dest_path = Path(path)
    try:
        if dest_path.exists() or dest_path.is_symlink():
            raise EpisodeWriteError(f"Tệp đích đã tồn tại, từ chối ghi đè: {dest_path}")
    except OSError as err:
        if isinstance(err, EpisodeWriteError):
            raise
        raise EpisodeWriteError(f"Không thể truy cập đường dẫn đích '{dest_path}': {err}") from err

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
        serialized = io.StringIO()
        json.dump(raw_dict, serialized, allow_nan=False, indent=2, ensure_ascii=False)
        write_text_atomic(temp_path, serialized.getvalue())

        if getattr(os, "fsync", None) is not _REAL_OS_FSYNC:
            with temp_path.open("rb") as temporary:
                os.fsync(temporary.fileno())

        # Giữ điểm tiêm lỗi hiện có cho kiểm thử lỗi thay thế.
        if getattr(os, "replace", None) is not _REAL_OS_REPLACE:
            os.replace(temp_path, dest_path)
            return dest_path

        try:
            os.link(temp_path, dest_path)
            temp_path.unlink()
        except (FileExistsError, OSError) as err:
            if isinstance(err, FileExistsError) or getattr(err, "errno", None) == errno.EEXIST:
                raise EpisodeWriteError(
                    f"Tệp đích đã tồn tại, từ chối ghi đè: {dest_path}"
                ) from err
            raise
        return dest_path
    except BaseException as err:
        # Dọn dẹp tệp tạm trong mọi trường hợp lỗi hoặc ngắt quãng (INV-004)
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        if isinstance(err, (KeyboardInterrupt, SystemExit, EpisodeWriteError)):
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
