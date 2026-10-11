"""Mô-đun quản lý cấu hình môi trường khuỷu tay (mma_ai.environment.env_config).

Cung cấp cấu hình bất biến và phương thức nạp load() theo chuẩn hợp đồng:
- FR-014: Quản lý cấu hình tập trung từ tệp YAML duy nhất và kiểm tra tính hợp lệ.
- API-002: Lớp ElbowEnvConfig với phương thức nạp ElbowEnvConfig.load(path=None).
- INV-001: Ràng buộc chéo split_block_m > 1.1 * min_separation_m chống rò rỉ mục tiêu.
"""

from __future__ import annotations

import importlib.resources
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from mma_ai.environment.errors import EnvConfigError

_REQUIRED_ROOT_KEYS: set[str] = {
    "schema_version",
    "physics_timestep_s",
    "substeps_per_action",
    "fingertip_site",
    "target_split",
    "reward",
    "tolerance_m",
    "max_actions",
    "obs",
    "targets",
}

_REQUIRED_REWARD_KEYS: set[str] = {
    "w_dist",
    "w_effort",
    "d_ref_m",
}

_REQUIRED_OBS_KEYS: set[str] = {
    "qvel_scale_rad_s",
}

_REQUIRED_TARGETS_KEYS: set[str] = {
    "n_train",
    "n_test",
    "min_separation_m",
    "split_block_m",
    "angle_margin_rad",
    "default_seed",
}


@dataclass(frozen=True)
class RewardConfig:
    """Cấu hình trọng số và tham số hàm phần thưởng (reward)."""

    w_dist: float
    w_effort: float
    d_ref_m: float


@dataclass(frozen=True)
class ObsConfig:
    """Cấu hình các tham số chuẩn hoá không gian quan sát (observation)."""

    qvel_scale_rad_s: float


@dataclass(frozen=True)
class TargetConfig:
    """Cấu hình không gian mục tiêu và phân tách train/test (targets)."""

    n_train: int
    n_test: int
    min_separation_m: float
    split_block_m: float
    angle_margin_rad: float
    default_seed: int


@dataclass(frozen=True)
class ElbowEnvConfig:
    """Cấu hình toàn diện môi trường khuỷu tay MyoElbow (FR-014, API-002)."""

    schema_version: str
    physics_timestep_s: float
    substeps_per_action: int
    fingertip_site: str
    target_split: Literal["train", "test"] | str
    reward: RewardConfig
    tolerance_m: float
    max_actions: int
    obs: ObsConfig
    targets: TargetConfig

    def to_dict(self) -> dict[str, Any]:
        """Xuất cấu hình thành từ điển (dictionary) tương thích JSON Schema hợp đồng."""
        return {
            "schema_version": self.schema_version,
            "physics_timestep_s": self.physics_timestep_s,
            "substeps_per_action": self.substeps_per_action,
            "fingertip_site": self.fingertip_site,
            "target_split": self.target_split,
            "reward": {
                "w_dist": self.reward.w_dist,
                "w_effort": self.reward.w_effort,
                "d_ref_m": self.reward.d_ref_m,
            },
            "tolerance_m": self.tolerance_m,
            "max_actions": self.max_actions,
            "obs": {
                "qvel_scale_rad_s": self.obs.qvel_scale_rad_s,
            },
            "targets": {
                "n_train": self.targets.n_train,
                "n_test": self.targets.n_test,
                "min_separation_m": self.targets.min_separation_m,
                "split_block_m": self.targets.split_block_m,
                "angle_margin_rad": self.targets.angle_margin_rad,
                "default_seed": self.targets.default_seed,
            },
        }

    @classmethod
    def load(cls, path: str | Path | None = None) -> ElbowEnvConfig:
        """Nạp cấu hình môi trường từ tệp YAML mặc định hoặc chỉ định (API-002)."""
        content = _read_config_content(path)

        try:
            raw_data = yaml.safe_load(content)
        except Exception as err:
            target_name = str(path) if path is not None else "elbow_env.yaml mặc định"
            raise EnvConfigError(
                f"Cú pháp YAML trong tệp cấu hình '{target_name}' không hợp lệ: {err}"
            ) from err

        if not isinstance(raw_data, dict):
            target_name = str(path) if path is not None else "elbow_env.yaml mặc định"
            raw_type = type(raw_data).__name__
            raise EnvConfigError(
                f"Nội dung cấu hình '{target_name}' phải là một mapping/dict, nhận: {raw_type}"
            )

        return _validate_and_build(raw_data)


