"""Kiểm thử đơn vị cho mô-đun đối chiếu mô hình model_check (tests/unit/test_model_check.py).

Chứng minh các yêu cầu và bất biến kiến trúc:
- FR-012: Kiểm tra lệch mô hình khi phát lại, từ chối hoặc cảnh báo theo cờ.
- INV-001: Không phát lại sai ngầm khi mô hình khác biệt.
- API-VIS-0005: Giao diện check_model và enforce.
- AC-4: Kịch bản chấp nhận về phát hiện lệch mô hình và tương thích cấu trúc.
- FR-018: Thông điệp lỗi tiếng Việt nêu rõ giá trị và ngữ cảnh.
"""

from __future__ import annotations

from typing import Any

import pytest

from mma_ai.visualization.episode import ModelRecord
from mma_ai.visualization.errors import ModelMismatch
from mma_ai.visualization.model_check import (
    ModelCheck,
    MuscleModelInfo,
    check_model,
    enforce,
)

SAMPLE_XML_HASH_A = "a" * 64
SAMPLE_XML_HASH_B = "b" * 64
SAMPLE_MUSCLES = ["TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA"]


def _make_model_record(
    sha256: str = SAMPLE_XML_HASH_A,
    nq: int = 1,
    nv: int = 1,
    muscle_names: list[str] | None = None,
) -> ModelRecord:
    """Tạo đối tượng ModelRecord mẫu phục vụ kiểm thử."""
    return ModelRecord(
        sha256=sha256,
        source="myo_sim/elbow/myoelbow_1dof6muscles.xml",
        muscle_names=list(muscle_names if muscle_names is not None else SAMPLE_MUSCLES),
        nq=nq,
        nv=nv,
    )


def _make_model_info(
    sha256: str = SAMPLE_XML_HASH_A,
    nq: int = 1,
    nv: int = 1,
    muscle_names: list[str] | None = None,
) -> MuscleModelInfo:
    """Tạo đối tượng MuscleModelInfo mẫu phục vụ kiểm thử."""
    return MuscleModelInfo(
        sha256=sha256,
        muscle_names=list(muscle_names if muscle_names is not None else SAMPLE_MUSCLES),
        nq=nq,
        nv=nv,
    )


def test_hash_and_structure_cases() -> None:
    """Kiểm tra toàn diện trường hợp mã băm và cấu trúc (FR-012, INV-001, API-VIS-0005, AC-4)."""
    # Trường hợp 1: Trùng khớp hoàn toàn (match=True, compatible=True)
    rec_exact = _make_model_record(SAMPLE_XML_HASH_A, nq=1, nv=1)
    info_exact = _make_model_info(SAMPLE_XML_HASH_A, nq=1, nv=1)
    chk_exact = check_model(rec_exact, info_exact)

    assert chk_exact.match is True
    assert chk_exact.compatible is True
    assert chk_exact.episode_sha256 == SAMPLE_XML_HASH_A
    assert chk_exact.current_sha256 == SAMPLE_XML_HASH_A
    assert len(chk_exact.reasons) == 0
    # enforce không ném lỗi trong trường hợp hoàn toàn trùng khớp
    enforce(chk_exact, allow_mismatch=False)

    # Trường hợp 2: Lệch mã băm nhưng tương thích cấu trúc (match=False, compatible=True)
    rec_diff_hash = _make_model_record(SAMPLE_XML_HASH_A, nq=1, nv=1)
    info_diff_hash = _make_model_info(SAMPLE_XML_HASH_B, nq=1, nv=1)
    chk_diff_hash = check_model(rec_diff_hash, info_diff_hash)

    assert chk_diff_hash.match is False
    assert chk_diff_hash.compatible is True
    assert len(chk_diff_hash.reasons) == 1
    assert "SHA-256" in chk_diff_hash.reasons[0]

    # Khi không có cờ cho phép: ném ModelMismatch nêu cả hai hash (mã thoát 6)
    with pytest.raises(ModelMismatch) as exc_no_flag:
        enforce(chk_diff_hash, allow_mismatch=False)
    assert exc_no_flag.value.exit_code == 6
    assert SAMPLE_XML_HASH_A in str(exc_no_flag.value)
    assert SAMPLE_XML_HASH_B in str(exc_no_flag.value)

    # Khi có cờ cho phép: tiếp tục kèm cảnh báo
    with pytest.warns(UserWarning, match="lệch"):
        enforce(chk_diff_hash, allow_mismatch=True)

    # Trường hợp 3: Trùng mã băm nhưng lệch số tọa độ nq (match=True, compatible=False)
    rec_diff_nq = _make_model_record(SAMPLE_XML_HASH_A, nq=2, nv=1)
    info_orig = _make_model_info(SAMPLE_XML_HASH_A, nq=1, nv=1)
    chk_diff_nq = check_model(rec_diff_nq, info_orig)

    assert chk_diff_nq.match is True
    assert chk_diff_nq.compatible is False
    assert any("nq" in r for r in chk_diff_nq.reasons)

    # Cấu trúc không tương thích thì kể cả có allow_mismatch vẫn phải từ chối (INV-001)
    with pytest.raises(ModelMismatch) as exc_nq:
        enforce(chk_diff_nq, allow_mismatch=True)
    assert exc_nq.value.exit_code == 6
    assert "nq" in str(exc_nq.value)

    # Trường hợp 4: Trùng mã băm nhưng lệch số bậc tự do nv (match=True, compatible=False)
    rec_diff_nv = _make_model_record(SAMPLE_XML_HASH_A, nq=1, nv=2)
    chk_diff_nv = check_model(rec_diff_nv, info_orig)

    assert chk_diff_nv.match is True
    assert chk_diff_nv.compatible is False
    assert any("nv" in r for r in chk_diff_nv.reasons)
    with pytest.raises(ModelMismatch) as exc_nv:
        enforce(chk_diff_nv, allow_mismatch=True)
    assert exc_nv.value.exit_code == 6
    assert "nv" in str(exc_nv.value)

    # Trường hợp 5: Trùng mã băm nhưng số lượng cơ bắp khác biệt (match=True, compatible=False)
    rec_diff_muscles = _make_model_record(
        SAMPLE_XML_HASH_A, nq=1, nv=1, muscle_names=["TRIlong", "TRIlat"]
    )
    chk_diff_muscles = check_model(rec_diff_muscles, info_orig)

    assert chk_diff_muscles.match is True
    assert chk_diff_muscles.compatible is False
    with pytest.raises(ModelMismatch) as exc_muscles:
        enforce(chk_diff_muscles, allow_mismatch=True)
    assert exc_muscles.value.exit_code == 6

    # Trường hợp 6: Vừa lệch mã băm vừa lệch cấu trúc (match=False, compatible=False)
    rec_both_diff = _make_model_record(SAMPLE_XML_HASH_A, nq=3, nv=2)
    info_other = _make_model_info(SAMPLE_XML_HASH_B, nq=1, nv=1)
    chk_both_diff = check_model(rec_both_diff, info_other)

    assert chk_both_diff.match is False
    assert chk_both_diff.compatible is False
    with pytest.raises(ModelMismatch):
        enforce(chk_both_diff, allow_mismatch=False)
    with pytest.raises(ModelMismatch):
        enforce(chk_both_diff, allow_mismatch=True)


