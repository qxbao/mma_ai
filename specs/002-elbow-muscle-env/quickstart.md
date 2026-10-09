---
id: "QS-002"
title: "M1 (1/4) — Hướng dẫn kiểm chứng nhanh (Quickstart)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "002-elbow-muscle-env"
version: "1.0.0"
---

# Quickstart — kiểm chứng môi trường khuỷu tay

- [Kịch bản 1 — Dựng môi trường & 6 cơ (AC-1, AC-4, INV-003)](#kich-ban-1-dung-moi-truong-6-co-ac-1-ac-4-inv-003)
- [Kịch bản 2 — Rollout ngẫu nhiên: chiều, NaN/Inf, ngoài khoảng (AC-2, INV-004)](#kich-ban-2-rollout-ngau-nhien-chieu-naninf-ngoai-khoang-ac-2-inv-004)
- [Kịch bản 3 — Tập mục tiêu train/test tách bạch, tất định (AC-3, INV-001, INV-002)](#kich-ban-3-tap-muc-tieu-traintest-tach-bach-tat-dinh-ac-3-inv-001-inv-002)
- [Kịch bản 4 — Reward và kết thúc episode (AC-2)](#kich-ban-4-reward-va-ket-thuc-episode-ac-2)
- [Kịch bản 5 — Quyết định phiên bản & cài trong môi trường sạch (AC-5)](#kich-ban-5-quyet-dinh-phien-ban-cai-trong-moi-truong-sach-ac-5)
- [Kịch bản 6 — Hợp đồng bản ghi (AC-1, AC-3)](#kich-ban-6-hop-dong-ban-ghi-ac-1-ac-3)


Lệnh và API: `contracts/python-api.md`; khuôn bản ghi: `contracts/*.schema.json`; thực thể: `data-model.md`. Chỉ thực hiện sau khi các task triển khai đã dựng mã và M0 (001) đã có mã. Mọi tên test dưới đây là tên **kế hoạch**; chưa chạy nghĩa là chưa có kết quả.

**Điều kiện tiên quyết**: `uv` đã cài; Linux/WSL2 Ubuntu; mã của 001 (`mma_ai.physics`, `configs/body.yaml`).

<a id="kich-ban-1-dung-moi-truong-6-co-ac-1-ac-4-inv-003"></a>
## Kịch bản 1 — Dựng môi trường & 6 cơ (AC-1, AC-4, INV-003)

1. `uv python install 3.11 && uv sync --extra dev`
2. `uv run python -c "from mma_ai.environment.single_agent import make_env; e=make_env(); print(e.action_space, e.observation_space.shape); print(e.model_record()['n_muscles'], e.model_record()['sha256'])"`
3. Test tự động thay cho đọc tay: `tests/integration/test_elbow_env.py::test_loads_exactly_six_muscles`, `::test_action_space_is_unit_box_6`, `::test_model_sha256_in_info`, `tests/integration/test_control_structure.py::test_all_actuators_are_muscle`, `::test_state_not_written_outside_mj_step`.

Kỳ vọng: `Box(0.0, 1.0, (6,), float32)`, `(14,)`, `6`, hash 64 ký tự hex; 0 actuator không phải cơ.

<a id="kich-ban-2-rollout-ngau-nhien-chieu-naninf-ngoai-khoang-ac-2-inv-004"></a>
## Kịch bản 2 — Rollout ngẫu nhiên: chiều, NaN/Inf, ngoài khoảng (AC-2, INV-004)

1. `uv run python -m pytest -q tests/integration/test_elbow_env.py::test_random_rollout_no_nan_inf tests/unit/test_observation.py`
2. Kỳ vọng: ≥ 10 episode × tối đa 100 hành động ngẫu nhiên có seed; 0 NaN, 0 Inf, 0 giá trị ngoài `observation_space`; rollout cực đoan (toàn 0, toàn 1, nhóm gập, nhóm duỗi) cũng trong cận (`test_observation::test_normalisation_matches_bounds`).
3. Chạy không màn hình (NFR-HEADLESS-001): `tests/integration/test_headless.py::test_runs_without_display` (bỏ đặt `DISPLAY`); `tests/integration/test_elbow_env.py::test_gymnasium_check_env`.

<a id="kich-ban-3-tap-muc-tieu-traintest-tach-bach-tat-dinh-ac-3-inv-001-inv-002"></a>
## Kịch bản 3 — Tập mục tiêu train/test tách bạch, tất định (AC-3, INV-001, INV-002)

1. `uv run python -m pytest -q tests/regression/test_target_determinism.py tests/unit/test_targets.py`
2. Kỳ vọng: `test_same_seed_same_sets` (hai lần sinh cùng seed ⇒ `fingerprint_sha256` trùng), `test_train_test_disjoint` (giao = ∅, `min_cross_distance_m ≥ min_separation_m`), `test_all_targets_reachable`, `test_infeasible_config_raises`.
3. Môi trường chỉ bốc đúng tập đã chọn: `tests/integration/test_elbow_env.py::test_test_split_never_samples_train`, `::test_reset_info_fields` (trường `target_split`, `target_index`, `seed`).

<a id="kich-ban-4-reward-va-ket-thuc-episode-ac-2"></a>
## Kịch bản 4 — Reward và kết thúc episode (AC-2)

1. `uv run python -m pytest -q tests/unit/test_reward.py tests/integration/test_elbow_env.py::test_terminated_on_reach tests/integration/test_elbow_env.py::test_truncated_at_max_actions`
2. Kỳ vọng: reward hữu hạn; gần mục tiêu ⇒ thành phần khoảng cách cao hơn; đặt `w_effort = 0` ⇒ thành phần phạt = 0; `terminated` khi `d ≤ tolerance_m`, `truncated` khi đủ `max_actions`.

<a id="kich-ban-5-quyet-dinh-phien-ban-cai-trong-moi-truong-sach-ac-5"></a>
## Kịch bản 5 — Quyết định phiên bản & cài trong môi trường sạch (AC-5)

1. `uv run python -m pytest -q tests/integration/test_dependency_decision.py` — `myosuite` không có trong `pyproject.toml`/`uv.lock`, `gymnasium` ≥ 1.4.
2. `uv run python scripts/verify_clean_install.py` — tạo môi trường ảo mới, cài theo `uv.lock` (`uv sync --frozen`), chạy bộ test của môi trường; mã thoát 0 và `logs/m1/verify_clean_install.json` ghi lệnh, phiên bản đã cài, mã thoát.
3. Lý do chọn phiên bản: `research.md` Q1 (phương án chọn, phương án loại, bằng chứng đã đo).

<a id="kich-ban-6-hop-dong-ban-ghi-ac-1-ac-3"></a>
## Kịch bản 6 — Hợp đồng bản ghi (AC-1, AC-3)

1. `uv run python -m pytest -q tests/integration/test_contract_examples_m1.py` — mọi tệp ở `contracts/examples/` hợp schema tương ứng (draft 2020-12), và đầu ra thật của `env.model_record()`, `TargetGenerator.generate(...).to_dict()`, `reset`/`step` info hợp schema.
