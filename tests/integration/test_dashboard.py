"""Kiểm thử tích hợp máy chủ bảng quan sát huấn luyện MMA-AI (dashboard).

Hiện thực và chứng minh các yêu cầu:
- FR-020: Cung cấp giao diện quan sát thời gian thực chỉ-đọc.
- FR-021: Giao diện chỉ đọc dữ liệu huấn luyện, không thay đổi tệp run.
- NFR-PERF-002: Độ trễ cập nhật giao diện không quá 5 giây.
- INV-005: Giao diện chỉ-đọc, không ảnh hưởng đến tiến trình train hay checkpoint.
- API-TRN-0001: Điểm cuối GET /api/progress trả dữ liệu snapshot.
- API-TRN-0002: Điểm cuối GET / phục vụ trang HTML tĩnh một tệp nội tuyến.
- AC-7: Hiển thị đầy đủ reward, loss, 6 cơ, env steps/s, tiến độ bước, checkpoint.
"""

from __future__ import annotations

import ast
import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from mma_ai.monitoring.dashboard import Server, serve


def _schema() -> dict[str, Any]:
    path = (
        Path(__file__).parents[2]
        / "specs/003-ppo-train-repro/contracts/progress-snapshot.schema.json"
    )
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _valid_snapshot() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "run_id": "20261010T010101Z_elbow_s42",
        "stage": "elbow",
        "seed": 42,
        "status": "running",
        "timestamp_utc": "2026-10-10T01:01:05Z",
        "update_idx": 5,
        "env_steps": 10240,
        "total_steps": 100000,
        "env_steps_per_second": 1520.4,
        "mean_return": -42.5,
        "loss": {"policy": -0.015, "value": 28.3, "entropy": 3.9},
        "activation": {
            "muscle_names": ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"],
            "mean": [0.25, 0.30, 0.28, 0.55, 0.49, 0.51],
        },
        "checkpoint": {
            "count": 1,
            "every_updates": 5,
            "last_path": "checkpoints/ckpt_u000005.pt",
            "last_update_idx": 5,
        },
        "history": {
            "env_steps": [2048, 4096, 6144, 8192, 10240],
            "mean_return": [-55.0, -51.2, -47.8, -44.1, -42.5],
            "value_loss": [45.1, 39.8, 34.2, 30.1, 28.3],
        },
    }


def _hash_directory(directory: Path) -> dict[str, str]:
    """Tính bảng băm SHA-256 cho toàn bộ tệp trong thư mục để kiểm tra tính chỉ-đọc."""
    hashes: dict[str, str] = {}
    for item in sorted(directory.rglob("*")):
        if item.is_file():
            content = item.read_bytes()
            hashes[str(item.relative_to(directory))] = hashlib.sha256(content).hexdigest()
    return hashes


def test_progress_endpoint_matches_schema(tmp_path: Path) -> None:
    """FR-020, API-TRN-0001, AC-7: GET /api/progress trả 200 và khớp JSON schema."""
    snapshot = _valid_snapshot()
    progress_file = tmp_path / "progress.json"
    progress_file.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    server: Server = serve(tmp_path, host="127.0.0.1", port=0)
    assert isinstance(server, Server)
    try:
        url = f"{server.url}/api/progress"
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5.0) as response:
            assert response.status == 200
            assert "application/json" in response.headers.get("Content-Type", "")
            raw = response.read().decode("utf-8")
            data = json.loads(raw)

        Draft202012Validator(_schema(), format_checker=FormatChecker()).validate(data)
        assert data["run_id"] == snapshot["run_id"]
        assert data["update_idx"] == 5
        assert data["env_steps"] == 10240
    finally:
        server.close()


def test_progress_503_when_no_file(tmp_path: Path) -> None:
    """FR-020, API-TRN-0001, INV-005, AC-7: GET /api/progress trả 503 khi chưa có tệp."""
    server = serve(tmp_path, host="127.0.0.1", port=0)
    try:
        url = f"{server.url}/api/progress"
        request = urllib.request.Request(url, method="GET")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(request, timeout=5.0)

        error = exc_info.value
        assert error.code == 503
        payload = json.loads(error.read().decode("utf-8"))
        assert payload == {"error": "chưa có dữ liệu"}
    finally:
        server.close()


