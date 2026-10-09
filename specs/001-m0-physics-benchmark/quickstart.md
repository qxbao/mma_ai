---
id: "QS-001"
title: "M0 — Hướng dẫn kiểm chứng nhanh (Quickstart)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "001-m0-physics-benchmark"
version: "1.0.0"
---

# Quickstart — kiểm chứng M0

Hướng dẫn chạy để chứng minh M0 hoạt động. Lệnh và đầu ra: `contracts/cli.md`; khuôn tệp: `contracts/*.schema.json`; thực thể: `data-model.md`. Chỉ thực hiện sau khi các task triển khai đã dựng mã. Mọi tên test dưới đây là tên **kế hoạch**; chưa chạy nghĩa là chưa có kết quả (INV-001).

**Điều kiện tiên quyết**: `uv` đã cài; Linux/WSL2 Ubuntu; (cho AC-4) driver NVIDIA nhìn thấy GPU từ WSL2.

## Kịch bản 1 — Dựng môi trường & nạp mô hình 6 cơ (AC-1, AC-5, INV-004)

1. `uv python install 3.11`
2. `uv sync --extra dev` (thêm `--extra gpu` khi cần đo GPU)
3. `python scripts/check_env.py` → ghi `env.json`; mở tệp xác nhận Python 3.11, phiên bản mujoco/myo-sim.
4. Test tự động thay cho đọc tay: `tests/unit/test_body_model.py::test_loads_exactly_six_muscles`, `::test_no_non_muscle_actuators`, `::test_muscle_name_order_matches_data_model`.

Kỳ vọng: `n_muscles = 6`, `n_non_muscle_actuators = 0`, hash mô hình in ra.

## Kịch bản 2 — Smoke test không NaN/Inf, không lỗi vật lý (AC-1, AC-2, INV-004)

1. `python scripts/smoke_test.py --seed 42`
2. Kỳ vọng: dòng cuối `NaN=0 Inf=0 WARN=0 PASS`, mã thoát 0, `logs/m0/<run_id>/smoke.json` hợp `contracts/smoke-result.schema.json`.
3. Test tự động: `tests/integration/test_smoke_cli.py::test_smoke_passes_and_matches_schema`; từ chối vector sai: `tests/unit/test_activation_validation.py` (sai kích thước, <0, >1, NaN, Inf); quét: `tests/unit/test_numeric_health.py`; lực trong ngưỡng: `tests/unit/test_force_bound.py` (kèm quét toàn dải góc — xác nhận công thức ngưỡng ở research Q3).
4. Ca âm: `tests/integration/test_smoke_cli.py::test_smoke_exits_nonzero_on_injected_nan` (tiêm NaN vào mô hình giả lập hỏng bằng `monkeypatch` trên hàm quét, không đổi vật lý thật) → mã thoát 1 và nêu đại lượng/bước/mẫu.

## Kịch bản 3 — Tất định theo seed (AC-2, INV-002, NFR-REPRO-001)

1. Chạy `smoke_test.py --seed 42` hai lần.
2. Test tự động: `tests/regression/test_determinism.py::test_same_seed_same_verdict_and_fingerprint` so `passed`, `totals`, `trajectory_fingerprint`; `::test_different_seed_changes_random_samples`.

Kỳ vọng: không khác biệt. Nếu khác ⇒ ghi vào "vấn đề còn lại" của báo cáo nghiệm thu.

## Kịch bản 4 — Benchmark CPU + RAM đỉnh (AC-3, AC-4, NFR-PERF-001, INV-001)

1. `python scripts/benchmark.py --seed 42`
2. Kỳ vọng: `benchmark.json` hợp schema; mỗi kết quả có ≥ 5 giá trị lặp, median > 0, `cv` được báo; `peak_ram_mb` > 0; mã thoát 0.
3. Test tự động: `tests/integration/test_benchmark_cli.py::test_benchmark_report_matches_schema_and_has_min_repeats`, `::test_benchmark_rejects_fewer_than_five_repeats` (mã thoát 2); `tests/unit/test_stats.py` (median/stdev/cv tính đúng trên vectơ cố định).
4. Nhiễu nền: chạy benchmark khi một tiến trình khác đang bận CPU và đọc `cv` — không có test tự động (ghi tay vào báo cáo nếu thực hiện).

## Kịch bản 5 — GPU/CUDA (AC-4, INV-001)

1. `python scripts/check_env.py` rồi `python scripts/benchmark.py` trên máy đích.
2. Kỳ vọng trên máy có GPU: `cuda.available = true`, `arch_supported = true` (RTX 5060 cần `sm_120` — research Q6), `gpu.tensor_op_ok = true`, `total_mb` và `peak_allocated_mb` là số đo.
3. Kỳ vọng trên máy không GPU: `gpu.available = false`, các số `null`, `reason` khác null; AC-4 = `chua_dat`.
4. Test tự động: `tests/unit/test_gpu_probe.py::test_probe_without_cuda_returns_reason_not_numbers` (giả lập thiếu CUDA bằng `monkeypatch`) — kiểm hành vi dự phòng, KHÔNG thay thế phép đo trên máy đích (bước 1–2 là bằng chứng duy nhất cho AC-4 đạt).

## Kịch bản 6 — Báo cáo nghiệm thu & cổng M0 (AC-1…AC-5, NFR-DOC-001, INV-001, INV-003)

1. `python scripts/m0_report.py`
2. Kỳ vọng: `acceptance.json` có đủ 5 tiêu chí; `acceptance.md` theo mẫu báo cáo cột mốc (Milestone · Các thành phần hoàn thành · Các file được tạo/sửa · Cách chạy · Test đã chạy và kết quả · Benchmark · Vấn đề còn lại · Tiêu chí nghiệm thu đã đạt/chưa đạt · Đề xuất milestone tiếp theo); `gate_open = true` chỉ khi cả 5 AC = `dat`.
3. Test tự động: `tests/unit/test_acceptance.py::test_no_dat_without_evidence`, `::test_missing_gpu_keeps_gate_closed`, `::test_report_has_five_criteria`; `tests/unit/test_runlog.py::test_rejects_absolute_paths_and_nan` (INV-003, INV-001); `tests/integration/test_repo_hygiene.py::test_no_absolute_home_paths_in_tracked_text` (quét mã/tài liệu theo mẫu `/home/`, `/mnt/`, `C:\\`).

## Kịch bản 7 — Lệnh chưa triển khai & dựng lại sạch (AC-5, FR-016)

1. `python scripts/train.py --stage elbow --seed 42; echo $?` → in `chưa triển khai (M0)`, mã 3. Test: `tests/integration/test_unimplemented_cli.py::test_train_evaluate_replay_exit_3`.
2. Dựng lại sạch: xoá `.venv`, làm đúng `README.md` từ đầu đến smoke test đạt. **Không có test tự động** — người thực hiện ghi bước mơ hồ vào báo cáo; tiêu chí AC-5 chỉ `dat` khi `uv.lock` đã được tạo sau một smoke test đạt (kiểm: `tests/integration/test_repo_hygiene.py::test_lockfile_exists_and_pins_core_libs`).
