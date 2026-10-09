---
id: "QS-005"
title: "M1 (4/4) — Quickstart kiểm chứng"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "005-replay-3d-muscle-demo"
version: "1.0.0"
---

# Quickstart — kiểm chứng replay 3D và demo bằng cơ

- [Điều kiện tiên quyết](#dieu-kien-tien-quyet)
- [Kịch bản 1 — Sinh một episode không cần màn hình rồi xem lại bằng mắt (AC-1, AC-2, INV-003)](#kich-ban-1-sinh-mot-episode-khong-can-man-hinh-roi-xem-lai-bang-mat-ac-1-ac-2-inv-003)
- [Kịch bản 2 — Demo trực tiếp từ checkpoint (AC-2, INV-002, NFR-REPRO-001)](#kich-ban-2-demo-truc-tiep-tu-checkpoint-ac-2-inv-002-nfr-repro-001)
- [Kịch bản 3 — Activation 6 cơ hiển thị và ghi lại (AC-1, AC-2, AC-3, INV-006)](#kich-ban-3-activation-6-co-hien-thi-va-ghi-lai-ac-1-ac-2-ac-3-inv-006)
- [Kịch bản 4 — Máy không có màn hình (AC-3, NFR-HEADLESS-001)](#kich-ban-4-may-khong-co-man-hinh-ac-3-nfr-headless-001)
- [Kịch bản 5 — Lệch mô hình không phát sai ngầm (AC-4, INV-001)](#kich-ban-5-lech-mo-hinh-khong-phat-sai-ngam-ac-4-inv-001)
- [Kịch bản 6 — Đường dẫn hoặc tệp không dùng được (AC-5, INV-004)](#kich-ban-6-duong-dan-hoac-tep-khong-dung-duoc-ac-5-inv-004)
- [Kịch bản 7 — Nhịp thời gian thực (AC-1, NFR-PERF-001)](#kich-ban-7-nhip-thoi-gian-thuc-ac-1-nfr-perf-001)
- [Kịch bản 8 — Ranh giới và hợp đồng (AC-1, NFR-REL-001, INV-005)](#kich-ban-8-ranh-gioi-va-hop-dong-ac-1-nfr-rel-001-inv-005)


Hướng dẫn chạy và kiểm chứng; KHÔNG chứa mã triển khai. Khuôn bản ghi: [contracts/episode.schema.json](contracts/episode.schema.json), [contracts/replay-summary.schema.json](contracts/replay-summary.schema.json), [contracts/replay-config.schema.json](contracts/replay-config.schema.json); lệnh và mã thoát: [contracts/cli.md](contracts/cli.md); luật dữ liệu: [data-model.md](data-model.md). Các kịch bản dưới đây chưa chạy được cho đến khi 001–003 có mã (research Q11); số liệu trong `contracts/examples/` là ví dụ khuôn, không phải kết quả đo.

<a id="dieu-kien-tien-quyet"></a>
## Điều kiện tiên quyết

1. Môi trường: `uv sync --extra dev --extra rl` (Python 3.11; con 4 không thêm extra).
2. Một run của con 2 đã có checkpoint: `uv run python scripts/train.py --stage elbow --seed 42 --config configs/train_elbow_smoke.yaml` → `runs/<run_id>/`.
3. Kịch bản 1 (bước xem bằng mắt) cần máy có màn hình; các kịch bản còn lại chạy được khi `DISPLAY` và `WAYLAND_DISPLAY` bỏ đặt.

<a id="kich-ban-1-sinh-mot-episode-khong-can-man-hinh-roi-xem-lai-bang-mat-ac-1-ac-2-inv-003"></a>
## Kịch bản 1 — Sinh một episode không cần màn hình rồi xem lại bằng mắt (AC-1, AC-2, INV-003)

1. Sinh và lưu episode (không màn hình): `uv run python scripts/replay.py --checkpoint runs/<run_id>/checkpoints/latest.json --headless --save-episode runs/<run_id>/replays/test0.episode.json; echo $?`
2. Xem lại: `uv run python scripts/replay.py --episode runs/<run_id>/replays/test0.episode.json --speed 0.1; echo $?` (máy có màn hình).
3. Test tự động thay cho đọc tay: `tests/integration/test_demo_cli.py::test_demo_saves_episode_headless`, `::test_demo_only_muscle_excitation_in_unit_interval`; `tests/unit/test_episode.py::test_write_read_roundtrip_and_schema`, `::test_refuse_overwrite`; `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` (nhánh có màn hình: viewer mở, phát đủ khung, mã 0).

Kỳ vọng: bước 1 mã 0 và in tóm tắt JSON; bước 2 mở cửa sổ, khuỷu tay chuyển động (tới mục tiêu hay không là số đo thật, không biết trước), bảng 6 activation đổi theo khung, đóng cửa sổ → mã 0.

<a id="kich-ban-2-demo-truc-tiep-tu-checkpoint-ac-2-inv-002-nfr-repro-001"></a>
## Kịch bản 2 — Demo trực tiếp từ checkpoint (AC-2, INV-002, NFR-REPRO-001)

1. `uv run python scripts/replay.py --checkpoint runs/<run_id>/checkpoints/latest.json --split test --target-index 3 --speed 0.25`
2. Test: `tests/integration/test_demo_cli.py::test_demo_same_seed_same_episode` (NFR-REPRO-001), `::test_demo_selects_requested_target`, `tests/unit/test_recorder.py::test_actions_checked_before_step`, `::test_recorder_never_writes_env_state`.

Kỳ vọng: mục tiêu hiện đúng chỉ số 3 của tập kiểm thử; hai lần chạy cùng checkpoint/seed cho hai episode giống nhau (≤ 1×10⁻⁶).

<a id="kich-ban-3-activation-6-co-hien-thi-va-ghi-lai-ac-1-ac-2-ac-3-inv-006"></a>
## Kịch bản 3 — Activation 6 cơ hiển thị và ghi lại (AC-1, AC-2, AC-3, INV-006)

1. `uv run python scripts/replay.py --episode runs/<run_id>/replays/test0.episode.json --headless | uv run python -m json.tool`
2. Test: `tests/unit/test_playback.py::test_hud_shows_recorded_activation_each_frame`, `::test_hud_names_match_muscle_names`, `tests/unit/test_hud.py::test_rounding_only_in_display`, `tests/unit/test_summary.py::test_activation_stats_match_hand_values`, `tests/integration/test_replay_headless.py::test_summary_has_all_fields`.

Kỳ vọng: tóm tắt nêu với từng cơ activation nhỏ nhất/lớn nhất/trung bình/cuối khớp tính tay; HUD ở mỗi khung hiện đúng 6 giá trị của khung đó.

<a id="kich-ban-4-may-khong-co-man-hinh-ac-3-nfr-headless-001"></a>
## Kịch bản 4 — Máy không có màn hình (AC-3, NFR-HEADLESS-001)

1. `env -u DISPLAY -u WAYLAND_DISPLAY uv run python scripts/replay.py --episode <path>; echo $?` → thông báo tiếng Việt nêu thiếu màn hình và gợi ý `--headless`, mã 7, trong ≤ 5 s.
2. `env -u DISPLAY -u WAYLAND_DISPLAY uv run python scripts/replay.py --episode <path> --headless; echo $?` → tóm tắt JSON, mã 0.
3. Test: `tests/integration/test_replay_nodisplay.py::test_no_display_exits_7_fast_with_hint`, `::test_headless_exit0_with_summary`, `::test_bogus_display_handled_like_no_display`, `tests/integration/test_visualization_imports.py::test_headless_never_imports_viewer`.

<a id="kich-ban-5-lech-mo-hinh-khong-phat-sai-ngam-ac-4-inv-001"></a>
## Kịch bản 5 — Lệch mô hình không phát sai ngầm (AC-4, INV-001)

1. Sửa hash `model.sha256` trong một bản sao episode rồi `uv run python scripts/replay.py --episode <bản sao> --headless; echo $?` → nêu cả hai hash, mã 6.
2. Với `--allow-model-mismatch` (cấu trúc tương thích) → tiếp tục, `model_check.match = false`, `warnings` có "MÔ HÌNH LỆCH".
3. Test: `tests/integration/test_replay_model_mismatch.py::test_mismatch_stops_names_both_hashes`, `::test_mismatch_allowed_warns_persistently`, `::test_incompatible_structure_always_refused`, `tests/unit/test_model_check.py::test_hash_and_structure_cases`.

<a id="kich-ban-6-duong-dan-hoac-tep-khong-dung-duoc-ac-5-inv-004"></a>
## Kịch bản 6 — Đường dẫn hoặc tệp không dùng được (AC-5, INV-004)

1. `uv run python scripts/replay.py --episode runs/khong-ton-tai.episode.json; echo $?` → lỗi nêu đường dẫn, mã 5, không mở viewer.
2. Test: `tests/integration/test_replay_bad_input.py::test_missing_episode_exit5`, `::test_corrupt_json_exit5_names_field`, `::test_nonfinite_values_exit5`, `::test_missing_checkpoint_exit4_no_viewer_no_file`, `::test_both_or_neither_mode_exit2`, `::test_existing_save_path_exit8_not_overwritten`, `::test_interrupt_leaves_no_partial_episode`.

<a id="kich-ban-7-nhip-thoi-gian-thuc-ac-1-nfr-perf-001"></a>
## Kịch bản 7 — Nhịp thời gian thực (AC-1, NFR-PERF-001)

1. Test: `tests/unit/test_pacing.py::test_ratio_within_5pct_at_speed_1` (đồng hồ giả, episode 0,2–4 s), `::test_late_frames_reported_not_dropped`, `::test_single_frame_episode_no_zero_division`, `::test_loop_repeats_until_sink_closed`.
2. Ghi tay trên máy có màn hình: tỷ lệ thực in cuối phiên (`ratio`, `frames_late`) — số đo thật, không là cam kết.

<a id="kich-ban-8-ranh-gioi-va-hop-dong-ac-1-nfr-rel-001-inv-005"></a>
## Kịch bản 8 — Ranh giới và hợp đồng (AC-1, NFR-REL-001, INV-005)

Test: `tests/integration/test_contract_examples_replay.py::test_examples_match_schemas`, `::test_no_nonfinite_values`, `tests/integration/test_visualization_imports.py::test_visualization_has_no_training_imports`, `::test_episode_path_does_not_import_torch`, `tests/integration/test_replay_readonly.py::test_run_files_unchanged_by_replay_and_demo`.
