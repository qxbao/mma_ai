---
id: "PLAN-010"
title: "Đồng bộ tài liệu dự án với mã đã gộp (006 · 007 · 008 · 009) — Kế hoạch triển khai (Implementation plan)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-13"
feature: "010-docs-platform-sync"
version: "1.0.0"
---

# Implementation Plan: Đồng bộ tài liệu dự án với mã đã gộp (006 · 007 · 008 · 009)

- [Summary](#summary)
- [Technical Context](#technical-context)
- [Constitution Check](#constitution-check)
- [Kiến trúc & quyết định thiết kế](#kien-truc-quyet-dinh-thiet-ke)
- [Project Structure](#project-structure)
  - [Documentation (this feature)](#documentation-this-feature)
  - [Source Code (repository root) — chỉ phần 010 chạm tới](#source-code-repository-root-chi-phan-010-cham-toi)
- [Lệnh build / test](#lenh-build-test)
- [Truy vết yêu cầu → thiết kế](#truy-vet-yeu-cau-thiet-ke)
- [Rủi ro & việc CHƯA KIỂM](#rui-ro-viec-chua-kiem)
- [Quyết định ở bước tasks](#quyet-dinh-o-buoc-tasks)
- [Complexity Tracking](#complexity-tracking)


**Branch**: `010-docs-platform-sync` (tên thư mục feature; không tạo nhánh git) | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Input**: `specs/010-docs-platform-sync/spec.md` (bản hiện tại, 1.0.0; không còn câu hỏi treo chờ người; Q-0001/Q-0002 đã ghi đúng khuôn `- Q: … → A: … (người, Q-NNNN)` ở Clarifications). Lượt này viết lại plan theo spec hiện tại.

<a id="summary"></a>
## Summary

`master` (b82d690) đã gộp mã đa nền tảng của 006 nhưng README, CHANGELOG và `docs/guides/` còn nói trạng thái cũ. Feature chỉ sửa **tài liệu tiếng Việt** và **một tệp test tài liệu**, không đụng `src/`, `pyproject.toml`, `uv.lock`, `.github/`. Năm việc:

1. **W-1 (docs)** — `docs/guides/platforms.md` (mới, ≤ 120 dòng) + sửa đúng chỗ đã đổi ở `docs/guides/replay-demo.md` (macOS: mã thoát 7 kèm gợi ý `mjpython`, đối chiếu mã `src/mma_ai/visualization/cli.py`); `training.md` và `evaluation.md` giữ nguyên (đối chiếu xong, xem [research.md Q3](research.md#q3-ba-huong-dan-hien-co-co-lech-voi-ma-khong)).
2. **W-2 (docs)** — `README.md`: viết lại nội dung mục "Tình trạng nền tảng" (dạng danh sách có nhãn *đã kiểm*/*chưa kiểm* để test bắt được) và thêm liên kết `platforms.md` ở mục "Tài liệu"; không thêm tiêu đề `##`.
3. **W-3 (docs)** — `CHANGELOG.md` mục `[Unreleased]`: `### Added` + `### Changed` cho 006/007/008/009, mỗi dòng một liên kết spec, một câu giới hạn; không đổi `[0.1.0]`, không khối lệnh.
4. **W-4 (qa)** — `tests/e2e/test_008_docs_entrypoints.py`: đổi assert nền tảng sang mô tả mới và mở rộng các assert cấu trúc cho `platforms.md` **mà không đổi `GUIDES`** (thân test INV-002 của 008 dùng `GUIDES` — xem D-2). Không skip/xfail, số test không giảm (mốc đo: 24 test thu thập ở HEAD).
5. **W-5 (reviewer)** — verdict độc lập: đối chiếu mọi lệnh/đường dẫn/marker với mã, ghi kết quả đối chiếu ba hướng dẫn cũ; AC-3 bằng `ai-sdlc verify --branch ai-sdlc/integration`.

Bằng chứng đã/chưa kiểm lấy từ spec 006 + báo cáo QA T640: **Linux = đã kiểm**; **Windows 11, WSL2, macOS, CUDA, ô CI chạy thật trên GitHub Actions = chưa kiểm** (INV-001). `status:` của spec 006 giữ `draft` (INV-005; xác nhận ở D-7).

<a id="technical-context"></a>
## Technical Context

**Language/Version**: Python ≥ 3.11, < 3.13 (`pyproject.toml`); tài liệu Markdown tiếng Việt

**Primary Dependencies**: `pytest` (+ `pytest-playwright` ở cổng e2e theo profile); không thêm phụ thuộc

**Storage**: N/A — tệp Markdown và một tệp test

**Testing**: `pytest` (e2e `tests/e2e/test_008_docs_entrypoints.py`), `ruff check`, `mypy --strict`; cổng toàn hệ `ai-sdlc verify`

**Target Platform**: tài liệu mô tả Linux (đã kiểm) và nêu Windows/macOS/CUDA/CI thật (chưa kiểm); test e2e viết bằng `sys.executable`/`pathlib` để chạy được mọi OS

**Project Type**: thư viện + CLI (`python-mujoco-cli`; stack đã có ở `.ai/stack-proposal.yml`, không ghi lại)

**Performance Goals**: không có; `platforms.md` ≤ 120 dòng (NFR-DOC-002)

**Constraints**: 0 liên kết hỏng (NFR-DOC-001); tỉ lệ loại ≤ 5% (NFR-GATE-001); `ruff` + `mypy --strict` xanh (NFR-QUAL-001); vùng ghi đúng danh sách ở spec User Story 5 (INV-002)

**Scale/Scope**: 4–5 tệp tài liệu (README, CHANGELOG, `platforms.md`, `replay-demo.md`) + 1 tệp test (≈ 40–80 dòng đổi)

<a id="constitution-check"></a>
## Constitution Check

| Nguyên tắc | Đạt? | Căn cứ |
|---|---|---|
| I. Bằng chứng thắng lời khai | Đạt | "đã/chưa kiểm" chỉ lấy từ spec 006 + QA T640; test e2e chạy lệnh thật (`env_report`, `--help`) thay vì tin tài liệu; AC-3 bằng cổng `ai-sdlc verify`; reviewer khác vai viết |
| II. Test trước, sửa sau | Đạt | W-4 đổi test cùng lúc đổi README (task chỉ đổi test được miễn `tdd_red`); không skip/xfail; số test không giảm (mốc 24) |
| III. Lát cắt nhỏ, một vai một task | Đạt | mỗi tệp một chủ trong `outputs`; docs/qa/reviewer tách vai; xem [Quyết định ở bước tasks](#quyet-dinh-o-buoc-tasks) |
| IV. INV/NFR có mã và ngưỡng | Đạt | INV-001…005, NFR-DOC-001/002, NFR-GATE-001, NFR-QUAL-001 khai ở `spec.md` với `Ngưỡng:`/`Đo bằng:` |
| V. Không đổi cái không được yêu cầu | Đạt | không đổi `src/`, `pyproject.toml`, `uv.lock`, `.github/`, `[0.1.0]`, `status:` của 006 |
| VI. Bí mật qua biến môi trường | Đạt | không có bí mật; tài liệu không chứa khoá/token; remote chỉ nêu khi cần |
| VII. Nhánh bảo vệ | Đạt | không commit/đổi nhánh ở lượt đặc tả; thi công qua nhánh task |
| VIII–IX. Tài liệu sinh từ mã; mỗi tài liệu một chỗ | Đạt | mọi khẳng định có nguồn trong mã/spec ([data-model.md](data-model.md)); tài liệu mới chỉ ở `docs/guides/platforms.md`, không chép chi tiết spec 006 sang `docs/` |

Không vi phạm ⇒ bảng Complexity Tracking trống.

<a id="kien-truc-quyet-dinh-thiet-ke"></a>
## Kiến trúc & quyết định thiết kế

Một bounded context (tài liệu dự án); không có `docs/02-strategic/context-map.md` mới, không `docs/03-tactical/*`, không `rbac.md`, không `contracts/` (không API/wire mới; báo cáo `env_report --json` và báo cáo năng lực là hợp đồng của 006, feature chỉ đọc — xem [data-model.md](data-model.md)). Không ghi `.ai/stack-proposal.yml` (stack không đổi).

| # | Quyết định | Lý do | Căn cứ |
|---|---|---|---|
| D-1 | Mục "Tình trạng nền tảng" của README là danh sách gạch đầu dòng, mỗi dòng `**<Hạng mục>**: <đã kiểm hoặc chưa kiểm> — <lời>`: Linux = đã kiểm; Windows 11 · WSL2 · macOS · CUDA · ô CI chạy thật trên GitHub Actions = chưa kiểm; thêm đoạn tả bốn thành phần đã gộp và liên kết `specs/006-cross-platform-support/` | test phân tích được từng dòng (không chỉ tìm chuỗi), cấm "khẳng định hơn bằng chứng" có kiểm máy (INV-001) | spec FR-001/FR-002; QA T640 |
| D-2 | **Không** thêm `platforms.md` vào hằng `GUIDES`; thêm hằng riêng (ví dụ `PLATFORM_GUIDE`, `ALL_GUIDES`) cho các assert cấu trúc/liên kết/độ dài | thân `test_inv002_document_commits_keep_product_code_untouched` tính `allowed` từ `GUIDES` và so với commit **đã tạo** README/CHANGELOG (không chứa `platforms.md`); thêm vào `GUIDES` làm test này đỏ, mà thân test bị cấm sửa (FR-011) | ĐÃ ĐỌC test 008 dòng 118–138; research Q2 |
| D-3 | Cờ trong `platforms.md` đối chiếu với nguồn thật: `python -m mma_ai.compat.env_report` ↔ chạy thật `--json` (mã thoát ∈ {0,1}, stdout là JSON có `schema_version`) và cờ lạ trả mã 2; `pytest --capability-report`/`--capability-max-ratio` ↔ `python -m pytest --help` | env_report **không có `--help`** (cờ lạ trả mã 2) nên cơ chế `_help()` hiện có không dùng được; không bỏ kiểm tra, không nới (INV-004) | ĐÃ ĐO `env_report --bogus` → mã 2; `pytest --help` có `--capability-report`; research Q2 |
| D-4 | `platforms.md` dùng khối `sh` chỉ cho lệnh có thật: `python -m mma_ai.compat.env_report`, `python -m mma_ai.compat.env_report --json`, `python -m pytest -q --capability-report capability.json`; mỗi dòng ánh xạ được trong `_command_for_line` mở rộng | `_command_for_line` gọi `pytest.fail` với lệnh chưa ánh xạ; mở rộng ánh xạ là thêm kiểm tra, không nới | ĐÃ ĐỌC test 008 dòng 74–93 |
| D-5 | CHANGELOG: nhóm `### Added` (006: gói `mma_ai.compat`, cổng năng lực + sáu dấu, CI ma trận, báo cáo môi trường; 009: `requires_git_history`; 008: bộ tài liệu) và `### Changed` (007: ổn định hai test viewer/tiến trình; 006: các CLI nhận UTF-8/ghi tệp nguyên tử); cuối mục một câu giới hạn; chỉ liên kết `specs/00x-…/`; không khối `sh` | test 008 đòi CHANGELOG không có khối lệnh; yêu cầu gốc đòi Added/Changed + liên kết + giới hạn | spec FR-004/FR-005 |
| D-6 | `replay-demo.md`: thêm vào hàng mã thoát `7` rằng trên macOS khi chạy bằng `python` thường cần `mjpython` (CHƯA KIỂM trên macOS thật); `training.md`/`evaluation.md` không đổi | đầu ra mới có thật ở mã (`visualization/cli.py` đặt mã 7 + gợi ý khi macOS không `--headless`); hai hướng dẫn kia không có cờ/mã thoát/đầu ra nào đổi từ commit tạo chúng (98366d6) | ĐÃ ĐỌC `git diff 98366d6 HEAD`; research Q3 |
| D-7 | Giữ `status: draft` của spec 006; assert test vẫn đòi `^status: draft$` | không quy tắc nào trong `CLAUDE.md`, `docs/MAP.md`, hiến chương bắt đổi; yêu cầu cấm đổi nếu không bắt buộc | ĐÃ ĐỌC; **nêu cho người duyệt**: nếu người duyệt muốn 006 sang `active` khi có bằng chứng Windows/macOS thật thì là feature khác |
| D-8 | `platforms.md` lấy khuôn frontmatter của ba hướng dẫn cũ (`doc_type: guide`, `owner_agent: docs`, `status: active`), có liên kết `../../README.md`, thuật ngữ song ngữ ở lần đầu, nhắc `docs/guides/` không dẫn tới tệp chưa tồn tại | test 008 kiểm ≤ 120 dòng, liên kết `../../README.md`, UTF-8 | ĐÃ ĐỌC test 008 dòng 213–254 |
| D-9 | Không nhắc `scripts/check_env.py`; chỉ nêu `python -m mma_ai.compat.env_report` | QA T640 ghi vỏ đó "chưa có chủ"; `scripts/` chỉ có `train.py` | ĐÃ ĐỌC |
| D-10 | Không chép số liệu một lượt chạy (1/1552, 0,1%, 24 test…) vào tài liệu như hằng số; ví dụ báo cáo dùng "X/Y" | INV-001, Edge Case số liệu | spec |

<a id="project-structure"></a>
## Project Structure

<a id="documentation-this-feature"></a>
### Documentation (this feature)

```text
specs/010-docs-platform-sync/
├── spec.md              # đặc tả (AC-1…AC-3, FR-001…FR-014, NFR-*, INV-001…005)
├── plan.md              # tệp này
├── research.md          # Phase 0 — nguồn bằng chứng nền tảng, tác động lên test 008, đối chiếu ba hướng dẫn
├── data-model.md        # Phase 1 — mô hình tài liệu: khẳng định → nguồn → kiểm bằng gì
├── quickstart.md        # Phase 1 — kịch bản kiểm chứng gắn mã AC/INV/NFR
├── request.link         # trỏ tới .ai/chat/request-docs-sync.md
├── checklists/requirements.md
└── tasks.md             # Phase 2 — KHÔNG do plan tạo (máy chạy /speckit-tasks sau)
```

<a id="source-code-repository-root-chi-phan-010-cham-toi"></a>
### Source Code (repository root) — chỉ phần 010 chạm tới

```text
README.md                          # W-2 (docs): mục "Tình trạng nền tảng" + liên kết ở "Tài liệu"
CHANGELOG.md                       # W-3 (docs): chỉ mục [Unreleased]
docs/guides/
├── platforms.md                   # W-1 (docs): MỚI
├── replay-demo.md                 # W-1 (docs): chỉ hàng mã thoát 7 (+ updated)
├── training.md                    # KHÔNG đổi
└── evaluation.md                  # KHÔNG đổi
tests/e2e/test_008_docs_entrypoints.py   # W-4 (qa)
evidence/reviews/                  # W-5 (reviewer): verdict
src/ · pyproject.toml · uv.lock · .github/ · tests/unit/capability_gate.py   # KHÔNG sửa
```

Không có thư mục khung mới, không manifest mới, không FE/BE tách phía (đồ án một gói Python quản lý bằng `uv`). `docs/MAP.md` và `docs/05-tracing/` do máy sinh sau khi có `tasks.md`.

<a id="lenh-build-test"></a>
## Lệnh build / test

Theo `.ai/profile.yml` (chạy trong worktree của task):

| Mục đích | Lệnh |
|---|---|
| Test tài liệu 008 + báo cáo năng lực | `uv run --isolated --with pytest --with pytest-playwright pytest -q -p no:cacheprovider tests/e2e/test_008_docs_entrypoints.py --capability-report=<tệp>` |
| Cổng e2e (khi đổi `tests/e2e/**`) | `uv run --isolated --with pytest --with pytest-playwright pytest -q -p no:cacheprovider tests/e2e` |
| Cổng tests | `uv run --isolated --with pytest --with pytest-xdist pytest -q -p no:cacheprovider -n auto --ignore=tests/e2e` |
| lint | `uv run --isolated --with ruff ruff check .` |
| typecheck | `uv run --isolated --with mypy mypy --strict .` |
| Đếm test (so mốc 24 của tệp 008) | `uv run --isolated --with pytest pytest -q -p no:cacheprovider tests/e2e/test_008_docs_entrypoints.py --collect-only` |
| Lệnh được tài liệu hoá (kiểm tay trên Linux) | `uv run python -m mma_ai.compat.env_report` · `… --json` |
| Toàn hệ (AC-3) | `ai-sdlc verify --branch ai-sdlc/integration` |

<a id="truy-vet-yeu-cau-thiet-ke"></a>
## Truy vết yêu cầu → thiết kế

| Mã | Thiết kế | Test / cổng đề xuất | Mức |
|---|---|---|---|
| AC-1 | D-1, D-3, D-4, D-5, D-6, D-8 | `test_008_docs_entrypoints.py`: `test_ac1_ac2_ac3_ac4_ac5_document_structure`, `test_ac2_ac3_ac4_ac5_inv004_relative_links` (+`platforms.md`), `test_ac2_ac3_ac5_inv001_documented_flags` (+`platforms.md`), `test_ac2_inv004_readme_quickstart` (giữ nguyên) | entrypoint (e2e) |
| AC-2 | D-1, D-7, D-9, D-10 | `test_ac2_inv003_platform_claims_match_draft_support` (đổi sang danh sách đã/chưa kiểm) | entrypoint (e2e) |
| AC-3 | D-2 | cổng `ai-sdlc verify --branch ai-sdlc/integration` (5 cổng) | cổng |
| FR-001, FR-002, FR-003 | D-1 | test AC-2 ở trên + `test_ac1_…document_structure` (10 tiêu đề `##`) + `test_ac2_inv004_readme_quickstart` | e2e |
| FR-004, FR-005 | D-5 | test CHANGELOG mới: `[Unreleased]` có `### Added`/`### Changed`, đủ 4 liên kết spec, đủ 6 tên dấu; `git diff` mục `[0.1.0]` rỗng (reviewer) | e2e + cổng |
| FR-006, FR-007 | D-3, D-4, D-8 | `test_ac2_…documented_flags[platforms.md]`; test mới: `platforms.md` nêu đủ 6 dấu và README liên kết tới nó | e2e |
| FR-008 | D-6 | báo cáo review ghi kết quả đối chiếu ba hướng dẫn (research Q3); `test_ac5_inv001_guide_options` (giữ nguyên) | e2e + cổng |
| FR-009 | D-3, D-9 | test e2e chạy thật `env_report`; test: 6 dấu trong tài liệu ⊆ dấu khai ở `capability_gate.py`; không có chuỗi `check_env.py` | e2e |
| FR-010 | D-2, D-3 | diff `tests/e2e/test_008_docs_entrypoints.py` (reviewer) | cổng |
| FR-011 | D-2 | quét diff `skip`/`skipif`/`xfail`/`importorskip`; `--collect-only` số test ≥ 24; `git diff` thân test INV-002 rỗng | cổng |
| FR-012 | D-5…D-6 | verdict reviewer (vai khác docs) | cổng |
| FR-013 | D-7 | `git diff --name-only`; `grep '^status: draft$' specs/006-…/spec.md` | cổng |
| FR-014 | — | `ai-sdlc verify` | cổng |
| NFR-DOC-001 | D-8 | `test_ac2_ac3_ac4_ac5_inv004_relative_links` mở rộng cho `platforms.md` | e2e |
| NFR-DOC-002 | D-8 | `test_ac1_…document_structure` (≤ 120 dòng, gồm `platforms.md`) | e2e |
| NFR-GATE-001 | — | `--capability-report` ở cổng e2e: `ratio ≤ 0.05` | cổng |
| NFR-QUAL-001 | — | cổng `lint`, `typecheck` | cổng |
| INV-001 | D-1, D-10 | test AC-2 (mỗi hạng mục chưa kiểm không chứa "đã kiểm"); reviewer đọc | e2e + reviewer |
| INV-002 | D-2 | `git diff --name-only` đối chiếu vùng ghi | cổng |
| INV-003 | D-2 | quét diff; `--collect-only`; thân test INV-002 nguyên | cổng |
| INV-004 | D-3, D-4 | test cờ/lệnh/đường dẫn ở trên | e2e |
| INV-005 | D-7 | test AC-2 vẫn đòi `status: draft` | e2e |

<a id="rui-ro-viec-chua-kiem"></a>
## Rủi ro & việc CHƯA KIỂM

| # | Rủi ro / việc | Mức | Xử lý |
|---|---|---|---|
| R-1 | Đổi README trước khi qa đổi test ⇒ test 008 cũ đỏ giữa hai commit | thấp | cổng e2e chỉ chạy khi diff chạm `tests/e2e/**` (profile); task qa phụ thuộc các task docs; mọi commit trên nhánh tích hợp xanh ở thời điểm gộp |
| R-2 | Thêm `platforms.md` vào `GUIDES` làm test INV-002 của 008 đỏ (thân bị cấm sửa) | trung bình nếu bỏ qua | D-2; reviewer đối chiếu diff test |
| R-3 | `python -m mma_ai.compat.env_report` thoát mã 1 ở môi trường cổng thiếu gói bắt buộc ⇒ test sai nếu đòi mã 0 | thấp | test chỉ đòi mã ∈ {0,1} và JSON hợp lệ; tài liệu mô tả cả hai mã (ĐÃ ĐỌC `main()`) |
| R-4 | `ci.yml` còn ghi chú "kho chưa có kho từ xa" lỗi thời, mâu thuẫn tài liệu | thấp | ngoài phạm vi (Out of Scope); khuyến nghị cho vai platform ở lượt khác; tài liệu không lặp câu đó |
| R-5 | Người đọc hiểu "đã kiểm Linux" là mọi bản phân phối Linux/WSL2 | thấp | WSL2 liệt kê riêng là *chưa kiểm*; "Linux" ghi rõ là môi trường phát triển/QA đã chạy |
| R-6 | Bản archive không có `.git`: test INV-002 của 008 bị loại, `platforms.md` phải nói đúng điều này | thấp | `platforms.md` mục lịch sử git; tỉ lệ loại giữ ≤ 5% (mốc: 0/24 ở môi trường có git; ở archive 1/24 ≈ 4,2% — ĐÃ TÍNH, mẫu số phiên `e2e` đầy đủ lớn hơn) |
| R-7 | 007 được mô tả sai trong CHANGELOG (spec 007 vẫn `draft`, chưa đọc diff mã 007) | thấp | docs đối chiếu `specs/007-…/spec.md` và commit liên quan trước khi viết; reviewer kiểm; mô tả chỉ ở mức đã có chứng cứ |

Việc CHƯA KIỂM của lượt đặc tả: không chạy `ai-sdlc verify`; không chạy e2e cổng đầy đủ (chỉ chạy riêng `test_008_docs_entrypoints.py` ở HEAD: 24 passed, 0/24 bị loại — ĐÃ ĐO); Windows 11/macOS/CUDA/CI thật vẫn CHƯA KIỂM theo bằng chứng 006.

<a id="quyet-dinh-o-buoc-tasks"></a>
## Quyết định ở bước tasks

Gợi ý cho `/speckit-tasks` (do máy chạy sau; plan không tạo `tasks.md`). Mỗi tệp một chủ trong `outputs`:

| Task gợi ý | Vai | `outputs` (vùng ghi) | Phụ thuộc | Mã phủ |
|---|---|---|---|---|
| A. Hướng dẫn đa nền tảng + sửa hàng mã thoát 7 của hướng dẫn phát lại | docs | `docs/guides/platforms.md` · `docs/guides/replay-demo.md` | — | AC-1, AC-2, FR-006, FR-008, FR-009, NFR-DOC-002, INV-001, INV-004 |
| B. README: tình trạng nền tảng + liên kết hướng dẫn | docs | `README.md` | A (liên kết tới `platforms.md`) | AC-1, AC-2, FR-001…FR-003, FR-007, INV-001, INV-005 |
| C. CHANGELOG `[Unreleased]` | docs | `CHANGELOG.md` | — | AC-1, AC-2, FR-004, FR-005, INV-001 |
| D. Cập nhật assert test 008 theo mô tả mới | qa | `tests/e2e/test_008_docs_entrypoints.py` | A, B, C | AC-1, AC-2, FR-010, FR-011, NFR-DOC-001, NFR-DOC-002, INV-003, INV-004, INV-005 |
| E. Review độc lập + bằng chứng cổng | reviewer | `evidence/reviews/**` · `.ai/runs/*/reports/reviewer-docs-sync-check.md` | A, B, C, D | AC-3, FR-008, FR-012…FR-014, NFR-GATE-001, NFR-QUAL-001, INV-002 |

- `tdd_red`: D chỉ đổi test nên được miễn; A, B, C chỉ đổi tài liệu (không có test đỏ trước theo nghĩa mã; test của D là cổng chứng minh chúng).
- Không có cờ UI/hạ tầng (`has_ui=false`, `has_infra=false`): không màn mẫu, không `ui_task_walk`.
- Không cần vai `challenger` (không có bất biến kiểu bảo mật; test assert thẳng trên sản phẩm).
- Task sửa `status:` của 006 KHÔNG có trong danh sách (D-7).
- Mỗi task docs ≤ 600 LoC (thực tế ≲ 120 dòng mỗi tệp).

<a id="complexity-tracking"></a>
## Complexity Tracking

Không có vi phạm hiến chương cần biện minh.
