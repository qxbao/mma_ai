"""Nạp và kiểm tra cấu hình huấn luyện bất biến."""

from __future__ import annotations

import copy
import importlib.resources
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from mma_ai.learning.errors import TrainConfigError

_ROOT_KEYS = frozenset(
    {
        "schema_version",
        "stage",
        "seed",
        "env_config",
        "ppo",
        "network",
        "normalization",
        "schedule",
        "checkpoint",
        "reproducibility",
        "paths",
        "ui",
    }
)
_GROUP_KEYS = {
    "ppo": frozenset(
        {
            "learning_rate",
            "clip_range",
            "gamma",
            "gae_lambda",
            "entropy_coef",
            "value_coef",
            "max_grad_norm",
        }
    ),
    "network": frozenset({"actor_hidden", "critic_hidden", "activation", "log_std_init"}),
    "normalization": frozenset({"normalize_obs", "clip_obs", "epsilon"}),
    "schedule": frozenset({"total_timesteps", "n_steps", "batch_size", "n_epochs"}),
    "checkpoint": frozenset({"every_updates"}),
    "reproducibility": frozenset(
        {"rel_tolerance", "head_updates", "torch_threads", "deterministic_algorithms"}
    ),
    "paths": frozenset({"runs_dir"}),
    "ui": frozenset(
        {
            "mode",
            "host",
            "port",
            "snapshot_interval_s",
            "poll_interval_ms",
            "history_points",
            "view3d",
        }
    ),
}
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


@dataclass(frozen=True)
class PpoConfig:
    learning_rate: float
    clip_range: float
    gamma: float
    gae_lambda: float
    entropy_coef: float
    value_coef: float
    max_grad_norm: float


@dataclass(frozen=True)
class NetworkConfig:
    actor_hidden: tuple[int, ...]
    critic_hidden: tuple[int, ...]
    activation: str
    log_std_init: float


@dataclass(frozen=True)
class NormalizationConfig:
    normalize_obs: bool
    clip_obs: float
    epsilon: float


@dataclass(frozen=True)
class ScheduleConfig:
    total_timesteps: int
    n_steps: int
    batch_size: int
    n_epochs: int


@dataclass(frozen=True)
class CheckpointConfig:
    every_updates: int


@dataclass(frozen=True)
class ReproducibilityConfig:
    rel_tolerance: float
    head_updates: int
    torch_threads: int
    deterministic_algorithms: bool


@dataclass(frozen=True)
class PathsConfig:
    runs_dir: str


@dataclass(frozen=True)
class UiConfig:
    mode: str
    host: str
    port: int
    snapshot_interval_s: float
    poll_interval_ms: int
    history_points: int
    view3d: bool


@dataclass(frozen=True)
class TrainConfig:
    """Cấu hình huấn luyện đã kiểm tra, dùng chung cho mọi thành phần learning."""

    schema_version: str
    stage: str
    seed: int
    env_config: str
    ppo: PpoConfig
    network: NetworkConfig
    normalization: NormalizationConfig
    schedule: ScheduleConfig
    checkpoint: CheckpointConfig
    reproducibility: ReproducibilityConfig
    paths: PathsConfig
    ui: UiConfig

    @classmethod
    def load(
        cls, path: str | Path | None = None, overrides: Mapping[str, Any] | None = None
    ) -> TrainConfig:
        """Nạp YAML, áp ghi đè CLI và chỉ trả về cấu hình hợp lệ."""
        raw = _load_yaml(path)
        if overrides:
            _apply_overrides(raw, overrides)
        return _validate(raw)

    def to_dict(self) -> dict[str, Any]:
        """Xuất bản sao từ điển để lưu nguyên văn vào hồ sơ run."""
        return {
            "schema_version": self.schema_version,
            "stage": self.stage,
            "seed": self.seed,
            "env_config": self.env_config,
            "ppo": self.ppo.__dict__.copy(),
            "network": {
                "actor_hidden": list(self.network.actor_hidden),
                "critic_hidden": list(self.network.critic_hidden),
                "activation": self.network.activation,
                "log_std_init": self.network.log_std_init,
            },
            "normalization": self.normalization.__dict__.copy(),
            "schedule": self.schedule.__dict__.copy(),
            "checkpoint": self.checkpoint.__dict__.copy(),
            "reproducibility": self.reproducibility.__dict__.copy(),
            "paths": self.paths.__dict__.copy(),
            "ui": self.ui.__dict__.copy(),
        }


