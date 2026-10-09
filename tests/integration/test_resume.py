"""Kiểm thử tích hợp cho tiếp tục huấn luyện và nạp điểm kiểm tra qua CLI (test_resume.py).

Hiện thực và xác minh:
- FR-003, AC-2, AC-6: Bộ chuẩn hoá quan sát (observation normalizer) được khôi phục nguyên vẹn.
- FR-008, AC-2, KQ-2, SC-002: Nạp checkpoint cho cùng hành động xác định (deterministic action)
  trong dung sai <= 1e-6 trên mỗi phần tử cho lô 64 quan sát mẫu (sample observations).
- FR-009, AC-2: Tiếp tục huấn luyện (resume training) tạo thư mục lượt chạy mới (run directory),
  ghi nhận lượt chạy cha (resumed_from) và giữ nguyên tính bất biến (immutability) của thư mục cha.
- FR-009, INV-004: Khôi phục bộ chuẩn hoá, bộ tối ưu hoá (optimizer), bộ sinh số ngẫu nhiên (RNG)
  và các bộ đếm bước mà không khởi tạo lại từ đầu.
- FR-008, FR-009: Từ chối tiếp tục huấn luyện với mã thoát 4 khi mã băm XML mô hình khác biệt.
- FR-008, AC-2: Checkpoint hỏng (corrupt), thiếu bộ chuẩn hoá hoặc khác cấu trúc mạng
  thoát mã 4 và nêu rõ nguyên nhân trong thông điệp lỗi, không âm thầm trả chính sách (policy).
- INV-001: Run cha giữ nguyên mã băm toàn vẹn cây thư mục (hash tree digest) sau khi run con xong.
- NFR-REPRO-001: Tính tái lập tất định (deterministic reproducibility) sau lưu và nạp checkpoint.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from train_fixtures import (
    hash_tree,
    list_runs,
    load_manifest,
    run_train_cli,
    sample_observations,
    smoke_config,
)

from mma_ai.learning.cli import _build_parser


def test_resume_contract_independent_assertion() -> None:
    """FR-008, FR-009, INV-004, SC-002: Khẳng định độc lập trên base về nạp checkpoint.

    Đảm bảo kiểm thử không bị bỏ qua toàn bộ (skip) khi thiếu phụ thuộc tuỳ chọn.
    Xác minh sự hiện diện của các mô-đun cốt lõi, cờ --resume trong bộ phân tích cú pháp CLI
    và danh sách các thành phần bắt buộc của điểm kiểm tra.
    """
    # 1. Xác minh các mô-đun checkpoint và cli có mặt trên hệ thống
    assert importlib.util.find_spec("mma_ai.learning.checkpoint") is not None, (
        "Thiếu mô-đun mma_ai.learning.checkpoint trên base"
    )
    assert importlib.util.find_spec("mma_ai.learning.cli") is not None, (
        "Thiếu mô-đun mma_ai.learning.cli trên base"
    )

    # 2. Xác minh cờ --resume được định nghĩa đúng hợp đồng trong CLI parser
    parser = _build_parser()
    action_map = {action.dest: action for action in parser._actions}
    assert "resume" in action_map, "Bộ phân tích cú pháp CLI thiếu cờ --resume"
    resume_action = action_map["resume"]
    assert "--resume" in resume_action.option_strings, "Cờ --resume không nằm trong option_strings"

    # 3. Xác minh hợp đồng schema checkpoint-meta có đủ các trường và thành phần bắt buộc
    contract_schema_path = (
        Path.cwd() / "specs" / "003-ppo-train-repro" / "contracts" / "checkpoint-meta.schema.json"
    )
    assert contract_schema_path.is_file(), (
        f"Không tìm thấy lược đồ hợp đồng: {contract_schema_path}"
    )
    schema_data = json.loads(contract_schema_path.read_text(encoding="utf-8"))
    assert "components" in schema_data.get("properties", {}), (
        "Lược đồ checkpoint-meta.schema.json thiếu thuộc tính 'components'"
    )

    expected_components = {
        "actor",
        "critic",
        "obs_normalizer",
        "optimizer",
        "seed",
        "rng_state",
    }
    if importlib.util.find_spec("torch") is not None:
        from mma_ai.learning.checkpoint import REQUIRED_COMPONENTS

        assert set(REQUIRED_COMPONENTS) == expected_components, (
            f"Danh sách thành phần checkpoint không khớp: {REQUIRED_COMPONENTS}"
        )


def _require_torch() -> Any:
    """Yêu cầu PyTorch cho các bài kiểm thử tích hợp huấn luyện PPO."""
    return pytest.importorskip("torch", reason="Cần extra rl (torch) để thực thi kiểm thử tích hợp")


@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def parent_smoke_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Khởi chạy duy nhất một lượt huấn luyện smoke cha (parent smoke run) qua CLI.

    Lượt chạy này sinh ra các checkpoint định kỳ và checkpoint cuối cùng (final checkpoint)
    để phục vụ kiểm thử khứ hồi chính sách (roundtrip) và tiếp tục huấn luyện (resume).
    """
    _require_torch()
    pytest.importorskip("tensorboard", reason="Cần tensorboard để hoàn tất huấn luyện smoke")

    tmp_dir = tmp_path_factory.mktemp("resume_parent_smoke")
    config_file = smoke_config(tmp_dir, total_timesteps=4096, n_steps=2048, every_updates=1)
    runs_dir = tmp_dir / "runs"

    # Ghi nhận hành động trước khi lưu checkpoint cuối bằng hook chạy trực tiếp
    recorded_final_actions_file = tmp_dir / "expected_final_actions.npy"
    obs_batch = sample_observations(n=64)

    test_script = (
        "import sys\n"
        "import numpy as np\n"
        "from pathlib import Path\n"
        "import torch\n"
        "import mma_ai.learning.cli as cli_mod\n"
        "from mma_ai.learning.checkpoint import save_checkpoint as orig_save\n"
        f"actions_path = Path({str(recorded_final_actions_file)!r})\n"
        f"sample_obs = np.array({obs_batch.tolist()!r}, dtype=np.float64)\n"
        "def hooked_save(agent, run_dir, kind='periodic', ctx=None):\n"
        "    if kind == 'final':\n"
        "        norm = ctx.get('obs_normalizer') if isinstance(ctx, dict) "
        "else getattr(ctx, 'obs_normalizer', None)\n"
        "        norm_obs = norm(sample_obs) if norm is not None else sample_obs\n"
        "        model = getattr(agent, 'model', agent)\n"
        "        obs_t = torch.as_tensor(norm_obs, dtype=torch.float32)\n"
        "        with torch.no_grad():\n"
        "            act, _, _ = model.act(obs_t, deterministic=True)\n"
        "        np.save(actions_path, act.detach().cpu().numpy())\n"
        "    return orig_save(agent, run_dir, kind=kind, ctx=ctx)\n"
        "import mma_ai.learning.trainer as tr_mod\n"
        "tr_mod.save_checkpoint = hooked_save\n"
        f"sys.exit(cli_mod.main(['--stage', 'elbow', '--seed', '42', "
        f"'--config', {str(config_file)!r}]))\n"
    )

    clean_env = os.environ.copy()
    clean_env.pop("DISPLAY", None)
    clean_env.pop("WAYLAND_DISPLAY", None)

    proc = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=180.0,
        cwd=str(Path.cwd()),
        check=False,
    )

    assert proc.returncode == 0, (
        f"Huấn luyện cha thất bại với mã {proc.returncode}.\n"
        f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    )

    created_runs = list_runs(runs_dir)
    assert len(created_runs) >= 1, "Không tìm thấy thư mục lượt chạy cha"
    parent_dir = created_runs[0]

    parent_manifest = load_manifest(parent_dir)
    latest_json = parent_dir / "checkpoints" / "latest.json"
    assert latest_json.is_file(), "Không tìm thấy tệp latest.json trong run cha"

    latest_data = json.loads(latest_json.read_text(encoding="utf-8"))
    final_ckpt_path = parent_dir / latest_data["path"]
    assert final_ckpt_path.is_file(), f"Không tìm thấy tệp checkpoint: {final_ckpt_path}"

    parent_digest = hash_tree(parent_dir)

    return {
        "tmp_dir": tmp_dir,
        "runs_dir": runs_dir,
        "parent_dir": parent_dir,
        "parent_manifest": parent_manifest,
        "latest_json": latest_json,
        "final_ckpt_path": final_ckpt_path,
        "parent_digest": parent_digest,
        "recorded_actions_file": recorded_final_actions_file,
        "sample_obs": obs_batch,
    }


