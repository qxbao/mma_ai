"""Bộ kiểm thử đơn vị cho việc đọc, ghi và xác thực cấu trúc Episode (mma_ai.visualization.episode).

Truy vết các yêu cầu kỹ thuật và bất biến:
- FR-007: Định dạng dữ liệu episode với đầy đủ thông tin (tự đủ).
- FR-008: Ghi episode nguyên tử (atomic write) và từ chối ghi đè tệp đã tồn tại.
- FR-009: Kiểm tra cấu trúc và tính nhất quán (luật R1–R7) khi nạp episode.
- FR-013: Báo lỗi khi episode không tồn tại hoặc sai khuôn lược đồ.
- FR-018: Thông báo lỗi bằng tiếng Việt kèm ngữ cảnh chi tiết.
- INV-003: Bản ghi episode tự đủ (seed, hash XML, 6 tên cơ, phiên bản, giá trị null tường minh).
- INV-004: Thoát mã lỗi và dọn sạch tệp tạm khi gặp sự cố, không để lại tệp dở dang.
- INV-005: Hoạt động chỉ đọc đối với tệp nguồn, từ chối ghi đè lên tệp đích đã có.
- NFR-REL-001: Độ tin cậy số học, 0 giá trị NaN/Infinity, từ chối các số không hữu hạn.
- API-VIS-0002: read_episode(path) -> Episode.
- API-VIS-0003: write_episode(episode, path) -> Path.
- AC-1: Đọc và xác thực cấu trúc episode phục vụ phát lại 3D.
- AC-4: Kiểm tra và lưu vết hash mô hình XML.
- AC-5: Xử lý ngoại lệ chuẩn xác khi đường dẫn sai hoặc tệp hỏng.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

try:
    import jsonschema
except ImportError:
    jsonschema = None

import pytest

from mma_ai.visualization.episode import (
    Episode,
    read_episode,
    write_episode,
)
from mma_ai.visualization.errors import (
    EpisodeInvalid,
    EpisodeNotFound,
    EpisodeWriteError,
)

SCHEMA_PATH = Path("specs/005-replay-3d-muscle-demo/contracts/episode.schema.json")
EXAMPLES_DIR = Path("specs/005-replay-3d-muscle-demo/contracts/examples")


@pytest.fixture  # type: ignore[untyped-decorator]
def episode_schema() -> dict[str, Any]:
    """Nạp lược đồ JSON Schema chuẩn của Episode để đối chiếu."""
    assert SCHEMA_PATH.is_file(), f"Không tìm thấy lược đồ tại {SCHEMA_PATH}"
    return cast(dict[str, Any], json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


@pytest.fixture  # type: ignore[untyped-decorator]
def valid_episode_data() -> dict[str, Any]:
    """Cung cấp dữ liệu từ điển hợp lệ của một episode mẫu chuẩn."""
    return {
        "schema_version": "1.0.0",
        "created_utc": "2026-10-09T08:00:00Z",
        "seed": 12345,
        "model": {
            "sha256": "384dcb555561287f000000000000000000000000000000000000000000000000",
            "source": "myo_sim/elbow/myoelbow_1dof6muscles.xml",
            "muscle_names": [
                "TRIlong",
                "TRIlat",
                "TRImed",
                "BIClong",
                "BICshort",
                "BRA",
            ],
            "nq": 1,
            "nv": 1,
        },
        "target": {
            "position_m": [-0.21, -0.106, 1.12],
            "split": "test",
            "index": 0,
            "tolerance_m": 0.02,
        },
        "source": {
            "checkpoint_path": "runs/example_run/checkpoints/ckpt_u000050_final.pt",
            "checkpoint_sha256": "5555555555555555555555555555555555555555555555555555555555555555",
            "run_id": "example_run",
            "update_idx": 50,
        },
        "library_versions": {
            "mujoco": "3.15.0",
            "numpy": "2.4.6",
            "python": "3.11.15",
        },
        "timing": {
            "action_dt_s": 0.04,
            "physics_timestep_s": 0.0025,
        },
        "outcome": {
            "terminated": True,
            "truncated": False,
            "end_reason": "reached",
            "reached": True,
            "n_actions": 1,
            "final_distance_m": 0.012,
        },
        "frames": [
            {
                "t_s": 0.0,
                "qpos": [0.05],
                "qvel": [0.0],
                "activation": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "excitation": None,
                "fingertip_position_m": [-0.21, 0.05, 0.9],
                "distance_m": 0.3,
                "reward": 0.0,
            },
            {
                "t_s": 0.04,
                "qpos": [0.55],
                "qvel": [12.0],
                "activation": [0.01, 0.01, 0.01, 0.22, 0.2, 0.18],
                "excitation": [0.0, 0.0, 0.0, 0.9, 0.85, 0.8],
                "fingertip_position_m": [-0.21, 0.0, 0.97],
                "distance_m": 0.012,
                "reward": 1.0,
            },
        ],
    }


def test_write_read_roundtrip_and_schema(
    tmp_path: Path, valid_episode_data: dict[str, Any], episode_schema: dict[str, Any]
) -> None:
    """Kiểm tra ghi rồi đọc lại episode bảo toàn dữ liệu và tuân thủ lược đồ JSON Schema.

    Chứng minh: FR-007, FR-008, API-VIS-0002, API-VIS-0003, AC-1, INV-003.
    """
    file_path = tmp_path / "test.episode.json"
    ep_obj = Episode.from_dict(valid_episode_data)

    saved_path = write_episode(ep_obj, file_path)
    assert saved_path == file_path
    assert file_path.is_file()

    # Kiểm tra JSON trên đĩa hợp lệ theo episode.schema.json
    raw_saved = json.loads(file_path.read_text(encoding="utf-8"))
    if jsonschema is not None:
        jsonschema.validate(instance=raw_saved, schema=episode_schema)

    # Đọc lại và kiểm tra tính toàn vẹn (roundtrip)
    loaded_ep = read_episode(file_path)
    assert loaded_ep.schema_version == "1.0.0"
    assert loaded_ep.seed == 12345
    assert loaded_ep.model.sha256 == valid_episode_data["model"]["sha256"]
    assert loaded_ep.model.muscle_names == valid_episode_data["model"]["muscle_names"]
    assert len(loaded_ep.frames) == 2
    assert loaded_ep.outcome.reached is True
    assert loaded_ep.frames[0].excitation is None
    assert loaded_ep.frames[1].excitation is not None
    assert loaded_ep.to_dict() == valid_episode_data


def test_required_provenance_fields(tmp_path: Path, valid_episode_data: dict[str, Any]) -> None:
    """Kiểm tra các trường nguồn gốc xuất xứ bắt buộc theo INV-003 không được thiếu.

    Chứng minh: INV-003, FR-007, AC-1.
    """
    file_path = tmp_path / "missing_field.json"

    # Kiểm tra khi source = null vẫn hợp lệ (INV-003: null tường minh)
    data_with_null_source = dict(valid_episode_data)
    data_with_null_source["source"] = None
    file_path.write_text(json.dumps(data_with_null_source), encoding="utf-8")
    loaded = read_episode(file_path)
    assert loaded.source is None

    # Thiếu trường bắt buộc cấp 1 (ví dụ seed)
    data_missing_seed = dict(valid_episode_data)
    del data_missing_seed["seed"]
    file_path.write_text(json.dumps(data_missing_seed), encoding="utf-8")
    with pytest.raises(EpisodeInvalid, match="seed"):
        read_episode(file_path)

    # Thiếu trường trong model (ví dụ sha256)
    data_missing_sha = dict(valid_episode_data)
    data_missing_sha["model"] = dict(valid_episode_data["model"])
    del data_missing_sha["model"]["sha256"]
    file_path.write_text(json.dumps(data_missing_sha), encoding="utf-8")
    with pytest.raises(EpisodeInvalid, match="sha256"):
        read_episode(file_path)


def test_refuse_overwrite(tmp_path: Path, valid_episode_data: dict[str, Any]) -> None:
    """Kiểm tra hàm write_episode từ chối ghi đè lên tệp đã tồn tại sẵn.

    Chứng minh: INV-005, FR-008, AC-5.
    """
    file_path = tmp_path / "existing.episode.json"
    file_path.write_text("{}", encoding="utf-8")

    ep_obj = Episode.from_dict(valid_episode_data)
    with pytest.raises(EpisodeWriteError, match="đã tồn tại"):
        write_episode(ep_obj, file_path)

    # Đảm bảo nội dung tệp cũ không bị thay đổi
    assert file_path.read_text(encoding="utf-8") == "{}"


def test_atomic_write_no_partial(
    tmp_path: Path, valid_episode_data: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kiểm tra việc ghi nguyên tử dọn sạch tệp tạm khi gặp lỗi, không để lại tệp dở dang.

    Chứng minh: INV-004, FR-008, AC-5.
    """
    file_path = tmp_path / "target.episode.json"
    ep_obj = Episode.from_dict(valid_episode_data)

    def _mock_dump_error(*args: Any, **kwargs: Any) -> None:
        raise OSError("Giả lập lỗi đĩa khi ghi")

    monkeypatch.setattr(json, "dump", _mock_dump_error)

    with pytest.raises(EpisodeWriteError, match="lỗi"):
        write_episode(ep_obj, file_path)

    assert not file_path.exists()
    # Kiểm tra không còn tệp tạm nào sót lại trong thư mục
    tmp_files = list(tmp_path.glob("*.tmp*"))
    assert len(tmp_files) == 0