def test_muscle_names_ordering_sensitivity() -> None:
    """Kiểm tra việc so sánh tên cơ nhạy cảm với thứ tự cơ (INV-001, FR-012, API-VIS-0005)."""
    reversed_muscles = list(reversed(SAMPLE_MUSCLES))
    rec = _make_model_record(SAMPLE_XML_HASH_A, muscle_names=reversed_muscles)
    info = _make_model_info(SAMPLE_XML_HASH_A, muscle_names=SAMPLE_MUSCLES)

    chk = check_model(rec, info)
    assert chk.match is True
    assert chk.compatible is False
    assert any("thứ tự" in r.lower() or "tên cơ" in r.lower() for r in chk.reasons)

    with pytest.raises(ModelMismatch) as exc:
        enforce(chk, allow_mismatch=True)
    assert exc.value.exit_code == 6


def test_check_model_input_formats() -> None:
    """Kiểm tra check_model xử lý linh hoạt nhiều kiểu đầu vào (API-VIS-0005, FR-012)."""
    # 1. Truyền dict chứa key 'model' (mô phỏng dict của toàn bộ Episode)
    episode_dict: dict[str, Any] = {
        "model": {
            "sha256": SAMPLE_XML_HASH_A,
            "source": "model.xml",
            "muscle_names": SAMPLE_MUSCLES,
            "nq": 1,
            "nv": 1,
        }
    }
    info = _make_model_info(SAMPLE_XML_HASH_A)
    chk1 = check_model(episode_dict, info)
    assert chk1.match is True
    assert chk1.compatible is True

    # 2. Truyền dict trần của model
    model_dict: dict[str, Any] = {
        "sha256": SAMPLE_XML_HASH_A,
        "muscle_names": SAMPLE_MUSCLES,
        "nq": 1,
        "nv": 1,
    }
    chk2 = check_model(model_dict, info)
    assert chk2.match is True
    assert chk2.compatible is True

    # 3. model_info là dict
    info_dict: dict[str, Any] = {
        "sha256": SAMPLE_XML_HASH_A,
        "muscle_names": SAMPLE_MUSCLES,
        "nq": 1,
        "nv": 1,
    }
    chk3 = check_model(model_dict, info_dict)
    assert chk3.match is True
    assert chk3.compatible is True


def test_model_check_to_dict() -> None:
    """Kiểm tra phương thức to_dict của ModelCheck (FR-012, API-VIS-0005)."""
    chk = ModelCheck(
        match=False,
        compatible=True,
        episode_sha256=SAMPLE_XML_HASH_A,
        current_sha256=SAMPLE_XML_HASH_B,
        reasons=["Mã băm SHA-256 XML không khớp"],
    )
    d = chk.to_dict()
    assert d == {
        "match": False,
        "compatible": True,
        "episode_sha256": SAMPLE_XML_HASH_A,
        "current_sha256": SAMPLE_XML_HASH_B,
        "reasons": ["Mã băm SHA-256 XML không khớp"],
    }


def test_enforce_raises_model_mismatch_with_context() -> None:
    """Kiểm tra enforce ném ModelMismatch kèm ngữ cảnh chi tiết (INV-001, FR-018)."""
    # Khi lệch cấu trúc nq và số cơ
    rec = _make_model_record(SAMPLE_XML_HASH_A, nq=2, muscle_names=["TRIlong"])
    info = _make_model_info(SAMPLE_XML_HASH_A, nq=1, muscle_names=SAMPLE_MUSCLES)
    chk = check_model(rec, info)

    with pytest.raises(ModelMismatch) as exc:
        enforce(chk, allow_mismatch=True)

    msg = str(exc.value)
    # Thông điệp tiếng Việt phải nêu rõ giá trị mong đợi và thực có
    assert "nq" in msg
    assert "cơ" in msg
    assert exc.value.exit_code == 6