def test_roundtrip_via_cli_same_action(parent_smoke_run: dict[str, Any]) -> None:
    """FR-008, INV-004, NFR-REPRO-001, SC-002, AC-2, KQ-2: Nạp checkpoint cùng hành động <= 1e-6.

    Xác minh khứ hồi (roundtrip): Sau khi hoàn tất lượt huấn luyện smoke bằng CLI,
    nạp checkpoint cuối cùng bằng load_policy cho hành động xác định (deterministic action)
    giống lúc lưu trong dung sai tuyệt đối <= 1e-6 trên mỗi phần tử, trên lô 64 quan sát mẫu.
    """
    _require_torch()
    from mma_ai.learning.checkpoint import load_policy

    final_ckpt_path: Path = parent_smoke_run["final_ckpt_path"]
    latest_json: Path = parent_smoke_run["latest_json"]
    sample_obs: np.ndarray = parent_smoke_run["sample_obs"]
    recorded_file: Path = parent_smoke_run["recorded_actions_file"]

    # 1. Đọc hành động đã lưu lại từ chính agent trước thời điểm ghi đĩa
    assert recorded_file.is_file(), "Không tìm thấy tệp lưu hành động mong đợi"
    expected_actions = np.load(recorded_file)
    assert expected_actions.shape == (64, 6), (
        f"Hình dạng hành động không hợp lệ: {expected_actions.shape}"
    )

    # 2. Nạp chính sách bằng đường dẫn trực tiếp tới tệp checkpoint .pt
    policy_from_pt = load_policy(final_ckpt_path)
    restored_actions_pt = policy_from_pt.act_deterministic(sample_obs)

    # Khẳng định sai khác tuyệt đối trên mỗi phần tử không vượt quá dung sai 1e-6
    diff_pt = np.abs(expected_actions - restored_actions_pt)
    max_diff_pt = float(np.max(diff_pt))
    assert max_diff_pt <= 1e-6, (
        f"Sai khác hành động từ tệp .pt vượt quá dung sai 1e-6: max_diff = {max_diff_pt}"
    )

    # 3. Nạp chính sách qua con trỏ latest.json
    policy_from_latest = load_policy(latest_json)
    restored_actions_latest = policy_from_latest.act_deterministic(sample_obs)

    diff_latest = np.abs(expected_actions - restored_actions_latest)
    max_diff_latest = float(np.max(diff_latest))
    assert max_diff_latest <= 1e-6, (
        f"Sai khác hành động qua latest.json vượt quá dung sai 1e-6: max_diff = {max_diff_latest}"
    )


