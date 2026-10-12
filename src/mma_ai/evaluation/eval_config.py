"""Mô-đun quản lý cấu hình đánh giá chính sách (mma_ai.evaluation.eval_config).

Cung cấp cấu hình bất biến (immutable configuration) EvalConfig và phương thức nạp load()
theo chuẩn hợp đồng mô-đun đánh giá:
- AC-2: Cấu hình chứa tiêu chí đánh giá khai trước (criterion) và mức tin cậy phục vụ so sánh.
- INV-006: Tiêu chí kết luận được khai trước, cấm mọi hành vi ghi đè qua tham số overrides.
- FR-007: Tiêu chí kết luận được đọc từ cấu hình và giữ nguyên vẹn trong báo cáo đánh giá.
- FR-018: Quản lý cấu hình tập trung từ tệp YAML duy nhất, từ chối tham số vi phạm ranh giới.
- API-EVL-0001: Hiện thực phương thức EvalConfig.load(path=None, overrides=None).
"""

from __future__ import annotations

import importlib.resources
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from mma_ai.compat.pathrules import is_absolute_any_os
from mma_ai.evaluation.errors import EvalConfigError

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

_ROOT_REQUIRED_KEYS: set[str] = {
    "schema_version",
    "seeds",
    "episodes",
    "criterion",
    "stats",
    "logs",
    "charts",
    "paths",
}

_SEEDS_REQUIRED_KEYS: set[str] = {
    "episode_base",
    "random_policy",
}

_EPISODES_REQUIRED_KEYS: set[str] = {
    "repeats",
    "min_targets",
}

_CRITERION_REQUIRED_KEYS: set[str] = {
    "primary_metric",
    "confidence_level",
}

_STATS_REQUIRED_KEYS: set[str] = {
    "bootstrap_resamples",
    "bootstrap_seed",
}

_LOGS_REQUIRED_KEYS: set[str] = {
    "source",
    "tags",
}

_LOG_TAGS_REQUIRED_KEYS: set[str] = {
    "loss_prefix",
    "reward_prefix",
    "activation_prefix",
}

_CHARTS_REQUIRED_KEYS: set[str] = {
    "dpi",
    "format",
}

_PATHS_REQUIRED_KEYS: set[str] = {
    "runs_dir",
    "env_config_override",
    "expect_fingerprint_sha256",
}

_ALLOWED_OVERRIDE_PATHS: set[str] = {
    "episodes.repeats",
    "seeds.episode_base",
    "paths.runs_dir",
}


@dataclass(frozen=True)
class SeedsConfig:
    """Cấu hình hạt giống ngẫu nhiên (seeds) cho tập đánh giá và chính sách ngẫu nhiên."""

    episode_base: int
    random_policy: int


@dataclass(frozen=True)
class EpisodesConfig:
    """Cấu hình số tập lặp (repeats) và số mục tiêu tối thiểu (min_targets)."""

    repeats: int
    min_targets: int


@dataclass(frozen=True)
class CriterionConfig:
    """Cấu hình tiêu chí so sánh khai trước (criterion) và mức tin cậy."""

    primary_metric: str
    confidence_level: float


@dataclass(frozen=True)
class StatsConfig:
    """Cấu hình tham số thống kê bootstrap và hạt giống tái lập."""

    bootstrap_resamples: int
    bootstrap_seed: int


@dataclass(frozen=True)
class LogTagsConfig:
    """Cấu hình tiền tố thẻ nhật ký (tags) của các đại lượng huấn luyện."""

    loss_prefix: str
    reward_prefix: str
    activation_prefix: str


@dataclass(frozen=True)
class LogsConfig:
    """Cấu hình nguồn nhật ký (logs) và các thẻ dữ liệu liên quan."""

    source: str
    tags: LogTagsConfig


@dataclass(frozen=True)
class ChartsConfig:
    """Cấu hình xuất biểu đồ (charts) gồm độ phân giải và định dạng tệp."""

    dpi: int
    format: str


@dataclass(frozen=True)
class PathsConfig:
    """Cấu hình đường dẫn (paths) và mã băm kiểm tra (fingerprint hash)."""

    runs_dir: str
    env_config_override: str | None
    expect_fingerprint_sha256: str | None


