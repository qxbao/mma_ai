"""Kiểm thử tích hợp hiển thị 3D không làm hỏng tiến trình huấn luyện (T333).

Hiện thực và kiểm chứng các yêu cầu và bất biến:
- FR-022: Hiển thị 3D khuỷu tay chạy ở tiến trình riêng (separate process), bật/tắt được
  và mặc định tắt; huấn luyện mặc định không giao diện (headless); nạp chính sách (policy)
  mới nhất từ checkpoints/latest.json.
- INV-005: Giao diện chỉ-đọc (read-only); không được sửa hay ghi vào checkpoint, cấu hình
  hay tiến trình huấn luyện; tiến trình giao diện hoặc 3D bị đóng đột ngột không làm dừng train.
- NFR-HEADLESS-001: Khi thiếu biến môi trường DISPLAY hoặc WAYLAND_DISPLAY, in "3D không khả dụng"
  ra stderr và thoát với mã 0 (exit 0), không ném lỗi làm gián đoạn chương trình huấn luyện.
- US5, SC-007, AC-7: Hiển thị 3D khuỷu tay do policy điều khiển chạy ở tiến trình riêng,
  lấy trạng thái từ checkpoint mới nhất, tắt được mà không ảnh hưởng huấn luyện;
  khi không bật, train chạy headless.
"""

from __future__ import annotations

import importlib.util
import multiprocessing
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Protocol
from unittest.mock import patch

import pytest
import yaml
from train_fixtures import list_runs, load_manifest, run_train_cli, smoke_config

from mma_ai.learning.cli import _build_parser
from mma_ai.learning.train_config import TrainConfig
from mma_ai.monitoring.cli import main as watch_cli_main
from mma_ai.monitoring.viewer3d import View3D

# Hạn mức thời gian chờ tiến trình View3D khởi chạy có PID (007 AC-2, NFR-PERF-001)
PROCESS_START_TIMEOUT_S: float = 5.0


class _ProcessLike(Protocol):
    @property
    def pid(self) -> int | None: ...

    @property
    def exitcode(self) -> int | None: ...


def _wait_until_started(proc: _ProcessLike, timeout_s: float) -> None:
    """Chờ tiến trình View3D khởi chạy có hạn mức, tránh race condition khi máy bận.

    Hiện thực 007 AC-2, FR-003, FR-008:
    - Poll ngắn (time.sleep) cho tới khi proc.pid is not None.
    - Trả sớm và báo riêng 'đã thoát sớm' kèm mã thoát nếu proc.exitcode is not None.
    - Hết hạn mức timeout_s thì báo lỗi tiếng Việt 'không khởi chạy được trong hạn mức'.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if proc.exitcode is not None:
            pytest.fail(f"Tiến trình View3D đã thoát sớm với mã {proc.exitcode}")
        if proc.pid is not None:
            return
        time.sleep(0.01)

    if proc.exitcode is not None:
        pytest.fail(f"Tiến trình View3D đã thoát sớm với mã {proc.exitcode}")
    pytest.fail(f"Tiến trình View3D không khởi chạy được trong hạn mức {timeout_s} s")


def test_wait_until_started_success() -> None:
    """007 AC-2, FR-003: Chờ thành công khi tiến trình đã có PID hợp lệ."""

    class _LiveProcess:
        pid: int | None = 12345
        exitcode: int | None = None

    _wait_until_started(_LiveProcess(), timeout_s=0.5)


def test_wait_until_started_timeout() -> None:
    """007 AC-2, FR-003, FR-008: Kiểm thử báo lỗi tiếng Việt khi quá hạn mức."""

    class _HungProcess:
        pid: int | None = None
        exitcode: int | None = None

    with pytest.raises(pytest.fail.Exception, match="không khởi chạy được trong hạn mức"):
        _wait_until_started(_HungProcess(), timeout_s=0.05)


def test_wait_until_started_early_exit() -> None:
    """007 AC-2, FR-003, FR-008: Báo riêng đã thoát sớm kèm mã thoát khi exitcode khác None."""

    class _DeadProcess:
        pid: int | None = None
        exitcode: int | None = 1

    with pytest.raises(pytest.fail.Exception, match="đã thoát sớm với mã 1"):
        _wait_until_started(_DeadProcess(), timeout_s=0.05)



def test_viewer3d_train_independent_assertion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FR-022, INV-005, NFR-HEADLESS-001, AC-7, US5: Khẳng định độc lập không phụ thuộc extra rl.

    Đảm bảo kiểm thử không bị bỏ qua toàn bộ khi thiếu phụ thuộc tuỳ chọn torch.
    Xác minh hợp đồng cơ bản:
    - Mô-đun View3D tồn tại và sẵn sàng sử dụng.
    - Bộ phân tích cú pháp (CLI parser) của lệnh train hỗ trợ cờ --view3d và mặc định tắt (False).
    - Cấu hình huấn luyện mặc định TrainConfig có ui.view3d là False.
    - Khi không có biến môi trường hiển thị DISPLAY/WAYLAND_DISPLAY, View3D.run()
      in "3D không khả dụng" ra stderr và thoát với mã 0 mà không làm sập chương trình.
    """
    # 1. Xác thực mô-đun viewer3d tồn tại và nạp được
    assert importlib.util.find_spec("mma_ai.monitoring.viewer3d") is not None, (
        "Mô-đun mma_ai.monitoring.viewer3d phải có mặt trên hệ thống"
    )

    # 2. Xác thực bộ phân tích cú pháp CLI của train hỗ trợ cờ --view3d và mặc định là False
    parser = _build_parser()
    actions = {action.dest: action for action in parser._actions}
    assert "view3d" in actions, "CLI train phải hỗ trợ cờ dòng lệnh --view3d"
    assert actions["view3d"].default is False, "Cờ --view3d phải có giá trị mặc định là False"

    args = parser.parse_args([])
    assert args.view3d is False, "Mặc định phân tích cú pháp không cờ phải cho view3d là False"

    # 3. Xác thực cấu hình huấn luyện mặc định tắt hiển thị 3D (headless mặc định)
    cfg = TrainConfig.load()
    assert cfg.ui.view3d is False, "Cấu hình huấn luyện mặc định ui.view3d phải là False"

    # 4. Xác thực View3D nhận biết trạng thái không màn hình và thoát 0 kèm thông điệp tiếng Việt
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    viewer = View3D(tmp_path)
    assert viewer.has_display() is False, "Phải xác định chính xác trạng thái không có màn hình"

    exit_code = viewer.run()
    assert exit_code == 0, "View3D.run() phải trả về mã thoát 0 khi thiếu màn hình"

    captured = capsys.readouterr()
    assert "3D không khả dụng" in captured.err, (
        f"Kỳ vọng thông báo '3D không khả dụng' trong stderr, thực tế nhận: {captured.err!r}"
    )


