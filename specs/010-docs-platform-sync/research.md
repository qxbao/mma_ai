---
id: "RESEARCH-010"
title: "Nghiên cứu Phase 0 — nguồn bằng chứng nền tảng, tác động lên test 008, đối chiếu hướng dẫn hiện có"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-13"
feature: "010-docs-platform-sync"
version: "1.0.0"
---

# Research (Phase 0): đồng bộ tài liệu với mã đã gộp

- [Q1 — Điều gì ĐÃ kiểm và CHƯA kiểm về đa nền tảng?](#q1-dieu-gi-da-kiem-va-chua-kiem-ve-da-nen-tang)
- [Q2 — Thêm `platforms.md` và đổi README làm test 008 nào đỏ?](#q2-them-platformsmd-va-doi-readme-lam-test-008-nao-do)
- [Q3 — Ba hướng dẫn hiện có có lệch với mã không?](#q3-ba-huong-dan-hien-co-co-lech-voi-ma-khong)
- [Q4 — Lệnh/marker nào có thật để tài liệu nêu?](#q4-lenhmarker-nao-co-that-de-tai-lieu-neu)
- [Q5 — Ghi chú nào ngoài phạm vi nhưng ảnh hưởng tài liệu?](#q5-ghi-chu-nao-ngoai-pham-vi-nhung-anh-huong-tai-lieu)

Ký hiệu: **ĐÃ ĐỌC** (đọc mã/tài liệu), **ĐÃ ĐO** (chạy lệnh ở HEAD `b82d690` trên Linux), **CHƯA KIỂM**.

<a id="q1-dieu-gi-da-kiem-va-chua-kiem-ve-da-nen-tang"></a>
## Q1 — Điều gì ĐÃ kiểm và CHƯA kiểm về đa nền tảng?

**Decision**: README/CHANGELOG/`platforms.md` chỉ ghi *đã kiểm* cho **Linux**; *chưa kiểm* cho Windows 11, WSL2, macOS, CUDA và các ô CI chạy thật trên GitHub Actions.

**Rationale** (ĐÃ ĐỌC `.ai/runs/run-20261012-0ecb0c/reports/qa-006-crossplatform.md`, trạng thái `DONE_WITH_CONCERNS`):

- Đã chạy Linux: e2e 54 passed/1 skipped; unit+integration 1425 passed; `ruff`, `mypy --strict` xanh; `python -m mma_ai.compat.env_report` qua entrypoint thật; schema báo cáo và trạng thái Linux được kiểm.
- Chỉ chứng minh logic bằng hồ sơ tiêm/kiểm tĩnh: quy đổi RAM, hồ sơ `windows`/`macos`, ngoại lệ GLFW, ghi nguyên tử lỗi, năm dạng đường dẫn, workflow CI khai ma trận 3 OS × Python 3.11/3.12.
- CHƯA KIỂM (QA nêu thẳng): Windows 11 thật, WSL2, macOS thật (kể cả chạy viewer bằng `mjpython`), đo RAM thật trên Windows/macOS, CUDA (RTX 5060, giá trị backend chưa xác minh), 6/6 ô CI thật.
- Q-0002 (người, C-0036) chốt **mục tiêu**: Windows gốc là môi trường chính, CUDA tuỳ chọn, macOS phải chạy tốt → tài liệu ghi là mục tiêu của 006, không là kết quả.

**Alternatives considered**: (a) ghi "hỗ trợ Windows/macOS" vì mã đã gộp — bị loại, khẳng định hơn bằng chứng (INV-001); (b) giữ nguyên "đang được triển khai" — bị loại, lỗi thời với mã đã gộp (D-1 của spec); (c) ghi WSL2 là cách chạy khuyến nghị — bị loại, WSL2 chưa kiểm.

**Cập nhật bằng chứng**: nếu trước lúc thi công đã có ô CI chạy thật hoặc máy Windows/macOS thật, vai thi công MUST đưa bằng chứng đó cho người duyệt trước khi đổi "chưa kiểm" (Assumptions của spec).

<a id="q2-them-platformsmd-va-doi-readme-lam-test-008-nao-do"></a>
## Q2 — Thêm `platforms.md` và đổi README làm test 008 nào đỏ?

**ĐÃ ĐO**: `pytest tests/e2e/test_008_docs_entrypoints.py --capability-report=/dev/stdout` ở HEAD → **24 passed**, `collected 24`, `deselected 0` (mốc số test không giảm).

**ĐÃ ĐỌC** — tác động của thay đổi dự kiến:

| Test (tệp `tests/e2e/test_008_docs_entrypoints.py`) | Điều test đang khẳng định | Bị ảnh hưởng bởi | Xử lý của qa (task D) |
|---|---|---|---|
| `test_ac2_inv003_platform_claims_match_draft_support` | README có "Linux", "WSL2", "Windows", "macOS", `specs/006-…/`, "đang được triển khai", "chưa xác nhận khả năng chạy"; 006 `status: draft` | README mới | Đổi sang: danh sách hạng mục (Linux đã kiểm; Windows 11, WSL2, macOS, CUDA, ô CI chạy thật chưa kiểm — mỗi hạng mục chưa kiểm không chứa "đã kiểm"), có `specs/006-cross-platform-support/` và `mma_ai.compat.env_report`; **giữ** `^status: draft$` |
| `test_ac1_ac2_ac3_ac4_ac5_document_structure` | `docs/guides` chứa **đúng** `set(GUIDES)`; mỗi guide ≤ 120 dòng và có `../../README.md`; README đúng 10 tiêu đề `##` | thêm `platforms.md` | thư mục = `set(GUIDES) | {platforms.md}`; vòng độ dài/liên kết lặp cả `platforms.md`; README giữ 10 tiêu đề |
| `test_ac2_ac3_ac5_inv001_documented_flags[…]` | mỗi dòng lệnh trong khối `sh`/`bash` ánh xạ được bằng `_command_for_line`, cờ có ở `--help` | `platforms.md` có lệnh `env_report`, `pytest` | thêm ánh xạ cho `python -m mma_ai.compat.env_report` và `python -m pytest`; đối chiếu cờ theo D-3 của plan; CHANGELOG vẫn `assert not lines` |
| `test_ac5_inv001_guide_options[…]` | cờ nêu bằng văn xuôi trong mỗi guide có ở CLI ánh xạ trong `GUIDES` | `platforms.md` không ánh xạ được 1 CLI | thêm ca riêng cho `platforms.md`: cờ ⊆ cờ của `env_report` ∪ cờ của pytest (nguồn thật) |
| `test_ac2_ac3_ac4_ac5_inv004_relative_links[…]` | mọi liên kết tương đối có đích | `platforms.md`, README, CHANGELOG mới | thêm `platforms.md` vào `DOCUMENTS` |
| `test_inv002_document_commits_keep_product_code_untouched` | commit **tạo** README/CHANGELOG chỉ chạm tập `allowed` dựng từ `GUIDES` | **nếu** `platforms.md` bị thêm vào `GUIDES` | **KHÔNG thêm vào `GUIDES`** (D-2); thân test và dấu `requires_git_history` giữ nguyên |
| `test_ac2_inv004_readme_quickstart`, `test_ac2_ac5_inv001_cli_help[…]`, `test_ac2_nfr_doc002_first_step_is_executable` | bốn lệnh nhanh; `--help` của bốn CLI | không đổi | giữ nguyên |

**Decision**: dùng hằng riêng cho `platforms.md` (D-2) và đối chiếu cờ bằng thực thi thật (D-3).

**Rationale**: `env_report` ĐÃ ĐO: `python -m mma_ai.compat.env_report` → in 11 dòng `[ok]/[CẢNH BÁO]` + "Môi trường đạt yêu cầu.", mã 0 (torch chưa cài chỉ là cảnh báo); `--json` → một dòng JSON có `schema_version`, `os.kind`, `capabilities`, `checks`, `overall`; `--bogus` → "Cờ không được hỗ trợ: --bogus", mã 2. `main()` ĐÃ ĐỌC: trả 1 khi `overall == "fail"`, 0 khác. Cơ chế `_help()` đòi chuỗi `usage:` nên không dùng được cho `env_report`.

**Alternatives considered**: (a) thêm `--help` cho `env_report` — loại, sửa `src/` ngoài phạm vi; (b) bỏ qua kiểm cờ của `platforms.md` — loại, nới lỏng (INV-003/INV-004); (c) bỏ `platforms.md` khỏi kiểm liên kết — loại, vi phạm NFR-DOC-001.

<a id="q3-ba-huong-dan-hien-co-co-lech-voi-ma-khong"></a>
## Q3 — Ba hướng dẫn hiện có có lệch với mã không?

Hướng dẫn được tạo ở commit `98366d6`. ĐÃ ĐỌC `git diff 98366d6 HEAD -- src scripts` cho CLI liên quan:

| Hướng dẫn | Thay đổi mã từ `98366d6` | Cờ/mã thoát/đầu ra của hướng dẫn còn đúng? | Kết luận |
|---|---|---|---|
| `training.md` (`scripts/train.py`) | `learning/cli.py` chỉ thêm `ensure_utf8_stdio()`; `monitoring/cli.py` ghi `ui.json` qua `write_text_atomic`; không đổi cờ/mã thoát | Đúng (6 cờ và bảng mã `0,1,2,3,4,130` không đổi) | **Không đổi** |
| `evaluation.md` | `evaluation/cli.py` thêm `ensure_utf8_stdio()`; `eval_config.py` từ chối đường dẫn tuyệt đối theo mọi OS (trước chỉ bắt đầu bằng `/`); `report.py` ghi nguyên tử và chuẩn hoá đường dẫn ghi vào báo cáo | Đúng (cờ `--checkpoint --config --out --repeats --eval-seed --runs-dir` và mã `0,1,2,4,5,6,7` không đổi; hướng dẫn không nêu quy tắc đường dẫn tuyệt đối) | **Không đổi** |
| `replay-demo.md` | `visualization/cli.py` thêm: trên macOS, không `--headless`, khi `exit_code != 0` và có gợi ý khởi chạy → in gợi ý `mjpython` ra stderr và **đổi mã thoát thành 7** (ĐÃ ĐỌC dòng 41–64) | Cờ đúng; hàng `7` ("Không có màn hình dùng được; thử `--headless`") thiếu trường hợp macOS cần `mjpython` | **Sửa đúng một chỗ**: hàng mã `7` thêm macOS/`mjpython`, ghi *chưa kiểm trên macOS thật* (QA T640; quickstart 006 kịch bản 3 bước 4) |

Ngoài ra test 008 đã đối chiếu cờ của ba hướng dẫn với `--help` thật (ĐÃ ĐO: 24 passed). Việc đối chiếu mã thoát ở bảng trên là ĐÃ ĐỌC (không chạy CLI để gây từng mã).

**Decision**: chỉ sửa `replay-demo.md` (D-6). **Alternatives considered**: viết lại cả ba hướng dẫn — loại, yêu cầu "chỉ sửa nếu lệnh/đầu ra đã đổi".

<a id="q4-lenhmarker-nao-co-that-de-tai-lieu-neu"></a>
## Q4 — Lệnh/marker nào có thật để tài liệu nêu?

ĐÃ ĐỌC / ĐÃ ĐO:

| Thứ cần nêu | Nguồn thật | Ghi chú |
|---|---|---|
| `python -m mma_ai.compat.env_report [--json]` | `src/mma_ai/compat/env_report.py` (`main`, dòng 232–249) | mã 0/1/2; không `--help` |
| Sáu dấu năng lực `requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `requires_xdist`, `requires_git_history` | `tests/unit/capability_gate.py` (`pytest_configure`, dòng 59–68; `_capability_available`, dòng 75–113) | bộ cổng còn có `posix_only`, `linux_only`, `macos_only` — **chỉ nêu nếu cần**, yêu cầu nêu sáu dấu |
| Ý nghĩa từng dấu | mô tả trong `pytest_configure`: màn hình hiển thị; CUDA khả dụng; liên kết tượng trưng; chỉ Windows; pytest-xdist; lịch sử git (`git rev-parse --is-inside-work-tree` ở gốc dự án, `timeout=5`) | |
| Báo cáo "bị loại X/Y" | `pytest_terminal_summary`: `Kiểm thử bị loại theo năng lực: X/Y (R%; giới hạn L%).` rồi từng dòng `  <nodeid> [<dấu>]: <lý do>` (ĐÃ ĐO `0/24 (0.0%; giới hạn 5.0%)`) | tỉ lệ vượt ngưỡng ⇒ dòng "Tỷ lệ test bị loại vượt ngưỡng cho phép." và phiên đỏ |
| `--capability-report <tệp>`, `--capability-max-ratio` (mặc định 0.05) | `pytest_addoption` (dòng 43–56); báo cáo JSON có `collected`, `deselected`, `ratio`, `items` (ĐÃ ĐO) | đã dùng ở `ci.yml` và `.ai/profile.yml` |
| Ma trận CI | `.github/workflows/ci.yml`: `os: [ubuntu-latest, macos-latest, windows-latest]` × `python: ["3.11","3.12"]`, bước `env_report --json`, `pytest --capability-report`, e2e | **chưa chạy thật** |
| Vì sao test lịch sử git bị loại ở archive | spec 009 + `capability_gate.py` | lý do `Máy không có lịch sử git`; INV-002 của 008 chỉ chứng minh ở môi trường có git |
| `mjpython` trên macOS | `src/mma_ai/visualization/cli.py` + `compat/display.py` (`viewer_launch_hint`) | hành vi macOS CHƯA KIỂM |
| `scripts/check_env.py` | **không tồn tại** (`scripts/` chỉ có `train.py`) | không nêu (D-9) |

<a id="q5-ghi-chu-nao-ngoai-pham-vi-nhung-anh-huong-tai-lieu"></a>
## Q5 — Ghi chú nào ngoài phạm vi nhưng ảnh hưởng tài liệu?

- `.github/workflows/ci.yml` dòng 10: "Ma trận (matrix) chưa chạy trên dịch vụ CI thật vì kho chưa có kho từ xa (remote)" — lỗi thời (`git remote -v` ĐÃ ĐO: `origin git@github.com:qxbao/mma_ai.git`). Không sửa (Out of Scope); khuyến nghị vai platform lượt khác. Tài liệu chỉ nói "ô CI chạy thật chưa kiểm" (không khẳng định nguyên nhân).
- Khoảng trống năng lực còn mở trong báo cáo QA T640 (xem phần cuối báo cáo) — tài liệu không hứa hơn.
- `docs/00-survey/*` đang có thay đổi chưa commit (git status ban đầu) — không thuộc feature, không chạm.
