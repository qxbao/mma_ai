"""Kiểm thử hợp đồng hồ sơ run qua CLI (test_manifest_contract.py).

Hiện thực và xác minh US3, AC-3:
- FR-011, AC-3, SC-003: Mỗi lượt chạy huấn luyện (training run) tạo một thư mục lượt chạy
  mới duy nhất (unique run directory), chứa hồ sơ thí nghiệm (run manifest - manifest.json)
  hợp lệ tuyệt đối theo khuôn JSON Schema run-manifest.schema.json, không ghi đè lượt chạy cũ.
- FR-011, INV-001, SC-003: Hai lần chạy liên tiếp cùng giai đoạn (stage) và hạt giống (seed)
  tạo ra hai thư mục khác nhau; thư mục lượt chạy trước giữ nguyên mã băm toàn vẹn cây thư mục
  (hash tree digest - tính bất biến immutability).
- FR-011, AC-3, SC-003: Mã băm SHA-256 tệp XML mô hình trong hồ sơ lượt chạy khớp tuyệt đối
  với hồ sơ mô hình model_record() từ môi trường cánh tay khuỷu (elbow reach environment).
- FR-012, NFR-RES-001, AC-3: Hồ sơ lượt chạy ghi nhận đủ 100% các trường tài nguyên (CPU, RAM, GPU);
  khi không có GPU/CUDA thì các trường GPU/VRAM ghi tường minh giá trị rỗng (null).
- FR-013, AC-3: Hồ sơ lượt chạy ghi nhận thông lượng các bước môi trường trên giây (env steps/s)
  và thời gian chạy thực (wall-clock seconds) do máy đo bằng đồng hồ thật (perf_counter).
- FR-011, INV-001, SC-003: Trạng thái (status) ghi nhận 'running' lúc đang chạy, và được thay thế
  nguyên tử (atomic replacement) sang 'done' khi kết thúc thành công.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from train_fixtures import (
    hash_tree,
    list_runs,
    load_manifest,
    load_schema_registry,
    run_train_cli,
    smoke_config,
)


def _load_contract_schema(name: str) -> dict[str, Any]:
    """Nạp nội dung lược đồ JSON Schema từ thư mục hợp đồng."""
    schema_path = Path.cwd() / "specs" / "003-ppo-train-repro" / "contracts" / name
    if not schema_path.is_file():
        schema_path = (
            Path(__file__).resolve().parents[2]
            / "specs"
            / "003-ppo-train-repro"
            / "contracts"
            / name
        )
    return json.loads(schema_path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _build_manifest_validator() -> Draft202012Validator:
    """Khởi tạo bộ thẩm định lược đồ hồ sơ lượt chạy kèm registry tham chiếu."""
    schema = _load_contract_schema("run-manifest.schema.json")
    registry = load_schema_registry()
    return Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )


def test_manifest_contract_independent_assertion() -> None:
    """FR-011, FR-012, FR-013, INV-001, NFR-RES-001, SC-003, AC-3: Khẳng định độc lập trên base.

    Đảm bảo kiểm thử không bị bỏ qua toàn bộ (skip) khi thiếu phụ thuộc tuỳ chọn.
    Xác minh sự hiện diện của các mô-đun cốt lõi, tính đầy đủ của 20 trường bắt buộc trong hợp đồng
    hồ sơ run-manifest.schema.json, 7 trường tài nguyên và 7 thư viện bắt buộc.
    """
    # 1. Xác minh các mô-đun cốt lõi có mặt trên base
    assert importlib.util.find_spec("mma_ai.learning.manifest") is not None, (
        "Thiếu mô-đun mma_ai.learning.manifest trên base"
    )
    assert importlib.util.find_spec("mma_ai.learning.cli") is not None, (
        "Thiếu mô-đun mma_ai.learning.cli trên base"
    )

    # 2. Xác minh lược đồ hợp đồng run-manifest.schema.json
    schema = _load_contract_schema("run-manifest.schema.json")
    required_keys = set(schema.get("required", []))
    expected_20_keys = {
        "schema_version",
        "run_id",
        "stage",
        "status",
        "seed",
        "resumed_from",
        "started_utc",
        "finished_utc",
        "config",
        "library_versions",
        "model",
        "device",
        "checkpoints",
        "reward_metrics",
        "throughput",
        "resources",
        "numeric_health",
        "reproducibility",
        "ui",
        "error",
    }
    assert required_keys == expected_20_keys, (
        f"Thiếu hoặc thừa trường bắt buộc trong run-manifest.schema.json: "
        f"thiếu {expected_20_keys - required_keys}, thừa {required_keys - expected_20_keys}"
    )

    # 3. Xác minh 7 trường tài nguyên trong schema
    res_properties = schema.get("properties", {}).get("resources", {}).get("required", [])
    expected_resources = {
        "cpu_model",
        "cpu_logical_cores",
        "cpu_utilization_pct",
        "ram_peak_mb",
        "gpu_name",
        "gpu_utilization_pct",
        "vram_peak_mb",
    }
    assert set(res_properties) == expected_resources, (
        f"Các trường tài nguyên trong schema không khớp 7 trường bắt buộc: {set(res_properties)}"
    )

    # 4. Xác minh 7 thư viện bắt buộc trong schema
    lib_properties = schema.get("properties", {}).get("library_versions", {}).get("required", [])
    expected_libs = {"python", "torch", "numpy", "gymnasium", "mujoco", "myo-sim", "tensorboard"}
    assert set(lib_properties) == expected_libs, (
        f"Thư viện bắt buộc trong schema không khớp 7 thư viện: {set(lib_properties)}"
    )


@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def manifest_smoke_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Khởi chạy một lượt smoke qua CLI thật để dùng chung cho các phép kiểm tra hồ sơ."""
    pytest.importorskip("torch", reason="Cần extra rl (torch) để thực thi huấn luyện PPO")
    pytest.importorskip("tensorboard", reason="Cần tensorboard để kiểm tra nhật ký chỉ số")

    tmp_dir = tmp_path_factory.mktemp("manifest_smoke_integration")
    config_file = smoke_config(tmp_dir)
    runs_dir = tmp_dir / "runs"

    result = run_train_cli(
        ["--stage", "elbow", "--seed", "42", "--config", str(config_file)],
        timeout=180.0,
    )
    assert result.exit_code == 0, (
        f"Lượt huấn luyện smoke thất bại với mã {result.exit_code}.\n"
        f"Stderr: {result.stderr}\nStdout: {result.stdout}"
    )

    created_runs = list_runs(runs_dir)
    assert len(created_runs) >= 1, "Không tìm thấy thư mục lượt chạy được tạo trong runs_dir"
    run_dir = created_runs[-1]
    manifest = load_manifest(run_dir)

    return {
        "result": result,
        "runs_dir": runs_dir,
        "run_dir": run_dir,
        "manifest": manifest,
        "tmp_dir": tmp_dir,
        "config_file": config_file,
    }