def test_n_actions_matches_frames(tmp_path: Path, valid_episode_data: dict[str, Any]) -> None:
    """Kiểm tra luật R1: outcome.n_actions phải bằng số khung trừ đi 1.

    Chứng minh: FR-009, R1, AC-5.
    """
    file_path = tmp_path / "bad_n_actions.json"
    data = dict(valid_episode_data)
    data["outcome"] = dict(data["outcome"])
    data["outcome"]["n_actions"] = 99  # Trong khi có 2 khung -> kỳ vọng n_actions = 1

    file_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EpisodeInvalid) as exc_info:
        read_episode(file_path)
    assert "99" in str(exc_info.value)
    assert "1" in str(exc_info.value)


def test_time_monotonic(tmp_path: Path, valid_episode_data: dict[str, Any]) -> None:
    """Kiểm tra luật R2: t_s không giảm, khung 0 bằng 0.0 và hiệu hai khung liền kề ≈ dt.

    Chứng minh: FR-009, R2, AC-5.
    """
    file_path = tmp_path / "bad_timing.json"

    # Ca 1: khung 0 có t_s khác 0.0
    data1 = dict(valid_episode_data)
    data1["frames"] = [dict(f) for f in data1["frames"]]
    data1["frames"][0]["t_s"] = 0.5
    file_path.write_text(json.dumps(data1), encoding="utf-8")
    with pytest.raises(EpisodeInvalid, match="0\\.0"):
        read_episode(file_path)

    # Ca 2: thời gian giảm (không đơn điệu tăng)
    data2 = dict(valid_episode_data)
    data2["frames"] = [dict(f) for f in data2["frames"]]
    data2["frames"][0]["t_s"] = 0.0
    data2["frames"][1]["t_s"] = -0.01
    file_path.write_text(json.dumps(data2), encoding="utf-8")
    with pytest.raises(EpisodeInvalid):
        read_episode(file_path)

    # Ca 3: bước thời gian sai lệch quá dung sai so với action_dt_s
    data3 = dict(valid_episode_data)
    data3["frames"] = [dict(f) for f in data3["frames"]]
    data3["frames"][0]["t_s"] = 0.0
    data3["frames"][1]["t_s"] = 0.09  # dt = 0.09 khác 0.04
    file_path.write_text(json.dumps(data3), encoding="utf-8")
    with pytest.raises(EpisodeInvalid):
        read_episode(file_path)