def test_page_lists_required_panels(tmp_path: Path) -> None:
    """FR-020, API-TRN-0002, AC-7: GET / trả trang HTML tĩnh chứa đủ 6 khối giao diện."""
    server = serve(tmp_path, host="127.0.0.1", port=0)
    try:
        url = f"{server.url}/"
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5.0) as response:
            assert response.status == 200
            assert "text/html" in response.headers.get("Content-Type", "")
            html = response.read().decode("utf-8")

        # Khẳng định HTML chứa đủ các khối theo đặc tả
        assert "reward" in html.lower() or "phần thưởng" in html.lower()
        assert "loss" in html.lower() or "tổn thất" in html.lower()
        assert "kích hoạt" in html.lower() or "activation" in html.lower()
        assert "steps" in html.lower() or "tiến độ" in html.lower()
        assert "checkpoint" in html.lower()
        assert "chưa có dữ liệu" in html

        # Khẳng định không có liên kết tới CDN hay tài nguyên mạng bên ngoài
        assert "http://" not in html
        assert "https://" not in html
    finally:
        server.close()


def test_dashboard_is_read_only(tmp_path: Path) -> None:
    """FR-021, INV-005, AC-7: POST/PUT/DELETE bị 405 và băm thư mục run không đổi."""
    snapshot = _valid_snapshot()
    progress_file = tmp_path / "progress.json"
    progress_file.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
    meta_file = tmp_path / "config_snapshot.txt"
    meta_file.write_text("config: original", encoding="utf-8")

    initial_hashes = _hash_directory(tmp_path)

    server = serve(tmp_path, host="127.0.0.1", port=0)
    try:
        endpoints = [
            ("/", "POST"),
            ("/", "PUT"),
            ("/", "DELETE"),
            ("/api/progress", "POST"),
            ("/api/progress", "PUT"),
            ("/api/progress", "DELETE"),
            ("/malicious", "POST"),
        ]

        for path, method in endpoints:
            url = f"{server.url}{path}"
            request = urllib.request.Request(
                url, data=b'{"payload": "hostile"}', method=method
            )
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(request, timeout=5.0)
            assert exc_info.value.code == 405
            assert "GET" in exc_info.value.headers.get("Allow", "")

        # Kiểm tra bảng băm sau khi nhận các yêu cầu ghi
        post_hashes = _hash_directory(tmp_path)
        assert post_hashes == initial_hashes
    finally:
        server.close()


def test_dashboard_loopback_only(tmp_path: Path) -> None:
    """INV-005, AC-7: Chỉ cho phép lắng nghe trên địa chỉ loopback."""
    with pytest.raises(ValueError, match="loopback|vòng lặp ngược"):
        serve(tmp_path, host="0.0.0.0", port=0)

    with pytest.raises(ValueError, match="loopback|vòng lặp ngược"):
        serve(tmp_path, host="192.168.1.50", port=0)

    # loopback 127.0.0.1 và localhost phải khởi chạy thành công
    server1 = serve(tmp_path, host="127.0.0.1", port=0)
    try:
        assert server1.host == "127.0.0.1"
        assert server1.port > 0
    finally:
        server1.close()

    server2 = serve(tmp_path, host="localhost", port=0)
    try:
        assert server2.host == "localhost"
        assert server2.port > 0
    finally:
        server2.close()


def test_snapshot_latency_le_5s(tmp_path: Path) -> None:
    """NFR-PERF-002, AC-7: Độ trễ từ lúc ghi số liệu đến lúc nhận phản hồi <= 5 giây."""
    now_utc = datetime.now(timezone.utc)
    timestamp_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    snapshot = _valid_snapshot()
    snapshot["timestamp_utc"] = timestamp_str
    progress_file = tmp_path / "progress.json"
    progress_file.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    server = serve(tmp_path, host="127.0.0.1", port=0)
    try:
        url = f"{server.url}/api/progress"
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5.0) as response:
            assert response.status == 200
            data = json.loads(response.read().decode("utf-8"))

        recorded_time = datetime.fromisoformat(data["timestamp_utc"].replace("Z", "+00:00"))
        fetch_time = datetime.now(timezone.utc)
        latency = (fetch_time - recorded_time).total_seconds()

        assert latency >= 0.0
        assert latency <= 5.0
    finally:
        server.close()


