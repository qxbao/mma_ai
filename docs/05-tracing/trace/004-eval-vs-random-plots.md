---
id: "TRACE-004"
title: "Ma trận truy vết 004-eval-vs-random-plots"
doc_type: tracing
owner_agent: spec
status: draft
updated: "2026-10-09"
---

# Ma trận truy vết 004-eval-vs-random-plots

- [Ma trận](#ma-tran)
- [Truy vết ngược: task → mã](#truy-vet-nguoc-task-ma)
- [Chưa truy vết được](#chua-truy-vet-duoc)

> Đích: `docs/05-tracing/trace/004-eval-vs-random-plots.md` (`trace-matrix.md` là chỉ mục máy sinh, không sửa tay). Nguồn: `specs/004-eval-vs-random-plots/spec.md` (yêu cầu) và `specs/004-eval-vs-random-plots/tasks.md` (task `T401`…`T426`).
> Mức `entrypoint` = test chạy qua lệnh CLI thật `python -m mma_ai.evaluation.cli` (subprocess; vỏ `python scripts/evaluate.py` chưa có chủ — xem cuối tệp) hoặc e2e; mức `unit` = test mô-đun đơn lẻ. Tên hàm test là tên dự kiến theo `plan.md` và `tasks.md`; chưa có mã nên cột trạng thái ghi "có" nghĩa là đã có task + test dự kiến, KHÔNG có nghĩa test đã chạy xanh.

<a id="ma-tran"></a>
## Ma trận

| Mã | Yêu cầu (spec.md) | Task (tasks.md) | Test / cổng máy | Mức | Trạng thái |
|---|---|---|---|---|---|
| AC-1 | Cho checkpoint đã train, chạy evaluate trên tập mục tiêu kiểm thử thì in và lưu chỉ số của policy đã học và của random policy trên cùng tập | T407, T408, T412, T413, T415, T416, T420, T424 | `tests/integration/test_evaluate_cli.py::test_both_policies_same_targets`, `tests/integration/test_evaluate_cli.py::test_all_metrics_present_with_ci`, `tests/e2e/test_evaluate_acceptance.py::test_ac_1_evaluate_both_policies` | entrypoint | có |
| AC-2 | Cho kết quả hai policy, so sánh thì policy đã học tốt hơn random theo tiêu chí khai trước, kèm khoảng tin cậy | T404, T411, T417, T424 | `tests/integration/test_verdict_known_policies.py::test_scripted_reaching_policy_is_better`, `tests/integration/test_verdict_known_policies.py::test_always_zero_policy_is_not_better`, `tests/e2e/test_evaluate_acceptance.py::test_ac_2_verdict_with_ci` | entrypoint | có |
| AC-3 | Cho log của một run, tạo biểu đồ thì có ảnh loss, reward, activation (6 cơ), kể cả không màn hình | T410, T418, T424 | `tests/integration/test_evaluate_headless.py::test_evaluate_with_display_unset_exit0`, `tests/integration/test_evaluate_headless.py::test_missing_activation_series_exit6_results_saved`, `tests/e2e/test_evaluate_acceptance.py::test_ac_3_three_charts` | entrypoint | có |
| AC-4 | Cho tập đánh giá, kiểm tra thì không mục tiêu/seed nào trùng tập train; vi phạm thì không chạy episode nào | T409, T419, T424 | `tests/integration/test_evaluate_leakage.py::test_leak_exits5_no_episode_run`, `tests/integration/test_evaluate_leakage.py::test_disjointness_recorded_in_report`, `tests/e2e/test_evaluate_acceptance.py::test_ac_4_no_overlap_with_train` | entrypoint | có |
| AC-5 | Cho checkpoint không tồn tại hoặc hỏng, chạy evaluate thì báo lỗi rõ, mã thoát khác 0, không in kết quả giả | T412, T422, T424 | `tests/integration/test_evaluate_bad_checkpoint.py::test_missing_checkpoint_exit4_no_output`, `tests/integration/test_evaluate_bad_checkpoint.py::test_corrupt_checkpoint_exit4_names_cause`, `tests/e2e/test_evaluate_acceptance.py::test_ac_5_bad_checkpoint` | entrypoint | có |
| KQ-1 | Báo cáo so sánh policy học được và random trên cùng tập mục tiêu: tỷ lệ tới mục tiêu, khoảng cách cuối, khoảng tin cậy | T408, T415, T416 | `tests/integration/test_evaluate_cli.py::test_all_metrics_present_with_ci`, `tests/integration/test_report_contract.py::test_report_schema_and_no_nonfinite` | entrypoint | có |
| KQ-2 | Policy đã học tốt hơn random có ý nghĩa thống kê theo tiêu chí khai trước | T404, T411, T417 | `tests/integration/test_verdict_known_policies.py::test_scripted_reaching_policy_is_better`, `tests/unit/test_stats.py::test_verdict_rule_ci_lower_gt_zero` | entrypoint | có |
| KQ-3 | Có 3 biểu đồ loss, reward, activation cơ (6 cơ) lưu thành tệp ảnh | T410, T418 | `tests/integration/test_evaluate_headless.py::test_evaluate_with_display_unset_exit0`, `tests/unit/test_charts.py::test_three_files_valid_png` | entrypoint | có |
| KQ-4 | Kết quả đánh giá lưu cùng hồ sơ run (seed, checkpoint được dùng) | T411, T420 | `tests/integration/test_evaluate_storage.py::test_report_names_seed_and_checkpoint_hash` | entrypoint | có |
| FR-001 | Lệnh evaluate `--checkpoint` nạp policy chỉ-đọc và đánh giá cùng random policy trên tập kiểm thử, in và lưu chỉ số | T412, T413, T415 | `tests/integration/test_evaluate_cli.py::test_both_policies_same_targets`, `tests/unit/test_eval_cli_args.py::test_missing_checkpoint_arg_exit2` | entrypoint | có |
| FR-002 | Hai policy chạy trên cùng danh sách mục tiêu, cùng thứ tự, cùng cấu hình; mỗi mục tiêu một episode mỗi policy | T405, T407, T412 | `tests/integration/test_evaluate_cli.py::test_both_policies_same_targets`, `tests/integration/test_report_contract.py::test_n_episodes_equal_targets_times_repeats`, `tests/unit/test_rollout.py::test_each_target_once_per_repeat_same_order_for_two_policies`, `tests/unit/test_env_target_index.py::test_target_index_selects_ith_test_target` | entrypoint | có |
| FR-003 | Policy học được dùng hành động xác định; random lấy mẫu đều `[0,1]^6` có seed; chỉ kích thích cơ, không position controller | T406, T407, T415 | `tests/integration/test_evaluate_cli.py::test_actions_in_unit_interval`, `tests/unit/test_policies.py::test_random_policy_seeded_and_in_unit_interval`, `tests/unit/test_policies.py::test_random_ignores_observation` | entrypoint | có |
| FR-004 | Tính bảy nhóm chỉ số cho mỗi policy ở mô-đun `metrics.py` | T408, T415 | `tests/integration/test_evaluate_cli.py::test_all_metrics_present_with_ci`, `tests/unit/test_metrics.py::test_summarize_all_groups` | entrypoint | có |
| FR-005 | Khoảng tin cậy 95% (mức cấu hình được) cho tỷ lệ, khoảng cách cuối, reward và cho hiệu; tất định theo seed; ghi tên phương pháp | T404, T408, T421 | `tests/unit/test_stats.py::test_wilson_matches_hand_values`, `tests/unit/test_stats.py::test_newcombe_matches_hand_values`, `tests/integration/test_eval_determinism.py::test_bootstrap_seed_fixed_gives_same_ci` | unit | có |
| FR-006 | Kết luận tốt hơn / không tốt hơn theo tiêu chí khai trước: cận dưới khoảng tin cậy của hiệu tỷ lệ tới mục tiêu > 0 | T404, T411, T417 | `tests/unit/test_stats.py::test_verdict_rule_ci_lower_gt_zero`, `tests/integration/test_verdict_known_policies.py::test_identical_policies_not_better` | entrypoint | có |
| FR-007 | Tiêu chí kết luận đọc từ cấu hình, ghi vào báo cáo, không đường nào đổi sau khi có kết quả | T403, T413, T415, T417 | `tests/integration/test_evaluate_cli.py::test_criterion_in_report_and_no_override_flag`, `tests/unit/test_eval_config.py::test_criterion_override_rejected` | entrypoint | có |
| FR-008 | Trước episode đầu kiểm tập đánh giá không giao tập train và seed khác seed train; vi phạm thì dừng, mã khác 0 | T409, T412, T419 | `tests/integration/test_evaluate_leakage.py::test_leak_exits5_no_episode_run`, `tests/unit/test_split_guard.py::test_target_within_min_distance_rejected`, `tests/unit/test_split_guard.py::test_seed_range_overlap_rejected` | entrypoint | có |
| FR-009 | Không thiết lập được tập/seed train của run thì từ chối đánh giá | T409, T419 | `tests/integration/test_evaluate_leakage.py::test_unknown_train_set_exit5`, `tests/unit/test_split_guard.py::test_unknown_train_set_refused` | entrypoint | có |
| FR-010 | Ba biểu đồ loss, reward, activation 6 cơ có nhãn từ nhật ký của run; đọc nhật ký ở `metrics.py` | T401, T408, T410, T418 | `tests/unit/test_training_log.py::test_reads_jsonl_and_tfevents`, `tests/unit/test_charts.py::test_activation_has_six_named_lines`, `tests/unit/test_charts.py::test_points_match_log`, `tests/integration/test_evaluate_headless.py::test_evaluate_with_display_unset_exit0` | entrypoint | có |
| FR-011 | Vẽ không cần màn hình; nhật ký thiếu thì báo biểu đồ nào không tạo được, không ảnh rỗng, lưu kết quả số, mã khác 0 | T410, T418 | `tests/integration/test_evaluate_headless.py::test_missing_activation_series_exit6_results_saved`, `tests/unit/test_charts.py::test_missing_series_no_empty_image` | entrypoint | có |
| FR-012 | Điểm NaN/Inf trong nhật ký không bị vẽ thành giá trị giả; ghi số điểm bỏ và lý do | T410, T418 | `tests/unit/test_charts.py::test_nonfinite_points_dropped_and_counted`, `tests/integration/test_evaluate_headless.py::test_nonfinite_loss_points_reported` | entrypoint | có |
| FR-013 | Mỗi lượt lưu bản ghi trong `eval/<mã>/` duy nhất, gồm seed run, checkpoint + hash, hash XML, seed đánh giá, cấu hình, giao rỗng, chỉ số, kết luận, biểu đồ, trạng thái run, phiên bản thư viện | T411, T414, T420 | `tests/integration/test_evaluate_storage.py::test_report_names_seed_and_checkpoint_hash`, `tests/integration/test_evaluate_storage.py::test_two_evals_two_dirs_first_unchanged`, `tests/integration/test_evaluate_storage.py::test_checkpoint_outside_run_requires_out` | entrypoint | có |
| FR-014 | Không sửa, ghi đè hay xoá hồ sơ run, checkpoint, nhật ký của con 2 | T411, T412, T420, T423 | `tests/integration/test_evaluate_storage.py::test_run_files_unchanged_by_evaluation`, `tests/integration/test_evaluation_imports.py::test_evaluation_has_no_training_imports` | entrypoint | có |
| FR-015 | Checkpoint không tồn tại/hỏng/thiếu thành phần/khác cấu trúc/khác hash XML thì lỗi nêu nguyên nhân, mã khác 0, không chỉ số/biểu đồ/thư mục `eval/` dở dang | T402, T412, T413, T422 | `tests/integration/test_evaluate_bad_checkpoint.py::test_xml_hash_mismatch_exit4`, `tests/integration/test_evaluate_bad_checkpoint.py::test_no_eval_dir_after_checkpoint_error`, `tests/integration/test_evaluate_bad_checkpoint.py::test_missing_component_exit4` | entrypoint | có |
| FR-016 | Episode mất ổn định tính là kết thúc bất thường, không tới mục tiêu, loại khỏi khoảng cách cuối, không dừng lượt; đếm NaN/Inf | T407, T408, T415 | `tests/integration/test_evaluate_cli.py::test_abnormal_episode_counted_not_fatal`, `tests/unit/test_metrics.py::test_abnormal_excluded_from_distance`, `tests/unit/test_rollout.py::test_instability_counted_not_fatal` | entrypoint | có |
| FR-017 | Chỉ số không có dữ liệu hợp lệ ghi `null` kèm lý do; mọi tệp kết quả là JSON hợp lệ không NaN/Infinity | T408, T411, T416 | `tests/integration/test_report_contract.py::test_null_with_reason_when_no_valid_data`, `tests/unit/test_metrics.py::test_all_abnormal_distance_is_null_with_reason` | entrypoint | có |
| FR-018 | Cấu hình đánh giá một tệp lưu nguyên văn; cấu hình sai bị từ chối trước episode đầu | T403, T413 | `tests/unit/test_eval_config.py::test_invalid_values_raise`, `tests/unit/test_eval_config.py::test_defaults_load`, `tests/integration/test_report_contract.py::test_contract_examples_eval` | unit | có |
| FR-019 | Báo cáo phân biệt số đo với giả định, ghi giới hạn kết luận, không khẳng định chất lượng ngoài số đo | T411, T416, T417 | `tests/unit/test_report.py::test_limits_present_and_no_quality_claim`, `tests/integration/test_verdict_known_policies.py::test_wide_ci_few_targets_reported_as_computed` | unit | có |
| FR-020 | Bộ test tự động phủ đủ chỉ số, kết luận, khoảng tin cậy, biểu đồ, giao rỗng, checkpoint lỗi, tái lập | T414, T424 | `uv run python -m pytest -q` (toàn bộ), `tests/e2e/test_evaluate_acceptance.py` | entrypoint | có |
| NFR-REPRO-001 | Tái lập lượt đánh giá theo seed trên cùng loại thiết bị (chỉ số lệch ≤ 1×10⁻⁶) | T406, T421 | `tests/integration/test_eval_determinism.py::test_same_seed_same_actions_and_metrics`, `tests/integration/test_eval_determinism.py::test_diff_seed_diff_random_actions` | entrypoint | có |
| NFR-REL-001 | Độ tin cậy số học của báo cáo: 0 NaN, 0 Inf trong tệp kết quả, hợp schema | T411, T416 | `tests/integration/test_report_contract.py::test_report_schema_and_no_nonfinite`, `tests/unit/test_report.py::test_report_validates_schema_and_no_nonfinite` | entrypoint | có |
| NFR-HEADLESS-001 | Đánh giá và vẽ biểu đồ chạy không đồ hoạ (`DISPLAY` bỏ đặt) | T410, T418, T423 | `tests/integration/test_evaluate_headless.py::test_evaluate_with_display_unset_exit0`, `tests/integration/test_evaluation_imports.py::test_charts_import_does_not_require_display` | entrypoint | có |
| NFR-STAT-001 | Tính đúng của khoảng tin cậy và kết luận trên dữ liệu tổng hợp có đáp án | T404, T417 | `tests/unit/test_stats.py::test_edge_counts_0_and_n_finite`, `tests/integration/test_verdict_known_policies.py::test_both_rates_zero_or_one_finite` | unit | có |
| INV-001 | Tập đánh giá không giao tập train (mục tiêu, khoảng cách tối thiểu, seed); không thiết lập được thì không đánh giá | T409, T419, T425 | `tests/integration/test_evaluate_leakage.py::test_resume_chain_seeds_rejected`, `tests/unit/test_split_guard.py::test_resume_chain_seeds_collected`, `tests/challenge/test_evaluate_invariants.py` (biên khoảng cách, dải seed) | entrypoint | có |
| INV-002 | Hai policy so trên cùng tập, thứ tự, cấu hình, giới hạn episode; hash XML môi trường = hash hồ sơ run | T407, T412, T415, T416 | `tests/integration/test_report_contract.py::test_hash_consistency`, `tests/integration/test_evaluate_cli.py::test_both_policies_same_targets` | entrypoint | có |
| INV-003 | Mọi hành động của cả hai policy trong `[0,1]^6` và là kích thích cơ; không đường điều khiển lực/toạ độ tay | T406, T407, T415, T425 | `tests/integration/test_evaluate_cli.py::test_actions_in_unit_interval`, `tests/unit/test_rollout.py::test_nan_action_blocked_before_step`, `tests/challenge/test_evaluate_invariants.py` (hành động NaN/ngoài biên) | entrypoint | có |
| INV-004 | Khi lỗi thoát mã khác 0 và không để lại hay in kết quả trông hợp lệ; bản ghi chỉ xuất hiện khi hoàn tất | T402, T411, T412, T420, T422, T425 | `tests/integration/test_evaluate_storage.py::test_no_partial_dir_on_interrupt`, `tests/integration/test_evaluate_storage.py::test_unwritable_eval_dir_exit7`, `tests/unit/test_runner.py::test_no_eval_dir_before_publish`, `tests/challenge/test_evaluate_invariants.py` (ngắt/ghi lỗi ở mọi bước) | entrypoint | có |
| INV-005 | Đánh giá chỉ đọc đối với checkpoint, hồ sơ run, nhật ký; kết quả ghi tệp mới, không ghi đè kết quả cũ | T411, T412, T420, T423, T425 | `tests/integration/test_evaluate_storage.py::test_run_files_unchanged_by_evaluation`, `tests/integration/test_evaluate_storage.py::test_two_evals_two_dirs_first_unchanged`, `tests/challenge/test_evaluate_invariants.py` (đích đã có) | entrypoint | có |
| INV-006 | Tiêu chí kết luận khai trước, không đổi theo kết quả, báo cáo ghi nguyên tiêu chí đã dùng | T403, T404, T413, T425 | `tests/integration/test_evaluate_cli.py::test_criterion_in_report_and_no_override_flag`, `tests/unit/test_eval_cli_args.py::test_no_criterion_override_flag`, `tests/challenge/test_evaluate_invariants.py` (đột biến tiêu chí) | entrypoint | có |
| INV-007 | Cùng checkpoint, cấu hình, seed: random policy cùng chuỗi hành động và cùng chỉ số trong dung sai | T406, T421 | `tests/integration/test_eval_determinism.py::test_same_seed_same_actions_and_metrics`, `tests/unit/test_policies.py::test_diff_seed_diff_actions` | entrypoint | có |
| SC-001 | Evaluate trên checkpoint hợp lệ thoát 0, in/lưu chỉ số hai policy, mỗi mục tiêu một episode mỗi policy, khoảng tin cậy 95% | T415, T424 | `tests/integration/test_evaluate_cli.py::test_both_policies_same_targets`, `tests/e2e/test_evaluate_acceptance.py::test_ac_1_evaluate_both_policies` | entrypoint | có |
| SC-002 | Mỗi báo cáo nêu kết luận kèm hiệu và khoảng tin cậy; đúng 100% trên bộ test có đáp án | T417, T424 | `tests/integration/test_verdict_known_policies.py::test_scripted_reaching_policy_is_better`, `tests/e2e/test_evaluate_acceptance.py::test_ac_2_verdict_with_ci` | entrypoint | có |
| SC-003 | Mỗi lượt có nhật ký đủ tạo đúng 3 ảnh khác rỗng, kể cả không màn hình | T418, T424 | `tests/integration/test_evaluate_headless.py::test_evaluate_with_display_unset_exit0`, `tests/e2e/test_evaluate_acceptance.py::test_ac_3_three_charts` | entrypoint | có |
| SC-004 | 100% lượt chạy phép kiểm giao rỗng trước episode đầu; vi phạm thì 0 episode được chạy | T419 | `tests/integration/test_evaluate_leakage.py::test_leak_exits5_no_episode_run` | entrypoint | có |
| SC-005 | Checkpoint không tồn tại/hỏng: mã khác 0, nêu nguyên nhân, 0 chỉ số, 0 biểu đồ, 0 bản ghi | T422 | `tests/integration/test_evaluate_bad_checkpoint.py::test_no_eval_dir_after_checkpoint_error` | entrypoint | có |
| SC-006 | Bản ghi nêu seed run và định danh + hash checkpoint; 100% tệp con 2 giữ nguyên hash sau lượt đánh giá | T420 | `tests/integration/test_evaluate_storage.py::test_run_files_unchanged_by_evaluation`, `tests/integration/test_evaluate_storage.py::test_report_names_seed_and_checkpoint_hash` | entrypoint | có |

<a id="truy-vet-nguoc-task-ma"></a>
## Truy vết ngược: task → mã

| Task | Hiện thực mã |
|---|---|
| T401 | FR-010 · NFR-HEADLESS-001 (extra `eval`) |
| T402 | FR-015 · FR-018 · INV-004 |
| T403 | FR-007 · FR-018 · INV-006 |
| T404 | FR-005 · FR-006 · NFR-STAT-001 · INV-006 |
| T405 | FR-002 · INV-002 |
| T406 | FR-003 · INV-003 · INV-007 · NFR-REPRO-001 |
| T407 | FR-002 · FR-003 · FR-016 · INV-002 · INV-003 |
| T408 | FR-004 · FR-010 · FR-016 · FR-017 |
| T409 | FR-008 · FR-009 · INV-001 |
| T410 | FR-010 · FR-011 · FR-012 · NFR-HEADLESS-001 |
| T411 | FR-013 · FR-014 · FR-017 · FR-019 · INV-004 · INV-005 · NFR-REL-001 |
| T412 | FR-001 · FR-002 · FR-008 · FR-014 · FR-015 · INV-001 · INV-002 · INV-004 · INV-005 |
| T413 | FR-001 · FR-007 · FR-015 · FR-018 · INV-006 |
| T414 | FR-013 · FR-020 |
| T415…T423 | test tích hợp theo story (AC-1…AC-5, FR, INV, NFR, SC như bảng trên) |
| T424 | AC-1…AC-5 · FR-020 · SC-001…SC-003 |
| T425 | INV-001 · INV-003 · INV-004 · INV-005 · INV-006 |
| T426 | đối chiếu AC-1…AC-5 · INV-001…INV-007 · NFR |

<a id="chua-truy-vet-duoc"></a>
## Chưa truy vết được

- Không có mã nào của `spec.md` thiếu task hoặc test dự kiến.
- **Phụ thuộc chéo feature chưa khai ở cột `depends_on`**: 001–003 chưa có `tasks.md` (chưa có id task), nên T405, T406, T409, T414 và T401 (phần sau task khung của 001/003) chỉ ghi bằng chữ ở mục "Phụ thuộc chéo feature" của `tasks.md`; bước converge/`plan_fix` phải bổ sung khi các `tasks.md` đó có.
- **Vỏ `scripts/evaluate.py` và `configs/eval_elbow.yaml` chưa có chủ**: `scripts/**` và `configs/**` ngoài vùng ghi của mọi vai (khoảng trống năng lực, plan.md mục "Quyết định ở bước tasks"). Mọi AC được chứng minh qua entrypoint `python -m mma_ai.evaluation.cli`; chuỗi lệnh `python scripts/evaluate.py` của AC-1…AC-5 chưa có test riêng cho tới khi vỏ có chủ (đề xuất `ai-sdlc capability propose`).
- **Kết quả đo trên checkpoint thật** (policy học được có tốt hơn random hay không) chưa biết: cơ chế kết luận được chứng minh bằng policy chất lượng đã biết (T417); mọi test hiện chỉ là dự kiến vì 001–003 chưa có mã.
