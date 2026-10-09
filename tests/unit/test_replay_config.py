"""Kiểm thử đơn vị cho cấu hình phát lại ReplayConfig (mma_ai.visualization.replay_config).

Chứng minh các yêu cầu, bất biến và hợp đồng:
- FR-006: Cấu hình hệ số tốc độ (playback speed), chế độ lặp (loop) và giữ khung cuối.
- FR-017: Cấu hình tập trung tại tệp YAML duy nhất; phát hiện và từ chối giá trị sai.
- API-VIS-0001: Hàm nạp cấu hình ReplayConfig.load(path=None, overrides=None).
- AC-1: Khởi tạo cấu hình phát lại thời gian thực cho phiên MuJoCo Viewer.
- AC-5: Báo lỗi ReplayConfigError với mã thoát 2 khi cấu hình thiếu khoá hoặc sai giá trị.
- INV-004: Thoát mã lỗi khác 0 (exit code 2) khi cấu hình không hợp lệ.
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from mma_ai.visualization.errors import ReplayConfigError
from mma_ai.visualization.replay_config import (
    DemoConfig,
    HudConfig,
    PlaybackConfig,
    ReplayConfig,
    TargetMarkerConfig,
)


def test_defaults_load() -> None:
    """FR-006, FR-017, API-VIS-0001, AC-1: Nạp cấu hình mặc định đóng gói từ replay.yaml."""
    cfg = ReplayConfig.load()
    assert isinstance(cfg, ReplayConfig)

    # Kiểm tra cấu hình playback
    assert isinstance(cfg.playback, PlaybackConfig)
    assert cfg.playback.speed == 1.0
    assert cfg.playback.loop is False
    assert cfg.playback.display_hz == 60
    assert cfg.playback.hold_after_end_s is None

    # Kiểm tra cấu hình demo
    assert isinstance(cfg.demo, DemoConfig)
    assert cfg.demo.split == "test"
    assert cfg.demo.target_index == 0
    assert cfg.demo.seed == 12345

    # Kiểm tra cấu hình HUD
    assert isinstance(cfg.hud, HudConfig)
    assert cfg.hud.decimals == 3
    assert cfg.hud.bar_width == 10

    # Kiểm tra cấu hình target_marker
    assert isinstance(cfg.target_marker, TargetMarkerConfig)
    assert cfg.target_marker.radius_m == 0.02
    assert cfg.target_marker.rgba == (1.0, 0.2, 0.2, 0.6)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("override_key", "override_val", "expected_err_keyword"),
    [
        # playback.speed
        ("speed", 0.0, "speed"),
        ("speed", -1.0, "speed"),
        ("speed", "nhanh", "speed"),
        ("speed", True, "speed"),
        # playback.display_hz
        ("display_hz", 0, "display_hz"),
        ("display_hz", 241, "display_hz"),
        ("display_hz", -5, "display_hz"),
        ("display_hz", 60.5, "display_hz"),
        ("display_hz", True, "display_hz"),
        # playback.loop
        ("loop", "khong", "loop"),
        ("loop", 1, "loop"),
        # playback.hold_after_end_s
        ("hold_after_end_s", -0.5, "hold_after_end_s"),
        ("hold_after_end_s", "vo_han", "hold_after_end_s"),
        ("hold_after_end_s", True, "hold_after_end_s"),
        # demo.split
        ("split", "validation", "split"),
        ("split", 123, "split"),
        # demo.target_index
        ("target_index", -1, "target_index"),
        ("target_index", 1.5, "target_index"),
        ("target_index", True, "target_index"),
        # demo.seed
        ("seed", -10, "seed"),
        ("seed", 3.14, "seed"),
        ("seed", True, "seed"),
        # hud.decimals
        ("decimals", -1, "decimals"),
        ("decimals", 7, "decimals"),
        ("decimals", "ba", "decimals"),
        ("decimals", True, "decimals"),
        # hud.bar_width
        ("bar_width", -1, "bar_width"),
        ("bar_width", 41, "bar_width"),
        ("bar_width", 10.5, "bar_width"),
        ("bar_width", True, "bar_width"),
        # target_marker.radius_m
        ("radius_m", 0.0, "radius_m"),
        ("radius_m", -0.05, "radius_m"),
        ("radius_m", "nho", "radius_m"),
        ("radius_m", True, "radius_m"),
        # target_marker.rgba
        ("rgba", [1.0, 0.2, 0.2], "rgba"),
        ("rgba", [1.0, 0.2, 0.2, 0.6, 1.0], "rgba"),
        ("rgba", [1.5, 0.2, 0.2, 0.6], "rgba"),
        ("rgba", [-0.1, 0.2, 0.2, 0.6], "rgba"),
        ("rgba", [True, 0.2, 0.2, 0.6], "rgba"),
        ("rgba", "do", "rgba"),
    ],
)
def test_invalid_values_raise(
    override_key: str, override_val: Any, expected_err_keyword: str
) -> None:
    """FR-017, AC-5, INV-004: Báo lỗi ReplayConfigError khi cấu hình chứa giá trị không hợp lệ."""
    with pytest.raises(ReplayConfigError) as exc_info:
        ReplayConfig.load(overrides={override_key: override_val})

    err_msg = str(exc_info.value).lower()
    assert expected_err_keyword.lower() in err_msg
    assert exc_info.value.exit_code == 2


def test_missing_required_keys_raise(tmp_path: Path) -> None:
    """FR-017, AC-5, INV-004: Từ chối tệp cấu hình thiếu các phần hoặc khoá bắt buộc."""
    # Thiếu phần playback
    bad_cfg_file = tmp_path / "missing_playback.yaml"
    bad_cfg_file.write_text(
        "demo: {split: test, target_index: 0, seed: 1}\n"
        "hud: {decimals: 3, bar_width: 10}\n"
        "target_marker: {radius_m: 0.02, rgba: [1, 0, 0, 1]}\n",
        encoding="utf-8",
    )
    with pytest.raises(ReplayConfigError) as exc_info:
        ReplayConfig.load(path=bad_cfg_file)
    assert "playback" in str(exc_info.value).lower()

    # Thiếu khoá display_hz trong playback
    bad_cfg_file_2 = tmp_path / "missing_display_hz.yaml"
    bad_cfg_file_2.write_text(
        "playback: {speed: 1.0, loop: false, hold_after_end_s: null}\n"
        "demo: {split: test, target_index: 0, seed: 1}\n"
        "hud: {decimals: 3, bar_width: 10}\n"
        "target_marker: {radius_m: 0.02, rgba: [1, 0, 0, 1]}\n",
        encoding="utf-8",
    )
    with pytest.raises(ReplayConfigError) as exc_info_2:
        ReplayConfig.load(path=bad_cfg_file_2)
    assert "display_hz" in str(exc_info_2.value).lower()


def test_extra_keys_raise(tmp_path: Path) -> None:
    """FR-017, AC-5: Từ chối khoá thừa không được định nghĩa trong schema."""
    bad_cfg_file = tmp_path / "extra_keys.yaml"
    bad_cfg_file.write_text(
        "playback: {speed: 1.0, loop: false, display_hz: 60, hold_after_end_s: null}\n"
        "demo: {split: test, target_index: 0, seed: 1}\n"
        "hud: {decimals: 3, bar_width: 10}\n"
        "target_marker: {radius_m: 0.02, rgba: [1, 0, 0, 1]}\n"
        "extra_section: {foo: bar}\n",
        encoding="utf-8",
    )
    with pytest.raises(ReplayConfigError) as exc_info:
        ReplayConfig.load(path=bad_cfg_file)
    assert "extra_section" in str(exc_info.value).lower()


def test_overrides_apply_correctly() -> None:
    """FR-006, FR-017, API-VIS-0001: Ghi đè tham số cấu hình linh hoạt từ dòng lệnh (CLI flags)."""
    # 1. Ghi đè dạng phẳng (flat aliases)
    cfg1 = ReplayConfig.load(
        overrides={
            "speed": 2.5,
            "loop": True,
            "display_hz": 120,
            "hold_after_end_s": 5.0,
            "split": "train",
            "target_index": 3,
            "seed": 999,
            "decimals": 2,
            "bar_width": 20,
            "radius_m": 0.05,
            "rgba": [0.0, 1.0, 0.0, 0.8],
        }
    )
    assert cfg1.playback.speed == 2.5
    assert cfg1.playback.loop is True
    assert cfg1.playback.display_hz == 120
    assert cfg1.playback.hold_after_end_s == 5.0
    assert cfg1.demo.split == "train"
    assert cfg1.demo.target_index == 3
    assert cfg1.demo.seed == 999
    assert cfg1.hud.decimals == 2
    assert cfg1.hud.bar_width == 20
    assert cfg1.target_marker.radius_m == 0.05
    assert cfg1.target_marker.rgba == (0.0, 1.0, 0.0, 0.8)

    # 2. Ghi đè dạng lồng nhau (nested dict)
    cfg2 = ReplayConfig.load(
        overrides={
            "playback": {"speed": 0.5, "loop": True},
            "demo": {"split": "train"},
        }
    )
    assert cfg2.playback.speed == 0.5
    assert cfg2.playback.loop is True
    assert cfg2.playback.display_hz == 60
    assert cfg2.demo.split == "train"

    # 3. Ghi đè dạng chấm (dot notation)
    cfg3 = ReplayConfig.load(
        overrides={
            "playback.speed": 1.75,
            "demo.target_index": 2,
        }
    )
    assert cfg3.playback.speed == 1.75
    assert cfg3.demo.target_index == 2


def test_unknown_override_key_raises() -> None:
    """FR-017, AC-5: Ghi đè khoá lạ không tồn tại ném ReplayConfigError."""
    with pytest.raises(ReplayConfigError) as exc_info:
        ReplayConfig.load(overrides={"unknown_cli_flag": "val"})
    assert "unknown_cli_flag" in str(exc_info.value)


def test_nonexistent_file_raises(tmp_path: Path) -> None:
    """FR-017, AC-5: Tệp cấu hình không tồn tại ném ReplayConfigError."""
    nonexistent = tmp_path / "not_found.yaml"
    with pytest.raises(ReplayConfigError) as exc_info:
        ReplayConfig.load(path=nonexistent)
    assert str(nonexistent) in str(exc_info.value) or "không tồn tại" in str(exc_info.value).lower()


def test_malformed_yaml_raises(tmp_path: Path) -> None:
    """FR-017, AC-5: Tệp YAML hỏng cú pháp ném ReplayConfigError."""
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("playback: [unclosed list\n", encoding="utf-8")
    with pytest.raises(ReplayConfigError):
        ReplayConfig.load(path=bad_yaml)


def test_non_dict_yaml_raises(tmp_path: Path) -> None:
    """FR-017, AC-5: Tệp YAML không phải mapping/dictionary ném ReplayConfigError."""
    bad_yaml = tmp_path / "string_only.yaml"
    bad_yaml.write_text("just a string\n", encoding="utf-8")
    with pytest.raises(ReplayConfigError):
        ReplayConfig.load(path=bad_yaml)


def test_boundary_values() -> None:
    """FR-006, FR-017: Kiểm tra các giá trị biên hợp lệ (boundary values)."""
    cfg = ReplayConfig.load(
        overrides={
            "display_hz": 1,
            "decimals": 0,
            "bar_width": 0,
            "hold_after_end_s": 0.0,
            "target_index": 0,
            "seed": 0,
            "speed": 0.0001,
            "radius_m": 0.0001,
            "rgba": [0.0, 0.0, 0.0, 0.0],
        }
    )
    assert cfg.playback.display_hz == 1
    assert cfg.hud.decimals == 0
    assert cfg.hud.bar_width == 0
    assert cfg.playback.hold_after_end_s == 0.0
    assert cfg.demo.target_index == 0
    assert cfg.demo.seed == 0
    assert cfg.target_marker.rgba == (0.0, 0.0, 0.0, 0.0)

    cfg_max = ReplayConfig.load(
        overrides={
            "display_hz": 240,
            "decimals": 6,
            "bar_width": 40,
            "rgba": [1.0, 1.0, 1.0, 1.0],
        }
    )
    assert cfg_max.playback.display_hz == 240
    assert cfg_max.hud.decimals == 6
    assert cfg_max.hud.bar_width == 40
    assert cfg_max.target_marker.rgba == (1.0, 1.0, 1.0, 1.0)


def test_immutable_config() -> None:
    """Bất biến: Đối tượng ReplayConfig là bất biến (frozen dataclass)."""
    cfg = ReplayConfig.load()
    with pytest.raises(FrozenInstanceError):
        cfg.playback.speed = 2.0  # type: ignore[misc]


def test_to_dict_matches_schema() -> None:
    """FR-017: Phương thức to_dict() khớp chuẩn lược đồ JSON Schema của replay-config."""
    cfg = ReplayConfig.load()
    dict_repr = cfg.to_dict()

    schema_path = (
        Path(__file__).resolve().parents[2]
        / "specs"
        / "005-replay-3d-muscle-demo"
        / "contracts"
        / "replay-config.schema.json"
    )
    if schema_path.is_file():
        try:
            import jsonschema

            with schema_path.open("r", encoding="utf-8") as f:
                schema = json.load(f)
            jsonschema.validate(instance=dict_repr, schema=schema)
        except ImportError:
            pass
