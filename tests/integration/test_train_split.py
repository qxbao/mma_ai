"""Kiểm thử tích hợp chỉ dùng tập huấn luyện train split (T324).

Hiện thực và xác minh:
- FR-016, AC-1, US1: Huấn luyện MUST lấy mục tiêu chỉ từ tập train của môi trường
  (con 1) và MUST NOT dùng tập test.
- INV-003, AC-1: Bất biến phân tách mục tiêu — huấn luyện chỉ dùng mục tiêu thuộc
  tập train; tập test không bao giờ xuất hiện trong lúc train (bảo vệ đánh giá con 3).
"""

from __future__ import annotations

import importlib.resources
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from train_fixtures import list_runs, run_train_cli, smoke_config

from mma_ai.environment.single_agent import ElbowReachEnv
from mma_ai.learning.cli import _build_parser
from mma_ai.learning.errors import TrainConfigError, TrainError
from mma_ai.learning.train_config import TrainConfig


def test_split_contract_independent_assertion() -> None:
    """FR-016, INV-003, AC-1, US1: Khẳng định độc lập trên base về phân tách mục tiêu huấn luyện.

    Đảm bảo kiểm thử không bị bỏ qua toàn bộ khi thiếu phụ thuộc tuỳ chọn (optional dependency).
    Xác minh bộ phân tích cú pháp CLI và cấu hình huấn luyện không có cơ chế chọn tập test.
    """
    # 1. Xác minh bộ phân tích cú pháp CLI tuyệt đối không có cờ chọn tập dữ liệu (split)
    parser = _build_parser()
    actions = {action.dest for action in parser._actions}
    for dest in actions:
        assert "split" not in dest.lower(), (
            f"Phát hiện cờ dòng lệnh '{dest}' liên quan đến split vi phạm bất biến INV-003"
        )

    # 2. Xác minh cấu hình TrainConfig từ chối mọi trường split qua ghi đè (overrides)
    with pytest.raises(TrainConfigError, match="Khoá ghi đè 'split' không tồn tại"):
        TrainConfig.load(overrides={"split": "test"})

    with pytest.raises(TrainConfigError, match="Khoá ghi đè 'schedule.split' không tồn tại"):
        TrainConfig.load(overrides={"schedule.split": "test"})

    # 3. Xác minh môi trường huấn luyện con 1 phân tách độc lập giữa tập train và test
    env_train = ElbowReachEnv(split="train")
    assert env_train.split == "train", "Môi trường huấn luyện phải có vai trò split='train'"
    assert len(env_train.targets.train.targets) > 0, "Tập mục tiêu train không được rỗng"
    assert len(env_train.targets.test.targets) > 0, "Tập mục tiêu test không được rỗng"

    train_positions = {
        (round(t.position_m[0], 6), round(t.position_m[1], 6), round(t.position_m[2], 6))
        for t in env_train.targets.train.targets
    }
    test_positions = {
        (round(t.position_m[0], 6), round(t.position_m[1], 6), round(t.position_m[2], 6))
        for t in env_train.targets.test.targets
    }
    assert train_positions.isdisjoint(test_positions), (
        "Tập mục tiêu train và test phải hoàn toàn rời nhau (INV-001 của con 1)"
    )


