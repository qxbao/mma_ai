---
id: "QS-004"
title: "M1 (3/4) — Quickstart kiểm chứng"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "004-eval-vs-random-plots"
version: "1.0.0"
---

# Quickstart — kiểm chứng đánh giá so với random policy và biểu đồ

- [Điều kiện tiên quyết](#dieu-kien-tien-quyet)
- [Kịch bản 1 — Đánh giá hai policy trên cùng tập mục tiêu (AC-1, INV-002, INV-003)](#kich-ban-1-danh-gia-hai-policy-tren-cung-tap-muc-tieu-ac-1-inv-002-inv-003)
- [Kịch bản 2 — Kết luận theo tiêu chí khai trước (AC-2, INV-006, NFR-STAT-001)](#kich-ban-2-ket-luan-theo-tieu-chi-khai-truoc-ac-2-inv-006-nfr-stat-001)
- [Kịch bản 3 — Ba biểu đồ từ nhật ký (AC-3, NFR-HEADLESS-001)](#kich-ban-3-ba-bieu-do-tu-nhat-ky-ac-3-nfr-headless-001)
- [Kịch bản 4 — Tập đánh giá không giao tập train (AC-4, INV-001)](#kich-ban-4-tap-danh-gia-khong-giao-tap-train-ac-4-inv-001)
- [Kịch bản 5 — Lưu cùng hồ sơ run, không sửa dữ liệu con 2 (AC-1, INV-005)](#kich-ban-5-luu-cung-ho-so-run-khong-sua-du-lieu-con-2-ac-1-inv-005)
- [Kịch bản 6 — Checkpoint không tồn tại hoặc hỏng (AC-5, INV-004)](#kich-ban-6-checkpoint-khong-ton-tai-hoac-hong-ac-5-inv-004)
- [Kịch bản 7 — Tái lập theo seed (NFR-REPRO-001, INV-007, NFR-REL-001)](#kich-ban-7-tai-lap-theo-seed-nfr-repro-001-inv-007-nfr-rel-001)
- [Số đo ghi lại khi triển khai (không viết tay)](#so-do-ghi-lai-khi-trien-khai-khong-viet-tay)


Hướng dẫn chạy và kiểm chứng; KHÔNG chứa mã triển khai. Khuôn bản ghi: [contracts/eval-report.schema.json](contracts/eval-report.schema.json), [contracts/eval-config.schema.json](contracts/eval-config.schema.json); lệnh và mã thoát: [contracts/cli.md](contracts/cli.md); luật dữ liệu: [data-model.md](data-model.md). Các kịch bản dưới đây chưa chạy được cho đến khi 001–003 có mã (research Q11); số liệu trong `contracts/examples/` là ví dụ khuôn, không phải kết quả đo.

<a id="dieu-kien-tien-quyet"></a>
## Điều kiện tiên quyết

1. Môi trường: `uv sync --extra dev --extra rl --extra eval` (Python 3.11).
2. Một run của con 2 đã có checkpoint và nhật ký: ví dụ `uv run python scripts/train.py --stage elbow --seed 42 --config configs/train_elbow_smoke.yaml` → `runs/<run_id>/`.
3. Không cần màn hình: mọi kịch bản chạy được khi `DISPLAY` bỏ đặt.

<a id="kich-ban-1-danh-gia-hai-policy-tren-cung-tap-muc-tieu-ac-1-inv-002-inv-003"></a>
## Kịch bản 1 — Đánh giá hai policy trên cùng tập mục tiêu (AC-1, INV-002, INV-003)

1. `uv run python scripts/evaluate.py --checkpoint runs/<run_id>/checkpoints/latest.json; echo $?`
2. Test tự động thay cho đọc tay: `tests/integration/test_evaluate_cli.py::test_both_policies_same_targets`, `::test_all_metrics_present_with_ci`, `::test_actions_in_unit_interval`, `::test_abnormal_episode_counted_not_fatal`; `tests/unit/test_metrics.py::test_summarize_all_groups`.

Kỳ vọng: mã thoát 0 (hoặc 6 nếu thiếu biểu đồ — xem kịch bản 3); stdout in chỉ số hai policy; `report.json` hợp khuôn; `policies.learned.n_episodes` = `policies.random.n_episodes` = số mục tiêu kiểm thử × `repeats`; kết luận in kèm hiệu và khoảng tin cậy — kết quả cụ thể là số đo thật, không biết trước.

<a id="kich-ban-2-ket-luan-theo-tieu-chi-khai-truoc-ac-2-inv-006-nfr-stat-001"></a>
## Kịch bản 2 — Kết luận theo tiêu chí khai trước (AC-2, INV-006, NFR-STAT-001)

1. Chứng minh cơ chế bằng policy chất lượng đã biết: `tests/integration/test_verdict_known_policies.py::test_scripted_reaching_policy_is_better`, `::test_always_zero_policy_is_not_better`, `::test_identical_policies_not_better`.
2. Chứng minh thống kê bằng đáp án tay: `tests/unit/test_stats.py::test_wilson_matches_hand_values`, `::test_newcombe_matches_hand_values`, `::test_edge_counts_0_and_n_finite`, `::test_verdict_rule_ci_lower_gt_zero`, `::test_bootstrap_seeded_reproducible`.
3. Tiêu chí ghi trước kết quả: `tests/integration/test_evaluate_cli.py::test_criterion_in_report_and_no_override_flag`.

Kỳ vọng: 100% ca có đáp án đúng; mọi khoảng tin cậy hữu hạn và nằm trong miền hợp lệ; báo cáo nêu `criterion` và `limits` (kể cả khi "không tốt hơn").

<a id="kich-ban-3-ba-bieu-do-tu-nhat-ky-ac-3-nfr-headless-001"></a>
## Kịch bản 3 — Ba biểu đồ từ nhật ký (AC-3, NFR-HEADLESS-001)

1. `ls runs/<run_id>/eval/<eval_id>/charts/` → `loss.png`, `reward.png`, `activation.png`.
2. Test tự động: `tests/unit/test_training_log.py::test_reads_jsonl_and_tfevents`, `::test_missing_group_names_available_tags`; `tests/unit/test_charts.py::test_three_files_valid_png`, `::test_activation_has_six_named_lines`, `::test_points_match_log`, `::test_nonfinite_points_dropped_and_counted`; `tests/integration/test_evaluate_headless.py::test_evaluate_with_display_unset_exit0`, `::test_missing_activation_series_exit6_results_saved`.

Kỳ vọng: 3 ảnh PNG khác rỗng, activation có đúng 6 đường có nhãn tên cơ; thiếu một đại lượng ⇒ mã 6, kết quả số vẫn lưu, `charts.status = incomplete` kèm lý do, không có ảnh rỗng giả.

<a id="kich-ban-4-tap-danh-gia-khong-giao-tap-train-ac-4-inv-001"></a>
## Kịch bản 4 — Tập đánh giá không giao tập train (AC-4, INV-001)

1. Test tự động: `tests/unit/test_split_guard.py::test_disjoint_targets_and_min_distance_ok`, `::test_seed_equal_train_seed_rejected`, `::test_seed_range_overlap_rejected`, `::test_target_within_min_distance_rejected`, `::test_unknown_train_set_refused`, `::test_resume_chain_seeds_collected`, `::test_fingerprint_mismatch_rejected`; `tests/integration/test_evaluate_cli.py::test_leak_exits5_no_episode_run`.
2. Chạy tay (tuỳ chọn): `uv run python scripts/evaluate.py --checkpoint <ckpt> --eval-seed 42; echo $?` với run train seed 42 ⇒ kỳ vọng mã 5, thông báo nêu seed trùng, không có thư mục `eval`.

Kỳ vọng: giao mục tiêu = 0, khoảng cách nhỏ nhất ≥ `min_required_m`, báo cáo ghi kết quả phép kiểm; vi phạm ⇒ 0 episode được chạy.

<a id="kich-ban-5-luu-cung-ho-so-run-khong-sua-du-lieu-con-2-ac-1-inv-005"></a>
## Kịch bản 5 — Lưu cùng hồ sơ run, không sửa dữ liệu con 2 (AC-1, INV-005)

1. Test tự động: `tests/integration/test_evaluate_storage.py::test_report_names_seed_and_checkpoint_hash`, `::test_two_evals_two_dirs_first_unchanged`, `::test_run_files_unchanged_by_evaluation`, `::test_no_partial_dir_on_interrupt`, `::test_unwritable_eval_dir_exit7`.

Kỳ vọng: `report.json` nêu `run.seed`, `checkpoint.path`, `checkpoint.sha256`, seed đánh giá, cấu hình đầy đủ; hai lượt ⇒ hai thư mục `eval_id` khác nhau; băm mọi tệp của run (ngoài `eval`) trước/sau khớp.

<a id="kich-ban-6-checkpoint-khong-ton-tai-hoac-hong-ac-5-inv-004"></a>
## Kịch bản 6 — Checkpoint không tồn tại hoặc hỏng (AC-5, INV-004)

1. `uv run python scripts/evaluate.py --checkpoint runs/none/checkpoints/x.pt; echo $?` → kỳ vọng mã 4, thông báo nêu đường dẫn không tồn tại, stdout không có chỉ số.
2. Test tự động: `tests/integration/test_evaluate_cli.py::test_missing_checkpoint_exit4_no_output`, `::test_corrupt_checkpoint_exit4_names_cause`, `::test_missing_component_exit4`, `::test_xml_hash_mismatch_exit4`, `::test_no_eval_dir_after_checkpoint_error`.

Kỳ vọng: mã khác 0, thông báo nêu nguyên nhân, 0 chỉ số in ra, 0 bản ghi/biểu đồ/thư mục `eval` dở dang.

<a id="kich-ban-7-tai-lap-theo-seed-nfr-repro-001-inv-007-nfr-rel-001"></a>
## Kịch bản 7 — Tái lập theo seed (NFR-REPRO-001, INV-007, NFR-REL-001)

1. Test tự động: `tests/regression/test_eval_determinism.py::test_same_seed_same_actions_and_metrics`, `::test_diff_seed_diff_random_actions`; `tests/integration/test_report_contract.py::test_report_schema_and_no_nonfinite`, `::test_contract_examples_eval`.

Kỳ vọng: chuỗi hành động random giống hệt giữa hai lượt cùng seed và cùng loại thiết bị; chỉ số lệch ≤ 1×10⁻⁶; seed khác ⇒ chuỗi khác; không NaN/Infinity trong `report.json`.

<a id="so-do-ghi-lai-khi-trien-khai-khong-viet-tay"></a>
## Số đo ghi lại khi triển khai (không viết tay)

Thời gian chạy một lượt đánh giá và episode/giây do máy đo, ghi vào `report.timing`; không có ngân sách thời gian được khẳng định trước (master plan XI.10).
