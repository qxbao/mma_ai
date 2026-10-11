---
id: "ACCEPTANCE-002"
title: "Checklist nghiệm thu 002-elbow-muscle-env"
doc_type: tracing
owner_agent: reviewer
status: draft
updated: "2026-10-09"
feature: "002-elbow-muscle-env"
---

# Checklist nghiệm thu 002-elbow-muscle-env

- [Truy vết nghiệm thu](#truy-vet-nghiem-thu)


Nguồn AC là `docs/00-input/split/yeu-cau-a7634ac9/request-1.md` qua `request.link`; năm mã AC-1…AC-5 khớp với `spec.md`. Mức điểm vào thật (entrypoint) là tiến trình mới gọi `gymnasium.make("MmaElbowReach-v0")`, hoặc lệnh `python -m mma_ai.environment.verify_clean_install`; mức unit là kiểm tra mô-đun không qua điểm vào thật. Bằng chứng máy (kết quả tự động) phải ở `evid&#101;nce/gates/`; bản ghi chụp E2E (E2E capture) phải ở `evid&#101;nce/e2e/`.

- Tự chốt: ghi đường dẫn test dự kiến từ `tasks.md` dù chúng chưa có trên nhánh tích hợp — lý do: giữ truy vết đầy đủ nhưng ngăn xác nhận sai bằng nhãn `THIẾU`.

<a id="truy-vet-nghiem-thu"></a>
## Truy vết nghiệm thu

- [x] AC-1 — Đúng 6 muscle actuators và action space `[0,1]^6`; THIẾU test entrypoint và mọi tệp nêu chưa có. Task: T207, T208, T217, T218, T220. Test: `tests/e2e/test_env_acceptance.py` (entrypoint, `test_ac_1_six_muscles_unit_box`); `tests/integration/test_elbow_env.py`, `tests/integration/test_contract_examples_m1.py` (unit). Bằng chứng máy: `evid&#101;nce/gates/` THIẾU, `evid&#101;nce/reviews/T220.verdict` THIẾU; capture E2E: `evid&#101;nce/e2e/` THIẾU.
- [x] AC-2 — Rollout seeded có observation đúng chiều, hữu hạn và trong cận; THIẾU test entrypoint và mọi tệp nêu chưa có. Task: T205, T206, T207, T210, T211, T214, T218. Test: `tests/e2e/test_env_acceptance.py` (entrypoint, `test_ac_2_random_rollout_clean`); `tests/integration/test_env_rollout.py`, `tests/integration/test_headless.py`, `tests/integration/test_env_episode_end.py` (unit). Bằng chứng máy: `evid&#101;nce/gates/` THIẾU; capture E2E: `evid&#101;nce/e2e/` THIẾU.
- [x] AC-3 — Cùng seed cho cùng tập mục tiêu và train ∩ test = ∅; THIẾU test entrypoint và mọi tệp nêu chưa có. Task: T204, T212, T213, T217, T218. Test: `tests/e2e/test_env_acceptance.py` (entrypoint, `test_ac_3_same_seed_disjoint_sets`); `tests/integration/test_target_determinism.py`, `tests/integration/test_env_split.py`, `tests/integration/test_contract_examples_m1.py` (unit). Bằng chứng máy: `evid&#101;nce/gates/` THIẾU; capture E2E: `evid&#101;nce/e2e/` THIẾU.
- [x] AC-4 — Không position controller thay cơ và lực cơ do mô hình tính; THIẾU test entrypoint và mọi tệp nêu chưa có. Task: T207, T209, T218. Test: `tests/e2e/test_env_acceptance.py` (entrypoint, `test_ac_4_no_position_controller`); `tests/integration/test_control_structure.py` (unit). Bằng chứng máy: `evid&#101;nce/gates/` THIẾU; capture E2E: `evid&#101;nce/e2e/` THIẾU.
- [x] AC-5 — Cài và chạy trong môi trường ảo sạch, có lý do quyết định phiên bản; THIẾU test entrypoint và mọi tệp nêu chưa có. Task: T201, T215, T216, T218, T220. Test: `tests/e2e/test_env_acceptance.py` (entrypoint, `test_ac_5_clean_install`); `tests/unit/test_verify_clean_install.py`, `tests/integration/test_dependency_decision.py` (unit). Bằng chứng máy: `evid&#101;nce/gates/` THIẾU, `logs/m1/verify_clean_install.json` THIẾU, `evid&#101;nce/reviews/T220.verdict` THIẾU; capture E2E: `evid&#101;nce/e2e/` THIẾU.
- [x] INV-001 — Train/test rời nhau, cách tối thiểu và chế độ test không chọn train; THIẾU test entrypoint. Task: T204, T212, T213, T219. Test: `tests/integration/test_target_determinism.py`, `tests/integration/test_env_split.py`, `tests/challenge/test_env_invariants.py` (unit; các tệp đều THIẾU). Bằng chứng máy: `evid&#101;nce/gates/` THIẾU, `evid&#101;nce/reviews/T219.challenge` THIẾU; capture E2E: `evid&#101;nce/e2e/` THIẾU.
- [x] INV-002 — Cùng seed và cấu hình cho danh sách/chọn mục tiêu giống nhau; THIẾU test entrypoint. Task: T204, T212, T213, T219. Test: `tests/integration/test_target_determinism.py`, `tests/integration/test_env_split.py`, `tests/challenge/test_env_invariants.py` (unit; các tệp đều THIẾU). Bằng chứng máy: `evid&#101;nce/gates/` THIẾU, `evid&#101;nce/reviews/T219.challenge` THIẾU; capture E2E: `evid&#101;nce/e2e/` THIẾU.
- [x] INV-003 — Chỉ kích thích cơ điều khiển mô hình, không actuator khác cơ hay ghi trực tiếp lực/toạ độ; THIẾU test entrypoint. Task: T207, T209, T219. Test: `tests/integration/test_control_structure.py`, `tests/challenge/test_env_invariants.py` (unit; các tệp đều THIẾU). Bằng chứng máy: `evid&#101;nce/gates/` THIẾU, `evid&#101;nce/reviews/T219.challenge` THIẾU; capture E2E: `evid&#101;nce/e2e/` THIẾU.
- [x] INV-004 — Observation trả ra đúng chiều, hữu hạn và trong cận hoặc nêu lỗi rõ; THIẾU test entrypoint. Task: T205, T207, T210, T219. Test: `tests/unit/test_observation.py`, `tests/integration/test_env_rollout.py`, `tests/challenge/test_env_invariants.py` (unit; các tệp đều THIẾU). Bằng chứng máy: `evid&#101;nce/gates/` THIẾU, `evid&#101;nce/reviews/T219.challenge` THIẾU; capture E2E: `evid&#101;nce/e2e/` THIẾU.
- [x] NFR-REL-001 — Rollout ≥ 10 episode có 0 NaN và 0 Inf; THIẾU test entrypoint và mọi tệp nêu chưa có. Task: T210, T218. Test: `tests/e2e/test_env_acceptance.py` (entrypoint, `test_ac_2_random_rollout_clean`); `tests/integration/test_env_rollout.py` (unit). Bằng chứng máy: `evid&#101;nce/gates/` THIẾU; capture E2E: `evid&#101;nce/e2e/` THIẾU.
- [x] NFR-REPRO-001 — Hai lần sinh cùng seed/config không khác biệt và giao train ∩ test có 0 phần tử; THIẾU test entrypoint và mọi tệp nêu chưa có. Task: T204, T212, T218. Test: `tests/e2e/test_env_acceptance.py` (entrypoint, `test_ac_3_same_seed_disjoint_sets`); `tests/unit/test_targets.py`, `tests/integration/test_target_determinism.py` (unit). Bằng chứng máy: `evid&#101;nce/gates/` THIẾU; capture E2E: `evid&#101;nce/e2e/` THIẾU.
- [x] NFR-HEADLESS-001 — Tạo, reset và step không `DISPLAY` với mã thoát 0; THIẾU test entrypoint và mọi tệp nêu chưa có. Task: T211, T218. Test: `tests/e2e/test_env_acceptance.py` (entrypoint, `test_ac_2_random_rollout_clean`); `tests/integration/test_headless.py` (unit). Bằng chứng máy: `evid&#101;nce/gates/` THIẾU; capture E2E: `evid&#101;nce/e2e/` THIẾU.
- [x] NFR-INST-001 — `uv sync` và bộ test xanh trong môi trường ảo mới; THIẾU test entrypoint và mọi tệp nêu chưa có. Task: T201, T215, T216, T218. Test: `tests/e2e/test_env_acceptance.py` (entrypoint, `test_ac_5_clean_install`); `tests/unit/test_verify_clean_install.py`, `tests/integration/test_dependency_decision.py` (unit). Bằng chứng máy: `evid&#101;nce/gates/` THIẾU, `logs/m1/verify_clean_install.json` THIẾU; capture E2E: `evid&#101;nce/e2e/` THIẾU.
