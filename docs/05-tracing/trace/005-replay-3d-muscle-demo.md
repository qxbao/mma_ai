---
id: "TRACE-005"
title: "Ma trận truy vết 005-replay-3d-muscle-demo"
doc_type: tracing
owner_agent: spec
status: draft
updated: "2026-10-09"
---

# Ma trận truy vết 005-replay-3d-muscle-demo

- [Ma trận](#ma-tran)
- [Truy vết ngược: task → mã](#truy-vet-nguoc-task-ma)
- [Chưa truy vết được](#chua-truy-vet-duoc)

> Đích: `docs/05-tracing/trace/005-replay-3d-muscle-demo.md` (`trace-matrix.md` là chỉ mục máy sinh, không sửa tay). Nguồn: `specs/005-replay-3d-muscle-demo/spec.md` (yêu cầu) và `specs/005-replay-3d-muscle-demo/tasks.md` (task `T501`…`T523`).
> Mức `entrypoint` = test chạy qua lệnh CLI thật `python -m mma_ai.visualization.cli` (subprocess; vỏ `python scripts/replay.py` chưa có chủ — xem cuối tệp) hoặc viewer thật; mức `unit` = test mô-đun đơn lẻ. Tên hàm test là tên dự kiến theo `plan.md` và `tasks.md`; chưa có mã nên cột trạng thái ghi "có" nghĩa là đã có task + test dự kiến, KHÔNG có nghĩa test đã chạy xanh.

<a id="ma-tran"></a>
## Ma trận

| Mã | Yêu cầu (spec.md) | Task (tasks.md) | Test / cổng máy | Mức | Trạng thái |
|---|---|---|---|---|---|
| AC-1 | Cho episode đã lưu, chạy lệnh replay `--episode <path>` thì MuJoCo Viewer mở và phát lại chuyển động khuỷu tay, thoát mã 0 | T514, T515, T519, T521 | `tests/e2e/test_replay_acceptance.py::test_ac_1_replay_episode`, `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` | entrypoint | có |
| AC-2 | Cho checkpoint, chạy demo thì khuỷu tay chuyển động tới mục tiêu và hiển thị activation 6 cơ | T513, T518, T521 | `tests/e2e/test_replay_acceptance.py::test_ac_2_demo_from_checkpoint`, `tests/integration/test_demo_cli.py::test_demo_saves_episode_headless` | entrypoint | có |
| AC-3 | Môi trường không có display: báo lỗi rõ hoặc chạy chế độ không màn hình, không treo | T511, T516, T521 | `tests/e2e/test_replay_acceptance.py::test_ac_3_no_display`, `tests/integration/test_replay_nodisplay.py::test_no_display_exits_7_fast_with_hint` | entrypoint | có |
| AC-4 | Episode có hash XML khác mô hình hiện tại: cảnh báo lệch mô hình, không phát lại sai ngầm | T506, T517, T521 | `tests/e2e/test_replay_acceptance.py::test_ac_4_model_mismatch`, `tests/integration/test_replay_model_mismatch.py::test_mismatch_stops_names_both_hashes` | entrypoint | có |
| AC-5 | Đường dẫn episode không tồn tại: báo lỗi rõ, mã thoát khác 0 | T504, T517, T521 | `tests/e2e/test_replay_acceptance.py::test_ac_5_missing_path`, `tests/integration/test_replay_bad_input.py::test_missing_episode_exit5` | entrypoint | có |
| INV-001 | Replay không phát lại sai ngầm: hash XML lệch ⇒ dừng, hoặc chỉ khi có cờ tường minh và cấu trúc tương thích ⇒ phát kèm cảnh báo liên tục | T506, T510, T514, T517, T522 | `tests/integration/test_replay_model_mismatch.py::test_mismatch_allowed_warns_persistently`, `tests/integration/test_replay_model_mismatch.py::test_incompatible_structure_always_refused`, `tests/challenge/test_replay_invariants.py` (đột biến hash/cấu trúc) | entrypoint | có |
| INV-002 | Đường điều khiển duy nhất là kích thích cơ `u_i ∈ [0,1]`; lớp hiển thị không ghi lực, góc khớp hay toạ độ tay | T505, T512, T513, T518, T522 | `tests/integration/test_demo_cli.py::test_demo_only_muscle_excitation_in_unit_interval`, `tests/unit/test_recorder.py::test_actions_checked_before_step`, `tests/challenge/test_replay_invariants.py` (hành động NaN/ngoài biên) | entrypoint | có |
| INV-003 | Episode tự đủ để phát lại đúng mô hình: luôn có seed, hash XML, 6 tên cơ, phiên bản; giá trị không áp dụng ghi `null`, không NaN/Infinity | T504, T520, T522 | `tests/unit/test_episode.py::test_required_provenance_fields`, `tests/integration/test_contract_examples_replay.py::test_examples_match_schemas`, `tests/challenge/test_replay_invariants.py` (đổi/xoá trường) | entrypoint | có |
| INV-004 | Khi lỗi: thoát mã khác 0, không treo, không viewer nửa vời, không tệp episode dở dang | T502, T514, T517, T522 | `tests/integration/test_replay_bad_input.py::test_interrupt_leaves_no_partial_episode`, `tests/unit/test_episode.py::test_atomic_write_no_partial`, `tests/challenge/test_replay_invariants.py` (ngắt/ghi lỗi) | entrypoint | có |
| INV-005 | Replay và demo chỉ đọc checkpoint, hồ sơ run, nhật ký train, episode nguồn; đầu ra là tệp mới, không ghi đè | T504, T514, T518, T522 | `tests/integration/test_replay_readonly.py::test_run_files_unchanged_by_replay_and_demo`, `tests/integration/test_replay_bad_input.py::test_existing_save_path_exit8_not_overwritten` | entrypoint | có |
| INV-006 | Activation hiển thị bằng giá trị trong episode/mô phỏng; làm tròn chỉ ở hiển thị, không ở dữ liệu ghi hay tóm tắt | T507, T509, T510 | `tests/unit/test_hud.py::test_rounding_only_in_display`, `tests/unit/test_summary.py::test_activation_stats_match_hand_values`, `tests/integration/test_replay_headless.py::test_summary_has_all_fields` | entrypoint | có |
| NFR-PERF-001 | Nhịp thời gian thực: tỷ lệ thời gian phát / mô phỏng ∈ [0,95 ; 1,05] ở hệ số 1,0 trên đồng hồ giả; khung chậm thì báo tỷ lệ thực | T508, T510 | `tests/unit/test_pacing.py::test_ratio_within_5pct_at_speed_1`, `tests/unit/test_pacing.py::test_late_frames_reported_not_dropped` | unit | có |
| NFR-HEADLESS-001 | `--headless` thoát mã 0 với tóm tắt đủ trường; không `--headless` thoát mã khác 0 trong ≤ 5 s khi không có màn hình | T511, T516 | `tests/integration/test_replay_nodisplay.py::test_headless_exit0_with_summary`, `tests/integration/test_replay_nodisplay.py::test_no_display_exits_7_fast_with_hint` | entrypoint | có |
| NFR-REPRO-001 | Hai lần demo không màn hình cùng checkpoint, seed, mục tiêu cho chuỗi hành động giống hệt và trường số lệch ≤ 1×10⁻⁶ | T513, T518 | `tests/integration/test_demo_cli.py::test_demo_same_seed_same_episode` | entrypoint | có |
| NFR-REL-001 | 0 NaN và 0 Inf trong episode/tóm tắt do hệ thống ghi; episode nạp có giá trị không hữu hạn bị từ chối | T504, T507, T517, T520 | `tests/unit/test_episode.py::test_nonfinite_rejected`, `tests/integration/test_replay_bad_input.py::test_nonfinite_values_exit5`, `tests/integration/test_contract_examples_replay.py::test_no_nonfinite_values` | entrypoint | có |
| FR-001 | Lệnh `--episode` mở MuJoCo Viewer, phát đúng thứ tự khung từ đầu tới cuối | T510, T512, T514, T519 | `tests/unit/test_playback.py::test_frames_in_recorded_order`, `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` | entrypoint | có |
| FR-002 | Chế độ demo `--checkpoint`; hai chế độ loại trừ nhau, thiếu cả hai hoặc có cả hai là lỗi tham số | T513, T514, T515, T518 | `tests/integration/test_demo_cli.py::test_demo_saves_episode_headless`, `tests/integration/test_replay_bad_input.py::test_both_or_neither_mode_exit2` | entrypoint | có |
| FR-003 | Hành động demo chỉ là kích thích cơ `u_i ∈ [0,1]`, xác định; không position controller; replay chỉ đặt trạng thái đã ghi | T505, T513, T518 | `tests/unit/test_recorder.py::test_recorder_never_writes_env_state`, `tests/integration/test_demo_cli.py::test_demo_only_muscle_excitation_in_unit_interval` | entrypoint | có |
| FR-004 | Viewer hiển thị mục tiêu đúng vị trí, tách biệt khỏi thân khuỷu, suốt phiên phát | T510, T512, T519 | `tests/unit/test_playback.py::test_target_marker_at_recorded_position`, `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` | entrypoint | có |
| FR-005 | Viewer hiển thị 6 activation kèm tên cơ, cập nhật theo khung, đúng giá trị ghi/mô phỏng | T509, T510, T512 | `tests/unit/test_playback.py::test_hud_shows_recorded_activation_each_frame`, `tests/unit/test_playback.py::test_hud_names_match_muscle_names` | unit | có |
| FR-006 | Tốc độ thời gian thực mặc định, chỉnh hệ số tốc độ và lặp, giữ khung cuối, gợi ý khi episode < 1 s, báo tỷ lệ khi trễ | T503, T508, T510, T516 | `tests/unit/test_pacing.py::test_loop_repeats_until_sink_closed`, `tests/integration/test_replay_headless.py::test_short_episode_hint_on_stderr` | entrypoint | có |
| FR-007 | Định dạng episode đầy đủ trường, có khuôn máy đọc được | T504, T520 | `tests/unit/test_episode.py::test_write_read_roundtrip_and_schema`, `tests/integration/test_contract_examples_replay.py::test_examples_match_schemas` | entrypoint | có |
| FR-008 | Lưu episode đúng đường dẫn chỉ định, ghi nguyên tử, không ghi đè, không ghi ngầm | T504, T514, T518 | `tests/unit/test_episode.py::test_refuse_overwrite`, `tests/integration/test_demo_cli.py::test_no_file_written_without_save_flag` | entrypoint | có |
| FR-009 | Đọc episode kiểm cấu trúc, nhất quán, hữu hạn, phiên bản; từ chối nêu trường và lý do | T504, T517 | `tests/unit/test_episode.py::test_n_actions_matches_frames`, `tests/integration/test_replay_bad_input.py::test_corrupt_json_exit5_names_field` | entrypoint | có |
| FR-010 | Chế độ `--headless` không mở viewer: tóm tắt máy đọc được; với `--checkpoint` chạy và lưu episode | T507, T514, T516 | `tests/integration/test_replay_headless.py::test_summary_has_all_fields`, `tests/unit/test_summary.py::test_activation_stats_match_hand_values` | entrypoint | có |
| FR-011 | Không màn hình và không `--headless`: lỗi tiếng Việt, gợi ý `--headless`, mã khác 0 trong ≤ 5 s; viewer không khởi tạo được xử lý như không màn hình | T511, T514, T516 | `tests/integration/test_replay_nodisplay.py::test_bogus_display_handled_like_no_display`, `tests/unit/test_display.py::test_unavailable_reports_reason_without_crash` | entrypoint | có |
| FR-012 | Hash XML lệch ⇒ cảnh báo nêu cả hai hash và dừng; chỉ cờ tường minh mới đi tiếp kèm "MÔ HÌNH LỆCH"; cấu trúc không tương thích luôn từ chối | T506, T514, T517 | `tests/unit/test_model_check.py::test_hash_and_structure_cases`, `tests/integration/test_replay_model_mismatch.py::test_mismatch_stops_names_both_hashes` | entrypoint | có |
| FR-013 | Episode/checkpoint không tồn tại, hỏng, thiếu thành phần: lỗi nêu nguyên nhân, mã khác 0, không viewer, không kết quả giả; checkpoint kiểm hash XML | T502, T514, T517 | `tests/integration/test_replay_bad_input.py::test_missing_checkpoint_exit4_no_viewer_no_file`, `tests/integration/test_replay_bad_input.py::test_checkpoint_xml_hash_mismatch_exit4` | entrypoint | có |
| FR-014 | Mã thoát phản ánh kết quả phát lại, không phản ánh lỗi dọn dẹp đồ hoạ; viewer đóng bình thường ⇒ mã 0 | T515, T519 | `tests/unit/test_script_exit.py::test_exit_code_is_result_not_teardown`, `tests/unit/test_script_exit.py::test_os_exit_only_when_viewer_opened`, `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` | entrypoint | có |
| FR-015 | Replay chạy tiến trình riêng, chỉ đọc, không nhập `learning.trainer`/`learning.ppo`; `--episode` không cần thư viện học máy | T502, T520 | `tests/integration/test_visualization_imports.py::test_visualization_has_no_training_imports`, `tests/integration/test_visualization_imports.py::test_episode_path_does_not_import_torch` | entrypoint | có |
| FR-016 | Chọn mục tiêu theo chỉ số trong một tập và seed; giá trị ngoài phạm vi bị từ chối trước khi mở viewer | T513, T514, T517, T518 | `tests/integration/test_demo_cli.py::test_demo_selects_requested_target`, `tests/integration/test_replay_bad_input.py::test_target_index_out_of_range_exit2` | entrypoint | có |
| FR-017 | Cấu hình replay ở một tệp duy nhất; giá trị sai bị từ chối trước khi mở viewer | T503 | `tests/unit/test_replay_config.py::test_defaults_load`, `tests/unit/test_replay_config.py::test_invalid_values_raise` | unit | có |
| FR-018 | Lỗi và thông báo bằng tiếng Việt nêu giá trị và ngữ cảnh; đường dẫn trong tóm tắt và episode là tương đối | T507, T514, T517 | `tests/integration/test_replay_bad_input.py::test_errors_are_vietnamese_with_context`, `tests/unit/test_summary.py::test_paths_relative` | entrypoint | có |
| FR-019 | Bộ test tự động phủ định dạng episode, phát lại, bộ lập nhịp, demo, không màn hình, lệch mô hình, đường dẫn không tồn tại | T504, T508, T510, T513, T516, T517, T518, T521 | `uv run python -m pytest -q` (toàn bộ), `tests/e2e/test_replay_acceptance.py` | entrypoint | có |
| SC-001 | `--episode` hợp lệ ở máy có màn hình mở viewer, phát đủ 100% khung theo thứ tự, thoát mã 0 khi đóng | T519, T521 | `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` | entrypoint | có |
| SC-002 | Demo từ checkpoint hợp lệ: 100% hành động là kích thích cơ trong `[0,1]^6`, hiển thị mục tiêu và 6 activation có tên cơ ở mọi khung | T513, T518, T521 | `tests/integration/test_demo_cli.py::test_demo_only_muscle_excitation_in_unit_interval` | entrypoint | có |
| SC-003 | Không màn hình: 100% lần chạy hoặc mã 0 với tóm tắt (`--headless`) hoặc mã khác 0 trong ≤ 5 s với thông báo rõ; 0 lần treo | T516, T521 | `tests/integration/test_replay_nodisplay.py::test_no_display_exits_7_fast_with_hint` | entrypoint | có |
| SC-004 | 100% episode lệch hash XML bị dừng với cảnh báo nêu cả hai hash khi không có cờ chấp nhận | T517, T521 | `tests/integration/test_replay_model_mismatch.py::test_mismatch_stops_names_both_hashes` | entrypoint | có |
| SC-005 | Đường dẫn episode/checkpoint không tồn tại: mã khác 0, thông báo nêu đường dẫn, 0 viewer, 0 tệp episode | T517, T521 | `tests/integration/test_replay_bad_input.py::test_missing_episode_exit5` | entrypoint | có |
| SC-006 | Mỗi episode do hệ thống ghi hợp khuôn, có seed, hash XML, 6 tên cơ, activation 6 cơ mọi khung, 0 NaN/Inf | T504, T520 | `tests/integration/test_contract_examples_replay.py::test_no_nonfinite_values`, `tests/unit/test_episode.py::test_write_read_roundtrip_and_schema` | entrypoint | có |

<a id="truy-vet-nguoc-task-ma"></a>
## Truy vết ngược: task → mã

| Task | Vai | Mã hiện thực (FR · INV · NFR · AC · API · CMD) | Tệp test dự kiến |
|---|---|---|---|
| T501 | builder | FR-015, FR-019 | `tests/unit/test_smoke_mma_ai.py` |
| T502 | builder | FR-013, FR-018, INV-004 | — |
| T503 | builder | API-VIS-0001, FR-006, FR-017 | `tests/unit/test_replay_config.py` |
| T504 | builder | API-VIS-0002, API-VIS-0003, FR-007, FR-008, FR-009, INV-003, INV-005, NFR-REL-001 | `tests/unit/test_episode.py` |
| T505 | builder | FR-002, FR-003, INV-002 | `tests/unit/test_env_read_state.py` |
| T506 | builder | API-VIS-0005, FR-012, INV-001 | `tests/unit/test_model_check.py` |
| T507 | builder | API-VIS-0006, FR-010, FR-018, INV-006, NFR-REL-001 | `tests/unit/test_summary.py` |
| T508 | builder | API-VIS-0007, FR-006, NFR-PERF-001 | `tests/unit/test_pacing.py` |
| T509 | builder | API-VIS-0012, FR-005, INV-006 | `tests/unit/test_hud.py` |
| T510 | builder | API-VIS-0009, FR-001, FR-004, FR-005, FR-006, INV-001, INV-006 | `tests/unit/test_playback.py` |
| T511 | builder | API-VIS-0008, FR-011, NFR-HEADLESS-001 | `tests/unit/test_display.py` |
| T512 | builder | API-VIS-0010, FR-001, FR-004, FR-005, INV-002 | `tests/unit/test_viewer.py` |
| T513 | builder | API-VIS-0004, FR-002, FR-003, FR-016, INV-002, NFR-REPRO-001 | `tests/unit/test_recorder.py` |
| T514 | builder | API-VIS-0011, CMD-VIS-0001, FR-001, FR-002, FR-008, FR-010, FR-011, FR-012, FR-013, FR-016, FR-018, INV-001, INV-004, INV-005 | `tests/unit/test_run_replay.py` |
| T515 | builder | CMD-VIS-0001, FR-014 | `tests/unit/test_script_exit.py` |
| T516 | builder | AC-3, FR-006, FR-010, FR-011, NFR-HEADLESS-001 | `tests/integration/test_replay_headless.py`, `tests/integration/test_replay_nodisplay.py` |
| T517 | builder | AC-4, AC-5, FR-009, FR-012, FR-013, FR-016, FR-018, INV-001, INV-004, NFR-REL-001 | `tests/integration/test_replay_model_mismatch.py`, `tests/integration/test_replay_bad_input.py` |
| T518 | builder | AC-2, FR-002, FR-003, FR-008, FR-016, INV-002, INV-005, NFR-REPRO-001 | `tests/integration/test_demo_cli.py`, `tests/integration/test_replay_readonly.py` |
| T519 | builder | AC-1, AC-2, FR-001, FR-004, FR-005, FR-014 | `tests/integration/test_replay_viewer_real.py` |
| T520 | builder | AC-1, AC-4, FR-007, FR-015, INV-003, NFR-REL-001 | `tests/integration/test_visualization_imports.py`, `tests/integration/test_contract_examples_replay.py` |
| T521 | qa | AC-1, AC-2, AC-3, AC-4, AC-5, FR-001, FR-010, FR-011, FR-012, FR-013, SC-001, SC-006 | `tests/e2e/test_replay_acceptance.py` |
| T522 | challenger | INV-001, INV-002, INV-003, INV-004, INV-005 | `tests/challenge/test_replay_invariants.py` |
| T523 | reviewer | AC-1, AC-5, INV-001, INV-006 | — |

<a id="chua-truy-vet-duoc"></a>
## Chưa truy vết được

- Không mã nào ở trạng thái `THIẾU`: mọi `AC-*`, `INV-*`, `NFR-*`, `FR-*`, `SC-*` của `spec.md` đều có task và test dự kiến.
- Giới hạn của bằng chứng (không phải mã thiếu): nhánh "viewer thật phát khung" của AC-1/AC-2/FR-001/FR-004/FR-005/SC-001 chỉ chứng minh được ở máy có `DISPLAY` (đã đo ở máy phát triển Linux gốc); trong CI không màn hình test `test_real_viewer_plays_or_reports_no_display` chỉ chạy nhánh mã 7. WSL2/WSLg CHƯA KIỂM. Người xử: người vận hành chạy lần kiểm trên máy có màn hình sau khi M0 đạt nghiệm thu.
- `NFR-PERF-001` và `FR-005` được đo ở mức `unit` (đồng hồ giả, `RecordingSink`) vì tỷ lệ thời gian của viewer thật phụ thuộc phần cứng đích RTX 5060 (chưa đo; master plan XI.10); tỷ lệ thực của phiên viewer thật được ghi trong dòng tóm tắt cuối phiên, không là điều kiện nghiệm thu.
- Khoảng trống năng lực: vỏ `scripts/replay.py` (chuỗi lệnh nguyên văn của AC-1…AC-5) và `configs/replay.yaml` không nằm trong vùng ghi của vai nào (`ai-sdlc check tasks` từ chối); logic chạy ở `src/mma_ai/visualization/cli.py`, mọi test dùng `python -m mma_ai.visualization.cli`. Tới khi vỏ script có chủ, AC-1…AC-5 chưa được chứng minh qua đúng chuỗi `python scripts/replay.py`. Người xử: `ai-sdlc capability propose <dự-án> "vùng ghi cho scripts/** và configs/**"`, sau đó converge thêm task vỏ script + cập nhật `test_unimplemented_cli.py` (xem `plan.md`, mục "Quyết định ở bước tasks").
- Phụ thuộc chéo feature chưa khai được ở cột `depends_on` vì `tasks.md` của 001–004 chưa tồn tại (xem `tasks.md`, mục "Phụ thuộc chéo feature"): `T501`, `T505`, `T513`, `T515`. Người xử: bước converge/`plan_fix` khi các `tasks.md` đó được sinh.