def _read_config_content(path: str | Path | None) -> str:
    """Đọc nội dung văn bản cấu hình từ đường dẫn tệp hoặc gói đóng sẵn."""
    if path is not None:
        cfg_path = Path(path)
        if not cfg_path.is_file():
            raise EnvConfigError(
                f"Tệp cấu hình không tồn tại hoặc không phải là tệp hợp lệ: {path}"
            )
        try:
            return cfg_path.read_text(encoding="utf-8")
        except Exception as err:
            raise EnvConfigError(f"Không thể đọc tệp cấu hình tại {path}: {err}") from err

    # Nạp tệp elbow_env.yaml đóng gói sẵn trong package
    try:
        packaged_ref = importlib.resources.files("mma_ai.environment").joinpath("elbow_env.yaml")
        with importlib.resources.as_file(packaged_ref) as config_file:
            if not config_file.is_file():
                raise FileNotFoundError(f"Không tìm thấy tệp {config_file}")
            return config_file.read_text(encoding="utf-8")
    except Exception as err:
        fallback_path = Path(__file__).resolve().parent / "elbow_env.yaml"
        if fallback_path.is_file():
            return fallback_path.read_text(encoding="utf-8")
        raise EnvConfigError(
            f"Không thể nạp cấu hình mặc định từ gói mma_ai.environment: {err}"
        ) from err


def _validate_and_build(data: dict[str, Any]) -> ElbowEnvConfig:
    """Xác thực toàn bộ cấu trúc dữ liệu cấu hình và dựng đối tượng ElbowEnvConfig."""
    for key in _REQUIRED_ROOT_KEYS:
        if key not in data:
            raise EnvConfigError(f"Thiếu khoá bắt buộc ở cấp gốc: '{key}'.")

    for key in data:
        if key not in _REQUIRED_ROOT_KEYS:
            raise EnvConfigError(f"Khoá thừa không hợp lệ ở cấp gốc: '{key}'.")

    # 1. schema_version
    schema_version = data["schema_version"]
    if schema_version != "1.0.0":
        raise EnvConfigError(
            f"Khoá 'schema_version' phải là '1.0.0', nhận được: '{schema_version}'."
        )

    # 2. physics_timestep_s
    physics_timestep_s = data["physics_timestep_s"]
    if (
        isinstance(physics_timestep_s, bool)
        or not isinstance(physics_timestep_s, (int, float))
        or physics_timestep_s <= 0
    ):
        raise EnvConfigError(
            f"Khoá 'physics_timestep_s' phải là số thực dương (> 0), "
            f"nhận được: {physics_timestep_s}."
        )

    # 3. substeps_per_action
    substeps_per_action = data["substeps_per_action"]
    if (
        isinstance(substeps_per_action, bool)
        or type(substeps_per_action) is not int
        or substeps_per_action < 1
    ):
        raise EnvConfigError(
            f"Khoá 'substeps_per_action' phải là số nguyên >= 1, nhận được: {substeps_per_action}."
        )

    # 4. fingertip_site
    fingertip_site = data["fingertip_site"]
    if not isinstance(fingertip_site, str) or len(fingertip_site.strip()) == 0:
        raise EnvConfigError(
            f"Khoá 'fingertip_site' phải là chuỗi ký tự không rỗng, nhận được: {fingertip_site!r}."
        )

    # 5. target_split
    target_split = data["target_split"]
    if target_split not in ("train", "test"):
        raise EnvConfigError(
            f"Khoá 'target_split' phải là 'train' hoặc 'test', nhận được: {target_split!r}."
        )

    # 6. tolerance_m
    tolerance_m = data["tolerance_m"]
    if (
        isinstance(tolerance_m, bool)
        or not isinstance(tolerance_m, (int, float))
        or tolerance_m <= 0
    ):
        raise EnvConfigError(
            f"Khoá 'tolerance_m' phải là số thực dương (> 0), nhận được: {tolerance_m}."
        )

    # 7. max_actions
    max_actions = data["max_actions"]
    if (
        isinstance(max_actions, bool)
        or type(max_actions) is not int
        or max_actions < 1
    ):
        raise EnvConfigError(
            f"Khoá 'max_actions' phải là số nguyên >= 1, nhận được: {max_actions}."
        )

    # 8. reward
    reward_cfg = _validate_reward(data["reward"])

    # 9. obs
    obs_cfg = _validate_obs(data["obs"])

    # 10. targets
    targets_cfg = _validate_targets(data["targets"])

    return ElbowEnvConfig(
        schema_version=schema_version,
        physics_timestep_s=float(physics_timestep_s),
        substeps_per_action=substeps_per_action,
        fingertip_site=fingertip_site,
        target_split=target_split,
        reward=reward_cfg,
        tolerance_m=float(tolerance_m),
        max_actions=max_actions,
        obs=obs_cfg,
        targets=targets_cfg,
    )


