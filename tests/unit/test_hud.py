"""Kiểm thử đơn vị cho mô-đun hiển thị HUD (mma_ai.visualization.hud).

Bao phủ các yêu cầu và bất biến:
- FR-005: Hiển thị 6 giá trị kích hoạt cơ (muscle activation) kèm tên cơ và thanh trực quan.
- FR-012: Hiển thị cảnh báo lệch mô hình (model mismatch warning) "MÔ HÌNH LỆCH" khi có.
- INV-006: Giá trị kích hoạt cơ làm tròn chỉ ở hiển thị, bảo toàn dữ liệu gốc.
- API-VIS-0012: Hợp đồng hàm hud_lines(activation, muscle_names, cfg, warning=None) -> list[str].
- AC-1, AC-2, AC-4: Các kịch bản chấp nhận hiển thị HUD trong phát lại và chạy demo.
"""

from __future__ import annotations

import numpy as np
import pytest

from mma_ai.visualization.hud import hud_lines
from mma_ai.visualization.replay_config import (
    DemoConfig,
    HudConfig,
    PlaybackConfig,
    ReplayConfig,
    TargetMarkerConfig,
)

_SIX_MUSCLES: list[str] = [
    "TRIlong",
    "TRIlat",
    "TRImed",
    "BIClong",
    "BICshort",
    "BRA",
]


def _make_dummy_replay_config(decimals: int = 3, bar_width: int = 10) -> ReplayConfig:
    """Tạo cấu hình phát lại giả lập phục vụ kiểm thử."""
    return ReplayConfig(
        playback=PlaybackConfig(
            speed=1.0,
            loop=False,
            display_hz=60,
            hold_after_end_s=None,
        ),
        demo=DemoConfig(
            split="test",
            target_index=0,
            seed=12345,
        ),
        hud=HudConfig(
            decimals=decimals,
            bar_width=bar_width,
        ),
        target_marker=TargetMarkerConfig(
            radius_m=0.02,
            rgba=(1.0, 0.2, 0.2, 0.6),
        ),
    )


def test_rounding_only_in_display() -> None:
    """Kiểm tra làm tròn chỉ áp dụng tại hiển thị và không biến đổi mảng gốc.

    Hiện thực kiểm chứng: FR-005, INV-006, API-VIS-0012, AC-2.
    """
    raw_activations = [0.123456, 0.654321, 0.999999, 0.000001, 0.500000, 0.777777]
    activations_snapshot = list(raw_activations)
    cfg = _make_dummy_replay_config(decimals=3, bar_width=10)

    lines = hud_lines(raw_activations, _SIX_MUSCLES, cfg)

    # 1. Dữ liệu gốc không bị biến đổi (INV-006)
    assert raw_activations == activations_snapshot

    # 2. Giá trị hiển thị được làm tròn đúng 3 chữ số thập phân
    assert len(lines) == 6
    assert "0.123" in lines[0]
    assert "0.654" in lines[1]
    assert "1.000" in lines[2]
    assert "0.000" in lines[3]
    assert "0.500" in lines[4]
    assert "0.778" in lines[5]

    # 3. Thử nghiệm với số chữ số làm tròn khác (decimals=2)
    cfg_2 = _make_dummy_replay_config(decimals=2, bar_width=10)
    lines_2 = hud_lines(raw_activations, _SIX_MUSCLES, cfg_2)
    assert "0.12" in lines_2[0]
    assert "0.65" in lines_2[1]


def test_hud_names_match_muscle_names() -> None:
    """Kiểm tra thứ tự và tên cơ hiển thị khớp danh sách tên cơ đầu vào.

    Hiện thực kiểm chứng: FR-005, API-VIS-0012, AC-1.
    """
    activations = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    cfg = _make_dummy_replay_config()

    lines = hud_lines(activations, _SIX_MUSCLES, cfg)

    assert len(lines) == len(_SIX_MUSCLES)
    for idx, name in enumerate(_SIX_MUSCLES):
        assert lines[idx].startswith(f"{name}:")


