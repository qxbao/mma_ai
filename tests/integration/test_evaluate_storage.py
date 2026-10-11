"""Kiểm thử tích hợp lưu trữ và tính chỉ-đọc qua CLI đánh giá (T420).

Hiện thực các kịch bản kiểm thử tích hợp (integration test) và chấp nhận (acceptance test)
cho cơ chế lưu trữ kết quả và bảo đảm tính bất biến (immutability) chỉ-đọc đối với dữ liệu
huấn luyện:
- 004 US5, 004 AC-1, FR-013, SC-006: Bản ghi kết quả đánh giá (report.json) nêu đầy đủ hạt giống
  huấn luyện của run (run.seed), định danh và mã băm SHA-256 của checkpoint được dùng, hạt giống
  đánh giá (eval_seed_range), cấu hình đánh giá đầy đủ (config) và phiên bản thư viện
  (library_versions).
- 004 US5, 004 AC-1, FR-013, INV-005: Hai lượt đánh giá liên tiếp trên cùng checkpoint tạo ra hai
  thư mục đánh giá riêng biệt trong eval/, nội dung và mã băm toàn cây (hash_tree) của thư mục
  lượt trước hoàn toàn giữ nguyên, không bị thay đổi.
- 004 US5, 004 AC-1, FR-014, INV-005, SC-006: Phiên đánh giá hoàn toàn chỉ-đọc đối với các tệp do
  phân hệ huấn luyện 003 ghi; mã băm của manifest.json, thư mục checkpoints/ và nhật ký
  metrics.jsonl trước và sau đánh giá hoàn toàn trùng khớp.
- 004 US5, 004 AC-1, FR-013, INV-004, AC-5: Checkpoint nằm ngoài thư mục run bắt buộc phải có
  tham số --out (out_dir); thiếu --out thoát với mã 2 (EvalConfigError). Khi có --out nhưng không
  thể thiết lập tập huấn luyện của run thì thoát với mã 5 (TrainSetUnknown).
- 004 US5, 004 AC-1, INV-004, AC-5: Khi bị ngắt giữa chừng (KeyboardInterrupt / Ctrl-C), tiến trình
  dọn dẹp sạch sẽ thư mục tạm .tmp-*, thoát mã 130 và tuyệt đối không để lại bản ghi dở dang nào.
- 004 US5, 004 AC-1, FR-013, INV-004, SC-006: Thư mục eval/ hoặc thư mục --out không ghi được
  (thiếu quyền hạn / unwritable) thì lệnh báo lỗi EvalWriteError, thoát mã 7 và tuyệt đối không in
  tóm tắt kết quả ra stdout như thể đã lưu thành công.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from eval_fixtures import hash_tree, make_run_dir, run_cli

from mma_ai.evaluation import runner
from mma_ai.evaluation.cli import main
from mma_ai.evaluation.errors import EvalWriteError
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.runner import evaluate_checkpoint


def _eval_deps() -> tuple[Any, Any, Any]:
    """Kiểm tra và nạp các thư viện phụ thuộc tùy chọn (optional dependencies) eval và rl."""
    pd = pytest.importorskip("pandas", reason="Cần extra eval (pandas) để chạy đánh giá")
    mpl = pytest.importorskip("matplotlib", reason="Cần extra eval (matplotlib) vẽ biểu đồ")
    torch = pytest.importorskip("torch", reason="Cần extra rl (torch) để chạy CLI")
    return pd, mpl, torch


def test_regress_tdd_red_unwritable_eval_dir_maps_to_exit7(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-004: lỗi tạo eval/ phải thành EvalWriteError và mã thoát 7, không cần extra tùy chọn."""
    checkpoint_path = tmp_path / "checkpoint.pt"
    checkpoint_path.write_bytes(b"checkpoint")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    env_config = run_dir / "env.yaml"
    env_config.write_text("targets: {}\n", encoding="utf-8")
    manifest_file = run_dir / "manifest.json"
    manifest_file.write_text(
        json.dumps({"config": {"env_config": str(env_config)}, "model": {"sha256": "model-sha"}}),
        encoding="utf-8",
    )

    fake_checkpoint = SimpleNamespace(
        model_sha256="model-sha",
        update_idx=0,
        env_steps=0,
        library_versions={},
    )
    checkpoint_module = ModuleType("mma_ai.learning.checkpoint")

    def _load_checkpoint(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return fake_checkpoint

    setattr(checkpoint_module, "load_checkpoint", _load_checkpoint)
    monkeypatch.setitem(sys.modules, "mma_ai.learning.checkpoint", checkpoint_module)
    monkeypatch.setattr(runner, "_resolve_checkpoint_file", lambda _checkpoint: checkpoint_path)
    monkeypatch.setattr(
        runner,
        "_find_run_directory_and_manifest",
        lambda *_args: (run_dir, manifest_file),
    )
    monkeypatch.setattr(
        runner,
        "load_muscle_model",
        lambda _name: SimpleNamespace(
            model=object(),
            info=SimpleNamespace(
                sha256="model-sha",
                muscle_names=("m1", "m2", "m3", "m4", "m5", "m6"),
            ),
        ),
    )
    monkeypatch.setattr(runner, "LearnedPolicy", lambda _checkpoint: object())
    monkeypatch.setattr(
        runner,
        "check_disjoint",
        lambda **_kwargs: SimpleNamespace(n_eval_targets=2),
    )
    monkeypatch.setattr(
        runner,
        "ElbowEnvConfig",
        SimpleNamespace(
            load=lambda _path: SimpleNamespace(targets=SimpleNamespace(default_seed=1))
        ),
    )
    monkeypatch.setattr(
        runner,
        "TargetGenerator",
        lambda **_kwargs: SimpleNamespace(generate=lambda *, seed: object()),
    )
    monkeypatch.setattr(runner, "ElbowReachEnv", lambda **_kwargs: object())
    monkeypatch.setattr(runner, "RandomPolicy", lambda **_kwargs: object())

    eval_root = run_dir / "eval"
    original_mkdir = Path.mkdir

    def _deny_eval_root(
        path: Path,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        if path == eval_root:
            raise OSError(30, "Read-only file system", str(path))
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    monkeypatch.setattr(Path, "mkdir", _deny_eval_root)

    with pytest.raises(EvalWriteError) as caught:
        evaluate_checkpoint(checkpoint_path, cfg=EvalConfig.load())

    assert runner.get_exit_code(caught.value) == 7


def test_report_names_seed_and_checkpoint_hash(tmp_path: Path) -> None:
    """004 US5, 004 AC-1, FR-013, SC-006:
    Bản ghi report.json nêu đúng run.seed, checkpoint (định danh + SHA-256), seed đánh giá,
    cấu hình đầy đủ và phiên bản thư viện.
    """
    _eval_deps()

    train_seed = 42
    eval_seed = 100
    run_dir = make_run_dir(tmp_path / "run_storage_01", seed=train_seed, with_log=True)
    checkpoint_target = run_dir / "checkpoints" / "latest.json"

    res = run_cli([
        "--checkpoint",
        str(checkpoint_target),
        "--eval-seed",
        str(eval_seed),
        "--repeats",
        "1",
    ])

    assert res.exit_code == 0, (
        f"Kỳ vọng mã thoát 0 nhưng nhận {res.exit_code}.\n"
        f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    )

    eval_root = run_dir / "eval"
    assert eval_root.is_dir(), f"Thư mục eval/ phải được tạo: {eval_root}"

    eval_dirs = [p for p in eval_root.iterdir() if p.is_dir() and not p.name.startswith(".tmp-")]
    assert len(eval_dirs) == 1, f"Kỳ vọng đúng 1 thư mục đánh giá nhưng thấy: {eval_dirs}"

    eval_dir = eval_dirs[0]
    report_file = eval_dir / "report.json"
    assert report_file.is_file(), f"Tệp report.json phải tồn tại tại {report_file}"

    report = json.loads(report_file.read_text(encoding="utf-8"))

    # 1. Kiểm tra hạt giống của run huấn luyện
    assert "run" in report, "Báo cáo phải chứa khối 'run'"
    assert report["run"]["seed"] == train_seed, (
        f"Hạt giống run phải là {train_seed}, nhận {report['run']['seed']}"
    )

    # 2. Kiểm tra định danh và mã băm SHA-256 của checkpoint
    assert "checkpoint" in report, "Báo cáo phải chứa khối 'checkpoint'"
    ckpt_info = report["checkpoint"]
    assert "path" in ckpt_info and len(ckpt_info["path"]) > 0, "Khối checkpoint phải có path"
    assert "sha256" in ckpt_info and len(ckpt_info["sha256"]) == 64, (
        "Khối checkpoint phải có mã băm SHA-256 64 ký tự"
    )

    # Đối chiếu mã băm với tệp checkpoint thực tế trên đĩa
    actual_ckpt_file = run_dir / ckpt_info["path"]
    assert actual_ckpt_file.is_file(), f"Tệp checkpoint thực tế phải tồn tại: {actual_ckpt_file}"
    actual_ckpt_sha = hash_tree(actual_ckpt_file)
    assert ckpt_info["sha256"] == actual_ckpt_sha, (
        f"Mã băm trong báo cáo ({ckpt_info['sha256']}) không khớp "
        f"mã băm thực tế ({actual_ckpt_sha})"
    )

    # 3. Kiểm tra hạt giống đánh giá trong disjointness
    assert "disjointness" in report, "Báo cáo phải chứa khối 'disjointness'"
    eval_seeds = report["disjointness"].get("eval_seed_range", [])
    assert len(eval_seeds) == 2, "eval_seed_range phải là khoảng [bắt đầu, kết thúc)"
    assert eval_seeds[0] == eval_seed, f"Hạt giống bắt đầu phải là {eval_seed}"

    # 4. Kiểm tra cấu hình đánh giá đầy đủ (config)
    assert "config" in report, "Báo cáo phải chứa khối 'config'"
    config_dict = report["config"]
    assert "seeds" in config_dict, "Cấu hình phải có nhóm 'seeds'"
    assert "episodes" in config_dict, "Cấu hình phải có nhóm 'episodes'"
    assert "criterion" in config_dict, "Cấu hình phải có nhóm 'criterion'"
    assert "stats" in config_dict, "Cấu hình phải có nhóm 'stats'"
    assert "charts" in config_dict, "Cấu hình phải có nhóm 'charts'"
    assert "paths" in config_dict, "Cấu hình phải có nhóm 'paths'"

    # 5. Kiểm tra phiên bản thư viện (library_versions)
    assert "library_versions" in report, "Báo cáo phải chứa khối 'library_versions'"
    lib_vers = report["library_versions"]
    for required_lib in ("python", "numpy", "pandas", "matplotlib", "torch", "gymnasium", "mujoco"):
        assert required_lib in lib_vers, f"library_versions phải ghi nhận thư viện '{required_lib}'"


def test_two_evals_two_dirs_first_unchanged(tmp_path: Path) -> None:
    """004 US5, 004 AC-1, FR-013, INV-005:
    Hai lượt đánh giá liên tiếp trên cùng checkpoint tạo hai mục riêng trong eval/,
    mục lượt trước giữ nguyên tuyệt đối mã băm.
    """
    _eval_deps()

    run_dir = make_run_dir(tmp_path / "run_storage_02", seed=42, with_log=True)
    checkpoint_target = run_dir / "checkpoints" / "latest.json"

    # Lượt đánh giá thứ nhất với seed 100
    res1 = run_cli([
        "--checkpoint",
        str(checkpoint_target),
        "--eval-seed",
        "100",
        "--repeats",
        "1",
    ])
    assert res1.exit_code == 0, f"Lượt 1 thất bại: {res1.stderr}"

    eval_root = run_dir / "eval"
    eval_dirs_after_first = sorted([
        p for p in eval_root.iterdir() if p.is_dir() and not p.name.startswith(".tmp-")
    ])
    assert len(eval_dirs_after_first) == 1, (
        f"Kỳ vọng 1 thư mục sau lượt 1, nhưng thấy: {eval_dirs_after_first}"
    )

    first_eval_dir = eval_dirs_after_first[0]
    hash_first_before = hash_tree(first_eval_dir)

    # Lượt đánh giá thứ hai với seed 200
    res2 = run_cli([
        "--checkpoint",
        str(checkpoint_target),
        "--eval-seed",
        "200",
        "--repeats",
        "1",
    ])
    assert res2.exit_code == 0, f"Lượt 2 thất bại: {res2.stderr}"

    eval_dirs_after_second = sorted([
        p for p in eval_root.iterdir() if p.is_dir() and not p.name.startswith(".tmp-")
    ])
    assert len(eval_dirs_after_second) == 2, (
        f"Kỳ vọng 2 thư mục đánh giá sau lượt 2, nhưng thấy: {eval_dirs_after_second}"
    )
    assert first_eval_dir in eval_dirs_after_second, (
        "Thư mục của lượt 1 phải vẫn còn tồn tại sau lượt 2"
    )

    # Bất biến INV-005: Thư mục lượt 1 hoàn toàn không đổi nội dung
    hash_first_after = hash_tree(first_eval_dir)
    assert hash_first_before == hash_first_after, (
        "Mã băm toàn cây của thư mục đánh giá lượt 1 bị thay đổi sau lượt đánh giá thứ hai!"
    )


def test_run_files_unchanged_by_evaluation(tmp_path: Path) -> None:
    """004 US5, 004 AC-1, FR-014, INV-005, SC-006:
    Đánh giá hoàn toàn chỉ-đọc với tệp của run; manifest.json, checkpoints/, metrics.jsonl
    giữ nguyên mã băm trước và sau khi đánh giá.
    """
    _eval_deps()

    run_dir = make_run_dir(tmp_path / "run_storage_03", seed=42, with_log=True)
    checkpoint_target = run_dir / "checkpoints" / "latest.json"

    manifest_file = run_dir / "manifest.json"
    checkpoints_dir = run_dir / "checkpoints"
    metrics_file = run_dir / "metrics.jsonl"

    # Tính mã băm trước khi chạy đánh giá
    manifest_hash_before = hash_tree(manifest_file)
    checkpoints_hash_before = hash_tree(checkpoints_dir)
    metrics_hash_before = hash_tree(metrics_file)

    res = run_cli([
        "--checkpoint",
        str(checkpoint_target),
        "--eval-seed",
        "100",
        "--repeats",
        "1",
    ])
    assert res.exit_code == 0, f"Lượt đánh giá thất bại: {res.stderr}"

    # Tính mã băm sau khi chạy đánh giá
    manifest_hash_after = hash_tree(manifest_file)
    checkpoints_hash_after = hash_tree(checkpoints_dir)
    metrics_hash_after = hash_tree(metrics_file)

    # Bất biến INV-005: Toàn bộ tệp của run huấn luyện phải giữ nguyên vẹn
    assert manifest_hash_before == manifest_hash_after, (
        "manifest.json bị sửa đổi bởi quy trình đánh giá!"
    )
    assert checkpoints_hash_before == checkpoints_hash_after, (
        "Thư mục checkpoints/ bị sửa đổi bởi quy trình đánh giá!"
    )
    assert metrics_hash_before == metrics_hash_after, (
        "Nhật ký metrics.jsonl bị sửa đổi bởi quy trình đánh giá!"
    )


def test_checkpoint_outside_run_requires_out(tmp_path: Path) -> None:
    """004 US5, 004 AC-1, FR-013, INV-004, AC-5:
    Checkpoint nằm ngoài thư mục run bắt buộc phải có cờ --out; thiếu --out thoát mã 2.
    Có --out nhưng không thiết lập được tập huấn luyện thoát mã 5.
    """
    _eval_deps()

    # Tạo một checkpoint hợp lệ trong run mẫu, rồi sao chép ra thư mục cô lập
    src_run = make_run_dir(tmp_path / "src_run", seed=42)
    src_pt = src_run / "checkpoints" / "ckpt_u000001.pt"

    isolated_dir = tmp_path / "isolated_checkpoints"
    isolated_dir.mkdir(parents=True, exist_ok=True)
    isolated_pt = isolated_dir / "external_model.pt"
    shutil.copy2(src_pt, isolated_pt)

    # Nhánh 1: Chạy đánh giá checkpoint cô lập mà KHÔNG truyền --out -> thoát mã 2 (EvalConfigError)
    res_no_out = run_cli([
        "--checkpoint",
        str(isolated_pt),
        "--eval-seed",
        "100",
    ])

    assert res_no_out.exit_code == 2, (
        "Kỳ vọng mã thoát 2 khi thiếu --out cho checkpoint ngoài run, "
        f"nhận {res_no_out.exit_code}.\nstderr:\n{res_no_out.stderr}"
    )
    assert "EvalConfigError" in res_no_out.stderr
    assert "out_dir" in res_no_out.stderr or "--out" in res_no_out.stderr

    # Nhánh 2: Có truyền cờ --out nhưng không thiết lập được tập train
    # -> thoát mã 5 (TrainSetUnknown)
    custom_out = tmp_path / "custom_eval_out"
    res_with_out = run_cli([
        "--checkpoint",
        str(isolated_pt),
        "--out",
        str(custom_out),
        "--eval-seed",
        "100",
    ])

    assert res_with_out.exit_code == 5, (
        f"Kỳ vọng mã thoát 5 khi không thiết lập được tập train, nhận {res_with_out.exit_code}.\n"
        f"stderr:\n{res_with_out.stderr}"
    )
    assert "TrainSetUnknown" in res_with_out.stderr


def test_no_partial_dir_on_interrupt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """004 US5, 004 AC-1, INV-004, AC-5:
    Khi bị ngắt bởi KeyboardInterrupt (Ctrl-C), thư mục tạm .tmp-* bị dọn sạch, thoát mã 130
    và không để lại bất kỳ bản ghi hay thư mục kết quả dở dang nào.
    """
    _eval_deps()

    run_dir = make_run_dir(tmp_path / "run_interrupt", seed=42, with_log=True)
    checkpoint_target = run_dir / "checkpoints" / "latest.json"

    # Giả lập KeyboardInterrupt phát sinh trong bước chạy rollout
    def _mock_interrupt(*args: Any, **kwargs: Any) -> Any:
        raise KeyboardInterrupt("Giả lập người dùng bấm Ctrl-C trong khi đánh giá")

    monkeypatch.setattr("mma_ai.evaluation.runner.run_policy_on_targets", _mock_interrupt)

    # Kiểm tra điểm vào CLI main trả về mã 130 khi bị ngắt
    exit_code = main([
        "--checkpoint",
        str(checkpoint_target),
        "--eval-seed",
        "100",
        "--repeats",
        "1",
    ])

    assert exit_code == 130, f"Kỳ vọng mã thoát 130 khi bị ngắt bởi Ctrl-C, nhận {exit_code}"

    # Kiểm tra không tồn tại bất kỳ thư mục tạm .tmp-* nào còn sót lại trong eval/
    eval_root = run_dir / "eval"
    if eval_root.exists():
        tmp_dirs = [p for p in eval_root.iterdir() if p.name.startswith(".tmp-")]
        assert len(tmp_dirs) == 0, f"Thư mục tạm chưa được dọn dẹp sau khi ngắt: {tmp_dirs}"
        published_dirs = [
            p for p in eval_root.iterdir() if p.is_dir() and not p.name.startswith(".tmp-")
        ]
        assert len(published_dirs) == 0, (
            f"Không được để lại bản ghi hoàn chỉnh dở dang: {published_dirs}"
        )


def test_unwritable_eval_dir_exit7(tmp_path: Path) -> None:
    """004 US5, 004 AC-1, FR-013, INV-004, SC-006:
    Thư mục eval/ hoặc --out không ghi được (unwritable) thì thoát mã 7 (EvalWriteError),
    thông báo lỗi nêu rõ nguyên nhân và tuyệt đối không in tóm tắt kết quả ra stdout.
    """
    _eval_deps()

    run_dir = make_run_dir(tmp_path / "run_unwritable", seed=42, with_log=True)
    checkpoint_target = run_dir / "checkpoints" / "latest.json"

    # Tạo trước thư mục eval/ và phân quyền chỉ đọc (read-only 0o555)
    eval_root = run_dir / "eval"
    eval_root.mkdir(parents=True, exist_ok=True)
    os.chmod(eval_root, 0o555)

    try:
        res = run_cli([
            "--checkpoint",
            str(checkpoint_target),
            "--eval-seed",
            "100",
            "--repeats",
            "1",
        ])

        assert res.exit_code == 7, (
            f"Kỳ vọng mã thoát 7 khi thư mục eval không ghi được, nhận {res.exit_code}.\n"
            f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
        )
        assert "EvalWriteError" in res.stderr
        # Tuyệt đối không in tiêu đề kết quả như thể đã thành công
        assert "KẾT QUẢ ĐÁNH GIÁ CHÍNH SÁCH" not in res.stdout
    finally:
        # Khôi phục quyền ghi để pytest có thể dọn dẹp tmp_path sạch sẽ
        os.chmod(eval_root, 0o755)
