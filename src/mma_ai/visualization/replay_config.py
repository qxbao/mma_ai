"""Mô-đun quản lý cấu hình phát lại và demo 3D (mma_ai.visualization.replay_config).

Cung cấp các lớp dữ liệu cấu hình bất biến và phương thức nạp load() theo chuẩn hợp đồng:
- FR-006: Hỗ trợ cấu hình tốc độ phát lại (playback speed) và chế độ lặp (loop).
- FR-017: Quản lý cấu hình tập trung từ tệp YAML duy nhất và kiểm tra tính hợp lệ (validation).
- API-VIS-0001: Hàm ReplayConfig.load(path=None, overrides=None) -> ReplayConfig.
"""

from __future__ import annotations

import copy
import importlib.resources
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from mma_ai.visualization.errors import ReplayConfigError

# Bản đồ ánh xạ từ cờ dòng lệnh phẳng sang phần cấu hình tương ứng
_SECTION_MAP: dict[str, str] = {
    "speed": "playback",
    "loop": "playback",
    "display_hz": "playback",
    "hold_after_end_s": "playback",
    "split": "demo",
    "target_index": "demo",
    "seed": "demo",
    "decimals": "hud",
    "bar_width": "hud",
    "radius_m": "target_marker",
    "rgba": "target_marker",
}


@dataclass(frozen=True)
class PlaybackConfig:
    """Cấu hình phát lại mô phỏng (playback settings)."""

    speed: float
    loop: bool
    display_hz: int
    hold_after_end_s: float | None


@dataclass(frozen=True)
class DemoConfig:
    """Cấu hình phiên demo chính sách khuỷu tay (demo settings)."""

    split: Literal["train", "test"] | str
    target_index: int
    seed: int


@dataclass(frozen=True)
class HudConfig:
    """Cấu hình hiển thị thông số HUD (HUD settings)."""

    decimals: int
    bar_width: int


@dataclass(frozen=True)
class TargetMarkerConfig:
    """Cấu hình điểm đánh dấu mục tiêu 3D (target marker settings)."""

    radius_m: float
    rgba: tuple[float, float, float, float]