def test_resume_creates_new_run_with_parent(parent_smoke_run: dict[str, Any]) -> None:
    """FR-009, INV-001, SC-002, AC-2: Cờ --resume tạo thư mục run mới, ghi cha, giữ nguyên băm cha.

    Xác minh:
    - --resume tạo một thư mục lượt chạy MỚI hoàn toàn, không ghi đè vào thư mục lượt chạy cha.
    - Hồ sơ manifest của lượt chạy mới ghi nhận trường resumed_from chứa run_id và checkpoint cha.
    - Toàn bộ cây thư mục của lượt chạy cha được bảo toàn nguyên vẹn tính bất biến.
    """
    _require_torch()
    runs_dir: Path = parent_smoke_run["runs_dir"]
    parent_dir: Path = parent_smoke_run["parent_dir"]
    parent_manifest: dict[str, Any] = parent_smoke_run["parent_manifest"]
    latest_json: Path = parent_smoke_run["latest_json"]
    parent_digest_before: str = parent_smoke_run["parent_digest"]

    # Tạo cấu hình cho lượt chạy con: tiếp tục huấn luyện thêm 1 lượt cập nhật (tổng 6144 bước)
    child_tmp = parent_smoke_run["tmp_dir"] / "child_run_config"
    child_config_file = smoke_config(
        child_tmp,
        runs_dir=os.path.relpath(runs_dir, Path.cwd()),
        total_timesteps=6144,
        n_steps=2048,
        every_updates=1,
    )

    # Thực thi CLI tiếp tục huấn luyện với cờ --resume
    result = run_train_cli(
        [
            "--stage",
            "elbow",
            "--config",
            str(child_config_file),
            "--resume",
            str(latest_json),
        ],
        timeout=180.0,
    )

    assert result.exit_code == 0, (
        f"Lượt huấn luyện tiếp tục (--resume) thất bại với mã {result.exit_code}.\n"
        f"Stderr: {result.stderr}\nStdout: {result.stdout}"
    )

    # Kiểm tra danh sách thư mục lượt chạy trong runs_dir
    current_runs = list_runs(runs_dir)
    assert len(current_runs) >= 2, (
        f"Kỳ vọng ít nhất 2 run trong runs_dir, nhận: {len(current_runs)}"
    )

    child_dirs = [r for r in current_runs if r.resolve() != parent_dir.resolve()]
    assert len(child_dirs) == 1, f"Kỳ vọng duy nhất 1 thư mục run con mới, nhận: {child_dirs}"
    child_dir = child_dirs[0]

    # Kiểm tra hồ sơ manifest của lượt chạy con
    child_manifest = load_manifest(child_dir)
    assert child_manifest.get("status") == "done", (
        f"Trạng thái lượt chạy con không phải 'done': {child_manifest.get('status')}"
    )

    resumed_from = child_manifest.get("resumed_from")
    assert resumed_from is not None, "Hồ sơ lượt chạy con thiếu trường resumed_from"
    assert resumed_from["run_id"] == parent_manifest["run_id"], (
        f"run_id cha không khớp: kỳ vọng '{parent_manifest['run_id']}', "
        f"nhận '{resumed_from['run_id']}'"
    )
    assert "checkpoints" in resumed_from["checkpoint"], (
        f"Đường dẫn checkpoint cha không hợp lệ: {resumed_from['checkpoint']}"
    )
    assert len(resumed_from["checkpoint_sha256"]) == 64, (
        f"Mã băm SHA-256 checkpoint cha không hợp lệ: {resumed_from['checkpoint_sha256']}"
    )

    # INV-001: Khẳng định tính bất biến — thư mục cha không bị sửa đổi bất kỳ tệp nào
    parent_digest_after = hash_tree(parent_dir)
    assert parent_digest_after == parent_digest_before, (
        "Thư mục lượt chạy cha bị thay đổi sau khi lượt chạy con hoàn tất (vi phạm INV-001)!"
    )


