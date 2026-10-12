---
id: "DM-010"
title: "Đồng bộ tài liệu — Mô hình tài liệu (Document model): khẳng định → nguồn → cách kiểm"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-13"
feature: "010-docs-platform-sync"
version: "1.0.0"
---

# Mô hình tài liệu (Document model) — 010

- [Phạm vi mô hình](#pham-vi-mo-hinh)
- [Tài liệu và khẳng định bắt buộc](#tai-lieu-va-khang-dinh-bat-buoc)
- [Ánh xạ nhãn ↔ khoá](#anh-xa-nhan-khoa)
- [Khuôn đọc-chỉ của hợp đồng 006 mà tài liệu mô tả](#khuon-doc-chi-cua-hop-dong-006-ma-tai-lieu-mo-ta)

<a id="pham-vi-mo-hinh"></a>
## Phạm vi mô hình

Feature không có bảng/CSDL (không `TBL-*`), không sự kiện (`EVT-*`), không lệnh/truy vấn/API (`CMD-*`/`QRY-*`/`API-*`), không thực thể dữ liệu mới (spec không có Key Entity). Thứ cần mô hình hoá là **quan hệ giữa khẳng định trong tài liệu và nguồn chứng minh nó** — để reviewer và test kiểm một lần, một chỗ.

<a id="tai-lieu-va-khang-dinh-bat-buoc"></a>
## Tài liệu và khẳng định bắt buộc

| Mã | Tài liệu · mục | Khẳng định bắt buộc | Nguồn thật (đối chiếu) | Kiểm bằng | Mã spec |
|---|---|---|---|---|---|
| CL-001 | `README.md` · Tình trạng nền tảng | Gói `mma_ai.compat` đã gộp (dò nền tảng/RAM/màn hình, thay tệp nguyên tử) | `src/mma_ai/compat/{platform_info,memory,display,fsio}.py` | test e2e: chuỗi `mma_ai.compat` + tệp tồn tại; reviewer | FR-001 · AC-1 |
| CL-002 | `README.md` · Tình trạng nền tảng | Báo cáo môi trường `python -m mma_ai.compat.env_report` | `src/mma_ai/compat/env_report.py` | test e2e chạy thật lệnh (mã ∈ {0,1}, JSON) | FR-001, FR-009 · AC-1 |
| CL-003 | `README.md` · Tình trạng nền tảng | Cổng năng lực loại test theo máy | `tests/unit/capability_gate.py`, `conftest.py` (`pytest_plugins`) | reviewer; test chuỗi "cổng năng lực" | FR-001 · AC-1 |
| CL-004 | `README.md` · Tình trạng nền tảng | Ma trận CI 3 HĐH × Python 3.11/3.12 trong `.github/workflows/ci.yml` | `ci.yml` (`os`, `python`) | test e2e: đường dẫn `.github/workflows/ci.yml` tồn tại | FR-001 · AC-1 |
| CL-005 | `README.md` · Tình trạng nền tảng | **Linux = đã kiểm** | QA T640 (Linux) | test e2e: dòng Linux chứa "đã kiểm" | FR-002 · AC-2 |
| CL-006 | `README.md` · Tình trạng nền tảng | **Windows 11, WSL2, macOS, CUDA, ô CI chạy thật trên GitHub Actions = chưa kiểm**; mỗi dòng chứa "chưa kiểm", không chứa "đã kiểm" | QA T640 (CHƯA KIỂM) | test e2e (phân tích từng dòng) | FR-002 · AC-2 · INV-001 |
| CL-007 | `README.md` · Tình trạng nền tảng | Liên kết `specs/006-cross-platform-support/` | thư mục có thật | test liên kết (NFR-DOC-001) | FR-002 · AC-1 |
| CL-008 | `README.md` · Tài liệu | Liên kết `docs/guides/platforms.md` | `docs/guides/platforms.md` | test liên kết + test "README liên kết tới platforms.md" | FR-007 · AC-1 |
| CL-009 | `README.md` | Giữ 10 tiêu đề `##`, bốn lệnh nhanh, huy hiệu | test hiện có | `test_ac1_…document_structure`, `test_ac2_inv004_readme_quickstart` | FR-003 · AC-1 |
| CL-010 | `CHANGELOG.md` · `[Unreleased]` | `### Added` + `### Changed`, dòng cho 006, 007, 008, 009, mỗi dòng liên kết `specs/<NNN-slug>/` | `specs/006…009/spec.md` | test e2e (4 liên kết, 2 tiêu đề nhóm) | FR-004 · AC-1 |
| CL-011 | `CHANGELOG.md` · `[Unreleased]` | Đủ 6 tên dấu: `requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `requires_xdist`, `requires_git_history` | `capability_gate.py` (`pytest_configure`) | test e2e: mỗi tên ∈ dấu khai ở `capability_gate.py` | FR-004, FR-009 · AC-1 |
| CL-012 | `CHANGELOG.md` · `[Unreleased]` | Câu giới hạn: chưa kiểm Windows/macOS/CI thật; chỉ Linux đã kiểm | QA T640 | test e2e: chuỗi "chưa kiểm" trong `[Unreleased]` | FR-005 · AC-2 |
| CL-013 | `CHANGELOG.md` · `[0.1.0]` | Không đổi | `git diff` | reviewer (`git diff` rỗng ở mục này) | FR-005 · AC-1 |
| CL-014 | `CHANGELOG.md` | Không có khối `sh`/`bash` | test hiện có `assert not lines` | `test_ac2_ac3_ac5_inv001_documented_flags[CHANGELOG.md]` | FR-005 |
| CL-015 | `docs/guides/platforms.md` | Lệnh `python -m mma_ai.compat.env_report` và `--json`; mã thoát 0/1 và 2 (cờ lạ) | `env_report.py:main` | test e2e chạy thật | FR-006 · AC-1 |
| CL-016 | `docs/guides/platforms.md` | Ý nghĩa 6 dấu năng lực (khớp mô tả ở `pytest_configure`) | `capability_gate.py` | test e2e (đủ 6 tên) + reviewer đọc ý nghĩa | FR-006 · AC-1 |
| CL-017 | `docs/guides/platforms.md` | Cách đọc `Kiểm thử bị loại theo năng lực: X/Y (R%; giới hạn L%).`, danh sách `nodeid [dấu]: lý do`, ngưỡng 5%, `--capability-report <tệp>` | `pytest_terminal_summary`, `pytest_addoption` | test e2e: cờ ⊆ `python -m pytest --help`; reviewer đọc định dạng | FR-006 · AC-1 |
| CL-018 | `docs/guides/platforms.md` | Test lịch sử git bị loại có báo cáo ở archive không `.git`, lý do `Máy không có lịch sử git`; INV-002 của 008 chỉ chứng minh ở môi trường có git | `capability_gate.py`, spec 009 | reviewer; test chuỗi lý do | FR-006 · AC-1 |
| CL-019 | `docs/guides/platforms.md` | Giới hạn đã/chưa kiểm của từng nền tảng; mục tiêu của 006 ghi là mục tiêu | QA T640, spec 006 Clarifications Q-0002 | test e2e: có "chưa kiểm" cho Windows, macOS, CUDA, CI | FR-006 · AC-2 |
| CL-020 | `docs/guides/platforms.md` | ≤ 120 dòng; `../../README.md`; frontmatter như ba hướng dẫn cũ | test 008 | `test_ac1_…document_structure` | FR-006 · NFR-DOC-002 |
| CL-021 | `docs/guides/replay-demo.md` · bảng mã thoát | Hàng `7` nêu macOS cần `mjpython` (chưa kiểm trên macOS thật) | `src/mma_ai/visualization/cli.py` (mã 7 + gợi ý) | reviewer; `test_ac5_inv001_guide_options[replay-demo.md]` (cờ) | FR-008 · AC-1 |
| CL-022 | `docs/guides/training.md`, `evaluation.md` | Không đổi; kết quả đối chiếu ghi ở verdict | research Q3 | verdict của reviewer | FR-008 · AC-1 |
| CL-023 | mọi tài liệu | Không nhắc `scripts/check_env.py`; không chép số liệu một lượt chạy như hằng số | QA T640; INV-001 | test: không chứa `check_env.py`; reviewer | FR-009 · INV-001 |

<a id="anh-xa-nhan-khoa"></a>
## Ánh xạ nhãn ↔ khoá

Yêu cầu đầu vào không có bảng ánh xạ nhãn hiển thị ↔ khoá dữ liệu cho wire (không có API). Hai danh sách dùng làm khoá đối chiếu của test (một luật: **tên dấu/cờ trong tài liệu là chuỗi nguyên văn từ mã**; nhãn tiếng Việt chỉ nằm ở lời giải thích):

| Khoá (nguyên văn từ mã) | Nhãn tiếng Việt trong tài liệu | Nguồn |
|---|---|---|
| `requires_display` | cần màn hình hiển thị | `capability_gate.py` |
| `requires_cuda` | cần CUDA khả dụng | `capability_gate.py` |
| `requires_symlink` | cần liên kết tượng trưng (symbolic link) | `capability_gate.py` |
| `windows_only` | chỉ chạy trên Windows | `capability_gate.py` |
| `requires_xdist` | cần pytest-xdist | `capability_gate.py` |
| `requires_git_history` | cần lịch sử git | `capability_gate.py` |
| `--json` | in báo cáo môi trường dạng JSON | `env_report.py:main` |
| `--capability-report` | ghi báo cáo JSON về test bị loại | `capability_gate.py:pytest_addoption` |
| `--capability-max-ratio` | tỉ lệ loại tối đa (mặc định 0.05) | `capability_gate.py:pytest_addoption` |

<a id="khuon-doc-chi-cua-hop-dong-006-ma-tai-lieu-mo-ta"></a>
## Khuôn đọc-chỉ của hợp đồng 006 mà tài liệu mô tả

Feature **không định nghĩa** các khuôn này (thuộc 006) và không tạo `contracts/`; chỉ nêu để người viết biết trường nào được phép nhắc.

- Báo cáo môi trường (`env_report --json`, ĐÃ ĐO ở Linux): `schema_version` (`"1.0.0"`), `os{kind, release, machine, is_wsl, tested}`, `python{version, supported, required_range}`, `packages{…}`, `torch_device` (nullable), `capabilities{display, symlink, long_paths, ram_peak, utf8_stdio}` (mỗi mục `{available, reason}`), `checks[]` (`id`, `status ∈ ok|warn|fail`, `message`), `overall ∈ ok|fail`.
- Báo cáo năng lực pytest (`--capability-report`, ĐÃ ĐO): `collected`, `deselected`, `ratio`, `items[]` (`nodeid`, `marker`, `reason`).

Tài liệu mô tả chúng ở mức người đọc (không chép schema); trường nào nêu ra MUST có trong khuôn trên.