@dataclass(frozen=True)
class ReplayConfig:
    """Cấu hình phát lại và demo toàn diện (FR-006, FR-017, API-VIS-0001)."""

    playback: PlaybackConfig
    demo: DemoConfig
    hud: HudConfig
    target_marker: TargetMarkerConfig

    def to_dict(self) -> dict[str, Any]:
        """Xuất cấu hình thành từ điển (dictionary) tương thích với lược đồ JSON Schema."""
        return {
            "playback": {
                "speed": self.playback.speed,
                "loop": self.playback.loop,
                "display_hz": self.playback.display_hz,
                "hold_after_end_s": self.playback.hold_after_end_s,
            },
            "demo": {
                "split": self.demo.split,
                "target_index": self.demo.target_index,
                "seed": self.demo.seed,
            },
            "hud": {
                "decimals": self.hud.decimals,
                "bar_width": self.hud.bar_width,
            },
            "target_marker": {
                "radius_m": self.target_marker.radius_m,
                "rgba": list(self.target_marker.rgba),
            },
        }

    @classmethod
    def load(
        cls,
        path: str | Path | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> ReplayConfig:
        """Nạp cấu hình phát lại từ tệp YAML mặc định hoặc chỉ định (API-VIS-0001)."""
        content = _read_config_content(path)

        try:
            raw_data = yaml.safe_load(content)
        except Exception as err:
            target_name = str(path) if path is not None else "replay.yaml mặc định"
            raise ReplayConfigError(
                f"Cú pháp YAML trong tệp cấu hình '{target_name}' không hợp lệ: {err}"
            ) from err

        if not isinstance(raw_data, dict):
            target_name = str(path) if path is not None else "replay.yaml mặc định"
            raw_type = type(raw_data).__name__
            raise ReplayConfigError(
                f"Nội dung cấu hình '{target_name}' phải là một mapping/dict, nhận: {raw_type}"
            )

        merged_data = _apply_overrides(raw_data, overrides)
        return _validate_and_build(merged_data)


def _read_config_content(path: str | Path | None) -> str:
    """Đọc nội dung văn bản cấu hình từ đường dẫn hoặc gói đóng sẵn."""
    if path is not None:
        cfg_path = Path(path)
        if not cfg_path.is_file():
            raise ReplayConfigError(
                f"Tệp cấu hình không tồn tại hoặc không phải là tệp hợp lệ: {path}"
            )
        try:
            return cfg_path.read_text(encoding="utf-8")
        except Exception as err:
            raise ReplayConfigError(f"Không thể đọc tệp cấu hình tại {path}: {err}") from err

    # Nạp tệp replay.yaml đóng gói sẵn trong package
    try:
        packaged_ref = importlib.resources.files("mma_ai.visualization").joinpath("replay.yaml")
        with importlib.resources.as_file(packaged_ref) as config_file:
            if not config_file.is_file():
                raise FileNotFoundError(f"Không tìm thấy tệp {config_file}")
            return config_file.read_text(encoding="utf-8")
    except Exception as err:
        fallback_path = Path(__file__).resolve().parent / "replay.yaml"
        if fallback_path.is_file():
            return fallback_path.read_text(encoding="utf-8")
        raise ReplayConfigError(
            f"Không thể nạp cấu hình mặc định từ gói mma_ai.visualization: {err}"
        ) from err


def _apply_overrides(
    raw_data: dict[str, Any],
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    """Áp dụng các giá trị ghi đè (overrides) từ tham số dòng lệnh vào dữ liệu cấu hình."""
    data = copy.deepcopy(raw_data)
    if overrides is None:
        return data

    if not isinstance(overrides, dict):
        raise ReplayConfigError("Giá trị overrides phải là một từ điển (dictionary).")

    for key, val in overrides.items():
        if key in _SECTION_MAP:
            section = _SECTION_MAP[key]
            if section not in data or not isinstance(data[section], dict):
                data[section] = {}
            data[section][key] = val
        elif "." in key:
            section, prop = key.split(".", 1)
            if section in ("playback", "demo", "hud", "target_marker") and isinstance(
                data.get(section), dict
            ):
                data[section][prop] = val
            else:
                raise ReplayConfigError(f"Khoá không xác định trong overrides: '{key}'.")
        elif key in ("playback", "demo", "hud", "target_marker"):
            if not isinstance(val, dict):
                raise ReplayConfigError(
                    f"Giá trị phần '{key}' trong overrides phải là một mapping/dict."
                )
            if key not in data or not isinstance(data[key], dict):
                data[key] = {}
            for subkey, subval in val.items():
                data[key][subkey] = subval
        else:
            raise ReplayConfigError(f"Khoá không xác định trong overrides: '{key}'.")

    return data


def _validate_playback(data: dict[str, Any]) -> PlaybackConfig:
    """Kiểm tra tính hợp lệ của phân đoạn cấu hình phát lại playback (FR-006, FR-017)."""
    allowed_keys = {"speed", "loop", "display_hz", "hold_after_end_s"}
    for k in allowed_keys:
        if k not in data:
            raise ReplayConfigError(f"Thiếu khoá bắt buộc trong 'playback': '{k}'.")
    for k in data:
        if k not in allowed_keys:
            raise ReplayConfigError(f"Khoá thừa không hợp lệ trong 'playback': '{k}'.")

    speed = data["speed"]
    # Bắt buộc loại trừ bool do bool là lớp con của int trong Python
    if isinstance(speed, bool) or not isinstance(speed, (int, float)) or speed <= 0:
        raise ReplayConfigError(
            f"Giá trị 'playback.speed' phải là số thực lớn hơn 0, nhận được: {speed}"
        )

    loop = data["loop"]
    if not isinstance(loop, bool):
        raise ReplayConfigError(
            f"Giá trị 'playback.loop' phải là boolean (True/False), nhận được: {loop}"
        )

    display_hz = data["display_hz"]
    if isinstance(display_hz, bool) or type(display_hz) is not int or not (1 <= display_hz <= 240):
        raise ReplayConfigError(
            f"Giá trị 'playback.display_hz' phải trong khoảng [1, 240], nhận được: {display_hz}"
        )

    hold_after_end_s = data["hold_after_end_s"]
    if hold_after_end_s is not None:
        if (
            isinstance(hold_after_end_s, bool)
            or not isinstance(hold_after_end_s, (int, float))
            or hold_after_end_s < 0
        ):
            raise ReplayConfigError(
                f"Giá trị 'playback.hold_after_end_s' phải >= 0 hoặc null, nhận: {hold_after_end_s}"
            )
        hold_val = float(hold_after_end_s)
    else:
        hold_val = None

    return PlaybackConfig(
        speed=float(speed),
        loop=loop,
        display_hz=display_hz,
        hold_after_end_s=hold_val,
    )


def _validate_demo(data: dict[str, Any]) -> DemoConfig:
    """Kiểm tra tính hợp lệ của phân đoạn cấu hình demo (FR-017)."""
    allowed_keys = {"split", "target_index", "seed"}
    for k in allowed_keys:
        if k not in data:
            raise ReplayConfigError(f"Thiếu khoá bắt buộc trong 'demo': '{k}'.")
    for k in data:
        if k not in allowed_keys:
            raise ReplayConfigError(f"Khoá thừa không hợp lệ trong 'demo': '{k}'.")

    split = data["split"]
    if split not in ("train", "test"):
        raise ReplayConfigError(
            f"Giá trị 'demo.split' phải là 'train' hoặc 'test', nhận được: {split}"
        )

    target_index = data["target_index"]
    if isinstance(target_index, bool) or type(target_index) is not int or target_index < 0:
        raise ReplayConfigError(
            f"Giá trị 'demo.target_index' phải là số nguyên >= 0, nhận được: {target_index}"
        )

    seed = data["seed"]
    if isinstance(seed, bool) or type(seed) is not int or seed < 0:
        raise ReplayConfigError(
            f"Giá trị 'demo.seed' phải là số nguyên không âm (>= 0), nhận được: {seed}"
        )

    return DemoConfig(
        split=split,
        target_index=target_index,
        seed=seed,
    )


def _validate_hud(data: dict[str, Any]) -> HudConfig:
    """Kiểm tra tính hợp lệ của phân đoạn cấu hình HUD (FR-017)."""
    allowed_keys = {"decimals", "bar_width"}
    for k in allowed_keys:
        if k not in data:
            raise ReplayConfigError(f"Thiếu khoá bắt buộc trong 'hud': '{k}'.")
    for k in data:
        if k not in allowed_keys:
            raise ReplayConfigError(f"Khoá thừa không hợp lệ trong 'hud': '{k}'.")

    decimals = data["decimals"]
    if isinstance(decimals, bool) or type(decimals) is not int or not (0 <= decimals <= 6):
        raise ReplayConfigError(
            f"Giá trị 'hud.decimals' phải là số nguyên trong khoảng [0, 6], nhận được: {decimals}"
        )

    bar_width = data["bar_width"]
    if isinstance(bar_width, bool) or type(bar_width) is not int or not (0 <= bar_width <= 40):
        raise ReplayConfigError(
            f"Giá trị 'hud.bar_width' phải là số nguyên trong [0, 40], nhận được: {bar_width}"
        )

    return HudConfig(
        decimals=decimals,
        bar_width=bar_width,
    )


def _validate_target_marker(data: dict[str, Any]) -> TargetMarkerConfig:
    """Kiểm tra tính hợp lệ của phân đoạn điểm đánh dấu mục tiêu (FR-017)."""
    allowed_keys = {"radius_m", "rgba"}
    for k in allowed_keys:
        if k not in data:
            raise ReplayConfigError(f"Thiếu khoá bắt buộc trong 'target_marker': '{k}'.")
    for k in data:
        if k not in allowed_keys:
            raise ReplayConfigError(f"Khoá thừa không hợp lệ trong 'target_marker': '{k}'.")

    radius_m = data["radius_m"]
    if isinstance(radius_m, bool) or not isinstance(radius_m, (int, float)) or radius_m <= 0:
        raise ReplayConfigError(
            f"Giá trị 'target_marker.radius_m' phải là số thực lớn hơn 0, nhận được: {radius_m}"
        )

    rgba = data["rgba"]
    is_valid_rgba = (
        isinstance(rgba, (list, tuple))
        and len(rgba) == 4
        and all(
            not isinstance(c, bool) and isinstance(c, (int, float)) and 0.0 <= c <= 1.0
            for c in rgba
        )
    )
    if not is_valid_rgba:
        raise ReplayConfigError(
            f"Giá trị 'target_marker.rgba' phải là 4 số thực trong [0, 1], nhận được: {rgba}"
        )

    return TargetMarkerConfig(
        radius_m=float(radius_m),
        rgba=(float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3])),
    )


