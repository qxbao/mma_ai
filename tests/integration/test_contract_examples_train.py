"""Kiểm thử tích hợp hợp đồng và ví dụ cho feature huấn luyện PPO.

Hiện thực các bài kiểm thử xác nhận hợp đồng dữ liệu cho quy trình huấn luyện:
- FR-011: Hồ sơ run manifest và các tệp JSON hợp đồng tuân thủ schema.
- FR-018: Cấu hình TrainConfig hợp chuẩn train-config.schema.json.
- FR-019: Kiểm chứng các ví dụ hợp đồng mẫu đóng gói.
- FR-023: Báo cáo chuẩn đo hiệu năng benchmark hợp train-benchmark.schema.json.
- INV-001: Tính bất biến và tính hợp lệ của lược đồ JSON Schema.
- AC-3: Kiểm tra toàn diện mọi tệp ví dụ hợp đồng trong thư mục examples/*.json.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path, PureWindowsPath
from typing import Any, cast

import pytest

pytest.importorskip("jsonschema", reason="Cần jsonschema để xác thực hợp đồng JSON Schema.")

from jsonschema import Draft202012Validator
from train_fixtures import load_schema_registry

from mma_ai.learning.train_config import TrainConfig

_CONTRACTS_DIR = (
    Path(__file__).resolve().parents[2] / "specs" / "003-ppo-train-repro" / "contracts"
)


def _load_json(path: Path) -> dict[str, Any]:
    """Nạp một bản ghi JSON hợp đồng từ đĩa."""
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _load_all_schemas() -> dict[str, dict[str, Any]]:
    """Nạp tất cả các tệp JSON Schema từ thư mục hợp đồng."""
    return {
        path.name: _load_json(path)
        for path in sorted(_CONTRACTS_DIR.glob("*.schema.json"))
    }


def _assert_valid(instance: dict[str, Any], schema_name: str) -> None:
    """Xác thực một bản ghi dữ liệu bằng JSON Schema draft 2020-12 đã nạp registry."""
    registry = load_schema_registry()
    schemas = _load_all_schemas()
    if schema_name not in schemas:
        raise KeyError(f"Không tìm thấy lược đồ schema '{schema_name}' trong hợp đồng.")
    validator = Draft202012Validator(schemas[schema_name], registry=registry)
    validator.validate(instance)


def _string_values(value: Any) -> Iterator[str]:
    """Duyệt đệ quy mọi chuỗi trong bản ghi để kiểm tra đường dẫn tuyệt đối."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _string_values(child)


def test_all_examples_valid_against_schemas() -> None:
    """FR-011, FR-018, FR-019, AC-3: mọi ví dụ JSON hợp đồng hợp schema tương ứng."""
    example_mapping = (
        ("checkpoint-meta.final.json", "checkpoint-meta.schema.json"),
        ("progress-snapshot.running.json", "progress-snapshot.schema.json"),
        ("progress-snapshot.starting.json", "progress-snapshot.schema.json"),
        ("run-manifest.done.json", "run-manifest.schema.json"),
        ("run-manifest.error.json", "run-manifest.schema.json"),
        ("train-benchmark.example.json", "train-benchmark.schema.json"),
        ("train-config.default.json", "train-config.schema.json"),
        ("train-config.smoke.json", "train-config.schema.json"),
    )

    for example_name, schema_name in example_mapping:
        example_path = _CONTRACTS_DIR / "examples" / example_name
        assert example_path.is_file(), f"Tệp ví dụ không tồn tại: {example_path}"
        data = _load_json(example_path)
        _assert_valid(data, schema_name)


def test_all_contract_examples_are_listed() -> None:
    """FR-011, FR-019, AC-3: đảm bảo không bỏ sót tệp ví dụ JSON nào trong thư mục examples."""
    actual_examples = {
        path.name for path in (_CONTRACTS_DIR / "examples").glob("*.json")
    }
    registered_examples = {
        "checkpoint-meta.final.json",
        "progress-snapshot.running.json",
        "progress-snapshot.starting.json",
        "run-manifest.done.json",
        "run-manifest.error.json",
        "train-benchmark.example.json",
        "train-config.default.json",
        "train-config.smoke.json",
    }
    assert registered_examples == actual_examples, (
        f"Danh sách tệp ví dụ không khớp: thừa/thiếu {actual_examples ^ registered_examples}"
    )


def test_train_config_default_equals_packaged_yaml() -> None:
    """FR-018, FR-019, AC-3: cấu hình mặc định sau phân giải hợp train-config.schema.json."""
    default_config = TrainConfig.load()
    config_dict = default_config.to_dict()

    _assert_valid(config_dict, "train-config.schema.json")

    # So sánh nội dung logic cơ bản với bản mẫu train-config.default.json
    example_default = _load_json(_CONTRACTS_DIR / "examples" / "train-config.default.json")
    assert config_dict["schema_version"] == example_default["schema_version"]
    assert config_dict["stage"] == example_default["stage"]
    assert config_dict["seed"] == example_default["seed"]
    assert config_dict["ppo"]["learning_rate"] == example_default["ppo"]["learning_rate"]
    assert (
        config_dict["schedule"]["total_timesteps"]
        == example_default["schedule"]["total_timesteps"]
    )
    assert config_dict["schedule"]["batch_size"] == example_default["schedule"]["batch_size"]
    assert config_dict["ui"]["host"] == example_default["ui"]["host"]


def test_benchmark_example_valid() -> None:
    """FR-023, AC-3: ví dụ báo cáo benchmark hợp train-benchmark.schema.json."""
    benchmark_example_path = _CONTRACTS_DIR / "examples" / "train-benchmark.example.json"
    benchmark_data = _load_json(benchmark_example_path)

    _assert_valid(benchmark_data, "train-benchmark.schema.json")

    assert benchmark_data["schema_version"] == "1.0.0"
    assert benchmark_data["repeats"] >= 5
    assert "ratio_median" in benchmark_data
    assert "passed" in benchmark_data
    assert "ui_off" in benchmark_data
    assert "ui_on" in benchmark_data
    assert "ui_cost" in benchmark_data
    assert "view3d" in benchmark_data
    assert len(benchmark_data["ui_off"]["env_steps_per_second"]) == benchmark_data["repeats"]
    assert len(benchmark_data["ui_on"]["env_steps_per_second"]) == benchmark_data["repeats"]


def test_contract_examples_have_no_absolute_paths() -> None:
    """INV-001, FR-011, FR-019: mọi tệp ví dụ hợp đồng không chứa đường dẫn tuyệt đối của máy."""
    for example_file in sorted((_CONTRACTS_DIR / "examples").glob("*.json")):
        data = _load_json(example_file)
        for text in _string_values(data):
            assert not Path(text).is_absolute() and not PureWindowsPath(text).is_absolute(), (
                f"Phát hiện đường dẫn tuyệt đối '{text}' trong tệp ví dụ {example_file.name}"
            )