def test_config_cannot_select_test_split(tmp_path: Path) -> None:
    """FR-016, INV-003, AC-1, US1: Cấu hình hay cờ đặt split khác train bị từ chối hoặc bỏ qua.

    Xác minh không có cờ dòng lệnh hay cấu hình nào đưa được tập test vào lúc huấn luyện.
    """
    runs_dir = tmp_path / "runs"

    # 1. Thử truyền cờ lạ --split test vào CLI: bộ phân tích cú pháp phải từ chối với mã khác 0
    cli_res_flag = run_train_cli(["--stage", "elbow", "--split", "test"], timeout=30.0)
    assert cli_res_flag.exit_code != 0, (
        f"Kỳ vọng CLI từ chối cờ --split lạ, nhưng nhận mã {cli_res_flag.exit_code}"
    )
    assert (
        "unrecognized arguments" in cli_res_flag.stderr
        or "--split" in cli_res_flag.stderr
    ), f"Thông điệp lỗi phải nêu cờ không hợp lệ: {cli_res_flag.stderr}"
    assert list_runs(runs_dir) == [], "Không được tạo thư mục run khi cờ dòng lệnh sai"

    # 2. Thử truyền tệp YAML chứa khoá lạ split='test' ở gốc cấu hình
    bad_root_yaml = tmp_path / "bad_root_split.yaml"
    resource = importlib.resources.files("mma_ai.learning").joinpath("train_elbow_smoke.yaml")
    raw_cfg_root: dict[str, Any] = yaml.safe_load(resource.read_text(encoding="utf-8"))
    raw_cfg_root["split"] = "test"
    bad_root_yaml.write_text(yaml.safe_dump(raw_cfg_root), encoding="utf-8")

    cli_res_cfg = run_train_cli(
        ["--stage", "elbow", "--config", str(bad_root_yaml)],
        timeout=30.0,
    )
    assert cli_res_cfg.exit_code == 2, (
        f"Kỳ vọng mã thoát 2 khi cấu hình chứa khoá thừa, nhận {cli_res_cfg.exit_code}"
    )
    assert (
        "split" in cli_res_cfg.stderr or "Cấu hình" in cli_res_cfg.stderr
    ), f"Thông báo lỗi phải chỉ ra khoá không hợp lệ: {cli_res_cfg.stderr}"
    assert list_runs(runs_dir) == [], "Không được tạo thư mục run khi cấu hình YAML không hợp lệ"

    # 3. Thử truyền tệp YAML chứa khoá lạ ppo.split='test'
    bad_sub_yaml = tmp_path / "bad_sub_split.yaml"
    raw_cfg_sub: dict[str, Any] = yaml.safe_load(resource.read_text(encoding="utf-8"))
    raw_cfg_sub["ppo"]["split"] = "test"
    bad_sub_yaml.write_text(yaml.safe_dump(raw_cfg_sub), encoding="utf-8")

    cli_res_sub = run_train_cli(
        ["--stage", "elbow", "--config", str(bad_sub_yaml)],
        timeout=30.0,
    )
    assert cli_res_sub.exit_code == 2, (
        f"Kỳ vọng mã thoát 2 khi nhóm con chứa khoá thừa, nhận {cli_res_sub.exit_code}"
    )
    assert list_runs(runs_dir) == [], "Không được tạo thư mục run khi cấu hình con sai"

    # 4. Khi có phụ thuộc torch: xác nhận Trainer từ chối ngay lập tức môi trường test
    try:
        import torch  # noqa: F401
    except ImportError:
        return

    from mma_ai.learning.trainer import Trainer

    env_test = ElbowReachEnv(split="test")
    valid_cfg = TrainConfig.load()
    with pytest.raises(TrainError, match="Trainer chỉ chấp nhận môi trường với split='train'"):
        Trainer(cfg=valid_cfg, env=env_test, run_dir=tmp_path / "dummy_run")