def test_state_dims_match_model(tmp_path: Path, valid_episode_data: dict[str, Any]) -> None:
    """Kiểm tra luật R3: độ dài qpos và qvel ở mọi khung phải khớp model.nq và model.nv.

    Chứng minh: FR-009, R3, AC-5.
    """
    file_path = tmp_path / "bad_dims.json"
    data = dict(valid_episode_data)
    data["frames"] = [dict(f) for f in data["frames"]]
    data["frames"][1]["qpos"] = [0.1, 0.2]  # nq = 1 nhưng có 2 phần tử

    file_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EpisodeInvalid, match="qpos"):
        read_episode(file_path)


def test_first_frame_has_no_action(tmp_path: Path, valid_episode_data: dict[str, Any]) -> None:
    """Kiểm tra luật R4: khung 0 có excitation = null và các khung sau có excitation != null.

    Chứng minh: FR-009, R4, AC-5.
    """
    file_path = tmp_path / "bad_excitation.json"

    # Khung 0 có excitation
    data1 = dict(valid_episode_data)
    data1["frames"] = [dict(f) for f in data1["frames"]]
    data1["frames"][0]["excitation"] = [0.0] * 6
    file_path.write_text(json.dumps(data1), encoding="utf-8")
    with pytest.raises(EpisodeInvalid, match="khung 0"):
        read_episode(file_path)

    # Khung 1 thiếu excitation (bị null)
    data2 = dict(valid_episode_data)
    data2["frames"] = [dict(f) for f in data2["frames"]]
    data2["frames"][1]["excitation"] = None
    file_path.write_text(json.dumps(data2), encoding="utf-8")
    with pytest.raises(EpisodeInvalid):
        read_episode(file_path)