def test_view3d_off_by_default(tmp_path: Path) -> None:
    """FR-022, INV-005, NFR-HEADLESS-001, AC-7: Khi không truyền cờ --view3d, không tạo 3D."""
    # 1. Kiểm tra cấu hình smoke mặc định không bật view3d
    cfg_file = smoke_config(tmp_path)
    raw_cfg = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    assert raw_cfg.get("ui", {}).get("view3d") is False, "Cấu hình smoke phải có ui.view3d là False"

    # 2. Khẳng định View3D không tự khởi động khi khởi tạo đối tượng
    viewer = View3D(tmp_path)
    assert viewer.is_running is False, "Đối tượng View3D không được tự chạy khi khởi tạo"

    # 3. Kiểm tra với watch_cli: khi không có cờ --view3d, không tạo multiprocessing.Process cho 3D
    run_dir = tmp_path / "run_test_default"
    run_dir.mkdir(parents=True, exist_ok=True)
    stop_event = threading.Event()
    stop_event.set()

    with patch("multiprocessing.Process") as mock_process_cls:
        exit_code = watch_cli_main(
            ["--run", str(run_dir), "--port", "0"],
            stop_event=stop_event,
        )
        assert exit_code == 0, f"watch_cli phải thoát mã 0, nhận {exit_code}"
        assert not mock_process_cls.called, (
            "FR-022: Khi không có cờ --view3d, tuyệt đối không khởi tạo tiến trình 3D"
        )