def _validate_reward(data: Any) -> RewardConfig:
    """Kiểm tra và khởi tạo RewardConfig."""
    if not isinstance(data, dict):
        raise EnvConfigError(
            f"Phân đoạn 'reward' phải là một mapping/dict, nhận: {type(data).__name__}."
        )

    for key in _REQUIRED_REWARD_KEYS:
        if key not in data:
            raise EnvConfigError(f"Thiếu khoá bắt buộc trong 'reward': '{key}'.")

    for key in data:
        if key not in _REQUIRED_REWARD_KEYS:
            raise EnvConfigError(f"Khoá thừa không hợp lệ trong 'reward': '{key}'.")

    w_dist = data["w_dist"]
    if (
        isinstance(w_dist, bool)
        or not isinstance(w_dist, (int, float))
        or w_dist < 0
    ):
        raise EnvConfigError(
            f"Khoá 'reward.w_dist' phải là số thực không âm (>= 0), nhận được: {w_dist}."
        )

    w_effort = data["w_effort"]
    if (
        isinstance(w_effort, bool)
        or not isinstance(w_effort, (int, float))
        or w_effort < 0
    ):
        raise EnvConfigError(
            f"Khoá 'reward.w_effort' phải là số thực không âm (>= 0), nhận được: {w_effort}."
        )

    d_ref_m = data["d_ref_m"]
    if (
        isinstance(d_ref_m, bool)
        or not isinstance(d_ref_m, (int, float))
        or d_ref_m <= 0
    ):
        raise EnvConfigError(
            f"Khoá 'reward.d_ref_m' phải là số thực dương (> 0), nhận được: {d_ref_m}."
        )

    return RewardConfig(
        w_dist=float(w_dist),
        w_effort=float(w_effort),
        d_ref_m=float(d_ref_m),
    )


def _validate_obs(data: Any) -> ObsConfig:
    """Kiểm tra và khởi tạo ObsConfig."""
    if not isinstance(data, dict):
        raise EnvConfigError(
            f"Phân đoạn 'obs' phải là một mapping/dict, nhận: {type(data).__name__}."
        )

    for key in _REQUIRED_OBS_KEYS:
        if key not in data:
            raise EnvConfigError(f"Thiếu khoá bắt buộc trong 'obs': '{key}'.")

    for key in data:
        if key not in _REQUIRED_OBS_KEYS:
            raise EnvConfigError(f"Khoá thừa không hợp lệ trong 'obs': '{key}'.")

    qvel_scale_rad_s = data["qvel_scale_rad_s"]
    if (
        isinstance(qvel_scale_rad_s, bool)
        or not isinstance(qvel_scale_rad_s, (int, float))
        or qvel_scale_rad_s <= 0
    ):
        raise EnvConfigError(
            f"Khoá 'obs.qvel_scale_rad_s' phải là số thực dương (> 0), "
            f"nhận được: {qvel_scale_rad_s}."
        )

    return ObsConfig(
        qvel_scale_rad_s=float(qvel_scale_rad_s),
    )