def test_muscle_names_unique(tmp_path: Path, valid_episode_data: dict[str, Any]) -> None:
    """Kiểm tra luật R5: danh sách muscle_names phải có đủ 6 tên khác nhau và không rỗng.

    Chứng minh: FR-009, R5, AC-5.
    """
    file_path = tmp_path / "bad_muscles.json"

    # Trùng tên cơ
    data1 = dict(valid_episode_data)
    data1["model"] = dict(data1["model"])
    data1["model"]["muscle_names"] = ["TRI", "TRI", "TRI", "BIC", "BIC", "BRA"]
    file_path.write_text(json.dumps(data1), encoding="utf-8")
    with pytest.raises(EpisodeInvalid, match="trùng"):
        read_episode(file_path)

    # Có tên cơ rỗng sau khi cắt khoảng trắng
    data2 = dict(valid_episode_data)
    data2["model"] = dict(data2["model"])
    data2["model"]["muscle_names"] = ["TRIlong", "   ", "TRImed", "BIClong", "BICshort", "BRA"]
    file_path.write_text(json.dumps(data2), encoding="utf-8")
    with pytest.raises(EpisodeInvalid, match="rỗng"):
        read_episode(file_path)


def test_outcome_consistent(tmp_path: Path, valid_episode_data: dict[str, Any]) -> None:
    """Kiểm tra luật R6: tính nhất quán giữa end_reason, reached, terminated và truncated.

    Chứng minh: FR-009, R6, AC-5.
    """
    file_path = tmp_path / "bad_outcome.json"

    # end_reason = "reached" nhưng reached = False
    data1 = dict(valid_episode_data)
    data1["outcome"] = dict(data1["outcome"])
    data1["outcome"]["end_reason"] = "reached"
    data1["outcome"]["reached"] = False
    data1["outcome"]["terminated"] = True
    file_path.write_text(json.dumps(data1), encoding="utf-8")
    with pytest.raises(EpisodeInvalid, match="reached"):
        read_episode(file_path)

    # end_reason = "max_actions" nhưng truncated = False
    data2 = dict(valid_episode_data)
    data2["outcome"] = dict(data2["outcome"])
    data2["outcome"]["end_reason"] = "max_actions"
    data2["outcome"]["reached"] = False
    data2["outcome"]["terminated"] = False
    data2["outcome"]["truncated"] = False
    file_path.write_text(json.dumps(data2), encoding="utf-8")
    with pytest.raises(EpisodeInvalid, match="truncated"):
        read_episode(file_path)