def test_manifest_fields_and_schema(manifest_smoke_run: dict[str, Any]) -> None:
    """FR-011, FR-012, FR-013, NFR-RES-001, SC-003, AC-3: Hồ sơ thật hợp schema và đủ các trường."""
    manifest: dict[str, Any] = manifest_smoke_run["manifest"]

    # 1. Thẩm định toàn diện tính hợp lệ theo JSON Schema
    validator = _build_manifest_validator()
    validator.validate(manifest)

    # 2. Khẳng định các trường cốt lõi của lượt chạy hoàn thành
    assert manifest["schema_version"] == "1.0.0", "Phiên bản schema không khớp '1.0.0'"
    assert manifest["stage"] == "elbow", "Giai đoạn lượt chạy không khớp 'elbow'"
    assert manifest["status"] == "done", "Trạng thái lượt chạy không phải 'done'"
    assert manifest["seed"] == 42, "Hạt giống ngẫu nhiên không khớp 42"
    assert manifest["resumed_from"] is None, "Lượt chạy mới không được có resumed_from"
    assert manifest["finished_utc"] is not None, "Thời điểm kết thúc không được là null"
    assert manifest["error"] is None, "Lượt chạy thành công không được ghi nhận lỗi"

    # 3. Khẳng định 7 thư viện bắt buộc trong library_versions
    expected_libs = {"python", "torch", "numpy", "gymnasium", "mujoco", "myo-sim", "tensorboard"}
    actual_libs = set(manifest.get("library_versions", {}).keys())
    assert expected_libs.issubset(actual_libs), (
        f"Thiếu thư viện bắt buộc trong library_versions: {expected_libs - actual_libs}"
    )

    # 4. Khẳng định thông tin mô hình cơ xương (musculoskeletal model)
    model_info = manifest["model"]
    assert len(model_info["sha256"]) == 64, "Mã băm XML SHA-256 phải có đúng 64 ký tự hex"
    assert len(model_info["muscle_names"]) == 6, "Mô hình khuỷu tay phải có đúng 6 cơ"
    assert model_info["source"].endswith(".xml"), "Nguồn mô hình phải trỏ tới tệp .xml"

    # 5. Khẳng định danh sách điểm kiểm tra (checkpoints)
    checkpoints = manifest["checkpoints"]
    assert isinstance(checkpoints, list) and len(checkpoints) >= 2, (
        f"Kỳ vọng ít nhất 2 điểm kiểm tra (định kỳ và final), nhận: {len(checkpoints)}"
    )

    # 6. Khẳng định chỉ số phần thưởng (reward metrics)
    reward_metrics = manifest["reward_metrics"]
    assert reward_metrics["n_updates"] > 0, "Số lượt cập nhật phải > 0"
    assert reward_metrics["n_episodes"] > 0, "Số tập huấn luyện phải > 0"
    assert reward_metrics["head_updates"] > 0, "Số lượt cập nhật đầu kỳ head_updates phải > 0"
    assert len(reward_metrics["head_mean_return"]) == reward_metrics["head_updates"], (
        "Số điểm head_mean_return không khớp head_updates"
    )

    # 7. Khẳng định thông lượng (throughput) do máy đo bằng đồng hồ thật (FR-013)
    throughput = manifest["throughput"]
    assert throughput["env_steps"] == 4096, "Tổng số bước môi trường lượt smoke phải là 4096"
    assert throughput["env_steps_per_second"] is not None
    assert throughput["env_steps_per_second"] > 0.0, (
        f"Thông lượng env_steps_per_second phải > 0, nhận: {throughput['env_steps_per_second']}"
    )
    assert throughput["wall_clock_seconds"] is not None
    assert throughput["wall_clock_seconds"] > 0.0, (
        f"Thời gian chạy thực wall_clock_seconds phải > 0, nhận: {throughput['wall_clock_seconds']}"
    )

    # 8. Khẳng định độ tin cậy số học (numeric health) và tính tái lập (reproducibility)
    numeric_health = manifest["numeric_health"]
    assert numeric_health["nan_count"] == 0, "Phát hiện giá trị NaN trong quá trình huấn luyện"
    assert numeric_health["inf_count"] == 0, "Phát hiện giá trị Inf trong quá trình huấn luyện"

    reproducibility = manifest["reproducibility"]
    assert reproducibility["rel_tolerance"] == 1e-6, "Dung sai tái lập không khớp 1e-6"
    assert reproducibility["head_updates"] == 10, "Số lượt đầu kỳ không khớp 10"
    assert reproducibility["deterministic_algorithms"] is True, "Phải bật thuật toán tất định"


