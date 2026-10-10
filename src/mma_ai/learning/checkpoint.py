"""Mô-đun quản lý lưu và nạp điểm kiểm tra (checkpoint) cùng chính sách (policy).

Thực hiện lưu nguyên tử (atomic save), quét tính hữu hạn (finite scan) ngăn chặn NaN/Inf,
và nạp an toàn chỉ chứa trọng số (weights-only load) theo hợp đồng INV-004, FR-006...FR-009.
Chỉ nhập các mô-đun networks và normalizer, không nhập ppo hay trainer.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import sys
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, cast

import numpy as np

if TYPE_CHECKING:
    from torch import Tensor

    from mma_ai.learning.networks import ActorCritic
else:
    Tensor = Any

from mma_ai.learning.errors import CheckpointError, CheckpointIOError, NonFiniteError
from mma_ai.learning.normalizer import RunningNorm
from mma_ai.learning.train_config import TrainConfig

# Danh sách đủ 6 thành phần bắt buộc của một checkpoint hợp lệ (INV-004)
REQUIRED_COMPONENTS: tuple[str, ...] = (
    "actor",
    "critic",
    "obs_normalizer",
    "optimizer",
    "seed",
    "rng_state",
)


@dataclass(frozen=True)
class CheckpointMeta:
    """Siêu dữ liệu (metadata) mô tả một checkpoint theo schema checkpoint-meta."""

    schema_version: str = "1.0.0"
    path: str = ""
    kind: str = "periodic"
    update_idx: int = 0
    env_steps: int = 0
    sha256: str = ""
    created_utc: str = ""
    model_sha256: str = ""
    components: list[str] = field(default_factory=lambda: list(REQUIRED_COMPONENTS))
    library_versions: dict[str, str] = field(default_factory=dict)
    finite: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Xuất đối tượng thành từ điển chuẩn theo schema."""
        return {
            "schema_version": self.schema_version,
            "path": self.path,
            "kind": self.kind,
            "update_idx": self.update_idx,
            "env_steps": self.env_steps,
            "sha256": self.sha256,
            "created_utc": self.created_utc,
            "model_sha256": self.model_sha256,
            "components": list(self.components),
            "library_versions": dict(self.library_versions),
            "finite": self.finite,
        }


@dataclass
class LoadedCheckpoint:
    """Dữ liệu điểm kiểm tra đã nạp vào bộ nhớ."""

    actor_state_dict: dict[str, Tensor]
    critic_state_dict: dict[str, Tensor]
    obs_normalizer_state_dict: dict[str, Any]
    optimizer_state_dict: dict[str, Any]
    seed: int
    rng_state: dict[str, Any]
    update_idx: int
    env_steps: int
    model_sha256: str
    library_versions: dict[str, str]
    config: Any
    log_std: Tensor | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


class Policy:
    """Chính sách (policy) đã nạp, chỉ-đọc (read-only) dành cho suy luận tất định."""

    def __init__(self, model: ActorCritic, normalizer: RunningNorm) -> None:
        self.model = model
        self.normalizer = normalizer
        self.model.eval()

    def act_deterministic(self, obs_raw: np.ndarray | Tensor) -> np.ndarray:
        """Tính toán hành động tất định u in (0, 1)^6 từ quan sát thô (raw observation)."""
        import torch

        if isinstance(obs_raw, torch.Tensor):
            obs_array = obs_raw.detach().cpu().numpy()
        else:
            obs_array = np.asarray(obs_raw, dtype=np.float64)

        is_single = obs_array.ndim == 1
        if is_single:
            obs_array = obs_array.reshape(1, -1)

        norm_obs = self.normalizer(obs_array)
        obs_tensor = torch.as_tensor(norm_obs, dtype=torch.float32)

        with torch.no_grad():
            action, _, _ = self.model.act(obs_tensor, deterministic=True)
            action_np = action.detach().cpu().numpy()

        if is_single:
            return np.asarray(action_np[0], dtype=np.float32)
        return np.asarray(action_np, dtype=np.float32)


