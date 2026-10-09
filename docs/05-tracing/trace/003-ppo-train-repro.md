---
id: "TRACE-003"
title: "Ma trận truy vết 003-ppo-train-repro"
doc_type: tracing
owner_agent: spec
status: draft
updated: "2026-10-09"
---

# Ma trận truy vết 003-ppo-train-repro

- [Ma trận](#ma-tran)
- [Truy vết ngược: task → mã](#truy-vet-nguoc-task-ma)
- [Chưa truy vết được](#chua-truy-vet-duoc)

> Đích: `docs/05-tracing/trace/003-ppo-train-repro.md` (`trace-matrix.md` là chỉ mục máy sinh, không sửa tay). Nguồn: `specs/003-ppo-train-repro/spec.md` (yêu cầu) và `specs/003-ppo-train-repro/tasks.md` (task `T301`…`T339`).
> Mức `entrypoint` = test chạy qua lệnh CLI thật `python -m mma_ai.learning.cli` / `python -m mma_ai.monitoring.cli` (subprocess; vỏ `python scripts/train.py` chưa có chủ — xem cuối tệp), qua điểm HTTP loopback thật hoặc e2e; mức `unit` = test mô-đun đơn lẻ. Tên hàm test là tên dự kiến theo `tasks.md`; chưa có mã nên cột trạng thái ghi "có" nghĩa là đã có task + test dự kiến, KHÔNG có nghĩa test đã chạy xanh.

<a id="ma-tran"></a>
## Ma trận

| Mã | Yêu cầu (spec.md) | Task (tasks.md) | Test / cổng máy | Mức | Trạng thái |
|---|---|---|---|---|---|
| AC-1 | Cho môi trường xanh, chạy `train.py --stage elbow --seed 42` thì huấn luyện chạy được, ghi log TensorBoard và checkpoint định kỳ (smoke ≤ 4 096 bước, mã 0, 0 NaN/Inf) | T303, T309, T310, T311, T314, T319, T322, T323, T324, T325, T337 | `tests/integration/test_train_cli.py::test_smoke_train_exit0`, `tests/integration/test_train_cli.py::test_tensorboard_scalars_present`, `tests/integration/test_train_cli.py::test_periodic_and_final_checkpoint`, `tests/integration/test_train_headless.py::test_zero_nan_inf_counters_in_manifest`, `tests/e2e/test_train_acceptance.py::test_ac_1_train_smoke` | entrypoint | có |
| AC-2 | Cho checkpoint đã lưu, nạp lại thì policy cho cùng hành động xác định trên cùng observation mẫu và train tiếp được | T311, T314, T319, T327, T337 | `tests/integration/test_resume.py::test_roundtrip_via_cli_same_action`, `tests/integration/test_resume.py::test_resume_creates_new_run_with_parent`, `tests/integration/test_resume.py::test_resume_restores_normalizer_optimizer_rng`, `tests/unit/test_checkpoint.py::test_roundtrip_same_action`, `tests/e2e/test_train_acceptance.py::test_ac_2_checkpoint_roundtrip_and_resume` | entrypoint | có |
| AC-3 | Cho một run xong, mở thư mục run thì có seed, config, phiên bản thư viện, hash XML, checkpoint, reward metrics | T305, T306, T312, T328, T329, T337 | `tests/integration/test_manifest_contract.py::test_manifest_fields_and_schema`, `tests/integration/test_manifest_contract.py::test_two_runs_two_dirs`, `tests/integration/test_manifest_contract.py::test_manifest_hash_matches_env_model_record`, `tests/e2e/test_train_acceptance.py::test_ac_3_run_manifest_fields` | entrypoint | có |
| AC-4 | Cho hai run cùng seed/cấu hình, so sánh thì kết quả nằm trong dung sai tái lập đã khai | T313, T318, T330, T337 | `tests/integration/test_train_determinism.py::test_same_seed_head_curve_within_tolerance`, `tests/integration/test_train_determinism.py::test_diff_seed_differs`, `tests/integration/test_train_determinism.py::test_compare_cli_exit0_within_tolerance`, `tests/e2e/test_train_acceptance.py::test_ac_4_same_seed_within_tolerance` | entrypoint | có |
| AC-5 | Cho `--stage balance` (hoặc stage chưa hỗ trợ), gọi CLI thì báo rõ "chưa triển khai", mã thoát khác 0, không tạo thư mục run | T319, T336, T337 | `tests/integration/test_train_stage.py::test_stage_not_implemented_exit3`, `tests/integration/test_train_stage.py::test_no_run_dir_for_unimplemented`, `tests/e2e/test_train_acceptance.py::test_ac_5_stage_not_implemented` | entrypoint | có |
| AC-6 | Cho cấu hình MLP, kiểm tra mạng thì actor và critic đều 2 lớp × 256, có chuẩn hoá observation và gradient clipping | T309, T310, T335, T337 | `tests/integration/test_network_config.py::test_actor_critic_2x256_from_default_config`, `tests/integration/test_network_config.py::test_normalizer_and_clipping_present`, `tests/unit/test_networks.py::test_actor_critic_2x256`, `tests/e2e/test_train_acceptance.py::test_ac_6_network_2x256` | entrypoint | có |
| AC-7 | Trong lúc train chạy, giao diện quan sát hiện reward, loss, kích hoạt 6 cơ, env steps/s, số bước / tổng, trạng thái checkpoint; cập nhật ≤ 5 s; chỉ đọc; bật giao diện giảm env steps/s ≤ 10% | T308, T315, T316, T317, T320, T331, T333, T334, T337 | `tests/integration/test_dashboard_resilience.py::test_dashboard_during_train_shows_required_fields`, `tests/integration/test_dashboard_resilience.py::test_train_survives_ui_failure`, `tests/integration/test_dashboard.py::test_dashboard_is_read_only`, `tests/integration/test_dashboard.py::test_snapshot_latency_le_5s`, `tests/integration/test_benchmark_train.py::test_benchmark_schema_and_ratio`, `tests/e2e/test_train_acceptance.py::test_ac_7_progress_ui_live` | entrypoint | có |
| KQ-1 | Lệnh train chạy hết một lượt smoke không lỗi, 0 NaN/Inf trong loss và tham số | T322, T323 | `tests/integration/test_train_cli.py::test_smoke_train_exit0`, `tests/integration/test_train_headless.py::test_zero_nan_inf_counters_in_manifest` | entrypoint | có |
| KQ-2 | Checkpoint lưu định kỳ; nạp lại cho policy cùng hành động (trong dung sai) trên cùng observation | T311, T327 | `tests/integration/test_resume.py::test_roundtrip_via_cli_same_action`, `tests/unit/test_checkpoint.py::test_roundtrip_same_action` | entrypoint | có |
| KQ-3 | Mỗi lần chạy lưu đủ seed, config, phiên bản thư viện, hash XML, checkpoint, reward metrics | T312, T328 | `tests/integration/test_manifest_contract.py::test_manifest_fields_and_schema` | entrypoint | có |
| KQ-4 | Cùng seed + cùng cấu hình ⇒ đường reward đầu kỳ giống nhau trong dung sai đã khai | T313, T330 | `tests/integration/test_train_determinism.py::test_same_seed_head_curve_within_tolerance` | entrypoint | có |
| FR-001 | Lệnh `train.py --stage elbow --seed 42` chạy PPO hành động liên tục; `--seed` điều khiển mọi nguồn ngẫu nhiên | T313, T314, T319, T322, T330 | `tests/integration/test_train_cli.py::test_smoke_train_exit0`, `tests/unit/test_repro.py::test_seed_everything_same_draws` | entrypoint | có |
| FR-002 | Actor MLP 2×256, critic MLP 2×256, chuẩn hoá observation, gradient clipping; cấu trúc ở cấu hình | T303, T309, T310, T335 | `tests/unit/test_networks.py::test_actor_critic_2x256`, `tests/unit/test_networks.py::test_custom_structure_follows_config`, `tests/integration/test_network_config.py::test_actor_critic_2x256_from_default_config` | unit | có |
| FR-003 | Bộ chuẩn hoá observation ước lượng lúc train, áp trước actor/critic, thống kê nằm trong checkpoint | T304, T314, T335 | `tests/unit/test_normalizer.py::test_matches_numpy_stats`, `tests/unit/test_normalizer.py::test_state_dict_roundtrip`, `tests/integration/test_resume.py::test_resume_restores_normalizer_optimizer_rng` | unit | có |
| FR-004 | Gradient clipping ở mỗi bước cập nhật, chuẩn gradient sau clipping không vượt ngưỡng | T310, T335 | `tests/unit/test_ppo.py::test_grad_norm_after_clip_le_threshold`, `tests/integration/test_network_config.py::test_normalizer_and_clipping_present` | unit | có |
| FR-005 | Hành động vào môi trường là kích thích cơ u ∈ [0,1] cho 6 cơ; không điều khiển lực/toạ độ tay, không position controller | T309, T314, T322 | `tests/integration/test_train_cli.py::test_actions_in_unit_interval`, `tests/unit/test_networks.py::test_action_always_in_unit_interval` | entrypoint | có |
| FR-006 | Checkpoint định kỳ theo tần số cấu hình (mặc định mỗi 10 lượt), đủ actor, critic, bộ chuẩn hoá, optimizer, seed, RNG, hash XML, phiên bản | T311, T314, T322 | `tests/integration/test_train_cli.py::test_periodic_and_final_checkpoint`, `tests/unit/test_trainer.py::test_checkpoint_cadence` | entrypoint | có |
| FR-007 | Ghi checkpoint trọn vẹn rồi mới công bố mới nhất; không ghi đè checkpoint cũ; không ghi checkpoint chứa NaN/Inf | T311, T325 | `tests/unit/test_checkpoint.py::test_atomic_write_no_partial`, `tests/unit/test_checkpoint.py::test_nan_not_written`, `tests/unit/test_checkpoint.py::test_old_checkpoints_not_overwritten`, `tests/integration/test_train_nan_guard.py::test_nan_loss_stops_without_checkpoint` | entrypoint | có |
| FR-008 | Nạp checkpoint để suy luận hoặc train tiếp; cùng hành động trong dung sai; hỏng/thiếu/khác cấu trúc thì báo lỗi nêu nguyên nhân | T311, T327 | `tests/unit/test_checkpoint.py::test_missing_component_raises`, `tests/unit/test_checkpoint.py::test_shape_mismatch_raises`, `tests/integration/test_resume.py::test_corrupt_checkpoint_exit4_names_cause` | entrypoint | có |
| FR-009 | Train tiếp khôi phục optimizer, bộ chuẩn hoá, RNG và tạo run mới ghi run/checkpoint cha | T311, T314, T319, T327 | `tests/integration/test_resume.py::test_resume_creates_new_run_with_parent`, `tests/integration/test_resume.py::test_resume_refused_when_xml_hash_differs` | entrypoint | có |
| FR-010 | Log TensorBoard gồm loss, reward, activation 6 cơ theo bước đủ cho con 3 vẽ biểu đồ | T307, T314, T322 | `tests/integration/test_train_cli.py::test_tensorboard_scalars_present`, `tests/unit/test_metrics_log.py::test_activation_tags_for_six_muscles` | entrypoint | có |
| FR-011 | Mỗi lần chạy một thư mục run mới, duy nhất, chứa hồ sơ theo JSON Schema; không ghi đè run cũ | T305, T312, T328 | `tests/unit/test_run_dir.py::test_unique_dirs_no_overwrite`, `tests/integration/test_manifest_contract.py::test_manifest_fields_and_schema`, `tests/integration/test_manifest_contract.py::test_two_runs_two_dirs` | entrypoint | có |
| FR-012 | Hồ sơ ghi loại thiết bị và tài nguyên CPU, RAM, GPU/VRAM; trường không áp dụng ghi `null` | T306, T312, T328 | `tests/integration/test_manifest_contract.py::test_resources_fields_null_explicit`, `tests/unit/test_resources.py::test_resource_fields_present_null_without_gpu` | entrypoint | có |
| FR-013 | Báo cáo env steps/second và wall-clock do máy đo, không suy ra từ số khác | T306, T314, T319, T322 | `tests/integration/test_train_cli.py::test_report_has_steps_per_second_and_wallclock`, `tests/unit/test_resources.py::test_throughput_and_wallclock_measured` | entrypoint | có |
| FR-014 | Hồ sơ ghi dung sai và loại thiết bị; phép so sánh hai run theo dung sai chỉ có nghĩa cùng loại thiết bị | T312, T313, T318, T330 | `tests/unit/test_repro.py::test_compare_within_tolerance`, `tests/unit/test_repro.py::test_not_comparable_different_device`, `tests/integration/test_train_determinism.py::test_manifest_records_tolerance_and_device` | entrypoint | có |
| FR-015 | CLI chỉ hỗ trợ `--stage elbow`; stage khác in "chưa triển khai", mã khác 0, không tạo thư mục run | T302, T319, T336 | `tests/integration/test_train_stage.py::test_stage_not_implemented_exit3`, `tests/integration/test_train_stage.py::test_unknown_stage_exit3` | entrypoint | có |
| FR-016 | Huấn luyện chỉ lấy mục tiêu từ tập train, không dùng tập test | T314, T324 | `tests/integration/test_train_split.py::test_training_only_uses_train_split`, `tests/integration/test_train_split.py::test_config_cannot_select_test_split` | entrypoint | có |
| FR-017 | NaN/Inf, môi trường mất ổn định hoặc không ghi được checkpoint thì dừng với lỗi rõ, mã khác 0, hồ sơ ghi lỗi | T302, T314, T325 | `tests/integration/test_train_nan_guard.py::test_nan_loss_stops_without_checkpoint`, `tests/integration/test_train_nan_guard.py::test_env_instability_reported_status_error`, `tests/integration/test_train_nan_guard.py::test_checkpoint_write_failure_stops` | entrypoint | có |
| FR-018 | Mọi siêu tham số ở một cấu hình duy nhất lưu nguyên văn vào hồ sơ; cấu hình sai bị từ chối trước khi train | T303, T319, T322, T329 | `tests/unit/test_train_config.py::test_defaults_load`, `tests/unit/test_train_config.py::test_invalid_values_raise`, `tests/integration/test_train_cli.py::test_invalid_checkpoint_frequency_rejected`, `tests/integration/test_train_cli.py::test_total_steps_le_zero_rejected` | entrypoint | có |
| FR-019 | Bộ test tự động: seed xác định, lưu/nạp checkpoint, cấu trúc mạng, stage chưa triển khai, đủ trường hồ sơ | T301, T321, T326, T337 | `tests/integration/test_dependency_train.py::test_gymnasium_torch_tensorboard_import_together`, `tests/unit/test_train_packaging.py::test_rl_extra_has_torch_and_tensorboard`, tests/e2e/test_train_acceptance.py (cả tệp) | entrypoint | có |
| FR-020 | Giao diện quan sát mở được trong lúc train, thấy đủ reward, loss, kích hoạt 6 cơ, env steps/s, số bước / tổng, trạng thái checkpoint, cập nhật định kỳ | T308, T315, T317, T319, T331 | `tests/integration/test_dashboard.py::test_progress_endpoint_matches_schema`, `tests/integration/test_dashboard.py::test_page_lists_required_panels`, `tests/integration/test_dashboard_resilience.py::test_dashboard_during_train_shows_required_fields` | entrypoint | có |
| FR-021 | Giao diện chỉ đọc dữ liệu train; không điều khiển, không sửa policy, tham số, cấu hình hay tiến trình | T315, T317, T332 | `tests/integration/test_dashboard.py::test_dashboard_is_read_only`, `tests/integration/test_dashboard.py::test_dashboard_loopback_only`, `tests/integration/test_monitoring_imports.py::test_monitoring_has_no_training_imports` | entrypoint | có |
| FR-022 | Hiển thị 3D ở tiến trình riêng, bật/tắt được, mặc định tắt; train mặc định headless | T316, T319, T333 | `tests/integration/test_viewer3d_train.py::test_view3d_off_by_default`, `tests/integration/test_viewer3d_train.py::test_view3d_unavailable_without_display_does_not_break_train`, `tests/integration/test_viewer3d_train.py::test_view3d_process_separate` | entrypoint | có |
| FR-023 | Chi phí CPU/GPU/VRAM của giao diện được đo trong benchmark; giao diện không khởi động được không làm dừng train | T320, T331, T334 | `tests/integration/test_benchmark_train.py::test_benchmark_schema_and_ratio`, `tests/integration/test_benchmark_train.py::test_benchmark_records_ui_cost`, `tests/integration/test_dashboard_resilience.py::test_train_survives_ui_failure` | entrypoint | có |
| FR-024 | Ghi rõ hình thức giao diện đã chọn, lý do và chi phí đo được trong kế hoạch của feature | T339 | rà soát tài liệu: `specs/003-ppo-train-repro/plan.md` mục "Giao diện quan sát" (reviewer T339); không có mã | tài liệu | có |
| NFR-REL-001 | 0 NaN và 0 Inf trong loss và tham số sau lượt smoke ≤ 4 096 bước, mã 0 | T307, T310, T314, T323 | `tests/integration/test_train_headless.py::test_zero_nan_inf_counters_in_manifest`, `tests/integration/test_train_headless.py::test_params_finite_in_final_checkpoint` | entrypoint | có |
| NFR-REPRO-001 | Lệch tương đối ≤ 1×10⁻⁶ ở K điểm đầu giữa hai run cùng seed/cấu hình/thiết bị; sai khác tuyệt đối ≤ 1×10⁻⁶ sau lưu/nạp | T311, T313, T327, T330 | `tests/integration/test_train_determinism.py::test_same_seed_head_curve_within_tolerance`, `tests/integration/test_resume.py::test_roundtrip_via_cli_same_action` | entrypoint | có |
| NFR-PERF-001 | env steps/s khi bật giao diện ≥ 90% khi tắt (cùng seed, cấu hình, máy) | T320, T334 | `tests/integration/test_benchmark_train.py::test_benchmark_schema_and_ratio`, số đo thật: `logs/m1/benchmark_train.json` (sinh trên máy đích) | entrypoint | có |
| NFR-PERF-002 | Độ trễ cập nhật giao diện ≤ 5 giây từ lúc ghi số liệu | T308, T315 | `tests/integration/test_dashboard.py::test_snapshot_latency_le_5s`, `tests/unit/test_progress.py::test_min_interval_respected` | entrypoint | có |
| NFR-RES-001 | 100% hồ sơ run có CPU, RAM, GPU, VRAM, env steps/second, wall-clock (không áp dụng ghi `null`) | T306, T312, T328 | `tests/integration/test_manifest_contract.py::test_resources_fields_null_explicit`, `tests/integration/test_manifest_contract.py::test_manifest_fields_and_schema` | entrypoint | có |
| NFR-HEADLESS-001 | Lượt smoke chạy hết khi `DISPLAY` bỏ đặt, mã 0 | T316, T323, T333 | `tests/integration/test_train_headless.py::test_smoke_without_display`, `tests/integration/test_viewer3d_train.py::test_view3d_unavailable_without_display_does_not_break_train` | entrypoint | có |
| INV-001 | Mỗi lần chạy có thư mục run riêng; thư mục đã có không bị ghi đè hoặc sửa (kể cả train tiếp) | T305, T312, T338 | `tests/unit/test_run_dir.py::test_unique_dirs_no_overwrite`, `tests/integration/test_manifest_contract.py::test_two_runs_two_dirs`, tests/challenge/test_train_invariants.py (vector INV-001) | entrypoint | có |
| INV-002 | Mọi hành động vào môi trường nằm trong [0,1]^6 và là kích thích cơ; không điều khiển lực/toạ độ tay | T309, T314, T338 | `tests/unit/test_networks.py::test_action_always_in_unit_interval`, `tests/integration/test_train_cli.py::test_actions_in_unit_interval`, tests/challenge/test_train_invariants.py (vector INV-002) | entrypoint | có |
| INV-003 | Huấn luyện chỉ dùng mục tiêu thuộc tập train; tập test không bao giờ xuất hiện lúc train | T314, T324, T338 | `tests/integration/test_train_split.py::test_training_only_uses_train_split`, tests/challenge/test_train_invariants.py (vector INV-003) | entrypoint | có |
| INV-004 | Checkpoint đủ trạng thái để khứ hồi và train tiếp liên tục; không chứa NaN/Inf | T311, T327, T338 | `tests/unit/test_checkpoint.py::test_roundtrip_same_action`, `tests/unit/test_checkpoint.py::test_nan_not_written`, `tests/unit/test_checkpoint.py::test_atomic_write_no_partial`, `tests/integration/test_resume.py::test_resume_restores_normalizer_optimizer_rng`, tests/challenge/test_train_invariants.py (vector INV-004) | entrypoint | có |
| INV-005 | Giao diện chỉ đọc; mở, đóng, lỗi hay không khởi động không đổi policy, checkpoint, cấu hình hay dừng train | T315, T317, T332, T338 | `tests/integration/test_dashboard.py::test_dashboard_is_read_only`, `tests/integration/test_monitoring_imports.py::test_monitoring_has_no_training_imports`, `tests/integration/test_dashboard_resilience.py::test_train_survives_ui_killed_midrun`, tests/challenge/test_train_invariants.py (vector INV-005) | entrypoint | có |
| SC-001 | Lệnh train chạy hết smoke, mã 0, 0 NaN/Inf, có log TensorBoard và ít nhất một checkpoint | T322, T323 | `tests/integration/test_train_cli.py::test_smoke_train_exit0` | entrypoint | có |
| SC-002 | Nạp lại checkpoint cho hành động xác định giống trước khi lưu (≤ 1×10⁻⁶) và train tiếp được | T327 | `tests/integration/test_resume.py::test_roundtrip_via_cli_same_action` | entrypoint | có |
| SC-003 | Mỗi run có đủ 6 mục cùng env steps/second và wall-clock, kiểm theo JSON Schema | T328 | `tests/integration/test_manifest_contract.py::test_manifest_fields_and_schema` | entrypoint | có |
| SC-004 | Hai run cùng seed/cấu hình/thiết bị lệch ≤ 1×10⁻⁶; khác seed thì khác | T330 | `tests/integration/test_train_determinism.py::test_same_seed_head_curve_within_tolerance`, `tests/integration/test_train_determinism.py::test_diff_seed_differs` | entrypoint | có |
| SC-005 | `--stage balance` và stage chưa hỗ trợ báo "chưa triển khai", mã khác 0, không thư mục run | T336 | `tests/integration/test_train_stage.py::test_stage_not_implemented_exit3` | entrypoint | có |
| SC-006 | Actor và critic 2×256, có chuẩn hoá observation và gradient clipping, kiểm bằng test cấu trúc | T335 | `tests/integration/test_network_config.py::test_actor_critic_2x256_from_default_config` | entrypoint | có |
| SC-007 | Giao diện hiện đủ số liệu, cập nhật ≤ 5 s, bật giao diện giảm env steps/s ≤ 10% | T331, T334 | `tests/integration/test_dashboard_resilience.py::test_dashboard_during_train_shows_required_fields`, `tests/integration/test_benchmark_train.py::test_benchmark_schema_and_ratio` | entrypoint | có |
| CMD-TRN-0001 | `train.py --stage elbow --seed 42 [...]` (hợp đồng `contracts/cli.md`) | T319, T322, T336 | `tests/integration/test_train_cli.py::test_smoke_train_exit0`, `tests/integration/test_train_stage.py::test_stage_not_implemented_exit3` | entrypoint | có |
| CMD-TRN-0002 | `watch_train.py --run RUN_DIR` mở giao diện quan sát chỉ-đọc | T317, T331 | `tests/unit/test_watch_cli.py::test_writes_ui_json`, `tests/integration/test_dashboard_resilience.py::test_dashboard_during_train_shows_required_fields` | entrypoint | có |
| CMD-TRN-0003 | `compare_runs.py RUN_A RUN_B` so đường reward đầu kỳ theo dung sai | T318, T330 | `tests/unit/test_compare_cli.py::test_exit0_within_tolerance`, `tests/unit/test_compare_cli.py::test_exit1_outside` | entrypoint | có |
| CMD-TRN-0004 | `benchmark_train.py --seed 42 [--repeats 5]` đo chi phí giao diện | T320, T334 | `tests/integration/test_benchmark_train.py::test_benchmark_schema_and_ratio` | entrypoint | có |
| API-TRN-0001 | `GET /api/progress` trả snapshot hợp schema hoặc 503 "chưa có dữ liệu" | T315, T331 | `tests/integration/test_dashboard.py::test_progress_endpoint_matches_schema`, `tests/integration/test_dashboard.py::test_progress_503_when_no_file` | entrypoint | có |
| API-TRN-0002 | `GET /` trang tĩnh có các khối reward, loss, 6 cơ, env steps/s, số bước / tổng, trạng thái checkpoint | T315 | `tests/integration/test_dashboard.py::test_page_lists_required_panels` | entrypoint | có |
| API-003 | API Python `mma_ai.learning`/`mma_ai.monitoring` (`contracts/python-api.md`) mà con 3 và con 4 gọi | T311, T314 | `tests/unit/test_checkpoint.py::test_roundtrip_same_action`, `tests/unit/test_trainer.py::test_trainer_runs_toy_env_and_writes_artifacts` | unit | có |

<a id="truy-vet-nguoc-task-ma"></a>
## Truy vết ngược: task → mã

| Task | Mã hiện thực |
|---|---|
| T301 | FR-002 · FR-010 · FR-019 |
| T302 | FR-015 · FR-017 · INV-005 |
| T303 | FR-002 · FR-004 · FR-018 · INV-005 |
| T304 | FR-003 · INV-004 |
| T305 | FR-011 · INV-001 |
| T306 | FR-012 · FR-013 · NFR-RES-001 |
| T307 | FR-010 · NFR-REL-001 |
| T308 | FR-020 · NFR-PERF-002 · INV-005 |
| T309 | FR-002 · FR-005 · INV-002 |
| T310 | FR-002 · FR-004 · NFR-REL-001 |
| T311 | FR-006 · FR-007 · FR-008 · FR-009 · INV-004 · NFR-REPRO-001 · API-003 |
| T312 | FR-011 · FR-012 · FR-013 · FR-014 · NFR-RES-001 · INV-001 |
| T313 | FR-001 · FR-014 · NFR-REPRO-001 |
| T314 | FR-001 · FR-003 · FR-005 · FR-006 · FR-007 · FR-009 · FR-010 · FR-013 · FR-016 · FR-017 · INV-002 · INV-003 · INV-004 · NFR-REL-001 · API-003 |
| T315 | FR-020 · FR-021 · NFR-PERF-002 · INV-005 · API-TRN-0001 · API-TRN-0002 |
| T316 | FR-022 · INV-005 · NFR-HEADLESS-001 |
| T317 | FR-020 · FR-021 · FR-022 · CMD-TRN-0002 · INV-005 |
| T318 | FR-014 · CMD-TRN-0003 · NFR-REPRO-001 |
| T319 | FR-001 · FR-009 · FR-013 · FR-015 · FR-018 · FR-020 · FR-022 · FR-023 · CMD-TRN-0001 · INV-002 · INV-005 |
| T320 | FR-023 · NFR-PERF-001 · CMD-TRN-0004 · INV-005 |
| T321 | FR-019 |
| T322…T336 | test tích hợp theo story (AC-1…AC-7, FR, INV, NFR, SC như ma trận trên) |
| T337 | AC-1…AC-7 · FR-019 · SC-001…SC-007 |
| T338 | INV-001 · INV-002 · INV-003 · INV-004 · INV-005 |
| T339 | đối chiếu AC-1…AC-7 · INV-001…INV-005 · NFR · FR-024 |

<a id="chua-truy-vet-duoc"></a>
## Chưa truy vết được

- Không có mã nào của `spec.md` thiếu task hoặc test dự kiến; FR-024 là yêu cầu tài liệu (hình thức giao diện, lý do, chi phí) nên chứng minh bằng rà soát của reviewer (T339) trên `plan.md`, không bằng test mã.
- **Phụ thuộc chéo feature chưa khai ở cột `depends_on`**: 001 và 002 chưa có `tasks.md` (chưa có id task), nên T301, T306, T312, T314, T316, T319 và T321 chỉ ghi bằng chữ ở mục "Phụ thuộc chéo feature" của `tasks.md`; bước converge/`plan_fix` phải bổ sung khi các `tasks.md` đó có. Chỉ T301 đã khai `depends_on` T501 (khung của 005).
- **Vỏ `scripts/train.py`, `watch_train.py`, `compare_runs.py`, `benchmark_train.py` và `configs/train_elbow*.yaml` chưa có chủ**: `scripts/**`, `configs/**`, `tests/regression/**` và `.gitignore` ngoài vùng ghi của mọi vai (khoảng trống năng lực). Mọi AC được chứng minh qua entrypoint `python -m mma_ai.learning.cli` / `python -m mma_ai.monitoring.cli`; chuỗi lệnh `python scripts/train.py` của AC-1…AC-5 chưa có test riêng cho tới khi vỏ script có chủ (đề xuất `ai-sdlc capability propose` đã ghi trong `tasks.md`).
- **Cổng `tests` thiếu extra**: lệnh cổng hiện không kèm `--extra rl`/`--extra dev`, test nhập `torch`/`tensorboard` sẽ đỏ vì thiếu thư viện — cần bước `plan_fix` nháp lại cổng theo `plan.md`.
- **Số đo thật** (env steps/s, chi phí giao diện ≥ 90%, độ trễ ≤ 5 s, tái lập GPU↔GPU, chi phí 3D khi có màn hình) CHƯA có: chỉ có sau khi `benchmark.py` và test chạy trên máy đích; mọi test hiện chỉ là dự kiến vì 001 và 002 chưa có mã.
