"""Kiểm thử đầu-cuối các tiêu chí nghiệm thu PPO qua entrypoint thật.

Các kiểm thử này chỉ gọi ``python -m mma_ai.learning.cli`` và
``python -m mma_ai.monitoring.cli`` trong tiến trình con; không dựng trực tiếp
router HTTP, Trainer hay môi trường giả.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SIX_MUSCLES = ("TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA")


def _wait_until(predicate: Callable[[], bool], *, timeout: float, message: str) -> None:
    """Chờ điều kiện quan sát được thay vì chờ theo thời lượng cố định."""
    deadline = time.monotonic() + timeout
    waiter = threading.Event()
    while time.monotonic() < deadline:
        if predicate():
            return
        waiter.wait(0.05)
    raise AssertionError(message)


def _runs(root: Path) -> list[Path]:
    """Trả các thư mục run có manifest, theo thứ tự tên."""
    if not root.is_dir():
        return []
    return sorted(path for path in root.iterdir() if (path / "manifest.json").is_file())


def _ui_runs(root: Path) -> list[Path]:
    """Trả các thư mục run có giao diện quan sát đã sẵn sàng."""
    if not root.is_dir():
        return []
    return sorted(
        path for path in root.iterdir() if path.is_dir() and (path / "ui.json").is_file()
    )


def _manifest(run_dir: Path) -> dict[str, Any]:
    """Nạp hồ sơ JSON của một lượt train đã hoàn thành."""
    return cast(
        dict[str, Any], json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    )


def _write_config(
    tmp_path: Path, name: str, *, total_steps: int = 4096, ui: str = "none"
) -> tuple[Path, Path]:
    """Tạo cấu hình smoke riêng để mọi entrypoint thật ghi vào vùng tạm cô lập."""
    config = yaml.safe_load(
        files("mma_ai.learning").joinpath("train_elbow_smoke.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(config, dict)
    runs_dir = tmp_path / f"runs_{name}"
    runs_dir.mkdir()
    config["paths"]["runs_dir"] = os.path.relpath(runs_dir, PROJECT_ROOT)
    config["schedule"]["total_timesteps"] = total_steps
    config["schedule"]["n_steps"] = 2048
    config["schedule"]["batch_size"] = 256
    config["checkpoint"]["every_updates"] = 1
    config["ui"]["mode"] = ui
    config["ui"]["snapshot_interval_s"] = 0.1
    config_path = tmp_path / f"{name}.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return config_path, runs_dir


def _run_train(args: list[str], *, timeout: float = 240.0) -> subprocess.CompletedProcess[str]:
    """Chạy CLI train thật ở chế độ headless."""
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    cli_args = [*args] if "--ui" in args else [*args, "--ui", "none"]
    return subprocess.run(
        [
            "uv",
            "run",
            "--isolated",
            "--extra",
            "rl",
            "python",
            "-m",
            "mma_ai.learning.cli",
            *cli_args,
        ],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def completed_runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Tạo ba lượt smoke thật: hai cùng seed và một seed khác cho AC-1…AC-6."""
    tmp_path = tmp_path_factory.mktemp("e2e_train")
    records: dict[str, Any] = {"tmp_path": tmp_path}
    for name, seed in (("first", 42), ("same", 42), ("different", 137)):
        config_path, runs_dir = _write_config(tmp_path, name)
        result = _run_train(["--stage", "elbow", "--seed", str(seed), "--config", str(config_path)])
        assert result.returncode == 0, f"Train {name} lỗi:\n{result.stderr}\n{result.stdout}"
        created = _runs(runs_dir)
        assert len(created) == 1, f"Train {name} không tạo đúng một run: {created}"
        records[name] = {"result": result, "run_dir": created[0], "manifest": _manifest(created[0])}
    return records