def _scan_finite(data: Any, path: str = "checkpoint") -> None:
    """Quét đệ quy phát hiện NaN hoặc vô cực (infinity) trong mọi tensor hoặc mảng số."""
    if "torch" in sys.modules:
        import torch

        if isinstance(data, torch.Tensor):
            if not bool(torch.isfinite(data).all()):
                nan_count = int(torch.isnan(data).sum())
                inf_count = int(torch.isinf(data).sum())
                raise NonFiniteError(
                    f"Phát hiện tensor không hữu hạn tại '{path}': "
                    f"{nan_count} NaN, {inf_count} Inf."
                )
            return

    if isinstance(data, np.ndarray):
        if not bool(np.isfinite(data).all()):
            nan_count = int(np.isnan(data).sum())
            inf_count = int(np.isinf(data).sum())
            raise NonFiniteError(
                f"Phát hiện mảng numpy không hữu hạn tại '{path}': "
                f"{nan_count} NaN, {inf_count} Inf."
            )
    elif isinstance(data, (float, int)):
        if isinstance(data, float) and not math.isfinite(data):
            raise NonFiniteError(f"Phát hiện giá trị thực không hữu hạn tại '{path}': {data}.")
    elif isinstance(data, Mapping):
        for key, value in data.items():
            _scan_finite(value, f"{path}.{key}")
    elif isinstance(data, (list, tuple)):
        for index, item in enumerate(data):
            _scan_finite(item, f"{path}[{index}]")


