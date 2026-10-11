"""Kiểm thử tích hợp các ví dụ hợp đồng (contract examples) cho replay và demo 3D (US4/FR-007).

Hiện thực và bảo vệ các yêu cầu:
- US4: Episode lưu đủ thông tin để phát lại đúng mô hình.
- FR-007: Định dạng episode có khuôn máy đọc được, hợp chuẩn JSON Schema.
- FR-015: Hợp đồng cho tiến trình replay độc lập.
- INV-003: Bất biến tự đủ của episode, không bỏ trường, không NaN/Infinity.
- NFR-REL-001: Độ tin cậy số học của episode và bản ghi tóm tắt.
- AC-1: Bản ghi episode hợp lệ phát lại trơn tru.
- AC-4: Nhận diện lệch mô hình qua mã băm XML và cấu trúc cơ.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterator
from pathlib import Path, PureWindowsPath
from typing import Any, cast

import pytest

pytest.importorskip("jsonschema", reason="Cần jsonschema để xác thực hợp đồng JSON Schema.")

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


def _get_contracts_dir() -> Path:
    """Trả về thư mục hợp đồng (contracts directory) của feature 005."""
    return (
        Path(__file__).resolve().parents[2]
        / "specs"
        / "005-replay-3d-muscle-demo"
        / "contracts"
    )


def _load_json(path: Path) -> dict[str, Any]:
    """Nạp một bản ghi JSON từ đĩa."""
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _schema_registry() -> tuple[Registry, dict[str, dict[str, Any]]]:
    """Nạp toàn bộ schema vào Registry dùng chung để phân giải tham chiếu chéo ($ref)."""
    contracts_dir = _get_contracts_dir()
    schemas = {
        path.name: _load_json(path)
        for path in sorted(contracts_dir.glob("*.schema.json"))
    }
    resources = [
        (schema["$id"], Resource.from_contents(schema))
        for schema in schemas.values()
        if "$id" in schema
    ]
    return Registry().with_resources(resources), schemas


def _assert_valid(instance: dict[str, Any], schema_name: str) -> None:
    """Xác thực bản ghi dữ liệu bằng JSON Schema draft 2020-12."""
    registry, schemas = _schema_registry()
    if schema_name not in schemas:
        raise KeyError(f"Không tìm thấy lược đồ schema '{schema_name}' trong hợp đồng.")
    validator = Draft202012Validator(schemas[schema_name], registry=registry)
    validator.validate(instance)


def _string_values(value: Any) -> Iterator[str]:
    """Duyệt đệ quy mọi chuỗi ký tự trong bản ghi JSON."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _string_values(child)


def _check_finite_recursive(value: Any, locator: str) -> None:
    """Kiểm tra đệ quy mọi giá trị số thực hữu hạn (finite numbers)."""
    if isinstance(value, float):
        assert math.isfinite(value), (
            f"NFR-REL-001 / INV-003 vi phạm: phát hiện số không hữu hạn '{value}' tại {locator}"
        )
    elif isinstance(value, dict):
        for k, child in value.items():
            _check_finite_recursive(child, f"{locator}.{k}")
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            _check_finite_recursive(child, f"{locator}[{idx}]")


def test_examples_match_schemas() -> None:
    """US4, FR-007, FR-015, INV-003, NFR-REL-001, AC-1, AC-4: Ví dụ mẫu hợp schema."""
    contracts_dir = _get_contracts_dir()
    examples_dir = contracts_dir / "examples"

    example_mapping = (
        ("episode.from-checkpoint-reached.json", "episode.schema.json"),
        ("episode.minimal-null-source.json", "episode.schema.json"),
        ("replay-config.default.json", "replay-config.schema.json"),
        ("replay-summary.demo-saved.json", "replay-summary.schema.json"),
        ("replay-summary.episode-match.json", "replay-summary.schema.json"),
        ("replay-summary.model-mismatch-allowed.json", "replay-summary.schema.json"),
    )

    for example_file, schema_file in example_mapping:
        path = examples_dir / example_file
        assert path.is_file(), f"Tệp ví dụ mẫu không tồn tại: {path}"
        data = _load_json(path)
        _assert_valid(data, schema_file)


def test_all_contract_examples_are_listed() -> None:
    """US4, FR-007, AC-1: Đảm bảo không bỏ sót tệp ví dụ JSON nào trong contracts/examples/."""
    contracts_dir = _get_contracts_dir()
    examples_dir = contracts_dir / "examples"

    actual_examples = {path.name for path in examples_dir.glob("*.json")}
    registered_examples = {
        "episode.from-checkpoint-reached.json",
        "episode.minimal-null-source.json",
        "replay-config.default.json",
        "replay-summary.demo-saved.json",
        "replay-summary.episode-match.json",
        "replay-summary.model-mismatch-allowed.json",
    }
    assert actual_examples == registered_examples, (
        f"Danh sách tệp ví dụ không khớp: thừa={actual_examples - registered_examples}, "
        f"thiếu={registered_examples - actual_examples}"
    )


