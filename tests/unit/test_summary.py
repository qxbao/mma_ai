"""Kiểm thử đơn vị cho mô-đun tóm tắt phiên phát summary (tests/unit/test_summary.py).

Chứng minh các yêu cầu và bất biến kiến trúc:
- FR-010: Chế độ tóm tắt máy đọc được cho episode và demo theo replay-summary.schema.json.
- FR-018: Đường dẫn tương đối (relative path) và thông điệp tiếng Việt chuẩn mực.
- INV-006: Thống kê activation không làm tròn (unrounded activation statistics).
- NFR-REL-001: Độ tin cậy số học, từ chối mọi giá trị không hữu hạn (NaN, Infinity).
- API-VIS-0006: Giao diện hàm summarize_episode.
- AC-1, AC-2, AC-3, AC-4, AC-5: Các kịch bản chấp nhận liên quan đến tóm tắt phiên phát.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mma_ai.visualization.episode import (
    Episode,
    Frame,
    ModelRecord,
    OutcomeRecord,
    SourceRecord,
    TargetRecord,
    TimingRecord,
)
from mma_ai.visualization.errors import EpisodeInvalid
from mma_ai.visualization.model_check import ModelCheck
from mma_ai.visualization.pacing import PlaybackStats
from mma_ai.visualization.summary import summarize_episode

SAMPLE_XML_HASH_A = "a" * 64
SAMPLE_XML_HASH_B = "b" * 64
SAMPLE_CKPT_HASH = "c" * 64
SAMPLE_MUSCLES = ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"]


def _make_sample_episode(
    n_frames: int = 3,
    activations: list[list[float]] | None = None,
    distance_final: float = 0.015,
    reached: bool = True,
    end_reason: str = "reached",
    source_ckpt: bool = False,
) -> Episode:
    """Tạo đối tượng Episode mẫu phục vụ kiểm thử đơn vị."""
    model = ModelRecord(
        sha256=SAMPLE_XML_HASH_A,
        source="myo_sim/elbow/myoelbow_1dof6muscles.xml",
        muscle_names=list(SAMPLE_MUSCLES),
        nq=1,
        nv=1,
    )
    target = TargetRecord(
        position_m=(-0.21, -0.106, 1.12),
        split="test",
        index=0,
        tolerance_m=0.02,
    )
    source = (
        SourceRecord(
            checkpoint_path="runs/test/ckpt.pt",
            checkpoint_sha256=SAMPLE_CKPT_HASH,
            run_id="test",
            update_idx=10,
        )
        if source_ckpt
        else None
    )
    timing = TimingRecord(action_dt_s=0.04, physics_timestep_s=0.0025)
    outcome = OutcomeRecord(
        terminated=reached,
        truncated=not reached,
        end_reason=end_reason,
        reached=reached,
        n_actions=max(0, n_frames - 1),
        final_distance_m=distance_final,
    )

    frames: list[Frame] = []
    for k in range(n_frames):
        if activations is not None:
            act = list(activations[k])
        else:
            act = [0.05 * (k + 1)] * 6
        exc = [0.1] * 6 if k > 0 else None
        frames.append(
            Frame(
                t_s=k * 0.04,
                qpos=[0.1 * k],
                qvel=[0.0],
                activation=act,
                excitation=exc,
                fingertip_position_m=(-0.21, -0.106, 1.12),
                distance_m=distance_final,
                reward=1.0 if reached else -0.1,
            )
        )

    return Episode(
        schema_version="1.0.0",
        created_utc="2026-10-09T08:00:00Z",
        seed=12345,
        model=model,
        target=target,
        source=source,
        library_versions={"mujoco": "3.15.0", "numpy": "2.4.6", "python": "3.11.15"},
        timing=timing,
        outcome=outcome,
        frames=frames,
    )


def test_activation_stats_match_hand_values() -> None:
    """Kiểm tra thống kê activation tính tay khớp, không làm tròn (FR-010, INV-006, AC-3)."""
    # 4 khung hình với activation được ấn định chính xác cho 6 cơ
    raw_acts = [
        [0.100, 0.000, 0.250, 0.500, 0.050, 0.700],
        [0.200, 0.400, 0.150, 0.600, 0.150, 0.600],
        [0.050, 0.300, 0.050, 0.700, 0.250, 0.500],
        [0.450, 0.100, 0.350, 0.800, 0.350, 0.400],
    ]
    episode = _make_sample_episode(n_frames=4, activations=raw_acts)
    model_chk = ModelCheck(
        match=True,
        compatible=True,
        episode_sha256=SAMPLE_XML_HASH_A,
        current_sha256=SAMPLE_XML_HASH_A,
    )

    src_dict = {
        "episode_path": "replays/test.episode.json",
        "checkpoint_path": None,
        "checkpoint_sha256": None,
    }
    summary = summarize_episode(
        episode,
        model_chk,
        source=src_dict,
    )

    act_summary = summary["activation"]
    assert act_summary["muscle_names"] == SAMPLE_MUSCLES

    # Cơ 0 ("TRIlong"): [0.100, 0.200, 0.050, 0.450]
    # min: 0.050, max: 0.450, mean: (0.1+0.2+0.05+0.45)/4 = 0.200, final: 0.450
    assert act_summary["min"][0] == 0.050
    assert act_summary["max"][0] == 0.450
    assert act_summary["mean"][0] == 0.200
    assert act_summary["final"][0] == 0.450

    # Cơ 1 ("TRIlat"): [0.000, 0.400, 0.300, 0.100]
    # min: 0.000, max: 0.400, mean: (0.0+0.4+0.3+0.1)/4 = 0.200, final: 0.100
    assert act_summary["min"][1] == 0.000
    assert act_summary["max"][1] == 0.400
    assert act_summary["mean"][1] == pytest.approx(0.200)
    assert act_summary["final"][1] == 0.100

    # Cơ 3 ("BIClong"): [0.500, 0.600, 0.700, 0.800]
    # min: 0.500, max: 0.800, mean: 0.650, final: 0.800
    assert act_summary["min"][3] == 0.500
    assert act_summary["max"][3] == 0.800
    assert act_summary["mean"][3] == 0.650
    assert act_summary["final"][3] == 0.800

    # INV-006: Không làm tròn, giữ nguyên số học dấu phẩy động
    raw_fraction_acts = [
        [1.0 / 3.0] * 6,
        [2.0 / 3.0] * 6,
    ]
    ep_fraction = _make_sample_episode(n_frames=2, activations=raw_fraction_acts)
    src_frac = {
        "episode_path": "replays/frac.episode.json",
        "checkpoint_path": None,
        "checkpoint_sha256": None,
    }
    sum_fraction = summarize_episode(
        ep_fraction,
        model_chk,
        source=src_frac,
    )
    # mean của 1/3 và 2/3 là 0.5
    assert sum_fraction["activation"]["mean"][0] == 0.5
    # min giữ nguyên 1/3, không bị làm tròn thành 0.33
    assert sum_fraction["activation"]["min"][0] == 1.0 / 3.0


def test_paths_relative() -> None:
    """Kiểm tra đường dẫn trong tóm tắt luôn là tương đối (FR-018, AC-3, API-VIS-0006)."""
    cwd = Path.cwd()
    abs_ep_path = cwd / "runs" / "exp1" / "demo.episode.json"
    abs_saved_path = cwd / "runs" / "exp1" / "saved.episode.json"
    abs_ckpt_path = cwd / "checkpoints" / "model.pt"

    episode = _make_sample_episode(n_frames=2)
    model_chk = ModelCheck(
        match=True,
        compatible=True,
        episode_sha256=SAMPLE_XML_HASH_A,
        current_sha256=SAMPLE_XML_HASH_A,
    )

    # 1. Đường dẫn episode_path tuyệt đối phải chuyển thành tương đối
    src_abs = {
        "episode_path": str(abs_ep_path),
        "checkpoint_path": None,
        "checkpoint_sha256": None,
    }
    sum_ep = summarize_episode(
        episode,
        model_chk,
        source=src_abs,
    )
    assert not Path(sum_ep["source"]["episode_path"]).is_absolute()
    assert sum_ep["source"]["episode_path"] == "runs/exp1/demo.episode.json"

    # 2. saved_episode tuyệt đối phải chuyển thành tương đối
    sum_saved = summarize_episode(
        episode,
        model_chk,
        source={
            "episode_path": None,
            "checkpoint_path": str(abs_ckpt_path),
            "checkpoint_sha256": SAMPLE_CKPT_HASH,
        },
        saved_episode=abs_saved_path,
    )
    assert sum_saved["saved_episode"] == "runs/exp1/saved.episode.json"
    assert not Path(sum_saved["source"]["checkpoint_path"]).is_absolute()
    assert sum_saved["source"]["checkpoint_path"] == "checkpoints/model.pt"


def test_inv_005_windows_absolute_paths_are_recorded_relatively() -> None:
    """INV-005: Đường dẫn tuyệt đối kiểu Windows được ghi theo dạng tương đối."""
    episode = _make_sample_episode(n_frames=2)
    model_chk = ModelCheck(
        match=True,
        compatible=True,
        episode_sha256=SAMPLE_XML_HASH_A,
        current_sha256=SAMPLE_XML_HASH_A,
    )

    summary = summarize_episode(
        episode,
        model_chk,
        source={
            "episode_path": r"C:\runs\exp1\demo.episode.json",
            "checkpoint_path": r"C:\checkpoints\model.pt",
            "checkpoint_sha256": SAMPLE_CKPT_HASH,
        },
        saved_episode=r"C:\runs\exp1\saved.episode.json",
    )

    assert summary["source"]["episode_path"] == "runs/exp1/demo.episode.json"
    assert summary["source"]["checkpoint_path"] == "checkpoints/model.pt"
    assert summary["saved_episode"] == "runs/exp1/saved.episode.json"


def test_single_frame_episode_no_zero_division() -> None:
    """Kiểm tra episode chỉ có 1 khung không gây lỗi chia cho 0 (FR-010, API-VIS-0006, AC-1)."""
    episode = _make_sample_episode(n_frames=1)
    model_chk = ModelCheck(
        match=True,
        compatible=True,
        episode_sha256=SAMPLE_XML_HASH_A,
        current_sha256=SAMPLE_XML_HASH_A,
    )

    src_single = {
        "episode_path": "replays/single.json",
        "checkpoint_path": None,
        "checkpoint_sha256": None,
    }
    summary = summarize_episode(
        episode,
        model_chk,
        source=src_single,
    )

    assert summary["n_frames"] == 1
    assert summary["n_actions"] == 0
    assert summary["duration_sim_s"] == 0.0
    for i in range(6):
        assert summary["activation"]["min"][i] == summary["activation"]["max"][i]
        assert summary["activation"]["mean"][i] == summary["activation"]["final"][i]


def test_nonfinite_rejected() -> None:
    """Kiểm tra từ chối giá trị không hữu hạn NaN/Infinity (NFR-REL-001, FR-010, AC-5)."""
    episode = _make_sample_episode(n_frames=2)
    model_chk = ModelCheck(
        match=True,
        compatible=True,
        episode_sha256=SAMPLE_XML_HASH_A,
        current_sha256=SAMPLE_XML_HASH_A,
    )

    # 1. Frame chứa NaN trong activation
    bad_frame_nan = Frame(
        t_s=0.08,
        qpos=[0.0],
        qvel=[0.0],
        activation=[0.1, float("nan"), 0.1, 0.1, 0.1, 0.1],
        excitation=None,
        fingertip_position_m=(-0.21, -0.106, 1.12),
        distance_m=0.015,
        reward=0.0,
    )
    bad_ep_nan = Episode(
        schema_version="1.0.0",
        created_utc=episode.created_utc,
        seed=1,
        model=episode.model,
        target=episode.target,
        source=None,
        library_versions=episode.library_versions,
        timing=episode.timing,
        outcome=episode.outcome,
        frames=[episode.frames[0], bad_frame_nan],
    )
    src_test = {
        "episode_path": "test.json",
        "checkpoint_path": None,
        "checkpoint_sha256": None,
    }
    with pytest.raises(EpisodeInvalid, match="hữu hạn|non-finite|NaN"):
        summarize_episode(
            bad_ep_nan,
            model_chk,
            source=src_test,
        )

    # 2. Target chứa Infinity
    bad_target = TargetRecord(
        position_m=(-0.21, float("inf"), 1.12),
        split="test",
        index=0,
        tolerance_m=0.02,
    )
    bad_ep_inf = Episode(
        schema_version="1.0.0",
        created_utc=episode.created_utc,
        seed=1,
        model=episode.model,
        target=bad_target,
        source=None,
        library_versions=episode.library_versions,
        timing=episode.timing,
        outcome=episode.outcome,
        frames=episode.frames,
    )
    with pytest.raises(EpisodeInvalid, match="hữu hạn|non-finite|Infinity"):
        summarize_episode(
            bad_ep_inf,
            model_chk,
            source=src_test,
        )


def test_summary_schema_conformance() -> None:
    """Kiểm tra tóm tắt tuân thủ replay-summary.schema.json (FR-010, API-VIS-0006, AC-3)."""
    rel_schema = "specs/005-replay-3d-muscle-demo/contracts/replay-summary.schema.json"
    schema_path = Path(rel_schema)
    if not schema_path.exists():
        root_prefix = Path("/mnt/01DCE9A4D6522BD0/Project/AI/fighterl")
        schema_path = root_prefix / rel_schema

    schema_data = json.loads(schema_path.read_text(encoding="utf-8"))

    try:
        import jsonschema
    except ImportError:
        jsonschema = None

    episode = _make_sample_episode(n_frames=3)
    model_chk = ModelCheck(
        match=True,
        compatible=True,
        episode_sha256=SAMPLE_XML_HASH_A,
        current_sha256=SAMPLE_XML_HASH_A,
    )

    src_spec = {
        "episode_path": "replays/demo.episode.json",
        "checkpoint_path": None,
        "checkpoint_sha256": None,
    }
    summary = summarize_episode(
        episode,
        model_chk,
        source=src_spec,
        saved_episode="replays/saved.episode.json",
        warnings=["Cảnh báo kiểm thử"],
    )

    expected_keys = {
        "schema_version",
        "mode",
        "headless",
        "source",
        "model_check",
        "n_frames",
        "n_actions",
        "duration_sim_s",
        "seed",
        "target",
        "outcome",
        "activation",
        "saved_episode",
        "playback",
        "warnings",
    }
    assert set(summary.keys()) == expected_keys

    # Xác thực với JSON Schema nếu thư viện jsonschema có sẵn trong môi trường
    if jsonschema is not None:
        jsonschema.validate(instance=summary, schema=schema_data)

    assert summary["mode"] == "episode"
    assert summary["headless"] is True
    assert summary["playback"] is None
    assert summary["warnings"] == ["Cảnh báo kiểm thử"]


def test_model_mismatch_in_summary() -> None:
    """Kiểm tra báo cáo lệch mô hình phản ánh đúng trong tóm tắt (FR-012, INV-001, AC-4)."""
    episode = _make_sample_episode(n_frames=2)
    model_chk = ModelCheck(
        match=False,
        compatible=True,
        episode_sha256=SAMPLE_XML_HASH_A,
        current_sha256=SAMPLE_XML_HASH_B,
        reasons=["Mã băm XML không khớp"],
    )

    src_mismatch = {
        "episode_path": "mismatch.json",
        "checkpoint_path": None,
        "checkpoint_sha256": None,
    }
    summary = summarize_episode(
        episode,
        model_chk,
        source=src_mismatch,
        warnings=["MÔ HÌNH LỆCH: đã chấp nhận bằng --allow-model-mismatch"],
    )

    assert summary["model_check"]["match"] is False
    assert summary["model_check"]["compatible"] is True
    assert summary["model_check"]["episode_sha256"] == SAMPLE_XML_HASH_A
    assert summary["model_check"]["current_sha256"] == SAMPLE_XML_HASH_B
    assert "Mã băm XML không khớp" in summary["model_check"]["reasons"]
    assert "MÔ HÌNH LỆCH: đã chấp nhận bằng --allow-model-mismatch" in summary["warnings"]


def test_demo_mode_with_playback_stats() -> None:
    """Kiểm tra demo có PlaybackStats khi không headless (FR-006, FR-010, AC-2)."""
    episode = _make_sample_episode(n_frames=5, source_ckpt=True)
    model_chk = ModelCheck(
        match=True,
        compatible=True,
        episode_sha256=SAMPLE_XML_HASH_A,
        current_sha256=SAMPLE_XML_HASH_A,
    )
    stats = PlaybackStats(
        wall_s=0.20,
        sim_s=0.16,
        ratio=1.25,
        frames_late=0,
        speed=1.0,
        frames_shown=5,
        max_late_ms=2.0,
    )

    src_demo = {
        "episode_path": None,
        "checkpoint_path": "runs/test/ckpt.pt",
        "checkpoint_sha256": SAMPLE_CKPT_HASH,
    }
    summary = summarize_episode(
        episode,
        model_chk,
        source=src_demo,
        playback=stats,
        saved_episode="replays/demo_out.episode.json",
    )

    assert summary["mode"] == "demo"
    assert summary["headless"] is False
    assert summary["playback"] is not None
    assert summary["playback"]["speed"] == 1.0
    assert summary["playback"]["ratio"] == 1.25
    assert summary["saved_episode"] == "replays/demo_out.episode.json"