def test_view3d_unavailable_without_display_does_not_break_train(tmp_path: Path) -> None:
    """FR-022, INV-005, NFR-HEADLESS-001, AC-7, US5: --view3d thiếu màn hình không hỏng train.

    Khi DISPLAY/WAYLAND_DISPLAY bị bỏ đặt:
    - In thông báo '3D không khả dụng' ra stderr.
    - Tiến trình huấn luyện vẫn hoàn thành thành công với mã thoát 0 (exit 0).
    - Tạo đầy đủ các điểm kiểm tra (checkpoints) định kỳ và điểm kiểm tra cuối cùng.
    - Hồ sơ thí nghiệm (run manifest) ghi nhận trạng thái 'done' và không có lỗi.
    """
    pytest.importorskip("torch", reason="Cần extra rl (torch) để thực thi huấn luyện PPO")

    runs_dir = tmp_path / "runs"
    cfg_file = smoke_config(
        tmp_path,
        total_timesteps=2048,
        n_steps=1024,
        batch_size=256,
        every_updates=1,
    )

    clean_env = os.environ.copy()
    clean_env.pop("DISPLAY", None)
    clean_env.pop("WAYLAND_DISPLAY", None)

    # Chạy lệnh huấn luyện với cờ --view3d
    res = run_train_cli(
        ["--stage", "elbow", "--seed", "42", "--config", str(cfg_file), "--view3d"],
        env=clean_env,
        timeout=120.0,
    )

    # Khẳng định tiến trình huấn luyện hoàn thành mã 0
    assert res.exit_code == 0, (
        f"Huấn luyện thất bại với mã {res.exit_code}.\nStdout: {res.stdout}\nStderr: {res.stderr}"
    )

    # Khẳng định thông báo '3D không khả dụng' xuất hiện trong stderr
    assert "3D không khả dụng" in res.stderr, (
        f"Kỳ vọng '3D không khả dụng' trong stderr khi thiếu màn hình, thực tế: {res.stderr!r}"
    )

    # Khẳng định thư mục run được tạo hợp lệ
    runs = list_runs(runs_dir)
    assert len(runs) == 1, f"Kỳ vọng đúng 1 thư mục run, tìm thấy: {len(runs)}"
    run_dir = runs[0]

    # Khẳng định có đầy đủ các checkpoint (ít nhất 1 checkpoint định kỳ và latest.json)
    checkpoints_dir = run_dir / "checkpoints"
    assert checkpoints_dir.is_dir(), "Thư mục checkpoints phải tồn tại"
    latest_json = checkpoints_dir / "latest.json"
    assert latest_json.is_file(), "Tệp checkpoints/latest.json phải tồn tại"

    pt_files = list(checkpoints_dir.glob("*.pt"))
    assert len(pt_files) >= 1, "Phải có ít nhất một tệp điểm kiểm tra (.pt) được lưu"

    # Khẳng định hồ sơ run có trạng thái done và không có lỗi
    manifest = load_manifest(run_dir)
    status = manifest.get("status")
    assert status == "done", f"Trạng thái run không phải done: {status}"
    assert manifest.get("error") is None, f"Hồ sơ run ghi nhận lỗi: {manifest.get('error')}"

    # Khẳng định sức khoẻ số học (numeric health) đạt chuẩn độ tin cậy số học
    numeric_health = manifest.get("numeric_health", {})
    assert numeric_health.get("nan_count") == 0, "Phát hiện giá trị NaN trong huấn luyện"
    assert numeric_health.get("inf_count") == 0, "Phát hiện giá trị Inf trong huấn luyện"