@dataclass(frozen=True)
class EvalConfig:
    """Cấu hình đánh giá chính sách hoàn chỉnh (API-EVL-0001)."""

    schema_version: str
    seeds: SeedsConfig
    episodes: EpisodesConfig
    criterion: CriterionConfig
    stats: StatsConfig
    logs: LogsConfig
    charts: ChartsConfig
    paths: PathsConfig

    @classmethod
    def load(
        cls,
        path: str | Path | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> EvalConfig:
        """Nạp cấu hình đánh giá từ tệp YAML hoặc mặc định đóng gói (API-EVL-0001).

        Args:
            path: Đường dẫn tệp cấu hình YAML tuỳ biến. Mặc định là None (dùng eval_elbow.yaml).
            overrides: Từ điển ghi đè các cờ dòng lệnh (chỉ nhận episodes.repeats,
                seeds.episode_base, paths.runs_dir).

        Returns:
            Đối tượng EvalConfig hợp lệ và bất biến.

        Raises:
            EvalConfigError: Khi tệp không tồn tại, cú pháp lỗi, sai giá trị hoặc
                vi phạm ghi đè INV-006.
        """
        raw_dict = cls._read_raw_dict(path)

        if overrides:
            cls._apply_overrides(raw_dict, overrides)

        return cls._validate_and_build(raw_dict)

    @classmethod
    def _read_raw_dict(cls, path: str | Path | None) -> dict[str, Any]:
        """Đọc từ điển thô từ tệp cấu hình YAML hoặc tài nguyên mặc định."""
        if path is None:
            try:
                ref = importlib.resources.files("mma_ai.evaluation").joinpath("eval_elbow.yaml")
                with ref.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except Exception:
                fallback_path = Path(__file__).parent / "eval_elbow.yaml"
                if not fallback_path.is_file():
                    raise EvalConfigError(
                        "Không tìm thấy tệp cấu hình mặc định eval_elbow.yaml đóng gói."
                    )
                try:
                    with open(fallback_path, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                except Exception as err:
                    raise EvalConfigError(
                        f"Lỗi đọc tệp cấu hình mặc định eval_elbow.yaml: {err}"
                    ) from err
        else:
            p = Path(path)
            if not p.is_file():
                raise EvalConfigError(
                    f"Tệp cấu hình đánh giá không tồn tại hoặc không phải tệp: '{p}'"
                )
            try:
                with open(p, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except Exception as err:
                raise EvalConfigError(
                    f"Lỗi phân tích cú pháp YAML trong tệp '{p}': {err}"
                ) from err

        if not isinstance(data, dict):
            raise EvalConfigError(
                "Nội dung tệp cấu hình phải là từ điển ánh xạ (mapping), nhận được: "
                f"{type(data).__name__}"
            )

        return data

    @classmethod
    def _apply_overrides(cls, raw_dict: dict[str, Any], overrides: dict[str, Any]) -> None:
        """Kiểm tra và áp dụng các giá trị ghi đè cờ dòng lệnh."""
        if not isinstance(overrides, dict):
            t_name = type(overrides).__name__
            raise EvalConfigError(f"Tham số overrides phải là từ điển (dict), nhận được: {t_name}")

        # Chuẩn hoá overrides thành danh sách cập nhật dạng dot-path
        normalized_updates: dict[str, Any] = {}

        for key, value in overrides.items():
            # Kiểm tra nghiêm ngặt vi phạm ghi đè criterion (INV-006)
            if key == "criterion" or key.startswith("criterion."):
                raise EvalConfigError(
                    f"Khoá ghi đè '{key}' bị từ chối: Tiêu chí kết luận (criterion) được "
                    "khai trước và cấm mọi hành vi ghi đè theo bất biến INV-006."
                )

            if isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    dot_key = f"{key}.{sub_key}"
                    if dot_key.startswith("criterion."):
                        raise EvalConfigError(
                            f"Khoá ghi đè '{dot_key}' bị từ chối: Tiêu chí kết luận (criterion) "
                            "được khai trước và cấm mọi hành vi ghi đè theo bất biến INV-006."
                        )
                    normalized_updates[dot_key] = sub_val
            else:
                # Ánh xạ tên cờ ngắn tương đương nếu có
                if key == "repeats":
                    normalized_updates["episodes.repeats"] = value
                elif key in {"eval_seed", "episode_base"}:
                    normalized_updates["seeds.episode_base"] = value
                elif key == "runs_dir":
                    normalized_updates["paths.runs_dir"] = value
                else:
                    normalized_updates[key] = value

        orig_ep_base = raw_dict.get("seeds", {}).get("episode_base")
        orig_rand_policy = raw_dict.get("seeds", {}).get("random_policy")

        # Kiểm tra tính hợp lệ của từng khoá ghi đè
        for dot_path, val in normalized_updates.items():
            if dot_path not in _ALLOWED_OVERRIDE_PATHS:
                raise EvalConfigError(
                    f"Khoá ghi đè '{dot_path}' không được phép. Chỉ cho phép ghi đè các cờ: "
                    f"{', '.join(sorted(_ALLOWED_OVERRIDE_PATHS))}"
                )

            parts = dot_path.split(".")
            target: dict[str, Any] = raw_dict
            for part in parts[:-1]:
                if part not in target or not isinstance(target[part], dict):
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = val

        # NFR-REPRO-001, INV-007: Đồng bộ random_policy theo episode_base khi cấu hình ban đầu
        # dùng chung hạt giống đánh giá (evaluation seed) và không tách riêng hai hạt giống
        if "seeds.episode_base" in normalized_updates and orig_rand_policy == orig_ep_base:
            if "seeds" in raw_dict and isinstance(raw_dict["seeds"], dict):
                raw_dict["seeds"]["random_policy"] = raw_dict["seeds"]["episode_base"]

    @classmethod
    def _validate_and_build(cls, data: dict[str, Any]) -> EvalConfig:
        """Xác thực cấu trúc từ điển theo schema và khởi tạo đối tượng EvalConfig."""
        # 1. Cấp gốc (root)
        cls._validate_keys("Gốc (root)", set(data.keys()), _ROOT_REQUIRED_KEYS)

        schema_version = data["schema_version"]
        if schema_version != "1.0.0":
            raise EvalConfigError(
                f"Giá trị 'schema_version' không hợp lệ: '{schema_version}'. "
                "Bắt buộc phải là '1.0.0'."
            )

        # 2. Hạt giống (seeds)
        seeds_data = data["seeds"]
        if not isinstance(seeds_data, dict):
            raise EvalConfigError(
                f"Phần 'seeds' phải là từ điển, nhận được: {type(seeds_data).__name__}"
            )
        cls._validate_keys("seeds", set(seeds_data.keys()), _SEEDS_REQUIRED_KEYS)

        ep_base = seeds_data["episode_base"]
        if not isinstance(ep_base, int) or isinstance(ep_base, bool) or ep_base < 0:
            raise EvalConfigError(
                f"Giá trị 'seeds.episode_base' phải là số nguyên >= 0, nhận được: {ep_base}"
            )

        rnd_policy = seeds_data["random_policy"]
        if not isinstance(rnd_policy, int) or isinstance(rnd_policy, bool) or rnd_policy < 0:
            raise EvalConfigError(
                f"Giá trị 'seeds.random_policy' phải là số nguyên >= 0, nhận được: {rnd_policy}"
            )

        # 3. Tập episode (episodes)
        episodes_data = data["episodes"]
        if not isinstance(episodes_data, dict):
            raise EvalConfigError(
                f"Phần 'episodes' phải là từ điển, nhận được: {type(episodes_data).__name__}"
            )
        cls._validate_keys("episodes", set(episodes_data.keys()), _EPISODES_REQUIRED_KEYS)

        repeats = episodes_data["repeats"]
        if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats <= 0:
            raise EvalConfigError(
                f"Giá trị 'episodes.repeats' phải là số nguyên dương (> 0), nhận được: {repeats}"
            )

        min_targets = episodes_data["min_targets"]
        if not isinstance(min_targets, int) or isinstance(min_targets, bool) or min_targets < 2:
            raise EvalConfigError(
                f"Giá trị 'episodes.min_targets' phải là số nguyên >= 2, nhận được: {min_targets}"
            )

        # 4. Tiêu chí (criterion)
        criterion_data = data["criterion"]
        if not isinstance(criterion_data, dict):
            raise EvalConfigError(
                f"Phần 'criterion' phải là từ điển, nhận được: {type(criterion_data).__name__}"
            )
        cls._validate_keys("criterion", set(criterion_data.keys()), _CRITERION_REQUIRED_KEYS)

        primary_metric = criterion_data["primary_metric"]
        if primary_metric != "success_rate":
            raise EvalConfigError(
                f"Giá trị 'criterion.primary_metric' không hợp lệ: '{primary_metric}'. "
                "Chỉ chấp nhận: 'success_rate'."
            )

        conf_level = criterion_data["confidence_level"]
        is_num = isinstance(conf_level, (int, float)) and not isinstance(conf_level, bool)
        if not is_num or conf_level <= 0 or conf_level >= 1:
            raise EvalConfigError(
                "Giá trị 'criterion.confidence_level' phải là số thực trong khoảng (0, 1), "
                f"nhận được: {conf_level}"
            )

        # 5. Thống kê (stats)
        stats_data = data["stats"]
        if not isinstance(stats_data, dict):
            raise EvalConfigError(
                f"Phần 'stats' phải là từ điển, nhận được: {type(stats_data).__name__}"
            )
        cls._validate_keys("stats", set(stats_data.keys()), _STATS_REQUIRED_KEYS)

        boot_resamples = stats_data["bootstrap_resamples"]
        is_bad_boot = (
            not isinstance(boot_resamples, int)
            or isinstance(boot_resamples, bool)
            or boot_resamples < 100
        )
        if is_bad_boot:
            raise EvalConfigError(
                "Giá trị 'stats.bootstrap_resamples' phải là số nguyên >= 100, "
                f"nhận được: {boot_resamples}"
            )

        boot_seed = stats_data["bootstrap_seed"]
        if not isinstance(boot_seed, int) or isinstance(boot_seed, bool) or boot_seed < 0:
            raise EvalConfigError(
                f"Giá trị 'stats.bootstrap_seed' phải là số nguyên >= 0, nhận được: {boot_seed}"
            )

        # 6. Nhật ký (logs)
        logs_data = data["logs"]
        if not isinstance(logs_data, dict):
            raise EvalConfigError(
                f"Phần 'logs' phải là từ điển, nhận được: {type(logs_data).__name__}"
            )
        cls._validate_keys("logs", set(logs_data.keys()), _LOGS_REQUIRED_KEYS)

        log_source = logs_data["source"]
        if log_source not in {"auto", "jsonl", "tensorboard"}:
            raise EvalConfigError(
                f"Giá trị 'logs.source' không hợp lệ: '{log_source}'. "
                "Chỉ chấp nhận: 'auto', 'jsonl', 'tensorboard'."
            )

        tags_data = logs_data["tags"]
        if not isinstance(tags_data, dict):
            raise EvalConfigError(
                f"Phần 'logs.tags' phải là từ điển, nhận được: {type(tags_data).__name__}"
            )
        cls._validate_keys("logs.tags", set(tags_data.keys()), _LOG_TAGS_REQUIRED_KEYS)

        for tag_key in _LOG_TAGS_REQUIRED_KEYS:
            tag_val = tags_data[tag_key]
            if not isinstance(tag_val, str) or len(tag_val) < 1:
                raise EvalConfigError(
                    f"Giá trị thẻ 'logs.tags.{tag_key}' phải là chuỗi không rỗng, "
                    f"nhận được: {tag_val!r}"
                )

        # 7. Biểu đồ (charts)
        charts_data = data["charts"]
        if not isinstance(charts_data, dict):
            raise EvalConfigError(
                f"Phần 'charts' phải là từ điển, nhận được: {type(charts_data).__name__}"
            )
        cls._validate_keys("charts", set(charts_data.keys()), _CHARTS_REQUIRED_KEYS)

        dpi = charts_data["dpi"]
        if not isinstance(dpi, int) or isinstance(dpi, bool) or dpi < 50 or dpi > 600:
            raise EvalConfigError(
                f"Giá trị 'charts.dpi' phải là số nguyên trong khoảng [50, 600], nhận được: {dpi}"
            )

        chart_format = charts_data["format"]
        if chart_format != "png":
            raise EvalConfigError(
                f"Giá trị 'charts.format' không hợp lệ: '{chart_format}'. Chỉ chấp nhận 'png'."
            )

        # 8. Đường dẫn (paths)
        paths_data = data["paths"]
        if not isinstance(paths_data, dict):
            raise EvalConfigError(
                f"Phần 'paths' phải là từ điển, nhận được: {type(paths_data).__name__}"
            )
        cls._validate_keys("paths", set(paths_data.keys()), _PATHS_REQUIRED_KEYS)

        runs_dir = paths_data["runs_dir"]
        if (
            not isinstance(runs_dir, str)
            or len(runs_dir) == 0
            or is_absolute_any_os(runs_dir)
        ):
            detail = "không bắt đầu bằng '/'"
            if isinstance(runs_dir, str) and not runs_dir.startswith("/"):
                detail = "không phải đường dẫn tuyệt đối"
            raise EvalConfigError(
                "Giá trị 'paths.runs_dir' phải là đường dẫn tương đối không rỗng và "
                f"{detail}, nhận được: {runs_dir!r}"
            )

        env_override = paths_data["env_config_override"]
        if env_override is not None:
            is_valid_env = (
                isinstance(env_override, str)
                and not is_absolute_any_os(env_override)
                and env_override.endswith(".yaml")
            )
            if not is_valid_env:
                raise EvalConfigError(
                    "Giá trị 'paths.env_config_override' phải là đường dẫn tương đối có đuôi "
                    f"'.yaml' hoặc null, nhận được: {env_override!r}"
                )

        expect_fp = paths_data["expect_fingerprint_sha256"]
        if expect_fp is not None:
            if not isinstance(expect_fp, str) or not _SHA256_PATTERN.match(expect_fp):
                raise EvalConfigError(
                    "Giá trị 'paths.expect_fingerprint_sha256' phải là chuỗi SHA-256 64 ký tự "
                    f"hex chữ thường hoặc null, nhận được: {expect_fp!r}"
                )

        return cls(
            schema_version=schema_version,
            seeds=SeedsConfig(
                episode_base=ep_base,
                random_policy=rnd_policy,
            ),
            episodes=EpisodesConfig(
                repeats=repeats,
                min_targets=min_targets,
            ),
            criterion=CriterionConfig(
                primary_metric=primary_metric,
                confidence_level=float(conf_level),
            ),
            stats=StatsConfig(
                bootstrap_resamples=boot_resamples,
                bootstrap_seed=boot_seed,
            ),
            logs=LogsConfig(
                source=log_source,
                tags=LogTagsConfig(
                    loss_prefix=tags_data["loss_prefix"],
                    reward_prefix=tags_data["reward_prefix"],
                    activation_prefix=tags_data["activation_prefix"],
                ),
            ),
            charts=ChartsConfig(
                dpi=dpi,
                format=chart_format,
            ),
            paths=PathsConfig(
                runs_dir=runs_dir,
                env_config_override=env_override,
                expect_fingerprint_sha256=expect_fp,
            ),
        )

    @classmethod
    def _validate_keys(cls, context: str, actual_keys: set[str], required_keys: set[str]) -> None:
        """Kiểm tra thiếu khoá hoặc khoá lạ ngoài danh sách cho phép."""
        missing = required_keys - actual_keys
        if missing:
            raise EvalConfigError(
                f"Thiếu các khoá bắt buộc trong mục {context}: {sorted(missing)}"
            )
        extra = actual_keys - required_keys
        if extra:
            raise EvalConfigError(
                f"Phát hiện các khoá không hợp lệ hoặc không hỗ trợ trong {context}: "
                f"{sorted(extra)}"
            )

    def as_dict(self) -> dict[str, Any]:
        """Chuyển đổi cấu hình thành từ điển nguyên văn tương thích eval-config.schema.json."""
        return {
            "schema_version": self.schema_version,
            "seeds": {
                "episode_base": self.seeds.episode_base,
                "random_policy": self.seeds.random_policy,
            },
            "episodes": {
                "repeats": self.episodes.repeats,
                "min_targets": self.episodes.min_targets,
            },
            "criterion": {
                "primary_metric": self.criterion.primary_metric,
                "confidence_level": self.criterion.confidence_level,
            },
            "stats": {
                "bootstrap_resamples": self.stats.bootstrap_resamples,
                "bootstrap_seed": self.stats.bootstrap_seed,
            },
            "logs": {
                "source": self.logs.source,
                "tags": {
                    "loss_prefix": self.logs.tags.loss_prefix,
                    "reward_prefix": self.logs.tags.reward_prefix,
                    "activation_prefix": self.logs.tags.activation_prefix,
                },
            },
            "charts": {
                "dpi": self.charts.dpi,
                "format": self.charts.format,
            },
            "paths": {
                "runs_dir": self.paths.runs_dir,
                "env_config_override": self.paths.env_config_override,
                "expect_fingerprint_sha256": self.paths.expect_fingerprint_sha256,
            },
        }


__all__: list[str] = [
    "ChartsConfig",
    "CriterionConfig",
    "EpisodesConfig",
    "EvalConfig",
    "LogTagsConfig",
    "LogsConfig",
    "PathsConfig",
    "SeedsConfig",
    "StatsConfig",
]