def test_no_nonfinite_values() -> None:
    """US4, FR-007, INV-003, NFR-REL-001, AC-1: Bản ghi ví dụ không chứa hằng số NaN/Infinity."""
    contracts_dir = _get_contracts_dir()
    examples_dir = contracts_dir / "examples"

    def _reject_constant(c: str) -> None:
        raise ValueError(f"INV-003 vi phạm: phát hiện hằng số JSON không chuẩn '{c}'")

    for path in sorted(examples_dir.glob("*.json")):
        # 1. Từ chối ngay khi phân tích cú pháp JSON nếu gặp hằng số NaN, Infinity
        raw_text = path.read_text(encoding="utf-8")
        data = json.loads(raw_text, parse_constant=_reject_constant)

        # 2. Kiểm tra đệ quy các trường số thực
        _check_finite_recursive(data, path.name)


def test_records_have_no_absolute_paths() -> None:
    """US4, NFR-REL-001, Constitution VI: Bản ghi ví dụ hợp đồng không chứa đường dẫn tuyệt đối."""
    contracts_dir = _get_contracts_dir()
    examples_dir = contracts_dir / "examples"

    for path in sorted(examples_dir.glob("*.json")):
        data = _load_json(path)
        for text in _string_values(data):
            # Kiểm tra cả định dạng đường dẫn POSIX và Windows
            assert not Path(text).is_absolute(), (
                f"Constitution VI: đường dẫn tuyệt đối POSIX '{text}' trong {path.name}"
            )
            assert not PureWindowsPath(text).is_absolute(), (
                f"Constitution VI: đường dẫn tuyệt đối Windows '{text}' trong {path.name}"
            )


def test_episode_examples_satisfy_domain_invariants() -> None:
    """US4, FR-007, INV-003, AC-1, AC-4: Các bản ghi episode mẫu thoả mãn bất biến nghiệp vụ."""
    contracts_dir = _get_contracts_dir()
    examples_dir = contracts_dir / "examples"
    episode_files = ("episode.from-checkpoint-reached.json", "episode.minimal-null-source.json")

    for ep_name in episode_files:
        data = _load_json(examples_dir / ep_name)

        # 1. Bất biến phiên bản định dạng
        assert data.get("schema_version") == "1.0.0"

        # 2. Bất biến quan hệ giữa số khung và số hành động: n_actions == len(frames) - 1
        frames = data["frames"]
        n_actions = data["outcome"]["n_actions"]
        assert n_actions == len(frames) - 1, (
            f"INV-003: n_actions ({n_actions}) != len(frames) - 1 ({len(frames) - 1}) tại {ep_name}"
        )

        # 3. Khung 0 không có hành động (excitation is None)
        assert frames[0]["excitation"] is None, (
            f"INV-003 vi phạm tại {ep_name}: khung 0 phải có excitation là null"
        )

        # 4. Các khung tiếp theo (>= 1) phải có excitation 6 cơ trong khoảng [0, 1]
        for idx in range(1, len(frames)):
            exc = frames[idx]["excitation"]
            assert exc is not None and len(exc) == 6, (
                f"INV-003 vi phạm tại {ep_name}: khung {idx} phải có excitation gồm 6 phần tử"
            )
            assert all(0.0 <= val <= 1.0 for val in exc), (
                f"INV-003 vi phạm tại {ep_name}: excitation ngoài đoạn [0, 1] ở khung {idx}"
            )

        # 5. Kích thước trạng thái khớp với mô hình: qpos == nq, qvel == nv
        nq = data["model"]["nq"]
        nv = data["model"]["nv"]
        for idx, f in enumerate(frames):
            assert len(f["qpos"]) == nq, (
                f"INV-003: độ dài qpos ({len(f['qpos'])}) != nq ({nq}) ở khung {idx}"
            )
            assert len(f["qvel"]) == nv, (
                f"INV-003: độ dài qvel ({len(f['qvel'])}) != nv ({nv}) ở khung {idx}"
            )
            assert len(f["activation"]) == 6, (
                f"INV-003: activation phải có đúng 6 cơ ở khung {idx}"
            )
            assert all(0.0 <= a <= 1.0 for a in f["activation"]), (
                f"INV-003: activation ngoài đoạn [0, 1] ở khung {idx}"
            )

        # 6. Dòng thời gian đơn điệu tăng (monotonic increasing time)
        for idx in range(len(frames) - 1):
            assert frames[idx]["t_s"] < frames[idx + 1]["t_s"], (
                f"INV-003: t_s không tăng giữa khung {idx} và {idx + 1} tại {ep_name}"
            )

        # 7. Danh sách 6 tên cơ phân biệt duy nhất
        muscle_names = data["model"]["muscle_names"]
        assert len(muscle_names) == 6
        assert len(set(muscle_names)) == 6

        # 8. Mã băm SHA-256 XML gồm đúng 64 ký tự hex
        sha256 = data["model"]["sha256"]
        assert len(sha256) == 64 and all(c in "0123456789abcdef" for c in sha256)
