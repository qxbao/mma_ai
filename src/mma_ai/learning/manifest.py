"""Hồ sơ thí nghiệm (run manifest) cho pipeline huấn luyện tăng cường (reinforcement learning).

Định nghĩa cấu trúc hồ sơ, hàm dựng thuần túy (pure builder) và ghi nguyên tử (atomic write)
đáp ứng các yêu cầu FR-011...FR-014, NFR-RES-001, NFR-REL-001 và các bất biến INV-001, INV-004.
"""

from __future__ import annotations

import importlib.metadata
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

from mma_ai.learning.errors import NonFiniteError, RunDirError

# Mẫu regex định danh lượt chạy (run id) theo schema
RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z_[a-z]+_s[0-9]+(-[0-9]+)?$")

# Danh sách 7 thư viện bắt buộc trong hồ sơ (FR-011)
REQUIRED_LIBRARIES: tuple[str, ...] = (
    "python",
    "torch",
    "numpy",
    "gymnasium",
    "mujoco",
    "myo-sim",
    "tensorboard",
)

# Danh sách 6 cơ bắp chuẩn của mô hình khuỷu tay
DEFAULT_MUSCLE_NAMES: tuple[str, ...] = (
    "TRIlong",
    "TRIlat",
    "TRImed",
    "BIClong",
    "BICshort",
    "BRA",
)