def _load_yaml(path: str | Path | None) -> dict[str, Any]:
    name = str(path) if path is not None else "train_elbow.yaml mặc định"
    try:
        if path is None:
            resource = importlib.resources.files("mma_ai.learning").joinpath("train_elbow.yaml")
            content = resource.read_text(encoding="utf-8")
        else:
            content = Path(path).read_text(encoding="utf-8")
        loaded = yaml.safe_load(content)
    except (OSError, yaml.YAMLError) as error:
        raise TrainConfigError(f"Không thể đọc cấu hình '{name}': {error}") from error
    if not isinstance(loaded, dict):
        raise TrainConfigError(f"Cấu hình '{name}' phải là mapping, nhận {type(loaded).__name__}.")
    return copy.deepcopy(loaded)


def _apply_overrides(data: dict[str, Any], overrides: Mapping[str, Any]) -> None:
    for key, value in overrides.items():
        parts = key.split(".")
        target: dict[str, Any] = data
        for part in parts[:-1]:
            current = target.get(part)
            if not isinstance(current, dict):
                raise TrainConfigError(f"Khoá ghi đè '{key}' không tồn tại trong cấu hình.")
            target = current
        if parts[-1] not in target:
            raise TrainConfigError(f"Khoá ghi đè '{key}' không tồn tại trong cấu hình.")
        target[parts[-1]] = value


def _validate(data: dict[str, Any]) -> TrainConfig:
    _require_exact_keys(data, _ROOT_KEYS, "")
    for group, keys in _GROUP_KEYS.items():
        value = data[group]
        if not isinstance(value, dict):
            raise TrainConfigError(f"Khoá '{group}' phải là mapping, nhận {type(value).__name__}.")
        _require_exact_keys(value, keys, f"{group}.")

    if data["schema_version"] != "1.0.0":
        raise TrainConfigError(
            f"Khoá 'schema_version' phải là '1.0.0', nhận {data['schema_version']!r}."
        )
    if data["stage"] != "elbow":
        raise TrainConfigError(f"Khoá 'stage' phải là 'elbow', nhận {data['stage']!r}.")

    seed = _integer(data["seed"], "seed", minimum=0)
    env_config = _relative_path(data["env_config"], "env_config", suffix=".yaml")
    ppo_data = data["ppo"]
    ppo = PpoConfig(
        learning_rate=_positive(ppo_data["learning_rate"], "ppo.learning_rate"),
        clip_range=_bounded(ppo_data["clip_range"], "ppo.clip_range", 0, 1, upper_inclusive=False),
        gamma=_bounded(ppo_data["gamma"], "ppo.gamma", 0, 1),
        gae_lambda=_bounded(ppo_data["gae_lambda"], "ppo.gae_lambda", 0, 1),
        entropy_coef=_nonnegative(ppo_data["entropy_coef"], "ppo.entropy_coef"),
        value_coef=_nonnegative(ppo_data["value_coef"], "ppo.value_coef"),
        max_grad_norm=_positive(ppo_data["max_grad_norm"], "ppo.max_grad_norm"),
    )
    network_data = data["network"]
    network = NetworkConfig(
        actor_hidden=_hidden(network_data["actor_hidden"], "network.actor_hidden"),
        critic_hidden=_hidden(network_data["critic_hidden"], "network.critic_hidden"),
        activation=_enum(network_data["activation"], "network.activation", {"tanh"}),
        log_std_init=_number(network_data["log_std_init"], "network.log_std_init"),
    )
    normalization_data = data["normalization"]
    normalization = NormalizationConfig(
        normalize_obs=_boolean(normalization_data["normalize_obs"], "normalization.normalize_obs"),
        clip_obs=_positive(normalization_data["clip_obs"], "normalization.clip_obs"),
        epsilon=_positive(normalization_data["epsilon"], "normalization.epsilon"),
    )
    schedule_data = data["schedule"]
    schedule = ScheduleConfig(
        total_timesteps=_integer(
            schedule_data["total_timesteps"], "schedule.total_timesteps", minimum=1
        ),
        n_steps=_integer(schedule_data["n_steps"], "schedule.n_steps", minimum=1),
        batch_size=_integer(schedule_data["batch_size"], "schedule.batch_size", minimum=1),
        n_epochs=_integer(schedule_data["n_epochs"], "schedule.n_epochs", minimum=1),
    )
    if schedule.batch_size > schedule.n_steps:
        raise TrainConfigError("Khoá 'schedule.batch_size' không được lớn hơn 'schedule.n_steps'.")
    if schedule.n_steps > schedule.total_timesteps:
        raise TrainConfigError(
            "Khoá 'schedule.n_steps' không được lớn hơn 'schedule.total_timesteps'."
        )

    checkpoint = CheckpointConfig(
        every_updates=_integer(
            data["checkpoint"]["every_updates"], "checkpoint.every_updates", minimum=1
        )
    )
    reproducibility_data = data["reproducibility"]
    reproducibility = ReproducibilityConfig(
        rel_tolerance=_positive(
            reproducibility_data["rel_tolerance"], "reproducibility.rel_tolerance"
        ),
        head_updates=_integer(
            reproducibility_data["head_updates"], "reproducibility.head_updates", minimum=1
        ),
        torch_threads=_integer(
            reproducibility_data["torch_threads"], "reproducibility.torch_threads", minimum=1
        ),
        deterministic_algorithms=_boolean(
            reproducibility_data["deterministic_algorithms"],
            "reproducibility.deterministic_algorithms",
        ),
    )
    paths = PathsConfig(runs_dir=_relative_path(data["paths"]["runs_dir"], "paths.runs_dir"))
    ui_data = data["ui"]
    host = _enum(ui_data["host"], "ui.host", _LOOPBACK_HOSTS)
    ui = UiConfig(
        mode=_enum(ui_data["mode"], "ui.mode", {"web", "none"}),
        host=host,
        port=_integer(ui_data["port"], "ui.port", minimum=0, maximum=65535),
        snapshot_interval_s=_positive(ui_data["snapshot_interval_s"], "ui.snapshot_interval_s"),
        poll_interval_ms=_integer(ui_data["poll_interval_ms"], "ui.poll_interval_ms", minimum=250),
        history_points=_integer(ui_data["history_points"], "ui.history_points", minimum=10),
        view3d=_boolean(ui_data["view3d"], "ui.view3d"),
    )
    return TrainConfig(
        schema_version="1.0.0",
        stage="elbow",
        seed=seed,
        env_config=env_config,
        ppo=ppo,
        network=network,
        normalization=normalization,
        schedule=schedule,
        checkpoint=checkpoint,
        reproducibility=reproducibility,
        paths=paths,
        ui=ui,
    )