def test_nonfinite_rejected(tmp_path: Path, valid_episode_data: dict[str, Any]) -> None:
    """Kiểm tra luật R7: từ chối các giá trị không hữu hạn (NaN, Infinity) cả khi ghi lẫn khi đọc.

    Chứng minh: NFR-REL-001, FR-009, R7, AC-5.
    """
    file_path = tmp_path / "nonfinite.json"

    # Thử đọc tệp JSON chứa chuỗi NaN (được tạo thủ công)
    raw_text = json.dumps(valid_episode_data).replace("0.012", "NaN")
    file_path.write_text(raw_text, encoding="utf-8")
    with pytest.raises(EpisodeInvalid, match="NaN|hữu hạn"):
        read_episode(file_path)

    # Thử đọc tệp JSON chứa Infinity
    raw_text_inf = json.dumps(valid_episode_data).replace("0.012", "Infinity")
    file_path.write_text(raw_text_inf, encoding="utf-8")
    with pytest.raises(EpisodeInvalid, match="Infinity|hữu hạn"):
        read_episode(file_path)

    # Thử ghi dữ liệu chứa giá trị float('nan')
    data_nan = dict(valid_episode_data)
    data_nan["outcome"] = dict(data_nan["outcome"])
    data_nan["outcome"]["final_distance_m"] = float("nan")
    with pytest.raises((EpisodeInvalid, EpisodeWriteError)):
        write_episode(data_nan, tmp_path / "should_fail.episode.json")
    with pytest.raises(EpisodeInvalid, match="hữu hạn"):
        Episode.from_dict(data_nan)


def test_missing_file_raises_not_found(tmp_path: Path) -> None:
    """Kiểm tra mở tệp không tồn tại ném EpisodeNotFound với mã lỗi 5.

    Chứng minh: FR-013, AC-5, API-VIS-0002.
    """
    missing_path = tmp_path / "nonexistent.episode.json"
    with pytest.raises(EpisodeNotFound, match="Không tìm thấy"):
        read_episode(missing_path)


def test_unsupported_schema_version_rejected(
    tmp_path: Path, valid_episode_data: dict[str, Any]
) -> None:
    """Kiểm tra phiên bản lược đồ không được hỗ trợ bị từ chối và nêu rõ cả hai phiên bản.

    Chứng minh: FR-009, AC-5.
    """
    file_path = tmp_path / "unsupported_version.json"
    data = dict(valid_episode_data)
    data["schema_version"] = "2.0.0"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(EpisodeInvalid) as exc_info:
        read_episode(file_path)
    assert "2.0.0" in str(exc_info.value)
    assert "1.0.0" in str(exc_info.value)


def test_load_existing_contract_examples() -> None:
    """Kiểm tra nạp thành công các ví dụ hợp đồng mẫu đóng gói sẵn trong contracts/examples.

    Chứng minh: FR-007, INV-003, AC-1.
    """
    ex1 = EXAMPLES_DIR / "episode.minimal-null-source.json"
    if ex1.is_file():
        ep1 = read_episode(ex1)
        assert ep1.schema_version == "1.0.0"
        assert ep1.source is None

    ex2 = EXAMPLES_DIR / "episode.from-checkpoint-reached.json"
    if ex2.is_file():
        ep2 = read_episode(ex2)
        assert ep2.schema_version == "1.0.0"
        assert ep2.source is not None
        assert ep2.outcome.reached is True


def test_regress_f001_non_finite_numeric_string_rejected(
    tmp_path: Path, valid_episode_data: dict[str, Any]
) -> None:
    """Kiểm tra hồi quy F-001 (INV-003, NFR-REL-001, FR-009): từ chối chuỗi số không hữu hạn.

    Các chuỗi như 'NaN', 'inf', '-inf', 'Infinity', '-Infinity', '1e999' ở trường số
    (qpos, qvel, fingertip, reward, tolerance_m, final_distance_m) phải bị từ chối.
    """
    bad_strings = ["NaN", "nan", "inf", "-inf", "Infinity", "-Infinity", "1e999"]
    for val in bad_strings:
        # Trường hợp 1: qpos chứa chuỗi
        d1 = dict(valid_episode_data)
        d1["frames"] = [dict(f) for f in d1["frames"]]
        d1["frames"][1] = dict(d1["frames"][1])
        d1["frames"][1]["qpos"] = [val]
        p1 = tmp_path / f"bad_qpos_{val}.json"
        p1.write_text(json.dumps(d1), encoding="utf-8")
        with pytest.raises(EpisodeInvalid):
            read_episode(p1)

        # Trường hợp 2: reward chứa chuỗi
        d2 = dict(valid_episode_data)
        d2["frames"] = [dict(f) for f in d2["frames"]]
        d2["frames"][0] = dict(d2["frames"][0])
        d2["frames"][0]["reward"] = val
        p2 = tmp_path / f"bad_reward_{val}.json"
        p2.write_text(json.dumps(d2), encoding="utf-8")
        with pytest.raises(EpisodeInvalid):
            read_episode(p2)

        # Trường hợp 3: target.tolerance_m chứa chuỗi
        d3 = dict(valid_episode_data)
        d3["target"] = dict(d3["target"])
        d3["target"]["tolerance_m"] = val
        p3 = tmp_path / f"bad_tolerance_{val}.json"
        p3.write_text(json.dumps(d3), encoding="utf-8")
        with pytest.raises(EpisodeInvalid):
            read_episode(p3)

        # Trường hợp 4: outcome.final_distance_m chứa chuỗi
        d4 = dict(valid_episode_data)
        d4["outcome"] = dict(d4["outcome"])
        d4["outcome"]["final_distance_m"] = val
        p4 = tmp_path / f"bad_dist_{val}.json"
        p4.write_text(json.dumps(d4), encoding="utf-8")
        with pytest.raises(EpisodeInvalid):
            read_episode(p4)


