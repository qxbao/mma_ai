---
id: "SPEC-010"
title: "Đồng bộ tài liệu dự án với mã đã gộp (spec 006 đa nền tảng, 007, 008, 009) — Spec"
doc_type: spec
owner_agent: spec
status: draft
updated: "2026-10-13"
feature: "010-docs-platform-sync"
version: "1.0.0"
---

# Feature Specification: Đồng bộ tài liệu dự án với mã đã gộp (006 · 007 · 008 · 009)

- [Bối cảnh (Context)](#boi-canh-context)
- [Clarifications](#clarifications)
- [User Scenarios & Testing *(mandatory)*](#user-scenarios-testing-mandatory)
  - [User Story 1 - README nói đúng tình trạng nền tảng đã kiểm chứng (Priority: P1)](#user-story-1-readme-noi-dung-tinh-trang-nen-tang-da-kiem-chung-priority-p1)
  - [User Story 2 - CHANGELOG `[Unreleased]` liệt kê thay đổi của 006, 007, 008, 009 (Priority: P1)](#user-story-2-changelog-unreleased-liet-ke-thay-doi-cua-006-007-008-009-priority-p1)
  - [User Story 3 - Hướng dẫn `docs/guides/platforms.md` về môi trường và chẩn đoán đa nền tảng (Priority: P1)](#user-story-3-huong-dan-docsguidesplatformsmd-ve-moi-truong-va-chan-doan-da-nen-tang-priority-p1)
  - [User Story 4 - Cổng toàn hệ xanh và bộ test 008 khớp mô tả mới (Priority: P1)](#user-story-4-cong-toan-he-xanh-va-bo-test-008-khop-mo-ta-moi-priority-p1)
  - [User Story 5 - Reviewer độc lập duyệt, vùng ghi và ràng buộc được giữ (Priority: P2)](#user-story-5-reviewer-doc-lap-duyet-vung-ghi-va-rang-buoc-duoc-giu-priority-p2)
  - [Edge Cases](#edge-cases)
- [Requirements *(mandatory)*](#requirements-mandatory)
  - [Functional Requirements](#functional-requirements)
  - [Yêu cầu phi chức năng (Non-Functional Requirements)](#yeu-cau-phi-chuc-nang-non-functional-requirements)
  - [Bất biến (Invariants)](#bat-bien-invariants)
- [Success Criteria *(mandatory)*](#success-criteria-mandatory)
  - [Measurable Outcomes](#measurable-outcomes)
- [Out of Scope](#out-of-scope)
- [Assumptions](#assumptions)


**Feature Branch**: `010-docs-platform-sync` (tên thư mục feature; không tạo nhánh git mới)

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "Yêu cầu: cập nhật tài liệu dự án cho khớp mã đã gộp (spec 006 đa nền tảng, 007, 008, 009)" — nguồn: `.ai/chat/request-docs-sync.md` (qua `request.link`). Track S.

<a id="boi-canh-context"></a>
## Bối cảnh (Context)

Nhánh tích hợp đã được gộp vào `master` (commit `b82d690`) và `master` đã được đẩy lên kho từ xa (`origin` = `git@github.com:qxbao/mma_ai.git`). Tài liệu còn nói trạng thái cũ:

| # | Tài liệu | Hiện trạng (đối chiếu ở HEAD `b82d690`) | Sai lệch so với mã đã gộp |
|---|---|---|---|
| D-1 | `README.md`, mục "Tình trạng nền tảng" | Ghi "Hiện dự án nhắm tới Linux và lớp Linux trên Windows (WSL2)… hỗ trợ Windows và macOS đang được triển khai theo đặc tả 006, nên tài liệu này chưa xác nhận khả năng chạy" | Mã đa nền tảng của 006 đã gộp (gói `mma_ai.compat`, cổng năng lực, ma trận CI); mô tả "đang được triển khai" lỗi thời |
| D-2 | `CHANGELOG.md`, mục `[Unreleased]` | Trống | Đã có thay đổi của 006, 007, 008, 009 |
| D-3 | `docs/guides/` | Chỉ có `training.md`, `evaluation.md`, `replay-demo.md` | Chưa có hướng dẫn chạy/kiểm môi trường đa nền tảng |

Tài liệu đã lên kho công khai nên MUST đúng với **những gì đã được kiểm chứng**. Bằng chứng kiểm chứng hiện có (báo cáo QA T640 của 006, `.ai/runs/run-20261012-0ecb0c/reports/qa-006-crossplatform.md`): E2E, test đơn vị và tích hợp chạy xanh **trên Linux**; hành vi Windows/macOS chỉ được thử bằng hồ sơ nền tảng giả (tiêm); Windows 11 thật, macOS thật, CUDA thật và 6 ô CI thật **chưa kiểm**. Ngoài ra bộ test e2e của 008 (`tests/e2e/test_008_docs_entrypoints.py::test_ac2_inv003_platform_claims_match_draft_support`) đang khẳng định README chứa cụm "đang được triển khai" và "chưa xác nhận khả năng chạy"; mô tả mới của README phải đi kèm cập nhật đúng assert đó (vai qa), không nới lỏng test khác.

Người dùng của feature là **nhà nghiên cứu / kỹ sư dự án** (người cài và chạy dự án trên Windows, Linux, macOS) và các vai máy (qa, reviewer, cổng toàn hệ). Feature **không thêm hành vi sản phẩm**: chỉ sửa/thêm tài liệu tiếng Việt và cập nhật assert test tài liệu cho khớp. Mã `INV-*`, `AC-*`, `FR-*` không kèm "của 00x" là mã của **spec này**; mã của spec khác luôn ghi kèm "của 006"/"của 008"/"của 009".

<a id="clarifications"></a>
## Clarifications

- Tự chốt: Số hiệu feature → `010`, tên thư mục `010-docs-platform-sync` — lý do: kho đã có `specs/001`…`specs/009`; số tiếp theo là `010`.
- Q: Giao diện quan sát (C-0009) thuộc phạm vi vì chính người dùng đã đưa vào phạm vi con 2; vì vậy không phải mở rộng phạm vi do agent tự thêm. Hình thức giao diện (TensorBoard + bảng điều khiển web nhẹ, MuJoCo Viewer đọc checkpoint mới nhất, hay cả hai) là quyết định kỹ thuật được yêu cầu giao cho bước plan — cần người dùng xác nhận phạm vi — Lý do → A: Đồng ý (người dùng, C-0010): giao diện quan sát training thuộc phạm vi con 2; hình thức (TensorBoard, dashboard web nhẹ, MuJoCo Viewer đọc checkpoint mới nhất, hoặc kết hợp) để bước plan quyết định, kèm lý do và chi phí đo được; chỉ-đọc, chạy tiến trình riêng, không kéo chậm vòng train. (người, Q-0001)
- Tự chốt: Q-0001 → không áp dụng thêm cho feature này — lý do: câu trả lời ảnh hưởng `specs/003-ppo-train-repro/spec.md` và đã được ghi đúng khuôn ở đó; feature này không đổi giao diện quan sát. Tài liệu chỉ phải giữ đúng mô tả `--ui`/`--view3d` đã có trong hướng dẫn huấn luyện.
- Q: Mọi mục thêm ở bước này đều **dẫn xuất trực tiếp từ một trong sáu kết quả (a)–(f)**, không phải mở rộng phạm vi: ép UTF-8 cho đầu ra chuẩn, spawn của multiprocessing, tìm Python của venv theo OS (verify_clean_install), kiểm đường dẫn tuyệt đối theo mọi OS và .gitattributes đặt xuống dòng LF thuộc (a)/(d); khai báo năng lực (symlink, đường dẫn dài) thuộc (d)/(e)/(f); các Key Entity là mô hình hoá của "lớp tương thích", "báo cáo check_env" và "CI ma trận" mà yêu cầu nêu tên — cần người dùng xác nhận phạm vi — Lý do → A: Đồng ý (người dùng, C-0036): các mục thêm đều dẫn xuất từ (a)–(f), thuộc phạm vi Trong theo Default proposal. Xác nhận kèm: Windows native là môi trường chính, CUDA tuỳ chọn (máy người dùng có CUDA), macOS phải chạy tốt. (người, Q-0002)
- Tự chốt: Q-0002 → câu trả lời thuộc phạm vi của spec 006; ở feature này chỉ dùng làm **mục tiêu** của 006 (Windows gốc là môi trường chính, CUDA tuỳ chọn, macOS phải chạy tốt) và MUST được ghi là mục tiêu, không phải kết quả đã kiểm — lý do: yêu cầu gốc cấm khẳng định hơn bằng chứng; Windows gốc, macOS và CUDA chưa kiểm.
- Tự chốt: Mã tiêu chí → giữ nguyên AC-1, AC-2, AC-3 của yêu cầu gốc, không đặt thêm AC; các ràng buộc ("không sửa `src/`, `pyproject.toml`, `uv.lock`", "không nới lỏng test khác, không skip/xfail", "không đổi mục `[0.1.0]`", "không đổi `status:` của 006", "không khẳng định hơn bằng chứng") thành bất biến INV-001…INV-005 — lý do: yêu cầu gốc có đúng ba tiêu chí chấp nhận; ràng buộc là điều kiện giữ, không phải kết quả quan sát thêm.
- Tự chốt: `status:` của `specs/006-cross-platform-support/spec.md` → giữ `draft`, không đổi — lý do: yêu cầu cấm đổi trừ khi quy trình spec của dự án bắt buộc; không có quy tắc nào trong `CLAUDE.md`, `docs/MAP.md` hay các cổng đã đọc đòi đổi. Hệ quả: assert `^status: draft$` của test 008 vẫn đúng và được giữ; chỉ bỏ/đổi hai cụm văn bản "đang được triển khai" và "chưa xác nhận khả năng chạy". Bước plan phải xác nhận lại bằng đối chiếu cổng; nếu phát hiện quy trình bắt buộc đổi thì nêu rõ trong `plan.md` để người duyệt (không tự đổi).
- Tự chốt: Cụm từ bắt buộc mới của mục "Tình trạng nền tảng" → README MUST chứa các chuỗi `Windows`, `macOS`, `CUDA`, `chưa kiểm`, `specs/006-cross-platform-support/` và cụm `đã kiểm` gắn với Linux; test 008 được cập nhật để kiểm các chuỗi này thay cho hai cụm cũ — lý do: AC-2 đòi Linux = đã kiểm và Windows/macOS/CUDA/CI thật = chưa kiểm, ghi rõ; test phải bắt được việc README khẳng định hơn bằng chứng (ví dụ cấm cụm "hỗ trợ đầy đủ Windows" khi chưa kiểm). Cách diễn đạt chính xác thuộc bước plan/vai docs.
- Tự chốt: Thêm `docs/guides/platforms.md` kéo theo cập nhật các assert cấu trúc của test 008 — lý do: test hiện khẳng định thư mục `docs/guides` chứa **đúng** ba tệp (`{p.name for p in guides_dir.iterdir() if p.is_file()} == set(GUIDES)`), README có đúng 10 tiêu đề `##` và bốn lệnh nhanh, và mọi cờ trong guide được đối chiếu với `--help` của đúng một CLI ánh xạ trong `GUIDES`. Thêm tệp thứ tư mà không sửa test làm cổng đỏ; sửa các assert đó cho khớp (thêm `platforms.md` vào tập tệp, đối chiếu cờ của nó với `python -m mma_ai.compat.env_report` và `pytest --capability-report`, không bỏ kiểm tra) là hệ quả trực tiếp của mục 3 yêu cầu gốc, thuộc "vai qa cập nhật đúng các assert đó", không phải mở rộng phạm vi và không nới lỏng. Vùng ghi của task qa MUST khai đúng `tests/e2e/test_008_docs_entrypoints.py`.
- Tự chốt: Vị trí nội dung đa nền tảng trong README → nằm trong hai mục **đã có** ("Tình trạng nền tảng" và "Tài liệu"), không thêm tiêu đề `##` mới — lý do: test 008 khẳng định danh sách tiêu đề `##` cố định; thêm tiêu đề mới buộc đổi cấu trúc ngoài yêu cầu.
- Tự chốt: Lệnh chẩn đoán môi trường trong tài liệu → chỉ `python -m mma_ai.compat.env_report [--json]` — lý do: báo cáo QA T640 ghi "vỏ `scripts/check_env.py` chưa có chủ"; `scripts/` chỉ có `train.py`. Tài liệu MUST NOT nhắc `scripts/check_env.py` như lệnh dùng được.
- Tự chốt: Khối lệnh trong `CHANGELOG.md` → không dùng khối `sh`/`bash` (đường dẫn, tên marker, tên lệnh viết trong văn xuôi hoặc mã nội dòng) — lý do: test 008 khẳng định CHANGELOG không có khối lệnh (`assert not lines`); giữ nguyên.
- Tự chốt: Ghi chú lỗi thời trong `.github/workflows/ci.yml` ("ma trận chưa chạy trên dịch vụ CI thật vì kho chưa có kho từ xa") → ngoài phạm vi, không sửa; tài liệu MUST nêu thẳng "ô CI thật chưa kiểm" — lý do: yêu cầu giới hạn vào README/CHANGELOG/`docs/guides/` + assert test 008; `.github/` thuộc vùng ghi của 006, sửa ở đó là mở rộng phạm vi. Ghi nhận thành khuyến nghị cho vai platform ở phần Assumptions, không tự quyết.
- Tự chốt: Mức chi tiết các hướng dẫn hiện có (`training.md`, `evaluation.md`, `replay-demo.md`) → chỉ sửa nếu đối chiếu mã cho thấy lệnh/cờ/mã thoát/đầu ra đã đổi; kết quả đối chiếu (đổi hay không đổi, kèm lý do) MUST được ghi trong báo cáo review — lý do: yêu cầu nói "chỉ sửa nếu lệnh/đầu ra đã đổi — đối chiếu với mã, không bịa".
- Tự chốt: Có reviewer độc lập → ghi như yêu cầu về quy trình (FR-012), không thêm FR sản phẩm — lý do: vai viết (docs) và vai duyệt (reviewer) là hai vai riêng trong `docs/MAP.md` (cột Vai của 008: docs, qa, reviewer).
- Kết luận phân loại: rà các điểm còn lại, không điểm nào cần người trả lời; không thêm Key Entity, không thêm endpoint hay màn hình, không thêm hành vi sản phẩm — không có quyết định mở rộng phạm vi, nên không còn câu hỏi nào treo chờ người.

<a id="user-scenarios-testing-mandatory"></a>
## User Scenarios & Testing *(mandatory)*

<a id="user-story-1-readme-noi-dung-tinh-trang-nen-tang-da-kiem-chung-priority-p1"></a>
### User Story 1 - README nói đúng tình trạng nền tảng đã kiểm chứng (Priority: P1)

**Tần suất**: hiếm — người dùng mới đọc README khi tìm hiểu hoặc cài dự án (vài lần mỗi tháng); reviewer đọc một lần mỗi lượt sửa.

Người dùng mở README, đọc mục "Tình trạng nền tảng" và biết ngay: mã đa nền tảng đã gộp (gói `mma_ai.compat` gồm dò nền tảng/RAM/màn hình, thay tệp nguyên tử, báo cáo môi trường `python -m mma_ai.compat.env_report`, cổng năng lực loại test theo máy, ma trận CI 3 hệ điều hành × Python 3.11/3.12 khai ở `.github/workflows/ci.yml`); **chỉ đã kiểm trên Linux**; Windows 11, macOS, CUDA và các ô CI chạy thật trên GitHub Actions **chưa kiểm**. README giữ liên kết tới `specs/006-cross-platform-support/`.

**Why this priority**: README là cửa vào công khai; khẳng định hơn bằng chứng làm người dùng Windows/macOS tin nhầm và vi phạm hiến chương I (trung thực về bằng chứng).

**Independent Test**: Đọc mục "Tình trạng nền tảng" và đối chiếu từng câu với `specs/006-cross-platform-support/` và báo cáo QA T640; chạy test e2e của 008 đã cập nhật.

**Acceptance Scenarios**:

1. **Given** README sau khi sửa, **When** đọc mục "Tình trạng nền tảng", **Then** mục mô tả đúng bốn thành phần đã gộp của 006 (gói `mma_ai.compat`; báo cáo môi trường `python -m mma_ai.compat.env_report`; cổng năng lực loại test theo máy; ma trận CI 3 hệ điều hành × Python 3.11/3.12 trong `.github/workflows/ci.yml`) và mỗi tên/đường dẫn nêu trong đó tồn tại thật trong kho (AC-1).
2. **Given** README sau khi sửa, **When** đọc mục đó, **Then** nêu Linux = **đã kiểm** và nêu thẳng Windows 11, macOS, CUDA và các ô CI chạy thật trên GitHub Actions = **chưa kiểm**; không có câu nào khẳng định chạy được trên Windows/macOS/CUDA/CI thật (AC-2).
3. **Given** README sau khi sửa, **When** kiểm liên kết, **Then** còn liên kết tới `specs/006-cross-platform-support/` và mọi liên kết tương đối khác trỏ tới đích tồn tại (AC-1).
4. **Given** README sau khi sửa, **When** đối chiếu cấu trúc, **Then** vẫn đúng 10 tiêu đề `##` cũ theo thứ tự cũ, bốn lệnh nhanh cũ, huy hiệu cũ, và các cụm "đang được triển khai"/"chưa xác nhận khả năng chạy" không còn khẳng định tình trạng đã lỗi thời (AC-1).

---

<a id="user-story-2-changelog-unreleased-liet-ke-thay-doi-cua-006-007-008-009-priority-p1"></a>
### User Story 2 - CHANGELOG `[Unreleased]` liệt kê thay đổi của 006, 007, 008, 009 (Priority: P1)

**Tần suất**: hiếm — người bảo trì đọc mỗi khi chuẩn bị phát hành (vài lần mỗi tháng); reviewer đọc một lần mỗi lượt sửa.

Người bảo trì mở `CHANGELOG.md` và thấy mục `[Unreleased]` có các dòng Added/Changed cho: 006 (gói `mma_ai.compat`; cổng năng lực với sáu dấu `requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `requires_xdist`, `requires_git_history`; CI ma trận), 007 (ổn định hai test viewer), 008 (bộ tài liệu dự án), 009 (năng lực `requires_git_history`). Mỗi dòng liên kết tới spec tương ứng; có một câu nêu giới hạn "chưa kiểm Windows/macOS/CI thật". Mục `[0.1.0]` không đổi.

**Why this priority**: Nhật ký thay đổi trống làm người dùng không biết kho đã đổi gì; thông tin giới hạn ngăn hiểu nhầm là đã phát hành đa nền tảng.

**Independent Test**: So `[Unreleased]` với `specs/006…009/spec.md` và mã; `git diff` mục `[0.1.0]` phải rỗng.

**Acceptance Scenarios**:

1. **Given** `CHANGELOG.md` sau khi sửa, **When** đọc mục `[Unreleased]`, **Then** có các nhóm `### Added` và `### Changed` và có dòng cho cả bốn spec 006, 007, 008, 009, mỗi dòng chứa liên kết tương đối tới `specs/006-cross-platform-support/`, `specs/007-stabilize-viewer-tests/`, `specs/008-project-docs/`, `specs/009-git-history-capability/` tương ứng (AC-1).
2. **Given** dòng của 006, **When** đọc, **Then** nêu đủ sáu tên dấu năng lực `requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `requires_xdist`, `requires_git_history` và mỗi tên có thật trong bộ cổng năng lực `tests/unit/capability_gate.py` (AC-1).
3. **Given** mục `[Unreleased]`, **When** đọc, **Then** có câu nêu giới hạn: chưa kiểm Windows, macOS và CI chạy thật; mọi kết quả đã kiểm chỉ trên Linux (AC-2).
4. **Given** `git diff` của `CHANGELOG.md`, **When** đối chiếu với bản trước, **Then** mục `## [0.1.0] - 2026-10-12` và các dòng của nó không đổi một ký tự (AC-1).

---

<a id="user-story-3-huong-dan-docsguidesplatformsmd-ve-moi-truong-va-chan-doan-da-nen-tang-priority-p1"></a>
### User Story 3 - Hướng dẫn `docs/guides/platforms.md` về môi trường và chẩn đoán đa nền tảng (Priority: P1)

**Tần suất**: hằng tuần — nhà nghiên cứu/kỹ sư chạy lại báo cáo môi trường khi đổi máy, cập nhật phụ thuộc hoặc khi cổng báo "bị loại X/Y" (vài lần mỗi tuần).

Người dùng mở `docs/guides/platforms.md` (ngắn, theo khuôn của ba hướng dẫn hiện có) và biết: chạy `python -m mma_ai.compat.env_report` (có cờ `--json`) để xem báo cáo môi trường; ý nghĩa sáu dấu năng lực `requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `requires_xdist`, `requires_git_history`; cách đọc dòng báo cáo "Kiểm thử bị loại theo năng lực: X/Y (…)" cùng tùy chọn `--capability-report`; vì sao test lịch sử git bị loại trên bản archive không có `.git`; và giới hạn đã kiểm/chưa kiểm của từng nền tảng. README (mục "Tài liệu") có liên kết tới hướng dẫn này.

**Why this priority**: Báo cáo "bị loại X/Y" và `env_report` là cách duy nhất để người dùng phân biệt "test đỏ vì lỗi thật" với "test bị loại vì thiếu năng lực của máy"; thiếu hướng dẫn làm người dùng nghi ngờ cổng.

**Independent Test**: Chạy `python -m mma_ai.compat.env_report` và `python -m mma_ai.compat.env_report --json` trên Linux, đối chiếu ý nghĩa mô tả với đầu ra thật; chạy pytest với `--capability-report` và đối chiếu định dạng dòng "bị loại".

**Acceptance Scenarios**:

1. **Given** `docs/guides/platforms.md`, **When** đọc, **Then** nêu lệnh `python -m mma_ai.compat.env_report` và cờ `--json`, và lệnh chạy được: trên Linux thoát mã 0 khi môi trường đạt (hoặc mã 1 khi có mục `fail`) và in dòng kết luận "Môi trường đạt yêu cầu." / "Môi trường chưa đạt yêu cầu." đúng như mã (AC-1).
2. **Given** `docs/guides/platforms.md`, **When** đối chiếu với `tests/unit/capability_gate.py`, **Then** liệt kê đủ sáu dấu năng lực và mô tả ý nghĩa từng dấu khớp mô tả khai trong bộ cổng (màn hình hiển thị; CUDA khả dụng; liên kết tượng trưng; chỉ Windows; pytest-xdist; lịch sử git) (AC-1).
3. **Given** `docs/guides/platforms.md`, **When** đọc phần "bị loại X/Y", **Then** giải thích định dạng "Kiểm thử bị loại theo năng lực: X/Y (tỉ lệ; giới hạn 5.0%)." kèm danh sách `nodeid [dấu]: lý do`, nêu ngưỡng loại mặc định 5% (vượt thì phiên đỏ), và cách ghi báo cáo JSON bằng `--capability-report <tệp>` (AC-1).
4. **Given** `docs/guides/platforms.md`, **When** đọc phần lịch sử git, **Then** giải thích: test INV-002 của 008 cần lịch sử commit, bị loại có báo cáo (không skip, không xfail, không xanh giả) trên bản archive không có `.git` với lý do `Máy không có lịch sử git`; INV-002 của 008 chỉ được chứng minh ở môi trường có git (AC-1).
5. **Given** `docs/guides/platforms.md`, **When** đọc phần giới hạn, **Then** ghi Linux = đã kiểm; Windows 11, macOS (kể cả cách chạy viewer bằng `mjpython` trên macOS), CUDA và ô CI thật = chưa kiểm; nêu rõ đây là mục tiêu của 006, không phải kết quả đã kiểm (AC-2).
6. **Given** README sau khi sửa, **When** đọc mục "Tài liệu", **Then** có liên kết tới `docs/guides/platforms.md` (đích tồn tại) bên cạnh ba hướng dẫn cũ (AC-1).
7. **Given** các hướng dẫn `training.md`, `evaluation.md`, `replay-demo.md`, **When** đối chiếu lệnh/cờ/mã thoát với `--help` và mã của CLI tương ứng, **Then** mỗi hướng dẫn hoặc không đổi (đối chiếu khớp, ghi kết quả vào báo cáo review) hoặc chỉ sửa đúng chỗ lệnh/đầu ra đã đổi; không thêm cờ/lệnh không có ở CLI thật (AC-1).

---

<a id="user-story-4-cong-toan-he-xanh-va-bo-test-008-khop-mo-ta-moi-priority-p1"></a>
### User Story 4 - Cổng toàn hệ xanh và bộ test 008 khớp mô tả mới (Priority: P1)

**Tần suất**: hằng ngày — mỗi lượt cổng toàn hệ (`ai-sdlc verify`) trên nhánh tích hợp (cổng máy; vai qa/reviewer xem kết quả nhiều lần mỗi ngày).

Sau khi tài liệu và assert test được cập nhật, `ai-sdlc verify --branch ai-sdlc/integration` xanh ở năm cổng. Test e2e của 008 (`tests/e2e/test_008_docs_entrypoints.py`) kiểm mô tả nền tảng mới của README (Linux đã kiểm; Windows/macOS/CUDA/CI thật chưa kiểm; liên kết tới 006) thay cho hai cụm cũ, và kiểm cấu trúc có thêm `platforms.md`, mà không bỏ kiểm tra nào khác.

**Why this priority**: Cổng đỏ chặn mọi feature khác; đồng thời assert phải đủ chặt để bắt README khẳng định hơn bằng chứng (nếu assert chỉ kiểm "có chữ Windows" thì không bảo vệ được AC-2).

**Independent Test**: Chạy `ai-sdlc verify --branch ai-sdlc/integration`; chạy riêng `pytest tests/e2e/test_008_docs_entrypoints.py` và đọc diff của tệp test.

**Acceptance Scenarios**:

1. **Given** nhánh tích hợp đã có thay đổi của feature này, **When** chạy `ai-sdlc verify --branch ai-sdlc/integration`, **Then** năm cổng `lint`, `tests`, `typecheck`, `e2e`, `risk_coverage` đều xanh (AC-3).
2. **Given** diff của `tests/e2e/test_008_docs_entrypoints.py`, **When** đối chiếu với bản trước, **Then** các assert của `test_ac2_inv003_platform_claims_match_draft_support` được đổi sang mô tả mới (Linux đã kiểm; Windows/macOS/CUDA/CI thật chưa kiểm; có `specs/006-cross-platform-support/`), vẫn đòi `status: draft` của 006 và vẫn đòi nêu "chưa kiểm" cho Windows, macOS và CI thật (AC-2).
3. **Given** diff đó, **When** quét, **Then** không có `pytest.skip`/`skipif`/`xfail`/`importorskip` mới, số test của tệp không giảm, thân test `test_inv002_document_commits_keep_product_code_untouched` và dấu `@pytest.mark.requires_git_history(reason="Máy không có lịch sử git")` của nó giữ nguyên, và các assert của test khác chỉ đổi đúng ở chỗ phải đổi vì `platforms.md` (tập tệp trong `docs/guides/`, ánh xạ cờ) (AC-1).
4. **Given** phiên cổng `e2e` ở bản archive không có `.git`, **When** đọc báo cáo năng lực, **Then** test INV-002 của 008 vẫn bị loại với lý do `Máy không có lịch sử git`, tỉ lệ loại ≤ 5% và phiên không đỏ vì feature này (AC-3).

---

<a id="user-story-5-reviewer-doc-lap-duyet-vung-ghi-va-rang-buoc-duoc-giu-priority-p2"></a>
### User Story 5 - Reviewer độc lập duyệt, vùng ghi và ràng buộc được giữ (Priority: P2)

**Tần suất**: hiếm — một lần mỗi lượt sửa, bởi vai reviewer (khác vai viết tài liệu).

Reviewer đối chiếu từng câu nền tảng/lệnh/marker trong tài liệu với mã và với báo cáo QA 006, rồi ghi verdict. Reviewer so diff với ràng buộc: không sửa `src/`, `pyproject.toml`, `uv.lock`; không đổi `status:` của 006; không đổi mục `[0.1.0]`; không nới lỏng test khác.

**Why this priority**: Hiến chương I và III: không tin bằng chứng tự khai, giới hạn vùng ghi; vai viết không tự duyệt.

**Independent Test**: `git diff --name-only` của lượt sửa; đối chiếu với cột outputs của `specs/010-docs-platform-sync/tasks.md`; đọc verdict.

**Acceptance Scenarios**:

1. **Given** diff của lượt sửa, **When** liệt kê tệp đổi, **Then** chỉ gồm `README.md`, `CHANGELOG.md`, `docs/guides/platforms.md` (và `docs/guides/{training,evaluation,replay-demo}.md` nếu có đối chiếu cho thấy đã đổi), `tests/e2e/test_008_docs_entrypoints.py`, tệp của feature (`specs/010-docs-platform-sync/`, `docs/05-tracing/`, `docs/MAP.md` do máy sinh) và bằng chứng review; không có tệp trong `src/`, không có `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml` (INV-002, AC-1).
2. **Given** verdict của reviewer, **When** đọc, **Then** reviewer là vai khác vai viết tài liệu (docs), đã đối chiếu mọi lệnh, đường dẫn, tên marker với mã, và ghi kết quả đối chiếu cho ba hướng dẫn hiện có (AC-1).
3. **Given** `specs/006-cross-platform-support/spec.md`, **When** đối chiếu với bản trước, **Then** dòng `status: draft` không đổi (INV-005, AC-2).

---

<a id="edge-cases"></a>
### Edge Cases

- Bản archive không có `.git`: test lịch sử git của 008 bị loại có báo cáo; tài liệu MUST nói rõ đây là hành vi đúng (không phải lỗi) và INV-002 của 008 chỉ chứng minh ở môi trường có git. (AC-2, INV-003)
- README ghi "đã kiểm trên Linux" nhưng bằng chứng QA chỉ là Linux của máy phát triển, không phải mọi bản phân phối Linux/WSL2: tài liệu MUST gắn "đã kiểm" với Linux mà không mở rộng sang WSL2 hay bản phân phối khác nếu không có bằng chứng; WSL2 chỉ được nêu như hướng dùng cho người dùng Windows ở mức đã có trong README cũ hoặc ghi "chưa kiểm". (AC-2, INV-001)
- Mục tiêu của 006 (Windows gốc là môi trường chính, CUDA tuỳ chọn, macOS phải chạy tốt) đúng là mục tiêu nhưng chưa kiểm: nếu tài liệu nhắc, MUST ghi là "mục tiêu" kèm "chưa kiểm". (AC-2, INV-001)
- Lệnh `python -m mma_ai.compat.env_report` thoát mã 1 khi có mục `fail` và mã 2 với cờ lạ: tài liệu chỉ nêu các hành vi này nếu đối chiếu mã xác nhận; không nêu `scripts/check_env.py` (không tồn tại). (AC-1, INV-001)
- Assert của test 008 đang khẳng định `docs/guides` chứa đúng ba tệp, README có đúng 10 tiêu đề `##`, mỗi hướng dẫn ≤ 120 dòng và chứa liên kết `../../README.md`, CHANGELOG không có khối lệnh: `platforms.md` MUST tuân các ràng buộc này (≤ 120 dòng, có liên kết `../../README.md`), và README/CHANGELOG MUST không phá cấu trúc đó. (AC-1)
- Hướng dẫn thật dùng cờ `--json` và `--capability-report` không thuộc `--help` của bốn CLI trong `GUIDES`: assert đối chiếu cờ cho `platforms.md` MUST đối chiếu với đúng nguồn của chúng (`env_report` và bộ cổng năng lực), không bỏ qua và không nới. (AC-1, INV-004)
- Liên kết trong tài liệu trỏ tới tệp do máy sinh (`docs/MAP.md`) hoặc thư mục spec: đích MUST tồn tại ở HEAD; không liên kết tới tệp chỉ có sau khi chạy lệnh. (AC-1)
- Ghi chú trong `.github/workflows/ci.yml` còn nói "kho chưa có kho từ xa" lỗi thời trong khi kho đã có `origin`: không sửa ở feature này; tài liệu MUST không lặp lại câu lỗi thời và vẫn nêu "ô CI chạy thật chưa kiểm". (AC-2, INV-002)
- Tên dấu năng lực trong bộ cổng có thêm các dấu `posix_only`, `linux_only`, `macos_only` ngoài sáu dấu nêu trong yêu cầu: tài liệu MUST đúng với mã; nếu nhắc dấu nào thì dấu đó phải có thật; yêu cầu liệt kê sáu dấu thì sáu dấu đó MUST có đủ. (AC-1)
- Số liệu của báo cáo QA (ví dụ 1/1552 bị loại, 0,1%) là của một lượt chạy tại SHA cụ thể, có thể đổi: tài liệu MUST không chép các số này như hằng số của sản phẩm. (INV-001)
- Số test của `tests/e2e/test_008_docs_entrypoints.py` không được giảm sau khi sửa assert. (INV-003)

<a id="requirements-mandatory"></a>
## Requirements *(mandatory)*

<a id="functional-requirements"></a>
### Functional Requirements

- **FR-001**: Mục "Tình trạng nền tảng" của `README.md` MUST mô tả đúng hiện trạng mã đã gộp: gói `mma_ai.compat` (dò nền tảng/RAM/màn hình, thay tệp nguyên tử), báo cáo môi trường `python -m mma_ai.compat.env_report`, cổng năng lực loại test theo máy, ma trận CI 3 hệ điều hành × Python 3.11/3.12 trong `.github/workflows/ci.yml`; mọi tên/đường dẫn nêu MUST tồn tại thật trong kho. (AC-1)
- **FR-002**: Mục đó MUST nêu Linux = **đã kiểm**; Windows 11, macOS, CUDA và các ô CI chạy thật trên GitHub Actions = **chưa kiểm**, bằng lời trực tiếp; MUST NOT có câu khẳng định chạy được/hỗ trợ đầy đủ trên các nền tảng chưa kiểm; MUST giữ liên kết tới `specs/006-cross-platform-support/`. (AC-1, AC-2)
- **FR-003**: README MUST giữ nguyên danh sách 10 tiêu đề `##` và thứ tự, bốn lệnh bắt đầu nhanh, huy hiệu và các mục khác; thay đổi nội dung nền tảng MUST nằm trong mục "Tình trạng nền tảng" và liên kết mới MUST nằm trong mục "Tài liệu". (AC-1)
- **FR-004**: Mục `[Unreleased]` của `CHANGELOG.md` MUST có nhóm `### Added` và `### Changed` liệt kê: 006 (gói `mma_ai.compat`; cổng năng lực với sáu dấu `requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `requires_xdist`, `requires_git_history`; CI ma trận), 007 (ổn định test viewer), 008 (tài liệu dự án), 009 (năng lực `requires_git_history`); mỗi dòng MUST liên kết tới spec tương ứng bằng đường dẫn tương đối tồn tại. (AC-1)
- **FR-005**: `[Unreleased]` MUST nêu giới hạn "chưa kiểm Windows/macOS/CI thật" (mọi kết quả đã kiểm chỉ trên Linux); mục `[0.1.0]` MUST giữ nguyên từng ký tự; CHANGELOG MUST không chứa khối lệnh `sh`/`bash`. (AC-1, AC-2)
- **FR-006**: MUST thêm `docs/guides/platforms.md` — hướng dẫn tiếng Việt ngắn (≤ 120 dòng, khung frontmatter như ba hướng dẫn hiện có, có liên kết `../../README.md`, thuật ngữ song ngữ ở lần đầu theo quy ước dự án) gồm: chạy `python -m mma_ai.compat.env_report` (và `--json`); ý nghĩa sáu dấu năng lực; cách đọc báo cáo "bị loại X/Y" và `--capability-report`; lý do test lịch sử git bị loại trên bản archive không có `.git`; giới hạn đã kiểm/chưa kiểm của từng nền tảng. (AC-1, AC-2)
- **FR-007**: README mục "Tài liệu" MUST có liên kết tới `docs/guides/platforms.md`. (AC-1)
- **FR-008**: Ba hướng dẫn hiện có (`training.md`, `evaluation.md`, `replay-demo.md`) MUST được đối chiếu với mã/`--help` của CLI tương ứng; chỉ sửa chỗ lệnh/cờ/mã thoát/đầu ra đã đổi; kết quả đối chiếu (đổi hay không đổi, lý do) MUST được ghi trong báo cáo review. (AC-1)
- **FR-009**: Mọi lệnh, đường dẫn, tên dấu năng lực trong README, CHANGELOG, `platforms.md` MUST tồn tại thật trong kho và lệnh MUST chạy được ở Linux; MUST NOT phát biểu về hành vi Windows/macOS/CUDA ngoài mức spec 006 và báo cáo QA T640 đã ghi là ĐÃ/CHƯA kiểm; MUST NOT nhắc `scripts/check_env.py`. (AC-1, AC-2)
- **FR-010**: Vai qa MUST cập nhật `tests/e2e/test_008_docs_entrypoints.py` đồng bộ: (a) assert `test_ac2_inv003_platform_claims_match_draft_support` chuyển sang mô tả mới của README (Linux đã kiểm; Windows, macOS, CUDA, ô CI thật chưa kiểm; có `specs/006-cross-platform-support/`; vẫn đòi `status: draft` của 006) và MUST đòi nêu "chưa kiểm" rõ ràng; (b) các assert cấu trúc chịu ảnh hưởng trực tiếp của `platforms.md` (tập tệp `docs/guides`, ánh xạ đối chiếu cờ, danh sách tài liệu kiểm liên kết) được sửa để **bao gồm** `platforms.md`, không bỏ kiểm tra. (AC-2, AC-3)
- **FR-011**: Thay đổi test MUST NOT thêm `pytest.skip`/`skipif`/`xfail`/`importorskip`, MUST NOT nới lỏng test khác, MUST NOT giảm số test, MUST NOT sửa thân test `test_inv002_document_commits_keep_product_code_untouched` (giữ nguyên dấu `requires_git_history`). (AC-3)
- **FR-012**: Phần tài liệu MUST được một reviewer độc lập (vai khác vai viết) duyệt, ghi verdict kèm kết quả đối chiếu lệnh/đường dẫn/marker với mã. (AC-1)
- **FR-013**: Feature MUST NOT sửa `src/`, `pyproject.toml`, `uv.lock`, `.github/`; MUST NOT đổi `status:` của `specs/006-cross-platform-support/spec.md`. (AC-3)
- **FR-014**: Sau khi các thay đổi vào nhánh tích hợp, `ai-sdlc verify --branch ai-sdlc/integration` MUST xanh ở `lint`, `tests`, `typecheck`, `e2e`, `risk_coverage`. (AC-3)

<a id="yeu-cau-phi-chuc-nang-non-functional-requirements"></a>
### Yêu cầu phi chức năng (Non-Functional Requirements)

- **NFR-DOC-001**: Liên kết nội bộ của tài liệu không hỏng.
  Ngưỡng: 0 liên kết tương đối có đích không tồn tại trong `README.md`, `CHANGELOG.md`, `docs/guides/platforms.md` và ba hướng dẫn cũ.
  Đo bằng: `pytest tests/e2e/test_008_docs_entrypoints.py` (test `test_ac2_ac3_ac4_ac5_inv004_relative_links` mở rộng cho `platforms.md`). (AC-1)
- **NFR-DOC-002**: Hướng dẫn mới đủ ngắn để đọc nhanh.
  Ngưỡng: `docs/guides/platforms.md` ≤ 120 dòng; mỗi hướng dẫn cũ vẫn ≤ 120 dòng.
  Đo bằng: assert độ dài trong `tests/e2e/test_008_docs_entrypoints.py` (`test_ac1_ac2_ac3_ac4_ac5_document_structure`). (AC-1)
- **NFR-GATE-001**: Tỉ lệ loại theo năng lực không vượt ngưỡng của 006.
  Ngưỡng: tỉ lệ test bị loại ≤ 5% (0,05) trên mỗi phiên cổng `tests` và `e2e`, kể cả ở bản archive không có `.git`; feature không đổi ngưỡng.
  Đo bằng: `pytest --capability-report=<tệp>` rồi đọc trường `ratio`. (AC-3)
- **NFR-QUAL-001**: Chất lượng mã kiểm thử.
  Ngưỡng: `ruff check` và `mypy --strict` xanh (0 lỗi) trên toàn kho sau khi sửa test.
  Đo bằng: cổng `lint` (`uv run --isolated --with ruff ruff check .`) và cổng `typecheck` (`uv run --isolated --with mypy mypy --strict .`). (AC-3)

<a id="bat-bien-invariants"></a>
### Bất biến (Invariants)

- **INV-001**: Tài liệu MUST NOT khẳng định hơn bằng chứng: Windows 11, macOS, CUDA và các ô CI chạy thật MUST được ghi "chưa kiểm"; Linux là nền tảng duy nhất ghi "đã kiểm"; số liệu của một lượt chạy cụ thể MUST NOT được chép như hằng số sản phẩm. (AC-2)
- **INV-002**: Vùng ghi: feature MUST NOT sửa `src/`, `pyproject.toml`, `uv.lock`, `.github/`, mục `[0.1.0]` của CHANGELOG, `status:` của spec 006; test chỉ được sửa ở `tests/e2e/test_008_docs_entrypoints.py` (và tệp của feature/bằng chứng review). (AC-3)
- **INV-003**: Không che lỗi bằng test: MUST NOT thêm `skip`/`skipif`/`xfail`/`importorskip`, MUST NOT nới lỏng hay xóa assert của test khác, số test của `tests/e2e/test_008_docs_entrypoints.py` MUST NOT giảm; thân test INV-002 của 008 MUST giữ nguyên (kế thừa INV-006 của 006, INV-001/INV-002 của 009). (AC-3)
- **INV-004**: Mọi lệnh/đường dẫn/tên marker trong tài liệu MUST tồn tại thật trong kho tại HEAD; cờ nêu trong tài liệu MUST được đối chiếu với nguồn thật của cờ đó. (AC-1)
- **INV-005**: `status:` của `specs/006-cross-platform-support/spec.md` MUST giữ nguyên `draft` trừ khi `plan.md` nêu quy trình bắt buộc và người duyệt chấp thuận. (AC-2)

<a id="success-criteria-mandatory"></a>
## Success Criteria *(mandatory)*

<a id="measurable-outcomes"></a>
### Measurable Outcomes

- **SC-001**: README mục "Tình trạng nền tảng" nêu đúng bốn thành phần đã gộp của 006 và 0 tên/đường dẫn không tồn tại; liên kết tới `specs/006-cross-platform-support/` còn nguyên. (AC-1)
- **SC-002**: Đúng 1 nền tảng (Linux) được ghi "đã kiểm"; 4 hạng mục (Windows 11, macOS, CUDA, ô CI chạy thật trên GitHub Actions) được ghi "chưa kiểm"; 0 câu khẳng định hơn bằng chứng. (AC-2)
- **SC-003**: `[Unreleased]` của CHANGELOG có dòng cho đủ 4/4 spec (006, 007, 008, 009), mỗi dòng 1 liên kết tới spec; sáu dấu năng lực nêu đủ 6/6; mục `[0.1.0]` diff = 0 dòng. (AC-1)
- **SC-004**: `docs/guides/platforms.md` tồn tại, ≤ 120 dòng, nêu đủ 6/6 dấu năng lực, lệnh `python -m mma_ai.compat.env_report` chạy thoát mã 0 trên Linux đạt yêu cầu, và README có 1 liên kết tới nó. (AC-1)
- **SC-005**: 0 liên kết tương đối hỏng trong 6 tài liệu (README, CHANGELOG, bốn hướng dẫn); `tests/e2e/test_008_docs_entrypoints.py` PASS ở môi trường có git với số test không giảm. (AC-1)
- **SC-006**: `ai-sdlc verify --branch ai-sdlc/integration` xanh ở 5/5 cổng (`lint`, `tests`, `typecheck`, `e2e`, `risk_coverage`). (AC-3)
- **SC-007**: `git diff --name-only` có 0 tệp trong `src/`, 0 thay đổi ở `pyproject.toml`, `uv.lock`, `.github/`; 0 `skip`/`xfail` mới. (AC-3)
- **SC-008**: Có 1 verdict của reviewer (vai khác vai docs) ghi kết quả đối chiếu mọi lệnh/đường dẫn/marker. (AC-1)

<a id="out-of-scope"></a>
## Out of Scope

- Sửa mã trong `src/`, `pyproject.toml`, `uv.lock`.
- Đổi `status:` của spec 006 (trừ khi `plan.md` chỉ ra quy trình spec bắt buộc và người duyệt chấp thuận).
- Nới lỏng hoặc xóa test khác, thêm `skip`/`xfail`, sửa thân test INV-002 của 008 (đã đánh dấu `requires_git_history`).
- Đổi mục `[0.1.0]` của CHANGELOG.
- Kiểm chứng Windows 11, macOS, CUDA hoặc chạy ma trận CI thật trên GitHub Actions (vẫn là "chưa kiểm"; tài liệu chỉ ghi thẳng điều đó).
- Sửa `.github/workflows/ci.yml` (kể cả ghi chú lỗi thời về "kho chưa có kho từ xa") và thêm vỏ `scripts/check_env.py`.
- Thêm hành vi sản phẩm, màn hình, endpoint hoặc thực thể dữ liệu mới; thêm tiêu đề `##` mới vào README.
- Sửa các hướng dẫn hiện có khi đối chiếu cho thấy lệnh/đầu ra chưa đổi.

<a id="assumptions"></a>
## Assumptions

- HEAD tại lượt đặc tả là `b82d690` trên `master`; mã của 006–009 đã gộp ở đó (`src/mma_ai/compat/`, `tests/unit/capability_gate.py`, `.github/workflows/ci.yml`, `docs/05-tracing/trace/00{6,7,8,9}-*.md` có mặt). Mã sản phẩm không đổi trong feature này nên đối chiếu ở HEAD vẫn đúng ở lúc thi công.
- Nguồn bằng chứng đã/chưa kiểm của Windows/macOS/CUDA/CI thật: `specs/006-cross-platform-support/` và báo cáo QA T640 (`.ai/runs/run-20261012-0ecb0c/reports/qa-006-crossplatform.md`). Nếu vai thi công tìm thấy bằng chứng mới (ví dụ ô CI đã chạy thật) thì MUST đưa lên người duyệt trước khi đổi "chưa kiểm"; không tự đổi.
- Ba hướng dẫn hiện có chưa được đối chiếu lại trong lượt đặc tả này (CHƯA KIỂM); việc đối chiếu `--help` và mã thoát là việc của bước plan/thi công (FR-008). Test 008 hiện đã đối chiếu cờ của chúng với `--help` thật.
- Ghi chú lỗi thời trong `.github/workflows/ci.yml` (kho chưa có remote) là khuyến nghị cho vai platform ở một lượt riêng; feature này không sửa (xem Out of Scope).
- Cổng toàn hệ trên bản archive không có `.git` vẫn loại test INV-002 của 008 theo năng lực `requires_git_history` (feature 009); feature này dựa vào cơ chế đó và không đổi nó.