def _validate_targets(data: Any) -> TargetConfig:
    """Kiểm tra và khởi tạo TargetConfig kèm kiểm tra bất biến INV-001."""
    if not isinstance(data, dict):
        raise EnvConfigError(
            f"Phân đoạn 'targets' phải là một mapping/dict, nhận: {type(data).__name__}."
        )

    for key in _REQUIRED_TARGETS_KEYS:
        if key not in data:
            raise EnvConfigError(f"Thiếu khoá bắt buộc trong 'targets': '{key}'.")

    for key in data:
        if key not in _REQUIRED_TARGETS_KEYS:
            raise EnvConfigError(f"Khoá thừa không hợp lệ trong 'targets': '{key}'.")

    n_train = data["n_train"]
    if isinstance(n_train, bool) or type(n_train) is not int or n_train < 1:
        raise EnvConfigError(
            f"Khoá 'targets.n_train' phải là số nguyên >= 1, nhận được: {n_train}."
        )

    n_test = data["n_test"]
    if isinstance(n_test, bool) or type(n_test) is not int or n_test < 1:
        raise EnvConfigError(
            f"Khoá 'targets.n_test' phải là số nguyên >= 1, nhận được: {n_test}."
        )

    min_separation_m = data["min_separation_m"]
    if (
        isinstance(min_separation_m, bool)
        or not isinstance(min_separation_m, (int, float))
        or min_separation_m <= 0
    ):
        raise EnvConfigError(
            f"Khoá 'targets.min_separation_m' phải là số thực dương (> 0), "
            f"nhận được: {min_separation_m}."
        )

    split_block_m = data["split_block_m"]
    if (
        isinstance(split_block_m, bool)
        or not isinstance(split_block_m, (int, float))
        or split_block_m <= 0
    ):
        raise EnvConfigError(
            f"Khoá 'targets.split_block_m' phải là số thực dương (> 0), nhận được: {split_block_m}."
        )

    angle_margin_rad = data["angle_margin_rad"]
    if (
        isinstance(angle_margin_rad, bool)
        or not isinstance(angle_margin_rad, (int, float))
        or angle_margin_rad < 0
    ):
        raise EnvConfigError(
            f"Khoá 'targets.angle_margin_rad' phải là số thực không âm (>= 0), "
            f"nhận được: {angle_margin_rad}."
        )

    default_seed = data["default_seed"]
    if (
        isinstance(default_seed, bool)
        or type(default_seed) is not int
        or default_seed < 0
    ):
        raise EnvConfigError(
            f"Khoá 'targets.default_seed' phải là số nguyên không âm (>= 0), "
            f"nhận được: {default_seed}."
        )

    min_sep = float(min_separation_m)
    split_block = float(split_block_m)
    required_threshold = 1.1 * min_sep
    # Bất biến INV-001: split_block_m phải lớn hơn 1.1 * min_separation_m
    if split_block <= required_threshold:
        raise EnvConfigError(
            f"Ràng buộc chéo thất bại: 'targets.split_block_m' ({split_block}) "
            f"phải lớn hơn 1.1 * 'targets.min_separation_m' ({required_threshold:.6f}) (INV-001)."
        )

    return TargetConfig(
        n_train=n_train,
        n_test=n_test,
        min_separation_m=min_sep,
        split_block_m=split_block,
        angle_margin_rad=float(angle_margin_rad),
        default_seed=default_seed,
    )


__all__: list[str] = [
    "ElbowEnvConfig",
    "ObsConfig",
    "RewardConfig",
    "TargetConfig",
]
