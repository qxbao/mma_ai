"""006: kiểm thử đầu-cuối (E2E) trên điểm vào (entrypoint) CLI thật.

Đối chiếu tương đương (parity) với mốc Linux (baseline) trước compat.
Thu dấu vết (trace) theo AC khi cổng cấp AI_SDLC_CAPTURE_DIR.
"""

from __future__ import annotations

import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import validate

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_SHA = "d1665d962f0d116c5f2e369c4ea527687f7e9964"
BASELINE_FILE = Path(__file__).with_name("data") / "platform-linux-baseline.json"


def _capture(name: str, payload: Any) -> None:
    """Ghi dấu vết có tên AC vào thư mục do cổng cấp, không tự đặt đường dẫn."""
    destination = os.environ.get("AI_SDLC_CAPTURE_DIR")
    if destination:
        root = Path(destination)
        root.mkdir(parents=True, exist_ok=True)
        (root / f"006-{name}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )


def _environment(source: Path = PROJECT_ROOT / "src") -> dict[str, str]:
    """Chọn mã cần kiểm, giữ backend thật và ép không có màn hình (headless)."""
    environment = os.environ.copy()
    environment.pop("DISPLAY", None)
    environment.pop("WAYLAND_DISPLAY", None)
    environment["MMA_AI_FORCE_NO_DISPLAY"] = "1"
    environment["PYTHONPATH"] = str(source)
    return environment


def _run(
    module: str, arguments: list[str], *, environment: dict[str, str], timeout: float = 240
) -> dict[str, Any]:
    """Gọi CLI thật với phụ thuộc khai trong manifest và tệp khóa (lockfile)."""
    command = [
        "uv",
        "run",
        "--isolated",
        "--extra",
        "rl",
        "--extra",
        "eval",
        "python",
        "-m",
        module,
        *arguments,
    ]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.decode("utf-8"),
        "stderr": completed.stderr.decode("utf-8"),
        "elapsed_s": time.monotonic() - started,
    }


def _exercise_entrypoints(work: Path, source: Path) -> dict[str, Any]:
    """Sinh dữ liệu bằng train/replay/benchmark thật, cùng seed và cấu hình."""
    work.mkdir(parents=True, exist_ok=True)
    environment = _environment(source)
    observer = work / "observer"
    observer.mkdir()
    # Chỉ quan sát sys.modules khi thoát, không thay hàm hay giá trị sản phẩm.
    (observer / "sitecustomize.py").write_text(
        "import atexit, json, os, sys\n"
        "from pathlib import Path\n"
        "def _record_imports():\n"
        "    root = Path(__file__).parent\n"
        "    data = {'argv': sys.argv, 'modules': sorted(sys.modules),\n"
        "        'environment': {key: os.environ.get(key) for key in (\n"
        "            'MUJOCO_GL', 'MMA_AI_FORCE_NO_DISPLAY', 'DISPLAY', 'WAYLAND_DISPLAY')},\n"
        "        'module_origins': {name: getattr(sys.modules[name], '__file__', None)\n"
        "            for name in ('mujoco', 'glfw', 'mujoco.glfw', 'mujoco.viewer')\n"
        "            if name in sys.modules}}\n"
        "    (root / (str(os.getpid()) + '.json')).write_text(\n"
        "        json.dumps(data, ensure_ascii=False), encoding='utf-8')\n"
        "atexit.register(_record_imports)\n",
        encoding="utf-8",
    )
    environment["PYTHONPATH"] = os.pathsep.join((str(observer), str(source)))
    config = yaml.safe_load(
        (source / "mma_ai/learning/train_elbow_smoke.yaml").read_text(encoding="utf-8")
    )
    runs = work / "runs"
    config["paths"]["runs_dir"] = Path(os.path.relpath(runs, PROJECT_ROOT)).as_posix()
    config_path = work / "train.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    train = _run(
        "mma_ai.learning.cli",
        ["--stage", "elbow", "--seed", "42", "--ui", "none", "--config", str(config_path)],
        environment=environment,
    )
    assert train["returncode"] == 0, train
    manifests = list(runs.glob("*/manifest.json"))
    assert len(manifests) == 1, manifests
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    checkpoints = list(manifests[0].parent.glob("checkpoints/*_final.pt"))
    assert len(checkpoints) == 1, checkpoints
    episode = work / "episode.json"
    demo = _run(
        "mma_ai.visualization.cli",
        [
            "--checkpoint",
            str(checkpoints[0]),
            "--headless",
            "--seed",
            "12345",
            "--save-episode",
            str(episode),
        ],
        environment=environment,
    )
    assert demo["returncode"] == 0, demo
    replay = _run(
        "mma_ai.visualization.cli",
        ["--episode", str(episode), "--headless"],
        environment=environment,
    )
    assert replay["returncode"] == 0, replay
    # Đo luồng CLI; cấu hình ngắn không nghiệm thu NFR-PERF-001 của spec 003.
    config["schedule"].update(total_timesteps=256, n_steps=128, batch_size=64, n_epochs=1)
    benchmark_config = work / "benchmark.yaml"
    benchmark_config.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    report_path = work / "benchmark.json"
    benchmark = _run(
        "mma_ai.learning.benchmark",
        [
            "--seed",
            "42",
            "--repeats",
            "5",
            "--total-steps",
            "256",
            "--config",
            str(benchmark_config),
            "--runs-dir",
            Path(os.path.relpath(work / "benchmark-runs", PROJECT_ROOT)).as_posix(),
            "--output",
            str(report_path),
        ],
        environment=environment,
    )
    assert report_path.is_file(), benchmark
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert benchmark["returncode"] == (0 if report["passed"] else 1), benchmark
    observations = [json.loads(p.read_text(encoding="utf-8")) for p in observer.glob("*.json")]
    assert len(observations) >= 14, "Thiếu quan sát tiến trình thật"
    return {
        "train": train,
        "demo": demo,
        "replay": replay,
        "benchmark": benchmark,
        "manifest": manifest,
        "summary": json.loads(replay["stdout"]),
        "report": report,
        "imports": observations,
        "work": str(work),
    }


