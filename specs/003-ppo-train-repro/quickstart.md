---
id: "QS-003"
title: "M1 (2/4) — Hướng dẫn kiểm chứng nhanh (Quickstart)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "003-ppo-train-repro"
version: "1.1.0"
---

# Quickstart — kiểm chứng huấn luyện PPO, checkpoint, hồ sơ và giao diện quan sát

Lệnh: `contracts/cli.md`; API: `contracts/python-api.md`; khuôn bản ghi: `contracts/*.schema.json`; thực thể: `data-model.md`. Chỉ thực hiện sau khi các task triển khai đã dựng mã, con 1 (`002-elbow-muscle-env`) đã xanh và M0 (001) đã có mã. Mọi tên test dưới đây là tên **kế hoạch**; chưa chạy nghĩa là chưa có kết quả.

**Điều kiện tiên quyết**: `uv` đã cài; Linux/WSL2 Ubuntu; `uv sync --extra dev --extra rl`; mã của 001 và 002.

## Kịch bản 1 — Lượt train ngắn (smoke), 0 NaN/Inf, TensorBoard + checkpoint (AC-1, NFR-REL-001, NFR-HEADLESS-001, INV-002, INV-003)

1. `uv run python scripts/train.py --stage elbow --seed 42 --config configs/train_elbow_smoke.yaml`
2. Test tự động thay cho đọc tay: `tests/integration/test_train_cli.py::test_smoke_train_exit0`, `::test_tensorboard_scalars_present`, `::test_periodic_and_final_checkpoint`, `::test_actions_in_unit_interval`; `tests/integration/test_train_headless.py::test_smoke_without_display`; `tests/integration/test_train_split.py::test_training_only_uses_train_split`; `tests/integration/test_train_nan_guard.py::test_nan_loss_stops_without_checkpoint`.

Kỳ vọng: mã thoát 0; `runs/<run_id>/` có `tb/`, `checkpoints/` (≥ 1 tệp `.pt`), `manifest.json` `status:"done"`; `numeric_health` = 0/0; chuỗi loss, reward, `activation/<tên cơ>` (6 cơ) có trong TensorBoard; mọi `reset` trong lúc train báo `target_split == "train"`.

## Kịch bản 2 — Lưu, nạp checkpoint, train tiếp (AC-2, INV-004)

1. `uv run python -m pytest -q tests/unit/test_checkpoint.py tests/integration/test_resume.py`
2. Kỳ vọng: `test_roundtrip_same_action` (lô 64 observation, sai khác tuyệt đối ≤ 1×10⁻⁶), `test_missing_component_raises`, `test_shape_mismatch_raises`, `test_nan_not_written`, `test_atomic_write_no_partial`, `test_resume_creates_new_run_with_parent`, `test_resume_restores_normalizer_optimizer_rng`, `test_resume_refused_when_xml_hash_differs`.
3. Chạy tay (tuỳ chọn): `uv run python scripts/train.py --stage elbow --seed 42 --config configs/train_elbow_smoke.yaml --resume runs/<run_id>/checkpoints/latest.json`.

## Kịch bản 3 — Hồ sơ thí nghiệm đủ trường (AC-3, NFR-RES-001, INV-001)

1. `uv run python -m pytest -q tests/integration/test_manifest_contract.py tests/unit/test_run_dir.py tests/unit/test_manifest.py`
2. Kỳ vọng: `test_manifest_fields_and_schema` (seed, config, phiên bản thư viện, hash XML, checkpoint, reward metrics, env steps/s, wall-clock, tài nguyên — 100% trường có mặt), `test_manifest_hash_matches_env_model_record`, `test_resources_fields_null_explicit` (không GPU ⇒ `null`, không bỏ trường), `test_two_runs_two_dirs` (hai run liên tiếp cùng seed ⇒ hai thư mục, run cũ không đổi), `test_unique_dirs_no_overwrite`, `tests/unit/test_manifest.py::test_throughput_and_wallclock_measured` (env steps/s và wall-clock do máy đo, FR-013).

## Kịch bản 4 — Tái lập theo seed (AC-4, NFR-REPRO-001)