def _validate_and_build(data: dict[str, Any]) -> ReplayConfig:
    """Xác thực toàn bộ cấu trúc và xây dựng đối tượng ReplayConfig bất biến."""
    required_sections = ("playback", "demo", "hud", "target_marker")
    for sec in required_sections:
        if sec not in data:
            raise ReplayConfigError(f"Thiếu phần cấu hình bắt buộc: '{sec}'.")
        if not isinstance(data[sec], dict):
            sec_type = type(data[sec]).__name__
            raise ReplayConfigError(
                f"Phần cấu hình '{sec}' phải là một mapping/dict, nhận được: {sec_type}"
            )

    for key in data:
        if key not in required_sections:
            raise ReplayConfigError(f"Cấu hình chứa khoá thừa không hợp lệ: '{key}'.")

    playback = _validate_playback(data["playback"])
    demo = _validate_demo(data["demo"])
    hud = _validate_hud(data["hud"])
    target_marker = _validate_target_marker(data["target_marker"])

    return ReplayConfig(
        playback=playback,
        demo=demo,
        hud=hud,
        target_marker=target_marker,
    )


__all__: list[str] = [
    "DemoConfig",
    "HudConfig",
    "PlaybackConfig",
    "ReplayConfig",
    "TargetMarkerConfig",
]