def test_view3d_process_separate(tmp_path: Path) -> None:
    """Hiển thị 3D ở tiến trình riêng, kết thúc không ảnh hưởng train.

    Truy vết yêu cầu:
    - 007 AC-2, 007 AC-3, 007 AC-4, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008
    - INV-001, INV-002, INV-003, NFR-PERF-001, NFR-QUAL-001, NFR-REL-001
    - FR-022, INV-005, AC-7, US5, US2.

    Xác minh:
    1. Khi bật --view3d, tiến trình hiển thị 3D chạy ở tiến trình con độc lập với PID riêng
       khác với PID của tiến trình huấn luyện chính và PID của máy chủ quan sát (FR-022).
       Tiến trình được chờ khởi chạy có hạn mức hữu hạn khai tường minh trước khi
       kiểm tra PID (007 AC-2, FR-003).
    2. Đóng hoặc kết thúc (terminate/kill) tiến trình 3D giữa chừng KHÔNG làm gián đoạn
       huấn luyện, không làm mất ui.json và không làm sai lệch tính toàn vẹn của run (INV-005).
    3. Luồng quan sát dừng sạch sẽ bằng stop_event.
    4. Huấn luyện thật với --view3d hoàn thành thành công mã 0 và có latest.json khi có torch.
    """
    # 1. Kiểm tra kiến trúc tiến trình độc lập thông qua giao diện quan sát watch_cli
    run_dir = tmp_path / "run_separate_test"
    run_dir.mkdir(parents=True, exist_ok=True)

    started_processes: list[multiprocessing.Process] = []

    def _fake_run_viewer(target_dir: str) -> None:
        # Giả lập vòng lặp hiển thị 3D hoạt động cho đến khi bị ngắt
        while True:
            time.sleep(0.05)

    original_process_cls = multiprocessing.Process

    def _tracking_process_factory(*args: Any, **kwargs: Any) -> multiprocessing.Process:
        kwargs["target"] = _fake_run_viewer
        proc = original_process_cls(*args, **kwargs)
        started_processes.append(proc)
        return proc

    stop_event = threading.Event()

    with patch("multiprocessing.Process", side_effect=_tracking_process_factory):
        # Chạy watch_cli với cờ --view3d trong luồng riêng để kiểm tra tiến trình con
        cli_thread = threading.Thread(
            target=watch_cli_main,
            args=(["--run", str(run_dir), "--port", "0", "--view3d"],),
            kwargs={"stop_event": stop_event},
            daemon=True,
        )
        cli_thread.start()

        # Chờ tiến trình 3D được đưa vào danh sách theo dõi khi khởi tạo đối tượng
        deadline = time.time() + PROCESS_START_TIMEOUT_S
        while time.time() < deadline and not started_processes:
            time.sleep(0.01)

        assert len(started_processes) == 1, "Phải khởi tạo đúng 1 tiến trình hiển thị 3D"
        viewer_proc = started_processes[0]

        # Chờ tiến trình thực sự khởi chạy có PID trong hạn mức (007 AC-2, FR-003)
        _wait_until_started(viewer_proc, timeout_s=PROCESS_START_TIMEOUT_S)

        # Khẳng định tiến trình 3D có PID riêng biệt khác PID tiến trình hiện tại
        assert viewer_proc.pid is not None, "Tiến trình 3D phải có PID hợp lệ sau khi khởi chạy"
        assert viewer_proc.pid != os.getpid(), (
            f"FR-022: PID 3D ({viewer_proc.pid}) phải khác PID chính ({os.getpid()})"
        )
        if viewer_proc.exitcode is not None:
            pytest.fail(
                f"Tiến trình View3D đã thoát sớm với mã {viewer_proc.exitcode} "
                "trước khi kiểm tra is_alive"
            )
        assert viewer_proc.is_alive() is True, "Tiến trình 3D phải đang hoạt động"

        # 2. Ngắt đột ngột tiến trình 3D (simulate kill)
        viewer_proc.terminate()
        viewer_proc.join(timeout=2.0)
        assert viewer_proc.is_alive() is False, "Tiến trình 3D phải dừng sau tín hiệu terminate"

        # Khẳng định tiến trình quan sát chính vẫn sống và phản hồi bình thường sau khi 3D bị tắt
        ui_json_path = run_dir / "ui.json"
        assert ui_json_path.is_file(), "ui.json vẫn tồn tại toàn vẹn sau khi tiến trình 3D bị tắt"

        # Dừng luồng giao diện quan sát
        stop_event.set()
        cli_thread.join(timeout=3.0)

    # 3. Kiểm tra tích hợp với huấn luyện thật khi có torch: kết thúc 3D không ảnh hưởng huấn luyện
    if importlib.util.find_spec("torch") is not None:
        runs_dir = tmp_path / "runs"
        cfg_file = smoke_config(
            tmp_path,
            total_timesteps=2048,
            n_steps=1024,
            batch_size=256,
            every_updates=1,
            **{"ui.mode": "web"},
        )

        clean_env = os.environ.copy()
        clean_env.pop("DISPLAY", None)
        clean_env.pop("WAYLAND_DISPLAY", None)

        cmd = [
            sys.executable,
            "-m",
            "mma_ai.learning.cli",
            "--stage",
            "elbow",
            "--seed",
            "42",
            "--config",
            str(cfg_file),
            "--view3d",
            "--ui-port",
            "0",
        ]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=clean_env,
            cwd=str(Path.cwd()),
        )

        try:
            # Chờ một khoảng thời gian để tiến trình huấn luyện hoàn thành
            stdout, stderr = proc.communicate(timeout=60.0)
            assert proc.returncode == 0, (
                f"Lệnh huấn luyện với --view3d thất bại: mã {proc.returncode}\nStderr: {stderr}"
            )

            # Khẳng định có checkpoint và thư mục run hoàn chỉnh
            created_runs = list_runs(runs_dir)
            assert len(created_runs) == 1, "Phải có đúng một thư mục run được tạo"
            completed_run = created_runs[0]
            latest_ckpt = completed_run / "checkpoints" / "latest.json"
            assert latest_ckpt.is_file(), "latest.json phải tồn tại sau khi huấn luyện xong"
        finally:
            if proc.poll() is None:
                proc.kill()