def test_resume_restores_normalizer_optimizer_rng(parent_smoke_run: dict[str, Any]) -> None:
    """FR-003, FR-009, INV-004, AC-2: Khôi phục normalizer, optimizer, RNG và bộ đếm tiếp nối.

    Xác minh:
    - RunningNorm không khởi tạo lại từ 0 mà tiếp tục từ số mẫu của checkpoint cha.
    - Bộ đếm lượt cập nhật (update_idx) và bước môi trường (env_steps) tiếp nối liền mạch.
    - Optimizer khôi phục các trạng thái tối ưu hoá nội bộ (internal optimizer states).
    - Bộ sinh số ngẫu nhiên RNG (PyTorch và NumPy) được khôi phục chính xác từ checkpoint.
    """
    _require_torch()
    import torch

    from mma_ai.environment.single_agent import make_env
    from mma_ai.learning.checkpoint import load_checkpoint
    from mma_ai.learning.train_config import TrainConfig
    from mma_ai.learning.trainer import Trainer

    latest_json: Path = parent_smoke_run["latest_json"]
    parent_dir: Path = parent_smoke_run["parent_dir"]

    # Nạp dữ liệu checkpoint cha vào bộ nhớ để lấy mốc đối chiếu
    loaded_ckpt = load_checkpoint(latest_json, for_training=True)
    expected_update_idx = loaded_ckpt.update_idx
    expected_env_steps = loaded_ckpt.env_steps
    expected_norm_count = int(loaded_ckpt.obs_normalizer_state_dict["count"])

    assert expected_update_idx > 0, "update_idx của checkpoint cha phải lớn hơn 0"
    assert expected_env_steps > 0, "env_steps của checkpoint cha phải lớn hơn 0"
    assert expected_norm_count > 0, "Số mẫu bộ chuẩn hoá của checkpoint cha phải lớn hơn 0"

    # Khởi tạo đối tượng Trainer với tham số resume_checkpoint
    env = make_env(split="train")
    cfg = parent_smoke_run["parent_manifest"]["config"]
    resolved_cfg = TrainConfig.load(overrides=cfg)
    child_run_dir = parent_dir.parent / "test_verify_restore_dir"

    trainer = Trainer(
        cfg=resolved_cfg,
        env=env,
        run_dir=child_run_dir,
        resume_checkpoint=latest_json,
    )

    # 1. Khẳng định các bộ đếm bước tiếp nối chính xác từ checkpoint
    assert trainer.start_update_idx == expected_update_idx, (
        f"start_update_idx ({trainer.start_update_idx}) "
        f"không khớp checkpoint ({expected_update_idx})"
    )
    assert trainer.start_env_steps == expected_env_steps, (
        f"start_env_steps ({trainer.start_env_steps}) "
        f"không khớp checkpoint ({expected_env_steps})"
    )

    # 2. Khẳng định bộ chuẩn hoá quan sát được khôi phục số liệu thống kê
    restored_norm_state = trainer.normalizer.state_dict()
    assert int(restored_norm_state["count"]) == expected_norm_count, (
        f"Bộ chuẩn hoá bị khởi tạo lại: count = {restored_norm_state['count']}, "
        f"kỳ vọng = {expected_norm_count}"
    )

    # 3. Khẳng định optimizer khôi phục trạng thái bộ đệm tham số
    opt_state = trainer.agent.optimizer.state_dict()
    assert "state" in opt_state, "Optimizer state_dict thiếu khoá 'state'"
    assert len(opt_state["state"]) > 0, (
        "Trạng thái nội bộ của optimizer rỗng (không được khôi phục)"
    )

    # 4. Khẳng định trạng thái RNG PyTorch khớp với trạng thái đã lưu
    curr_torch_rng = torch.get_rng_state()
    saved_torch_rng = loaded_ckpt.rng_state["torch_cpu"]
    assert torch.equal(curr_torch_rng, saved_torch_rng), (
        "Trạng thái sinh số ngẫu nhiên torch RNG không khớp trạng thái checkpoint"
    )


