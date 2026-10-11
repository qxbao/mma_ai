"""Kiểm hợp đồng (contract) môi trường nền tảng, AC-5."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).parents[2]
CONTRACT_DIR = PROJECT_ROOT / "specs/006-cross-platform-support/contracts"
EXAMPLES_DIR = CONTRACT_DIR / "examples"


def test_ac_5_examples_match_schema() -> None:
    """AC-5: bốn ví dụ nền tảng phải khớp lược đồ (schema) đã công bố."""
    schema = json.loads((CONTRACT_DIR / "check-env-report.schema.json").read_text())
    validator = Draft202012Validator(schema)
    examples = sorted(EXAMPLES_DIR.glob("check-env-report.*.json"))

    assert len(examples) == 4
    for example_path in examples:
        report = json.loads(example_path.read_text())
        errors = list(validator.iter_errors(report))
        assert not errors, f"{example_path.name}: {errors}"


def test_ac_5_negative_cases_rejected() -> None:
    """AC-5: lược đồ phải từ chối báo cáo thiếu trường bắt buộc và sai kiểu."""
    schema = json.loads((CONTRACT_DIR / "check-env-report.schema.json").read_text())
    validator = Draft202012Validator(schema)
    valid_report: dict[str, Any] = json.loads(
        (EXAMPLES_DIR / "check-env-report.linux-cuda.json").read_text()
    )
    missing_overall = {key: value for key, value in valid_report.items() if key != "overall"}
    invalid_kind = json.loads(json.dumps(valid_report))
    invalid_kind["os"]["kind"] = "plan9"

    assert list(validator.iter_errors(missing_overall))
    assert list(validator.iter_errors(invalid_kind))