@pytest.fixture(scope="module")
def platform_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """AC-1, AC-2, AC-3, AC-4: dùng chung dữ liệu sinh qua điểm vào thật."""
    records = _exercise_entrypoints(tmp_path_factory.mktemp("006-platform"), PROJECT_ROOT / "src")
    _capture("AC-1-AC-2-AC-3-AC-4-entrypoints", records)
    return records


def _compare_fields(baseline: Any, feature: Any, path: str = "") -> None:
    """So từng trường; dữ liệu có ở mốc không được mất hoặc thành rỗng."""
    if isinstance(baseline, dict):
        assert isinstance(feature, dict), path
        assert set(feature) == set(baseline), f"Khác tập khóa ở {path}"
        for key, value in baseline.items():
            _compare_fields(value, feature[key], f"{path}.{key}".lstrip("."))
    elif isinstance(baseline, list):
        assert isinstance(feature, list) and len(feature) == len(baseline), path
        for old, new in zip(baseline, feature, strict=True):
            _compare_fields(old, new, f"{path}[]")
    elif baseline is None:
        assert feature is None, path
    elif isinstance(baseline, bool):
        assert isinstance(feature, bool), path
    elif isinstance(baseline, (float, int)):
        assert type(feature) in (float, int) and math.isfinite(feature), path
    else:
        assert isinstance(feature, str), path
        assert not baseline or feature.strip(), f"Trường {path} bị rỗng"


def test_006_ac_1_ac_3_headless_replay_and_benchmark_exit_codes_match_baseline(
    platform_run: dict[str, Any],
) -> None:
    """AC-1, AC-3; FR-001, FR-008; INV-001: mã thoát cũ, không nạp GLFW/viewer."""
    baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    assert baseline["sha"] == BASELINE_SHA
    assert platform_run["replay"]["returncode"] == baseline["exit_codes"]["replay"] == 0
    report = platform_run["report"]
    assert platform_run["benchmark"]["returncode"] == (0 if report["passed"] else 1)
    assert platform_run["summary"]["headless"] is True
    assert platform_run["summary"]["model_check"]["match"] is True
    assert report["view3d"]["measured"] is False and report["view3d"]["reason"]
    forbidden = {"glfw", "mujoco.glfw", "mujoco.viewer"}
    violations = [
        {
            "argv": item["argv"],
            "modules": sorted(set(item["modules"]) & forbidden),
            "environment": item["environment"],
            "module_origins": item["module_origins"],
        }
        for item in platform_run["imports"]
        if set(item["modules"]) & forbidden
    ]
    _capture("AC-1-AC-3-headless-imports", {"violations": violations})
    assert not violations, f"Đường không màn hình vẫn nạp thư viện hiển thị: {violations}"