def test_training_only_uses_train_split(tmp_path: Path) -> None:
    """FR-016, INV-003, AC-1, US1: Qua một lượt train ngắn thật, mọi reset chỉ dùng tập train.

    Khởi chạy một lượt huấn luyện ngắn trên môi trường mô phỏng thật, hook bắt toàn bộ các lần
    gọi reset() và xác minh mọi mục tiêu được cấp phát đều thuộc tập train của con 1.
    """
    pytest.importorskip("torch", reason="Cần extra rl (torch) để thực thi huấn luyện PPO")

    # Tạo cấu hình huấn luyện ngắn (smoke) trong thư mục tạm
    config_file = smoke_config(
        tmp_path,
        total_timesteps=512,
        n_steps=256,
        batch_size=128,
        mode="none",
    )
    runs_dir = tmp_path / "runs"
    resets_log_file = tmp_path / "recorded_resets.json"

    # Đoạn mã thực thi qua tiến trình con với hook ghi nhận thông tin đặt lại môi trường
    escaped_resets = str(resets_log_file)
    escaped_config = str(config_file)
    runner_script = (
        "import sys\n"
        "import json\n"
        "from pathlib import Path\n"
        "import mma_ai.environment.single_agent as sa\n"
        "import mma_ai.learning.cli as cli_mod\n"
        f"resets_path = Path({escaped_resets!r})\n"
        "recorded_resets = []\n"
        "orig_reset = sa.ElbowReachEnv.reset\n"
        "def hooked_reset(self, *args, **kwargs):\n"
        "    obs, info = orig_reset(self, *args, **kwargs)\n"
        "    recorded_resets.append({\n"
        "        'target_split': str(info.get('target_split')),\n"
        "        'target_index': int(info.get('target_index')),\n"
        "        'target_position_m': "
        "[float(coord) for coord in info.get('target_position_m', [])],\n"
        "        'initial_distance_m': float(info.get('initial_distance_m', 0.0)),\n"
        "        'seed': int(info.get('seed', -1)),\n"
        "    })\n"
        "    return obs, info\n"
        "sa.ElbowReachEnv.reset = hooked_reset\n"
        "exit_code = 1\n"
        "try:\n"
        f"    exit_code = cli_mod.main(['--stage', 'elbow', '--seed', '42', "
        f"'--config', {escaped_config!r}])\n"
        "finally:\n"
        "    resets_path.write_text(json.dumps(recorded_resets), encoding='utf-8')\n"
        "sys.exit(exit_code)\n"
    )

    clean_env = os.environ.copy()
    clean_env.pop("DISPLAY", None)
    clean_env.pop("WAYLAND_DISPLAY", None)

    proc = subprocess.run(
        [sys.executable, "-c", runner_script],
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=120.0,
        cwd=str(Path.cwd()),
        check=False,
    )

    assert proc.returncode == 0, (
        f"Tiến trình huấn luyện thất bại với mã {proc.returncode}.\n"
        f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    )
    assert resets_log_file.is_file(), "Không tìm thấy tệp ghi nhận lượt reset"
    assert len(list_runs(runs_dir)) >= 1, "Thư mục lượt chạy không được tạo thành công"

    recorded_resets: list[dict[str, Any]] = json.loads(resets_log_file.read_text(encoding="utf-8"))
    assert len(recorded_resets) > 0, "Phải có ít nhất một lượt reset trong quá trình huấn luyện"

    # Môi trường tham chiếu để đối chiếu danh sách và toạ độ mục tiêu tập train và test
    ref_env = ElbowReachEnv(split="train")
    train_targets = ref_env.targets.train.targets
    test_targets = ref_env.targets.test.targets

    train_positions = {
        (round(t.position_m[0], 6), round(t.position_m[1], 6), round(t.position_m[2], 6))
        for t in train_targets
    }
    test_positions = {
        (round(t.position_m[0], 6), round(t.position_m[1], 6), round(t.position_m[2], 6))
        for t in test_targets
    }

    # Kiểm tra tính hợp lệ của mọi lượt reset trong quá trình huấn luyện
    for idx, reset_info in enumerate(recorded_resets):
        # 1. Bất biến INV-003, FR-016: target_split bắt buộc phải là 'train'
        split_val = reset_info["target_split"]
        assert split_val == "train", (
            f"Lượt reset #{idx} vi phạm INV-003: target_split='{split_val}', kỳ vọng 'train'"
        )

        # 2. target_index phải thuộc phạm vi chỉ mục hợp lệ của tập train
        target_idx = reset_info["target_index"]
        assert 0 <= target_idx < len(train_targets), (
            f"Lượt reset #{idx} có target_index={target_idx} nằm ngoài tập train "
            f"[0, {len(train_targets) - 1}]"
        )

        # 3. Toạ độ mục tiêu phải thuộc tập vị trí của train_positions
        actual_pos = tuple(round(coord, 6) for coord in reset_info["target_position_m"])
        assert actual_pos in train_positions, (
            f"Lượt reset #{idx} có toạ độ {actual_pos} không thuộc tập mục tiêu huấn luyện train"
        )

        # 4. Toạ độ mục tiêu tuyệt đối không được thuộc tập vị trí kiểm thử test_positions
        assert actual_pos not in test_positions, (
            f"Lượt reset #{idx} có toạ độ {actual_pos} thuộc tập kiểm thử (test) — vi phạm INV-003"
        )

        # 5. Đối chiếu khớp chính xác với phần tử mục tiêu thứ target_idx trong tập train của con 1
        expected_target_pos = tuple(round(c, 6) for c in train_targets[target_idx].position_m)
        assert actual_pos == expected_target_pos, (
            f"Lượt reset #{idx} có toạ độ {actual_pos} không khớp "
            f"với mục tiêu chỉ mục {target_idx} ({expected_target_pos})"
        )
