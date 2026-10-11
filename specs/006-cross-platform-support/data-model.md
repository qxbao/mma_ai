---
id: "DM-006"
title: "Hỗ trợ đa nền tảng — Mô hình dữ liệu (Data model)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-11"
feature: "006-cross-platform-support"
version: "1.1.0"
---

# Mô hình dữ liệu — Hỗ trợ đa nền tảng

- [Thực thể → đối tượng / tệp](#thuc-the-doi-tuong-tep)
- [Luật nhất quán mà JSON Schema không diễn đạt được (kiểm trong `build_environment_report` và test)](#luat-nhat-quan-ma-json-schema-khong-dien-dat-duoc-kiem-trong-build-environment-report-va-test)
- [Ánh xạ nhãn ↔ khoá](#anh-xa-nhan-khoa)
- [Trạng thái của một phiên `check_env`](#trang-thai-cua-mot-phien-check-env)
- [Tệp cấu hình và nơi dùng](#tep-cau-hinh-va-noi-dung)
- [Bất biến liên quan dữ liệu](#bat-bien-lien-quan-du-lieu)

Feature không có cơ sở dữ liệu (không `TBL-*`, không chỉ mục) và không đổi khuôn tệp của `001`…`005`: mọi thực thể dưới đây là đối tượng trong bộ nhớ, trừ **Báo cáo môi trường** (JSON do `check_env --json` in ra, khuôn ở [contracts/check-env-report.schema.json](contracts/check-env-report.schema.json)). Không có sự kiện miền (`EVT-*`) vì không có dịch vụ. Bất biến `INV-*` và ngưỡng `NFR-*` khai ở `spec.md` (bản 1.0.1); tệp này chỉ tham chiếu mã.

<a id="thuc-the-doi-tuong-tep"></a>
## Thực thể → đối tượng / tệp

| Thực thể (spec) | Đối tượng / tệp | Trường (kiểu) | Khoá / ràng buộc | Mã |
|---|---|---|---|---|
| Hồ sơ nền tảng | `PlatformProfile` (dataclass đóng băng, `compat/platform_info.py`) | `kind` (`windows`\|`linux`\|`wsl2`\|`macos`), `release` (str), `machine` (str), `python_version` (tuple 3 số nguyên), `is_wsl` (bool), `tested` (bool) | `kind` quyết định mọi nhánh; `tested=false` khi (`windows`, `ARM64`) hoặc (`macos`, `x86_64`); `is_wsl` ⇔ `kind == "wsl2"` | `API-PLT-0001`; FR-002 |
| Năng lực | `Capability` (dataclass đóng băng, `compat/capabilities.py`) | `available` (bool), `reason` (str \| None) | `reason is None` ⇔ `available`; không khả dụng thì `reason` tiếng Việt, không rỗng | `API-PLT-0004`; INV-004 |
| Kết quả dò màn hình | `DisplayProbe` (`compat/display.py`) → ánh xạ sang `DisplayStatus` có sẵn của `visualization/display.py` | `available` (bool), `reason` (str, không rỗng) | Khác `Capability` ở chỗ `reason` luôn là chuỗi (giữ chữ hiện có của `005`) | `API-PLT-0003`; FR-005 |
| Báo cáo môi trường | JSON in ra bởi `check_env --json`; dict từ `build_environment_report` | `schema_version`, `os{kind,release,machine,is_wsl,tested}`, `python{version,supported,required_range}`, `packages{mujoco,myo_sim,gymnasium,numpy,torch}`, `torch_device{kind,name}\|null`, `capabilities{display,symlink,long_paths,ram_peak,utf8_stdio}`, `checks[{id,status,message}]`, `overall` | Khuôn đóng (`additionalProperties: false`); `packages.*` nullable; `torch_device` nullable (null ⇔ `packages.torch` null); `overall = "fail"` ⇔ có `checks[].status = "fail"` ⇔ mã thoát 1 | `API-PLT-0008`, `CMD-PLT-0001`; FR-017 |
| Dấu năng lực | Dấu pytest (`pytest.mark.<tên>`) + bản ghi loại trong plugin `tests/unit/capability_gate.py` | `tên` ∈ {`requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `posix_only`, `linux_only`, `macos_only`}, `lý do` (str, bắt buộc) | Thiếu lý do ⇒ lỗi thu thập; bản ghi báo cáo: `nodeid`, `marker`, `reason` | `API-PLT-0009`; FR-021, INV-006 |
| Ô ma trận CI | Một phần tử của `strategy.matrix` trong workflow | `os` ∈ {`ubuntu-latest`, `macos-latest`, `windows-latest`}, `python` ∈ {`"3.11"`, `"3.12"`} | Đúng 6 tổ hợp; mỗi ô chạy `check_env` rồi test; `fail-fast: false` | FR-020, NFR-CI-001 |
| Báo cáo test bị loại | Tệp JSON tuỳ chọn (`--capability-report`) và phần tổng kết cuối của pytest | `collected` (int), `deselected` (int), `ratio` (float), `items[{nodeid, marker, reason}]` | `ratio = deselected / collected`; phiên thất bại nếu `ratio > 0,05` | FR-021, NFR-CI-001 |

<a id="luat-nhat-quan-ma-json-schema-khong-dien-dat-duoc-kiem-trong-build-environment-report-va-test"></a>
## Luật nhất quán mà JSON Schema không diễn đạt được (kiểm trong `build_environment_report` và test)

| Luật | Nơi kiểm | Mã |
|---|---|---|
| `os.kind == "wsl2"` ⇔ `os.is_wsl` | `test_env_report::test_wsl_kind_and_flag_agree` | FR-017 |
| `python.supported` ⇔ `3.11 ≤ phiên bản < 3.13`; `supported=false` ⇒ có phép kiểm `python_version` = `fail` | `test_env_report::test_python_range_check` | FR-017, AC-5 |
| `packages.torch` null ⇒ `torch_device` null và phép kiểm `package_torch` = `warn` (không phải `fail`) | `test_env_report::test_torch_absent_is_warning` | FR-017 |
| `capabilities.<x>.available=false` ⇒ `reason` không rỗng; ngược lại `null` | `test_env_report::test_capability_reason_contract` | INV-004 |
| `overall = "fail"` ⇔ ∃ `checks[].status = "fail"` ⇔ mã thoát 1 | `test_check_env_cli::test_exit_code_matches_overall` | FR-017 |
| `os.tested = false` ⇒ có phép kiểm `tested_configuration` = `warn` | `test_env_report::test_untested_configuration_warns` | FR-017, AC-5 |
| `check_env` không chứa đường dẫn tuyệt đối riêng của máy trong bất kỳ trường nào | `test_env_report::test_report_has_no_absolute_paths` | FR-024 |

<a id="anh-xa-nhan-khoa"></a>
## Ánh xạ nhãn ↔ khoá

Dây chỉ mang **khoá**; nhãn (thông điệp tiếng Việt) chỉ sinh ở bước hiển thị từ khoá.

| Khoá trên dây (`checks[].id`) | Nhãn hiển thị (tiếng Việt, bản văn bản) |
|---|---|
| `python_version` | Phiên bản Python |
| `package_mujoco` · `package_myo_sim` · `package_gymnasium` · `package_numpy` · `package_torch` | Gói `mujoco` · `myo-sim` · `gymnasium` · `numpy` · `torch` |
| `tested_configuration` | Cấu hình đã kiểm (OS/kiến trúc) |
| `display` | Màn hình hiển thị |
| `symlink` | Tạo symlink |
| `long_paths` | Đường dẫn dài (Windows) |
| `ram_peak` | Đo RAM đỉnh |
| `utf8_stdio` | Đầu ra UTF-8 |
| `wsl_windows_drive` | Thư mục run trên ổ Windows gắn vào WSL2 |

| Khoá trên dây (`os.kind`) | Nhãn hiển thị | Nguồn nhận diện |
|---|---|---|
| `windows` | Windows | `sys.platform == "win32"` |
| `linux` | Linux | `sys.platform == "linux"`, không phải WSL2 |
| `wsl2` | WSL2 (Linux trên Windows) | Linux và `platform.release()` chứa `wsl2` (hoặc `microsoft` kèm `WSL_DISTRO_NAME`) |
| `macos` | macOS | `sys.platform == "darwin"` |

**Ánh xạ nguồn đo RAM theo OS** (nguồn duy nhất của quy đổi; xem research Q3):

| `os.kind` | Nguồn đo | Đơn vị gốc | Công thức → `ram_peak_mb` (MiB) | Giá trị mẫu → kết quả |
|---|---|---|---|---|
| `linux`, `wsl2` | `getrusage(...).ru_maxrss` | KiB | gốc ÷ 1024 | 262 144 → 256,0 |
| `macos` | `getrusage(...).ru_maxrss` | byte | gốc ÷ 1 048 576 | 268 435 456 → 256,0 |
| `windows` | `GetProcessMemoryInfo(...).PeakWorkingSetSize` | byte | gốc ÷ 1 048 576 | 268 435 456 → 256,0 |

Luật chốt: một nơi duy nhất (`memory.ram_mib_from_raw`) làm phép quy đổi; mọi nơi khác chỉ nhận MiB.

<a id="trang-thai-cua-mot-phien-check-env"></a>
## Trạng thái của một phiên `check_env`

```text
bắt đầu → detect_platform → thu phiên bản gói (siêu dữ liệu gói, không nhập mujoco/torch nếu chưa cần)
        → nhập lười torch (nếu cài) → thu thiết bị torch
        → dò năng lực: display · symlink · long_paths · ram_peak · utf8_stdio
        → tổng hợp checks[] → overall → in (văn bản | JSON) → mã thoát 0|1
```

Không có trạng thái bền; lệnh không ghi tệp, không đổi môi trường (chỉ tạo và dọn một symlink thử trong thư mục tạm).

<a id="tep-cau-hinh-va-noi-dung"></a>
## Tệp cấu hình và nơi dùng

| Tệp | Nơi dùng | Ghi chú |
|---|---|---|
| `.github/workflows/ci.yml` (hoặc tên do task chọn) | Dịch vụ CI | Ma trận 6 ô; kiểm tĩnh bởi `test_ci_workflow` |
| `.gitattributes` | git | `eol=lf` cho `*.py`, `*.yaml`, `*.yml`, `*.json`, `*.md`, `*.toml`, `*.xml` |
| `docs/04-implementation/install-cross-platform.md` | Người dùng | Hướng dẫn cài đặt (FR-018); lệnh trong đó là lệnh `check_env` xác minh được |
| `pyproject.toml` | uv/pip | **Không đổi** (dấu test đăng ký bằng plugin; phụ thuộc không đổi) — research Q8, Q9 |
| `uv.lock` | uv | **Không đổi**; chỉ `uv lock --check` |

<a id="bat-bien-lien-quan-du-lieu"></a>
## Bất biến liên quan dữ liệu

`INV-004` (năng lực sai-an-toàn) áp cho `Capability`/`DisplayProbe`; `INV-005` (UTF-8, LF, đường dẫn tương đối) áp cho mọi tệp ghi và cho `check_env --json`; `INV-007` (đơn vị RAM) áp cho `ram_peak_mb`; `INV-006` áp cho `Dấu năng lực`. Không bất biến mới phát sinh ở bước plan.