def test_two_runs_two_dirs(tmp_path: Path) -> None:
    """FR-011, INV-001, SC-003, AC-3: Hai lần chạy cùng stage/seed tạo 2 thư mục, run 1 bất biến."""
    pytest.importorskip("torch", reason="Cần extra rl (torch) để thực thi huấn luyện PPO")
    pytest.importorskip("tensorboard", reason="Cần tensorboard để kiểm tra nhật ký chỉ số")

    # Cấu hình lượt chạy ngắn tối giản (2048 bước, 1 lượt cập nhật) để tối ưu thời gian thực thi
    config_file = smoke_config(
        tmp_path,
        total_timesteps=2048,
        n_steps=2048,
        every_updates=1,
    )
    runs_dir = tmp_path / "runs"

    # Lần chạy 1
    res1 = run_train_cli(
        ["--stage", "elbow", "--seed", "42", "--config", str(config_file)],
        timeout=120.0,
    )
    assert res1.exit_code == 0, f"Lần chạy 1 thất bại: {res1.stderr}"

    runs_after_1 = list_runs(runs_dir)
    assert len(runs_after_1) == 1, f"Kỳ vọng 1 thư mục run sau lần 1, nhận: {runs_after_1}"
    run_dir_1 = runs_after_1[0]

    # Ghi nhận mã băm toàn vẹn cây thư mục run 1 trước khi chạy run 2 (INV-001)
    digest_run_1_before = hash_tree(run_dir_1)

    # Lần chạy 2 (cùng stage 'elbow' và seed 42)
    res2 = run_train_cli(
        ["--stage", "elbow", "--seed", "42", "--config", str(config_file)],
        timeout=120.0,
    )
    assert res2.exit_code == 0, f"Lần chạy 2 thất bại: {res2.stderr}"

    runs_after_2 = list_runs(runs_dir)
    assert len(runs_after_2) == 2, f"Kỳ vọng 2 thư mục run sau lần 2, nhận: {runs_after_2}"
    assert run_dir_1 in runs_after_2, "Thư mục run 1 bị mất sau lần chạy 2"

    run_dir_2 = [r for r in runs_after_2 if r != run_dir_1][0]
    assert run_dir_1 != run_dir_2, f"Hai lần chạy trùng thư mục: {run_dir_1}"

    # Xác minh tính bất biến tuyệt đối của run 1: mã băm không đổi sau khi run 2 kết thúc
    digest_run_1_after = hash_tree(run_dir_1)
    assert digest_run_1_before == digest_run_1_after, (
        "INV-001 vi phạm: Nội dung thư mục run 1 bị thay đổi hoặc ghi đè sau lần chạy 2"
    )