1. `uv run python -m pytest -q tests/regression/test_train_determinism.py tests/unit/test_repro.py`
2. Kỳ vọng: `test_same_seed_head_curve_within_tolerance` (hai run smoke cùng seed/cấu hình/thiết bị: lệch tương đối ≤ 1×10⁻⁶ tại mỗi điểm, K = min(10, số lượt)), `test_diff_seed_differs`, `test_manifest_records_tolerance`, `test_compare_within_tolerance`, `test_compare_outside`.
3. Chạy tay: `uv run python scripts/compare_runs.py runs/<run_a> runs/<run_b>` (mã thoát 0 = trong dung sai).

## Kịch bản 5 — Cấu trúc mạng 2×256, chuẩn hoá, gradient clipping, PPO đúng (AC-6, FR-002…FR-004)

1. `uv run python -m pytest -q tests/unit/test_networks.py tests/unit/test_normalizer.py tests/unit/test_ppo.py tests/unit/test_train_config.py`
2. Kỳ vọng: `test_actor_critic_2x256`, `test_config_changes_structure`, `test_action_always_in_unit_interval`, `test_matches_numpy_stats`, `test_grad_norm_after_clip_le_threshold`, `test_gae_matches_hand_computed`, `test_learns_toy_env`, `test_invalid_values_raise`.

## Kịch bản 6 — Stage chưa triển khai (AC-5)

1. `uv run python scripts/train.py --stage balance --seed 42; echo $?`
2. Test tự động: `tests/integration/test_train_cli.py::test_stage_not_implemented_exit3`, `::test_no_run_dir_for_unimplemented`.

Kỳ vọng: thông báo "chưa triển khai", mã thoát 3 (khác 0), không có thư mục run mới.

## Kịch bản 7 — Giao diện quan sát khi đang train (AC-7, NFR-PERF-001, NFR-PERF-002, INV-005)

1. Chạy train nền với giao diện web (mặc định): `uv run python scripts/train.py --stage elbow --seed 42 --ui web &` rồi mở URL được in ra (`http://127.0.0.1:<cổng>/`); mở thêm TensorBoard: `uv run tensorboard --logdir runs`.
2. Test tự động: `tests/integration/test_dashboard.py::test_progress_endpoint_matches_schema`, `::test_page_lists_required_panels`, `::test_snapshot_latency_le_5s`, `::test_dashboard_is_read_only`, `::test_dashboard_loopback_only`, `::test_train_survives_ui_failure`; `tests/unit/test_progress.py::test_snapshot_atomic_and_schema`; `tests/integration/test_monitoring_imports.py::test_monitoring_has_no_training_imports`.
3. Chi phí: `uv run python scripts/benchmark_train.py --seed 42 --repeats 5` ⇒ `logs/m1/benchmark_train.json` (`passed:true` khi trung vị env steps/s bật ≥ 0,90 × tắt); test cấu trúc `tests/integration/test_benchmark_train.py::test_benchmark_schema_and_ratio`.
4. Hiển thị 3D (tuỳ chọn, cần màn hình): thêm `--view3d`; `tests/integration/test_viewer3d.py::test_view3d_off_by_default`, `::test_view3d_unavailable_without_display_does_not_break_train`.

Kỳ vọng: giao diện hiện reward, loss, kích hoạt 6 cơ, env steps/s, số bước đã chạy / tổng, trạng thái checkpoint; số liệu mới xuất hiện ≤ 5 giây; tắt/đóng giao diện hoặc cổng bị chiếm không dừng train; không thao tác nào trên giao diện đổi được policy hay cấu hình.

## Kịch bản 8 — Hợp đồng bản ghi và phụ thuộc (AC-3, AC-7)

1. `uv run python -m pytest -q tests/integration/test_contract_examples_train.py tests/integration/test_dependency_train.py`
2. Kỳ vọng: mọi tệp ở `contracts/examples/` hợp schema tương ứng (draft 2020-12, có registry cho `$ref`) và đầu ra thật của `build_manifest`, `save_checkpoint`, `ProgressWriter` hợp schema; `torch` + `tensorboard` nằm trong extra `rl`, `stable-baselines3` KHÔNG có trong `pyproject.toml`/`uv.lock`, `myosuite` không có.
