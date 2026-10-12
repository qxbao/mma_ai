"""Bộ kiểm thử đơn vị cho bộ nhận khung hình MuJoCo Viewer (ViewerSink).

Truy vết các yêu cầu kỹ thuật và hợp đồng API:
- FR-001: Phát lại chuỗi khung hình theo thứ tự thời gian đã ghi vào MuJoCo Viewer.
- FR-004: Điểm đánh dấu mục tiêu (target marker) hiển thị đúng vị trí đã ghi trong user_scn.
- FR-005: Hiển thị 6 giá trị kích hoạt cơ (muscle activation) tương ứng trên HUD qua set_texts.
- FR-015: Nhập lười mô-đun mujoco.viewer trong ViewerSink để đường không đồ hoạ an toàn.
- INV-002: Replay chỉ đặt lại trạng thái đã ghi (qpos/act) và mj_forward, không điều khiển cơ.
- NFR-HEADLESS-001: Kiểm tra mô-đun an toàn trong môi trường không có màn hình (headless).
- API-VIS-0010: Hiện thực lớp ViewerSink(model, data, cfg) tuân thủ giao diện FrameSink.
- AC-1: Kiểm tra phát lại 3D đúng thứ tự khung hình, vị trí mục tiêu và thông số HUD.
- AC-2: Kiểm tra cập nhật trạng thái và hiển thị activation theo từng khung.
"""

from __future__ import annotations

import contextlib
import sys
from typing import Any

import mujoco
import numpy as np
import pytest

from mma_ai.physics.body_model import load_muscle_model
from mma_ai.visualization.episode import (
    Episode,
    Frame,
    ModelRecord,
    OutcomeRecord,
    TargetRecord,
    TimingRecord,
)
from mma_ai.visualization.pacing import Pacer
from mma_ai.visualization.playback import FrameSink, play
from mma_ai.visualization.replay_config import (
    DemoConfig,
    HudConfig,
    PlaybackConfig,
    ReplayConfig,
    TargetMarkerConfig,
)


@pytest.fixture(autouse=True)  # type: ignore[untyped-decorator]
def _cleanup_viewer_modules() -> Any:
    """Dọn dẹp mujoco.viewer và glfw khỏi sys.modules sau mỗi test (FR-015)."""
    yield
    for mod in list(sys.modules.keys()):
        if (
            mod == "mujoco.viewer"
            or mod.startswith("mujoco.viewer.")
            or mod == "glfw"
            or mod.startswith("glfw.")
        ):
            sys.modules.pop(mod, None)
    if hasattr(mujoco, "viewer"):
        with contextlib.suppress(AttributeError):
            delattr(mujoco, "viewer")


class MockViewerHandle:
    """Đối tượng giả lập Handle của MuJoCo Viewer phục vụ kiểm thử đơn vị cách ly."""

    def __init__(self, user_scn: mujoco.MjvScene | None = None) -> None:
        self.user_scn = user_scn
        self.is_running_flag = True
        self.sync_calls = 0
        self.close_calls = 0
        self.text_records: list[Any] = []
        self.clear_texts_calls = 0

    def is_running(self) -> bool:
        """Đọc trạng thái hoạt động của cửa sổ giả lập."""
        return self.is_running_flag

    def sync(self, state_only: bool = False) -> None:
        """Đồng bộ hoá khung hình."""
        self.sync_calls += 1

    def close(self) -> None:
        """Đóng cửa sổ giả lập."""
        self.is_running_flag = False
        self.close_calls += 1

    def set_texts(self, texts: Any) -> None:
        """Ghi nhận văn bản hiển thị lớp trên (overlay HUD)."""
        self.text_records.append(texts)

    def clear_texts(self) -> None:
        """Xoá văn bản hiển thị trên HUD."""
        self.clear_texts_calls += 1

    def lock(self) -> Any:
        """Khoá cảnh phục vụ cập nhật an toàn theo luồng."""
        return contextlib.nullcontext()


def _create_sample_config() -> ReplayConfig:
    """Tạo cấu hình phát lại mẫu phục vụ kiểm thử."""
    return ReplayConfig(
        playback=PlaybackConfig(
            speed=1.0,
            loop=False,
            display_hz=25,
            hold_after_end_s=0.0,
        ),
        demo=DemoConfig(
            split="test",
            target_index=0,
            seed=42,
        ),
        hud=HudConfig(
            decimals=3,
            bar_width=10,
        ),
        target_marker=TargetMarkerConfig(
            radius_m=0.02,
            rgba=(1.0, 0.1, 0.1, 0.7),
        ),
    )