def test_006_ac_1_ac_4_cli_outputs_same_keys_as_linux_baseline(
    platform_run: dict[str, Any],
) -> None:
    """AC-1, AC-4; FR-001, FR-011, FR-012; INV-001, INV-005; NFR-PARITY-001."""
    baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    for key in ("manifest", "summary", "report"):
        _compare_fields(baseline[key], platform_run[key], key)
    manifest = platform_run["manifest"]
    assert manifest["status"] == "done" and manifest["seed"] == 42
    assert manifest["numeric_health"] == {"nan_count": 0, "inf_count": 0}
    assert manifest["throughput"]["env_steps"] == 4096
    assert manifest["model"]["muscle_names"] == baseline["manifest"]["model"]["muscle_names"]
    for checkpoint in manifest["checkpoints"]:
        assert "\\" not in checkpoint["path"] and not Path(checkpoint["path"]).is_absolute()
    text_files = [
        p
        for p in Path(platform_run["work"]).rglob("*")
        if p.is_file() and p.suffix in {".json", ".jsonl", ".yaml", ".yml", ".md"}
    ]
    assert text_files
    for path in text_files:
        raw = path.read_bytes()
        assert b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf"), path
        raw.decode("utf-8")
    _capture("AC-1-AC-4-parity", {"baseline_sha": BASELINE_SHA, "text_files": len(text_files)})


def test_006_ac_1_ac_2_ac_5_check_env_then_train_smoke_then_manifest_ram_plausible(
    tmp_path: Path,
) -> None:
    """AC-1, AC-2, AC-5; FR-004, FR-017; INV-007; NFR-ENV-001: ≤30 s, RAM hợp lệ."""
    check = _run("mma_ai.compat.env_report", ["--json"], environment=_environment())
    _capture("AC-5-check-env", check)
    assert check["returncode"] == 0 and check["elapsed_s"] <= 30, check
    report = json.loads(check["stdout"])
    schema = json.loads(
        (
            PROJECT_ROOT / "specs/006-cross-platform-support/contracts/check-env-report.schema.json"
        ).read_text(encoding="utf-8")
    )
    validate(report, schema)
    if sys.platform == "win32":
        expected = "windows"
    elif sys.platform == "darwin":
        expected = "macos"
    else:
        release = platform.release().lower()
        is_wsl = "microsoft" in release or "wsl" in release or os.environ.get("WSL_DISTRO_NAME")
        expected = "wsl2" if is_wsl else "linux"
    assert report["os"]["kind"] == expected
    # Chỉ train SAU khi chẩn đoán môi trường xanh, không dựa thứ tự test của pytest.
    config = yaml.safe_load(
        (PROJECT_ROOT / "src/mma_ai/learning/train_elbow_smoke.yaml").read_text(encoding="utf-8")
    )
    runs = tmp_path / "runs"
    config["paths"]["runs_dir"] = Path(os.path.relpath(runs, PROJECT_ROOT)).as_posix()
    config_path = tmp_path / "smoke.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    train = _run(
        "mma_ai.learning.cli",
        ["--config", str(config_path), "--ui", "none"],
        environment=_environment(),
    )
    assert train["returncode"] == 0, train
    manifests = list(runs.glob("*/manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["status"] == "done" and "ram_peak_mb" in manifest["resources"]
    ram = manifest["resources"]["ram_peak_mb"]
    assert ram is None or (type(ram) in (int, float) and math.isfinite(ram) and ram > 0)
    _capture("AC-2-AC-5-check-then-train", {"check": check, "train": train, "manifest": manifest})


def test_006_ac_6_capability_collection_ratio_and_reasons(tmp_path: Path) -> None:
    """AC-6; FR-021, FR-022; INV-006; NFR-CI-001: loại ≤5%, mọi mục có lý do."""
    report_path = tmp_path / "capabilities.json"
    command = [
        "uv",
        "run",
        "--isolated",
        "--with",
        "pytest",
        "--with",
        "pytest-playwright",
        "python",
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-p",
        "no:cacheprovider",
        "--capability-report",
        str(report_path),
    ]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=90,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["collected"] > 0 and report["ratio"] <= 0.05
    assert report["deselected"] == len(report["items"])
    assert report["ratio"] == report["deselected"] / report["collected"]
    for item in report["items"]:
        assert item["nodeid"] and item["marker"] and item["reason"].strip(), item
    _capture("AC-6-capability-collection", {"command": command, "report": report})


@pytest.mark.parametrize("arguments", [["--json"], []], ids=["json", "texte"])
def test_006_ac_4_ac_5_env_report_survives_cp1252(arguments: list[str]) -> None:
    """AC-4, AC-5; FR-013, FR-024; NFR-ENC-001: UTF-8 dù luồng khai cp1252."""
    environment = _environment()
    environment["PYTHONIOENCODING"] = "cp1252"
    result = _run("mma_ai.compat.env_report", arguments, environment=environment)
    _capture(f"AC-4-AC-5-cp1252-{'json' if arguments else 'texte'}", result)
    assert result["returncode"] == 0, result
    assert "UnicodeEncodeError" not in result["stdout"] + result["stderr"]
    assert any(ord(c) > 127 for c in result["stdout"] + result["stderr"])
    if arguments:
        assert json.loads(result["stdout"])["overall"] == "ok"
    else:
        assert "Môi trường đạt yêu cầu." in result["stdout"]
