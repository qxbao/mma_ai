---
id: "QS-006"
title: "Hỗ trợ đa nền tảng — Quickstart kiểm chứng"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-11"
feature: "006-cross-platform-support"
version: "1.1.0"
---

# Quickstart — kiểm chứng hỗ trợ đa nền tảng

- [Điều kiện tiên quyết](#dieu-kien-tien-quyet)
- [Kịch bản 1 — Cài đặt tái lập và kiểm môi trường trên Windows gốc (AC-5, NFR-ENV-001)](#kich-ban-1-cai-dat-tai-lap-va-kiem-moi-truong-tren-windows-goc-ac-5-nfr-env-001)
- [Kịch bản 2 — WSL2 và máy không có màn hình (AC-5, AC-3, INV-004)](#kich-ban-2-wsl2-va-may-khong-co-man-hinh-ac-5-ac-3-inv-004)
- [Kịch bản 3 — macOS và `mjpython` (AC-3, AC-1)](#kich-ban-3-macos-va-mjpython-ac-3-ac-1)
- [Kịch bản 4 — RAM đỉnh đúng đơn vị trên ba OS (AC-2, INV-007, NFR-RAM-001)](#kich-ban-4-ram-dinh-dung-don-vi-tren-ba-os-ac-2-inv-007-nfr-ram-001)
- [Kịch bản 5 — Dò màn hình nhất quán ở ba nơi (AC-3, NFR-DISPLAY-001, INV-004)](#kich-ban-5-do-man-hinh-nhat-quan-o-ba-noi-ac-3-nfr-display-001-inv-004)
- [Kịch bản 6 — Ghi tệp nguyên tử, UTF-8 và xuống dòng LF (AC-4, INV-003, INV-005, NFR-IO-001, NFR-ENC-001)](#kich-ban-6-ghi-tep-nguyen-tu-utf-8-va-xuong-dong-lf-ac-4-inv-003-inv-005-nfr-io-001-nfr-enc-001)
- [Kịch bản 7 — Đường dẫn tuyệt đối năm dạng và đường dẫn trong bản ghi (AC-4)](#kich-ban-7-duong-dan-tuyet-doi-nam-dang-va-duong-dan-trong-ban-ghi-ac-4)
- [Kịch bản 8 — CI ma trận và test loại theo năng lực (AC-6, INV-006, NFR-CI-001)](#kich-ban-8-ci-ma-tran-va-test-loai-theo-nang-luc-ac-6-inv-006-nfr-ci-001)
- [Kịch bản 9 — Linux không đổi hành vi và dữ liệu cũ còn đọc được (AC-1, AC-2, AC-3, INV-001, INV-007, NFR-PARITY-001)](#kich-ban-9-linux-khong-doi-hanh-vi-va-du-lieu-cu-con-doc-duoc-ac-1-ac-2-ac-3-inv-001-inv-007-nfr-parity-001)
- [Kịch bản 10 — CLI chạy trọn trên ba OS (AC-1, INV-001, INV-002)](#kich-ban-10-cli-chay-tron-tren-ba-os-ac-1-inv-001-inv-002)

<a id="dieu-kien-tien-quyet"></a>
## Điều kiện tiên quyết

- Thứ tự kịch bản theo quyết định của người dùng (Q-0002): Windows gốc là môi trường chính nên kịch bản 1 là Windows; CUDA tuỳ chọn; macOS phải chạy tốt (kịch bản 3).
- Python 3.11 hoặc 3.12; công cụ uv (hoặc pip). Trên Windows: PowerShell; trên macOS: Apple Silicon; trên WSL2: bản Ubuntu.
- Lệnh dưới đây chạy từ gốc repo. Mọi đường dẫn trong tài liệu là tương đối. Bước nào test tự động làm được thì chỉ tên test; bước "kiểm tay" là bước người trên máy thật và **CHƯA KIỂM** cho tới khi có lần chạy thật (bằng chứng ghi vào `evidence/` do cổng sinh, không do tay viết).
- Test thật theo OS chạy ở ô CI tương ứng; test nhánh theo OS chạy ở mọi OS bằng hồ sơ nền tảng giả (tiêm).

<a id="kich-ban-1-cai-dat-tai-lap-va-kiem-moi-truong-tren-windows-goc-ac-5-nfr-env-001"></a>
## Kịch bản 1 — Cài đặt tái lập và kiểm môi trường trên Windows gốc (AC-5, NFR-ENV-001)

1. Cài uv và Python 3.12 (`uv python install 3.12`), lấy mã, rồi dựng môi trường từ khoá: `uv sync --locked --extra dev --extra rl --extra eval` (torch CPU từ khoá; không cần GPU). Phương án pip: `uv export --format requirements-txt` rồi `pip install -r` và `pip install -e . --no-deps` (tài liệu cài đặt nêu rõ pip tái lập yếu hơn).
2. Chạy `uv run python scripts/check_env.py`. Kỳ vọng: mã thoát 0, dòng `[ok]` cho Python và các gói, `os.kind` = Windows; nếu chưa bật quyền symlink hoặc đường dẫn dài thì có dòng `[CẢNH BÁO]` kèm cách xử lý — không phải lỗi.
3. Chạy `uv run python scripts/check_env.py --json`; kỳ vọng đúng một đối tượng JSON hợp khuôn.
4. Test tự động: `tests/unit/test_env_report.py::test_python_range_check`, `::test_torch_absent_is_warning`, `::test_untested_configuration_warns`, `::test_report_has_no_absolute_paths`, `tests/integration/test_check_env_cli.py::test_json_output_valid_and_exit_matches_overall`, `::test_report_os_kind_matches_detect_platform`, `::test_unknown_flag_exits_2`; ô CI Windows chạy `check_env` thật.
5. **Kiểm tay (CHƯA KIỂM)**: trên một máy Windows 11 mới, làm đúng từng lệnh trong `docs/04-implementation/install-cross-platform.md` rồi bước 2; ghi kết quả vào báo cáo của task qa.
6. CUDA (tuỳ chọn; máy của người dùng có CUDA nên đây là bước kiểm tay có giá trị nhất, CHƯA KIỂM — máy phát triển của agent không có NVIDIA): làm theo mục "torch CUDA" của tài liệu cài đặt rồi chạy lại bước 2; kỳ vọng `torch_device.kind` = `cuda` kèm tên GPU. Không có GPU thì `cpu` và vẫn mã 0.

<a id="kich-ban-2-wsl2-va-may-khong-co-man-hinh-ac-5-ac-3-inv-004"></a>
## Kịch bản 2 — WSL2 và máy không có màn hình (AC-5, AC-3, INV-004)

1. Trong WSL2 Ubuntu, dựng môi trường như trên rồi chạy `uv run python scripts/check_env.py`; kỳ vọng `os.kind` = WSL2.
2. Khi chưa có WSLg (`DISPLAY` và `WAYLAND_DISPLAY` đều chưa đặt), kỳ vọng dòng `[CẢNH BÁO]` về màn hình kèm gợi ý `--headless`, mã thoát vẫn 0.
3. Chạy `uv run python -m mma_ai.visualization.cli --episode <tệp> --headless` (khi CLI replay có mặt); kỳ vọng mã 0 và không nạp GLFW.
4. Test tự động: `tests/unit/test_compat_platform.py::test_wsl2_detected_by_release_or_distro_env`, `tests/unit/test_env_report.py::test_wsl_kind_and_flag_agree`, `tests/unit/test_compat_display.py::test_linux_unset_env_unavailable_exact_message`, `tests/challenge/test_platform_invariants.py::test_inv004_unknown_capability_is_unavailable`.
5. **Kiểm tay (CHƯA KIỂM)**: thư mục run trên ổ Windows gắn vào WSL2 phải sinh cảnh báo `wsl_windows_drive`, không phải lỗi.

<a id="kich-ban-3-macos-va-mjpython-ac-3-ac-1"></a>
## Kịch bản 3 — macOS và `mjpython` (AC-3, AC-1)

1. Trên macOS Apple Silicon, dựng môi trường và chạy `uv run python scripts/check_env.py`; kỳ vọng `os.kind` = macOS và mã 0.
2. Mở viewer bằng `mjpython -m mma_ai.visualization.cli --episode <tệp>` (khi CLI replay có mặt); kỳ vọng cửa sổ mở. Chạy cùng lệnh bằng `python` thường: kỳ vọng lỗi tiếng Việt nêu cách chạy bằng `mjpython`, mã khác 0, không treo.
3. Test tự động: `tests/unit/test_viewer.py::test_macos_without_mjpython_reports_vietnamese_hint`, `tests/unit/test_compat_display.py::test_macos_ignores_display_env_vars`; ô CI macOS chạy `check_env` và bộ test.
4. **Kiểm tay (CHƯA KIỂM)**: bước 2 trên máy có màn hình thật; ghi chuỗi lỗi MuJoCo thật khi thiếu `mjpython` để hiệu chỉnh nhận diện (research Q4).

<a id="kich-ban-4-ram-dinh-dung-don-vi-tren-ba-os-ac-2-inv-007-nfr-ram-001"></a>
## Kịch bản 4 — RAM đỉnh đúng đơn vị trên ba OS (AC-2, INV-007, NFR-RAM-001)

1. Quy đổi: `tests/unit/test_compat_memory.py::test_linux_kib_to_mib` (262 144 → 256,0), `::test_macos_bytes_to_mib` (268 435 456 → 256,0), `::test_windows_bytes_to_mib` (268 435 456 → 256,0), `::test_invalid_raw_raises`, `::test_failure_returns_none_not_zero`.
2. Nhập mô-đun trên Windows: `tests/unit/test_compat_memory.py::test_peak_does_not_import_resource_on_windows_profile` và `tests/integration/test_cross_platform_imports.py::test_no_module_level_os_specific_imports`.
3. Đo thật: `tests/integration/test_ram_real_measure.py::test_real_peak_grows_by_allocation_within_band` (cấp phát và chạm 256 MiB; mức tăng ∈ [230,4 ; 332,8] MB) — chạy ở ô CI của cả ba OS.
4. Hồ sơ run: `tests/unit/test_manifest.py` (hiện có, phải xanh) và `tests/e2e/test_platform_acceptance.py::test_check_env_then_train_smoke_then_manifest_ram_plausible` (`ram_peak_mb` là số dương hợp lý, không lệch 1024 lần).

<a id="kich-ban-5-do-man-hinh-nhat-quan-o-ba-noi-ac-3-nfr-display-001-inv-004"></a>
## Kịch bản 5 — Dò màn hình nhất quán ở ba nơi (AC-3, NFR-DISPLAY-001, INV-004)

1. Linux không đổi: `tests/unit/test_platform_characterization.py::test_display_unset_message_matches_legacy`, `tests/unit/test_compat_display.py::test_linux_unset_env_unavailable_exact_message`, `::test_linux_bogus_display_unavailable`.
2. Windows/macOS không đọc `DISPLAY`/`WAYLAND_DISPLAY`: `::test_windows_ignores_display_env_vars`, `::test_macos_ignores_display_env_vars`, `::test_windows_no_primary_monitor_unavailable`.
3. Ngoại lệ GLFW: `::test_glfw_exception_is_unavailable_with_detail`; thời gian: `::test_probe_returns_within_5s_real` (đồng hồ thật, mọi ô CI).
4. Ba nơi cùng kết luận: `tests/integration/test_display_consumers_agree.py::test_three_consumers_agree_for_each_profile` (bốn hồ sơ giả) và `::test_view3d_linux_shortcut_does_not_import_glfw`.
5. Viewer thật: test mang dấu `requires_display` (ví dụ `tests/integration/test_viewer3d.py::test_real_window_requires_display`) chạy khi máy có màn hình, bị loại có báo cáo khi không có. **Kiểm tay (CHƯA KIỂM)**: mở viewer 3D trên Windows 11 thật.

<a id="kich-ban-6-ghi-tep-nguyen-tu-utf-8-va-xuong-dong-lf-ac-4-inv-003-inv-005-nfr-io-001-nfr-enc-001"></a>
## Kịch bản 6 — Ghi tệp nguyên tử, UTF-8 và xuống dòng LF (AC-4, INV-003, INV-005, NFR-IO-001, NFR-ENC-001)

1. Nguyên tử: `tests/unit/test_compat_fsio.py::test_failure_cases_keep_old_bytes_and_clean_tmp` (4 ca tiêm lỗi), `::test_windows_retries_permission_error_then_succeeds`, `::test_windows_gives_up_within_one_second_keeps_old_bytes`, `::test_posix_does_not_retry`, `::test_temp_file_in_same_directory`; thật trên Windows: `tests/integration/test_atomic_replace_locked_windows.py::test_replace_over_open_destination_keeps_old_bytes`.
2. Byte: `tests/unit/test_compat_fsio.py::test_text_is_utf8_lf_no_bom`, `::test_linux_bytes_identical_to_legacy_pattern`, `tests/unit/test_platform_characterization.py::test_atomic_write_bytes_match_legacy`.
3. Đầu ra chuẩn: `tests/unit/test_compat_stdio.py::test_reconfigure_sets_utf8_replace` và `tests/integration/test_cross_platform_cli_utf8.py::test_clis_survive_legacy_stdio_encoding` (đặt `PYTHONIOENCODING=cp1252` rồi chạy từng CLI; 0 `UnicodeEncodeError`), `::test_written_text_files_have_no_cr_or_bom` (0 byte `\r`, 0 BOM trong tệp do hệ thống ghi).
4. Thử thách: `tests/challenge/test_platform_invariants.py::test_inv003_fault_injection_never_leaves_partial_file`.

<a id="kich-ban-7-duong-dan-tuyet-doi-nam-dang-va-duong-dan-trong-ban-ghi-ac-4"></a>
## Kịch bản 7 — Đường dẫn tuyệt đối năm dạng và đường dẫn trong bản ghi (AC-4)

1. `tests/unit/test_compat_pathrules.py::test_five_absolute_forms_rejected_on_every_os` (bắt đầu `/`, bắt đầu `\`, UNC, ổ đĩa kèm `\`, ổ đĩa không dấu phân cách — 5/5), `::test_relative_forms_accepted`, `::test_to_record_path_uses_slash_and_is_relative`, `::test_venv_python_by_os`.
2. Cấu hình: `tests/unit/test_eval_config.py` (hiện có, phải xanh) cộng ca mới cho từng dạng ở `runs_dir`.
3. Thử thách: `tests/challenge/test_platform_invariants.py::test_path_rules_fuzz_never_raises_and_never_leaks_backslash`.
4. Symlink/đường dẫn dài: `tests/unit/test_compat_capabilities.py::test_symlink_probe_unavailable_with_reason_on_oserror`, `::test_long_paths_reads_registry_value_on_windows_profile`.

<a id="kich-ban-8-ci-ma-tran-va-test-loai-theo-nang-luc-ac-6-inv-006-nfr-ci-001"></a>
## Kịch bản 8 — CI ma trận và test loại theo năng lực (AC-6, INV-006, NFR-CI-001)

1. Cơ chế loại: `tests/unit/test_capability_gate.py::test_unsatisfied_marker_is_deselected_not_skipped`, `::test_missing_reason_is_collection_error`, `::test_ratio_over_limit_fails_session`, `::test_report_lists_each_deselected_with_reason`.
2. Không che lỗi: `tests/unit/test_no_new_skip_xfail.py::test_feature_tests_have_no_skip_or_xfail`; `tests/challenge/test_platform_invariants.py::test_inv006_deselect_always_reported`; cổng máy quét diff tìm `skip`/`xfail` mới.
3. Tệp CI (kiểm tĩnh): `tests/integration/test_ci_workflow.py::test_matrix_has_six_cells`, `::test_each_cell_runs_check_env_then_tests`, `::test_lockfile_is_checked_and_locked_sync`, `::test_no_failure_masking_in_workflow`.
4. **Kiểm tay (CHƯA KIỂM)**: đẩy nhánh lên remote có dịch vụ CI (repo hiện chưa có remote) và đọc 6 ô; ghi kết quả 6/6 ô xanh.

<a id="kich-ban-9-linux-khong-doi-hanh-vi-va-du-lieu-cu-con-doc-duoc-ac-1-ac-2-ac-3-inv-001-inv-007-nfr-parity-001"></a>
## Kịch bản 9 — Linux không đổi hành vi và dữ liệu cũ còn đọc được (AC-1, AC-2, AC-3, INV-001, INV-007, NFR-PARITY-001)

1. Trước khi đổi mã: chạy `tests/unit/test_platform_characterization.py` (xanh trên mã cũ): `::test_linux_kib_formula_matches_legacy`, `::test_display_unset_message_matches_legacy`, `::test_view3d_has_display_matches_env`, `::test_atomic_write_bytes_match_legacy`.
2. Sau khi đổi: chạy `uv run --isolated --with pytest pytest -q -p no:cacheprovider --ignore=tests/e2e`; kỳ vọng mọi test M0–M1 xanh trước vẫn xanh; so số test thu thập bằng `test_count_command` của `.ai/profile.yml` không nhỏ hơn mốc.
3. Hợp đồng dữ liệu cũ: `tests/integration/test_manifest_contract.py`, `tests/integration/test_contract_examples_train.py` (hiện có, phải xanh).

<a id="kich-ban-10-cli-chay-tron-tren-ba-os-ac-1-inv-001-inv-002"></a>
## Kịch bản 10 — CLI chạy trọn trên ba OS (AC-1, INV-001, INV-002)

1. Nhập mọi mô-đun: `tests/integration/test_cross_platform_imports.py::test_every_mma_ai_module_imports`.
2. Tiến trình con dưới `spawn`: `tests/integration/test_spawn_context.py::test_viewer3d_process_target_runs_under_spawn`.
3. Train, benchmark, evaluate, replay `--headless` với cấu hình smoke: `tests/e2e/test_platform_acceptance.py::test_headless_replay_and_benchmark_exit_codes_match_baseline`, `::test_cli_outputs_same_keys_as_linux_baseline` — chạy ở ô CI của từng OS (evaluate/replay khi có mặt ở nhánh tích hợp).
4. **Kiểm tay (CHƯA KIỂM)**: chạy train smoke trên Windows 11 gốc bằng PowerShell và so mã thoát với Linux.