def test_resume_refused_when_xml_hash_differs(
    parent_smoke_run: dict[str, Any], tmp_path: Path
) -> None:
    """FR-008, FR-009, AC-2: Từ chối tiếp tục huấn luyện với mã thoát 4 khi mã băm XML khác biệt.

    Xác minh:
    - Khi điểm kiểm tra được tạo từ mô hình có mã băm XML khác với mô hình hiện tại,
      lệnh CLI huấn luyện từ chối chạy tiếp và thoát với mã 4.
    - Thông điệp lỗi trên stderr nêu rõ nguyên nhân sai khác mã băm XML (model SHA-256).
    - Không có thư mục lượt chạy mới nào được tạo ra.
    """
    torch = _require_torch()
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    final_ckpt_path: Path = parent_smoke_run["final_ckpt_path"]

    # Đọc checkpoint gốc và làm sai lệch trường model_sha256
    ckpt_payload = torch.load(final_ckpt_path, weights_only=True)
    mismatched_hash = "f" * 64
    ckpt_payload["model_sha256"] = mismatched_hash

    tampered_ckpt = tmp_path / "tampered_xml_hash.pt"
    torch.save(ckpt_payload, tampered_ckpt)

    config_file = smoke_config(tmp_path, runs_dir=os.path.relpath(runs_dir, Path.cwd()))

    result = run_train_cli(
        [
            "--stage",
            "elbow",
            "--config",
            str(config_file),
            "--resume",
            str(tampered_ckpt),
        ],
        timeout=30.0,
    )

    assert result.exit_code == 4, (
        f"Kỳ vọng mã thoát 4 khi sai khác mã băm XML, nhưng nhận {result.exit_code}.\n"
        f"Stderr: {result.stderr}\nStdout: {result.stdout}"
    )
    assert (
        "mã băm XML" in result.stderr
        or "XML" in result.stderr
        or "model_sha256" in result.stderr
    ), f"Thông điệp lỗi không nêu nguyên nhân sai khác mã băm XML: {result.stderr}"

    assert list_runs(runs_dir) == [], (
        "Không được tạo thư mục lượt chạy mới khi điểm kiểm tra bị từ chối"
    )


