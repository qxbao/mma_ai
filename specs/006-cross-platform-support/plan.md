---
id: "PLAN-006"
title: "Hỗ trợ đa nền tảng (Windows · Linux/WSL2 · macOS) — Kế hoạch triển khai (Implementation plan)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-11"
feature: "006-cross-platform-support"
version: "1.1.0"
---

# Implementation Plan: Hỗ trợ đa nền tảng cho mma_ai (Windows · Linux/WSL2 · macOS)

- [Summary](#summary)
- [Quyết định của người dùng đã áp vào kế hoạch](#quyet-dinh-cua-nguoi-dung)
- [Technical Context](#technical-context)
- [Constitution Check](#constitution-check)
- [Phụ thuộc vào 001–005](#phu-thuoc-vao-001-005)
- [Kiến trúc & tách trách nhiệm](#kien-truc-tach-trach-nhiem)
  - [Quyết định thiết kế](#quyet-dinh-thiet-ke)
- [Project Structure](#project-structure)
  - [Documentation (this feature)](#documentation-this-feature)
  - [Source Code (repository root) — chỉ phần 006 thêm vào hoặc sửa](#source-code-repository-root-chi-phan-006-them-vao-hoac-sua)
- [Lệnh build / test (cho task khung dựng đúng một lần)](#lenh-build-test-cho-task-khung-dung-dung-mot-lan)
- [Truy vết yêu cầu → thiết kế](#truy-vet-yeu-cau-thiet-ke)
- [Rủi ro & việc CHƯA KIỂM](#rui-ro-viec-chua-kiem)
- [Quyết định ở bước tasks](#quyet-dinh-o-buoc-tasks)
- [Phản biện plan_lint](#phan-bien-plan-lint)
- [Complexity Tracking](#complexity-tracking)

**Branch**: `006-cross-platform-support` (tên thư mục feature; không tạo nhánh git) | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: `specs/006-cross-platform-support/spec.md` bản **hiện tại** (1.0.1: Q-0002 đã được người dùng trả lời và đã chuyển vào mục Clarifications; không còn dấu chờ làm rõ nào). Plan này được dựng lại từ đầu trên spec đó, không kế thừa bản plan cũ dựng trên spec chưa áp Q-0002. Khảo sát hiện trạng: `docs/00-survey/mma-ai-cross-platform.md`.

<a id="summary"></a>
## Summary

Feature làm cho M0–M1 chạy giống nhau trên **Windows gốc (môi trường chính), Linux (kể cả WSL2) và macOS Apple Silicon** mà không đổi hành vi nghiệm thu trên Linux. Nó không thêm năng lực nghiệp vụ: nó gom mọi điểm gắn nền tảng vào **một gói lá `mma_ai.compat`**, sửa các điểm gọi hiện có (F-001…F-019) để đi qua gói đó, thêm lệnh `check_env`, tài liệu cài đặt (Windows gốc viết đầu tiên), plugin test theo năng lực và CI ma trận 6 ô.

Cách tiếp cận (chi tiết và số đo ở [research.md](research.md)):

- **Lớp tương thích `mma_ai.compat`** (Q1): tám mô-đun nhỏ, mỗi mô-đun một trách nhiệm, mọi hàm có tham số tiêm (hồ sơ nền tảng, `environ`, đồng hồ, hàm hệ thống) nên **test nhánh Windows/macOS chạy được trên Linux**; test thật theo OS chạy ở ô CI tương ứng.
- **RAM đỉnh theo OS** (Q3): Linux KiB, macOS byte, Windows `PeakWorkingSetSize` qua `ctypes`; `import resource` chỉ trong nhánh; `null` khi không đo được. ĐÃ ĐO Linux: +256,02 MiB khi cấp phát 256 MiB.
- **Dò màn hình một hàm, ba nơi dùng** (Q4): Linux/WSL2 giữ nguyên (biến môi trường rồi GLFW); Windows/macOS không đọc `DISPLAY`/`WAYLAND_DISPLAY`, dò bằng GLFW + màn hình chính; macOS cần `mjpython` cho viewer (NGUỒN TÀI LIỆU của MuJoCo) nên có thông báo tiếng Việt thay vì treo.
- **Ghi nguyên tử dùng chung** (Q5): tệp tạm cùng thư mục, `fsync`, `os.replace`; chỉ Windows thử lại `PermissionError` (≤ 5 lần, ≤ 0,55 s theo lịch) rồi báo lỗi và giữ bản cũ; Linux một lần như cũ.
- **Đường dẫn, UTF-8, LF** (Q6, Q7): `is_absolute_any_os` (ĐÃ ĐO: `is_absolute()` một mình bỏ sót dạng `\…` và ổ đĩa không dấu phân cách), `to_record_path`, `write_text(newline="\n")`, `reconfigure` UTF-8 ở đầu mọi `main()` (ĐÃ ĐO: `PYTHONIOENCODING=cp1252` tái hiện lỗi trên Linux).
- **Test theo năng lực không dùng skip/xfail** (Q9): plugin `tests/capability_gate.py` loại khi thu thập, báo cáo từng test + lý do, thất bại nếu tỷ lệ > 5% (ĐÃ ĐO nguyên mẫu: `1 passed, 1 deselected`).
- **Cài đặt** (Q8): không đổi `pyproject.toml`/`uv.lock`; CPU là mặc định từ khoá, CUDA là bước tuỳ chọn có tài liệu (`--torch-backend`), vì khoá đã có wheel `win_amd64`/`macosx_arm64` (ĐÃ ĐO).
- **CI** (Q10): GitHub Actions, 3 OS × Python 3.11/3.12 = 6 ô; repo chưa có remote nên chỉ kiểm tĩnh tệp (CHƯA KIỂM chạy thật).
- **Phạm vi**: không GPU AMD/Metal, không installer, không M2–M9, không sửa lỗi sản phẩm đã ghi bằng `xfail` hiện hữu.

<a id="quyet-dinh-cua-nguoi-dung"></a>
## Quyết định của người dùng đã áp vào kế hoạch

Nguồn: Q-0002 (C-0035/C-0036), đã ghi ở mục Clarifications của `spec.md`.

| Quyết định của người | Hệ quả cho kế hoạch |
|---|---|
| **Windows gốc là môi trường chính** | Tài liệu cài đặt viết Windows gốc (PowerShell, uv rồi pip) **trước**, WSL2 và macOS sau; lệnh trong plan và tài liệu không dùng cú pháp riêng của bash/zsh để chạy nguyên văn ở PowerShell; ô CI Windows là bằng chứng chính của AC-1, AC-4, AC-5; kiểm tay trên Windows 11 là bước đầu của `quickstart.md`. |
| **CUDA tuỳ chọn, máy người dùng có CUDA** | Đường CPU vẫn là đường nghiệm thu bắt buộc (CI không có GPU); đường CUDA có mục hướng dẫn riêng cho Windows và một kịch bản kiểm tay (`quickstart.md`, kịch bản 1 bước 6) vì máy của người dùng là bằng chứng thật duy nhất; `check_env` báo `torch_device.kind` = `cuda` kèm tên GPU; test cần CUDA mang dấu `requires_cuda` (loại có báo cáo, không skip). |
| **macOS phải chạy tốt** | Mức "chạy", không chỉ "không lỗi": train, evaluate, replay `--headless`, benchmark và toàn bộ test chạy trong ô CI macOS (Apple Silicon); viewer 3D qua `mjpython`; macOS Intel ngoài cấu hình đã kiểm. |
| **Phạm vi Trong gồm các mục dẫn xuất từ (a)–(f)** | Giữ nguyên các thành phần: ép UTF-8, kiểm tiến trình con `spawn`, `venv_python` theo OS, `is_absolute_any_os`, `.gitattributes`, khai báo năng lực symlink/đường dẫn dài, và ba Key Entity (hồ sơ nền tảng, báo cáo `check_env`, ô CI) — không cắt, không thêm thành phần nào khác. |

<a id="technical-context"></a>
## Technical Context

**Language/Version**: Python 3.11–3.12 (`requires-python = ">=3.11,<3.13"` giữ nguyên; máy phát triển đo: 3.12.3)

**Primary Dependencies**: kế thừa 001–005 (`mujoco` 3.15.0, `myo-sim==0.2.3`, `gymnasium>=1.4,<1.5`, `numpy`, `pyyaml`, `jsonschema`; extra `rl`: `torch`, `tensorboard`; extra `eval`; extra `dev`: `pytest`). **Mới: không có.** `ctypes`, `winreg`, `resource`, `glfw` (đi kèm `mujoco`) chỉ nhập lười trong nhánh OS. Không `psutil`, `portalocker`, `platformdirs`

**Storage**: tệp — không CSDL; không đổi khuôn tệp của 001–005; hồ sơ mới duy nhất là JSON của `check_env --json` ([contracts/check-env-report.schema.json](contracts/check-env-report.schema.json))

**Testing**: `pytest` (`python -m pytest`); test nhánh OS bằng hồ sơ nền tảng giả (tiêm) chạy ở mọi OS; test thật theo OS ở ô CI; **một** plugin loại theo năng lực (không `skip`/`skipif`/`xfail`/`importorskip` mới); không mock vật lý; `monkeypatch` chỉ để tiêm lỗi hệ thống (`os.replace`, `os.symlink`, GLFW), đồng hồ và `winreg`, được gọi tên rõ

**Target Platform**: Windows 11 gốc (Python 3.11–3.12, PowerShell) — **môi trường chính, đích tham chiếu**; Linux (Ubuntu, máy phát triển ĐÃ ĐO); WSL2 Ubuntu (CHƯA KIỂM, kể cả WSLg); macOS Apple Silicon (CHƯA KIỂM, mức chạy); phần cứng của người dùng RTX 5060 8GB · Ryzen 9 HX · 32GB RAM (CUDA tuỳ chọn); macOS Intel và Windows ARM64 ngoài cấu hình đã kiểm

**Project Type**: thư viện + CLI nghiên cứu (không máy chủ) kèm CI

**Performance Goals**: không đặt FPS/thông lượng; mục tiêu đo được là NFR-RAM-001 (độ đúng), NFR-DISPLAY-001 (≤ 5 s), NFR-IO-001 (thử lại ≤ 5 lần/≤ 1,0 s), NFR-ENV-001 (`check_env` ≤ 30 s), NFR-CI-001 (≤ 5% loại). Các con số này là giá trị đề xuất đo được, CHƯA KIỂM trên Windows/macOS thật

**Constraints**: không phá hành vi Linux (mọi test M0–M1 xanh phải còn xanh; số test thu thập không giảm); không thêm phụ thuộc nặng; không đổi phiên bản phụ thuộc; không đường dẫn tuyệt đối riêng của máy trong tài liệu/bản ghi/báo cáo; lớp `compat` không nhập `learning`/`evaluation`/`visualization`/`monitoring`/`environment`/`physics`; theo hiến chương (II: không thêm cơ chế bỏ qua test; III: một chủ mỗi tệp; V: không refactor toàn cục)

**Scale/Scope**: 1 gói mới (8 mô-đun + `__init__`, ≈ 700–900 dòng dự kiến); 18 tệp mã nguồn hiện có chỉ đổi điểm gắn nền tảng (cộng 4 tệp evaluate/replay khi có mặt); 1 script; 1 plugin test; 22 tệp test mới (11 unit, 9 integration, 1 e2e, 1 challenge) + 6 tệp test hiện có sửa nhãn/tiêm (`conftest.py`, `test_display.py`, `test_viewer.py`, `test_viewer3d.py`, hai tệp `challenge`) và ca mới ở `test_eval_config.py`; 1 workflow CI; 1 `.gitattributes`; 1 tài liệu cài đặt

<a id="constitution-check"></a>
## Constitution Check

*Cổng: phải qua trước Phase 0; kiểm lại sau Phase 1.* Nguồn: `.specify/memory/constitution.md` v1.0.0.

| Nguyên tắc | Đánh giá | Cách plan đáp ứng |
|---|---|---|
| I. Bằng chứng thắng lời khai | Đạt, **có điều kiện** | Mọi AC có test chạy ngoài và ô CI sinh bằng chứng; phần Windows/macOS thật **chỉ** chứng minh được bằng ô CI hoặc lần chạy thật của người dùng — plan ghi CHƯA KIỂM cho tới khi có bằng chứng do cổng sinh, không khẳng định "đã chạy trên Windows" ở bất kỳ tài liệu nào; ví dụ trong `contracts/examples/` ghi rõ là minh hoạ khuôn |
| II. Test trước, sửa sau | Đạt | Test đặc trưng Linux (QC của spec) xanh **trước** khi đổi mã; mỗi mô-đun `compat` có test đặt tên sẵn ở bảng truy vết, đỏ trước mã; **không** thêm skip/xfail/importorskip — loại theo năng lực bằng plugin (Q9); `xfail`/`importorskip` đã có giữ nguyên |
| III. Lát cắt nhỏ, một vai một task | Đạt, có tệp chung | Mỗi mô-đun `compat` một tệp một task; tệp mã của 001–005 đổi điểm gắn nền tảng **mỗi tệp một task chủ** đứng sau task `compat` tương ứng; tệp test hiện có (`conftest.py`, `test_display.py`, `test_viewer.py`, `test_viewer3d.py`, hai tệp `challenge`) mỗi tệp một task; diff chưa commit của vai khác (evaluate/replay xoá staged) để nguyên |
| IV. Bất biến & phi chức năng có mã số | Đạt | INV-001…007 và NFR-PARITY/RAM/DISPLAY/IO/ENC/ENV/CI-001 khai ở `spec.md` (mỗi NFR có dòng `Ngưỡng` và `Đo bằng`); plan chỉ tham chiếu. **Không có INV/NFR mới phát hiện ở bước plan** |
| V. Không đổi cái không được yêu cầu | Đạt, có ghi chú | `pyproject.toml`/`uv.lock` **không đổi** (Q8 phương án A, Q9 đăng ký dấu bằng plugin); không đổi môi trường/reward/thuật toán; không đổi khuôn tệp; đổi 6 tệp ghi nguyên tử sang hàm chung là **một việc** (điểm gắn nền tảng của (d)), được bảo vệ bằng test byte-đích đặc trưng; đề xuất B (extras CUDA trong `pyproject.toml`) ghi như **đề xuất riêng**, không làm lẫn |
| VI. Bí mật chỉ qua biến môi trường | Đạt | Không bí mật; tài liệu/`check_env`/ví dụ không chứa thư mục riêng của máy hay ký tự ổ đĩa — kiểm bằng `test_report_has_no_absolute_paths` và bộ quét của cổng |
| VII. Nhánh bảo vệ | Đạt | Lượt spec không commit, không đổi nhánh; workflow CI không tự merge/push |
| VIII. Tài liệu sinh từ mã và bằng chứng | Đạt | Số trong `research.md` gắn nhãn ĐÃ ĐO / NGUỒN TÀI LIỆU / CHƯA KIỂM; tài liệu cài đặt chỉ chứa lệnh mà `check_env`/CI xác minh được; không viết tay kết quả CI |
| IX. Mỗi tài liệu MỘT chỗ | Đạt | Data model/hợp đồng CHỈ ở `specs/006-…/`; `docs/` chưa có `02-strategic`/`03-tactical`/`01-intent` ⇒ không có tệp để đồng bộ; tài liệu cài đặt cho người dùng ở `docs/04-implementation/` (tầng triển khai) và không chép lại hợp đồng |

**Kiểm lại sau Phase 1**: Đạt — thiết kế không thêm phụ thuộc, không đổi `pyproject.toml`/`uv.lock`; không có vi phạm cần ghi ở Complexity Tracking ngoài mục đã biện minh.

**Quy mô tài liệu & kiến trúc**: vẫn **một bounded context** (mô phỏng và huấn luyện cơ–xương, gói `mma_ai`) như 001–005; `compat` là gói hạ tầng lá trong cùng context, không phải context mới (không có ≥ 2 bounded context hay dịch vụ) ⇒ KHÔNG ghi `docs/02-strategic/context-map.md`, `docs/03-tactical/*` hay `docs/01-intent/overview.md` (không aggregate/invariant/NFR của context nào đổi; INV/NFR của feature này là xuyên suốt nền tảng và sống ở `spec.md`; hiện `docs/` không có tệp nào thuộc ba tầng đó để đọc hay đồng bộ). **Không có phân quyền** (lệnh cục bộ, không vai/khoá/token) ⇒ không `rbac.md`. Không có API HTTP ⇒ không có `contracts/<api-id>.schema.json` theo kiểu dây mạng; hợp đồng dây duy nhất là JSON của `check_env --json` có schema + ví dụ. Stack không đổi (`python-mujoco-cli`) ⇒ **không ghi lại `.ai/stack-proposal.yml`** (đã có bản máy kiểm; stack, cổng và preset không đổi — `preset.layer_rules` chưa nhắc `compat`, đề xuất thêm `compat` vào mọi dòng quy tắc tầng ở "Quyết định ở bước tasks").

<a id="phu-thuoc-vao-001-005"></a>
## Phụ thuộc vào 001–005

Feature **sửa điểm gắn nền tảng** của mã 002–005 đã có; nó không đổi hành vi của chúng. Dựa vào các thành phần sau (đã có mã trừ khi ghi khác):

| Mã | Thành phần | Dùng để | Ghi chú |
|---|---|---|---|
| D-1 | 003: `learning/{resources,manifest,checkpoint,progress,metrics_log,benchmark,trainer,cli,compare_cli}.py`, `monitoring/{cli,viewer3d}.py` | Điểm gọi cần chuyển sang `compat` (F-001, F-002, F-004, F-005, F-007, F-012, F-018, F-019) | Mỗi tệp **một task chủ** của 006; `.ai` xếp wave theo va chạm `outputs` với task cũ của 003 |
| D-2 | 004: `evaluation/eval_config.py` (còn) và `evaluation/{runner,cli,…}.py` (đang xoá staged) | F-009, F-012 | Phần xoá staged **chờ phụ thuộc**: task chỉ tạo khi các tệp có mặt ở nhánh tích hợp (research Q12) |
| D-3 | 005: `visualization/{display,viewer,recorder,summary,episode}.py` (còn), `replay.py`, `cli.py` (đang xoá staged); `conftest.py`, `tests/unit/test_display.py`, `tests/unit/test_viewer.py` | F-003, F-007, F-010, F-012, F-017 | Như D-2 cho `replay.py`/`cli.py` |
| D-4 | 002: `environment/verify_clean_install.py`; `tests/challenge/test_env_invariants.py` | F-013, F-015 | |
| D-5 | 003: `tests/challenge/test_train_invariants.py`, `tests/integration/test_viewer3d.py` | F-016, F-017 | |
| D-6 | `mujoco` 3.15.0 (`mujoco.viewer`, `mjpython`), `glfw` 2.10.2, `uv` | viewer, dò màn hình, cài đặt | ĐÃ ĐO wheel trong khoá; hành vi Windows/macOS CHƯA KIỂM |

**Quy tắc thứ tự** (cho bước tasks): (1) test đặc trưng Linux (xanh trên mã cũ) trước mọi thay đổi; (2) mô-đun `compat` (lá) trước mã gọi chúng; (3) plugin `capability_gate` + sửa `conftest.py` trước mọi test dùng dấu và trước các sửa `test_display.py`/`test_viewer3d.py`/hai tệp `challenge`; (4) `scripts/check_env.py` sau `compat/env_report.py`; (5) CI, `.gitattributes` và tài liệu cài đặt sau `check_env`; (6) test e2e/challenge sau cùng. Lệch hợp đồng khi triển khai ⇒ sửa ở nơi chủ sở hữu, không sao chép.

<a id="kien-truc-tach-trach-nhiem"></a>
## Kiến trúc & tách trách nhiệm

Phụ thuộc một chiều: `learning · evaluation · visualization · monitoring · environment → compat`; `compat` chỉ phụ thuộc thư viện chuẩn (và nhập lười `glfw`, `torch`, `winreg`, `resource`, `ctypes`). Mô-đun mới (đều dưới `src/mma_ai/compat/`):

| Mô-đun | Trách nhiệm | FR / INV |
|---|---|---|
| `platform_info` | `PlatformProfile`, `detect_platform` (bốn loại, `tested`, tiêm được) | FR-002 |
| `memory` | `ram_mib_from_raw`, `peak_ram_mb` (nguồn theo OS, `null` khi thất bại) | FR-004, FR-003, INV-002, INV-007 |
| `display` | `probe_display` → `DisplayProbe` (theo OS, tiêm GLFW) | FR-005, FR-006, FR-008, INV-004 |
| `capabilities` | `Capability`, `symlink_supported`, `long_paths_enabled`, `ram_probe`, `utf8_stdio_ok` | FR-014, INV-004 |
| `fsio` | `replace_atomic`, `write_text_atomic`, `write_bytes_atomic`, `AtomicWriteError` | FR-009, FR-012, INV-003, INV-005 |
| `pathrules` | `is_absolute_any_os`, `to_record_path`, `venv_python` | FR-010, FR-011, FR-016 |
| `stdio` | `ensure_utf8_stdio` | FR-013 |
| `env_report` | `build_environment_report`, `render_text`, `main` (= `CMD-PLT-0001`) | FR-017, FR-024 |

Ngoài gói: `scripts/check_env.py` (vỏ 5 dòng gọi `env_report.main`), `tests/capability_gate.py` (plugin, nạp từ `conftest.py`), `.github/workflows/ci.yml`, `.gitattributes`, `docs/04-implementation/install-cross-platform.md`.

<a id="quyet-dinh-thiet-ke"></a>
### Quyết định thiết kế

- **Một phép dò, giữ chữ cũ**: `probe_display` giữ nguyên chữ thông điệp Linux của `display.py` (INV-001); `display_available()` vẫn trả `DisplayStatus` như cũ nên test hiện có và hợp đồng `API-VIS-0008` của 005 không đổi.
- **Đường tắt Linux của `View3D.has_display()`**: biến môi trường trống ⇒ trả False ngay (không nạp GLFW), đúng như hiện nay; chỉ Windows/macOS (và Linux khi có biến) nạp GLFW — trong tiến trình con riêng đã có cờ `--view3d` (Q-0001: chỉ-đọc, tiến trình riêng).
- **Hàm chung có tham số tiêm**: mọi hàm `compat` nhận hồ sơ/`environ`/hàm hệ thống tuỳ chọn để test dựng Windows/macOS trên Linux; không có biến toàn cục trạng thái; không singleton.
- **Không đổi mã tạo tiến trình**: Linux giữ `fork` mặc định (INV-001); thêm test `spawn` ở cả ba OS (Q11) — đặc biệt quan trọng vì Windows (môi trường chính) chỉ có `spawn`.
- **Thử lại chỉ Windows**: tránh làm chậm/đổi hành vi lỗi thật trên Linux/macOS (ví dụ hết quyền ghi phải lỗi ngay).
- **Plugin test nằm ở `tests/`, không trong gói phân phối**: pytest không phải phụ thuộc chạy; đăng ký dấu bằng `addinivalue_line` nên `pyproject.toml` không đổi.
- **Lệnh trung lập shell**: mọi lệnh trong plan, `quickstart.md`, tài liệu cài đặt và workflow là một dòng `uv …`/`python …` không dùng cú pháp riêng của bash/zsh (không `&&` lồng, không `export`, không `$(…)`), để chạy nguyên văn ở PowerShell, bash và zsh; biến môi trường cho test (ví dụ `PYTHONIOENCODING`) đặt qua tham số `env` của `subprocess` trong test, không qua cú pháp shell.
- **Kiểm chứng tương xứng**: test assert thẳng trên sản phẩm; KHÔNG tự viết bộ kiểm an ninh riêng cho đường dẫn/ghi tệp ngoài các luật spec nêu (`is_absolute_any_os` là luật của spec, không phải validator chống tấn công); challenger chỉ fuzz các luật này (không đòi chuẩn trình duyệt/an ninh).

<a id="project-structure"></a>
## Project Structure

<a id="documentation-this-feature"></a>
### Documentation (this feature)

```text
specs/006-cross-platform-support/
├── plan.md
├── research.md          # Q1 gói · Q2 nhận diện · Q3 RAM · Q4 màn hình/macOS · Q5 ghi nguyên tử · Q6 đường dẫn · Q7 UTF-8/LF · Q8 cài đặt · Q9 test theo năng lực · Q10 CI · Q11 spawn · Q12 phạm vi CLI · Q13 bất định
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md                          # CMD-PLT-0001, quy ước CLI chung, hợp đồng thu thập test
│   ├── python-api.md                   # API-PLT-0001…0009
│   ├── check-env-report.schema.json
│   └── examples/                       # ví dụ hợp schema (minh hoạ khuôn, không phải số đo)
└── tasks.md             # bước /speckit-tasks — KHÔNG tạo ở bước plan
```

<a id="source-code-repository-root-chi-phan-006-them-vao-hoac-sua"></a>
### Source Code (repository root) — chỉ phần 006 thêm vào hoặc sửa

```text
src/mma_ai/
└── compat/                         # MỚI — gói lá
    ├── __init__.py
    ├── platform_info.py   memory.py        display.py     capabilities.py
    ├── fsio.py            pathrules.py     stdio.py       env_report.py
scripts/
└── check_env.py                    # MỚI — vỏ 5 dòng gọi mma_ai.compat.env_report.main (xem "Quyết định ở bước tasks")
tests/
├── capability_gate.py              # MỚI — plugin loại theo năng lực (không thuộc gói phân phối)
├── unit/        # MỚI: test_compat_platform, test_compat_memory, test_compat_display, test_compat_capabilities,
│                #      test_compat_fsio, test_compat_pathrules, test_compat_stdio, test_env_report,
│                #      test_capability_gate, test_platform_characterization, test_no_new_skip_xfail
├── integration/ # MỚI: test_ram_real_measure, test_display_consumers_agree, test_atomic_replace_locked_windows,
│                #      test_check_env_cli, test_contract_examples_platform, test_ci_workflow,
│                #      test_cross_platform_imports, test_cross_platform_cli_utf8, test_spawn_context
├── e2e/         # MỚI: test_platform_acceptance
└── challenge/   # MỚI: test_platform_invariants
.github/workflows/ci.yml            # MỚI — ma trận 6 ô (tên tệp do task chọn)
.gitattributes                      # MỚI — eol=lf
docs/04-implementation/install-cross-platform.md   # MỚI — hướng dẫn cài đặt (FR-018), mục Windows gốc đứng đầu
```

**Sửa (chỉ điểm gắn nền tảng, mỗi tệp một task chủ)**: `src/mma_ai/learning/{resources,manifest,checkpoint,progress,metrics_log,benchmark,trainer,cli,compare_cli}.py`, `src/mma_ai/monitoring/{cli,viewer3d}.py`, `src/mma_ai/visualization/{display,viewer,recorder,summary,episode}.py`, `src/mma_ai/evaluation/eval_config.py`, `src/mma_ai/environment/verify_clean_install.py`; khi có mặt ở nhánh tích hợp: `src/mma_ai/evaluation/{cli,runner}.py`, `src/mma_ai/visualization/{cli,replay}.py`. Test hiện có sửa nhãn/tiêm (không đổi nghĩa): `conftest.py`, `tests/unit/test_display.py`, `tests/unit/test_viewer.py`, `tests/integration/test_viewer3d.py`, `tests/challenge/test_env_invariants.py`, `tests/challenge/test_train_invariants.py`, và ca mới ở `tests/unit/test_eval_config.py`.

**Structure Decision**: dự án đơn (single project), thêm một gói con lá `compat/` vào cây `src/mma_ai/` của 001–005; plugin test ở `tests/`; không thêm quy tắc `.gitignore`; `pyproject.toml`, `uv.lock`, `.ai/profile.yml` không đổi.

<a id="lenh-build-test-cho-task-khung-dung-dung-mot-lan"></a>
## Lệnh build / test (cho task khung dựng đúng một lần)

Mọi lệnh chạy từ gốc repo và chạy nguyên văn ở PowerShell (Windows gốc), bash/zsh (Linux, WSL2, macOS).

| Việc | Lệnh |
|---|---|
| Dựng môi trường (mọi OS) | `uv python install 3.12` rồi `uv sync --locked --extra dev --extra rl --extra eval` (không extra mới) |
| Kiểm khoá | `uv lock --check` |
| Toàn bộ test (cổng `tests`) | `uv run --isolated --with pytest pytest -q -p no:cacheprovider --ignore=tests/e2e` |
| Test e2e | `uv run python -m pytest -q -p no:cacheprovider tests/e2e` |
| Test riêng feature | `uv run python -m pytest -q tests/unit/test_compat_platform.py tests/unit/test_compat_memory.py tests/unit/test_compat_display.py tests/unit/test_compat_fsio.py tests/unit/test_compat_pathrules.py tests/unit/test_env_report.py tests/unit/test_capability_gate.py tests/integration/test_check_env_cli.py tests/integration/test_ci_workflow.py` |
| Báo cáo test bị loại | `uv run python -m pytest -q --capability-report capability-report.json` (tệp báo cáo là sinh phẩm, không commit) |
| Kiểm môi trường | `uv run python scripts/check_env.py` · `uv run python scripts/check_env.py --json` |
| Lint · kiểu | `uv run --isolated --with ruff ruff check .` · `uv run --isolated --with mypy mypy --strict .` (cổng của `.ai/profile.yml`, không đổi) |
| Đếm test (mốc không giảm) | `test_count_command` của `.ai/profile.yml` |
| macOS, viewer 3D | `mjpython -m <mô-đun CLI>` thay cho `python -m <mô-đun CLI>` (CHƯA KIỂM trên macOS thật) |
| CUDA (tuỳ chọn, tài liệu) | `uv pip install --reinstall --torch-backend=<cuXXX> torch` rồi `uv run --no-sync …` (CHƯA KIỂM) |

Cổng máy (`gates:`) do bước plan_fix nháp từ tệp này; plan không khai tay trong `.ai/profile.yml`.

<a id="truy-vet-yeu-cau-thiet-ke"></a>
## Truy vết yêu cầu → thiết kế

| Yêu cầu | Thực hiện bởi | Bằng chứng / Test |
|---|---|---|
| FR-001, AC-1, INV-001 | toàn bộ sửa điểm gắn + `compat` | `tests/e2e/test_platform_acceptance.py::test_headless_replay_and_benchmark_exit_codes_match_baseline`, `::test_cli_outputs_same_keys_as_linux_baseline`, `::test_check_env_then_train_smoke_then_manifest_ram_plausible` |
| FR-002 | `platform_info` | `test_compat_platform::test_four_kinds_from_injected_inputs`, `::test_wsl2_detected_by_release_or_distro_env`, `::test_untested_configurations_flagged`, `::test_detect_never_raises` |
| FR-003, INV-002 | toàn gói + sửa nhập mức mô-đun | `test_cross_platform_imports::test_every_mma_ai_module_imports`, `::test_no_module_level_os_specific_imports`, `test_compat_memory::test_peak_does_not_import_resource_on_windows_profile` |
| FR-004, INV-007, NFR-RAM-001, AC-2 | `memory`, sửa `learning/resources.py` | `test_compat_memory::test_linux_kib_to_mib`, `::test_macos_bytes_to_mib`, `::test_windows_bytes_to_mib`, `::test_invalid_raw_raises`, `::test_failure_returns_none_not_zero`, `::test_linux_formula_unchanged`, `test_ram_real_measure::test_real_peak_grows_by_allocation_within_band`, `test_platform_characterization::test_linux_kib_formula_matches_legacy` |
| FR-005, NFR-DISPLAY-001, INV-004, AC-3 | `display` | `test_compat_display::test_linux_unset_env_unavailable_exact_message`, `::test_linux_bogus_display_unavailable`, `::test_windows_ignores_display_env_vars`, `::test_macos_ignores_display_env_vars`, `::test_windows_no_primary_monitor_unavailable`, `::test_glfw_exception_is_unavailable_with_detail`, `::test_probe_returns_within_5s_real` |
| FR-006 | sửa `display.py`, `monitoring/viewer3d.py`, `learning/benchmark.py` | `test_display_consumers_agree::test_three_consumers_agree_for_each_profile`, `::test_view3d_linux_shortcut_does_not_import_glfw`, `test_platform_characterization::test_display_unset_message_matches_legacy`, `::test_view3d_has_display_matches_env`, `tests/unit/test_display.py` (sửa), `tests/unit/test_benchmark_logic.py` (hiện có) |
| FR-007 | sửa `visualization/viewer.py`, `monitoring/viewer3d.py` | `tests/unit/test_viewer.py::test_macos_without_mjpython_reports_vietnamese_hint`; kiểm tay trên macOS (CHƯA KIỂM) |
| FR-008 | `compat/display`, đường `--headless` sẵn có | `test_platform_acceptance::test_headless_replay_and_benchmark_exit_codes_match_baseline` + `tests/integration/test_replay_headless.py` của 005 (đang xoá staged — chờ phụ thuộc, research Q12) |
| FR-009, INV-003, NFR-IO-001, AC-4 | `fsio`, sửa 6 tệp ghi | `test_compat_fsio::test_failure_cases_keep_old_bytes_and_clean_tmp`, `::test_windows_retries_permission_error_then_succeeds`, `::test_windows_gives_up_within_one_second_keeps_old_bytes`, `::test_posix_does_not_retry`, `::test_temp_file_in_same_directory`, `test_atomic_replace_locked_windows::test_replace_over_open_destination_keeps_old_bytes`, `test_platform_invariants::test_inv003_fault_injection_never_leaves_partial_file`, `test_platform_characterization::test_atomic_write_bytes_match_legacy` |
| FR-010, AC-4 | `pathrules`, sửa F-012 | `test_compat_pathrules::test_five_absolute_forms_rejected_on_every_os`, `::test_relative_forms_accepted`, `tests/unit/test_eval_config.py` (ca mới theo năm dạng), `test_platform_invariants::test_path_rules_fuzz_never_raises_and_never_leaks_backslash` |
| FR-011, INV-005 | `pathrules.to_record_path` | `test_compat_pathrules::test_to_record_path_uses_slash_and_is_relative`, `tests/unit/test_summary.py::test_paths_relative` (005, hiện có) |
| FR-012, INV-005, NFR-ENC-001 | `fsio`, `.gitattributes`, sửa F-018 | `test_compat_fsio::test_text_is_utf8_lf_no_bom`, `::test_linux_bytes_identical_to_legacy_pattern`, `test_cross_platform_cli_utf8::test_written_text_files_have_no_cr_or_bom` |
| FR-013 | `stdio`, sửa `main()` | `test_compat_stdio::test_reconfigure_sets_utf8_replace`, `::test_stream_without_reconfigure_is_ignored`, `::test_idempotent`, `test_cross_platform_cli_utf8::test_clis_survive_legacy_stdio_encoding` |
| FR-014 | `capabilities` | `test_compat_capabilities::test_symlink_probe_available_when_os_symlink_works`, `::test_symlink_probe_unavailable_with_reason_on_oserror`, `::test_symlink_probe_cleans_up`, `::test_long_paths_always_true_off_windows`, `::test_long_paths_reads_registry_value_on_windows_profile` |
| FR-015 | test `spawn` (mã giữ nguyên) | `test_spawn_context::test_viewer3d_process_target_runs_under_spawn` |
| FR-016 | `pathrules.venv_python`, sửa `verify_clean_install` | `test_compat_pathrules::test_venv_python_by_os`, `tests/unit/test_verify_clean_install.py` (hiện có) |
| FR-017, NFR-ENV-001, AC-5 | `env_report`, `scripts/check_env.py` | `test_env_report::test_wsl_kind_and_flag_agree`, `::test_python_range_check`, `::test_torch_absent_is_warning`, `::test_capability_reason_contract`, `::test_untested_configuration_warns`, `test_check_env_cli::test_json_output_valid_and_exit_matches_overall`, `::test_text_output_vietnamese_one_line_per_check`, `::test_unknown_flag_exits_2`, `::test_report_os_kind_matches_detect_platform`, `test_contract_examples_platform::test_examples_match_schema`, `::test_negative_cases_rejected` |
| FR-018 | `docs/04-implementation/install-cross-platform.md` | `test_env_report::test_report_has_no_absolute_paths`; bộ quét cổng cho đường dẫn tuyệt đối trong `docs/`; kiểm tay trên Windows 11 (CHƯA KIỂM) |
| FR-019 | giữ `pyproject.toml`, `uv.lock` | `uv lock --check` ở ô CI; `tests/integration/test_dependency_decision.py`, `test_dependency_train.py` (hiện có) |
| FR-020, NFR-CI-001, AC-6 | `.github/workflows/ci.yml` | `test_ci_workflow::test_matrix_has_six_cells`, `::test_each_cell_runs_check_env_then_tests`, `::test_lockfile_is_checked_and_locked_sync`, `::test_no_failure_masking_in_workflow` |
| FR-021, INV-006 | `tests/capability_gate.py`, `conftest.py` | `test_capability_gate::test_unsatisfied_marker_is_deselected_not_skipped`, `::test_missing_reason_is_collection_error`, `::test_ratio_over_limit_fails_session`, `::test_report_lists_each_deselected_with_reason`, `test_platform_invariants::test_inv006_deselect_always_reported` |
| FR-022 | sửa 5 tệp test hiện có + `conftest.py` | `tests/challenge/test_env_invariants.py` (`linux_only`), `tests/challenge/test_train_invariants.py` (`requires_symlink`), `tests/integration/test_viewer3d.py` (`requires_display`), `tests/unit/test_display.py` (tiêm hồ sơ), `tests/unit/test_viewer.py` (tiêm hồ sơ macOS), `conftest.py` (cách ly theo OS) |
| FR-023 | toàn bộ bộ test trên | `python -m pytest` + ô CI |
| FR-024 | mọi mô-đun | `test_env_report::test_report_has_no_absolute_paths`, `test_check_env_cli::test_text_output_vietnamese_one_line_per_check`, `test_compat_fsio::test_failure_cases_keep_old_bytes_and_clean_tmp` (lỗi nêu đường dẫn đích) |
| NFR-PARITY-001, AC-1 | bảo vệ bằng đặc trưng | `tests/unit/test_platform_characterization.py` (cả bốn ca), `tests/unit/test_no_new_skip_xfail.py::test_feature_tests_have_no_skip_or_xfail`, `python -m pytest` toàn bộ, `test_count_command` |

<a id="rui-ro-viec-chua-kiem"></a>
## Rủi ro & việc CHƯA KIỂM

1. **Không có máy Windows/macOS trong môi trường phát triển của agent** — mọi hành vi thật của GLFW/MuJoCo/`ctypes`/`os.replace` trên hai OS này là CHƯA KIỂM; test nhánh bằng tiêm chứng minh **logic** chứ không chứng minh **API hệ điều hành**. Bằng chứng duy nhất là ô CI hoặc lần chạy tay của người dùng (máy Windows 11 có CUDA của họ); trước đó mọi tài liệu phải ghi CHƯA KIỂM.
2. **Repo chưa có remote** — workflow CI chỉ kiểm tĩnh; ma trận 6 ô chưa từng chạy. Nếu dịch vụ CI không có runner Windows/macOS trong gói của người dùng thì AC-6 chỉ đạt phần cấu hình.
3. **Runner CI Windows/macOS có hay không có màn hình** — không biết `glfw.init()` thành công hay thất bại ở đó; thiết kế đúng cả hai nhánh (dấu `requires_display` theo chính phép dò), nhưng nếu `glfw.init()` thành công mà tạo cửa sổ vẫn thất bại thì test thật mở viewer sẽ đỏ trên runner đó — cần quan sát lần chạy đầu và bổ sung phép dò "tạo cửa sổ ẩn thử" nếu cần (ghi nhận, chưa thêm vì có thể thừa).
4. **`mjpython` trên macOS** — chuỗi lỗi MuJoCo và cách nhận diện chưa kiểm (research Q4); sai nhận diện làm thông báo không xuất hiện nhưng không gây treo vì lỗi gốc của MuJoCo vẫn nổi lên.
5. **Tệp evaluate/replay đang xoá staged** — AC-1 phủ cả hai; nếu nhánh tích hợp không khôi phục chúng thì test AC-1 tương ứng ở danh sách chờ phụ thuộc (spec nêu rõ, không tự khôi phục).
6. **Thử lại ghi trên Windows** — lịch chờ (0,05/0,10/0,20/0,20 s) là đề xuất; nếu phần mềm quét tệp giữ khoá lâu hơn, ghi checkpoint vẫn lỗi (báo rõ, bản cũ giữ nguyên) — không im lặng; hiệu chỉnh theo số đo CI.
7. **Đường dẫn dài trên Windows** — chưa kiểm Python từ uv/python.org có bật hỗ trợ đường dẫn dài trong manifest ứng dụng; `check_env` chỉ báo cờ Registry; thông báo lỗi khi ghi thất bại vì quá dài là phản ứng cuối.
8. **CUDA trên Windows (máy người dùng)** — `--torch-backend` là tính năng thử nghiệm của uv; giá trị `cuXXX` cho GPU RTX 50-series (RTX 5060) và việc `uv run` cài lại bản trong khoá (phải dùng `--no-sync`) CHƯA KIỂM; tài liệu nêu rõ và `check_env` là cách xác minh; vì CUDA là tuỳ chọn nên thất bại ở đây không chặn nghiệm thu AC-5 (đường CPU).
9. **Đổi 6 tệp ghi sang hàm chung** — rủi ro lệch byte đích trên Linux; giảm bằng test đặc trưng ghi byte của từng cách ghi **trước** khi đổi và test thuộc tính `test_manifest_properties` hiện có phải xanh.
10. **Tải CI** — cài `torch` ≈ 124–555 MB mỗi ô × 6 ô; ngân sách thời gian CHƯA KIỂM; có thể phải cache của uv hoặc giảm test nặng bằng dấu.
11. **Preset `python-mujoco-cli`** — `layer_rules` chưa liệt kê `compat`; nếu cổng kiến trúc của kit từ chối nhập từ `compat` thì cần khai (việc của vai platform/conductor, ghi ở tasks).
12. **Shell của runner Windows** — shell mặc định là PowerShell; workflow chỉ dùng lệnh một dòng không cú pháp riêng của bash để không phụ thuộc shell; nếu vẫn lỗi trích dẫn thì đặt `shell: bash` ở bước tương ứng (CHƯA KIỂM).

<a id="quyet-dinh-o-buoc-tasks"></a>
## Quyết định ở bước tasks

- **Vai `challenger`: CÓ DÙNG** (một task `challenge` cuối dải) — Tự chốt: spec khai INV-003 (ghi nguyên tử) và INV-004 (năng lực sai-an-toàn) mà đầu vào người dùng/hệ thống chạm được (đường dẫn tuỳ ý từ cấu hình và CLI, đích đang bị giữ, ngoại lệ lạ của GLFW/Registry); `is_absolute_any_os`/`to_record_path` fuzz được không cần máy Windows; đây là chỗ "sai ngầm" đắt nhất (bản ghi hỏng, lệch byte giữa OS). Cổng review cần nhất trí reviewer + challenger.
- **Khoảng trống năng lực (capability gap) đã biết từ `005`**: bảng vùng ghi hiệu lực có thể không phủ `scripts/**`, `.github/**`, `.gitattributes`, `docs/04-implementation/**`. Tự chốt: đặt MỌI logic ở `src/mma_ai/compat/` (kể cả `env_report.main`, chạy được bằng `python -m mma_ai.compat.env_report`) nên AC-5 chứng minh được qua entrypoint module mà không cần `scripts/check_env.py`; giao `.github/**` và `.gitattributes` cho vai `platform` (hạ tầng/CI), tài liệu cài đặt cho vai `writer`; nếu vùng ghi của vai không phủ đường nào trong số đó thì **KHÔNG** dồn sang `builder` bằng cách khai output ngoài vùng — ghi khoảng trống và đề xuất `ai-sdlc capability propose <dự-án> "vùng ghi cho scripts/** và .github/** và .gitattributes"`; việc CHƯA CÓ CHỦ khi đó: (a) vỏ `scripts/check_env.py` 5 dòng, (b) workflow CI, (c) `.gitattributes`, (d) tài liệu cài đặt. Cho tới lúc đó AC-5 qua `python -m mma_ai.compat.env_report`, AC-6 chỉ phần cơ chế loại + kiểm tĩnh nếu workflow chưa tạo được — trạng thái nêu ở `tasks.md` và ma trận truy vết.
- **Khung dự án**: không dựng khung mới; mọi task đứng sau test đặc trưng. `pyproject.toml`, `uv.lock` không thuộc `outputs` của bất kỳ task nào.
- **Phụ thuộc chéo feature**: dùng id task có sẵn của 002–005 khi khai `depends_on` (xem `specs/00N-*/tasks.md`); id của 006 dùng dải `T601`…; tệp trùng `outputs` với task cũ do máy xếp wave.
- **Cổng E2E**: task `qa` chạy `uv run python -m pytest -q tests/e2e` (gồm `test_platform_acceptance`) trên entrypoint thật; cổng `e2e` do `plan_fix` nháp từ `tasks.md`.
- **Kiểm tay trên máy người dùng**: một task `qa` cuối dải ghi kết quả kiểm tay Windows 11 (cài từ tài liệu, `check_env`, viewer 3D, CUDA) vào báo cáo; kết quả giữ nhãn CHƯA KIỂM cho tới khi có bằng chứng do cổng sinh (hiến chương I).
- **Đề xuất (không làm trong feature)**: thêm `compat` vào `layer_rules` của preset; extras `rl-cpu`/`rl-cuda` trong `pyproject.toml` (research Q8-B); phép dò "tạo cửa sổ ẩn thử" nếu runner CI có GLFW khởi tạo được nhưng không mở được cửa sổ.

<a id="phan-bien-plan-lint"></a>
## Phản biện plan_lint

- Tạo cả gói `compat` thay vì thêm vài hàm vào `learning/resources.py` và `visualization/display.py`: nếu chỉ sửa tại chỗ thì ba bản dò màn hình và sáu bản ghi nguyên tử vẫn lệch nhau trên Windows; gói lá chỉ gồm tám mô-đun nhỏ, không có trạng thái, không phụ thuộc ngoài — đủ nhỏ để review và là nơi duy nhất cần kiểm theo OS.
- Plugin loại test thay vì `skipif`: `skipif` là cơ chế bỏ qua bị hiến chương II cấm và che lỗi thật; loại có báo cáo + ngưỡng 5% + lỗi khi thiếu lý do đảm bảo "bỏ qua có chủ đích" nhưng nhìn thấy được. Chi phí: một plugin ≈ 100 dòng, đã nguyên mẫu hoá được (ĐÃ ĐO).
- Không dùng `psutil` cho RAM đỉnh: thêm phụ thuộc trái ràng buộc, và không cho đỉnh RSS trên Linux; `ctypes` ở nhánh Windows đủ và chỉ chạy ở đó.
- Không đổi `pyproject.toml` để chọn torch CUDA dù máy người dùng có CUDA: đổi phụ thuộc/khoá ngoài phạm vi (hiến chương V) và có thể làm đỏ test phụ thuộc hiện có; CUDA là tuỳ chọn theo quyết định của người dùng nên tài liệu + `check_env` đáp ứng "có hướng dẫn"; đề xuất B ghi riêng để người dùng quyết định nếu muốn cài CUDA bằng một lệnh.
- Thử lại chỉ trên Windows: nếu thử lại cả trên Linux sẽ đổi hành vi lỗi (che lỗi quyền thật) — vi phạm INV-001.
- Dò GLFW ngay trong `View3D.has_display()` trên Windows/macOS tốn thời gian hơn đọc biến môi trường: chấp nhận vì phép dò chạy trong tiến trình con riêng và chỉ khi có `--view3d`; Linux giữ đường tắt (không đổi chi phí).
- Chưa có số đo thật nào trên Windows/macOS: mọi ngưỡng là đề xuất (đã nêu ở Clarifications); nghiệm thu dựa vào test, mã thoát và ô CI, không dựa vào plan.

<a id="complexity-tracking"></a>
## Complexity Tracking

Không có vi phạm hiến chương cần biện minh. Độ phức tạp thêm vào được biện minh bằng số đo/quan sát: gói `compat` — vì có 3 bản dò màn hình và ≥ 8 chỗ ghi nguyên tử đang lệch nhau (đọc mã, F-003/F-004/F-005/F-007); tham số tiêm — vì không có máy Windows/macOS nên test nhánh OS chỉ chạy được nếu tiêm (đã nêu ở Rủi ro 1); plugin loại theo năng lực — vì hiến chương II cấm `skip`/`xfail` còn yêu cầu (f) đòi "bỏ qua có chủ đích" (ĐÃ ĐO nguyên mẫu); `is_absolute_any_os` thay `startswith("/")` — vì `PureWindowsPath("\\runs").is_absolute()` là `False` (ĐÃ ĐO) nên dùng `is_absolute()` một mình bỏ sót hai dạng. Phương án đơn giản hơn (sửa tại chỗ, `skipif`, `psutil`) không đáp ứng các tiêu chí đó.
