"""Kiểm thử tích hợp phát hiện rò rỉ dữ liệu qua CLI đánh giá (T419).

Hiện thực các kịch bản kiểm thử tích hợp (integration test) và nghiệm thu (acceptance test)
cho cơ chế bảo vệ ranh giới phân tách dữ liệu huấn luyện và đánh giá (split guard):
- 004 US4, 004 AC-4, FR-008, INV-001, SC-004: Hạt giống đánh giá (evaluation seed) trùng với
  hạt giống huấn luyện (training seed) của phiên chạy bị từ chối với mã thoát 5, thông báo lỗi
  nêu rõ hạt giống trùng lặp, 0 tập phim (episode) được chạy (chứng minh bằng việc không tạo
  thư mục eval/ và không sinh tệp episodes.csv).
- 004 US4, 004 AC-4, FR-008, INV-001, SC-004: Tập đánh giá có mục tiêu nằm trong khoảng cách
  tối thiểu (minimum separation distance) của tập huấn luyện bị từ chối với mã thoát 5, thông
  báo lỗi chỉ rõ đích danh mục tiêu kiểm thử và mục tiêu huấn luyện vi phạm khoảng cách.
- 004 US4, 004 AC-4, FR-009, INV-001, SC-004: Hồ sơ lượt chạy (manifest.json) thiếu cấu hình
  môi trường hoặc thiếu hạt giống huấn luyện thì từ chối đánh giá với mã thoát 5 (TrainSetUnknown),
  tuyệt đối không thực hiện đánh giá khi chưa thể kiểm tra tính không giao cắt.
- 004 US4, 004 AC-4, FR-008, INV-001, SC-004: Lượt đánh giá thành công ghi nhận đầy đủ kết quả
  kiểm tra tính không giao cắt trong báo cáo (report.json) gồm số mục tiêu đã kiểm, khoảng cách
  nhỏ nhất đo được, dải hạt giống đánh giá và danh sách hạt giống huấn luyện.
- 004 US4, 004 AC-4, FR-008, INV-001, SC-004: Hạt giống đánh giá trùng với hạt giống của phiên
  chạy cha trong chuỗi huấn luyện tiếp nối (resume chain) bị từ chối với mã thoát 5.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from eval_fixtures import make_run_dir, run_cli

from mma_ai.environment.targets import Target, TargetGenerator, TargetSet, TargetSetPair
from mma_ai.evaluation.cli import main
from mma_ai.evaluation.errors import EvalError, LeakageError, TrainSetUnknown
from mma_ai.evaluation.split_guard import DisjointnessReport, check_disjoint


def _eval_deps() -> tuple[Any, Any, Any]:
    """Kiểm tra và nạp các thư viện phụ thuộc tùy chọn (optional dependencies) eval và rl."""
    pd = pytest.importorskip("pandas", reason="Cần extra eval (pandas) để chạy đánh giá")
    mpl = pytest.importorskip("matplotlib", reason="Cần extra eval (matplotlib) vẽ biểu đồ")
    torch = pytest.importorskip("torch", reason="Cần extra rl (torch) để chạy CLI")
    return pd, mpl, torch


def test_independent_assertion_leakage_contract() -> None:
    """Khẳng định độc lập trên base chứng minh hợp đồng kiểm thử rò rỉ (INV-001, API-EVL-0003).

    Bảo đảm bộ kiểm thử không bị bỏ qua toàn bộ khi thiếu các phụ thuộc tùy chọn.
    Xác minh sự hiện diện của các hàm và lớp ngoại lệ trọng yếu bảo vệ tính không giao cắt.
    """
    assert callable(check_disjoint), "Hàm check_disjoint phải tồn tại và có thể gọi."
    assert issubclass(DisjointnessReport, object), "Lớp DisjointnessReport phải tồn tại."
    assert issubclass(LeakageError, EvalError), "LeakageError phải kế thừa EvalError."
    assert LeakageError.exit_code == 5, "Mã thoát của LeakageError phải là 5."
    assert issubclass(TrainSetUnknown, EvalError), "TrainSetUnknown phải kế thừa EvalError."
    assert TrainSetUnknown.exit_code == 5, "Mã thoát của TrainSetUnknown phải là 5."
    assert callable(run_cli), "Tiện ích run_cli phải tồn tại trong eval_fixtures."
    assert callable(make_run_dir), "Tiện ích make_run_dir phải tồn tại trong eval_fixtures."


def test_leak_exits5_no_episode_run(tmp_path: Path) -> None:
    """004 US4, 004 AC-4, FR-008, INV-001, SC-004:
    Hạt giống đánh giá trùng seed train thoát mã 5, nêu seed trùng, 0 tập phim chạy.
    """
    _eval_deps()

    train_seed = 42
    run_dir = make_run_dir(tmp_path / "leak_seed_run", seed=train_seed, with_log=True)
    checkpoint_target = run_dir / "checkpoints" / "latest.json"

    # Chạy CLI với --eval-seed trùng đúng hạt giống huấn luyện 42
    res = run_cli([
        "--checkpoint",
        str(checkpoint_target),
        "--eval-seed",
        str(train_seed),
        "--repeats",
        "1",
    ])

    assert res.exit_code == 5, (
        f"Kỳ vọng mã thoát 5 khi rò rỉ hạt giống, nhưng nhận {res.exit_code}.\n"
        f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    )
    assert "LeakageError" in res.stderr
    assert str(train_seed) in res.stderr

    # Chứng minh 0 tập phim (episode) được chạy: không có thư mục eval/ và không có episodes.csv
    eval_dir = run_dir / "eval"
    assert not eval_dir.exists(), f"Thư mục eval/ không được phép tồn tại: {eval_dir}"
    episodes_files = list(run_dir.rglob("episodes.csv"))
    assert len(episodes_files) == 0, f"Không được tạo tệp episodes.csv nào: {episodes_files}"

    # Không in tóm tắt chỉ số đánh giá thành công ra stdout
    assert "KẾT QUẢ ĐÁNH GIÁ CHÍNH SÁCH" not in res.stdout


def test_target_within_min_distance_exits5_names_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """004 US4, 004 AC-4, FR-008, INV-001, SC-004:
    Tập đánh giá có mục tiêu trong khoảng cách tối thiểu thoát mã 5 và nêu mục tiêu vi phạm.
    """
    _eval_deps()

    train_seed = 42
    run_dir = make_run_dir(tmp_path / "target_distance_run", seed=train_seed, with_log=True)
    checkpoint_target = run_dir / "checkpoints" / "latest.json"

    # Tiêm mục tiêu vi phạm khoảng cách tối thiểu vào TargetGenerator qua monkeypatch (gọi tên rõ)
    orig_generate = TargetGenerator.generate

    def patched_generate(self: TargetGenerator, seed: int | None = None) -> TargetSetPair:
        pair = orig_generate(self, seed=seed)
        t0 = pair.train[0]
        # Tạo mục tiêu test cách train #0 chỉ 0.001m (< ngưỡng tối thiểu 0.02m của mô hình)
        close_pos = (t0.position_m[0] + 0.001, t0.position_m[1], t0.position_m[2])
        bad_test_target = Target(index=0, angle_rad=pair.test[0].angle_rad, position_m=close_pos)
        bad_test_targets = (bad_test_target,) + tuple(pair.test[1:])
        bad_test_set = TargetSet(role="test", targets=bad_test_targets)
        return TargetSetPair(
            master_seed=pair.master_seed,
            model_sha256=pair.model_sha256,
            config=pair.config,
            arc=pair.arc,
            train=pair.train,
            test=bad_test_set,
            min_cross_distance_m=0.001,
            fingerprint_sha256=pair.fingerprint_sha256,
        )

    monkeypatch.setattr(TargetGenerator, "generate", patched_generate)

    # Chạy CLI qua điểm vào main của phân hệ đánh giá
    exit_code = main([
        "--checkpoint",
        str(checkpoint_target),
        "--eval-seed",
        "12345",
        "--repeats",
        "1",
    ])
    captured = capsys.readouterr()

    assert exit_code == 5, (
        f"Kỳ vọng mã thoát 5 khi vi phạm khoảng cách mục tiêu, nhưng nhận {exit_code}.\n"
        f"stdout:\n{captured.out}\nstderr:\n{captured.err}"
    )
    assert "LeakageError" in captured.err
    # Thông báo lỗi trên stderr phải chỉ rõ đích danh mục tiêu kiểm thử và huấn luyện vi phạm
    assert "test #0" in captured.err
    assert "train #0" in captured.err

    # Chứng minh 0 tập phim được chạy
    assert not (run_dir / "eval").exists()
    assert len(list(run_dir.rglob("episodes.csv"))) == 0
    assert "KẾT QUẢ ĐÁNH GIÁ CHÍNH SÁCH" not in captured.out


def test_unknown_train_set_exit5(tmp_path: Path) -> None:
    """004 US4, 004 AC-4, FR-009, INV-001, SC-004:
    Hồ sơ thiếu cấu hình môi trường hoặc hạt giống huấn luyện thoát mã 5, không đánh giá không kiểm.
    """
    _eval_deps()

    # Nhánh 1: Hồ sơ manifest thiếu hạt giống huấn luyện (seed)
    run_no_seed = make_run_dir(tmp_path / "run_no_seed", seed=42, with_log=True)
    manifest_file1 = run_no_seed / "manifest.json"
    manifest_data1 = json.loads(manifest_file1.read_text(encoding="utf-8"))
    del manifest_data1["seed"]
    manifest_file1.write_text(json.dumps(manifest_data1), encoding="utf-8")

    res1 = run_cli([
        "--checkpoint",
        str(run_no_seed / "checkpoints" / "latest.json"),
        "--eval-seed",
        "12345",
    ])
    assert res1.exit_code == 5, f"Kỳ vọng mã 5 khi thiếu seed, nhận {res1.exit_code}"
    assert "TrainSetUnknown" in res1.stderr
    assert "seed" in res1.stderr.lower()
    assert not (run_no_seed / "eval").exists()
    assert len(list(run_no_seed.rglob("episodes.csv"))) == 0

    # Nhánh 2: Hồ sơ manifest thiếu cấu hình môi trường (config.env_config)
    run_no_env = make_run_dir(tmp_path / "run_no_env", seed=42, with_log=True)
    manifest_file2 = run_no_env / "manifest.json"
    manifest_data2 = json.loads(manifest_file2.read_text(encoding="utf-8"))
    manifest_data2["config"] = {}
    manifest_file2.write_text(json.dumps(manifest_data2), encoding="utf-8")

    res2 = run_cli([
        "--checkpoint",
        str(run_no_env / "checkpoints" / "latest.json"),
        "--eval-seed",
        "12345",
    ])
    assert res2.exit_code == 5, f"Kỳ vọng mã 5 khi thiếu env_config, nhận {res2.exit_code}"
    assert "TrainSetUnknown" in res2.stderr
    assert not (run_no_env / "eval").exists()
    assert len(list(run_no_env.rglob("episodes.csv"))) == 0


def test_disjointness_recorded_in_report(tmp_path: Path) -> None:
    """004 US4, 004 AC-4, FR-008, INV-001, SC-004:
    Lượt đánh giá thành công ghi nhận kết quả kiểm tra tính không giao cắt trong báo cáo.
    """
    _eval_deps()

    train_seed = 42
    eval_seed = 12345
    run_dir = make_run_dir(tmp_path / "clean_disjoint_run", seed=train_seed, with_log=True)
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
        f"Kỳ vọng mã thoát 0 cho lượt chạy hợp lệ, nhận {res.exit_code}.\n"
        f"stderr:\n{res.stderr}"
    )

    eval_dirs = [
        p for p in (run_dir / "eval").iterdir() if p.is_dir() and not p.name.startswith(".")
    ]
    assert len(eval_dirs) == 1, f"Kỳ vọng đúng 1 thư mục đánh giá hoàn tất, nhận {eval_dirs}"

    report_file = eval_dirs[0] / "report.json"
    assert report_file.is_file(), "Tệp report.json phải được tạo trong thư mục đánh giá"

    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert "disjointness" in report, "Báo cáo phải chứa trường 'disjointness'"

    dj = report["disjointness"]
    assert dj["checked"] is True
    assert dj["passed"] is True
    assert dj["n_train_targets"] > 0
    assert dj["n_eval_targets"] > 0
    assert dj["min_cross_distance_m"] >= dj["min_required_m"]
    assert dj["eval_seed_range"][0] == eval_seed
    assert train_seed in dj["train_seeds"]
    assert dj["train_target_provenance"] in ("rebuilt_from_config", "manifest_fingerprint")
    assert len(dj["target_fingerprint_sha256"]) == 64


def test_resume_chain_seeds_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """004 US4, 004 AC-4, FR-008, INV-001, SC-004:
    Hạt giống đánh giá trùng với seed run cha trong chuỗi kế thừa bị từ chối thoát mã 5.
    """
    _eval_deps()

    # Chuẩn bị tệp cấu hình môi trường tương đối trong tmp_path trước khi chdir (FR-008, INV-001)
    env_yaml_src = Path.cwd() / "src" / "mma_ai" / "environment" / "elbow_env.yaml"
    env_yaml_dst = tmp_path / "src" / "mma_ai" / "environment" / "elbow_env.yaml"
    env_yaml_dst.parent.mkdir(parents=True, exist_ok=True)
    env_yaml_dst.write_text(env_yaml_src.read_text(encoding="utf-8"), encoding="utf-8")

    # Dùng thư mục tạm làm thư mục làm việc để paths.runs_dir tương đối hợp lệ (INV-004)
    monkeypatch.chdir(tmp_path)
    runs_dir = Path("runs")
    runs_dir.mkdir(exist_ok=True)

    parent_seed = 42
    child_seed = 99

    # 1. Tạo phiên chạy cha (run_parent) với hạt giống 42
    parent_dir = runs_dir / "run_parent"
    make_run_dir(parent_dir, seed=parent_seed, with_log=True)

    # 2. Tạo phiên chạy con (run_child) kế thừa từ run_parent
    child_dir = runs_dir / "run_child"
    make_run_dir(
        child_dir,
        seed=child_seed,
        with_log=True,
        resumed_from={
            "run_id": "run_parent",
            "checkpoint": "checkpoints/ckpt_u000001.pt",
            "checkpoint_sha256": "0" * 64,
        },
    )

    checkpoint_target = child_dir / "checkpoints" / "latest.json"

    # Chạy CLI đánh giá run_child nhưng chọn --eval-seed trùng với hạt giống phiên chạy cha (42)
    res = run_cli([
        "--checkpoint",
        str(checkpoint_target),
        "--runs-dir",
        "runs",
        "--eval-seed",
        str(parent_seed),
        "--repeats",
        "1",
    ])

    assert res.exit_code == 5, (
        f"Kỳ vọng mã thoát 5 khi trùng seed run cha, nhưng nhận {res.exit_code}.\n"
        f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    )
    assert "LeakageError" in res.stderr
    assert str(parent_seed) in res.stderr

    # Chứng minh 0 tập phim được chạy trên run_child
    assert not (child_dir / "eval").exists()
    assert len(list(child_dir.rglob("episodes.csv"))) == 0
