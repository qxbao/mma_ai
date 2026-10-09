"""Kiểm thử tích hợp tính tái lập qua giao diện dòng lệnh huấn luyện (T330).

Hiện thực và xác minh:
- FR-001, US4, AC-4: Huấn luyện PPO qua giao diện dòng lệnh (CLI) với cùng seed và cấu hình
  cho kết quả tái lập được.
- FR-014, AC-4, NFR-REPRO-001, SC-004: So sánh tính tái lập (reproducibility) của hai lượt chạy
  dựa trên hồ sơ thí nghiệm (run manifest); kiểm tra K điểm đầu của đường hàm phần thưởng
  (head_mean_return) theo dung sai tương đối (relative tolerance) <= 1e-6; hai lượt chạy khác
  seed cho đường phần thưởng khác nhau (chứng minh seed thực sự chi phối kết quả).
- Hồ sơ thí nghiệm ghi nhận rõ dung sai tái lập đã áp dụng và loại thiết bị tính toán (device kind).
- CMD-TRN-0003: Giao diện dòng lệnh so sánh compare_cli
  (python -m mma_ai.learning.compare_cli RUN_A RUN_B) thoát mã 0 khi trong dung sai và mã 1
  khi ngoài dung sai hoặc không thể so sánh.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from train_fixtures import list_runs, load_manifest, run_train_cli, smoke_config

from mma_ai.learning.compare_cli import main as compare_cli_main
from mma_ai.learning.manifest import build_manifest, write_manifest
from mma_ai.learning.repro import compare_manifests, compare_runs
from mma_ai.learning.train_config import TrainConfig


def test_determinism_contract_independent_assertion(tmp_path: Path) -> None:
    """FR-001, FR-014, NFR-REPRO-001, SC-004, AC-4, US4: Khẳng định độc lập trên base.

    Đảm bảo kiểm thử tích hợp (integration test) không bị bỏ qua toàn bộ khi thiếu phụ thuộc
    tuỳ chọn (optional dependency) PyTorch. Xác minh cấu hình mặc định, logic so sánh tái lập thuần
    (pure reproducibility comparison logic) và hành vi mã thoát của CLI compare_cli.
    """
    # 1. Xác minh cấu hình mặc định đáp ứng đầy đủ các tham số tái lập theo hợp đồng train-config
    cfg = TrainConfig.load()
    assert cfg.reproducibility.rel_tolerance == 1e-6, (
        f"Dung sai tương đối mặc định phải là 1e-6 nhưng nhận {cfg.reproducibility.rel_tolerance}"
    )
    assert cfg.reproducibility.head_updates == 10, (
        f"Số lượt cập nhật đầu kỳ mặc định phải là 10 nhưng nhận {cfg.reproducibility.head_updates}"
    )
    assert cfg.reproducibility.torch_threads == 1, (
        f"Số luồng Torch mặc định phải là 1 nhưng nhận {cfg.reproducibility.torch_threads}"
    )
    assert cfg.reproducibility.deterministic_algorithms is True, (
        "Thuật toán tất định (deterministic_algorithms) phải được bật mặc định"
    )

    # 2. Xác minh logic so sánh tái lập thuần (compare_manifests) trên các hồ sơ mẫu
    dummy_model = {
        "sha256": "384dcb555561287fe39d960aba6496db8b825bebd21df3873bb07920a886066f",
        "source": "myo_sim/models/legacy/elbow/myoelbow_1dof6muscles.xml",
        "muscle_names": ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"],
    }
    dummy_device_cpu = {"kind": "cpu", "name": "CPU Test", "cuda_available": False}
    dummy_device_cuda = {"kind": "cuda", "name": "GPU Test", "cuda_available": True}

    def _make_dummy_manifest(
        run_name: str,
        returns: list[float],
        device: dict[str, Any],
        tolerance: float = 1e-6,
    ) -> dict[str, Any]:
        manifest = build_manifest(
            run_id=f"20261010T080000Z_elbow_s42_{run_name}",
            config=cfg.to_dict(),
            seed=42,
            model=dummy_model,
            device=device,
            library_versions={"torch": "2.14.0"},
        )
        manifest["reward_metrics"]["head_mean_return"] = returns
        manifest["reproducibility"]["rel_tolerance"] = tolerance
        manifest["reproducibility"]["device_kind"] = device["kind"]
        manifest["reproducibility"]["torch_threads"] = 1
        return manifest

    manifest_a = _make_dummy_manifest("run_a", [-4.197435, -6.235825], dummy_device_cpu, 1e-6)
    manifest_b = _make_dummy_manifest("run_b", [-4.197435, -6.235825001], dummy_device_cpu, 1e-6)
    manifest_outside = _make_dummy_manifest("run_c", [-4.197435, -7.0], dummy_device_cpu, 1e-6)
    manifest_cuda = _make_dummy_manifest("run_d", [-4.197435, -6.235825], dummy_device_cuda, 1e-6)

    # Khẳng định hai lượt chạy trong dung sai tương đối
    report_within = compare_manifests(manifest_a, manifest_b)
    assert report_within.comparable is True
    assert report_within.matches is True

    # Khẳng định hai lượt chạy ngoài dung sai tương đối
    report_outside = compare_manifests(manifest_a, manifest_outside)
    assert report_outside.comparable is True
    assert report_outside.matches is False

    # Khẳng định không thể so sánh giữa hai thiết bị khác loại
    report_incomparable = compare_manifests(manifest_a, manifest_cuda)
    assert report_incomparable.comparable is False

    # 3. Xác minh giao diện dòng lệnh compare_cli với các thư mục lượt chạy giả lập
    dir_a = tmp_path / "mock_run_a"
    dir_b = tmp_path / "mock_run_b"
    dir_c = tmp_path / "mock_run_c"
    dir_a.mkdir(parents=True, exist_ok=True)
    dir_b.mkdir(parents=True, exist_ok=True)
    dir_c.mkdir(parents=True, exist_ok=True)

    write_manifest(dir_a, manifest_a)
    write_manifest(dir_b, manifest_b)
    write_manifest(dir_c, manifest_outside)

    exit_within = compare_cli_main([str(dir_a), str(dir_b)])
    assert exit_within == 0, f"Kỳ vọng mã thoát 0 cho cặp trong dung sai nhưng nhận {exit_within}"

    exit_outside = compare_cli_main([str(dir_a), str(dir_c)])
    assert exit_outside == 1, f"Kỳ vọng mã thoát 1 cho cặp ngoài dung sai nhưng nhận {exit_outside}"


@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def smoke_determinism_runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Khởi chạy ba lượt huấn luyện smoke để kiểm thử tính tái lập xác định qua CLI.

    Bao gồm:
    - run_1_s42: Seed 42, cấu hình smoke.
    - run_2_s42: Seed 42, cùng cấu hình smoke trên cùng môi trường tính toán.
    - run_3_s137: Seed 137, cùng cấu hình smoke để kiểm tra sự phân hoá khi khác seed.
    """
    pytest.importorskip("torch", reason="Cần extra rl (PyTorch) để thực thi huấn luyện PPO")

    base_dir = tmp_path_factory.mktemp("cli_determinism_integration")

    # Tạo các thư mục riêng biệt cho từng lượt chạy nhằm cô lập hoàn toàn môi trường ghi
    dir_1 = base_dir / "dir_run_1_s42"
    dir_2 = base_dir / "dir_run_2_s42"
    dir_3 = base_dir / "dir_run_3_s137"

    cfg_1 = smoke_config(dir_1, total_timesteps=4096, n_steps=2048, every_updates=1, mode="none")
    cfg_2 = smoke_config(dir_2, total_timesteps=4096, n_steps=2048, every_updates=1, mode="none")
    cfg_3 = smoke_config(dir_3, total_timesteps=4096, n_steps=2048, every_updates=1, mode="none")

    # Thực thi lượt chạy 1 với seed 42
    args_1 = ["--stage", "elbow", "--seed", "42", "--config", str(cfg_1)]
    proc_1 = run_train_cli(args_1, timeout=180.0)

    # Thực thi lượt chạy 2 với cùng seed 42
    args_2 = ["--stage", "elbow", "--seed", "42", "--config", str(cfg_2)]
    proc_2 = run_train_cli(args_2, timeout=180.0)

    # Thực thi lượt chạy 3 với seed khác biệt 137
    args_3 = ["--stage", "elbow", "--seed", "137", "--config", str(cfg_3)]
    proc_3 = run_train_cli(args_3, timeout=180.0)

    runs_1 = list_runs(dir_1 / "runs")
    runs_2 = list_runs(dir_2 / "runs")
    runs_3 = list_runs(dir_3 / "runs")

    assert len(runs_1) > 0, f"Lượt chạy 1 thất bại không tạo run dir. Stderr: {proc_1.stderr}"
    assert len(runs_2) > 0, f"Lượt chạy 2 thất bại không tạo run dir. Stderr: {proc_2.stderr}"
    assert len(runs_3) > 0, f"Lượt chạy 3 thất bại không tạo run dir. Stderr: {proc_3.stderr}"

    run_dir_1 = runs_1[0]
    run_dir_2 = runs_2[0]
    run_dir_3 = runs_3[0]

    return {
        "proc_1": proc_1,
        "proc_2": proc_2,
        "proc_3": proc_3,
        "run_dir_1": run_dir_1,
        "run_dir_2": run_dir_2,
        "run_dir_3": run_dir_3,
        "manifest_1": load_manifest(run_dir_1),
        "manifest_2": load_manifest(run_dir_2),
        "manifest_3": load_manifest(run_dir_3),
    }


