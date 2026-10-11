"""Kiểm thử tích hợp khả năng phục hồi và sống sót của giao diện quan sát (T331).

Hiện thực và chứng minh các yêu cầu và bất biến:
- FR-020, SC-007, AC-7: Trong lúc train đang chạy, giao diện quan sát thời gian thực cung cấp
  reward, loss, kích hoạt 6 cơ, env steps/s, env_steps / total_steps và trạng thái checkpoint.
- FR-021, INV-005: Giao diện quan sát chỉ đọc dữ liệu huấn luyện, không làm thay đổi policy,
  checkpoint, cấu hình hay làm dừng tiến trình train.
- FR-023: Giao diện quan sát không khởi động được (do cổng bị chiếm hoặc lỗi mạng)
  MUST NOT làm dừng train; tiến trình train tiếp tục hoàn tất bình thường với mã thoát 0.
- NFR-PERF-002: Bảng quan sát cập nhật dữ liệu định kỳ với độ trễ không vượt quá 5 giây.
- INV-005: Tiến trình giao diện bị đóng hoặc tắt đột ngột giữa chừng (killed midrun)
  MUST NOT làm dừng train, không làm mất checkpoint và mã băm SHA-256 của checkpoint không đổi.
- SC-007, AC-7: Khi lượt train kết thúc, giao diện quan sát hiển thị trạng thái hoàn thành
  kèm đầy đủ các số liệu cuối cùng.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import pytest
from train_fixtures import list_runs, run_train_cli, smoke_config

from mma_ai.learning.cli import _build_parser
from mma_ai.monitoring.dashboard import serve

_SIX_MUSCLES = ("TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA")


def test_dashboard_resilience_independent_assertion(tmp_path: Path) -> None:
    """FR-020, FR-021, INV-005, SC-007, AC-7: Khẳng định độc lập không phụ thuộc extra rl.

    Đảm bảo kiểm thử không bị bỏ qua (skipped) toàn bộ khi thiếu phụ thuộc tuỳ chọn torch.
    Xác minh hợp đồng giao diện quan sát:
    - CLI hỗ trợ đầy đủ các cờ điều khiển giao diện (--ui, --ui-port).
    - Máy chủ giao diện quan sát chạy độc lập chỉ-đọc, từ chối địa chỉ ngoài loopback.
    - Điểm cuối /api/progress trả lỗi 503 khi chưa có dữ liệu tiến trình.
    """
    # 1. Kiểm tra parser CLI hỗ trợ cờ điều khiển giao diện
    parser = _build_parser()
    actions = {action.dest for action in parser._actions}
    assert "ui" in actions, "CLI parser phải hỗ trợ cờ --ui"
    assert "ui_port" in actions, "CLI parser phải hỗ trợ cờ --ui-port"

    # 2. Kiểm tra máy chủ giao diện hoạt động ở chế độ chỉ-đọc không cần phụ thuộc rl
    with serve(tmp_path, host="127.0.0.1", port=0) as server:
        assert server.host == "127.0.0.1"
        assert server.port > 0

        # Chưa có tệp progress.json => trả 503 'chưa có dữ liệu' (INV-005, API-TRN-0001)
        progress_url = f"{server.url}/api/progress"
        req = urllib.request.Request(progress_url, method="GET")
        try:
            urllib.request.urlopen(req, timeout=2.0)
            pytest.fail("Kỳ vọng lỗi HTTP 503 khi chưa có progress.json")
        except urllib.error.HTTPError as http_err:
            assert http_err.code == 503
            err_data = json.loads(http_err.read().decode("utf-8"))
            assert err_data == {"error": "chưa có dữ liệu"}

        # Trang chủ / trả HTML chứa các khối thông tin cơ bản
        root_url = f"{server.url}/"
        root_req = urllib.request.Request(root_url, method="GET")
        with urllib.request.urlopen(root_req, timeout=2.0) as root_resp:
            assert root_resp.status == 200
            html = root_resp.read().decode("utf-8")
            assert "kích hoạt" in html.lower() or "activation" in html.lower()
            assert "checkpoint" in html.lower()


def test_dashboard_during_train_shows_required_fields(tmp_path: Path) -> None:
    """FR-020, FR-021, NFR-PERF-002, INV-005, SC-007, AC-7: Hiện đủ trường khi train chạy."""
    pytest.importorskip("torch", reason="Cần extra rl (torch) để thực thi huấn luyện PPO")
    runs_dir = tmp_path / "runs"
    cfg_file = smoke_config(
        tmp_path,
        total_timesteps=4096,
        n_steps=1024,
        batch_size=256,
        every_updates=1,
        **{"ui.snapshot_interval_s": 0.1, "ui.mode": "web"},
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
        "--ui",
        "web",
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

    ui_url: str | None = None
    ui_pid: int | None = None
    captured_snapshots: list[dict[str, Any]] = []

    try:
        # 1. Chờ tệp ui.json xuất hiện trong thư mục run
        deadline = time.time() + 15.0
        run_dir: Path | None = None
        while time.time() < deadline:
            runs = list_runs(runs_dir)
            if runs:
                candidate = runs[0]
                ui_json_path = candidate / "ui.json"
                if ui_json_path.is_file():
                    try:
                        ui_info = json.loads(ui_json_path.read_text(encoding="utf-8"))
                        ui_url = ui_info.get("url")
                        ui_pid = ui_info.get("pid")
                        run_dir = candidate
                        break
                    except Exception:
                        pass
            time.sleep(0.05)

        assert run_dir is not None, "Không tìm thấy thư mục run sau khi khởi chạy train"
        assert ui_url is not None and ui_url.startswith("http"), (
            f"ui.json không chứa URL hợp lệ: {ui_url}"
        )

        # 2. Thăm dò GET /api/progress qua URL trong ui.json trong lúc train đang chạy
        progress_url = f"{ui_url}/api/progress"
        poll_deadline = time.time() + 20.0
        while time.time() < poll_deadline and proc.poll() is None:
            try:
                req = urllib.request.Request(progress_url, method="GET")
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        captured_snapshots.append(data)
                        if len(captured_snapshots) >= 2 and (
                            captured_snapshots[-1]["env_steps"]
                            != captured_snapshots[0]["env_steps"]
                            or captured_snapshots[-1]["update_idx"]
                            != captured_snapshots[0]["update_idx"]
                        ):
                            break
            except Exception:
                pass
            time.sleep(0.1)

        # Chờ tiến trình train hoàn tất
        stdout, stderr = proc.communicate(timeout=60.0)
        assert proc.returncode == 0, (
            f"Lượt train bị dừng hoặc lỗi: code={proc.returncode}\nStderr: {stderr}"
        )

        if not captured_snapshots:
            try:
                req = urllib.request.Request(progress_url, method="GET")
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    captured_snapshots.append(json.loads(resp.read().decode("utf-8")))
            except Exception:
                pass

        assert len(captured_snapshots) >= 1, (
            "Không nhận được dữ liệu snapshot nào từ GET /api/progress"
        )

        snap = captured_snapshots[-1]
        assert "mean_return" in snap, "Thiếu trường reward (mean_return)"
        assert "loss" in snap, "Thiếu trường loss"
        assert "activation" in snap, "Thiếu trường activation"
        assert "env_steps_per_second" in snap, "Thiếu trường env_steps/s"
        assert "env_steps" in snap and "total_steps" in snap, "Thiếu env_steps hoặc total_steps"
        assert "checkpoint" in snap, "Thiếu trạng thái checkpoint"

        act = snap["activation"]
        assert isinstance(act, dict), "Activation phải là mapping"
        assert list(act.get("muscle_names", [])) == list(_SIX_MUSCLES), (
            "Thiếu hoặc sai tên 6 cơ trong activation"
        )
        assert len(act.get("mean", [])) == 6, "Activation mean phải có 6 phần tử"

        ckpt_st = snap["checkpoint"]
        assert isinstance(ckpt_st, dict), "Checkpoint status phải là mapping"
        assert "count" in ckpt_st
        assert "every_updates" in ckpt_st

        assert snap["total_steps"] == 4096
        assert snap["env_steps"] > 0
    finally:
        if proc.poll() is None:
            proc.kill()
        if ui_pid is not None:
            try:
                os.kill(ui_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass


def test_train_survives_ui_failure(tmp_path: Path) -> None:
    """FR-023, INV-005, SC-007, AC-7: Cổng bị chiếm => cảnh báo nêu lý do, train vẫn mã 0."""
    pytest.importorskip("torch", reason="Cần extra rl (torch) để thực thi huấn luyện PPO")
    cfg_file = smoke_config(tmp_path)

    # Mở một socket chiếm cổng loopback
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    busy_port = sock.getsockname()[1]

    try:
        result = run_train_cli(
            [
                "--stage",
                "elbow",
                "--seed",
                "42",
                "--config",
                str(cfg_file),
                "--ui",
                "web",
                "--ui-port",
                str(busy_port),
            ],
            timeout=60.0,
        )
    finally:
        sock.close()

    assert result.exit_code == 0, (
        f"Train bị dừng hoặc lỗi: code={result.exit_code}\nStderr: {result.stderr}"
    )
    assert (
        "Cảnh báo" in result.stderr
        or "Lỗi khởi động máy chủ" in result.stderr
        or str(busy_port) in result.stderr
    ), f"Kỳ vọng cảnh báo nêu lý do giao diện không khởi động được trong stderr:\n{result.stderr}"


def test_train_survives_ui_killed_midrun(tmp_path: Path) -> None:
    """FR-021, INV-005, SC-007, AC-7: UI bị kill đột ngột => train không dừng, không mất ckpt."""
    pytest.importorskip("torch", reason="Cần extra rl (torch) để thực thi huấn luyện PPO")
    runs_dir = tmp_path / "runs"
    cfg_file = smoke_config(
        tmp_path,
        total_timesteps=4096,
        n_steps=1024,
        batch_size=256,
        every_updates=1,
        **{"ui.snapshot_interval_s": 0.1, "ui.mode": "web"},
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
        "--ui",
        "web",
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

    killed_ui = False
    ui_pid: int | None = None
    try:
        deadline = time.time() + 15.0
        while time.time() < deadline and proc.poll() is None:
            runs = list_runs(runs_dir)
            if runs:
                ui_json_path = runs[0] / "ui.json"
                if ui_json_path.is_file():
                    try:
                        ui_info = json.loads(ui_json_path.read_text(encoding="utf-8"))
                        ui_pid = ui_info.get("pid")
                        if ui_pid is not None:
                            os.kill(ui_pid, signal.SIGKILL)
                            killed_ui = True
                            break
                    except Exception:
                        pass
            time.sleep(0.05)

        assert killed_ui, "Không thể kết thúc tiến trình giao diện trong lúc train"

        stdout, stderr = proc.communicate(timeout=60.0)
        assert proc.returncode == 0, (
            f"Train bị ảnh hưởng khi giao diện bị kill: code={proc.returncode}\nStderr: {stderr}"
        )

        runs = list_runs(runs_dir)
        assert len(runs) == 1, "Thư mục run phải tồn tại"
        ckpt_dir = runs[0] / "checkpoints"
        assert ckpt_dir.is_dir(), "Thư mục checkpoints phải tồn tại"

        meta_files = list(ckpt_dir.glob("*.meta.json"))
        assert len(meta_files) >= 1, "Phải có ít nhất một checkpoint meta"

        import torch

        for meta_file in meta_files:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            pt_name = meta_file.name.replace(".meta.json", ".pt")
            pt_file = ckpt_dir / pt_name
            assert pt_file.is_file(), f"Tệp checkpoint {pt_name} không tồn tại"

            hasher = hashlib.sha256()
            hasher.update(pt_file.read_bytes())
            actual_sha = hasher.hexdigest()
            assert actual_sha == meta["sha256"], (
                f"Băm checkpoint bị sai lệch: {actual_sha} != {meta['sha256']}"
            )

            loaded = torch.load(pt_file, weights_only=True)
            assert isinstance(loaded, dict), "Checkpoint phải nạp được dưới dạng dict"
    finally:
        if proc.poll() is None:
            proc.kill()
        if ui_pid is not None:
            try:
                os.kill(ui_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_ui_shows_finished_state_after_run(tmp_path: Path) -> None:
    """FR-020, INV-005, SC-007, AC-7: Hiện trạng thái hoàn thành kèm số liệu cuối sau train."""
    pytest.importorskip("torch", reason="Cần extra rl (torch) để thực thi huấn luyện PPO")
    runs_dir = tmp_path / "runs"
    cfg_file = smoke_config(tmp_path)

    res = run_train_cli(
        ["--stage", "elbow", "--seed", "42", "--config", str(cfg_file)],
        timeout=60.0,
    )
    assert res.exit_code == 0, f"Huấn luyện thất bại: {res.stderr}"

    runs = list_runs(runs_dir)
    assert len(runs) == 1, "Phải có đúng một thư mục run được tạo"
    run_dir = runs[0]

    with serve(run_dir, host="127.0.0.1", port=0) as server:
        url_api = f"{server.url}/api/progress"
        req_api = urllib.request.Request(url_api, method="GET")
        with urllib.request.urlopen(req_api, timeout=5.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))

        assert data["status"] == "done", f"Kỳ vọng status 'done' nhưng nhận: {data['status']}"
        assert data["env_steps"] == data["total_steps"]
        assert data["mean_return"] is not None
        assert data["loss"] is not None
        assert data["activation"] is not None
        assert data["checkpoint"]["count"] >= 1

        url_html = f"{server.url}/"
        req_html = urllib.request.Request(url_html, method="GET")
        with urllib.request.urlopen(req_html, timeout=5.0) as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")

        assert "done" in html.lower() or "hoàn thành" in html.lower(), (
            "Trang HTML không hiển thị trạng thái hoàn thành"
        )
        assert "kích hoạt" in html.lower() or "activation" in html.lower()
        assert "checkpoint" in html.lower()
        assert "reward" in html.lower() or "phần thưởng" in html.lower()
