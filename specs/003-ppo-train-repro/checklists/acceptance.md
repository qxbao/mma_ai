---
doc_type: tracing
feature: "003-ppo-train-repro"
source_request: "REQ-0102"
updated: "2026-10-09"
id: SPEC-003-ppo-train-repro-acceptance
title: 'Checklist nghiệm thu (acceptance checklist): PPO train và tái lập'
owner_agent: spec
status: draft
---

# Checklist nghiệm thu (acceptance checklist): PPO train và tái lập

- [Tiêu chí chấp nhận](#tieu-chi-chap-nhan)
- [Yêu cầu phi chức năng](#yeu-cau-phi-chuc-nang)
- [Bất biến](#bat-bien)


Mỗi dòng ánh xạ tiêu chí chấp nhận (acceptance criterion), bất biến (invariant) hoặc yêu cầu phi chức năng (non-functional requirement) sang test, mức kiểm và dấu vết do máy sinh. Các ô luôn để `[ ]`; chỉ cổng `ai-sdlc reconcile --mark` trên nhánh tích hợp mới được phép tích khi toàn bộ Task nêu trên dòng đã xanh, đã gộp và mọi tệp nêu đã tồn tại.

- Tự chốt: AC-1…AC-6 chép theo `docs/00-input/split/yeu-cau-a7634ac9/request-2.md`; AC-7 là bổ sung C-0009 chỉ có trong `spec.md` — lý do: REQ-0102 không chứa AC-7 nhưng `spec.md` chứa mã này và cổng cần một dòng cho mọi AC trong spec.

<a id="tieu-chi-chap-nhan"></a>
## Tiêu chí chấp nhận

- [ ] AC-1 — Cho môi trường xanh, khi chạy `python scripts/train.py --stage elbow --seed 42` thì huấn luyện chạy được, ghi log TensorBoard và checkpoint định kỳ. Task: T303, T309, T310, T311, T314, T319, T322, T323, T324, T325, T337. `tests/integration/test_train_cli.py::test_smoke_train_exit0`, `tests/integration/test_train_cli.py::test_tensorboard_scalars_present`, `tests/integration/test_train_cli.py::test_periodic_and_final_checkpoint`, `tests/integration/test_train_headless.py::test_zero_nan_inf_counters_in_manifest`, `tests/e2e/test_train_acceptance.py::test_ac_1_train_smoke` — entrypoint. Dấu vết máy: kết quả gates và capture E2E tên AC-1.
- [ ] AC-2 — Cho checkpoint đã lưu, khi nạp lại thì policy cho cùng hành động xác định trên cùng observation mẫu và có thể train tiếp. Task: T311, T314, T319, T327, T337. `tests/integration/test_resume.py::test_roundtrip_via_cli_same_action`, `tests/integration/test_resume.py::test_resume_creates_new_run_with_parent`, `tests/integration/test_resume.py::test_resume_restores_normalizer_optimizer_rng`, `tests/e2e/test_train_acceptance.py::test_ac_2_checkpoint_roundtrip_and_resume` — entrypoint. Dấu vết máy: kết quả gates và capture E2E tên AC-2.
- [ ] AC-3 — Cho một run xong, khi mở thư mục run thì có seed, config, phiên bản thư viện, hash XML, checkpoint, reward metrics. Task: T305, T306, T312, T328, T329, T337. `tests/integration/test_manifest_contract.py::test_manifest_fields_and_schema`, `tests/integration/test_manifest_contract.py::test_two_runs_two_dirs`, `tests/integration/test_manifest_contract.py::test_manifest_hash_matches_env_model_record`, `tests/e2e/test_train_acceptance.py::test_ac_3_run_manifest_fields` — entrypoint. Dấu vết máy: kết quả gates và capture E2E tên AC-3.
- [ ] AC-4 — Cho hai run cùng seed/cấu hình, khi so sánh thì kết quả nằm trong dung sai tái lập đã khai. Task: T313, T318, T330, T337. `tests/integration/test_train_determinism.py::test_same_seed_head_curve_within_tolerance`, `tests/integration/test_train_determinism.py::test_diff_seed_differs`, `tests/integration/test_train_determinism.py::test_compare_cli_exit0_within_tolerance`, `tests/e2e/test_train_acceptance.py::test_ac_4_same_seed_within_tolerance` — entrypoint. Dấu vết máy: kết quả gates và capture E2E tên AC-4.
- [ ] AC-5 — Cho `--stage balance` (hoặc stage chưa hỗ trợ), khi gọi CLI thì báo rõ "chưa triển khai", mã thoát khác 0. Task: T319, T336, T337. `tests/integration/test_train_stage.py::test_stage_not_implemented_exit3`, `tests/integration/test_train_stage.py::test_no_run_dir_for_unimplemented`, `tests/e2e/test_train_acceptance.py::test_ac_5_stage_not_implemented` — entrypoint. Dấu vết máy: kết quả gates và capture E2E tên AC-5.
- [ ] AC-6 — Cho cấu hình MLP, khi kiểm tra mạng thì actor và critic đều 2 lớp × 256, có chuẩn hoá observation và gradient clipping. Task: T309, T310, T335, T337. `tests/integration/test_network_config.py::test_actor_critic_2x256_from_default_config`, `tests/integration/test_network_config.py::test_normalizer_and_clipping_present`, `tests/e2e/test_train_acceptance.py::test_ac_6_network_2x256` — entrypoint. Dấu vết máy: kết quả gates và capture E2E tên AC-6.
- [ ] AC-7 — Bổ sung C-0009 trong `spec.md`: trong lúc train, giao diện quan sát hiện reward, loss, kích hoạt 6 cơ, env steps/s, số bước / tổng và trạng thái checkpoint; cập nhật trong tối đa 5 giây, chỉ đọc, và giảm env steps/s không quá 10%. Task: T308, T315, T316, T317, T320, T331, T333, T334, T337. `tests/integration/test_dashboard_resilience.py::test_dashboard_during_train_shows_required_fields`, `tests/integration/test_dashboard.py::test_dashboard_is_read_only`, `tests/integration/test_dashboard.py::test_snapshot_latency_le_5s`, `tests/integration/test_benchmark_train.py::test_benchmark_schema_and_ratio`, `tests/e2e/test_train_acceptance.py::test_ac_7_progress_ui_live` — entrypoint. Dấu vết máy: kết quả gates, capture E2E tên AC-7 và `logs/m1/benchmark_train.json` do benchmark sinh.

<a id="yeu-cau-phi-chuc-nang"></a>
## Yêu cầu phi chức năng

- [ ] NFR-REL-001 — Lượt smoke tối đa 4 096 bước có 0 NaN và 0 Inf trong loss và tham số, mã thoát 0. Task: T307, T310, T314, T323. `tests/integration/test_train_headless.py::test_zero_nan_inf_counters_in_manifest`, `tests/integration/test_train_headless.py::test_params_finite_in_final_checkpoint` — entrypoint. Dấu vết máy: kết quả gates và capture E2E tên AC-1.
- [ ] NFR-REPRO-001 — Hai run cùng seed/cấu hình/phiên bản/loại thiết bị lệch tương đối không quá 1×10⁻⁶ ở K điểm đầu; sau lưu/nạp, hành động xác định lệch tuyệt đối không quá 1×10⁻⁶. Task: T311, T313, T327, T330. `tests/integration/test_train_determinism.py::test_same_seed_head_curve_within_tolerance`, `tests/integration/test_resume.py::test_roundtrip_via_cli_same_action` — entrypoint. Dấu vết máy: kết quả gates và capture E2E tên AC-2, AC-4.
- [ ] NFR-PERF-001 — env steps/s khi bật giao diện đạt ít nhất 90% khi tắt, với cùng seed, cấu hình và máy. Task: T320, T334. `tests/integration/test_benchmark_train.py::test_benchmark_schema_and_ratio` — entrypoint. Dấu vết máy: kết quả gates, capture E2E tên AC-7 và `logs/m1/benchmark_train.json` do benchmark sinh.
- [ ] NFR-PERF-002 — Độ trễ từ lúc ghi số liệu đến lúc hiện trên giao diện không quá 5 giây. Task: T308, T315. `tests/integration/test_dashboard.py::test_snapshot_latency_le_5s` — entrypoint. Dấu vết máy: kết quả gates và capture E2E tên AC-7.
- [ ] NFR-RES-001 — 100% hồ sơ run có CPU, RAM, GPU, VRAM, env steps/second và wall-clock; trường không áp dụng là `null`. Task: T306, T312, T328. `tests/integration/test_manifest_contract.py::test_resources_fields_null_explicit`, `tests/integration/test_manifest_contract.py::test_manifest_fields_and_schema` — entrypoint. Dấu vết máy: kết quả gates và capture E2E tên AC-3.
- [ ] NFR-HEADLESS-001 — Lượt smoke hoàn tất với mã 0 khi `DISPLAY` không đặt. Task: T316, T323, T333. `tests/integration/test_train_headless.py::test_smoke_without_display`, `tests/integration/test_viewer3d_train.py::test_view3d_unavailable_without_display_does_not_break_train` — entrypoint. Dấu vết máy: kết quả gates và capture E2E tên AC-1, AC-7.

<a id="bat-bien"></a>
## Bất biến

- [ ] INV-001 — Mỗi lần train có thư mục run riêng; thư mục đã tồn tại không bị ghi đè hoặc sửa, kể cả khi train tiếp. Task: T305, T312, T338. `tests/integration/test_manifest_contract.py::test_two_runs_two_dirs`, `tests/challenge/test_train_invariants.py` (vector INV-001) — entrypoint. Dấu vết máy: kết quả gates, verdict challenger T338 và capture E2E tên AC-3.
- [ ] INV-002 — Mọi hành động policy đưa vào môi trường nằm trong `[0,1]^6`, là kích thích cơ, và không điều khiển trực tiếp lực hay toạ độ tay. Task: T309, T314, T338. `tests/integration/test_train_cli.py::test_actions_in_unit_interval`, `tests/challenge/test_train_invariants.py` (vector INV-002) — entrypoint. Dấu vết máy: kết quả gates, verdict challenger T338 và capture E2E tên AC-1.
- [ ] INV-003 — Huấn luyện chỉ dùng mục tiêu thuộc tập train; tập test không bao giờ xuất hiện lúc train. Task: T314, T324, T338. `tests/integration/test_train_split.py::test_training_only_uses_train_split`, `tests/challenge/test_train_invariants.py` (vector INV-003) — entrypoint. Dấu vết máy: kết quả gates, verdict challenger T338 và capture E2E tên AC-1.
- [ ] INV-004 — Checkpoint đủ trạng thái để khứ hồi và train tiếp liên tục, đồng thời không chứa NaN/Inf. Task: T311, T327, T338. `tests/integration/test_resume.py::test_resume_restores_normalizer_optimizer_rng`, `tests/challenge/test_train_invariants.py` (vector INV-004) — entrypoint. Dấu vết máy: kết quả gates, verdict challenger T338 và capture E2E tên AC-2.
- [ ] INV-005 — Giao diện chỉ đọc; mở, đóng, lỗi hoặc không khởi động không đổi policy, checkpoint, cấu hình hay dừng train. Task: T315, T317, T332, T338. `tests/integration/test_dashboard.py::test_dashboard_is_read_only`, `tests/integration/test_dashboard_resilience.py::test_train_survives_ui_killed_midrun`, `tests/challenge/test_train_invariants.py` (vector INV-005) — entrypoint. Dấu vết máy: kết quả gates, verdict challenger T338 và capture E2E tên AC-7.
