"""Bộ điều phối luồng đánh giá chính sách và so sánh đối chuẩn (API-EVL-0002, CMD-EVL-0001).

Hiện thực quy trình đánh giá chuẩn xác theo hợp đồng thứ tự contracts/cli.md:
- Bước 1: Nạp và kiểm tra cấu hình đánh giá bất biến (EvalConfig).
- Bước 2: Nạp điểm kiểm tra (checkpoint) chỉ-đọc và kiểm tra tính hợp lệ.
- Bước 3: Đọc hồ sơ run (manifest.json), kiểm tra mã băm XML giữa mô hình, checkpoint và manifest.
- Bước 4: Kiểm tra tính không giao cắt (check_disjoint) TRƯỚC tập phim đầu (INV-001).
- Bước 5: Chạy tập phim hai chính sách bằng cùng một hàm rollout trên cùng tập mục tiêu (INV-002).
- Bước 6: Tính toán chỉ số thống kê (summarize) và đưa ra kết luận (decide).
- Bước 7: Đọc nhật ký huấn luyện và kết xuất biểu đồ không cần màn hình (render_charts).
- Bước 8: Dựng báo cáo và công bố nguyên tử bằng thao tác đổi tên (publish_report, INV-004).

Bảo đảm các bất biến miền:
- 004 FR-001, 004 AC-1: So sánh đối chuẩn chính sách đã học với chính sách ngẫu nhiên.
- 004 FR-002, 004 INV-002: Thứ tự và hạt giống mục tiêu nhất quán giữa hai chính sách.
- 004 FR-007, 004 INV-006: Tiêu chí đánh giá cố định, không thay đổi theo kết quả.
- 004 FR-008, 004 INV-001: Rò rỉ dữ liệu bị ngăn chặn ngay lập tức, không chạy tập phim nào.
- 004 FR-009, 004 FR-015: Checkpoint ngoài run đòi hỏi out_dir, từ chối khi không rõ tập train.
- 004 FR-010, 004 FR-011: Thiếu nhật ký thoát mã 6 nhưng vẫn lưu báo cáo số liệu đầy đủ.
- 004 FR-013, 004 KQ-4: Lưu trữ kết quả đầy đủ trong runs/<run_id>/eval/<eval_id>/.
- 004 FR-014, 004 INV-005: Hoàn toàn chỉ-đọc với dữ liệu của con 2, không sửa tệp ngoài eval/.
- 004 FR-015, 004 AC-5: Checkpoint hỏng hoặc sai mã băm XML ném CheckpointUnusable (mã 4).
- 004 INV-004, 004 AC-5: Lỗi hoặc ngắt quãng không để lại kết quả dở dang.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from mma_ai.environment.env_config import ElbowEnvConfig
from mma_ai.environment.single_agent import ElbowReachEnv
from mma_ai.environment.targets import TargetGenerator
from mma_ai.evaluation.charts import ChartData, ChartResult, render_charts
from mma_ai.evaluation.errors import (
    CheckpointUnusable,
    EvalConfigError,
    EvalError,
    EvalWriteError,
    LogMissing,
    TrainSetUnknown,
)
from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.metrics import PolicyResult, read_training_log, summarize
from mma_ai.evaluation.policies import LearnedPolicy, RandomPolicy
from mma_ai.evaluation.report import (
    build_report,
    generate_eval_id,
    publish_report,
    save_evaluation_result,
)
from mma_ai.evaluation.rollout import EpisodeRecord, run_policy_on_targets
from mma_ai.evaluation.split_guard import check_disjoint
from mma_ai.evaluation.stats import Verdict, decide
from mma_ai.physics.body_model import load_muscle_model


@dataclass(frozen=True)
class EvalResult:
    """Kết quả hoàn tất của một lượt đánh giá chính sách (API-EVL-0002, DM-004).

    Attributes:
        eval_dir: Đường dẫn thư mục công bố kết quả đánh giá (runs/<run_id>/eval/<eval_id>/).
        report: Từ điển báo cáo hoàn chỉnh theo eval-report.schema.json.
        charts_status: Trạng thái của biểu đồ ('complete' hoặc 'incomplete').
        status: Trạng thái tổng thể ('done' hoặc 'done_charts_incomplete').
        exit_code: Mã thoát chuẩn CLI (0 nếu done, 6 nếu done_charts_incomplete).
        eval_id: Định danh lượt đánh giá chuẩn UTC.
        verdict: Kết luận so sánh thống kê Verdict.
    """

    eval_dir: Path
    report: dict[str, Any]
    charts_status: str
    status: str = "done"
    exit_code: int = 0
    eval_id: str = ""
    verdict: Verdict | None = None


def get_exit_code(err: BaseException) -> int:
    """Ánh xạ ngoại lệ sang mã thoát CLI ổn định theo hợp đồng contracts/cli.md.

    Args:
        err: Đối tượng ngoại lệ bắt được trong quá trình thực thi.

    Returns:
        int: Mã số thoát quy định cho dòng lệnh (0, 1, 2, 4, 5, 6, 7, 130).
    """
    if isinstance(err, KeyboardInterrupt):
        return 130
    if isinstance(err, EvalError):
        return err.exit_code
    return 1


def _compute_sha256(path: Path | str) -> str:
    """Tính mã băm SHA-256 nội dung của tệp theo từng khối 64KB."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _resolve_checkpoint_file(checkpoint: str | Path) -> Path:
    """Phân giải đường dẫn tệp điểm kiểm tra .pt từ đường dẫn hoặc con trỏ latest.json.

    Args:
        checkpoint: Đường dẫn tệp .pt hoặc .json.

    Returns:
        Path: Đường dẫn tệp .pt thực tế tồn tại trên hệ thống.

    Raises:
        CheckpointUnusable: Khi tệp không tồn tại hoặc con trỏ hỏng (mã thoát 4).
    """
    ckpt_path = Path(checkpoint)
    if not ckpt_path.is_file():
        raise CheckpointUnusable(
            f"Tệp checkpoint '{checkpoint}' không tồn tại hoặc không phải là tệp hợp lệ."
        )

    if ckpt_path.name == "latest.json" or ckpt_path.suffix == ".json":
        try:
            info = json.loads(ckpt_path.read_text(encoding="utf-8"))
        except Exception as err:
            raise CheckpointUnusable(
                f"Không thể đọc nội dung tệp con trỏ JSON '{ckpt_path}': {err}"
            ) from err

        if not isinstance(info, Mapping) or "path" not in info or not isinstance(info["path"], str):
            raise CheckpointUnusable(
                f"Tệp con trỏ '{ckpt_path}' không chứa trường 'path' hợp lệ trỏ tới checkpoint."
            )

        rel_pt = info["path"]
        # Thử tìm tương đối so với thư mục cha của checkpoints/ (run_dir)
        run_root = ckpt_path.parent.parent
        resolved_pt = run_root / rel_pt
        if not resolved_pt.is_file():
            # Thử tìm tương đối so với thư mục hiện tại của con trỏ
            resolved_pt = ckpt_path.parent / Path(rel_pt).name

        if not resolved_pt.is_file():
            raise CheckpointUnusable(
                f"Tệp checkpoint thực tế '{rel_pt}' được trỏ bởi '{ckpt_path}' không tồn tại."
            )
        return resolved_pt

    return ckpt_path