def _scan_finite(obj: Any, path: str = "manifest") -> None:
    """Quét đệ quy phát hiện tính hữu hạn (finite), từ chối NaN và Inf (FR-017, NFR-REL-001)."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise NonFiniteError(f"Phát hiện giá trị không hữu hạn ({obj}) tại '{path}'.")
    elif isinstance(obj, (int, str, bool)) or obj is None:
        return
    elif isinstance(obj, Mapping):
        for k, v in obj.items():
            _scan_finite(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _scan_finite(v, f"{path}[{i}]")
    else:
        # Kiểm tra qua duck typing cho mảng số học numpy hoặc tensor nếu có
        if hasattr(obj, "item") and callable(obj.item):
            try:
                val = float(obj.item())
                if math.isnan(val) or math.isinf(val):
                    raise NonFiniteError(f"Phát hiện giá trị không hữu hạn ({val}) tại '{path}'.")
            except (ValueError, TypeError):
                pass


def get_library_versions(custom: Mapping[str, str] | None = None) -> dict[str, str]:
    """Thu thập phiên bản các thư viện bắt buộc (library versions) của môi trường thực thi."""
    versions: dict[str, str] = {
        "python": sys.version.split()[0],
    }

    for pkg in ("torch", "numpy", "gymnasium", "mujoco", "myo-sim", "tensorboard"):
        if custom and pkg in custom:
            versions[pkg] = str(custom[pkg])
            continue
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except Exception:
            # Dự phòng tra cứu qua thuộc tính __version__ của module
            try:
                mod = sys.modules.get(pkg)
                if mod is not None and hasattr(mod, "__version__"):
                    versions[pkg] = str(mod.__version__)
                else:
                    versions[pkg] = "unknown"
            except Exception:
                versions[pkg] = "unknown"

    if custom:
        for k, v in custom.items():
            versions[k] = str(v)

    return versions


def _default_model_record() -> dict[str, Any]:
    """Hồ sơ mô hình mặc định cho khớp khuỷu tay 1 bậc tự do."""
    return {
        "sha256": "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f",
        "source": "myo_sim/models/legacy/elbow/myoelbow_1dof6muscles.xml",
        "muscle_names": list(DEFAULT_MUSCLE_NAMES),
    }


def build_manifest(
    run_id: str | Any | None = None,
    config: Any = None,
    seed: int | None = None,
    *,
    stage: str = "elbow",
    status: str = "running",
    resumed_from: dict[str, Any] | None = None,
    started_utc: str | None = None,
    finished_utc: str | None = None,
    model: dict[str, Any] | None = None,
    device: dict[str, Any] | None = None,
    checkpoints: Sequence[Any] | None = None,
    reward_metrics: dict[str, Any] | None = None,
    throughput: Any = None,
    resources: dict[str, Any] | None = None,
    numeric_health: dict[str, int] | None = None,
    reproducibility: dict[str, Any] | None = None,
    ui: dict[str, Any] | None = None,
    error: dict[str, Any] | Exception | None = None,
    library_versions: dict[str, str] | None = None,
    env: Any = None,
    base_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dựng đối tượng hồ sơ thí nghiệm (run manifest) hợp chuẩn JSON schema.

    Áp dụng kiến trúc functional core thuần túy, thẩm định dữ liệu đầu vào và từ chối NaN/Inf.
    """
    base = dict(base_manifest) if base_manifest is not None else {}

    # 1. Trích xuất run_id
    resolved_run_id = str(getattr(run_id, "run_id", run_id) or base.get("run_id") or "")
    if not resolved_run_id:
        raise ValueError("run_id không được để trống khi khởi tạo hồ sơ run.")

    # 2. Trích xuất config
    resolved_cfg = config if config is not None else base.get("config")
    if resolved_cfg is None:
        raise ValueError("config không được để trống khi khởi tạo hồ sơ run.")
    if hasattr(resolved_cfg, "to_dict") and callable(resolved_cfg.to_dict):
        cfg_dict = dict(resolved_cfg.to_dict())
    elif isinstance(resolved_cfg, Mapping):
        cfg_dict = dict(resolved_cfg)
    elif hasattr(resolved_cfg, "__dataclass_fields__"):
        import dataclasses

        cfg_dict = dataclasses.asdict(resolved_cfg)
    else:
        cfg_dict = dict(resolved_cfg)

    # 3. Trích xuất seed
    if seed is not None:
        resolved_seed = int(seed)
    elif "seed" in base:
        resolved_seed = int(base["seed"])
    elif "seed" in cfg_dict:
        resolved_seed = int(cfg_dict["seed"])
    elif hasattr(config, "seed"):
        resolved_seed = int(getattr(config, "seed"))
    else:
        resolved_seed = 0

    # 4. Trích xuất resumed_from
    resolved_resumed = resumed_from if resumed_from is not None else base.get("resumed_from")
    if resolved_resumed is not None:
        resumed_dict = {
            "run_id": str(resolved_resumed["run_id"]),
            "checkpoint": str(resolved_resumed["checkpoint"]).lstrip("/"),
            "checkpoint_sha256": str(resolved_resumed["checkpoint_sha256"]),
        }
    else:
        resumed_dict = None

    # 5. Mốc thời gian started_utc và finished_utc
    resolved_started = started_utc or base.get("started_utc")
    if not resolved_started:
        resolved_started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if status == "running":
        resolved_finished = None
    else:
        if finished_utc is not None:
            resolved_finished = finished_utc
        elif base.get("finished_utc") is not None:
            resolved_finished = base["finished_utc"]
        else:
            resolved_finished = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 6. Phiên bản thư viện (library_versions)
    custom_libs = library_versions or base.get("library_versions")
    resolved_libs = get_library_versions(custom_libs)

    # 7. Thông tin mô hình (model)
    if model is not None:
        resolved_model = {
            "sha256": str(model["sha256"]),
            "source": str(model["source"]).lstrip("/"),
            "muscle_names": list(model["muscle_names"]),
        }
    elif env is not None and hasattr(env, "model_record"):
        rec = env.model_record()
        resolved_model = {
            "sha256": str(rec["sha256"]),
            "source": str(rec["source"]).lstrip("/"),
            "muscle_names": list(rec["muscle_names"]),
        }
    elif "model" in base:
        resolved_model = dict(base["model"])
    else:
        resolved_model = _default_model_record()

    # 8. Thiết bị (device)
    if device is not None:
        resolved_device = {
            "kind": str(device["kind"]),
            "name": device.get("name"),
        }
    elif "device" in base:
        resolved_device = dict(base["device"])
    else:
        from mma_ai.learning.resources import detect_device

        detected = detect_device()
        resolved_device = {
            "kind": str(detected["kind"]),
            "name": detected.get("name"),
        }

    # 9. Danh sách điểm kiểm tra (checkpoints)
    raw_checkpoints = checkpoints if checkpoints is not None else base.get("checkpoints", [])
    resolved_checkpoints: list[dict[str, Any]] = []
    for ckpt in raw_checkpoints:
        if hasattr(ckpt, "to_dict") and callable(ckpt.to_dict):
            c_dict = dict(ckpt.to_dict())
        elif isinstance(ckpt, Mapping):
            c_dict = dict(ckpt)
        else:
            c_dict = dict(ckpt)
        if "path" in c_dict:
            c_dict["path"] = str(c_dict["path"]).lstrip("/")
        resolved_checkpoints.append(c_dict)

    # 10. Khả năng tái lập (reproducibility)
    repro_cfg: Mapping[str, Any] = {}
    if reproducibility is not None:
        repro_cfg = reproducibility
    elif "reproducibility" in base:
        repro_cfg = base["reproducibility"]
    elif "reproducibility" in cfg_dict and isinstance(cfg_dict["reproducibility"], Mapping):
        repro_cfg = cfg_dict["reproducibility"]
    elif hasattr(config, "reproducibility"):
        r_attr = getattr(config, "reproducibility")
        if hasattr(r_attr, "__dict__"):
            repro_cfg = r_attr.__dict__
        elif isinstance(r_attr, Mapping):
            repro_cfg = r_attr

    resolved_repro: dict[str, Any] = {
        "rel_tolerance": float(repro_cfg.get("rel_tolerance", 1e-6)),
        "head_updates": int(repro_cfg.get("head_updates", 10)),
        "device_kind": str(repro_cfg.get("device_kind", resolved_device["kind"])),
        "torch_threads": int(repro_cfg.get("torch_threads", 1)),
        "deterministic_algorithms": bool(repro_cfg.get("deterministic_algorithms", True)),
    }

    # 11. Chỉ số phần thưởng (reward_metrics)
    raw_reward = reward_metrics if reward_metrics is not None else base.get("reward_metrics")
    if raw_reward is not None:
        n_updates = int(raw_reward.get("n_updates", 0))
        n_episodes = int(raw_reward.get("n_episodes", 0))
        configured_head = int(resolved_repro["head_updates"])
        k = min(configured_head, n_updates)

        input_head_returns = list(raw_reward.get("head_mean_return", []))
        head_returns = [float(x) for x in input_head_returns[:k]]

        first_return = raw_reward.get("first_mean_return")
        if first_return is None and head_returns:
            first_return = head_returns[0]
        elif first_return is not None:
            first_return = float(first_return)

        last_return = raw_reward.get("last_mean_return")
        if last_return is None and head_returns:
            last_return = head_returns[-1]
        elif last_return is not None:
            last_return = float(last_return)

        succ_rate = raw_reward.get("success_rate")
        if succ_rate is not None:
            succ_rate = float(succ_rate)

        resolved_reward = {
            "n_updates": n_updates,
            "n_episodes": n_episodes,
            "head_updates": k,
            "head_mean_return": head_returns,
            "first_mean_return": first_return,
            "last_mean_return": last_return,
            "success_rate": succ_rate,
        }
    else:
        resolved_reward = {
            "n_updates": 0,
            "n_episodes": 0,
            "head_updates": 0,
            "head_mean_return": [],
            "first_mean_return": None,
            "last_mean_return": None,
            "success_rate": None,
        }

    # 12. Thông lượng (throughput)
    raw_tp = throughput if throughput is not None else base.get("throughput")
    if raw_tp is not None:
        if isinstance(raw_tp, Mapping):
            env_steps = int(raw_tp.get("env_steps", 0))
            steps_per_sec = raw_tp.get("env_steps_per_second")
            wall_clock = raw_tp.get("wall_clock_seconds")
        else:
            env_steps = int(getattr(raw_tp, "env_steps", 0))
            steps_per_sec = getattr(raw_tp, "env_steps_per_second", None)
            wall_clock = getattr(raw_tp, "wall_clock_seconds", None)

        resolved_tp = {
            "env_steps": env_steps,
            "env_steps_per_second": float(steps_per_sec) if steps_per_sec is not None else None,
            "wall_clock_seconds": float(wall_clock) if wall_clock is not None else None,
        }
    else:
        resolved_tp = {
            "env_steps": 0,
            "env_steps_per_second": None,
            "wall_clock_seconds": None,
        }

    # 13. Tài nguyên (resources)
    raw_res = resources if resources is not None else base.get("resources")
    if raw_res is not None:
        cpu_util = raw_res.get("cpu_utilization_pct")
        ram_peak = raw_res.get("ram_peak_mb")
        gpu_util = raw_res.get("gpu_utilization_pct")
        vram_peak = raw_res.get("vram_peak_mb")
        resolved_res = {
            "cpu_model": raw_res.get("cpu_model"),
            "cpu_logical_cores": int(raw_res.get("cpu_logical_cores", os.cpu_count() or 1)),
            "cpu_utilization_pct": float(cpu_util) if cpu_util is not None else None,
            "ram_peak_mb": float(ram_peak) if ram_peak is not None else None,
            "gpu_name": raw_res.get("gpu_name"),
            "gpu_utilization_pct": float(gpu_util) if gpu_util is not None else None,
            "vram_peak_mb": float(vram_peak) if vram_peak is not None else None,
        }
    else:
        from mma_ai.learning.resources import collect_resources

        collected = collect_resources()
        resolved_res = {
            "cpu_model": collected.get("cpu_model"),
            "cpu_logical_cores": int(collected.get("cpu_logical_cores", 1)),
            "cpu_utilization_pct": collected.get("cpu_utilization_pct"),
            "ram_peak_mb": collected.get("ram_peak_mb"),
            "gpu_name": collected.get("gpu_name"),
            "gpu_utilization_pct": collected.get("gpu_utilization_pct"),
            "vram_peak_mb": collected.get("vram_peak_mb"),
        }

    # 14. Sức khoẻ số học (numeric_health)
    raw_nh = numeric_health if numeric_health is not None else base.get("numeric_health")
    if raw_nh is not None:
        resolved_nh = {
            "nan_count": int(raw_nh.get("nan_count", 0)),
            "inf_count": int(raw_nh.get("inf_count", 0)),
        }
    else:
        resolved_nh = {
            "nan_count": 0,
            "inf_count": 0,
        }

    # 15. Giao diện (ui)
    raw_ui = ui if ui is not None else base.get("ui")
    if raw_ui is not None:
        resolved_ui = {
            "mode": str(raw_ui.get("mode", "none")),
            "url": raw_ui.get("url"),
            "view3d": bool(raw_ui.get("view3d", False)),
        }
    elif "ui" in cfg_dict and isinstance(cfg_dict["ui"], Mapping):
        resolved_ui = {
            "mode": str(cfg_dict["ui"].get("mode", "none")),
            "url": cfg_dict["ui"].get("url"),
            "view3d": bool(cfg_dict["ui"].get("view3d", False)),
        }
    else:
        resolved_ui = {
            "mode": "none",
            "url": None,
            "view3d": False,
        }

    # 16. Lỗi (error)
    raw_err = error if error is not None else base.get("error")
    if status == "error":
        if isinstance(raw_err, Exception):
            err_kind = "other"
            err_name = type(raw_err).__name__
            if err_name == "NonFiniteError":
                err_kind = "non_finite"
            elif err_name == "PhysicsInstabilityError":
                err_kind = "env_instability"
            elif err_name in ("CheckpointIOError", "CheckpointError"):
                err_kind = "checkpoint_io"
            resolved_err = {
                "kind": err_kind,
                "message": str(raw_err) or "Đã xảy ra lỗi trong quá trình huấn luyện",
                "update_idx": getattr(raw_err, "update_idx", None),
            }
        elif isinstance(raw_err, Mapping):
            resolved_err = {
                "kind": str(raw_err["kind"]),
                "message": str(raw_err["message"]),
                "update_idx": raw_err.get("update_idx"),
            }
        else:
            resolved_err = {
                "kind": "other",
                "message": "Đã xảy ra lỗi không xác định",
                "update_idx": None,
            }
    else:
        resolved_err = None

    manifest_payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "run_id": resolved_run_id,
        "stage": stage,
        "status": status,
        "seed": resolved_seed,
        "resumed_from": resumed_dict,
        "started_utc": resolved_started,
        "finished_utc": resolved_finished,
        "config": cfg_dict,
        "library_versions": resolved_libs,
        "model": resolved_model,
        "device": resolved_device,
        "checkpoints": resolved_checkpoints,
        "reward_metrics": resolved_reward,
        "throughput": resolved_tp,
        "resources": resolved_res,
        "numeric_health": resolved_nh,
        "reproducibility": resolved_repro,
        "ui": resolved_ui,
        "error": resolved_err,
    }

    # Quét tính hữu hạn (finite) trước khi trả về
    _scan_finite(manifest_payload)

    return manifest_payload