def _create_sample_frame(
    t_s: float = 0.04,
    qpos_val: float = 0.5,
    qvel_val: float = 0.1,
    activation_vals: list[float] | None = None,
) -> Frame:
    """Tạo một khung hình mẫu với dữ liệu số học xác định."""
    act = activation_vals or [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    return Frame(
        t_s=t_s,
        qpos=[qpos_val],
        qvel=[qvel_val],
        activation=act,
        excitation=None,
        fingertip_position_m=(0.1, 0.2, 0.3),
        distance_m=0.05,
        reward=1.0,
    )


def test_import_viewer_module_without_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra nhập mô-đun viewer an toàn khi không có màn hình (FR-015, NFR-HEADLESS-001)."""
    # Đảm bảo môi trường hoàn toàn không có biến hiển thị
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    # Loại bỏ mô-đun khỏi sys.modules để kiểm tra quá trình nạp mới từ đầu
    sys.modules.pop("mma_ai.visualization.viewer", None)
    sys.modules.pop("mujoco.viewer", None)

    import mma_ai.visualization.viewer as viewer_mod

    assert hasattr(viewer_mod, "ViewerSink")
    # mujoco.viewer chỉ được nạp lười khi khởi tạo ViewerSink, không nạp ở cấp độ mô-đun
    assert "mujoco.viewer" not in sys.modules


def test_viewer_sink_satisfies_frame_sink_protocol() -> None:
    """Kiểm tra lớp ViewerSink tuân thủ hợp đồng giao diện FrameSink (API-VIS-0010, FR-001)."""
    from mma_ai.visualization.viewer import ViewerSink

    # Khẳng định ViewerSink là một kiểu hợp lệ thoả mãn giao thức FrameSink
    assert issubclass(ViewerSink, FrameSink)


def test_viewer_sink_lazy_imports_mujoco_viewer_on_init(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kiểm tra ViewerSink nạp lười mujoco.viewer khi khởi tạo (FR-015, API-VIS-0010)."""
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    sys.modules.pop("mujoco.viewer", None)

    from mma_ai.visualization.viewer import ViewerSink

    assert "mujoco.viewer" not in sys.modules

    loaded = load_muscle_model("myoelbow")
    data = mujoco.MjData(loaded.model)
    cfg = _create_sample_config()
    mock_handle = MockViewerHandle()

    # Khởi tạo ViewerSink với handle giả lập
    sink = ViewerSink(loaded.model, data, cfg, handle=mock_handle)

    # Sau khi khởi tạo, mujoco.viewer đã được nạp lười vào sys.modules
    assert "mujoco.viewer" in sys.modules
    assert sink.is_open() is True


def test_viewer_sink_calls_launch_passive_when_no_handle_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kiểm tra ViewerSink gọi launch_passive khi không truyền handle (API-VIS-0010, FR-001)."""
    import mujoco.viewer

    from mma_ai.visualization.viewer import ViewerSink

    loaded = load_muscle_model("myoelbow")
    data = mujoco.MjData(loaded.model)
    cfg = _create_sample_config()
    mock_handle = MockViewerHandle()

    launch_args: list[tuple[Any, Any]] = []

    def fake_launch_passive(model: Any, d: Any) -> Any:
        launch_args.append((model, d))
        return mock_handle

    monkeypatch.setattr(mujoco.viewer, "launch_passive", fake_launch_passive)

    sink = ViewerSink(loaded.model, data, cfg)

    assert len(launch_args) == 1
    assert launch_args[0][0] is loaded.model
    assert launch_args[0][1] is data
    assert sink.is_open() is True


def test_macos_without_mjpython_reports_vietnamese_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-004, AC-3: từ chối khởi chạy viewer trên macOS khi thiếu mjpython."""
    import mujoco.viewer

    import mma_ai.visualization.viewer as viewer_module
    from mma_ai.compat.platform_info import PlatformProfile
    from mma_ai.visualization.errors import DisplayUnavailable

    profile = PlatformProfile("macos", "14", "arm64", (3, 12, 0), False, True)
    monkeypatch.setattr(viewer_module, "detect_platform", lambda: profile, raising=False)
    launch_calls: list[bool] = []
    monkeypatch.setattr(
        mujoco.viewer,
        "launch_passive",
        lambda *_args: launch_calls.append(True),
    )
    loaded = load_muscle_model("myoelbow")

    with pytest.raises(DisplayUnavailable, match="mjpython -m") as error:
        viewer_module.ViewerSink(
            loaded.model,
            mujoco.MjData(loaded.model),
            _create_sample_config(),
        )

    assert error.value.exit_code == 7
    assert launch_calls == []


def test_macos_launch_error_mentions_mjpython(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-004, AC-3: ánh xạ lỗi khởi chạy nhắc mjpython sang lỗi màn hình."""
    import mujoco.viewer

    import mma_ai.visualization.viewer as viewer_module
    from mma_ai.compat.platform_info import PlatformProfile
    from mma_ai.visualization.errors import DisplayUnavailable

    profile = PlatformProfile("macos", "14", "arm64", (3, 12, 0), False, True)
    monkeypatch.setattr(viewer_module, "detect_platform", lambda: profile, raising=False)
    monkeypatch.setattr(sys, "executable", "/usr/bin/mjpython")
    monkeypatch.setattr(
        mujoco.viewer,
        "launch_passive",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("must be run with mjpython")),
    )
    loaded = load_muscle_model("myoelbow")

    with pytest.raises(DisplayUnavailable, match="mjpython -m") as error:
        viewer_module.ViewerSink(
            loaded.model,
            mujoco.MjData(loaded.model),
            _create_sample_config(),
        )

    assert error.value.exit_code == 7


def test_viewer_sink_show_sets_state_and_forwards(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra show() cập nhật trạng thái và gọi forward (FR-001, FR-005, INV-002, AC-1, AC-2)."""
    from mma_ai.visualization.viewer import ViewerSink

    loaded = load_muscle_model("myoelbow")
    data = mujoco.MjData(loaded.model)
    cfg = _create_sample_config()
    mock_handle = MockViewerHandle()

    forward_calls: list[tuple[Any, Any]] = []
    original_forward = mujoco.mj_forward

    def track_forward(m: Any, d: Any) -> None:
        forward_calls.append((m, d))
        original_forward(m, d)

    monkeypatch.setattr(mujoco, "mj_forward", track_forward)

    sink = ViewerSink(loaded.model, data, cfg, handle=mock_handle)

    target_activation = [0.15, 0.25, 0.35, 0.45, 0.55, 0.65]
    frame = _create_sample_frame(
        t_s=0.08,
        qpos_val=0.62,
        qvel_val=-0.14,
        activation_vals=target_activation,
    )
    sample_hud = [
        "TRIlong: 0.150 [==        ]",
        "BIClong: 0.450 [=====     ]",
    ]

    sink.show(frame, sample_hud)

    # Khẳng định trạng thái vật lý trong MjData khớp đúng với khung hình đã ghi
    assert data.qpos[0] == pytest.approx(0.62)
    assert data.qvel[0] == pytest.approx(-0.14)
    assert np.allclose(data.act[:6], target_activation)
    assert data.time == pytest.approx(0.08)

    # Khẳng định mj_forward được gọi để đồng bộ động học (INV-002: chỉ forward, không điều khiển)
    assert len(forward_calls) >= 1
    assert forward_calls[0][0] is loaded.model

    # Khẳng định thông số HUD được chuyển qua set_texts
    assert len(mock_handle.text_records) == 1
    texts_payload = mock_handle.text_records[0]
    assert isinstance(texts_payload, list)
    expected_hud_combined = "\n".join(sample_hud)
    assert texts_payload[0][2] == expected_hud_combined

    # Khẳng định handle.sync() đã được gọi
    assert mock_handle.sync_calls == 1


def test_viewer_sink_renders_target_marker_in_user_scn() -> None:
    """Kiểm tra vẽ mục tiêu 3D hình cầu trong user_scn (FR-004, API-VIS-0010, AC-1)."""
    from mma_ai.visualization.viewer import ViewerSink

    loaded = load_muscle_model("myoelbow")
    data = mujoco.MjData(loaded.model)
    cfg = _create_sample_config()

    user_scn = mujoco.MjvScene(loaded.model, maxgeom=10)
    mock_handle = MockViewerHandle(user_scn=user_scn)

    sink = ViewerSink(loaded.model, data, cfg, handle=mock_handle)

    target_pos = (0.12, -0.24, 0.36)
    sink.set_target(target_pos)

    frame = _create_sample_frame(t_s=0.04)
    sink.show(frame, ["HUD text"])

    # Khẳng định hình cầu mục tiêu được ghi vào user_scn
    assert user_scn.ngeom == 1
    geom = user_scn.geoms[0]
    assert geom.type == mujoco.mjtGeom.mjGEOM_SPHERE
    assert geom.pos[0] == pytest.approx(0.12)
    assert geom.pos[1] == pytest.approx(-0.24)
    assert geom.pos[2] == pytest.approx(0.36)
    assert geom.size[0] == pytest.approx(cfg.target_marker.radius_m)
    assert np.allclose(geom.rgba, cfg.target_marker.rgba)


def test_viewer_sink_target_marker_cleared_when_no_target() -> None:
    """Kiểm tra không vẽ điểm đánh dấu khi chưa thiết lập vị trí mục tiêu (FR-004)."""
    from mma_ai.visualization.viewer import ViewerSink

    loaded = load_muscle_model("myoelbow")
    data = mujoco.MjData(loaded.model)
    cfg = _create_sample_config()

    user_scn = mujoco.MjvScene(loaded.model, maxgeom=10)
    mock_handle = MockViewerHandle(user_scn=user_scn)

    sink = ViewerSink(loaded.model, data, cfg, handle=mock_handle)

    frame = _create_sample_frame(t_s=0.04)
    sink.show(frame, ["HUD text"])

    # Không có toạ độ mục tiêu thì user_scn ngeom phải bằng 0
    assert user_scn.ngeom == 0


def test_viewer_sink_is_open_and_close_lifecycle() -> None:
    """Kiểm tra vòng đời mở và đóng của ViewerSink (API-VIS-0010, FR-001)."""
    from mma_ai.visualization.viewer import ViewerSink

    loaded = load_muscle_model("myoelbow")
    data = mujoco.MjData(loaded.model)
    cfg = _create_sample_config()
    mock_handle = MockViewerHandle()

    sink = ViewerSink(loaded.model, data, cfg, handle=mock_handle)
    assert sink.is_open() is True

    # Khi viewer bị người dùng đóng bên ngoài
    mock_handle.is_running_flag = False
    assert sink.is_open() is False

    # Khôi phục trạng thái mở rồi gọi close() từ mã lệnh
    mock_handle.is_running_flag = True
    assert sink.is_open() is True
    sink.close()

    assert sink.is_open() is False
    assert mock_handle.close_calls == 1

    # Gọi show khi sink đã đóng thì không cập nhật thêm
    frame = _create_sample_frame(t_s=0.1)
    sink.show(frame, ["HUD"])
    assert mock_handle.sync_calls == 0


def test_viewer_sink_context_manager() -> None:
    """Kiểm tra hỗ trợ cú pháp ngữ cảnh with ... as sink (API-VIS-0010)."""
    from mma_ai.visualization.viewer import ViewerSink

    loaded = load_muscle_model("myoelbow")
    data = mujoco.MjData(loaded.model)
    cfg = _create_sample_config()
    mock_handle = MockViewerHandle()

    with ViewerSink(loaded.model, data, cfg, handle=mock_handle) as sink:
        assert sink.is_open() is True

    # Ra khỏi khối with, sink phải được đóng tự động
    assert sink.is_open() is False
    assert mock_handle.close_calls == 1


def test_viewer_sink_clears_hud_when_empty() -> None:
    """Kiểm tra xoá thông số HUD khi danh sách dòng chữ rỗng (FR-005)."""
    from mma_ai.visualization.viewer import ViewerSink

    loaded = load_muscle_model("myoelbow")
    data = mujoco.MjData(loaded.model)
    cfg = _create_sample_config()
    mock_handle = MockViewerHandle()

    sink = ViewerSink(loaded.model, data, cfg, handle=mock_handle)

    frame = _create_sample_frame(t_s=0.04)
    # Truyền danh sách HUD rỗng
    sink.show(frame, [])

    assert mock_handle.clear_texts_calls >= 1 or len(mock_handle.text_records) >= 1


def test_viewer_sink_compatible_with_play_pipeline() -> None:
    """Kiểm tra ViewerSink tích hợp với hàm play() (FR-001, FR-004, FR-005, AC-1)."""
    from mma_ai.visualization.viewer import ViewerSink

    loaded = load_muscle_model("myoelbow")
    data = mujoco.MjData(loaded.model)
    cfg = _create_sample_config()

    user_scn = mujoco.MjvScene(loaded.model, maxgeom=10)
    mock_handle = MockViewerHandle(user_scn=user_scn)

    sink = ViewerSink(loaded.model, data, cfg, handle=mock_handle)

    f0 = _create_sample_frame(t_s=0.0, qpos_val=0.1, activation_vals=[0.1] * 6)
    f1 = _create_sample_frame(t_s=0.04, qpos_val=0.4, activation_vals=[0.6] * 6)

    episode = Episode(
        schema_version="1.0.0",
        created_utc="2026-10-09T10:00:00Z",
        seed=123,
        model=ModelRecord(
            sha256="dummy_sha256",
            source="myoelbow",
            muscle_names=["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"],
            nq=1,
            nv=1,
        ),
        target=TargetRecord(
            position_m=(0.2, 0.3, 0.4),
            split="test",
            index=0,
            tolerance_m=0.05,
        ),
        source=None,
        library_versions={"mujoco": "3.15.0"},
        timing=TimingRecord(action_dt_s=0.04, physics_timestep_s=0.0025),
        outcome=OutcomeRecord(
            terminated=True,
            truncated=False,
            end_reason="target_reached",
            reached=True,
            n_actions=1,
            final_distance_m=0.01,
        ),
        frames=[f0, f1],
    )

    class DummyClock:
        def __init__(self) -> None:
            self.t = 0.0

        def clock(self) -> float:
            return self.t

        def sleep(self, s: float) -> None:
            self.t += s

    clk = DummyClock()
    pacer = Pacer(clock=clk.clock, sleep=clk.sleep)

    stats = play(episode, cfg, sink, pacer=pacer)

    assert stats.frames_shown >= 2
    assert mock_handle.sync_calls >= 2
    assert user_scn.ngeom == 1
    assert user_scn.geoms[0].pos[0] == pytest.approx(0.2)


class NonReentrantLockingMockHandle:
    """Tay cầm giả lập có cơ chế khoá không tái nhập để phát hiện tranh chấp khoá."""

    def __init__(self, user_scn: mujoco.MjvScene | None = None) -> None:
        self.user_scn = user_scn
        self.is_running_flag = True
        self.is_locked = False
        self.set_texts_called_while_locked = False
        self.clear_texts_called_while_locked = False
        self.text_records: list[Any] = []
        self.clear_texts_calls = 0
        self.sync_calls = 0

    def is_running(self) -> bool:
        """Đọc trạng thái hoạt động của viewer."""
        return self.is_running_flag

    @contextlib.contextmanager
    def lock(self) -> Any:
        """Quản lý ngữ cảnh khoá không tái nhập (non-reentrant lock)."""
        if self.is_locked:
            raise RuntimeError("Khoá không tái nhập đang bị chiếm giữ!")
        self.is_locked = True
        try:
            yield
        finally:
            self.is_locked = False

    def set_texts(self, texts: Any) -> None:
        """Cập nhật văn bản HUD và kiểm tra cờ đang giữ khoá."""
        if self.is_locked:
            self.set_texts_called_while_locked = True
            raise AssertionError(
                "Lỗi bất biến: set_texts() bị gọi trong khi đang giữ khoá (lock_ctx)!"
            )
        self.text_records.append(texts)

    def clear_texts(self) -> None:
        """Xoá văn bản HUD và kiểm tra cờ đang giữ khoá."""
        if self.is_locked:
            self.clear_texts_called_while_locked = True
            raise AssertionError(
                "Lỗi bất biến: clear_texts() bị gọi trong khi đang giữ khoá (lock_ctx)!"
            )
        self.clear_texts_calls += 1

    def sync(self, state_only: bool = False) -> None:
        """Đồng bộ hiển thị và kiểm tra cờ đang giữ khoá."""
        if self.is_locked:
            raise AssertionError(
                "Lỗi bất biến: sync() bị gọi trong khi đang giữ khoá (lock_ctx)!"
            )
        self.sync_calls += 1

    def close(self) -> None:
        """Đóng viewer giả lập."""
        self.is_running_flag = False


def test_viewer_sink_show_calls_set_texts_outside_lock() -> None:
    """Kiểm tra gọi set_texts và clear_texts ngoài khối lock_ctx.

    Bảo đảm không giữ khoá cảnh khi cập nhật HUD:
    AC-1, AC-5, FR-001, FR-005, INV-002, NFR-REL-001.
    """
    from mma_ai.visualization.viewer import ViewerSink

    loaded = load_muscle_model("myoelbow")
    data = mujoco.MjData(loaded.model)
    cfg = _create_sample_config()
    mock_handle = NonReentrantLockingMockHandle()

    sink = ViewerSink(loaded.model, data, cfg, handle=mock_handle)

    frame = _create_sample_frame(t_s=0.04)
    sample_hud = ["Dòng 1", "Dòng 2"]

    # Gọi show với HUD hợp lệ: set_texts phải được gọi ngoài khối khoá lock_ctx
    sink.show(frame, sample_hud)

    assert not mock_handle.set_texts_called_while_locked
    assert len(mock_handle.text_records) == 1
    assert mock_handle.text_records[0][0][2] == "Dòng 1\nDòng 2"
    assert mock_handle.sync_calls == 1

    # Gọi show với HUD rỗng: clear_texts phải được gọi ngoài khối khoá lock_ctx
    sink.show(frame, [])

    assert not mock_handle.clear_texts_called_while_locked
    assert mock_handle.clear_texts_calls == 1
    assert mock_handle.sync_calls == 2