def _find_run_directory_and_manifest(
    pt_path: Path,
    runs_dir: str,
) -> tuple[Path | None, Path | None]:
    """Tìm kiếm thư mục run và tệp manifest.json tương ứng của checkpoint.

    Args:
        pt_path: Đường dẫn tệp checkpoint .pt.
        runs_dir: Thư mục chứa các phiên chạy cấu hình trong EvalConfig.

    Returns:
        tuple[Path | None, Path | None]: Cặp (run_dir, manifest_file) nếu tìm thấy.
    """
    # 1. Kiểm tra vị trí chuẩn: runs/<run_id>/checkpoints/*.pt
    if pt_path.parent.name == "checkpoints":
        potential_run = pt_path.parent.parent
        potential_manifest = potential_run / "manifest.json"
        if potential_manifest.is_file():
            return potential_run, potential_manifest

    # 2. Kiểm tra nếu checkpoint nằm trực tiếp trong thư mục run
    potential_manifest = pt_path.parent / "manifest.json"
    if potential_manifest.is_file():
        return pt_path.parent, potential_manifest

    # 3. Thử tìm kiếm trong runs_dir đã cấu hình
    cand_run = Path(runs_dir) / pt_path.parent.name
    cand_manifest = cand_run / "manifest.json"
    if cand_manifest.is_file():
        return cand_run, cand_manifest

    return None, None