def _compute_sha256(file_path: Path) -> str:
    """Tính mã băm (hash) SHA-256 của tệp trên đĩa theo khối nhị phân."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def save_checkpoint(
    agent: Any,
    run_dir: str | Path,
    kind: str = "periodic",
    ctx: Any = None,
) -> CheckpointMeta:
    """Lưu điểm kiểm tra an toàn theo cơ chế nguyên tử (atomic) và quét hữu hạn (FR-006, FR-007)."""
    import torch

    if kind not in ("periodic", "final"):
        raise CheckpointError(
            f"Loại checkpoint không hợp lệ: '{kind}', kỳ vọng 'periodic' hoặc 'final'."
        )

    run_path = Path(run_dir)
    checkpoints_dir = run_path / "checkpoints"

    # Trích xuất thông tin lượt cập nhật và số bước từ ngữ cảnh (context)
    update_idx = 0
    env_steps = 0
    model_sha256 = ""
    seed = 0
    cfg = getattr(agent, "cfg", None)

    if isinstance(ctx, Mapping):
        update_idx = int(ctx.get("update_idx", 0))
        env_steps = int(ctx.get("env_steps", 0))
        model_sha256 = str(ctx.get("model_sha256", ""))
        seed = int(ctx.get("seed", getattr(cfg, "seed", 0)))
        if "config" in ctx:
            cfg = ctx["config"]
    elif ctx is not None:
        update_idx = int(getattr(ctx, "update_idx", 0))
        env_steps = int(getattr(ctx, "env_steps", 0))
        model_sha256 = str(getattr(ctx, "model_sha256", ""))
        seed = int(getattr(ctx, "seed", getattr(cfg, "seed", 0)))

    # Trích xuất state_dict của agent qua duck typing
    if hasattr(agent, "state_dict") and callable(agent.state_dict):
        agent_state = agent.state_dict()
        actor_sd = agent_state.get("actor")
        critic_sd = agent_state.get("critic")
        optimizer_sd = agent_state.get("optimizer")
        log_std = agent_state.get("log_std")
    else:
        model = getattr(agent, "model", agent)
        actor_sd = model.actor.state_dict()
        critic_sd = model.critic.state_dict()
        log_std = getattr(model, "log_std", None)
        optimizer_sd = getattr(agent, "optimizer", None)
        if optimizer_sd is not None and hasattr(optimizer_sd, "state_dict"):
            optimizer_sd = optimizer_sd.state_dict()

    if actor_sd is None or critic_sd is None or optimizer_sd is None:
        raise CheckpointError("Không thể trích xuất đầy đủ actor, critic hoặc optimizer từ agent.")

    # Trích xuất bộ chuẩn hoá quan sát (normalizer)
    obs_normalizer = None
    if isinstance(ctx, Mapping) and "obs_normalizer" in ctx:
        obs_normalizer = ctx["obs_normalizer"]
    elif ctx is not None and hasattr(ctx, "obs_normalizer"):
        obs_normalizer = getattr(ctx, "obs_normalizer")
    elif hasattr(agent, "obs_normalizer"):
        obs_normalizer = getattr(agent, "obs_normalizer")

    if obs_normalizer is not None and hasattr(obs_normalizer, "state_dict"):
        norm_sd = obs_normalizer.state_dict()
        # Chuyển mảng NumPy sang Tensor để nạp an toàn với weights_only=True
        norm_dict = {
            "mean": torch.as_tensor(norm_sd["mean"]),
            "var": torch.as_tensor(norm_sd["var"]),
            "count": int(norm_sd["count"]),
        }
    else:
        norm_dict = {
            "mean": torch.empty(0),
            "var": torch.empty(0),
            "count": 0,
        }

    # Thu thập trạng thái sinh số ngẫu nhiên (RNG state) (INV-004, FR-009)
    torch_rng = torch.get_rng_state()
    numpy_state = None
    if isinstance(ctx, Mapping) and "rng_state" in ctx:
        ctx_rng = ctx["rng_state"]
        if isinstance(ctx_rng, Mapping) and "numpy" in ctx_rng:
            numpy_state = ctx_rng["numpy"]
        elif isinstance(ctx_rng, Mapping) and "bit_generator" in ctx_rng:
            numpy_state = ctx_rng
        elif ctx_rng is not None:
            numpy_state = ctx_rng

    if numpy_state is None:
        agent_rng = getattr(agent, "_rng", getattr(agent, "rng", None))
        if agent_rng is not None and hasattr(agent_rng, "bit_generator"):
            numpy_state = copy.deepcopy(agent_rng.bit_generator.state)

    if numpy_state is None:
        numpy_state = np.random.default_rng(seed).bit_generator.state

    rng_state_dict: dict[str, Any] = {
        "torch_cpu": torch_rng,
        "numpy": numpy_state,
    }
    if torch.cuda.is_available():
        rng_state_dict["torch_cuda"] = torch.cuda.get_rng_state()

    if isinstance(ctx, Mapping) and "env_np_random" in ctx:
        rng_state_dict["env_np_random"] = ctx["env_np_random"]
    elif isinstance(ctx, Mapping) and "env" in ctx:
        env_obj = ctx["env"]
        if hasattr(env_obj, "np_random") and hasattr(env_obj.np_random, "bit_generator"):
            rng_state_dict["env_np_random"] = copy.deepcopy(env_obj.np_random.bit_generator.state)

    library_versions = {
        "torch": str(torch.__version__),
        "numpy": str(np.__version__),
    }
    if isinstance(ctx, Mapping) and "library_versions" in ctx:
        library_versions.update(ctx["library_versions"])

    config_payload: Any = None
    if cfg is not None:
        if hasattr(cfg, "to_dict") and callable(cfg.to_dict):
            config_payload = cfg.to_dict()
        elif isinstance(cfg, Mapping):
            config_payload = dict(cfg)
        elif hasattr(cfg, "__dataclass_fields__"):
            import dataclasses

            config_payload = dataclasses.asdict(cfg)
        else:
            config_payload = str(cfg)

    checkpoint_payload: dict[str, Any] = {
        "actor": actor_sd,
        "critic": critic_sd,
        "obs_normalizer": norm_dict,
        "optimizer": optimizer_sd,
        "seed": seed,
        "rng_state": rng_state_dict,
        "update_idx": update_idx,
        "env_steps": env_steps,
        "model_sha256": model_sha256,
        "library_versions": library_versions,
        "config": config_payload,
    }
    if log_std is not None:
        checkpoint_payload["log_std"] = log_std

    # BƯỚC 1: Quét tính hữu hạn mọi tensor trước khi ghi (FR-007)
    _scan_finite(checkpoint_payload)

    # Đặt tên tệp theo chỉ số lượt (update index)
    filename = (
        f"ckpt_u{update_idx:06d}_final.pt" if kind == "final" else f"ckpt_u{update_idx:06d}.pt"
    )
    rel_path = f"checkpoints/{filename}"
    target_pt_path = checkpoints_dir / filename
    tmp_pt_path = checkpoints_dir / f"{filename}.tmp"

    try:
        checkpoints_dir.mkdir(parents=True, exist_ok=True)

        # BƯỚC 2: Ghi tệp .tmp, fsync và thay thế nguyên tử (os.replace)
        with tmp_pt_path.open("wb") as f:
            torch.save(checkpoint_payload, f)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_pt_path, target_pt_path)
    except (OSError, IOError, RuntimeError) as err:
        if tmp_pt_path.exists():
            try:
                tmp_pt_path.unlink()
            except OSError:
                pass
        raise CheckpointIOError(f"Lỗi ghi đĩa khi lưu tệp checkpoint: {err}") from err

    # BƯỚC 3: Tính hash SHA-256 của tệp checkpoint đã ghi
    pt_sha256 = _compute_sha256(target_pt_path)

    # BƯỚC 4: Ghi tệp siêu dữ liệu *.meta.json
    now_utc = datetime.now(timezone.utc).isoformat()
    meta = CheckpointMeta(
        schema_version="1.0.0",
        path=rel_path,
        kind=kind,
        update_idx=update_idx,
        env_steps=env_steps,
        sha256=pt_sha256,
        created_utc=now_utc,
        model_sha256=model_sha256,
        components=list(REQUIRED_COMPONENTS),
        library_versions=library_versions,
        finite=True,
    )

    meta_filename = f"{target_pt_path.stem}.meta.json"
    target_meta_path = checkpoints_dir / meta_filename
    tmp_meta_path = checkpoints_dir / f"{meta_filename}.tmp"

    try:
        with tmp_meta_path.open("w", encoding="utf-8") as f:
            json.dump(meta.to_dict(), f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_meta_path, target_meta_path)
    except (OSError, IOError, RuntimeError) as err:
        if tmp_meta_path.exists():
            try:
                tmp_meta_path.unlink()
            except OSError:
                pass
        raise CheckpointIOError(f"Lỗi ghi đĩa khi lưu siêu dữ liệu checkpoint: {err}") from err

    # BƯỚC 5: Cập nhật con trỏ latest.json bằng thay thế nguyên tử SAU CÙNG
    latest_path = checkpoints_dir / "latest.json"
    tmp_latest_path = checkpoints_dir / "latest.json.tmp"
    latest_payload = meta.to_dict()

    try:
        with tmp_latest_path.open("w", encoding="utf-8") as f:
            json.dump(latest_payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_latest_path, latest_path)
    except (OSError, IOError, RuntimeError) as err:
        if tmp_latest_path.exists():
            try:
                tmp_latest_path.unlink()
            except OSError:
                pass
        raise CheckpointIOError(f"Lỗi ghi đĩa khi cập nhật latest.json: {err}") from err

    return meta


def load_checkpoint(
    path: str | Path,
    for_training: bool = False,
    expected_model_sha256: str | None = None,
    expected_cfg: Any = None,
    expected_obs_dim: int | None = None,
    expected_checkpoint_sha256: str | None = None,
) -> LoadedCheckpoint:
    """Nạp điểm kiểm tra với weights_only=True và kiểm tra tính toàn vẹn (FR-008, FR-009)."""
    import torch

    target_path = Path(path)
    expected_sha256: str | None = expected_checkpoint_sha256

    # Nếu truyền vào là latest.json hoặc file JSON, phân giải đường dẫn tương ứng
    if target_path.name == "latest.json" or target_path.suffix == ".json":
        if not target_path.exists():
            raise CheckpointError(f"Tệp con trỏ '{target_path}' không tồn tại.")
        try:
            info = json.loads(target_path.read_text(encoding="utf-8"))
            if (
                not isinstance(info, Mapping)
                or "path" not in info
                or not isinstance(info["path"], str)
            ):
                raise CheckpointError(
                    f"Tệp con trỏ '{target_path}' không chứa trường 'path' hợp lệ."
                )
            if expected_sha256 is None and "sha256" in info:
                expected_sha256 = str(info["sha256"])
            rel_pt = info["path"]
            # Thư mục gốc run_dir nằm ở cha của checkpoints/
            run_root = target_path.parent.parent
            resolved_pt = run_root / rel_pt
            if not resolved_pt.exists():
                resolved_pt = target_path.parent / Path(rel_pt).name
            target_path = resolved_pt
        except CheckpointError:
            raise
        except Exception as err:
            raise CheckpointError(f"Không thể đọc thông tin từ '{target_path}': {err}") from err
    else:
        # Nếu nạp trực tiếp qua tệp .pt, tìm tệp *.meta.json để đối chiếu sha256
        meta_candidate = target_path.with_name(f"{target_path.stem}.meta.json")
        if meta_candidate.exists() and expected_sha256 is None:
            try:
                meta_info = json.loads(meta_candidate.read_text(encoding="utf-8"))
                if isinstance(meta_info, Mapping) and "sha256" in meta_info:
                    expected_sha256 = str(meta_info["sha256"])
            except Exception:
                pass

    if not target_path.exists():
        raise CheckpointError(f"Tệp checkpoint '{target_path}' không tồn tại.")

    # Đối chiếu mã băm sha256 với siêu dữ liệu nếu có (INV-004, FR-008)
    actual_sha256 = _compute_sha256(target_path)
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise CheckpointError(
            f"Tệp checkpoint '{target_path.name}' bị hỏng hoặc sai khác mã băm SHA-256: "
            f"tính được {actual_sha256}, kỳ vọng {expected_sha256}."
        )

    # Nạp bằng torch.load với weights_only=True để ngăn ngừa thực thi mã độc hại
    try:
        data = torch.load(target_path, weights_only=True)
    except Exception as err:
        raise CheckpointError(
            f"Không thể nạp checkpoint từ '{target_path}' (tệp hỏng hoặc lỗi cấu trúc): {err}"
        ) from err

    if not isinstance(data, Mapping):
        raise CheckpointError("Nội dung checkpoint không phải là từ điển hợp lệ.")

    # Kiểm tra đủ 6 thành phần bắt buộc (INV-004)
    missing_components = [c for c in REQUIRED_COMPONENTS if c not in data]
    if missing_components:
        raise CheckpointError(
            f"Checkpoint thiếu các thành phần bắt buộc: {', '.join(missing_components)}."
        )

    # Quét tính hữu hạn của toàn bộ dữ liệu đã nạp (INV-004, FR-008)
    try:
        _scan_finite(data, path="checkpoint")
    except NonFiniteError as err:
        raise CheckpointError(
            f"Dữ liệu checkpoint tại '{target_path}' chứa giá trị không hữu hạn (NaN/Inf): {err}"
        ) from err

    actor_sd = cast(dict[str, Tensor], dict(data["actor"]))
    critic_sd = cast(dict[str, Tensor], dict(data["critic"]))
    obs_norm_sd = dict(data["obs_normalizer"])
    optimizer_sd = dict(data["optimizer"])
    seed = int(data.get("seed", 0))
    rng_state = dict(data.get("rng_state", {}))
    update_idx = int(data.get("update_idx", 0))
    env_steps = int(data.get("env_steps", 0))
    ckpt_model_sha256 = str(data.get("model_sha256", ""))
    lib_versions = dict(data.get("library_versions", {}))
    config = data.get("config")
    log_std = data.get("log_std")

    # Kiểm tra tính toàn vẹn cấu trúc mạng actor
    if not isinstance(actor_sd, Mapping) or not actor_sd:
        raise CheckpointError("Thành phần actor không chứa trọng số hợp lệ.")

    weight_keys = [k for k in actor_sd if "weight" in k]
    if not weight_keys:
        raise CheckpointError("Không tìm thấy trọng số trong actor state_dict.")

    first_weight = actor_sd[weight_keys[0]]
    if not isinstance(first_weight, torch.Tensor):
        raise CheckpointError("Trọng số actor không phải là torch.Tensor.")
    actual_obs_dim = first_weight.shape[1]

    if expected_obs_dim is not None and actual_obs_dim != expected_obs_dim:
        raise CheckpointError(
            f"Khác hình dạng mạng: obs_dim của checkpoint là {actual_obs_dim}, "
            f"kỳ vọng {expected_obs_dim}."
        )

    if expected_cfg is not None:
        expected_network = getattr(expected_cfg, "network", None)
        if expected_network is not None:
            expected_actor_hidden = getattr(expected_network, "actor_hidden", None)
            if expected_actor_hidden is not None:
                # Tính các kích thước ẩn thực tế từ các trọng số
                actual_hidden = [actor_sd[k].shape[0] for k in weight_keys[:-1]]
                if list(actual_hidden) != list(expected_actor_hidden):
                    raise CheckpointError(
                        f"Khác cấu trúc mạng: actor_hidden là {actual_hidden}, "
                        f"kỳ vọng {expected_actor_hidden}."
                    )

    # Kiểm tra mã băm XML của mô hình
    if expected_model_sha256 is not None and ckpt_model_sha256 != expected_model_sha256:
        if for_training:
            raise CheckpointError(
                f"Từ chối huấn luyện tiếp do sai khác mã băm XML: "
                f"checkpoint có '{ckpt_model_sha256}', "
                f"mô hình hiện tại có '{expected_model_sha256}'."
            )
        warnings.warn(
            f"Cảnh báo: Mã băm XML của mô hình ({ckpt_model_sha256}) "
            f"khác mô hình hiện tại ({expected_model_sha256}).",
            UserWarning,
            stacklevel=2,
        )

    # Cảnh báo phiên bản thư viện nếu có khác biệt
    curr_torch_ver = str(torch.__version__)
    curr_numpy_ver = str(np.__version__)
    if "torch" in lib_versions and lib_versions["torch"] != curr_torch_ver:
        warnings.warn(
            f"Cảnh báo phiên bản: checkpoint lưu với PyTorch {lib_versions['torch']}, "
            f"hiện tại là {curr_torch_ver}.",
            UserWarning,
            stacklevel=2,
        )
    if "numpy" in lib_versions and lib_versions["numpy"] != curr_numpy_ver:
        warnings.warn(
            f"Cảnh báo phiên bản: checkpoint lưu với NumPy {lib_versions['numpy']}, "
            f"hiện tại là {curr_numpy_ver}.",
            UserWarning,
            stacklevel=2,
        )

    raw = dict(data)
    raw["path"] = f"checkpoints/{target_path.name}"
    raw["sha256"] = actual_sha256
    raw["run_id"] = target_path.parent.parent.name

    return LoadedCheckpoint(
        actor_state_dict=actor_sd,
        critic_state_dict=critic_sd,
        obs_normalizer_state_dict=obs_norm_sd,
        optimizer_state_dict=optimizer_sd,
        seed=seed,
        rng_state=rng_state,
        update_idx=update_idx,
        env_steps=env_steps,
        model_sha256=ckpt_model_sha256,
        library_versions=lib_versions,
        config=config,
        log_std=log_std,
        raw_data=raw,
    )


def load_policy(path: str | Path, cfg: TrainConfig | None = None) -> Policy:
    """Nạp chính sách chỉ-đọc sẵn sàng cho suy luận tất định (FR-008, API-003)."""
    import torch

    from mma_ai.learning.networks import ActorCritic

    loaded = load_checkpoint(path, for_training=False)

    actor_sd = loaded.actor_state_dict
    weight_keys = [k for k in actor_sd if "weight" in k]
    obs_dim = int(actor_sd[weight_keys[0]].shape[1])
    act_dim = int(actor_sd[weight_keys[-1]].shape[0])
    actor_hidden = tuple(int(actor_sd[k].shape[0]) for k in weight_keys[:-1])

    critic_sd = loaded.critic_state_dict
    critic_weight_keys = [k for k in critic_sd if "weight" in k]
    critic_hidden = tuple(int(critic_sd[k].shape[0]) for k in critic_weight_keys[:-1])

    # Khởi tạo hoặc cập nhật cấu hình mạng
    if cfg is None:
        if isinstance(loaded.config, TrainConfig):
            cfg = loaded.config
        elif isinstance(loaded.config, dict):
            try:
                cfg = TrainConfig.load(overrides=loaded.config)
            except Exception:
                cfg = TrainConfig.load()
        else:
            cfg = TrainConfig.load()

    # Điều chỉnh độ rộng mạng nếu khác với cấu hình mặc định
    if cfg.network.actor_hidden != actor_hidden or cfg.network.critic_hidden != critic_hidden:
        from dataclasses import replace

        new_net = replace(cfg.network, actor_hidden=actor_hidden, critic_hidden=critic_hidden)
        cfg = replace(cfg, network=new_net)

    try:
        model = ActorCritic(obs_dim=obs_dim, act_dim=act_dim, cfg=cfg)
        model.actor.load_state_dict(actor_sd)
        model.critic.load_state_dict(critic_sd)
        if loaded.log_std is not None:
            model.log_std.data.copy_(loaded.log_std)
    except Exception as err:
        raise CheckpointError(f"Không thể khởi tạo mạng ActorCritic từ checkpoint: {err}") from err

    normalizer = RunningNorm()
    norm_dict = dict(loaded.obs_normalizer_state_dict)

    # Chuyển đổi tensor trở lại thành NumPy array cho RunningNorm
    if isinstance(norm_dict.get("mean"), torch.Tensor):
        norm_dict["mean"] = norm_dict["mean"].detach().cpu().numpy()
    if isinstance(norm_dict.get("var"), torch.Tensor):
        norm_dict["var"] = norm_dict["var"].detach().cpu().numpy()

    if int(norm_dict.get("count", 0)) > 0:
        normalizer.load_state_dict(norm_dict)

    return Policy(model=model, normalizer=normalizer)