def write_manifest(run_dir: str | Path | Any, manifest: dict[str, Any]) -> Path:
    """Ghi hồ sơ thí nghiệm manifest.json theo cơ chế nguyên tử (atomic write).

    Bảo vệ bất biến INV-001: không bao giờ ghi đè hoặc sửa đổi hồ sơ của lần chạy đã hoàn tất.
    Từ chối các giá trị không hữu hạn (NaN hoặc Inf).
    """
    # BƯỚC 1: Quét tính hữu hạn của toàn bộ dữ liệu trước khi đụng vào đĩa
    _scan_finite(manifest)

    run_path = getattr(run_dir, "path", None)
    if run_path is None:
        run_path = Path(run_dir)
    else:
        run_path = Path(run_path)

    run_path.mkdir(parents=True, exist_ok=True)
    target_file = run_path / "manifest.json"
    tmp_file = run_path / "manifest.json.tmp"

    # BƯỚC 2: Kiểm tra bất biến INV-001 bảo vệ thư mục run đã kết thúc
    if target_file.is_file():
        try:
            existing_data = json.loads(target_file.read_text(encoding="utf-8"))
            existing_status = existing_data.get("status")
            if existing_status in ("done", "error", "interrupted"):
                raise RunDirError(
                    f"Không thể ghi đè hoặc sửa đổi hồ sơ của lần chạy đã kết thúc "
                    f"với trạng thái '{existing_status}' (INV-001)."
                )
        except json.JSONDecodeError:
            pass

    # BƯỚC 3: Ghi tệp .tmp, fsync và thay thế nguyên tử (os.replace)
    try:
        with tmp_file.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_file, target_file)
    except Exception:
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except OSError:
                pass
        raise

    return target_file


def read_manifest(run_dir: str | Path | Any) -> dict[str, Any]:
    """Đọc hồ sơ manifest.json từ thư mục run."""
    run_path = getattr(run_dir, "path", None)
    if run_path is None:
        run_path = Path(run_dir)
    else:
        run_path = Path(run_path)

    target_file = run_path / "manifest.json"
    if not target_file.is_file():
        raise FileNotFoundError(f"Không tìm thấy manifest.json tại: {target_file}")

    return cast(dict[str, Any], json.loads(target_file.read_text(encoding="utf-8")))