def test_manifest_hash_matches_env_model_record(manifest_smoke_run: dict[str, Any]) -> None:
    """FR-011, AC-3, SC-003: Mã băm SHA-256 XML trong hồ sơ khớp với env.model_record()."""
    import mma_ai.environment.single_agent as sa

    env = sa.make_env(split="train")
    try:
        model_rec = env.model_record()
    finally:
        env.close()

    manifest: dict[str, Any] = manifest_smoke_run["manifest"]
    manifest_model = manifest["model"]

    assert manifest_model["sha256"] == model_rec["sha256"], (
        f"Mã băm SHA-256 trong hồ sơ ({manifest_model['sha256']}) "
        f"không khớp model_record của môi trường ({model_rec['sha256']})"
    )
    assert manifest_model["source"] == model_rec["source"], (
        f"Đường dẫn nguồn mô hình ({manifest_model['source']}) "
        f"không khớp ({model_rec['source']})"
    )
    assert list(manifest_model["muscle_names"]) == list(model_rec["muscle_names"]), (
        f"Danh sách tên cơ ({manifest_model['muscle_names']}) "
        f"không khớp ({model_rec['muscle_names']})"
    )


def test_resources_fields_null_explicit(manifest_smoke_run: dict[str, Any]) -> None:
    """FR-012, NFR-RES-001, SC-003, AC-3: Tài nguyên đủ 100% trường; không có GPU thì ghi null."""
    manifest: dict[str, Any] = manifest_smoke_run["manifest"]
    resources = manifest.get("resources", {})

    expected_resource_keys = {
        "cpu_model",
        "cpu_logical_cores",
        "cpu_utilization_pct",
        "ram_peak_mb",
        "gpu_name",
        "gpu_utilization_pct",
        "vram_peak_mb",
    }
    actual_resource_keys = set(resources.keys())
    assert expected_resource_keys == actual_resource_keys, (
        f"Các trường tài nguyên không khớp danh mục bắt buộc 100%: "
        f"thiếu {expected_resource_keys - actual_resource_keys}, "
        f"thừa {actual_resource_keys - expected_resource_keys}"
    )

    assert resources["cpu_logical_cores"] >= 1, "Số nhân CPU logic phải >= 1"

    # Kiểm tra quy tắc tường minh khi không có GPU (hoặc trên thiết bị tính toán CPU)
    device_kind = manifest["device"]["kind"]
    if device_kind == "cpu" or resources["gpu_name"] is None:
        assert resources["gpu_name"] is None, "Khi không có GPU, gpu_name phải là null tường minh"
        assert resources["gpu_utilization_pct"] is None, (
            "Khi không có GPU, gpu_utilization_pct phải là null tường minh"
        )
        assert resources["vram_peak_mb"] is None, (
            "Khi không có GPU, vram_peak_mb phải là null tường minh"
        )
    else:
        assert isinstance(resources["gpu_name"], str), "gpu_name phải là chuỗi khi có GPU"
        assert resources["vram_peak_mb"] is None or resources["vram_peak_mb"] >= 0, (
            "vram_peak_mb phải >= 0 nếu có giá trị"
        )