def test_ac_1_train_smoke(completed_runs: dict[str, Any]) -> None:
    """AC-1, FR-019, SC-001: smoke CLI ghi TB/checkpoint và không có NaN/Inf."""
    record = completed_runs["first"]
    run_dir = record["run_dir"]
    manifest = record["manifest"]
    assert "Huấn luyện hoàn tất thành công" in record["result"].stdout
    assert any((run_dir / "tb").glob("events.out.tfevents.*")), "Thiếu log TensorBoard"
    assert len(list((run_dir / "checkpoints").glob("*.pt"))) >= 2, "Thiếu checkpoint định kỳ/final"
    assert manifest["numeric_health"] == {"nan_count": 0, "inf_count": 0}


def test_ac_2_checkpoint_roundtrip_and_resume(completed_runs: dict[str, Any]) -> None:
    """AC-2, SC-002: nạp checkpoint giữ hành động xác định và resume tạo run con."""
    parent = completed_runs["first"]
    parent_dir: Path = parent["run_dir"]
    parent_manifest = parent["manifest"]
    checkpoint = sorted((parent_dir / "checkpoints").glob("*_final.pt"))[-1]
    script = """
import json
import numpy as np
from mma_ai.learning.checkpoint import load_policy
np.random.seed(20261010)
obs = np.random.normal(size=(64, 14)).astype(np.float64)
first = load_policy(__import__('sys').argv[1]).act_deterministic(obs)
second = load_policy(__import__('sys').argv[1]).act_deterministic(obs)
print(json.dumps({"max_delta": float(np.max(np.abs(first - second))), "shape": list(first.shape)}))
"""
    policy_check = subprocess.run(
        ["uv", "run", "--isolated", "--extra", "rl", "python", "-c", script, str(checkpoint)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert policy_check.returncode == 0, policy_check.stderr
    action_result = json.loads(policy_check.stdout)
    assert action_result["shape"] == [64, 6]
    assert action_result["max_delta"] <= 1e-6

    child_config, child_runs = _write_config(
        completed_runs["tmp_path"], "resume", total_steps=6144
    )
    resumed = _run_train(
        [
            "--stage",
            "elbow",
            "--seed",
            "42",
            "--config",
            str(child_config),
            "--resume",
            str(checkpoint),
        ]
    )
    assert resumed.returncode == 0, resumed.stderr
    children = _runs(child_runs)
    assert len(children) == 1
    child_manifest = _manifest(children[0])
    assert child_manifest["resumed_from"]["run_id"] == parent_manifest["run_id"]
    assert child_manifest["resumed_from"]["checkpoint_sha256"]


def test_ac_3_run_manifest_fields(completed_runs: dict[str, Any]) -> None:
    """AC-3, SC-003: hồ sơ thật có trường tái lập, mô hình, checkpoint và đo runtime."""
    manifest = completed_runs["first"]["manifest"]
    expected = {
        "seed",
        "config",
        "library_versions",
        "model",
        "checkpoints",
        "reward_metrics",
        "throughput",
    }
    assert expected.issubset(manifest)
    assert manifest["seed"] == 42 and len(manifest["model"]["sha256"]) == 64
    assert manifest["checkpoints"] and manifest["reward_metrics"]["head_mean_return"]
    assert manifest["throughput"]["env_steps_per_second"] > 0.0
    assert manifest["throughput"]["wall_clock_seconds"] > 0.0


def test_ac_4_same_seed_within_tolerance(completed_runs: dict[str, Any]) -> None:
    """AC-4, SC-004: cùng seed trong dung sai và seed khác có đường reward khác."""
    first = completed_runs["first"]["manifest"]
    same = completed_runs["same"]["manifest"]
    different = completed_runs["different"]["manifest"]
    first_curve = first["reward_metrics"]["head_mean_return"]
    same_curve = same["reward_metrics"]["head_mean_return"]
    tolerance = first["reproducibility"]["rel_tolerance"]
    assert len(first_curve) == len(same_curve) > 0
    for actual, expected in zip(same_curve, first_curve, strict=True):
        assert math.isfinite(actual) and math.isfinite(expected)
        assert abs(actual - expected) / max(abs(expected), 1e-9) <= tolerance
    assert first_curve != different["reward_metrics"]["head_mean_return"]


def test_ac_5_stage_not_implemented(tmp_path: Path) -> None:
    """AC-5, 003/AC-5, SC-005: stage ngoài elbow trả mã 3 trước khi tạo thư mục run."""
    config_path, runs_dir = _write_config(tmp_path, "unsupported")
    result = _run_train(["--stage", "balance", "--config", str(config_path)])
    assert result.returncode == 3
    assert "chưa triển khai" in result.stderr.lower()
    assert _runs(runs_dir) == []


def test_ac_6_network_2x256(completed_runs: dict[str, Any]) -> None:
    """AC-6, SC-006: hồ sơ run ghi đúng hai lớp ẩn 256 cho actor và critic."""
    network = completed_runs["first"]["manifest"]["config"]["network"]
    assert network["actor_hidden"] == [256, 256]
    assert network["critic_hidden"] == [256, 256]


def test_ac_7_progress_ui_live(tmp_path: Path) -> None:
    """AC-7, NFR-PERF-002, INV-005: dashboard thật hiển thị số liệu và chỉ-đọc."""
    config_path, runs_dir = _write_config(tmp_path, "dashboard", ui="web")
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    proc = subprocess.Popen(
        [
            "uv", "run", "--isolated", "--extra", "rl", "python", "-m", "mma_ai.learning.cli",
            "--stage", "elbow", "--seed", "42", "--config", str(config_path), "--ui", "web",
            "--ui-port", "0",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    ui_pid: int | None = None
    try:
        _wait_until(
            lambda: len(_ui_runs(runs_dir)) == 1,
            timeout=20.0,
            message="Không thấy ui.json từ monitoring CLI",
        )
        run_dir = _ui_runs(runs_dir)[0]
        ui_info = json.loads((run_dir / "ui.json").read_text(encoding="utf-8"))
        ui_url = ui_info["url"]
        ui_pid = int(ui_info["pid"])

        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

        console_errors: list[str] = []
        snapshot_ready = False
        capture_dir = os.environ.get("AI_SDLC_CAPTURE_DIR")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()

            def record_console_error(message: Any) -> None:
                if message.type == "error" and "Failed to load resource" not in message.text:
                    console_errors.append(message.text)

            def record_http_error(response: Any) -> None:
                is_progress_request = response.url.rstrip("/").endswith("/api/progress")
                if response.status == 503 and is_progress_request and not snapshot_ready:
                    return
                if response.status >= 400:
                    console_errors.append(f"HTTP {response.status}: {response.url}")

            page.on("console", record_console_error)
            page.on("pageerror", lambda error: console_errors.append(str(error)))
            page.on("response", record_http_error)
            page.goto(ui_url, wait_until="domcontentloaded")
            page.wait_for_function(
                "document.querySelectorAll('#muscles-list .muscle-row').length === 6"
            )
            snapshot_ready = True
            assert page.locator("h1").count() == 1
            panels = page.locator(
                "#panel-reward, #panel-loss, #panel-activation, "
                "#panel-throughput, #panel-checkpoint"
            )
            assert panels.count() == 5
            assert page.locator("#muscles-list").inner_text().count("\n") >= 5
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            assert page.locator("html").get_attribute("lang") == "vi"
            if capture_dir:
                output = Path(capture_dir)
                output.mkdir(parents=True, exist_ok=True)
                page.screenshot(
                    path=str(output / "AC-7-dashboard-desktop-1280x800.png"),
                    animations="disabled",
                    full_page=True,
                )
                context.tracing.stop(path=str(output / "AC-7-dashboard-desktop-1280x800.zip"))
            else:
                context.tracing.stop()
            context.close()
            browser.close()
        assert not console_errors, f"Console dashboard có lỗi runtime: {console_errors}"

        request = urllib.request.Request(f"{ui_url}/api/progress", method="POST")
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=5.0)
        assert error.value.code == 405
        stdout, stderr = proc.communicate(timeout=240.0)
        assert proc.returncode == 0, f"Train dashboard lỗi:\n{stderr}\n{stdout}"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=10.0)
        if ui_pid is not None:
            try:
                os.kill(ui_pid, 15)
            except ProcessLookupError:
                pass