def test_same_seed_head_curve_within_tolerance(smoke_determinism_runs: dict[str, Any]) -> None:
    """FR-001, FR-014, NFR-REPRO-001, SC-004, AC-4, US4: Hai run cùng seed lệch tương đối <= 1e-6.

    Xác minh hai lượt huấn luyện smoke độc lập với cùng seed (42), cấu hình và thiết bị tính toán
    cho ra đường hàm phần thưởng đầu kỳ (head_mean_return) với K = min(10, số lượt thực chạy)
    hoàn toàn nằm trong dung sai tương đối 1×10⁻⁶ tại mọi điểm đo.
    """
    proc_1 = smoke_determinism_runs["proc_1"]
    proc_2 = smoke_determinism_runs["proc_2"]
    assert proc_1.returncode == 0, f"Lượt chạy 1 thất bại: {proc_1.stderr}"
    assert proc_2.returncode == 0, f"Lượt chạy 2 thất bại: {proc_2.stderr}"

    manifest_1 = smoke_determinism_runs["manifest_1"]
    manifest_2 = smoke_determinism_runs["manifest_2"]

    returns_1 = manifest_1.get("reward_metrics", {}).get("head_mean_return")
    returns_2 = manifest_2.get("reward_metrics", {}).get("head_mean_return")

    assert isinstance(returns_1, list) and len(returns_1) > 0, (
        f"head_mean_return của run 1 không hợp lệ: {returns_1}"
    )
    assert isinstance(returns_2, list) and len(returns_2) > 0, (
        f"head_mean_return của run 2 không hợp lệ: {returns_2}"
    )
    assert len(returns_1) == len(returns_2), (
        f"Số lượng điểm phần thưởng đầu kỳ không khớp: {len(returns_1)} != {len(returns_2)}"
    )

    k_points = min(10, len(returns_1))
    tolerance = float(manifest_1.get("reproducibility", {}).get("rel_tolerance", 1e-6))

    for idx in range(k_points):
        val_1 = float(returns_1[idx])
        val_2 = float(returns_2[idx])
        assert math.isfinite(val_1), f"Điểm {idx} của run 1 không hữu hạn: {val_1}"
        assert math.isfinite(val_2), f"Điểm {idx} của run 2 không hữu hạn: {val_2}"

        diff = abs(val_2 - val_1)
        denom = max(abs(val_1), 1e-9)
        rel_diff = diff / denom

        assert rel_diff <= tolerance, (
            f"Điểm {idx} vượt dung sai tương đối {tolerance:g}: "
            f"run_1={val_1}, run_2={val_2}, độ lệch={rel_diff:g}"
        )

    # Đối chiếu qua tiện ích so sánh chuẩn compare_runs
    run_dir_1 = smoke_determinism_runs["run_dir_1"]
    run_dir_2 = smoke_determinism_runs["run_dir_2"]
    report = compare_runs(run_dir_1, run_dir_2)

    assert report.comparable is True, (
        f"Hai lượt chạy cùng thiết bị phải so sánh được: {report.reason}"
    )
    assert report.matches is True, (
        f"Hai lượt chạy cùng seed phải khớp trong dung sai: {report.reason}"
    )


