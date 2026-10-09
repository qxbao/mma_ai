---
id: "TRACE-002"
title: "Ma trận truy vết 002-elbow-muscle-env"
doc_type: tracing
owner_agent: spec
status: draft
updated: "2026-10-09"
---

# Ma trận truy vết 002-elbow-muscle-env

- [Ma trận](#ma-tran)
- [Truy vết ngược: task → mã](#truy-vet-nguoc-task-ma)
- [Chưa truy vết được](#chua-truy-vet-duoc)

> Đích: `docs/05-tracing/trace/002-elbow-muscle-env.md` (`trace-matrix.md` là chỉ mục máy sinh, không sửa tay). Nguồn: `specs/002-elbow-muscle-env/spec.md` (yêu cầu) và `specs/002-elbow-muscle-env/tasks.md` (task `T201`…`T220`).
> Mức `entrypoint` = test chạy qua điểm vào công khai thật của feature — `gymnasium.make("MmaElbowReach-v0")` trong một tiến trình Python mới (subprocess, `DISPLAY` bỏ đặt) hoặc `python -m mma_ai.environment.verify_clean_install`; feature không có CLI nghiệp vụ hay điểm gọi mạng. Mức `integration` = test qua API công khai trong tiến trình test trên mô hình MuJoCo thật; mức `unit` = test mô-đun đơn lẻ. Tên hàm test là tên dự kiến theo `tasks.md`; chưa có mã nên cột trạng thái ghi "có" nghĩa là đã có task + test dự kiến, KHÔNG có nghĩa test đã chạy xanh.

<a id="ma-tran"></a>
## Ma trận

| Mã | Yêu cầu (spec.md) | Task (tasks.md) | Test / cổng máy | Mức | Trạng thái |
|---|---|---|---|---|---|
| AC-1 | Cho mô hình MyoElbow, nạp môi trường thì có đúng 6 muscle actuators, action space `[0,1]^6`, hash SHA-256 của XML và tên 6 cơ trong thông tin môi trường | T202, T207, T208, T213, T217, T218, T220 | `tests/e2e/test_env_acceptance.py::test_ac_1_six_muscles_unit_box`, `tests/integration/test_elbow_env.py::test_loads_exactly_six_muscles`, `tests/integration/test_elbow_env.py::test_action_space_is_unit_box_6`, `tests/integration/test_elbow_env.py::test_model_sha256_in_info`, `tests/integration/test_elbow_env.py::test_rejects_model_without_six_muscles` | entrypoint | có |
| AC-2 | Cho môi trường đã reset với seed, chạy episode hành động ngẫu nhiên thì observation đúng chiều, không NaN/Inf, không ngoài khoảng; reward hữu hạn; terminated/truncated phân biệt | T205, T206, T207, T210, T211, T214, T218 | `tests/e2e/test_env_acceptance.py::test_ac_2_random_rollout_clean`, `tests/integration/test_env_rollout.py::test_random_rollout_no_nan_inf`, `tests/integration/test_env_rollout.py::test_extreme_actions_stay_in_bounds`, `tests/integration/test_headless.py::test_runs_without_display`, `tests/integration/test_env_episode_end.py::test_terminated_on_reach`, `tests/integration/test_env_episode_end.py::test_truncated_at_max_actions` | entrypoint | có |
| AC-3 | Cho cùng seed, sinh tập mục tiêu hai lần thì giống nhau; tập train ∩ tập test = ∅ | T204, T212, T213, T217, T218 | `tests/e2e/test_env_acceptance.py::test_ac_3_same_seed_disjoint_sets`, `tests/integration/test_target_determinism.py::test_same_seed_same_sets`, `tests/integration/test_target_determinism.py::test_train_test_disjoint`, `tests/integration/test_env_split.py::test_test_split_never_samples_train` | entrypoint | có |
| AC-4 | Cho cấu hình đúng, quan sát cấu trúc điều khiển thì không có position controller thay cơ; lực cơ do mô hình tính | T207, T209, T218 | `tests/e2e/test_env_acceptance.py::test_ac_4_no_position_controller`, `tests/integration/test_control_structure.py::test_all_actuators_are_muscle`, `tests/integration/test_control_structure.py::test_only_ctrl_written_per_step` | entrypoint | có |
| AC-5 | Cho môi trường ảo sạch, cài theo quyết định phiên bản thì cài và chạy được; lý do chọn được ghi lại | T201, T215, T216, T218, T220 | `tests/e2e/test_env_acceptance.py::test_ac_5_clean_install`, `tests/integration/test_dependency_decision.py::test_decision_recorded_in_research_q1`, `tests/unit/test_verify_clean_install.py::test_record_has_all_fields` | entrypoint | có |
| SC-001 | Môi trường nạp mô hình với đúng 6 muscle actuators, action space `[0,1]^6`, chạy headless với 0 NaN/Inf trong rollout kiểm thử | T208, T210, T211, T218 | `tests/e2e/test_env_acceptance.py::test_ac_1_six_muscles_unit_box`, `tests/integration/test_headless.py::test_runs_without_display`, `tests/integration/test_env_rollout.py::test_random_rollout_no_nan_inf` | entrypoint | có |
| SC-002 | Observation/action có chiều và miền giá trị xác định, kiểm tự động chiều, NaN, ngoài khoảng, 0 vi phạm | T205, T210, T218 | `tests/integration/test_env_rollout.py::test_random_rollout_no_nan_inf`, `tests/unit/test_observation.py::test_layout_is_14_with_finite_bounds`, `tests/e2e/test_env_acceptance.py::test_ac_2_random_rollout_clean` | entrypoint | có |
| SC-003 | Tập train/test sinh theo seed, hai lần cùng seed giống nhau và giao rỗng, kiểm được bằng test | T204, T212, T218 | `tests/integration/test_target_determinism.py::test_same_seed_same_sets`, `tests/integration/test_target_determinism.py::test_train_test_disjoint`, `tests/e2e/test_env_acceptance.py::test_ac_3_same_seed_disjoint_sets` | entrypoint | có |
| SC-004 | Không có position controller thay cơ; lực cơ do mô hình tính, kiểm bằng test cấu trúc điều khiển | T209, T218 | `tests/integration/test_control_structure.py::test_all_actuators_are_muscle`, `tests/e2e/test_env_acceptance.py::test_ac_4_no_position_controller` | entrypoint | có |
| SC-005 | Có quyết định phiên bản `gymnasium`/`myosuite` ghi rõ lý do và chứng minh cài được trong môi trường ảo sạch | T216, T218 | `tests/integration/test_dependency_decision.py::test_myosuite_absent_from_pyproject_and_lock`, `tests/e2e/test_env_acceptance.py::test_ac_5_clean_install` | entrypoint | có |
| API-002 | Hợp đồng API Python `contracts/python-api.md`: `ElbowEnvConfig.load`, `TargetGenerator.generate`, `ElbowReachEnv`, `reset`, `step`, `model_record`, `make_env`, `register_envs` và khuôn JSON của các bản ghi | T203, T204, T207, T217 | `tests/integration/test_contract_examples_m1.py::test_all_examples_valid_against_schemas`, `tests/integration/test_contract_examples_m1.py::test_reset_and_step_info_real_output_valid`, `tests/unit/test_single_agent_state.py::test_registered_id_makes_env` | integration | có |
| FR-001 | Nạp MyoElbow qua MuJoCo, xác nhận đúng 6 muscle actuators; từ chối khi số cơ ≠ 6 hoặc có actuator không phải cơ | T207, T208 | `tests/integration/test_elbow_env.py::test_loads_exactly_six_muscles`, `tests/integration/test_elbow_env.py::test_rejects_model_without_six_muscles` | integration | có |
| FR-002 | Môi trường một agent theo Gymnasium trong `single_agent.py`, headless, không pixel observation | T202, T207, T208, T211 | `tests/integration/test_elbow_env.py::test_gymnasium_check_env`, `tests/integration/test_headless.py::test_runs_without_display`, `tests/unit/test_single_agent_state.py::test_registered_id_makes_env` | entrypoint | có |
| FR-003 | Action space `u ∈ [0,1]^6`; từ chối hành động sai kích thước, NaN/Inf, ngoài `[0,1]` kèm thông báo nêu giá trị | T202, T207, T208, T210 | `tests/integration/test_elbow_env.py::test_action_space_is_unit_box_6`, `tests/integration/test_env_rollout.py::test_rejects_invalid_actions` | integration | có |
| FR-004 | Chỉ nhận kích thích cơ; không position controller/joint motor, không ghi trực tiếp lực/góc khớp/toạ độ tay; lực cơ do MuJoCo tính | T207, T209 | `tests/integration/test_control_structure.py::test_all_actuators_are_muscle`, `tests/integration/test_control_structure.py::test_state_not_written_outside_mj_step`, `tests/integration/test_control_structure.py::test_no_public_state_writer_api` | integration | có |
| FR-005 | Observation gồm góc khớp, vận tốc khớp, kích hoạt từng cơ, vị trí đầu mút tay, vị trí mục tiêu; 14 chiều, cận hữu hạn, đã chuẩn hoá | T205, T210 | `tests/unit/test_observation.py::test_layout_is_14_with_finite_bounds`, `tests/unit/test_observation.py::test_normalisation_matches_bounds`, `tests/integration/test_env_rollout.py::test_random_rollout_no_nan_inf` | unit | có |
| FR-006 | Kiểm observation trước khi trả (chiều, NaN/Inf, cận); báo lỗi rõ khi mô phỏng mất ổn định | T202, T205, T207, T210 | `tests/unit/test_observation.py::test_rejects_out_of_bounds`, `tests/unit/test_observation.py::test_rejects_wrong_shape_and_nan_inf`, `tests/integration/test_env_rollout.py::test_physics_instability_raises` | integration | có |
| FR-007 | Bộ kiểm tự động chiều, NaN/Inf, ngoài khoảng của observation/action trên rollout ngẫu nhiên có seed | T210 | `tests/integration/test_env_rollout.py::test_random_rollout_no_nan_inf`, `tests/integration/test_env_rollout.py::test_same_seed_same_rollout` | integration | có |
| FR-008 | Reward gồm thành phần tiến tới mục tiêu và thành phần phạt kích hoạt/nỗ lực, trọng số cấu hình được, hữu hạn mọi bước | T206, T214 | `tests/unit/test_reward.py::test_closer_is_better`, `tests/unit/test_reward.py::test_effort_penalty_scales_and_zero_weight`, `tests/unit/test_reward.py::test_reward_finite`, `tests/integration/test_env_episode_end.py::test_reward_components_in_info_and_weights_configurable` | unit | có |
| FR-009 | Episode terminated khi khoảng cách ≤ dung sai, truncated khi đạt số hành động tối đa; phân biệt được ở đầu ra `step` | T206, T207, T214 | `tests/integration/test_env_episode_end.py::test_terminated_on_reach`, `tests/integration/test_env_episode_end.py::test_truncated_at_max_actions`, `tests/integration/test_env_episode_end.py::test_terminated_wins_on_tie` | integration | có |
| FR-010 | Bộ sinh mục tiêu sinh mục tiêu với tới được, tất định theo seed | T204, T212 | `tests/unit/test_targets.py::test_all_targets_reachable`, `tests/unit/test_targets.py::test_same_seed_same_fingerprint`, `tests/integration/test_target_determinism.py::test_same_seed_same_sets` | integration | có |
| FR-011 | Sinh hai tập train/test từ một seed với giao rỗng và khoảng cách tối thiểu cấu hình được; kích thước cấu hình được | T204, T212, T217 | `tests/unit/test_targets.py::test_min_separation`, `tests/unit/test_targets.py::test_infeasible_config_raises`, `tests/integration/test_target_determinism.py::test_train_test_disjoint`, `tests/integration/test_contract_examples_m1.py::test_target_set_real_output_valid` | integration | có |
| FR-012 | Chọn nguồn mục tiêu train hoặc test, không bao giờ bốc tập kia; `reset` báo tập nguồn, chỉ số, seed thực dùng | T207, T213, T217 | `tests/integration/test_env_split.py::test_test_split_never_samples_train`, `tests/integration/test_env_split.py::test_reset_info_fields`, `tests/integration/test_env_split.py::test_reset_seed_none_records_seed` | integration | có |
| FR-013 | Tính hash SHA-256 của XML mô hình đã nạp và đưa vào thông tin môi trường | T207, T208, T217 | `tests/integration/test_elbow_env.py::test_model_sha256_in_info`, `tests/integration/test_contract_examples_m1.py::test_model_record_real_output_valid` | integration | có |
| FR-014 | Mọi tham số ở một cấu hình duy nhất; bước vật lý đặt qua cấu hình, không sửa XML | T203, T208, T214, T217 | `tests/unit/test_env_config.py::test_defaults_load`, `tests/unit/test_env_config.py::test_invalid_values_raise`, `tests/integration/test_elbow_env.py::test_timestep_set_without_editing_xml`, `tests/integration/test_contract_examples_m1.py::test_env_config_default_valid` | unit | có |
| FR-015 | Có quyết định phiên bản `gymnasium`/`myosuite` ghi rõ phương án chọn, loại, lý do, bằng chứng cài thật | T201, T216, T220 | `tests/integration/test_dependency_decision.py::test_decision_recorded_in_research_q1`, `tests/integration/test_dependency_decision.py::test_myosuite_absent_from_pyproject_and_lock`, `tests/unit/test_env_packaging.py::test_myosuite_absent` | integration | có |
| FR-016 | Cài và chạy được trong môi trường ảo sạch; khoá lockfile chỉ sau khi smoke test đạt | T201, T215, T216, T220 | `tests/unit/test_verify_clean_install.py::test_exit_nonzero_when_sync_fails`, `tests/integration/test_dependency_decision.py::test_lock_matches_pyproject_constraints`, `tests/e2e/test_env_acceptance.py::test_ac_5_clean_install` | entrypoint | có |
| NFR-REL-001 | 0 NaN và 0 Inf trong observation, reward, trạng thái mô phỏng trên rollout ≥ 10 episode hành động ngẫu nhiên có seed; đo bằng `python -m pytest` | T210, T218 | `tests/integration/test_env_rollout.py::test_random_rollout_no_nan_inf`, `tests/e2e/test_env_acceptance.py::test_ac_2_random_rollout_clean` | entrypoint | có |
| NFR-REPRO-001 | 0 khác biệt giữa hai lần sinh tập mục tiêu cùng seed và cấu hình; giao train ∩ test có 0 phần tử | T204, T212, T218 | `tests/integration/test_target_determinism.py::test_same_seed_same_sets`, `tests/integration/test_target_determinism.py::test_train_test_disjoint`, `tests/e2e/test_env_acceptance.py::test_ac_3_same_seed_disjoint_sets` | entrypoint | có |
| NFR-HEADLESS-001 | Tạo, reset, bước được khi `DISPLAY` bỏ đặt với mã thoát 0 | T211, T218 | `tests/integration/test_headless.py::test_runs_without_display`, `tests/integration/test_headless.py::test_no_viewer_or_pixel_import` | entrypoint | có |
| NFR-INST-001 | Lệnh cài theo lockfile (`uv sync`) mã thoát 0 và bộ test của môi trường xanh trong môi trường ảo mới | T201, T215, T216, T218 | `tests/e2e/test_env_acceptance.py::test_ac_5_clean_install`, `tests/unit/test_verify_clean_install.py::test_refuses_without_lockfile` | entrypoint | có |
| INV-001 | Tập train và test giao rỗng, mọi cặp cách nhau ≥ khoảng cách tối thiểu > 0; chế độ test không bao giờ chọn mục tiêu train | T204, T212, T213, T219 | `tests/integration/test_target_determinism.py::test_train_test_disjoint`, `tests/integration/test_env_split.py::test_test_split_never_samples_train`, `tests/challenge/test_env_invariants.py` | integration | có |
| INV-002 | Cùng seed và cấu hình ⇒ danh sách mục tiêu từng tập và mục tiêu chọn ở `reset(seed)` giống nhau giữa các lần chạy | T204, T212, T213, T219 | `tests/integration/test_target_determinism.py::test_same_seed_same_sets`, `tests/integration/test_target_determinism.py::test_reset_same_seed_same_target`, `tests/challenge/test_env_invariants.py` | integration | có |
| INV-003 | Đường điều khiển duy nhất là kích thích cơ; mọi actuator là muscle actuator; policy không điều khiển trực tiếp lực hay toạ độ tay | T207, T209, T219 | `tests/integration/test_control_structure.py::test_all_actuators_are_muscle`, `tests/integration/test_control_structure.py::test_no_public_state_writer_api`, `tests/challenge/test_env_invariants.py` | integration | có |
| INV-004 | Mọi observation trả ra đúng chiều, hữu hạn, trong cận; observation vi phạm bị chặn bằng lỗi rõ | T205, T207, T210, T219 | `tests/unit/test_observation.py::test_rejects_out_of_bounds`, `tests/integration/test_env_rollout.py::test_extreme_actions_stay_in_bounds`, `tests/challenge/test_env_invariants.py` | integration | có |

<a id="truy-vet-nguoc-task-ma"></a>
## Truy vết ngược: task → mã

| Task | Mã hiện thực |
|---|---|
| T201 | FR-015 · FR-016 · NFR-INST-001 |
| T202 | FR-002 · FR-003 · FR-006 |
| T203 | FR-014 · API-002 |
| T204 | FR-010 · FR-011 · INV-001 · INV-002 · NFR-REPRO-001 · API-002 |
| T205 | FR-005 · FR-006 · INV-004 |
| T206 | FR-008 · FR-009 |
| T207 | FR-001 · FR-002 · FR-003 · FR-004 · FR-006 · FR-009 · FR-012 · FR-013 · INV-003 · INV-004 · API-002 |
| T208 | FR-001 · FR-002 · FR-003 · FR-013 · FR-014 · AC-1 · SC-001 |
| T209 | FR-004 · INV-003 · AC-4 · SC-004 |
| T210 | FR-003 · FR-005 · FR-006 · FR-007 · INV-004 · NFR-REL-001 · AC-2 · SC-002 |
| T211 | FR-002 · NFR-HEADLESS-001 · AC-2 |
| T212 | FR-010 · FR-011 · INV-001 · INV-002 · NFR-REPRO-001 · AC-3 · SC-003 |
| T213 | FR-012 · INV-001 · INV-002 · AC-3 |
| T214 | FR-008 · FR-009 · FR-014 · AC-2 |
| T215 | FR-016 · NFR-INST-001 · AC-5 |
| T216 | FR-015 · FR-016 · NFR-INST-001 · AC-5 · SC-005 |
| T217 | FR-011 · FR-012 · FR-013 · FR-014 · API-002 · AC-1 · AC-3 |
| T218 | AC-1 · AC-2 · AC-3 · AC-4 · AC-5 · SC-001 · SC-002 · SC-003 · SC-004 · SC-005 · NFR-REL-001 · NFR-REPRO-001 · NFR-HEADLESS-001 · NFR-INST-001 |
| T219 | INV-001 · INV-002 · INV-003 · INV-004 |
| T220 | AC-1 · AC-5 · FR-015 · FR-016 |

<a id="chua-truy-vet-duoc"></a>
## Chưa truy vết được

- Không mã nào của spec thiếu task hoặc test dự kiến. Các điểm cần theo dõi ở bước converge/`plan_fix`:
  - **Phụ thuộc vào 001 (M0)**: 001 chưa có `tasks.md` nên cột `depends_on` của T201, T203, T204, T205, T207, T217 chưa trỏ được tới task của 001 (chỉ T201 → T501); việc thêm `depends_on` do bước converge/`plan_fix` khi 001 có `tasks.md` (xem `specs/002-elbow-muscle-env/tasks.md`, mục "Phụ thuộc chéo feature"). Test của 002 chạy được chỉ khi 001 giao mã `mma_ai.physics`.
  - **Vỏ script và cấu hình mẫu chưa có chủ**: `scripts/verify_clean_install.py`, `configs/elbow_env.yaml`, `tests/regression/` và dòng `logs/` trong `.gitignore` ngoài vùng ghi của mọi vai; entrypoint thật của AC-5 tạm là `python -m mma_ai.environment.verify_clean_install` (đã nêu đề xuất `ai-sdlc capability propose` ở `tasks.md`).
  - **Chiều ngược lại**: các task của 003/004/005 chạm `pyproject.toml` hoặc `single_agent.py` cần `depends_on` T201/T207 (xem `tasks.md`); chưa sửa vì ngoài phạm vi tệp của feature này.
  - **AC-5 đòi mạng/cache `uv`**: `test_ac_5_clean_install` chạy cài thật nên chỉ xanh trên máy có `uv` và nguồn gói; chưa chạy cho tới khi triển khai.
