---
id: "TASKS-010"
title: "Đồng bộ tài liệu dự án với mã đã gộp (006 · 007 · 008 · 009) — Nhiệm vụ (Tasks)"
doc_type: tasks
owner_agent: spec
status: draft
updated: "2026-10-13"
feature: "010-docs-platform-sync"
version: "1.0.0"
---

# Nhiệm vụ: Đồng bộ tài liệu dự án với mã đã gộp (006 · 007 · 008 · 009)

- [Đầu vào](#dau-vao)
- [Quy ước task](#quy-uoc-task)
  - [Phụ thuộc chéo feature](#phu-thuoc-cheo-feature)
- [Nhóm việc theo user story](#nhom-viec-theo-user-story)
- [Đối chiếu độc lập](#doi-chieu-doc-lap)
  - [Quyết định về vai `challenger`](#quyet-dinh-ve-vai-challenger)
- [Bảng task](#bang-task)
- [Dependencies và wave](#dependencies-va-wave)
- [Điều kiện hoàn thành](#dieu-kien-hoan-thanh)

> Đích: `specs/010-docs-platform-sync/tasks.md`. Sinh từ `spec.md` + `plan.md` + `research.md` + `data-model.md` + `quickstart.md` HIỆN TẠI (viết lại hoàn toàn ở lượt 2026-10-13). Feature chỉ sửa/thêm tài liệu Markdown và một tệp test tài liệu: không có màn hình ⇒ không có mã `UI-*`; không có HTTP/`contracts/` ⇒ không có mã `API-*`; không có kế hoạch hạ tầng `infra/deploy/010-docs-platform-sync*.md` ⇒ không có task `platform`.

<a id="dau-vao"></a>
## Đầu vào

- `spec.md`: AC-1…AC-3, FR-001…FR-014, NFR-DOC-001, NFR-DOC-002, NFR-GATE-001, NFR-QUAL-001, INV-001…INV-005, SC-001…SC-008.
- `plan.md` (quyết định D-1…D-10, rủi ro R-1…R-7, gợi ý năm task A…E), `research.md` (nguồn bằng chứng nền tảng, tác động lên test 008, đối chiếu ba hướng dẫn cũ), `data-model.md` (khẳng định → nguồn → kiểm bằng gì), `quickstart.md`.
- Bằng chứng đã/chưa kiểm: `specs/006-cross-platform-support/` và báo cáo QA T640 (`.ai/runs/run-20261012-0ecb0c/reports/qa-006-crossplatform.md`): Linux = đã kiểm; Windows 11, WSL2, macOS, CUDA, ô CI chạy thật trên GitHub Actions = chưa kiểm.
- Khảo sát nguồn: `docs/00-survey/mma-ai-cross-platform.md`, `docs/00-survey/mma-ai-project-docs.md`.

<a id="quy-uoc-task"></a>
## Quy ước task

- **Dải mã `T1001`…`T1005`**: id task duy nhất toàn dự án (010 dùng dải `T10xx`, không va với `T2xx`…`T9xx`).
- **Năm task**: ba task `docs` (`T1001` `platforms.md` + `replay-demo.md`; `T1002` `README.md`; `T1003` `CHANGELOG.md`), một task `qa` (`T1004` cập nhật `tests/e2e/test_008_docs_entrypoints.py`), một task `reviewer` (`T1005`). Mỗi tệp đúng một task chủ; mọi `outputs` nằm trọn trong vùng ghi của vai.
- **Vùng ghi của feature (INV-002, FR-013, SC-007)**: chỉ `README.md`, `CHANGELOG.md`, `docs/guides/platforms.md`, `docs/guides/replay-demo.md`, `tests/e2e/test_008_docs_entrypoints.py` cộng verdict/báo cáo của reviewer và tệp của chính feature (`specs/010-docs-platform-sync/`, `docs/05-tracing/`, `docs/MAP.md` do máy sinh). `src/`, `pyproject.toml`, `uv.lock`, `.github/`, `tests/unit/capability_gate.py`, `docs/guides/training.md`, `docs/guides/evaluation.md`, mục `[0.1.0]` của CHANGELOG và `status:` của spec 006 KHÔNG đổi.
- **Không khẳng định hơn bằng chứng (INV-001)**: mọi câu về nền tảng lấy từ spec 006 + QA T640; Linux là nền tảng duy nhất ghi "đã kiểm"; Windows 11, WSL2, macOS, CUDA, ô CI chạy thật ghi thẳng "chưa kiểm"; không chép số liệu một lượt chạy (1/1552, 0,1%, 24 test…) thành hằng số; không nhắc `scripts/check_env.py` (không tồn tại, FR-009).
- **Mọi lệnh/đường dẫn/marker phải có thật (INV-004, FR-009)**: vai `docs` đối chiếu mã trước khi viết — `src/mma_ai/compat/env_report.py` (`--json`; mã thoát 0/1; cờ lạ ⇒ mã 2), `tests/unit/capability_gate.py` (sáu dấu `requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `requires_xdist`, `requires_git_history`; `--capability-report`, `--capability-max-ratio`), `.github/workflows/ci.yml`, `src/mma_ai/visualization/cli.py` (mã thoát 7 trên macOS).
- **Ràng buộc test 008 mà tài liệu phải tuân (D-2, D-8)**: `platforms.md` ≤ 120 dòng, có frontmatter như ba hướng dẫn cũ (`doc_type: guide`, `owner_agent: docs`) và liên kết `../../README.md`; README giữ đúng 10 tiêu đề `##`, bốn lệnh nhanh và huy hiệu; CHANGELOG không có khối `sh`/`bash`.
- **Tự chốt**: `platforms.md` KHÔNG được thêm vào hằng `GUIDES` của test 008 mà đi vào hằng riêng (ví dụ `PLATFORM_GUIDE`/`ALL_GUIDES`) — lý do: thân `test_inv002_document_commits_keep_product_code_untouched` tính `allowed` từ `GUIDES` và bị cấm sửa (FR-011); thêm vào `GUIDES` làm test đó đỏ.
- **Tự chốt**: `T1004` đứng SAU ba task docs (đảo thứ tự so với gợi ý chung "task test đứng trước") — lý do: assert mới của test 008 khẳng định nội dung README/CHANGELOG/`platforms.md` mới nên chỉ xanh khi ba tệp đó đã có; ngược lại, ba task docs không chạm `tests/e2e/**` nên cổng `e2e` của chúng không chạy, còn cổng `e2e` của `T1004` xanh ngay khi vào. Đặt test trước sẽ làm chính cổng của `T1004` đỏ (plan R-1).
- **Tự chốt**: cờ `--json` và `--capability-report` không thuộc `--help` của bốn CLI trong `GUIDES`, và `env_report` không có `--help` — lý do: `T1004` đối chiếu chúng với nguồn thật (chạy `env_report --json`, cờ lạ ⇒ mã 2; `pytest --help` có `--capability-report`) thay vì bỏ kiểm tra (INV-004, D-3).
- **Mã rủi ro có tiền tố**: docstring/tên test của `T1004` ghi nguyên chuỗi `010/AC-1`, `010/AC-2`, `010/FR-…`, `010/INV-001`, `010/INV-003`, `010/INV-004`, `010/INV-005`, `010/NFR-DOC-001`, `010/NFR-DOC-002` để cổng `risk_coverage` đo được và không lẫn với mã cùng tên của 006/008/009 (bài học `T904` của 009). Mã chỉ cổng máy/reviewer đo được (`AC-3`, `INV-002`, `FR-011`…`FR-014`, `NFR-GATE-001`, `NFR-QUAL-001`) do `T1005` ghi nhận bằng chứng.
- **Ngôn ngữ**: tài liệu tiếng Việt, thuật ngữ song ngữ ở lần đầu mỗi tài liệu (ví dụ "cổng năng lực (capability gate)", "ma trận CI (CI matrix)", "bản archive (archive)").

<a id="phu-thuoc-cheo-feature"></a>
### Phụ thuộc chéo feature

Các task của 010 sửa tệp do task của feature khác sinh ra hoặc tiêu thụ kết quả của chúng, nên cột `depends_on` khai thẳng id của feature khác:

| Task 010 | Phụ thuộc task feature khác | Vì sao |
|---|---|---|
| `T1001` | `T609` (006 `env_report.py`), `T606` (006 cổng năng lực), `T628` (006 `visualization/cli.py` mã thoát 7), `T802` (008 tạo `replay-demo.md`), `T902` (009 dấu `requires_git_history`), `T640` (006 báo cáo QA đã/chưa kiểm) | mô tả lệnh/marker/mã thoát do các task đó sinh; sửa tệp `replay-demo.md` do `T802` tạo; giới hạn đã/chưa kiểm lấy từ `T640` |
| `T1002` | `T801` (008 tạo `README.md`), `T635` (006 `ci.yml`), `T640` | sửa tệp do `T801` tạo; mô tả ma trận CI do `T635` sinh; bằng chứng đã/chưa kiểm |
| `T1003` | `T802` (008 tạo `CHANGELOG.md`), `T641` (006), `T711` (007), `T804` (008), `T905` (009) | sửa tệp do `T802` tạo; nội dung `[Unreleased]` tổng hợp kết quả đã vào nhánh tích hợp của bốn feature (verdict cuối của 006, 007, 009; test 008 của `T804`) |
| `T1004` | `T804` (008 tạo test), `T902` (009 thêm dấu `requires_git_history` vào cùng tệp) | sửa đúng tệp do hai task đó sinh/sửa; phải giữ nguyên dấu của `T902` |

Trong 010: `T1002` sau `T1001` (README liên kết `platforms.md`); `T1004` sau `T1001`, `T1002`, `T1003`; `T1005` sau cả bốn.

**Thay đổi làm SAI test đã có**: README mới bỏ cụm "đang được triển khai"/"chưa xác nhận khả năng chạy" mà `test_ac2_inv003_platform_claims_match_draft_support` (do `T804` sinh) đang khẳng định, và `platforms.md` làm sai các assert về tập tệp `docs/guides` (đúng ba tệp). `T1004` (vai `qa` — vai sở hữu test) cập nhật đúng các assert đó theo mô tả mới; `T1004` `depends_on` ba task đổi hành vi vì lý do đã nêu ở mục Quy ước ("Tự chốt").

<a id="nhom-viec-theo-user-story"></a>
## Nhóm việc theo user story

- **US1 — README nói đúng tình trạng nền tảng (P1)**: `T1002` (FR-001…FR-003, FR-007, INV-001, INV-005), `T1004` (assert AC-2).
- **US2 — CHANGELOG `[Unreleased]` (P1)**: `T1003` (FR-004, FR-005, INV-001).
- **US3 — Hướng dẫn `platforms.md` (P1)**: `T1001` (FR-006, FR-008, FR-009, NFR-DOC-002, INV-004).
- **US4 — Cổng toàn hệ xanh, test 008 khớp mô tả mới (P1)**: `T1004` (FR-010, FR-011, NFR-DOC-001, NFR-DOC-002, INV-003), `T1005` (FR-014, NFR-GATE-001, NFR-QUAL-001).
- **US5 — Reviewer độc lập, vùng ghi giữ nguyên (P2)**: `T1005` (FR-008, FR-012, FR-013, INV-002, INV-005).

<a id="doi-chieu-doc-lap"></a>
## Đối chiếu độc lập

- [ ] T1001 [US3] Docs: viết `docs/guides/platforms.md` và sửa hàng mã thoát 7 của `docs/guides/replay-demo.md` — docs/guides/platforms.md; docs/guides/replay-demo.md
- [ ] T1002 [US1] Docs: viết lại mục "Tình trạng nền tảng" và thêm liên kết `platforms.md` ở mục "Tài liệu" của README — README.md
- [ ] T1003 [US2] Docs: điền `[Unreleased]` của CHANGELOG (Added/Changed cho 006, 007, 008, 009 + câu giới hạn) — CHANGELOG.md
- [ ] T1004 [US1] [US3] [US4] QA: cập nhật assert của test 008 theo mô tả mới, thêm `platforms.md` vào các assert cấu trúc — tests/e2e/test_008_docs_entrypoints.py
- [ ] T1005 [US4] [US5] Reviewer: đối chiếu độc lập mọi lệnh/đường dẫn/marker, quét diff, ghi verdict — evidence/reviews/T1005.verdict; .ai/runs/*/reports/reviewer-docs-sync-check.md

<a id="quyet-dinh-ve-vai-challenger"></a>
### Quyết định về vai `challenger`

**KHÔNG DÙNG** vai `challenger` (khớp `plan.md` mục "Quyết định ở bước tasks"). Năm bất biến `INV-001…005` của spec là bất biến về **nội dung tài liệu và vùng ghi diff** (không khẳng định hơn bằng chứng, không đổi `src/`/`pyproject.toml`/`uv.lock`/`.github/`/`[0.1.0]`, không thêm skip/xfail, mọi lệnh/marker có thật, `status: draft` của 006 giữ nguyên), không phải bất biến của một hàm nhận đầu vào để dựng vector/fuzz đánh sập. Chúng được kiểm tất định bằng assert của `T1004` trên tài liệu thật, bằng lệnh thật (`env_report`, `pytest --help`) và bằng quét `git diff` của `T1005`. Thêm challenger sẽ buộc nhất trí hai vai độc lập mà không thêm khả năng phát hiện; reviewer độc lập khác vai viết (FR-012) đã đủ.

<a id="bang-task"></a>
## Bảng task

| id | mô tả | outputs | depends_on | role | độ khó |
|---|---|---|---|---|---|
| T1001 | **Hướng dẫn đa nền tảng + sửa hàng mã thoát 7** (FR-006, FR-008, FR-009; NFR-DOC-002; INV-001, INV-004; AC-1, AC-2). (1) Viết `docs/guides/platforms.md` — tiếng Việt, ≤ 120 dòng, frontmatter như ba hướng dẫn cũ (`id`, `title`, `doc_type: guide`, `owner_agent: docs`, `status: active`, `updated`), có liên kết `../../README.md`, thuật ngữ song ngữ ở lần đầu. Khối `sh` CHỈ chứa ba lệnh có thật: `python -m mma_ai.compat.env_report`, `python -m mma_ai.compat.env_report --json`, `python -m pytest -q --capability-report capability.json`. Nội dung: cách chạy báo cáo môi trường và ý nghĩa mã thoát (0 đạt; 1 có mục `fail`; 2 cờ lạ) cùng hai dòng kết luận "Môi trường đạt yêu cầu." / "Môi trường chưa đạt yêu cầu."; bảng sáu dấu năng lực `requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `requires_xdist`, `requires_git_history` với ý nghĩa khớp mô tả khai trong `tests/unit/capability_gate.py` (đọc mã, không chép trí nhớ; chỉ nhắc `posix_only`/`linux_only`/`macos_only` nếu có thật); cách đọc dòng "Kiểm thử bị loại theo năng lực: X/Y (tỉ lệ; giới hạn 5.0%)." kèm danh sách `nodeid [dấu]: lý do`, ngưỡng loại mặc định 5% (vượt thì phiên đỏ), `--capability-report <tệp>` ghi JSON, ví dụ dùng "X/Y" không số liệu một lượt chạy; vì sao test INV-002 của 008 bị loại (có báo cáo, không skip/xfail, không xanh giả) trên bản archive không có `.git` với lý do `Máy không có lịch sử git`, và INV-002 của 008 chỉ chứng minh ở môi trường có git; phần giới hạn: Linux = đã kiểm; Windows 11, WSL2, macOS (kể cả viewer bằng `mjpython`), CUDA, ô CI chạy thật = chưa kiểm, nêu là mục tiêu của 006 không phải kết quả đã kiểm. Không nhắc `scripts/check_env.py`, không lặp ghi chú lỗi thời "kho chưa có kho từ xa" của `ci.yml`. (2) `docs/guides/replay-demo.md`: chỉ sửa hàng mã thoát `7` — trên macOS khi chạy bằng `python` thường và không `--headless` thì thoát mã 7 kèm gợi ý dùng `mjpython` (đối chiếu `src/mma_ai/visualization/cli.py`; ghi "chưa kiểm trên macOS thật") — và dòng `updated`. (3) Ghi kết quả đối chiếu: `training.md` và `evaluation.md` KHÔNG đổi (lệnh/cờ/mã thoát không đổi từ commit tạo chúng); nêu vào báo cáo của `T1005`. Kiểm chứng: chạy thật `uv run python -m mma_ai.compat.env_report` và `… --json` trên Linux, đối chiếu mô tả với đầu ra. | docs/guides/platforms.md; docs/guides/replay-demo.md | T609; T606; T628; T802; T902; T640 | docs | vừa |
| T1002 | **README: tình trạng nền tảng + liên kết hướng dẫn** (FR-001, FR-002, FR-003, FR-007, FR-009; INV-001, INV-005; AC-1, AC-2). Chỉ sửa nội dung mục "Tình trạng nền tảng" và mục "Tài liệu"; KHÔNG thêm/đổi tiêu đề `##` (giữ đúng 10 tiêu đề và thứ tự), bốn lệnh nhanh, huy hiệu, các mục khác. Mục "Tình trạng nền tảng" viết dạng đoạn mô tả + danh sách gạch đầu dòng mỗi dòng `**<Hạng mục>**: <đã kiểm hoặc chưa kiểm> — <lời>` (D-1): đoạn mô tả đúng bốn thành phần đã gộp của 006 — gói `mma_ai.compat` (dò nền tảng/RAM/màn hình, thay tệp nguyên tử), báo cáo môi trường `python -m mma_ai.compat.env_report`, cổng năng lực loại test theo máy, ma trận CI 3 hệ điều hành × Python 3.11/3.12 trong `.github/workflows/ci.yml` (mọi tên/đường dẫn có thật); danh sách: Linux = **đã kiểm**; Windows 11, WSL2, macOS, CUDA, ô CI chạy thật trên GitHub Actions = **chưa kiểm**; không câu nào khẳng định chạy được/hỗ trợ đầy đủ trên nền tảng chưa kiểm; mục tiêu của 006 (Windows gốc chính, CUDA tuỳ chọn, macOS) chỉ ghi là "mục tiêu, chưa kiểm"; giữ liên kết `specs/006-cross-platform-support/`; không chép số liệu một lượt chạy; không nhắc `scripts/check_env.py`. Mục "Tài liệu": thêm liên kết `docs/guides/platforms.md` cạnh ba hướng dẫn cũ (đích có thật sau `T1001`). Kiểm chứng: mọi liên kết tương đối trỏ tới tệp tồn tại; `grep -c '^## '` vẫn là 10. | README.md | T1001; T801; T635; T640 | docs | vừa |
| T1003 | **CHANGELOG `[Unreleased]`** (FR-004, FR-005, FR-009; INV-001; AC-1, AC-2). Chỉ sửa mục `## [Unreleased]`; mục `## [0.1.0] - 2026-10-12` giữ nguyên từng ký tự; KHÔNG khối `sh`/`bash` (lệnh, đường dẫn, tên marker viết trong văn xuôi hoặc mã nội dòng). Nhóm `### Added`: 006 — gói `mma_ai.compat`, cổng năng lực với sáu dấu `requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `requires_xdist`, `requires_git_history` (mỗi tên có thật ở `tests/unit/capability_gate.py`), báo cáo môi trường `python -m mma_ai.compat.env_report`, ma trận CI 3 HĐH × Python 3.11/3.12; 009 — năng lực `requires_git_history` (test lịch sử git bị loại có báo cáo trên bản archive không `.git`); 008 — bộ tài liệu dự án (README, CONTRIBUTING, CHANGELOG, `docs/guides/`); 010 — hướng dẫn `docs/guides/platforms.md`. Nhóm `### Changed`: 007 — ổn định hai test viewer/tiến trình (đối chiếu `specs/007-stabilize-viewer-tests/spec.md` và commit liên quan trước khi viết, chỉ mô tả mức đã có chứng cứ — R-7); 006 — các CLI nhận UTF-8 và ghi tệp nguyên tử (đối chiếu mã/spec 006); 010 — README mô tả đúng tình trạng nền tảng. Mỗi dòng liên kết tương đối tới đúng một `specs/00x-…/` (`specs/006-cross-platform-support/`, `specs/007-stabilize-viewer-tests/`, `specs/008-project-docs/`, `specs/009-git-history-capability/`, `specs/010-docs-platform-sync/`). Cuối mục một câu giới hạn: chưa kiểm Windows, macOS và CI chạy thật; mọi kết quả đã kiểm chỉ trên Linux. | CHANGELOG.md | T802; T641; T711; T804; T905 | docs | dễ |
| T1004 | **Cập nhật assert test 008 theo mô tả mới** (FR-010, FR-011; NFR-DOC-001, NFR-DOC-002; INV-003, INV-004, INV-005; AC-1, AC-2, AC-3). Chỉ sửa `tests/e2e/test_008_docs_entrypoints.py`, KHÔNG đổi `GUIDES` (D-2). (a) `test_ac2_inv003_platform_claims_match_draft_support`: bỏ hai cụm "đang được triển khai"/"chưa xác nhận khả năng chạy"; đòi mục "Tình trạng nền tảng" có `specs/006-cross-platform-support/`, phân tích từng dòng danh sách: dòng Linux chứa "đã kiểm"; dòng Windows, macOS, CUDA và ô CI thật chứa "chưa kiểm" và KHÔNG chứa "đã kiểm"; cấm cụm khẳng định hơn bằng chứng (ví dụ "hỗ trợ đầy đủ"); vẫn đòi `^status: draft$` của spec 006 (INV-005). (b) Thêm hằng riêng (`PLATFORM_GUIDE`/`ALL_GUIDES`) và mở rộng các assert cấu trúc để BAO GỒM `platforms.md`, không bỏ kiểm tra: tập tệp `docs/guides` = ba tệp cũ + `platforms.md`; ≤ 120 dòng; liên kết `../../README.md`; UTF-8; liên kết tương đối không hỏng cho `README.md`, `CHANGELOG.md`, `platforms.md` và ba hướng dẫn cũ (NFR-DOC-001); README có liên kết tới `platforms.md`. (c) Đối chiếu cờ cho `platforms.md` với nguồn thật (D-3): chạy thật `python -m mma_ai.compat.env_report --json` (mã thoát ∈ {0,1}, stdout là JSON có `schema_version`), cờ lạ trả mã 2; `--capability-report`/`--capability-max-ratio` có trong `python -m pytest --help`; mọi lệnh trong khối `sh` của `platforms.md` ánh xạ được trong `_command_for_line` (mở rộng ánh xạ, không nới). (d) Test mới: `[Unreleased]` của CHANGELOG có `### Added` và `### Changed`, đủ bốn liên kết `specs/006…009`, đủ sáu tên dấu năng lực và mỗi tên có thật trong `tests/unit/capability_gate.py`, có câu "chưa kiểm" cho Windows/macOS/CI, không khối lệnh; `platforms.md` nêu đủ sáu dấu và không chứa `check_env.py`. (e) Ràng buộc (kế thừa INV-006 của 006 — không che lỗi bằng skip/xfail — qua INV-003 của spec này): không thêm `pytest.skip`/`skipif`/`xfail`/`importorskip`; số test của tệp KHÔNG giảm so với bản trước (đo `--collect-only`); thân `test_inv002_document_commits_keep_product_code_untouched` và dấu `@pytest.mark.requires_git_history(reason="Máy không có lịch sử git")` của `T902` giữ nguyên; các assert khác chỉ đổi đúng chỗ vì `platforms.md`. Docstring tiếng Việt ghi nguyên chuỗi `010/AC-1`, `010/AC-2`, `010/FR-010`, `010/INV-001`, `010/INV-003`, `010/INV-004`, `010/INV-005`, `010/NFR-DOC-001`, `010/NFR-DOC-002`. Kiểm chứng: `uv run --isolated --with pytest --with pytest-playwright pytest -q -p no:cacheprovider tests/e2e/test_008_docs_entrypoints.py --capability-report=<tệp>`, `ruff check`, `mypy --strict`. | tests/e2e/test_008_docs_entrypoints.py | T1001; T1002; T1003; T804; T902 | qa | vừa |
| T1005 | **Reviewer độc lập đối chiếu và chấm cổng** (FR-008, FR-012, FR-013, FR-014; NFR-GATE-001, NFR-QUAL-001; INV-001, INV-002, INV-005; AC-1, AC-2, AC-3). KHÔNG sửa tệp tài liệu hay test; chỉ ghi verdict và báo cáo. (a) Với từng lệnh, đường dẫn, tên dấu năng lực trong `README.md`, `CHANGELOG.md`, `docs/guides/platforms.md`: đối chiếu với mã (`env_report.py`, `capability_gate.py`, `ci.yml`, `visualization/cli.py`) và chạy thật `uv run python -m mma_ai.compat.env_report` và `… --json` trên Linux; ghi bảng "tài liệu nói gì ↔ mã nói gì ↔ khớp/lệch". (b) Đối chiếu từng câu nền tảng với `specs/006-cross-platform-support/` và QA T640: đúng một nền tảng (Linux) "đã kiểm"; bốn hạng mục (Windows 11, macOS, CUDA, ô CI chạy thật) "chưa kiểm"; 0 câu khẳng định hơn bằng chứng (INV-001); không số liệu một lượt chạy chép thành hằng số; không `scripts/check_env.py`. (c) Ghi kết quả đối chiếu ba hướng dẫn hiện có: `training.md`, `evaluation.md` không đổi (kèm lý do), `replay-demo.md` chỉ đổi hàng mã thoát 7 (kèm đối chiếu mã). (d) Quét `git diff --name-only` của feature: không có `src/`, `pyproject.toml`, `uv.lock`, `.github/`, `tests/unit/capability_gate.py`; `git diff` mục `[0.1.0]` của CHANGELOG rỗng; `grep '^status: draft$' specs/006-cross-platform-support/spec.md` còn; 0 `skip`/`skipif`/`xfail`/`importorskip` mới trong diff test; `--collect-only` số test của tệp 008 ≥ mốc trước; thân test INV-002 của 008 không đổi (INV-002, INV-005, FR-011, FR-013). (e) Chạy `tests/e2e/test_008_docs_entrypoints.py` với `--capability-report` và đọc `ratio` ≤ 0,05; ghi giới hạn: ở bản archive không `.git` test INV-002 của 008 bị loại, chỉ chứng minh ở môi trường có git (NFR-GATE-001). (f) Ghi kết quả cổng `lint` (`ruff check .`), `typecheck` (`mypy --strict .`) và `ai-sdlc verify --branch ai-sdlc/integration` 5/5 xanh (FR-014, NFR-QUAL-001; AC-3). Reviewer là vai khác `docs` và `qa`. Verdict `APPROVE` chỉ khi mọi mục khớp; báo cáo liệt kê rõ phần CHƯA KIỂM. | evidence/reviews/T1005.verdict; .ai/runs/*/reports/reviewer-docs-sync-check.md | T1001; T1002; T1003; T1004 | reviewer | vừa |

<a id="dependencies-va-wave"></a>
## Dependencies và wave

- Wave 1: `T1001` (hướng dẫn `platforms.md` + `replay-demo.md`) và `T1003` (CHANGELOG) — độc lập nhau, chạy song song; tệp khác nhau.
- Wave 2: `T1002` (README; liên kết tới `platforms.md` nên sau `T1001`).
- Wave 3: `T1004` (qa; assert khẳng định nội dung README/CHANGELOG/`platforms.md` đã có).
- Wave 4: `T1005` (reviewer cuối; cần cả tài liệu lẫn test mới đối chiếu được).
- DAG nội bộ: `T1001 → T1002 → T1004 → T1005` và `T1001 → T1004`, `T1003 → T1004`, `T1001/T1002/T1003/T1004 → T1005`; không vòng. Phụ thuộc chéo feature khai ở bảng trên (`T609`, `T606`, `T628`, `T635`, `T640`, `T641`, `T711`, `T801`, `T802`, `T804`, `T902`, `T905`).
- Không có task sửa `status:` của spec 006 (D-7, INV-005). Khuyến nghị cho vai `platform` ở lượt riêng (KHÔNG thuộc feature này): ghi chú lỗi thời trong `.github/workflows/ci.yml` ("ma trận chưa chạy trên dịch vụ CI thật vì kho chưa có kho từ xa") trong khi kho đã có `origin`; vai `platform` có vùng ghi phủ tệp đó nên không có khoảng trống năng lực, không cần `ai-sdlc capability propose`.
- Vỏ `scripts/check_env.py` vẫn "chưa có chủ" theo báo cáo QA T640 (không vai nào phủ `scripts/`); ngoài phạm vi feature, tài liệu không nhắc tới nó.

<a id="dieu-kien-hoan-thanh"></a>
## Điều kiện hoàn thành

- `docs/guides/platforms.md` có mặt, ≤ 120 dòng, đủ sáu dấu năng lực, lệnh `python -m mma_ai.compat.env_report` chạy được trên Linux (SC-004); README có một liên kết tới nó.
- README nêu đúng bốn thành phần đã gộp của 006, Linux = đã kiểm, bốn hạng mục chưa kiểm, giữ liên kết `specs/006-cross-platform-support/` (SC-001, SC-002).
- `CHANGELOG.md` `[Unreleased]` có dòng cho đủ 006, 007, 008, 009, mỗi dòng một liên kết spec, sáu dấu năng lực đủ 6/6, câu giới hạn; `[0.1.0]` diff = 0 dòng (SC-003).
- `tests/e2e/test_008_docs_entrypoints.py` xanh ở môi trường có git, số test không giảm, 0 `skip`/`xfail` mới, thân test INV-002 nguyên (SC-005, SC-007).
- `evidence/reviews/T1005.verdict` là `APPROVE`; báo cáo `reviewer-docs-sync-check.md` ghi đối chiếu mọi lệnh/đường dẫn/marker và ba hướng dẫn cũ (SC-008).
- `git diff --name-only` chỉ gồm vùng ghi đã nêu (SC-007); `ai-sdlc verify --branch ai-sdlc/integration` xanh 5/5 cổng (SC-006).
- `ai-sdlc check tasks .` và `ai-sdlc check docs .` sạch.