def test_diff_seed_differs(smoke_determinism_runs: dict[str, Any]) -> None:
    """FR-001, FR-014, SC-004, AC-4, US4: Hai run khác seed cho đường phần thưởng khác nhau.

    Chứng minh tính tất định không phải do môi trường cố định giá trị giả mạo (hardcoded)
    mà thực sự do seed ngẫu nhiên chi phối hành vi khởi tạo và quá trình lấy mẫu.
    """
    proc_3 = smoke_determinism_runs["proc_3"]
    assert proc_3.returncode == 0, f"Lượt chạy 3 (seed 137) thất bại: {proc_3.stderr}"

    manifest_1 = smoke_determinism_runs["manifest_1"]
    manifest_3 = smoke_determinism_runs["manifest_3"]

    returns_1 = manifest_1.get("reward_metrics", {}).get("head_mean_return")
    returns_3 = manifest_3.get("reward_metrics", {}).get("head_mean_return")

    assert isinstance(returns_1, list) and isinstance(returns_3, list)
    assert returns_1 != returns_3, (
        "Hai lượt chạy với seed khác nhau (42 và 137) không được trùng khớp hoàn toàn"
    )

    run_dir_1 = smoke_determinism_runs["run_dir_1"]
    run_dir_3 = smoke_determinism_runs["run_dir_3"]
    report = compare_runs(run_dir_1, run_dir_3)

    assert report.comparable is True, (
        f"Hai lượt chạy cùng thiết bị phải so sánh được: {report.reason}"
    )
    assert report.matches is False, (
        "Hai lượt chạy khác seed phải được đánh giá là không khớp trong dung sai tái lập"
    )