def test_unknown_path_404(tmp_path: Path) -> None:
    """API-TRN-0001, API-TRN-0002, INV-005: Đường dẫn lạ trả về 404 Not Found."""
    server = serve(tmp_path, host="127.0.0.1", port=0)
    try:
        bad_paths = ["/unknown", "/api/other", "/etc/passwd", "/.."]
        for path in bad_paths:
            url = f"{server.url}{path}"
            request = urllib.request.Request(url, method="GET")
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(request, timeout=5.0)
            assert exc_info.value.code == 404
    finally:
        server.close()


def test_starting_snapshot_with_nulls(tmp_path: Path) -> None:
    """FR-020, API-TRN-0001, AC-7: Ảnh chụp trạng thái khởi động với các trường null."""
    snapshot: dict[str, Any] = {
        "schema_version": "1.0.0",
        "run_id": "20261010T010101Z_elbow_s42",
        "stage": "elbow",
        "seed": 42,
        "status": "starting",
        "timestamp_utc": "2026-10-10T01:01:01Z",
        "update_idx": 0,
        "env_steps": 0,
        "total_steps": 100000,
        "env_steps_per_second": None,
        "mean_return": None,
        "loss": None,
        "activation": None,
        "checkpoint": {
            "count": 0,
            "every_updates": 10,
            "last_path": None,
            "last_update_idx": None,
        },
        "history": {"env_steps": [], "mean_return": [], "value_loss": []},
    }
    progress_file = tmp_path / "progress.json"
    progress_file.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    with serve(tmp_path, host="127.0.0.1", port=0) as server:
        url = f"{server.url}/api/progress"
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5.0) as response:
            assert response.status == 200
            data = json.loads(response.read().decode("utf-8"))

        Draft202012Validator(_schema(), format_checker=FormatChecker()).validate(data)
        assert data["status"] == "starting"
        assert data["loss"] is None
        assert data["activation"] is None


def test_dashboard_no_training_imports() -> None:
    """INV-005, FR-021: Module dashboard không được nhập torch, trainer hoặc ppo."""
    source_path = Path(__file__).parents[2] / "src/mma_ai/monitoring/dashboard.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    forbidden = {"torch", "mma_ai.learning.trainer", "mma_ai.learning.ppo"}
    found_imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found_imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found_imports.add(node.module)

    for item in found_imports:
        for f in forbidden:
            assert not (item == f or item.startswith(f + ".")), (
                f"dashboard.py không được phép import '{item}'"
            )


def test_finished_status_snapshots(tmp_path: Path) -> None:
    """FR-020, API-TRN-0001, AC-7: Kiểm tra các trạng thái kết thúc done, error, interrupted."""
    for st in ("done", "error", "interrupted"):
        snapshot = _valid_snapshot()
        snapshot["status"] = st
        progress_file = tmp_path / "progress.json"
        progress_file.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

        with serve(tmp_path, host="127.0.0.1", port=0) as server:
            url = f"{server.url}/api/progress"
            request = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(request, timeout=5.0) as response:
                assert response.status == 200
                data = json.loads(response.read().decode("utf-8"))
            assert data["status"] == st


def test_two_servers_in_one_process_keep_their_own_run_dir(tmp_path: Path) -> None:
    """INV-005, FR-020, F-006: Hai máy chủ trong cùng tiến trình giữ run_dir độc lập."""
    dir_a = tmp_path / "run_a"
    dir_b = tmp_path / "run_b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_a / "progress.json").write_text(json.dumps({"run": "a"}), encoding="utf-8")
    (dir_b / "progress.json").write_text(json.dumps({"run": "b"}), encoding="utf-8")

    with serve(dir_a, host="127.0.0.1", port=0) as server_a:
        with serve(dir_b, host="127.0.0.1", port=0) as server_b:
            url_a = f"{server_a.url}/api/progress"
            req_a = urllib.request.Request(url_a, method="GET")
            with urllib.request.urlopen(req_a, timeout=5.0) as res_a:
                assert res_a.status == 200
                data_a = json.loads(res_a.read().decode("utf-8"))
                assert data_a["run"] == "a"

            url_b = f"{server_b.url}/api/progress"
            req_b = urllib.request.Request(url_b, method="GET")
            with urllib.request.urlopen(req_b, timeout=5.0) as res_b:
                assert res_b.status == 200
                data_b = json.loads(res_b.read().decode("utf-8"))
                assert data_b["run"] == "b"
