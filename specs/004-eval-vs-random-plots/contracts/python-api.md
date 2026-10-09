---
id: "API-004"
title: "M1 (3/4) — Hợp đồng API Python"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "004-eval-vs-random-plots"
version: "1.0.0"
---

# Hợp đồng — API Python của gói `mma_ai.evaluation`

API mà `scripts/evaluate.py` và test gọi; con 4 (replay/demo) không bắt buộc dùng. Dạng dây của bản ghi: xem `*.schema.json` (không chép tên trường ở đây). Lệnh CLI và mã thoát: [cli.md](cli.md). `API-EVL-*` là mã hàm Python (không có HTTP).

## Hàm và lớp

| Mã | Ký hiệu | Mô-đun | Hợp đồng | FR |
|---|---|---|---|---|
| `API-EVL-0001` | `EvalConfig.load(path=None, overrides=None) -> EvalConfig` | `evaluation.eval_config` | Đọc `configs/eval_elbow.yaml` (khuôn [eval-config.schema.json](eval-config.schema.json)); ném `EvalConfigError` nêu khoá/giá trị sai (≤ 0, mức tin cậy ngoài (0,1), thiếu khoá, `min_targets < 2`) | FR-007, FR-018 |
| `API-EVL-0002` | `evaluate_checkpoint(checkpoint, cfg, out_dir=None) -> EvalResult` | `evaluation.runner` | Điều phối đúng thứ tự ở `cli.md`; trả đường dẫn thư mục công bố, báo cáo và trạng thái biểu đồ; ném `CheckpointUnusable` / `LeakageError` / `EvalConfigError` / `EvalWriteError` tương ứng mã thoát | FR-001, FR-013…FR-015 |
| `API-EVL-0003` | `check_disjoint(run, cfg, pair) -> DisjointnessReport` | `evaluation.split_guard` | Kiểm giao rỗng mục tiêu, khoảng cách tối thiểu theo `pair` của con 1, seed episode `[base, base + n)` và seed random policy so với mọi seed train; ném `LeakageError` nêu mục tiêu/seed vi phạm; ném `TrainSetUnknown` khi không thiết lập được | FR-008, FR-009 |
| `API-EVL-0004` | `RandomPolicy(seed, act_dim=6)` · `LearnedPolicy(checkpoint)` | `evaluation.policies` | Giao diện chung `act(obs_raw) -> u ∈ [0,1]^6`; `RandomPolicy` không nhìn observation và dùng MỘT bộ sinh xuyên suốt lượt; `LearnedPolicy` bọc `load_policy(...).act_deterministic` của 003 | FR-003 |
| `API-EVL-0005` | `run_policy_on_targets(env, policy, n_targets, repeats, seed_base) -> list[EpisodeRecord]` | `evaluation.rollout` | Mỗi mục tiêu `i`, mỗi lần lặp: `reset(seed=seed_base + k, options={"split": "test", "target_index": i})`; kiểm hành động hữu hạn và trong `[0,1]^6` trước `step`; bắt `PhysicsInstabilityError` ⇒ episode `abnormal`; không dừng lượt | FR-002, FR-016 |
| `API-EVL-0006` | `summarize(records, cfg) -> PolicyResult` · `aggregate_per_target(records)` | `evaluation.metrics` | Tính bảy nhóm chỉ số; `null` + `reason` khi không có dữ liệu hợp lệ (FR-017); đếm NaN/Inf riêng, không đưa vào trung bình | FR-004, FR-016, FR-017 |
| `API-EVL-0007` | `wilson_interval(k, n, level)` · `newcombe_difference(k1, n1, k2, n2, level)` · `bootstrap_mean_ci(x, level, resamples, seed)` · `decide(learned, random, level) -> Verdict` | `evaluation.stats` | Wilson, Newcombe (phương pháp 10) giải tích; bootstrap phân vị có seed; `Verdict.better ⇔ ci_low > 0`; hữu hạn và trong miền hợp lệ ở mọi đầu vào hợp lệ kể cả `k ∈ {0, n}` | FR-005, FR-006, NFR-STAT-001 |
| `API-EVL-0008` | `read_training_log(run_dir, cfg) -> TrainingLog` | `evaluation.metrics` | Đọc `metrics.jsonl` hoặc tfevents (cấu hình `logs.source`) thành bảng dài `(series, step, value)`; ném `LogMissing` nêu nhóm thiếu và thẻ thực có | FR-010, FR-011 |
| `API-EVL-0009` | `render_charts(log, muscle_names, out_dir, cfg) -> ChartResult` | `evaluation.charts` | Backend `Agg`; tạo `loss.png`, `reward.png`, `activation.png`; trả `ChartData` (đường, số điểm, bước đầu/cuối) để test kiểm nội dung; bỏ điểm không hữu hạn và đếm; một biểu đồ lỗi không làm mất biểu đồ khác | FR-010…FR-012 |
| `API-EVL-0010` | `build_report(...) -> dict` · `publish_report(tmp_dir, eval_dir) -> Path` | `evaluation.report` | Dựng báo cáo theo [eval-report.schema.json](eval-report.schema.json), từ chối NaN/Infinity; `publish_report` đổi tên thư mục tạm thành thư mục công bố (bước duy nhất làm kết quả xuất hiện) | FR-013, INV-004 |

## Quy tắc xuyên suốt

- `evaluation.*` chỉ ĐỌC checkpoint, hồ sơ và nhật ký của con 2; mọi ghi vào thư mục `eval` của run (INV-005). `evaluation` không import `learning.trainer` / `learning.ppo` (chỉ `learning.checkpoint`), kiểm bằng `test_evaluation_has_no_training_imports`.
- Chỉ số tính từ `EpisodeRecord`; không hàm nào đọc lại trạng thái môi trường ngoài `info` của `reset`/`step` (không có đường điều khiển lực, góc khớp hay toạ độ tay — INV-003).
- Lỗi hiển thị cho người dùng bằng tiếng Việt, nêu giá trị/ngữ cảnh.