def evaluate_checkpoint(
    checkpoint: str | Path,
    cfg: EvalConfig | None = None,
    out_dir: str | Path | None = None,
) -> EvalResult:
    """Điều phối toàn bộ quy trình đánh giá điểm kiểm tra theo hợp đồng API-EVL-0002.

    Thực hiện nghiêm ngặt thứ tự 8 bước của contracts/cli.md:
    1. Kiểm tra cấu hình.
    2. Nạp checkpoint chỉ-đọc.
    3. Đọc manifest và đối chiếu mã băm XML.
    4. Kiểm tra ranh giới dữ liệu không giao cắt (check_disjoint).
    5. Chạy tập phim hai chính sách trên cùng tập mục tiêu kiểm thử.
    6. Tính toán chỉ số thống kê và kết luận so sánh.
    7. Đọc nhật ký và vẽ bộ ba biểu đồ không đầu (headless charts).
    8. Dựng báo cáo và công bố nguyên tử bằng thao tác đổi tên thư mục tạm.

    Args:
        checkpoint: Đường dẫn tệp .pt hoặc latest.json của checkpoint cần đánh giá.
        cfg: Cấu hình đánh giá EvalConfig tuỳ chọn (mặc định nạp gói eval_elbow.yaml).
        out_dir: Thư mục xuất kết quả tuỳ chọn (bắt buộc khi checkpoint ngoài thư mục run).

    Returns:
        EvalResult: Đối tượng kết quả chứa đường dẫn, báo cáo, và trạng thái biểu đồ.

    Raises:
        CheckpointUnusable: Khi checkpoint hỏng, không tồn tại hoặc sai mã băm XML (mã 4).
        EvalConfigError: Khi cấu hình sai tham số hoặc thiếu out_dir bắt buộc (mã 2).
        LeakageError: Khi rò rỉ tập mục tiêu hoặc hạt giống trùng nhau (mã 5).
        TrainSetUnknown: Khi không thiết lập được tập huấn luyện của run (mã 5).
        EvalWriteError: Khi lỗi ghi đĩa hoặc không thể đổi tên công bố báo cáo (mã 7).
    """
    start_time = time.time()

    # BƯỚC 1: Nạp và kiểm tra cấu hình đánh giá (FR-007, FR-018, INV-006)
    if cfg is None:
        eval_cfg = EvalConfig.load()
    elif isinstance(cfg, EvalConfig):
        eval_cfg = cfg
    elif isinstance(cfg, (str, Path)):
        eval_cfg = EvalConfig.load(path=cfg)
    else:
        raise EvalConfigError(f"Kiểu cấu hình không hợp lệ: {type(cfg).__name__} (mã thoát 2).")

    if eval_cfg.episodes.min_targets < 2:
        raise EvalConfigError(
            f"Số lượng mục tiêu tối thiểu (min_targets={eval_cfg.episodes.min_targets}) "
            "phải lớn hơn hoặc bằng 2 để bảo đảm tính đúng của khoảng tin cậy (mã thoát 2)."
        )

    # BƯỚC 2: Nạp checkpoint chỉ-đọc (FR-015, INV-004, AC-5)
    pt_path = _resolve_checkpoint_file(checkpoint)
    checkpoint_sha256 = _compute_sha256(pt_path)

    try:
        from mma_ai.learning.checkpoint import load_checkpoint

        loaded_ckpt = load_checkpoint(pt_path, for_training=False)
    except CheckpointUnusable:
        raise
    except Exception as err:
        raise CheckpointUnusable(
            f"Điểm kiểm tra (checkpoint) tại '{pt_path}' không dùng được hoặc bị hỏng: {err}"
        ) from err

    ckpt_model_sha256 = loaded_ckpt.model_sha256
    update_idx = loaded_ckpt.update_idx
    env_steps = loaded_ckpt.env_steps
    checkpoint_saved_with = loaded_ckpt.library_versions

    learned_policy = LearnedPolicy(pt_path)

    # BƯỚC 3: Đọc hồ sơ run và đối chiếu mã băm XML mô hình (FR-014, FR-015, INV-002)
    run_dir, manifest_file = _find_run_directory_and_manifest(
        pt_path, eval_cfg.paths.runs_dir
    )

    if manifest_file is None or run_dir is None:
        # Checkpoint nằm ngoài thư mục run
        if out_dir is None:
            raise EvalConfigError(
                "Checkpoint nằm ngoài thư mục run nhưng thiếu tham số out_dir (--out) "
                "để chỉ định nơi lưu trữ kết quả đánh giá (mã thoát 2)."
            )
        raise TrainSetUnknown(
            f"Không thể thiết lập hồ sơ run và tập huấn luyện cho checkpoint ngoài thư mục run: "
            f"không tìm thấy manifest.json cạnh '{pt_path}' (mã thoát 5)."
        )

    try:
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as err:
        raise TrainSetUnknown(
            f"Không thể đọc hồ sơ run manifest.json tại '{manifest_file}': {err}"
        ) from err

    run_id = str(manifest_data.get("run_id") or run_dir.name)
    run_status = str(manifest_data.get("status", "done"))
    run_seed = int(manifest_data.get("seed", 0))
    manifest_model_sha256 = str(manifest_data.get("model", {}).get("sha256", ""))
    muscle_names_from_manifest = manifest_data.get("model", {}).get("muscle_names")

    body_model = load_muscle_model("myoelbow")
    current_model_sha256 = body_model.info.sha256

    if ckpt_model_sha256 and ckpt_model_sha256 != current_model_sha256:
        raise CheckpointUnusable(
            f"Mã băm XML mô hình trong checkpoint ({ckpt_model_sha256}) không khớp "
            f"với mô hình môi trường hiện tại ({current_model_sha256}) (mã thoát 4)."
        )

    if manifest_model_sha256 and manifest_model_sha256 != current_model_sha256:
        raise CheckpointUnusable(
            f"Mã băm XML mô hình trong hồ sơ run ({manifest_model_sha256}) không khớp "
            f"với mô hình môi trường hiện tại ({current_model_sha256}) (mã thoát 4)."
        )

    if muscle_names_from_manifest and len(muscle_names_from_manifest) == 6:
        muscle_names = list(muscle_names_from_manifest)
    else:
        muscle_names = list(body_model.info.muscle_names)

    # Chuẩn hoá đường dẫn tương đối của checkpoint theo hồ sơ run
    try:
        rel_checkpoint_path = str(pt_path.relative_to(run_dir)).replace("\\", "/")
    except ValueError:
        rel_checkpoint_path = f"checkpoints/{pt_path.name}"

    # BƯỚC 4: Kiểm tra không giao cắt ranh giới dữ liệu (FR-008, INV-001, AC-4)
    disjoint_report = check_disjoint(run=run_dir, cfg=eval_cfg)
    n_eval_targets = disjoint_report.n_eval_targets

    if n_eval_targets < eval_cfg.episodes.min_targets:
        raise EvalConfigError(
            f"Số lượng mục tiêu đánh giá ({n_eval_targets}) nhỏ hơn số lượng "
            f"tối thiểu yêu cầu ({eval_cfg.episodes.min_targets}) (mã thoát 2)."
        )

    # BƯỚC 5: Chạy tập phim hai chính sách trên cùng tập mục tiêu (FR-001, FR-002, INV-002)
    env_cfg_path_str = eval_cfg.paths.env_config_override or manifest_data.get("config", {}).get(
        "env_config"
    )
    if not env_cfg_path_str:
        raise TrainSetUnknown("Không tìm thấy cấu hình môi trường trong hồ sơ run.")

    resolved_env_cfg: Path | None = None
    for cand in [Path(env_cfg_path_str), run_dir / env_cfg_path_str]:
        if cand.is_file():
            resolved_env_cfg = cand
            break

    if resolved_env_cfg is None:
        raise TrainSetUnknown(
            f"Không tìm thấy tệp cấu hình môi trường tại '{env_cfg_path_str}'."
        )

    loaded_env_cfg = ElbowEnvConfig.load(resolved_env_cfg)
    target_gen = TargetGenerator(
        model=body_model.model, cfg=loaded_env_cfg, model_sha256=current_model_sha256
    )
    eval_pair = target_gen.generate(seed=loaded_env_cfg.targets.default_seed)

    env = ElbowReachEnv(cfg=loaded_env_cfg, targets=eval_pair, split="test")
    random_policy = RandomPolicy(seed=eval_cfg.seeds.random_policy, act_dim=6)

    repeats = eval_cfg.episodes.repeats
    seed_base = eval_cfg.seeds.episode_base

    eval_base_dir = Path(out_dir) if out_dir is not None else run_dir / "eval"
    try:
        existing_ids = (
            [p.name for p in eval_base_dir.iterdir() if p.is_dir()]
            if eval_base_dir.is_dir()
            else []
        )
    except OSError:
        existing_ids = []
    eval_id = generate_eval_id(episode_base=seed_base, existing_ids=existing_ids)
    tmp_dir = eval_base_dir / f".tmp-{eval_id}"
    final_eval_dir = eval_base_dir / eval_id

    # Khởi tạo thư mục tạm trước khi thực hiện các tác vụ tạo tệp (INV-004, FR-013)
    try:
        eval_base_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        raise EvalWriteError(
            f"Không thể khởi tạo thư mục kết quả đánh giá tại '{eval_base_dir}': {err}"
        ) from err

    try:
        # Thực hiện các tập phim đánh giá cho cả hai chính sách
        learned_records = run_policy_on_targets(
            env=env,
            policy=learned_policy,
            n_targets=n_eval_targets,
            repeats=repeats,
            seed_base=seed_base,
            policy_name="learned",
        )
        random_records = run_policy_on_targets(
            env=env,
            policy=random_policy,
            n_targets=n_eval_targets,
            repeats=repeats,
            seed_base=seed_base,
            policy_name="random",
        )
        all_records: list[EpisodeRecord] = list(learned_records) + list(random_records)

        # BƯỚC 6: Tính toán chỉ số thống kê và kết luận so sánh (FR-004, FR-006, INV-006)
        learned_result: PolicyResult = summarize(learned_records, eval_cfg)
        random_result: PolicyResult = summarize(random_records, eval_cfg)
        verdict: Verdict = decide(
            learned_result, random_result, level=eval_cfg.criterion.confidence_level
        )

        # BƯỚC 7: Đọc nhật ký huấn luyện và kết xuất biểu đồ (FR-010, FR-011, AC-3)
        tmp_charts_dir = tmp_dir / "charts"
        tmp_charts_dir.mkdir(parents=True, exist_ok=True)

        try:
            training_log = read_training_log(run_dir, eval_cfg)
            charts_result = render_charts(
                log=training_log,
                muscle_names=muscle_names,
                out_dir=tmp_charts_dir,
                cfg=eval_cfg,
            )
        except LogMissing as err:
            charts_result = ChartResult(
                status="incomplete",
                files={"loss": None, "reward": None, "activation": None},
                points_plotted={"loss": 0, "reward": 0, "activation": 0},
                points_dropped=0,
                reason=str(err),
                log_source=None,
                data=ChartData([], {}),
            )
        except Exception as err:
            charts_result = ChartResult(
                status="incomplete",
                files={"loss": None, "reward": None, "activation": None},
                points_plotted={"loss": 0, "reward": 0, "activation": 0},
                points_dropped=0,
                reason=f"Lỗi khi xử lý biểu đồ: {err}",
                log_source=None,
                data=ChartData([], {}),
            )

        # BƯỚC 8: Dựng báo cáo và công bố nguyên tử (FR-013, FR-014, INV-004, INV-005)
        wall_clock_seconds = round(time.time() - start_time, 2)
        report_data = build_report(
            eval_id=eval_id,
            run_id=run_id,
            run_status=run_status,
            run_seed=run_seed,
            train_seeds=list(disjoint_report.train_seeds),
            checkpoint_path=rel_checkpoint_path,
            checkpoint_sha256=checkpoint_sha256,
            update_idx=update_idx,
            env_steps=env_steps,
            model_sha256=current_model_sha256,
            muscle_names=muscle_names,
            cfg=eval_cfg,
            disjointness=disjoint_report,
            learned=learned_result,
            random=random_result,
            verdict=verdict,
            charts=charts_result,
            wall_clock_seconds=wall_clock_seconds,
            checkpoint_saved_with=checkpoint_saved_with,
        )

        save_evaluation_result(tmp_dir=tmp_dir, report=report_data, records=all_records)
        published_dir = publish_report(tmp_dir=tmp_dir, eval_dir=final_eval_dir)

        overall_status = str(report_data.get("status", "done"))
        exit_code = 0 if overall_status == "done" else 6

        return EvalResult(
            eval_dir=published_dir,
            report=report_data,
            charts_status=charts_result.status,
            status=overall_status,
            exit_code=exit_code,
            eval_id=eval_id,
            verdict=verdict,
        )

    except KeyboardInterrupt:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


__all__: list[str] = [
    "EvalResult",
    "evaluate_checkpoint",
    "get_exit_code",
]