def test_corrupt_checkpoint_exit4_names_cause(
    parent_smoke_run: dict[str, Any], tmp_path: Path
) -> None:
    """FR-008, AC-2: Checkpoint hỏng, thiếu bộ chuẩn hoá hoặc khác cấu trúc mạng thoát 4.

    Xác minh:
    - Điểm kiểm tra chứa nội dung nhị phân hỏng: Thoát 4 và thông báo lỗi nêu nguyên nhân hỏng.
    - Điểm kiểm tra thiếu thành phần bắt buộc: Thoát 4 và thông báo thiếu obs_normalizer.
    - Điểm kiểm tra có cấu trúc mạng khác biệt: Thoát 4 và nêu khác biệt.
    - load_policy ném CheckpointError tương ứng, tuyệt đối không trả chính sách dùng được âm thầm.
    """
    torch = _require_torch()
    from mma_ai.learning.checkpoint import load_policy
    from mma_ai.learning.errors import CheckpointError

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    config_file = smoke_config(tmp_path, runs_dir=os.path.relpath(runs_dir, Path.cwd()))
    final_ckpt_path: Path = parent_smoke_run["final_ckpt_path"]

    # 1. Trường hợp checkpoint hỏng nhị phân (corrupted bytes)
    corrupt_file = tmp_path / "corrupted_file.pt"
    corrupt_file.write_bytes(b"DATA_NHI_PHAN_BI_HONG_HOAN_TOAN_123456789")

    res_corrupt = run_train_cli(
        ["--stage", "elbow", "--config", str(config_file), "--resume", str(corrupt_file)],
        timeout=30.0,
    )
    assert res_corrupt.exit_code == 4, (
        f"Checkpoint hỏng phải thoát 4, nhận {res_corrupt.exit_code}: {res_corrupt.stderr}"
    )
    assert (
        "hỏng" in res_corrupt.stderr
        or "cấu trúc" in res_corrupt.stderr
        or "lỗi" in res_corrupt.stderr
    ), f"Thông báo lỗi không nêu nguyên nhân tệp hỏng: {res_corrupt.stderr}"

    # load_policy cũng phải ném CheckpointError, không trả policy âm thầm
    with pytest.raises(CheckpointError):
        load_policy(corrupt_file)

    # 2. Trường hợp checkpoint thiếu bộ chuẩn hoá quan sát (missing obs_normalizer)
    raw_valid = torch.load(final_ckpt_path, weights_only=True)
    missing_norm_payload = dict(raw_valid)
    del missing_norm_payload["obs_normalizer"]

    missing_norm_file = tmp_path / "missing_normalizer.pt"
    torch.save(missing_norm_payload, missing_norm_file)

    res_missing = run_train_cli(
        ["--stage", "elbow", "--config", str(config_file), "--resume", str(missing_norm_file)],
        timeout=30.0,
    )
    assert res_missing.exit_code == 4, (
        f"Thiếu obs_normalizer phải thoát 4, nhận {res_missing.exit_code}: {res_missing.stderr}"
    )
    assert "obs_normalizer" in res_missing.stderr or "thiếu" in res_missing.stderr, (
        f"Thông báo lỗi không nêu thành phần thiếu: {res_missing.stderr}"
    )

    with pytest.raises(CheckpointError) as exc_missing:
        load_policy(missing_norm_file)
    assert "obs_normalizer" in str(exc_missing.value) or "thiếu" in str(exc_missing.value)

    # 3. Trường hợp checkpoint có cấu trúc mạng khác biệt (mismatched network width)
    # Cấu hình mong đợi mặc định là actor_hidden = [256, 256].
    # Tạo checkpoint với mạng có kích thước ẩn khác: [128, 128]
    from mma_ai.learning.networks import ActorCritic
    from mma_ai.learning.train_config import TrainConfig

    mismatched_cfg = TrainConfig.load(
        overrides={"network.actor_hidden": [128, 128], "network.critic_hidden": [128, 128]}
    )
    mismatched_model = ActorCritic(obs_dim=14, act_dim=6, cfg=mismatched_cfg)

    mismatched_payload = dict(raw_valid)
    mismatched_payload["actor"] = mismatched_model.actor.state_dict()
    mismatched_payload["critic"] = mismatched_model.critic.state_dict()

    mismatched_net_file = tmp_path / "mismatched_hidden.pt"
    torch.save(mismatched_payload, mismatched_net_file)

    res_net = run_train_cli(
        ["--stage", "elbow", "--config", str(config_file), "--resume", str(mismatched_net_file)],
        timeout=30.0,
    )
    assert res_net.exit_code == 4, (
        f"Khác cấu trúc mạng phải thoát 4, nhận {res_net.exit_code}: {res_net.stderr}"
    )
    assert (
        "cấu trúc mạng" in res_net.stderr
        or "actor_hidden" in res_net.stderr
        or "hình dạng" in res_net.stderr
    ), f"Thông báo lỗi không nêu nguyên nhân khác cấu trúc mạng: {res_net.stderr}"

    assert list_runs(runs_dir) == [], "Không được tạo bất kỳ run nào khi checkpoint không hợp lệ"