def test_running_status_during_run(tmp_path: Path) -> None:
    """FR-011, INV-001, AC-3: Trạng thái 'running' lúc đang chạy, thay nguyên tử khi xong."""
    pytest.importorskip("torch", reason="Cần extra rl (torch) để thực thi huấn luyện PPO")
    pytest.importorskip("tensorboard", reason="Cần tensorboard để kiểm tra nhật ký chỉ số")

    status_snapshot_file = tmp_path / "observed_status.json"
    config_file = smoke_config(
        tmp_path,
        total_timesteps=2048,
        n_steps=2048,
        every_updates=1,
    )
    runs_dir = tmp_path / "runs"

    escaped_config = str(config_file)
    escaped_status = str(status_snapshot_file)
    escaped_runs_dir = str(runs_dir)

    # Kịch bản chạy huấn luyện có cài hook quan sát manifest lúc đang thu mẫu
    hook_script = (
        "import sys\n"
        "import json\n"
        "from pathlib import Path\n"
        "import mma_ai.environment.single_agent as sa\n"
        "import mma_ai.learning.cli as cli_mod\n"
        f"runs_dir = Path({escaped_runs_dir!r})\n"
        f"status_path = Path({escaped_status!r})\n"
        "observed = {}\n"
        "orig_step = sa.ElbowReachEnv.step\n"
        "step_counter = [0]\n"
        "def hooked_step(self, action):\n"
        "    step_counter[0] += 1\n"
        "    if step_counter[0] >= 10 and not observed:\n"
        "        if runs_dir.is_dir():\n"
        "            runs = sorted(p for p in runs_dir.iterdir() if p.is_dir())\n"
        "            if runs:\n"
        "                manifest_file = runs[-1] / 'manifest.json'\n"
        "                if manifest_file.is_file():\n"
        "                    try:\n"
        "                        m = json.loads(manifest_file.read_text(encoding='utf-8'))\n"
        "                        observed['status'] = m.get('status')\n"
        "                        observed['finished_utc'] = m.get('finished_utc')\n"
        "                        status_path.write_text(json.dumps(observed), encoding='utf-8')\n"
        "                    except Exception:\n"
        "                        pass\n"
        "    return orig_step(self, action)\n"
        "sa.ElbowReachEnv.step = hooked_step\n"
        "clean_args = ['--stage', 'elbow', '--seed', '42', '--config', "
        f"{escaped_config!r}]\n"
        "sys.exit(cli_mod.main(clean_args))\n"
    )

    clean_env = os.environ.copy()
    clean_env.pop("DISPLAY", None)
    clean_env.pop("WAYLAND_DISPLAY", None)

    proc = subprocess.run(
        [sys.executable, "-c", hook_script],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=120.0,
        cwd=str(Path.cwd()),
        check=False,
    )
    assert proc.returncode == 0, (
        f"Kịch bản kiểm tra trạng thái đang chạy thất bại với mã {proc.returncode}.\n"
        f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    )

    # 1. Khẳng định trạng thái quan sát được trong lúc đang chạy là 'running'
    assert status_snapshot_file.is_file(), (
        f"Hook không ghi nhận được trạng thái trong lúc chạy: {proc.stderr}"
    )
    observed_data = json.loads(status_snapshot_file.read_text(encoding="utf-8"))
    assert observed_data.get("status") == "running", (
        f"Kỳ vọng status là 'running', nhận: {observed_data.get('status')}"
    )
    assert observed_data.get("finished_utc") is None, (
        f"finished_utc phải là null lúc đang chạy, nhận: {observed_data.get('finished_utc')}"
    )

    # 2. Khẳng định trạng thái sau khi kết thúc là 'done' và thay thế nguyên tử
    created_runs = list_runs(runs_dir)
    assert len(created_runs) == 1, "Thư mục lượt chạy không tồn tại sau khi kết thúc"
    final_run_dir = created_runs[0]

    final_manifest = load_manifest(final_run_dir)
    assert final_manifest["status"] == "done", (
        f"Trạng thái cuối cùng phải là 'done', nhưng nhận: {final_manifest['status']}"
    )
    assert final_manifest["finished_utc"] is not None, (
        "Thời điểm kết thúc finished_utc phải được ghi nhận sau khi hoàn thành"
    )

    # Không còn tệp tạm thời manifest.json.tmp
    tmp_manifest_file = final_run_dir / "manifest.json.tmp"
    assert not tmp_manifest_file.exists(), (
        f"Tệp tạm thời chưa được dọn dẹp sau thay thế nguyên tử: {tmp_manifest_file}"
    )
