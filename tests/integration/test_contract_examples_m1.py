"""Kiểm thử hợp đồng bản ghi M1 cho môi trường khuỷu tay."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path, PureWindowsPath
from typing import Any, cast

import numpy as np
import pytest

pytest.importorskip("jsonschema", reason="Cần jsonschema để xác thực hợp đồng JSON Schema.")

from jsonschema import Draft202012Validator
from referencing import Registry, Resource  # type: ignore[import-not-found]

from mma_ai.environment.env_config import ElbowEnvConfig
from mma_ai.environment.single_agent import ElbowReachEnv
from mma_ai.environment.targets import TargetGenerator

_CONTRACTS_DIR = (
    Path(__file__).resolve().parents[2] / "specs" / "002-elbow-muscle-env" / "contracts"
)


def _load_json(path: Path) -> dict[str, Any]:
    """Nạp một bản ghi JSON hợp đồng."""
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _schema_registry() -> tuple[Registry, dict[str, dict[str, Any]]]:
    """Nạp mọi schema vào một registry để các $ref dùng chung một định danh."""
    schemas = {
        path.name: _load_json(path)
        for path in sorted(_CONTRACTS_DIR.glob("*.schema.json"))
    }
    resources = [
        (schema["$id"], Resource.from_contents(schema))
        for schema in schemas.values()
    ]
    return Registry().with_resources(resources), schemas


def _assert_valid(instance: dict[str, Any], schema_name: str) -> None:
    """Xác thực một bản ghi bằng JSON Schema draft 2020-12 đã đăng ký."""
    registry, schemas = _schema_registry()
    Draft202012Validator(schemas[schema_name], registry=registry).validate(instance)


def test_all_examples_valid_against_schemas() -> None:
    """FR-011, FR-012, FR-013, FR-014: mọi ví dụ hợp đồng hợp schema tương ứng."""
    examples = (
        ("env-config.default.json", "env-config.schema.json"),
        ("model-record.myoelbow.json", "model-record.schema.json"),
        ("reset-info.test-split.json", "reset-info.schema.json"),
        ("step-info.reached.json", "step-info.schema.json"),
        ("step-info.running.json", "step-info.schema.json"),
        ("step-info.truncated.json", "step-info.schema.json"),
        ("target-set.small.json", "target-set.schema.json"),
    )

    for example_name, schema_name in examples:
        _assert_valid(_load_json(_CONTRACTS_DIR / "examples" / example_name), schema_name)


def test_all_contract_examples_are_listed() -> None:
    """FR-011, FR-012, FR-013, FR-014: không ví dụ JSON nào bị bỏ qua khi thêm mới."""
    actual_examples = {
        path.name for path in (_CONTRACTS_DIR / "examples").glob("*.json")
    }
    registered_examples = {
        "env-config.default.json",
        "model-record.myoelbow.json",
        "reset-info.test-split.json",
        "step-info.reached.json",
        "step-info.running.json",
        "step-info.truncated.json",
        "target-set.small.json",
    }

    assert registered_examples == actual_examples


def test_model_record_real_output_valid() -> None:
    """FR-013, API-002, AC-1: bản ghi mô hình thật hợp model-record.schema.json."""
    env = ElbowReachEnv()

    _assert_valid(env.model_record(), "model-record.schema.json")


def test_target_set_real_output_valid() -> None:
    """FR-011, API-002, AC-3: tập mục tiêu thật hợp target-set.schema.json."""
    env = ElbowReachEnv()
    target_sets = TargetGenerator(env.model, env.cfg).generate(seed=217)

    _assert_valid(target_sets.to_dict(), "target-set.schema.json")


def test_reset_and_step_info_real_output_valid() -> None:
    """FR-012, API-002, AC-1: info thật của reset và step hợp schema."""
    env = ElbowReachEnv()
    _, reset_info = env.reset(seed=217)
    _, _, _, _, step_info = env.step(np.zeros(6, dtype=np.float32))

    _assert_valid(reset_info, "reset-info.schema.json")
    _assert_valid(step_info, "step-info.schema.json")


def test_env_config_default_valid() -> None:
    """FR-014, API-002: cấu hình đóng gói đã phân giải hợp env-config.schema.json."""
    _assert_valid(ElbowEnvConfig.load().to_dict(), "env-config.schema.json")


def _string_values(value: Any) -> Iterator[str]:
    """Duyệt chuỗi lồng nhau trong bản ghi JSON để phát hiện đường dẫn tuyệt đối."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _string_values(child)


def test_records_have_no_absolute_paths() -> None:
    """FR-011, FR-012, FR-013, FR-014: bản ghi công khai không lộ đường dẫn tuyệt đối."""
    env = ElbowReachEnv()
    _, reset_info = env.reset(seed=217)
    _, _, _, _, step_info = env.step(np.zeros(6, dtype=np.float32))
    records = (
        env.model_record(),
        TargetGenerator(env.model, env.cfg).generate(seed=217).to_dict(),
        reset_info,
        step_info,
        ElbowEnvConfig.load().to_dict(),
    )

    for record in records:
        assert all(
            not Path(text).is_absolute() and not PureWindowsPath(text).is_absolute()
            for text in _string_values(record)
        )