def test_manifest_records_tolerance_and_device(smoke_determinism_runs: dict[str, Any]) -> None:
    """FR-014, AC-4, NFR-REPRO-001, SC-004: Hồ sơ thí nghiệm ghi nhận đầy đủ dung sai và thiết bị.

    Xác minh các trường bắt buộc của hợp đồng tái lập được lưu nguyên văn trong manifest.json.
    """
    manifest = smoke_determinism_runs["manifest_1"]
    repro = manifest.get("reproducibility")
    assert isinstance(repro, dict), "Hồ sơ manifest phải có mục 'reproducibility'"

    assert repro.get("rel_tolerance") == 1e-6, (
        f"Dung sai tái lập trong hồ sơ kỳ vọng 1e-6 nhưng nhận {repro.get('rel_tolerance')}"
    )
    assert repro.get("head_updates") == 10, (
        f"head_updates trong hồ sơ kỳ vọng 10 nhưng nhận {repro.get('head_updates')}"
    )
    assert repro.get("device_kind") in ("cpu", "cuda"), (
        f"Loại thiết bị trong reproducibility không hợp lệ: {repro.get('device_kind')}"
    )
    assert repro.get("torch_threads") == 1, (
        f"torch_threads trong hồ sơ kỳ vọng 1 nhưng nhận {repro.get('torch_threads')}"
    )
    assert repro.get("deterministic_algorithms") is True, (
        "deterministic_algorithms trong hồ sơ phải là True"
    )

    device = manifest.get("device")
    assert isinstance(device, dict), "Hồ sơ manifest phải có mục 'device'"
    assert device.get("kind") in ("cpu", "cuda"), f"device.kind không hợp lệ: {device.get('kind')}"


def test_compare_cli_exit0_within_tolerance(smoke_determinism_runs: dict[str, Any]) -> None:
    """FR-014, CMD-TRN-0003, AC-4: CLI compare_cli thoát 0 trong dung sai và 1 ngoài dung sai.

    Kiểm tra cả việc gọi trực tiếp hàm main của CLI và chạy thông qua tiến trình con thực tế.
    """
    run_dir_1 = str(smoke_determinism_runs["run_dir_1"])
    run_dir_2 = str(smoke_determinism_runs["run_dir_2"])
    run_dir_3 = str(smoke_determinism_runs["run_dir_3"])

    # 1. Gọi trực tiếp hàm main của compare_cli
    exit_code_within = compare_cli_main([run_dir_1, run_dir_2])
    assert exit_code_within == 0, (
        f"compare_cli kỳ vọng mã thoát 0 cho cặp cùng seed nhưng nhận {exit_code_within}"
    )

    exit_code_outside = compare_cli_main([run_dir_1, run_dir_3])
    assert exit_code_outside == 1, (
        f"compare_cli kỳ vọng mã thoát 1 cho cặp khác seed nhưng nhận {exit_code_outside}"
    )

    # 2. Gọi thông qua tiến trình con độc lập bằng sys.executable
    cmd_within = [sys.executable, "-m", "mma_ai.learning.compare_cli", run_dir_1, run_dir_2]
    proc_within = subprocess.run(
        cmd_within,
        capture_output=True,
        text=True,
        cwd=str(Path.cwd()),
        check=False,
    )
    assert proc_within.returncode == 0, (
        f"Tiến trình con compare_cli kỳ vọng mã 0 nhưng nhận {proc_within.returncode}. "
        f"Stderr: {proc_within.stderr}"
    )
    assert "Trong dung sai tái lập" in proc_within.stdout, (
        f"Thông báo tiến trình con không chứa kết quả tiếng Việt: {proc_within.stdout}"
    )

    cmd_outside = [sys.executable, "-m", "mma_ai.learning.compare_cli", run_dir_1, run_dir_3]
    proc_outside = subprocess.run(
        cmd_outside,
        capture_output=True,
        text=True,
        cwd=str(Path.cwd()),
        check=False,
    )
    assert proc_outside.returncode == 1, (
        f"Tiến trình con compare_cli kỳ vọng mã 1 nhưng nhận {proc_outside.returncode}. "
        f"Stderr: {proc_outside.stderr}"
    )
    assert "Ngoài dung sai tái lập" in proc_outside.stdout, (
        f"Thông báo tiến trình con không chứa kết quả tiếng Việt: {proc_outside.stdout}"
    )