def test_regress_f002_schema_type_and_range_violations_rejected(
    tmp_path: Path, valid_episode_data: dict[str, Any]
) -> None:
    """Kiểm tra hồi quy F-002 (INV-003, FR-009): từ chối vi phạm lược đồ episode.schema.json.

    Bao gồm: target.split ngoài enum, target.index sai kiểu/âm, tolerance_m <= 0,
    final_distance_m < 0, created_utc sai kiểu, phần tử bool thay cho số.
    """
    cases: list[tuple[str, Any, Any]] = [
        ("target", "split", 123),
        ("target", "split", "validation"),
        ("target", "split", {}),
        ("target", "index", "x"),
        ("target", "index", -5),
        ("target", "index", []),
        ("target", "tolerance_m", -0.05),
        ("target", "tolerance_m", 0.0),
        ("outcome", "final_distance_m", -1.0),
        ("created_utc", None, {}),
        ("created_utc", None, 12345),
        ("created_utc", None, None),
    ]

    for parent, child, val in cases:
        d = dict(valid_episode_data)
        if child is None:
            d[parent] = val
        else:
            d[parent] = dict(d[parent])
            d[parent][child] = val
        p = tmp_path / f"bad_schema_{parent}_{child}_{type(val).__name__}.json"
        p.write_text(json.dumps(d), encoding="utf-8")
        with pytest.raises(EpisodeInvalid):
            read_episode(p)

    # Kiểm tra bool thay cho số trong qpos/reward
    d_bool = dict(valid_episode_data)
    d_bool["frames"] = [dict(f) for f in d_bool["frames"]]
    d_bool["frames"][0] = dict(d_bool["frames"][0])
    d_bool["frames"][0]["qpos"] = [True]
    p_bool = tmp_path / "bad_bool_qpos.json"
    p_bool.write_text(json.dumps(d_bool), encoding="utf-8")
    with pytest.raises(EpisodeInvalid):
        read_episode(p_bool)


def test_regress_f003_race_condition_file_created_between_check_and_write_not_overwritten(
    tmp_path: Path, valid_episode_data: dict[str, Any]
) -> None:
    """Kiểm tra hồi quy F-003 (INV-005): tệp xuất hiện trước bước hoán đổi không bị ghi đè.

    Sử dụng os.link nguyên tử thay vì os.replace ghi đè, và kiểm tra từ chối cả symlink treo.
    """
    dest = tmp_path / "concurrent_ep.json"
    ep = Episode.from_dict(valid_episode_data)

    # 1. Ghi lần đầu thành công
    res_path = write_episode(ep, dest)
    assert res_path == dest
    first_bytes = dest.read_bytes()

    # 2. Ghi lần hai vào cùng đích bị từ chối và nội dung cũ nguyên vẹn
    with pytest.raises(EpisodeWriteError):
        write_episode(ep, dest)
    assert dest.read_bytes() == first_bytes

    # 3. Đích là symlink treo (dangling symlink) phải bị từ chối
    dangling_link = tmp_path / "dangling.json"
    dangling_link.symlink_to(tmp_path / "nonexistent.json")
    with pytest.raises(EpisodeWriteError):
        write_episode(ep, dangling_link)
    assert dangling_link.is_symlink()

