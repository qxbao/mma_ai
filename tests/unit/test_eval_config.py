"""Kiểm thử đơn vị cho mô-đun cấu hình đánh giá (mma_ai.evaluation.eval_config).

Chứng minh các yêu cầu và bất biến theo hợp đồng:
- AC-2: Cấu hình chứa tiêu chí đánh giá khai trước và mức tin cậy phục vụ so sánh.
- INV-006: Tiêu chí kết luận (criterion) được khai trước, cấm mọi hành vi ghi đè qua overrides.
- FR-007: Tiêu chí kết luận được đọc từ cấu hình và giữ nguyên vẹn trong báo cáo.
- FR-018: Quản lý cấu hình tập trung từ YAML, từ chối tham số vi phạm ranh giới.
- API-EVL-0001: Hiện thực phương thức EvalConfig.load(path=None, overrides=None).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from mma_ai.evaluation.errors import EvalConfigError
from mma_ai.evaluation.eval_config import EvalConfig


def test_defaults_load() -> None:
    """AC-2, FR-007, FR-018, API-EVL-0001: Nạp cấu hình mặc định đóng gói thành công."""
    cfg = EvalConfig.load()

    assert cfg.schema_version == "1.0.0"
    assert cfg.seeds.episode_base == 12345
    assert cfg.seeds.random_policy == 12345
    assert cfg.episodes.repeats == 1
    assert cfg.episodes.min_targets == 2
    assert cfg.criterion.primary_metric == "success_rate"
    assert cfg.criterion.confidence_level == 0.95
    assert cfg.stats.bootstrap_resamples == 10000
    assert cfg.stats.bootstrap_seed == 0
    assert cfg.logs.source == "auto"
    assert cfg.logs.tags.loss_prefix == "loss"
    assert cfg.logs.tags.reward_prefix == "reward"
    assert cfg.logs.tags.activation_prefix == "activation/"
    assert cfg.charts.dpi == 120
    assert cfg.charts.format == "png"
    assert cfg.paths.runs_dir == "runs"
    assert cfg.paths.env_config_override is None
    assert cfg.paths.expect_fingerprint_sha256 is None

    # as_dict() trả về từ điển hoàn chỉnh
    cfg_dict = cfg.as_dict()
    assert isinstance(cfg_dict, dict)
    assert cfg_dict["schema_version"] == "1.0.0"
    assert cfg_dict["seeds"]["episode_base"] == 12345
    assert cfg_dict["episodes"]["repeats"] == 1
    assert cfg_dict["criterion"]["primary_metric"] == "success_rate"


def test_default_equals_contract_example() -> None:
    """FR-007, FR-018, API-EVL-0001: Giá trị mặc định khớp ví dụ hợp đồng default json."""
    rel_path = "specs/004-eval-vs-random-plots/contracts/examples/eval-config.default.json"
    contract_path = Path(rel_path)
    if not contract_path.exists():
        contract_path = Path("/mnt/01DCE9A4D6522BD0/Project/AI/fighterl") / rel_path

    with open(contract_path, encoding="utf-8") as f:
        expected = json.load(f)

    cfg = EvalConfig.load()
    assert cfg.as_dict() == expected


def test_invalid_values_raise(tmp_path: Path) -> None:
    """AC-2, FR-018, API-EVL-0001: Ném EvalConfigError khi cấu hình chứa giá trị sai."""
    cfg = EvalConfig.load()
    base_dict = cfg.as_dict()

    invalid_cases: list[dict[str, Any]] = [
        # Số lặp tập episode <= 0
        {"episodes": {"repeats": 0, "min_targets": 2}},
        {"episodes": {"repeats": -1, "min_targets": 2}},
        # min_targets < 2
        {"episodes": {"repeats": 1, "min_targets": 1}},
        {"episodes": {"repeats": 1, "min_targets": 0}},
        # confidence_level ngoài (0, 1)
        {"criterion": {"primary_metric": "success_rate", "confidence_level": 0.0}},
        {"criterion": {"primary_metric": "success_rate", "confidence_level": 1.0}},
        {"criterion": {"primary_metric": "success_rate", "confidence_level": -0.5}},
        {"criterion": {"primary_metric": "success_rate", "confidence_level": 1.5}},
        # primary_metric không nằm trong danh sách được hỗ trợ
        {"criterion": {"primary_metric": "mean_return", "confidence_level": 0.95}},
        {"criterion": {"primary_metric": "invalid_metric", "confidence_level": 0.95}},
        # stats: bootstrap_resamples < 100
        {"stats": {"bootstrap_resamples": 99, "bootstrap_seed": 0}},
        {"stats": {"bootstrap_resamples": -10, "bootstrap_seed": 0}},
        {"stats": {"bootstrap_resamples": 1000, "bootstrap_seed": -1}},
        # seeds âm
        {"seeds": {"episode_base": -1, "random_policy": 12345}},
        {"seeds": {"episode_base": 12345, "random_policy": -5}},
        # charts dpi ngoài [50, 600]
        {"charts": {"dpi": 49, "format": "png"}},
        {"charts": {"dpi": 601, "format": "png"}},
        {"charts": {"dpi": 120, "format": "svg"}},
        # logs source ngoài [auto, jsonl, tensorboard]
        {
            "logs": {
                "source": "stdout",
                "tags": {
                    "loss_prefix": "loss",
                    "reward_prefix": "reward",
                    "activation_prefix": "act",
                },
            }
        },
        # logs tags rỗng
        {
            "logs": {
                "source": "auto",
                "tags": {
                    "loss_prefix": "",
                    "reward_prefix": "reward",
                    "activation_prefix": "act",
                },
            }
        },
        # paths runs_dir là đường dẫn tuyệt đối hoặc rỗng
        {"paths": {"runs_dir": "/abs/path"}},
        {"paths": {"runs_dir": ""}},
        # paths env_config_override không phải đuôi .yaml hoặc là đường dẫn tuyệt đối
        {"paths": {"env_config_override": "config.json"}},
        {"paths": {"env_config_override": "/etc/config.yaml"}},
        # paths expect_fingerprint_sha256 sai định dạng sha256 64 ký tự hex
        {"paths": {"expect_fingerprint_sha256": "not_a_valid_sha256"}},
        # schema_version sai
        {"schema_version": "2.0.0"},
    ]

    for case_mod in invalid_cases:
        modified_dict = json.loads(json.dumps(base_dict))
        for k, v in case_mod.items():
            if isinstance(v, dict) and isinstance(modified_dict.get(k), dict):
                modified_dict[k].update(v)
            else:
                modified_dict[k] = v

        temp_yaml = tmp_path / f"invalid_case_{abs(hash(str(case_mod)))}.yaml"
        with open(temp_yaml, "w", encoding="utf-8") as f:
            yaml.dump(modified_dict, f)

        with pytest.raises(EvalConfigError):
            EvalConfig.load(temp_yaml)


def test_t629_ac_4_absolute_paths_are_rejected(tmp_path: Path) -> None:
    """AC-4: Từ chối đường dẫn tuyệt đối theo cú pháp POSIX và Windows."""
    absolute_paths = [
        "/absolute/path",
        "\\rooted\\path",
        "\\\\server\\share",
        "C:\\folder\\config",
        "C:folder",
    ]
    for field in ("runs_dir", "env_config_override"):
        for absolute_path in absolute_paths:
            config = EvalConfig.load().as_dict()
            value = absolute_path if field == "runs_dir" else f"{absolute_path}.yaml"
            config["paths"][field] = value
            config_path = tmp_path / f"{field}_{len(value)}.yaml"
            config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

            with pytest.raises(EvalConfigError) as exc_info:
                EvalConfig.load(config_path)

            assert repr(value) in str(exc_info.value)


def test_t629_ac_4_relative_paths_are_accepted(tmp_path: Path) -> None:
    """AC-4: Chấp nhận đường dẫn tương đối ở cả hai trường cấu hình."""
    config = EvalConfig.load().as_dict()
    config["paths"]["runs_dir"] = "runs/custom"
    config["paths"]["env_config_override"] = "configs/environment.yaml"
    config_path = tmp_path / "relative_paths.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    loaded = EvalConfig.load(config_path)

    assert loaded.paths.runs_dir == "runs/custom"
    assert loaded.paths.env_config_override == "configs/environment.yaml"


def test_missing_and_extra_keys_raise(tmp_path: Path) -> None:
    """FR-018: Ném EvalConfigError khi thiếu khoá bắt buộc hoặc có khoá lạ không cho phép."""
    cfg = EvalConfig.load()
    base_dict = cfg.as_dict()

    # Thiếu khoá gốc
    dict_missing = json.loads(json.dumps(base_dict))
    del dict_missing["criterion"]
    f1 = tmp_path / "missing_criterion.yaml"
    with open(f1, "w", encoding="utf-8") as f:
        yaml.dump(dict_missing, f)
    with pytest.raises(EvalConfigError):
        EvalConfig.load(f1)

    # Thừa khoá lạ ở root
    dict_extra = json.loads(json.dumps(base_dict))
    dict_extra["extra_root_key"] = 123
    f2 = tmp_path / "extra_key.yaml"
    with open(f2, "w", encoding="utf-8") as f:
        yaml.dump(dict_extra, f)
    with pytest.raises(EvalConfigError):
        EvalConfig.load(f2)

    # Thừa khoá lạ ở object con
    dict_child_extra = json.loads(json.dumps(base_dict))
    dict_child_extra["seeds"]["unexpected_seed"] = 42
    f3 = tmp_path / "extra_child_key.yaml"
    with open(f3, "w", encoding="utf-8") as f:
        yaml.dump(dict_child_extra, f)
    with pytest.raises(EvalConfigError):
        EvalConfig.load(f3)


def test_criterion_override_rejected() -> None:
    """INV-006, FR-007, AC-2: Cấm ghi đè mọi khoá criterion qua overrides theo bất biến."""
    with pytest.raises(EvalConfigError) as exc_info1:
        EvalConfig.load(overrides={"criterion.primary_metric": "success_rate"})
    assert "criterion" in str(exc_info1.value).lower()

    with pytest.raises(EvalConfigError) as exc_info2:
        EvalConfig.load(overrides={"criterion.confidence_level": 0.99})
    assert "criterion" in str(exc_info2.value).lower()

    with pytest.raises(EvalConfigError) as exc_info3:
        EvalConfig.load(overrides={"criterion": {"primary_metric": "success_rate"}})
    assert "criterion" in str(exc_info3.value).lower()


def test_allowed_overrides_applied() -> None:
    """API-EVL-0001, FR-018: Cho phép ghi đè các cờ dòng lệnh repeats, seed, runs_dir."""
    # Ghi đè dạng dot notation
    cfg = EvalConfig.load(overrides={
        "episodes.repeats": 5,
        "seeds.episode_base": 99999,
        "paths.runs_dir": "custom_experiments/runs",
    })
    assert cfg.episodes.repeats == 5
    assert cfg.seeds.episode_base == 99999
    assert cfg.paths.runs_dir == "custom_experiments/runs"

    # Ghi đè dạng lồng dict
    cfg2 = EvalConfig.load(overrides={
        "episodes": {"repeats": 3},
        "seeds": {"episode_base": 54321},
        "paths": {"runs_dir": "runs_v2"},
    })
    assert cfg2.episodes.repeats == 3
    assert cfg2.seeds.episode_base == 54321
    assert cfg2.paths.runs_dir == "runs_v2"


def test_forbidden_overrides_rejected() -> None:
    """INV-006, FR-018: Từ chối các khoá ghi đè không thuộc danh sách được hỗ trợ."""
    with pytest.raises(EvalConfigError):
        EvalConfig.load(overrides={"seeds.random_policy": 999})

    with pytest.raises(EvalConfigError):
        EvalConfig.load(overrides={"stats.bootstrap_resamples": 5000})

    with pytest.raises(EvalConfigError):
        EvalConfig.load(overrides={"charts.dpi": 300})

    with pytest.raises(EvalConfigError):
        EvalConfig.load(overrides={"arbitrary_key": "val"})


def test_file_not_found_and_invalid_yaml(tmp_path: Path) -> None:
    """FR-018: Ném EvalConfigError khi tệp cấu hình không tồn tại hoặc sai YAML."""
    with pytest.raises(EvalConfigError):
        EvalConfig.load("non_existent_config_file_path.yaml")

    # Tệp không phải YAML hợp lệ (danh sách thay vì mapping)
    bad_yaml = tmp_path / "list_not_dict.yaml"
    bad_yaml.write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(EvalConfigError):
        EvalConfig.load(bad_yaml)


def test_config_against_json_schema() -> None:
    """FR-018, API-EVL-0001: Cấu hình mặc định và ghi đè tuân thủ eval-config.schema.json."""
    import jsonschema

    rel_schema = "specs/004-eval-vs-random-plots/contracts/eval-config.schema.json"
    schema_path = Path(rel_schema)
    if not schema_path.exists():
        schema_path = Path("/mnt/01DCE9A4D6522BD0/Project/AI/fighterl") / rel_schema

    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    # 1. Cấu hình mặc định
    cfg_default = EvalConfig.load()
    jsonschema.validate(instance=cfg_default.as_dict(), schema=schema)

    # 2. Cấu hình với ghi đè hợp lệ
    cfg_overridden = EvalConfig.load(overrides={
        "episodes.repeats": 10,
        "seeds.episode_base": 77777,
        "paths.runs_dir": "runs_benchmark",
    })
    jsonschema.validate(instance=cfg_overridden.as_dict(), schema=schema)
