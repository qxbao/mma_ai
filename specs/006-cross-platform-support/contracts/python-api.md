---
id: "API-006"
title: "Hỗ trợ đa nền tảng — Hợp đồng API Python của lớp tương thích"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-11"
feature: "006-cross-platform-support"
version: "1.1.0"
---

# Hợp đồng — API Python của `mma_ai.compat`

Gói `mma_ai.compat` là lá của đồ thị phụ thuộc (không nhập `learning`, `evaluation`, `visualization`, `monitoring`, `environment`, `physics`). Mọi hàm có tham số **tiêm** (hồ sơ nền tảng, `environ`, đồng hồ, hàm hệ thống) để test chạy nhánh của mọi OS trên bất kỳ OS nào (FR-023). Không có điểm mạng. Mọi thông điệp người dùng bằng tiếng Việt (FR-024). Dấu `→` là kiểu trả về; chữ ký là hợp đồng, không phải mã.

- [Bảng API](#bang-api)
- [Điểm tích hợp vào mã đã có (mỗi dòng một chủ, chỉ đổi điểm gắn nền tảng)](#diem-tich-hop-vao-ma-da-co-moi-dong-mot-chu-chi-doi-diem-gan-nen-tang)

<a id="bang-api"></a>
## Bảng API

| Mã | Mô-đun · chữ ký | Hành vi hợp đồng | FR / INV / AC |
|---|---|---|---|
| `API-PLT-0001` | `platform_info.detect_platform(*, sys_platform=None, release=None, machine=None, environ=None) → PlatformProfile` | Trả hồ sơ bất biến `{kind ∈ windows\|linux\|wsl2\|macos, release, machine, python_version, is_wsl, tested}`; `tested=false` cho Windows ARM64 và macOS Intel; không ném ngoại lệ | FR-002; AC-1, AC-5 |
| `API-PLT-0002` | `memory.ram_mib_from_raw(raw, kind) → float` · `memory.peak_ram_mb(profile=None) → float \| None` | `ram_mib_from_raw`: linux/wsl2 KiB ÷ 1024; macos byte ÷ 1 048 576; windows byte ÷ 1 048 576; `raw` âm/không hữu hạn ⇒ `ValueError`. `peak_ram_mb`: gọi nguồn của OS (Linux/macOS `getrusage`; Windows `GetProcessMemoryInfo`), nhập `resource`/`ctypes` lười trong nhánh; thất bại ⇒ `None` | FR-004, INV-002, INV-007; AC-2 |
| `API-PLT-0003` | `display.probe_display(profile=None, *, environ=None, glfw_init=None) → DisplayProbe{available: bool, reason: str}` | Linux/WSL2: cả `DISPLAY` và `WAYLAND_DISPLAY` trống ⇒ không khả dụng (giữ nguyên chữ của `005`), ngược lại thử GLFW. Windows/macOS: bỏ qua hai biến, thử GLFW + màn hình chính. Mọi ngoại lệ ⇒ không khả dụng kèm chi tiết; ≤ 5 s; `reason` luôn là chuỗi không rỗng; khả dụng ⇒ `reason` = "Màn hình hiển thị khả dụng (display available)." (không đổi chữ) | FR-005, FR-006, INV-004; AC-3 |
| `API-PLT-0004` | `capabilities.symlink_supported(probe_dir=None) → Capability` · `capabilities.long_paths_enabled(profile=None) → Capability` · `capabilities.ram_probe(profile=None) → Capability` · `capabilities.utf8_stdio_ok() → Capability` | `Capability{available: bool, reason: str \| None}` (`reason` là `None` ⇔ khả dụng). `symlink_supported` tạo thật một symlink trong thư mục tạm rồi dọn; lỗi quyền ⇒ không khả dụng. `long_paths_enabled`: chỉ Windows đọc `LongPathsEnabled` (`winreg` nhập lười); OS khác ⇒ khả dụng | FR-014, INV-004; AC-4, AC-6 |
| `API-PLT-0005` | `fsio.replace_atomic(src, dst, *, attempts=5, waits=(0.05, 0.10, 0.20, 0.20), sleep=time.sleep, replace=os.replace, profile=None) → None` · `fsio.write_text_atomic(dst, text, *, profile=None) → None` · `fsio.write_bytes_atomic(dst, data, *, profile=None) → None` · lỗi `AtomicWriteError(OSError)` | Tệp tạm cùng thư mục với `dst`; `write_text_atomic` mã hoá UTF-8 không BOM, xuống dòng LF, `fsync` tệp; `replace_atomic` trên Windows thử lại `PermissionError` theo `waits` (tổng ≤ 1,0 s), trên OS khác một lần; thất bại ⇒ xoá tệp tạm, `dst` giữ nguyên byte, ném `AtomicWriteError` nêu `dst` và nguyên nhân gốc | FR-009, INV-003, INV-005; AC-4 |
| `API-PLT-0006` | `pathrules.is_absolute_any_os(value) → bool` · `pathrules.to_record_path(path, base=None) → str` · `pathrules.venv_python(venv_dir, profile=None) → Path` | `is_absolute_any_os`: đúng nếu POSIX tuyệt đối, hoặc có `drive`, hoặc có `root` (Windows) — kết quả không phụ thuộc OS đang chạy; `to_record_path`: tương đối theo `base`, dùng `/`, không ổ đĩa; `venv_python`: Windows ⇒ thư mục `Scripts` + `python.exe`, còn lại ⇒ thư mục `bin` + `python` | FR-010, FR-011, FR-016; AC-4, AC-5 |
| `API-PLT-0007` | `stdio.ensure_utf8_stdio(streams=None) → None` | Với `stdout`/`stderr` có `reconfigure`: đặt `encoding="utf-8"`, `errors="replace"`; luồng không hỗ trợ thì bỏ qua; gọi lặp lại vô hại; không ném ngoại lệ | FR-013; AC-4 |
| `API-PLT-0008` | `env_report.build_environment_report(profile=None, *, probes=None) → dict` · `env_report.render_text(report) → str` · `env_report.main(argv=None) → int` | `build_…` trả dict hợp [check-env-report.schema.json](check-env-report.schema.json); không ném ngoại lệ khi gói thiếu (ghi `null` + phép kiểm `fail`/`warn`); `main` = `CMD-PLT-0001` | FR-017; AC-5 |
| `API-PLT-0009` | Plugin test `tests/capability_gate.py` (không thuộc gói phân phối) | Đăng ký dấu, loại khi thu thập, báo cáo, ngưỡng tỷ lệ — xem `cli.md` mục "Hợp đồng thu thập test" | FR-021, INV-006; AC-6 |

<a id="diem-tich-hop-vao-ma-da-co-moi-dong-mot-chu-chi-doi-diem-gan-nen-tang"></a>
## Điểm tích hợp vào mã đã có (mỗi dòng một chủ, chỉ đổi điểm gắn nền tảng)

| Nơi gọi hiện có | Gọi | Ghi chú |
|---|---|---|
| `learning/resources.py::_peak_ram_mb` | `API-PLT-0002` | Bỏ `import resource` mức mô-đun (F-001) |
| `visualization/display.py::display_available` | `API-PLT-0003` | Giữ `DisplayStatus` và chữ thông điệp Linux (F-003) |
| `monitoring/viewer3d.py::View3D.has_display` | `API-PLT-0003` | Giữ `staticmethod`; đường tắt Linux không nạp GLFW (F-004) |
| `learning/benchmark.py::evaluate_view3d_status` | `API-PLT-0003` | F-005 |
| `learning/checkpoint.py`, `learning/manifest.py`, `learning/progress.py`, `visualization/episode.py`, `learning/benchmark.py::_write…`, `monitoring/cli.py` (`ui.json`), `environment/verify_clean_install.py` | `API-PLT-0005` | F-007, F-018 |
| `evaluation/eval_config.py`, `learning/manifest.py`, `learning/trainer.py`, `visualization/recorder.py`, `visualization/summary.py` | `API-PLT-0006` | F-012 |
| `environment/verify_clean_install.py::py_bin` | `API-PLT-0006` (`venv_python`) | F-013 |
| `main()` của `learning/cli.py`, `learning/benchmark.py`, `learning/compare_cli.py`, `monitoring/cli.py`, CLI evaluate/replay (khi có mặt) | `API-PLT-0007` | F-019 |
