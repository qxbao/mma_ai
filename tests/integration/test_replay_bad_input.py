"""Kiểm thử tích hợp cho các trường hợp đầu vào không hợp lệ và xử lý lỗi dòng lệnh.

Truy vết các yêu cầu kỹ thuật và tiêu chí chấp nhận (acceptance criteria):
- 005 AC-5: Đầu vào sai (thiếu/thừa cờ, tệp hỏng, không hữu hạn) thoát mã phù hợp.
- FR-008: Ghi episode nguyên tử, từ chối ghi đè tệp đã tồn tại (mã 8), dọn dẹp tệp tạm khi ngắt.
- FR-009: Kiểm tra cấu trúc theo luật R1–R7; từ chối JSON cụt, thiếu trường (mã 5).
- FR-012: Kiểm tra đối chiếu mã băm XML của checkpoint và từ chối khi không khớp (mã 4).
- FR-013: Báo lỗi mã 2, 4, 5 khi tham số dòng lệnh, checkpoint hoặc episode không dùng được.
- FR-016: Xác thực phạm vi chỉ số mục tiêu (--target-index) trong tập train/test (mã 2).
- FR-018: Thông báo lỗi bằng tiếng Việt có dấu, nêu rõ giá trị và ngữ cảnh cụ thể trên stderr.
- INV-001: Ngăn chặn phát lại sai ngầm, kiểm tra tính toàn vẹn mô hình trước khi mở cửa sổ.
- INV-004: Xử lý ngoại lệ chuẩn, dọn dẹp tài nguyên và trả mã 130 khi bị ngắt bởi người dùng.
- INV-005: Hoạt động chỉ đọc đối với tệp nguồn, không ghi đè tệp đích có sẵn.
- NFR-REL-001: Độ tin cậy số học, từ chối mọi giá trị không hữu hạn (NaN/Inf).
- CMD-VIS-0001: Hợp đồng mã thoát dòng lệnh: 2 (tham số), 4 (checkpoint), 5 (episode), 8, 130.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from mma_ai.physics.body_model import load_muscle_model
from mma_ai.visualization.episode import (
    Episode,
    Frame,
    ModelRecord,
    OutcomeRecord,
    TargetRecord,
    TimingRecord,
    write_episode,
)


def _get_clean_env() -> dict[str, str]:
    """Tạo bản sao biến môi trường đã loại bỏ DISPLAY và WAYLAND_DISPLAY."""
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    return env


def _create_minimal_valid_episode(file_path: Path) -> Path:
    """Tạo tệp episode JSON hợp lệ tối thiểu phục vụ kiểm thử tham số."""
    model_info = load_muscle_model("myoelbow").info
    names = list(model_info.muscle_names)
    model_sha = model_info.sha256

    frames = [
        Frame(
            t_s=0.0,
            qpos=[0.0],
            qvel=[0.0],
            activation=[0.1] * 6,
            excitation=None,
            fingertip_position_m=(-0.21, -0.106, 1.12),
            distance_m=0.15,
            reward=0.0,
        ),
        Frame(
            t_s=0.04,
            qpos=[0.2],
            qvel=[0.05],
            activation=[0.2] * 6,
            excitation=[0.2] * 6,
            fingertip_position_m=(-0.20, -0.105, 1.13),
            distance_m=0.05,
            reward=0.8,
        ),
    ]

    episode = Episode(
        schema_version="1.0.0",
        created_utc="2026-10-10T12:00:00Z",
        seed=42,
        model=ModelRecord(
            sha256=model_sha,
            source="myo_sim/elbow/myoelbow_1dof6muscles.xml",
            muscle_names=names,
            nq=1,
            nv=1,
        ),
        target=TargetRecord(
            position_m=(-0.19, -0.10, 1.16),
            split="test",
            index=0,
            tolerance_m=0.05,
        ),
        timing=TimingRecord(action_dt_s=0.04, physics_timestep_s=0.002),
        outcome=OutcomeRecord(
            terminated=True,
            truncated=False,
            end_reason="reached",
            reached=True,
            n_actions=1,
            final_distance_m=0.05,
        ),
        library_versions={"mujoco": "3.15.0", "numpy": "1.26.0"},
        frames=frames,
        source=None,
    )

    write_episode(episode, file_path)
    return file_path


def test_missing_episode_exit5(tmp_path: Path) -> None:
    """005 AC-5, FR-013, CMD-VIS-0001: Tệp episode không tồn tại thoát mã 5 và nêu tên tệp."""
    missing_file = tmp_path / "khong_ton_tai_123.json"
    clean_env = _get_clean_env()

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(missing_file),
            "--headless",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )

    assert proc.returncode == 5, (
        f"Kỳ vọng mã thoát 5 khi thiếu tệp episode nhưng nhận {proc.returncode}.\n"
        f"Stderr: {proc.stderr}"
    )
    assert str(missing_file) in proc.stderr
    assert "không tìm thấy" in proc.stderr.lower() or "không tồn tại" in proc.stderr.lower()


def test_missing_checkpoint_exit4_no_viewer_no_file(tmp_path: Path) -> None:
    """005 AC-5, FR-013, CMD-VIS-0001: Checkpoint không tồn tại thoát mã 4, không ghi tệp."""
    missing_ckpt = tmp_path / "khong_ton_tai_checkpoint.pt"
    out_file = tmp_path / "khong_duoc_tao.json"
    clean_env = _get_clean_env()

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--checkpoint",
            str(missing_ckpt),
            "--save-episode",
            str(out_file),
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )

    assert proc.returncode == 4, (
        f"Kỳ vọng mã thoát 4 khi thiếu tệp checkpoint nhưng nhận {proc.returncode}.\n"
        f"Stderr: {proc.stderr}"
    )
    assert str(missing_ckpt) in proc.stderr
    assert "không tồn tại" in proc.stderr.lower()
    # Khẳng định tệp đích không hề được tạo ra
    assert not out_file.exists(), "Tệp episode không được phép sinh ra khi checkpoint lỗi"


def test_corrupt_json_exit5_names_field(tmp_path: Path) -> None:
    """005 AC-5, FR-009, FR-013: JSON hỏng cú pháp hoặc thiếu trường thoát mã 5."""
    clean_env = _get_clean_env()

    # Ca 1: JSON hỏng cú pháp
    corrupt_syntax = tmp_path / "syntax_error.json"
    corrupt_syntax.write_text("{invalid_json_content: 123", encoding="utf-8")

    proc1 = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(corrupt_syntax),
            "--headless",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )

    assert proc1.returncode == 5
    assert "không hợp lệ" in proc1.stderr.lower() or "lỗi" in proc1.stderr.lower()

    # Ca 2: JSON hợp lệ nhưng thiếu trường bắt buộc cấp cao 'model'
    missing_field_file = tmp_path / "missing_model_field.json"
    missing_field_file.write_text(
        '{"schema_version": "1.0.0", "created_utc": "2026-10-10T12:00:00Z", "seed": 42}',
        encoding="utf-8",
    )

    proc2 = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(missing_field_file),
            "--headless",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )

    assert proc2.returncode == 5
    assert "model" in proc2.stderr.lower() or "thiếu trường" in proc2.stderr.lower()


def test_nonfinite_values_exit5(tmp_path: Path) -> None:
    """005 AC-5, FR-009, NFR-REL-001: Giá trị số không hữu hạn bị từ chối với mã 5 (R7)."""
    clean_env = _get_clean_env()

    # Ca 1: Tệp JSON chứa giá trị NaN
    nan_file = tmp_path / "nan_value.json"
    nan_file.write_text(
        '{"schema_version": "1.0.0", "seed": NaN, "model": {}}',
        encoding="utf-8",
    )

    proc1 = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(nan_file),
            "--headless",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )

    assert proc1.returncode == 5
    assert "hữu hạn" in proc1.stderr.lower() or "không hợp lệ" in proc1.stderr.lower()

    # Ca 2: Tệp JSON chứa giá trị Infinity
    inf_file = tmp_path / "inf_value.json"
    inf_file.write_text(
        '{"schema_version": "1.0.0", "seed": Infinity, "model": {}}',
        encoding="utf-8",
    )

    proc2 = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(inf_file),
            "--headless",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )

    assert proc2.returncode == 5
    assert "hữu hạn" in proc2.stderr.lower() or "không hợp lệ" in proc2.stderr.lower()


def test_both_or_neither_mode_exit2() -> None:
    """005 AC-5, CMD-VIS-0001: Thiếu cả hai hoặc dùng đồng thời cả hai chế độ thoát mã 2."""
    clean_env = _get_clean_env()

    # Ca 1: Không truyền chế độ nào
    proc_none = subprocess.run(
        [sys.executable, "-m", "mma_ai.visualization.cli"],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )
    assert proc_none.returncode == 2
    err_none = proc_none.stderr.lower()
    assert "chỉ định đúng một trong hai" in err_none or "lỗi tham số" in err_none

    # Ca 2: Truyền đồng thời cả hai chế độ
    proc_both = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            "ep.json",
            "--checkpoint",
            "ckpt.pt",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )
    assert proc_both.returncode == 2
    err_both = proc_both.stderr.lower()
    assert "đồng thời" in err_both or "lỗi tham số" in err_both


def test_target_index_out_of_range_exit2(tmp_path: Path) -> None:
    """005 AC-5, FR-016, CMD-VIS-0001: Chỉ số mục tiêu âm hoặc ngoài biên thoát mã 2."""
    clean_env = _get_clean_env()
    ep_file = _create_minimal_valid_episode(tmp_path / "valid_ep.json")

    # Ca 1: Dùng --target-index với --episode
    proc_wrong_mode = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(ep_file),
            "--target-index",
            "1",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )
    assert proc_wrong_mode.returncode == 2
    assert "target-index" in proc_wrong_mode.stderr.lower()

    # Ca 2: Dùng --target-index âm với --checkpoint
    proc_neg = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--checkpoint",
            "dummy.pt",
            "--target-index",
            "-5",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )
    assert proc_neg.returncode == 2
    assert "không được âm" in proc_neg.stderr.lower() or "target-index" in proc_neg.stderr.lower()

    # Ca 3: Dùng --target-index vượt quá số lượng mục tiêu trong split (ví dụ 9999)
    dummy_ckpt = tmp_path / "valid_dummy.pt"
    dummy_ckpt.touch()

    model_sha = load_muscle_model("myoelbow").info.sha256
    script_out_of_range = (
        "import sys, types\n"
        "from pathlib import Path\n"
        f"dummy_ckpt = types.SimpleNamespace(model_sha256={model_sha!r})\n"
        "class DummyPolicy:\n"
        "    def act_deterministic(self, obs):\n"
        "        return [0.1] * 6\n"
        "ckpt_mod = types.ModuleType('mma_ai.learning.checkpoint')\n"
        "ckpt_mod.load_checkpoint = lambda p, **kw: dummy_ckpt\n"
        "ckpt_mod.load_policy = lambda p, **kw: DummyPolicy()\n"
        "errors_mod = types.ModuleType('mma_ai.learning.errors')\n"
        "errors_mod.CheckpointError = type('CheckpointError', (Exception,), {})\n"
        "sys.modules['mma_ai.learning.checkpoint'] = ckpt_mod\n"
        "sys.modules['mma_ai.learning.errors'] = errors_mod\n"
        "from mma_ai.visualization.cli import main\n"
        f"ckpt_str = {str(dummy_ckpt)!r}\n"
        "sys.exit(main(['--checkpoint', ckpt_str, '--target-index', '9999', '--headless']))\n"
    )

    proc_out_range = subprocess.run(
        [sys.executable, "-c", script_out_of_range],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )

    assert proc_out_range.returncode == 2
    assert "vượt quá phạm vi" in proc_out_range.stderr.lower()
    assert "9999" in proc_out_range.stderr


def test_existing_save_path_exit8_not_overwritten(tmp_path: Path) -> None:
    """005 AC-5, FR-008, INV-005, CMD-VIS-0001: Đường dẫn đã tồn tại thoát mã 8, không ghi đè."""
    clean_env = _get_clean_env()
    dummy_ckpt = tmp_path / "valid_dummy.pt"
    dummy_ckpt.touch()

    existing_file = tmp_path / "already_exists.json"
    original_bytes = b"NOI_DUNG_BAN_DAU_BAT_BIEN_INV_005"
    existing_file.write_bytes(original_bytes)

    model_sha = load_muscle_model("myoelbow").info.sha256
    script_existing_save = (
        "import sys, types\n"
        "from pathlib import Path\n"
        f"dummy_ckpt = types.SimpleNamespace(model_sha256={model_sha!r})\n"
        "class DummyPolicy:\n"
        "    def act_deterministic(self, obs):\n"
        "        return [0.1] * 6\n"
        "ckpt_mod = types.ModuleType('mma_ai.learning.checkpoint')\n"
        "ckpt_mod.load_checkpoint = lambda p, **kw: dummy_ckpt\n"
        "ckpt_mod.load_policy = lambda p, **kw: DummyPolicy()\n"
        "errors_mod = types.ModuleType('mma_ai.learning.errors')\n"
        "errors_mod.CheckpointError = type('CheckpointError', (Exception,), {})\n"
        "sys.modules['mma_ai.learning.checkpoint'] = ckpt_mod\n"
        "sys.modules['mma_ai.learning.errors'] = errors_mod\n"
        "from mma_ai.visualization.cli import main\n"
        f"ckpt_str = {str(dummy_ckpt)!r}\n"
        f"save_str = {str(existing_file)!r}\n"
        "args = ['--checkpoint', ckpt_str, '--save-episode', save_str, '--headless']\n"
        "sys.exit(main(args))\n"
    )

    proc = subprocess.run(
        [sys.executable, "-c", script_existing_save],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )

    # CMD-VIS-0001: Mã thoát 8 khi tệp đích đã tồn tại
    assert proc.returncode == 8, (
        f"Kỳ vọng mã thoát 8 nhưng nhận {proc.returncode}.\n"
        f"Stderr: {proc.stderr}"
    )
    assert "đã tồn tại" in proc.stderr.lower()
    assert "từ chối ghi đè" in proc.stderr.lower()

    # INV-005: Khẳng định tệp đích tuyệt đối không bị sửa đổi
    assert existing_file.read_bytes() == original_bytes, (
        "Bất biến INV-005 bị vi phạm: tệp đích đã bị ghi đè nội dung!"
    )


def test_checkpoint_xml_hash_mismatch_exit4(tmp_path: Path) -> None:
    """005 AC-5, FR-012, FR-016: Checkpoint chứa mã băm XML không khớp mô hình thoát mã 4."""
    clean_env = _get_clean_env()
    dummy_ckpt = tmp_path / "mismatch_ckpt.pt"
    dummy_ckpt.touch()

    mismatch_sha = "0" * 64
    script_mismatch = (
        "import sys, types\n"
        "from pathlib import Path\n"
        f"dummy_ckpt = types.SimpleNamespace(model_sha256={mismatch_sha!r})\n"
        "class DummyPolicy:\n"
        "    def act_deterministic(self, obs):\n"
        "        return [0.1] * 6\n"
        "ckpt_mod = types.ModuleType('mma_ai.learning.checkpoint')\n"
        "ckpt_mod.load_checkpoint = lambda p, **kw: dummy_ckpt\n"
        "ckpt_mod.load_policy = lambda p, **kw: DummyPolicy()\n"
        "errors_mod = types.ModuleType('mma_ai.learning.errors')\n"
        "errors_mod.CheckpointError = type('CheckpointError', (Exception,), {})\n"
        "sys.modules['mma_ai.learning.checkpoint'] = ckpt_mod\n"
        "sys.modules['mma_ai.learning.errors'] = errors_mod\n"
        "from mma_ai.visualization.cli import main\n"
        f"ckpt_str = {str(dummy_ckpt)!r}\n"
        "sys.exit(main(['--checkpoint', ckpt_str, '--headless']))\n"
    )

    proc = subprocess.run(
        [sys.executable, "-c", script_mismatch],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )

    assert proc.returncode == 4, (
        f"Kỳ vọng mã thoát 4 khi hash XML của checkpoint không khớp nhưng nhận {proc.returncode}.\n"
        f"Stderr: {proc.stderr}"
    )
    assert mismatch_sha in proc.stderr
    assert "mã băm xml" in proc.stderr.lower() or "không tương thích" in proc.stderr.lower()


def test_interrupt_leaves_no_partial_episode(tmp_path: Path) -> None:
    """005 AC-5, FR-008, INV-004: Ngắt bằng tín hiệu thoát mã 130 và dọn dẹp sạch tệp tạm."""
    clean_env = _get_clean_env()
    dummy_ckpt = tmp_path / "dummy_for_interrupt.pt"
    dummy_ckpt.touch()

    target_file = tmp_path / "interrupted_episode.json"
    tmp_file = tmp_path / "interrupted_episode.json.tmp"

    model_sha = load_muscle_model("myoelbow").info.sha256
    script_interrupt = (
        "import sys, types\n"
        "from pathlib import Path\n"
        f"dummy_ckpt = types.SimpleNamespace(model_sha256={model_sha!r})\n"
        "class DummyPolicy:\n"
        "    def act_deterministic(self, obs):\n"
        "        return [0.1] * 6\n"
        "ckpt_mod = types.ModuleType('mma_ai.learning.checkpoint')\n"
        "ckpt_mod.load_checkpoint = lambda p, **kw: dummy_ckpt\n"
        "ckpt_mod.load_policy = lambda p, **kw: DummyPolicy()\n"
        "errors_mod = types.ModuleType('mma_ai.learning.errors')\n"
        "errors_mod.CheckpointError = type('CheckpointError', (Exception,), {})\n"
        "sys.modules['mma_ai.learning.checkpoint'] = ckpt_mod\n"
        "sys.modules['mma_ai.learning.errors'] = errors_mod\n"
        "import mma_ai.visualization.episode as ep_mod\n"
        f"tmp_candidate = Path({str(tmp_file)!r})\n"
        "def interrupt_write(ep, path):\n"
        "    tmp_candidate.touch()\n"
        "    raise KeyboardInterrupt('Giả lập tín hiệu ngắt Ctrl-C')\n"
        "ep_mod.write_episode = interrupt_write\n"
        "from mma_ai.visualization.cli import main\n"
        f"ckpt_str = {str(dummy_ckpt)!r}\n"
        f"save_str = {str(target_file)!r}\n"
        "args = ['--checkpoint', ckpt_str, '--save-episode', save_str, '--headless']\n"
        "sys.exit(main(args))\n"
    )

    proc = subprocess.run(
        [sys.executable, "-c", script_interrupt],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )

    # INV-004: Mã thoát khi bị ngắt là 130
    assert proc.returncode == 130, (
        f"Kỳ vọng mã thoát 130 khi bị ngắt Ctrl-C nhưng nhận {proc.returncode}.\n"
        f"Stderr: {proc.stderr}"
    )
    assert "ctrl-c" in proc.stderr.lower() or "ngắt" in proc.stderr.lower()

    # Khẳng định tệp tạm .tmp đã bị dọn dẹp và tệp đích không tồn tại
    assert not tmp_file.exists(), "Tệp tạm .tmp chưa được dọn dẹp sau khi bị ngắt"
    assert not target_file.exists(), "Tệp đích không được phép xuất hiện khi bị ngắt dở dang"


def test_errors_are_vietnamese_with_context(tmp_path: Path) -> None:
    """005 AC-5, FR-018: Thông báo lỗi tiếng Việt, kèm ngữ cảnh cụ thể, không lộ traceback."""
    clean_env = _get_clean_env()

    # 1. Kiểm tra lỗi hệ số tốc độ âm
    proc_speed = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            "dummy.json",
            "--speed",
            "-2.5",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )
    assert proc_speed.returncode == 2
    assert "-2.5" in proc_speed.stderr
    assert "hệ số tốc độ" in proc_speed.stderr.lower()
    # Không để lộ traceback thô chưa được bắt
    assert "Traceback (most recent call last)" not in proc_speed.stderr

    # 2. Kiểm tra lỗi dùng sai cờ --split với --episode
    ep_file = _create_minimal_valid_episode(tmp_path / "valid_for_flags.json")
    proc_flag = subprocess.run(
        [
            sys.executable,
            "-m",
            "mma_ai.visualization.cli",
            "--episode",
            str(ep_file),
            "--split",
            "train",
        ],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=15.0,
        check=False,
    )
    assert proc_flag.returncode == 2
    assert "--split" in proc_flag.stderr
    assert "chỉ áp dụng cho chế độ demo" in proc_flag.stderr.lower()
    assert "Traceback (most recent call last)" not in proc_flag.stderr