def _require_exact_keys(data: dict[str, Any], expected: frozenset[str], prefix: str) -> None:
    for key in expected - data.keys():
        raise TrainConfigError(f"Thiếu khoá bắt buộc '{prefix}{key}'.")
    for key in data.keys() - expected:
        raise TrainConfigError(f"Khoá thừa không hợp lệ '{prefix}{key}'.")


def _number(value: Any, key: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise TrainConfigError(f"Khoá '{key}' phải là số hữu hạn, nhận {value!r}.")
    return float(value)


def _positive(value: Any, key: str) -> float:
    result = _number(value, key)
    if result <= 0:
        raise TrainConfigError(f"Khoá '{key}' phải lớn hơn 0, nhận {value!r}.")
    return result


def _nonnegative(value: Any, key: str) -> float:
    result = _number(value, key)
    if result < 0:
        raise TrainConfigError(f"Khoá '{key}' phải không âm, nhận {value!r}.")
    return result


def _bounded(
    value: Any, key: str, lower: float, upper: float, upper_inclusive: bool = True
) -> float:
    result = _number(value, key)
    valid_upper = result <= upper if upper_inclusive else result < upper
    if result <= lower or not valid_upper:
        raise TrainConfigError(
            f"Khoá '{key}' phải trong khoảng ({lower}, {upper}), nhận {value!r}."
        )
    return result


def _integer(value: Any, key: str, minimum: int, maximum: int | None = None) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise TrainConfigError(f"Khoá '{key}' phải là số nguyên, nhận {value!r}.")
    if value < minimum or (maximum is not None and value > maximum):
        raise TrainConfigError(f"Khoá '{key}' ngoài khoảng hợp lệ, nhận {value!r}.")
    return value


def _hidden(value: Any, key: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise TrainConfigError(f"Khoá '{key}' phải là danh sách số nguyên dương không rỗng.")
    return tuple(_integer(item, key, minimum=1) for item in value)


def _boolean(value: Any, key: str) -> bool:
    if type(value) is not bool:
        raise TrainConfigError(f"Khoá '{key}' phải là boolean, nhận {value!r}.")
    return value


def _enum(value: Any, key: str, values: frozenset[str] | set[str]) -> str:
    if not isinstance(value, str) or value not in values:
        raise TrainConfigError(f"Khoá '{key}' có giá trị không hợp lệ: {value!r}.")
    return value


def _relative_path(value: Any, key: str, suffix: str | None = None) -> str:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or (suffix and not value.endswith(suffix))
    ):
        raise TrainConfigError(f"Khoá '{key}' phải là đường dẫn tương đối hợp lệ, nhận {value!r}.")
    return value


__all__ = [
    "CheckpointConfig",
    "NetworkConfig",
    "NormalizationConfig",
    "PathsConfig",
    "PpoConfig",
    "ReproducibilityConfig",
    "ScheduleConfig",
    "TrainConfig",
    "UiConfig",
]