def test_hud_bar_width_visualization() -> None:
    """Kiểm tra độ rộng và tỉ lệ lấp đầy của thanh trực quan khối ký tự.

    Hiện thực kiểm chứng: FR-005, API-VIS-0012.
    """
    # 0.0 -> rỗng; 0.5 -> 5 khối; 1.0 -> 10 khối
    activations = [0.0, 0.5, 1.0, 0.2, 0.8, 0.25]
    cfg = _make_dummy_replay_config(decimals=3, bar_width=10)

    lines = hud_lines(activations, _SIX_MUSCLES, cfg)

    # 0.0 -> thanh gồm 10 khoảng trắng
    assert "[          ]" in lines[0]
    # 0.5 -> thanh gồm 5 ký tự '█' và 5 khoảng trắng
    assert "[█████     ]" in lines[1]
    # 1.0 -> thanh gồm 10 ký tự '█'
    assert "[██████████]" in lines[2]

    # Kiểm tra trường hợp bar_width = 0 (không hiển thị thanh)
    cfg_no_bar = _make_dummy_replay_config(decimals=3, bar_width=0)
    lines_no_bar = hud_lines(activations, _SIX_MUSCLES, cfg_no_bar)
    assert "[" not in lines_no_bar[0]
    assert lines_no_bar[0] == f"{_SIX_MUSCLES[0]}: 0.000"


def test_hud_warning_line_displayed_when_present() -> None:
    """Kiểm tra dòng cảnh báo xuất hiện khi có cảnh báo lệch mô hình.

    Hiện thực kiểm chứng: FR-012, API-VIS-0012, AC-4.
    """
    activations = [0.1] * 6
    cfg = _make_dummy_replay_config()

    # Không có cảnh báo -> đúng 6 dòng
    lines_clean = hud_lines(activations, _SIX_MUSCLES, cfg, warning=None)
    assert len(lines_clean) == 6

    # Cảnh báo chuỗi tường minh "MÔ HÌNH LỆCH"
    lines_warn = hud_lines(activations, _SIX_MUSCLES, cfg, warning="MÔ HÌNH LỆCH")
    assert len(lines_warn) == 7
    assert lines_warn[-1] == "MÔ HÌNH LỆCH"

    # Cảnh báo dạng cờ boolean True
    lines_bool = hud_lines(activations, _SIX_MUSCLES, cfg, warning=True)
    assert len(lines_bool) == 7
    assert lines_bool[-1] == "MÔ HÌNH LỆCH"


def test_hud_config_sources_supported() -> None:
    """Kiểm tra hỗ trợ nạp cấu hình linh hoạt từ ReplayConfig, HudConfig hoặc từ điển.

    Hiện thực kiểm chứng: API-VIS-0012.
    """
    activations = [0.5] * 6

    # 1. Nạp từ HudConfig trực tiếp
    hud_cfg = HudConfig(decimals=1, bar_width=6)
    lines_hud = hud_lines(activations, _SIX_MUSCLES, hud_cfg)
    assert "0.5" in lines_hud[0]
    assert "[███   ]" in lines_hud[0]

    # 2. Nạp từ cấu hình dạng dict
    dict_cfg = {"hud": {"decimals": 2, "bar_width": 4}}
    lines_dict = hud_lines(activations, _SIX_MUSCLES, dict_cfg)
    assert "0.50" in lines_dict[0]
    assert "[██  ]" in lines_dict[0]


def test_hud_mismatched_lengths_raise_value_error() -> None:
    """Kiểm tra ném lỗi ValueError khi độ dài chuỗi kích hoạt và tên cơ không khớp.

    Hiện thực kiểm chứng: API-VIS-0012.
    """
    activations = [0.1, 0.2]  # 2 giá trị thay vì 6
    cfg = _make_dummy_replay_config()

    with pytest.raises(ValueError, match="không khớp"):
        hud_lines(activations, _SIX_MUSCLES, cfg)


def test_hud_numpy_array_input() -> None:
    """Kiểm tra tương thích với mảng numpy ndarray từ bộ quan sát mô phỏng.

    Hiện thực kiểm chứng: FR-005, INV-006, API-VIS-0012.
    """
    np_activations = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], dtype=np.float32)
    np_copy = np_activations.copy()
    cfg = _make_dummy_replay_config()

    lines = hud_lines(np_activations, _SIX_MUSCLES, cfg)

    # Mảng numpy gốc không bị đột biến
    np.testing.assert_array_equal(np_activations, np_copy)
    assert len(lines) == 6
    assert "0.100" in lines[0]


def test_hud_clamping_out_of_bounds_activation() -> None:
    """Kiểm tra tự động kẹp biên giá trị kích hoạt ngoài đoạn [0, 1] khi vẽ thanh.

    Hiện thực kiểm chứng: INV-006, API-VIS-0012.
    """
    activations = [-0.5, 1.5, 0.5, 0.5, 0.5, 0.5]
    cfg = _make_dummy_replay_config(decimals=3, bar_width=10)

    lines = hud_lines(activations, _SIX_MUSCLES, cfg)

    # -0.5 kẹp về 0 thanh đầy (0 khối)
    assert "[          ]" in lines[0]
    # 1.5 kẹp về tối đa 10 khối
    assert "[██████████]" in lines[1]
