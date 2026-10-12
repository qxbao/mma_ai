---
id: "SPEC-009"
title: "Năng lực `requires_git_history` cho cổng năng lực (sửa cổng toàn hệ đỏ do bản archive không có .git) — Spec"
doc_type: spec
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "009-git-history-capability"
version: "1.0.0"
---

# Feature Specification: Năng lực `requires_git_history` cho cổng năng lực

- [Bối cảnh (Context)](#boi-canh-context)
- [Clarifications](#clarifications)
- [User Scenarios & Testing *(mandatory)*](#user-scenarios-testing-mandatory)
  - [User Story 1 - Phép dò năng lực lịch sử git được chứng minh đủ các nhánh (Priority: P1)](#user-story-1-phep-do-nang-luc-lich-su-git-duoc-chung-minh-du-cac-nhanh-priority-p1)
  - [User Story 2 - Test INV-002 của 008 mang dấu năng lực, thân test giữ nguyên (Priority: P1)](#user-story-2-test-inv-002-cua-008-mang-dau-nang-luc-than-test-giu-nguyen-priority-p1)
  - [User Story 3 - Cổng toàn hệ trên bản archive không còn đỏ vì test này (Priority: P1)](#user-story-3-cong-toan-he-tren-ban-archive-khong-con-do-vi-test-nay-priority-p1)
  - [User Story 4 - Không che lỗi, không nới ngưỡng, vùng ghi đúng hai tệp test (Priority: P2)](#user-story-4-khong-che-loi-khong-noi-nguong-vung-ghi-dung-hai-tep-test-priority-p2)
  - [Edge Cases](#edge-cases)
- [Requirements *(mandatory)*](#requirements-mandatory)
  - [Functional Requirements](#functional-requirements)
  - [Yêu cầu phi chức năng (Non-Functional Requirements)](#yeu-cau-phi-chuc-nang-non-functional-requirements)
  - [Bất biến (Invariants)](#bat-bien-invariants)
- [Success Criteria *(mandatory)*](#success-criteria-mandatory)
  - [Measurable Outcomes](#measurable-outcomes)
- [Out of Scope](#out-of-scope)
- [Assumptions](#assumptions)


**Feature Branch**: `009-git-history-capability` (tên thư mục feature; không tạo nhánh git mới)

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "Yêu cầu: năng lực `requires_git_history` cho cổng năng lực (sửa cổng toàn hệ đỏ do bản archive không có .git)" — nguồn: `.ai/chat/request-git-history-gate.md` (qua `request.link`). Track S.

<a id="boi-canh-context"></a>
## Bối cảnh (Context)

Cổng toàn hệ (`ai-sdlc verify` / integration-check) chạy trên **bản archive** của nhánh tích hợp, **không có `.git`**. Kiểm thử `tests/e2e/test_008_docs_entrypoints.py::test_inv002_document_commits_keep_product_code_untouched` (bất biến INV-002 của spec 008: "commit tạo tài liệu không sửa mã sản phẩm hay CI") cần lịch sử commit nên đỏ: lệnh `git` thoát mã 128. Nhánh dự phòng "chỉ kiểm tệp có trên đĩa" **đã bị loại bỏ**: nó không chứng minh INV-002 của 008 nên không được thành PASS.

Hướng đã chốt: dùng cơ chế cổng năng lực của feature 006 (INV-006 của 006): test thiếu năng lực bị **loại khi thu thập, có báo cáo** dạng "bị loại X/Y" kèm lý do — không `skip`/`xfail`, ngưỡng loại 5% không đổi. Mã năng lực `requires_git_history` **đã có** trong bộ cổng năng lực (`tests/unit/capability_gate.py`, commit F022 trên nhánh tích hợp `ai-sdlc/integration` @ffea840): khả dụng khi `git rev-parse --is-inside-work-tree` ở gốc dự án trả mã 0. Còn thiếu đúng hai việc: (1) test chứng minh các nhánh của phép dò đó; (2) gắn dấu năng lực lên test INV-002 của 008.

| # | Việc | Vai | Tệp |
|---|---|---|---|
| W-1 | Test chứng minh cả hai nhánh phép dò + một phép chạy pytest thật trong thư mục không có `.git` | builder | `tests/unit/test_capability_gate.py` |
| W-2 | Gắn dấu `@pytest.mark.requires_git_history` lên đúng một test, thân test giữ nguyên | qa | `tests/e2e/test_008_docs_entrypoints.py` |

Người dùng của feature là **nhà nghiên cứu / kỹ sư dự án** và các vai máy (qa, reviewer, cổng toàn hệ) cần cổng cho kết quả **trung thực**: đỏ khi có lỗi thật, không đỏ vì thiếu năng lực của môi trường, và không xanh giả. Feature không thêm hành vi sản phẩm: chỉ thêm test và một dấu năng lực. Mã `INV-002`, `AC-1`… không kèm "của 008"/"của 006" là mã của **spec này**; mã của spec khác luôn ghi kèm "của 008"/"của 006".

<a id="clarifications"></a>
## Clarifications

- Tự chốt: Số hiệu feature → `009` — lý do: nhánh tích hợp đã có `specs/001`…`specs/008`; số tiếp theo là `009`.
- Tự chốt: Q-0001 và Q-0002 trong khối "Câu trả lời của người dùng" của lượt này → không áp dụng cho feature này: Q-0001 ảnh hưởng `specs/003-ppo-train-repro/spec.md`, Q-0002 ảnh hưởng `specs/006-cross-platform-support/spec.md`; hai câu trả lời đã được ghi đúng khuôn `- Q: … → A: … (người, Q-NNNN)` ở spec bị ảnh hưởng — lý do: không sao chép câu trả lời của người sang spec không bị chúng ảnh hưởng.
- Tự chốt: Mã tiêu chí → giữ nguyên AC-1, AC-2, AC-3 của yêu cầu gốc, không đặt thêm AC; các ràng buộc ("không sửa `pyproject.toml`/`uv.lock`", "không nới 5%", "không đổi test 008 khác", "không nhánh dự phòng PASS") thành bất biến INV-001…INV-003 — lý do: yêu cầu gốc có đúng ba tiêu chí chấp nhận; ràng buộc là điều kiện giữ, không phải kết quả quan sát thêm.
- Tự chốt: Chuỗi lý do của dấu năng lực → đúng `Máy không có lịch sử git` (nguyên văn từ AC-2) — lý do: cổng năng lực bắt buộc lý do tiếng Việt không rỗng, và AC-2 nêu chuỗi này tường minh.
- Tự chốt: Dấu năng lực gắn ở mức hàm test (không ở mức lớp hay mô-đun) — lý do: yêu cầu nói "chỉ gắn marker lên" đúng một test; gắn rộng hơn sẽ loại thêm test 008 khác, trái ràng buộc "không đổi tập test 008 khác".
- Tự chốt: Phép dò đã cố định thư mục chạy `git` theo vị trí tệp của bộ cổng năng lực (gốc dự án), không theo thư mục hiện hành của pytest → test "chạy trong thư mục tạm không có `.git`" MUST dựng một cây tạm có bản sao của bộ cổng năng lực ở đúng vị trí tương đối và chặn việc `git` tự leo lên thư mục cha; cách dựng cụ thể thuộc bước plan (xem `research.md`) — lý do: nếu chỉ đổi thư mục hiện hành thì phép dò vẫn thấy `.git` của dự án thật và test AC-2 sẽ cho kết quả sai (xanh vì không đo gì).
- Tự chốt: AC-3 (`ai-sdlc verify --branch ai-sdlc/integration` xanh) → bằng chứng là lần chạy cổng của máy, không phải test trong repo: không có test nào tự gọi `ai-sdlc verify` — lý do: lệnh đó là cổng của khung điều phối, chạy ngoài repo; kiểm bằng kết quả của chính cổng (hiến chương I).
- Tự chốt: Nếu test W-1 cho thấy phép dò hiện có SAI ở một nhánh → sửa `tests/unit/capability_gate.py` chỉ qua một task riêng có test đỏ-trước-sửa, sau khi test chứng minh lỗi (FR-004) — lý do: yêu cầu cho phép sửa tệp đó "trừ khi test chứng minh lỗi", và hiến chương II đòi test đỏ trước.
- Kết luận phân loại: rà các điểm còn lại, không điểm nào cần người trả lời; không thêm Key Entity, không thêm endpoint hay màn hình, không thêm hành vi sản phẩm — không có quyết định mở rộng phạm vi.

<a id="user-scenarios-testing-mandatory"></a>
## User Scenarios & Testing *(mandatory)*

<a id="user-story-1-phep-do-nang-luc-lich-su-git-duoc-chung-minh-du-cac-nhanh-priority-p1"></a>
### User Story 1 - Phép dò năng lực lịch sử git được chứng minh đủ các nhánh (Priority: P1)

**Tần suất**: hằng ngày — mỗi lượt cổng tests (vai builder/qa/reviewer và cổng máy, nhiều lần mỗi ngày).

Người chạy cổng tests chạy `tests/unit/test_capability_gate.py`. Các test thay `subprocess.run` trong mô-đun cổng năng lực bằng bản giả có kiểm soát để chứng minh `_capability_available("requires_git_history")` trả đúng ở **mọi nhánh**: có git (mã 0) và ba cách không có (mã 128, `OSError`, `TimeoutExpired`). Thêm một test chạy pytest thật trong thư mục không có `.git` để thấy test gắn dấu bị loại có báo cáo.

**Why this priority**: Đây là bằng chứng duy nhất cho phép dò mà cổng toàn hệ dựa vào để quyết định loại test; phép dò sai theo hướng "có git" làm test INV-002 của 008 đỏ lại, sai theo hướng "không có git" làm test bị loại âm thầm ở môi trường có git.

**Independent Test**: Chạy riêng tệp `tests/unit/test_capability_gate.py` ở máy có git và ở bản archive không có `.git`; kiểm xanh ở cả hai, và test chạy pytest thật cho kết quả như nhau ở cả hai máy.

**Acceptance Scenarios**:

1. **Given** `subprocess.run` trong mô-đun cổng năng lực bị thay bằng bản giả trả `returncode == 0`, **When** gọi `_capability_available("requires_git_history")`, **Then** kết quả là `True` (AC-1).
2. **Given** `subprocess.run` bản giả trả `returncode == 128`, **When** gọi phép dò, **Then** kết quả là `False` (AC-2).
3. **Given** `subprocess.run` bản giả ném `OSError` (không có chương trình `git`), **When** gọi phép dò, **Then** kết quả là `False` và không có ngoại lệ thoát ra khỏi phép dò (AC-2).
4. **Given** `subprocess.run` bản giả ném `subprocess.TimeoutExpired`, **When** gọi phép dò, **Then** kết quả là `False`, không có ngoại lệ thoát ra, và lời gọi `subprocess.run` mang hạn mức `timeout` hữu hạn ≤ 5 giây (AC-2).
5. **Given** một thư mục tạm **không có `.git`** chứa một test gắn `@pytest.mark.requires_git_history(reason="Máy không có lịch sử git")` cùng 19 test thường, **When** chạy pytest trong thư mục đó với bộ cổng năng lực, **Then** test gắn dấu **không** chạy (không PASS, không skip, không xfail), báo cáo ghi "bị loại 1/20" kèm tên test, tên dấu `requires_git_history` và lý do `Máy không có lịch sử git`, 19 test thường PASS và phiên thoát mã 0 (AC-2).

---

<a id="user-story-2-test-inv-002-cua-008-mang-dau-nang-luc-than-test-giu-nguyen-priority-p1"></a>
### User Story 2 - Test INV-002 của 008 mang dấu năng lực, thân test giữ nguyên (Priority: P1)

**Tần suất**: hằng ngày — mỗi lượt cổng e2e (vai qa/reviewer và cổng máy).

Người chạy cổng e2e thấy `test_inv002_document_commits_keep_product_code_untouched` chạy **thật** (kiểm lịch sử commit) ở môi trường có git, và bị **loại có báo cáo** ở bản archive không có `.git`. Hàm test chỉ được thêm đúng một decorator; thân hàm và mọi `assert` giữ nguyên.

**Why this priority**: Đây là điểm làm cổng toàn hệ đỏ; sửa nó đúng cách (loại có báo cáo thay vì xanh giả) giữ được độ trung thực của INV-002 của 008 ở nơi chứng minh được nó.

**Independent Test**: Chạy riêng test này ở máy có git (PASS như cũ) và ở bản archive không có `.git` (bị loại, báo cáo nêu lý do); so diff của hàm với bản trước: chỉ thêm một dòng decorator.

**Acceptance Scenarios**:

1. **Given** môi trường có git (`git rev-parse --is-inside-work-tree` thoát mã 0 ở gốc dự án), **When** chạy `test_inv002_document_commits_keep_product_code_untouched`, **Then** test chạy thật (đọc lịch sử commit của `README.md` và `CHANGELOG.md`) và PASS như cũ (AC-1).
2. **Given** bản archive không có `.git`, **When** chạy tests/e2e, **Then** test này bị loại khi thu thập, báo cáo ghi "bị loại" kèm lý do `Máy không có lịch sử git`, không PASS, không skip, không xfail, và nó không làm phiên đỏ (AC-2).
3. **Given** diff của `tests/e2e/test_008_docs_entrypoints.py`, **When** đối chiếu với bản trước, **Then** thay đổi chỉ là một dòng `@pytest.mark.requires_git_history(reason="Máy không có lịch sử git")` đặt trên đúng hàm đó; thân hàm, mọi `assert`, các test khác và `import` giữ nguyên (AC-1).
4. **Given** các test khác của `test_008_docs_entrypoints.py` (kiểm tệp tài liệu, cờ lệnh, liên kết), **When** chạy ở bản archive không có `.git`, **Then** chúng vẫn chạy và PASS như trước — chỉ test INV-002 của 008 bị loại (AC-2).

---

<a id="user-story-3-cong-toan-he-tren-ban-archive-khong-con-do-vi-test-nay-priority-p1"></a>
### User Story 3 - Cổng toàn hệ trên bản archive không còn đỏ vì test này (Priority: P1)

**Tần suất**: hằng ngày — mỗi lượt cổng toàn hệ (`ai-sdlc verify`) trên nhánh tích hợp (cổng máy; người xem kết quả nhiều lần mỗi ngày).

Sau khi hai việc W-1 và W-2 vào nhánh tích hợp, cổng toàn hệ chạy trên bản archive cho kết quả xanh ở cả năm cổng. Báo cáo của lượt nói thẳng giới hạn: INV-002 của 008 chỉ được chứng minh ở môi trường có git.

**Why this priority**: Mục đích cuối của feature — cổng toàn hệ đang đỏ chặn các feature khác; đồng thời tránh ngộ nhận "cổng xanh = INV-002 của 008 đã chứng minh".

**Independent Test**: Chạy `ai-sdlc verify --branch ai-sdlc/integration` trên bản archive không có `.git` và đọc kết quả từng cổng + báo cáo năng lực (`ratio`).

**Acceptance Scenarios**:

1. **Given** nhánh tích hợp đã có W-1 và W-2, **When** chạy `ai-sdlc verify --branch ai-sdlc/integration` trên bản archive không có `.git`, **Then** năm cổng `lint`, `tests`, `typecheck`, `e2e`, `risk_coverage` đều xanh (AC-3).
2. **Given** phiên pytest của cổng `e2e` trên bản archive, **When** đọc báo cáo năng lực, **Then** test INV-002 của 008 nằm trong danh sách bị loại với lý do `Máy không có lịch sử git` và tỉ lệ loại ≤ 5% (AC-2).
3. **Given** bản báo cáo kết quả của lượt, **When** đọc phần giới hạn, **Then** có câu nêu rõ: INV-002 của 008 chỉ được chứng minh ở môi trường có git; cổng toàn hệ trên archive không chứng minh nó (AC-3).

---

<a id="user-story-4-khong-che-loi-khong-noi-nguong-vung-ghi-dung-hai-tep-test-priority-p2"></a>
### User Story 4 - Không che lỗi, không nới ngưỡng, vùng ghi đúng hai tệp test (Priority: P2)

**Tần suất**: hiếm — kiểm một lần mỗi lượt sửa, bởi vai reviewer/challenger.

Reviewer so diff với ràng buộc của yêu cầu: không `skip`/`xfail`/`importorskip` mới, không nhánh dự phòng làm test INV-002 của 008 thành PASS khi thiếu git, ngưỡng 5% không đổi, không đụng `pyproject.toml`/`uv.lock`, không đổi test 008 khác.

**Why this priority**: Hiến chương II cấm giảm test và thêm cơ chế bỏ qua; hiến chương III giới hạn vùng ghi. Vi phạm làm xanh giả đúng ở chỗ feature này sinh ra để chống.

**Independent Test**: Quét diff của lượt sửa bằng `git diff --name-only` và tìm `skip`/`xfail`/`importorskip`; đối chiếu hằng số ngưỡng ở bộ cổng năng lực.

**Acceptance Scenarios**:

1. **Given** diff của lượt sửa, **When** quét hai tệp test, **Then** không có `pytest.skip`, `skipif`, `xfail`, `importorskip` mới và không có nhánh làm test INV-002 của 008 PASS khi thiếu `.git` (INV-001).
2. **Given** diff của lượt sửa, **When** liệt kê tệp đổi, **Then** chỉ gồm `tests/unit/test_capability_gate.py`, `tests/e2e/test_008_docs_entrypoints.py` và tệp thuộc `specs/009-git-history-capability/` + bằng chứng; không có `pyproject.toml`, `uv.lock` (INV-002, INV-003).
3. **Given** giá trị ngưỡng loại mặc định của bộ cổng năng lực, **When** đối chiếu với trước feature, **Then** vẫn là 0,05 (5%) (INV-003).

---

<a id="edge-cases"></a>
### Edge Cases

- Không cài chương trình `git` trên máy (`OSError`/`FileNotFoundError`): phép dò trả `False`, test INV-002 của 008 bị loại có báo cáo, không đỏ. (AC-2)
- `git` treo hoặc chậm quá hạn mức 5 giây (`TimeoutExpired`): phép dò trả `False`, không treo cổng. (AC-2, NFR-REL-001)
- Thư mục dự án nằm trong thư mục khác là một cây làm việc git (ví dụ giải nén archive vào bên trong một kho khác): `git rev-parse --is-inside-work-tree` thoát 0, phép dò trả `True`, test chạy thật trên lịch sử của kho cha và có thể đỏ vì lý do thật; phép dò không phân biệt được hai kho — đây là giới hạn ghi nhận, không che. (AC-1)
- Bản sao nông (shallow clone) hoặc kho chưa có commit: `rev-parse` thoát 0 nên test chạy thật; nếu lịch sử thiếu thì test đỏ với lý do thật, không bị loại. Giới hạn ghi nhận, không che. (AC-1)
- Test AC-2 chạy pytest trong thư mục tạm: phép dò cố định thư mục chạy `git` ở gốc dự án theo vị trí bộ cổng năng lực, nên test phải dựng cây tạm và chặn `git` leo lên thư mục cha, nếu không sẽ đo nhầm `.git` của dự án thật. (AC-2)
- Chạy một mình một tệp có ít hơn 20 test thu thập mà có 1 test bị loại: tỉ lệ vượt 5% ⇒ phiên đỏ theo thiết kế của cổng năng lực (NFR-GATE-001), không phải lỗi của feature; cổng chạy cả thư mục `tests/e2e` nên mẫu số đủ lớn. (AC-2)
- Dấu năng lực thiếu `reason` hoặc `reason` rỗng: lỗi thu thập (UsageError) theo cổng năng lực của 006; vì vậy dấu của W-2 MUST kèm lý do không rỗng. (AC-2)
- Test dùng bản giả `subprocess.run` không được để lại thay đổi toàn cục sau khi test kết thúc (khôi phục sau mỗi test). (INV-001)
- Số test trong `tests/unit/test_capability_gate.py` và trong `tests/e2e/test_008_docs_entrypoints.py` không được giảm. (INV-001)

<a id="requirements-mandatory"></a>
## Requirements *(mandatory)*

<a id="functional-requirements"></a>
### Functional Requirements

- **FR-001**: Bộ test của `tests/unit/test_capability_gate.py` MUST chứng minh `_capability_available("requires_git_history")` trả `True` khi `subprocess.run` (thay bằng bản giả trong mô-đun `capability_gate`) trả `returncode == 0`. (AC-1)
- **FR-002**: Bộ test đó MUST chứng minh phép dò trả `False` — và không để ngoại lệ thoát ra — ở ba nhánh: `returncode == 128`, `OSError`, `subprocess.TimeoutExpired`; và MUST kiểm lời gọi `subprocess.run` mang `timeout` hữu hạn ≤ 5 giây. (AC-2)
- **FR-003**: Bộ test đó MUST có một test chạy pytest thật (tiến trình con) trong thư mục tạm **không có `.git`**, cho thấy test gắn `requires_git_history` bị loại khi thu thập — báo cáo dạng "bị loại X/Y" (đúng `1/20` ở cấu hình 1 test gắn dấu + 19 test thường), ghi tên test, tên dấu và lý do `Máy không có lịch sử git`; test đó không PASS, không skip, không xfail; 19 test thường PASS; phiên thoát mã 0 vì tỉ lệ 5% không vượt ngưỡng. (AC-2)
- **FR-004**: `tests/unit/capability_gate.py` MUST NOT bị đổi trừ khi một test của FR-001…FR-003 chứng minh lỗi của nó; khi đó việc sửa MUST đi qua một task riêng, có test đỏ trước sửa, ghi nguyên nhân gốc. (AC-1, AC-2)
- **FR-005**: `test_inv002_document_commits_keep_product_code_untouched` trong `tests/e2e/test_008_docs_entrypoints.py` MUST mang dấu `@pytest.mark.requires_git_history(reason="Máy không có lịch sử git")` — đúng một decorator thêm vào, ở mức hàm. (AC-1, AC-2)
- **FR-006**: Thân hàm và mọi `assert` của test đó, cùng mọi test khác trong tệp, MUST giữ nguyên; ở môi trường có git phép kiểm lịch sử thật MUST vẫn chạy và PASS như cũ. (AC-1)
- **FR-007**: Feature MUST NOT thêm `pytest.skip`, `skipif`, `xfail`, `importorskip` hay bất kỳ nhánh nào làm test INV-002 của 008 PASS khi thiếu lịch sử git (kể cả nhánh "chỉ kiểm tệp có trên đĩa"); việc không chạy được MUST là "bị loại có báo cáo". (AC-2)
- **FR-008**: Ở bản archive không có `.git`, test INV-002 của 008 MUST bị loại với lý do `Máy không có lịch sử git` và tỉ lệ loại của phiên MUST ≤ 5% mà không đổi ngưỡng. (AC-2)
- **FR-009**: Sau khi W-1 và W-2 vào nhánh tích hợp, `ai-sdlc verify --branch ai-sdlc/integration` MUST xanh ở `lint`, `tests`, `typecheck`, `e2e`, `risk_coverage` trên bản archive không có `.git`. (AC-3)
- **FR-010**: Báo cáo của lượt (QA/review) MUST ghi rõ giới hạn: INV-002 của 008 chỉ được chứng minh ở môi trường có git; cổng toàn hệ trên bản archive không chứng minh nó. (AC-2, AC-3)
- **FR-011**: Vùng ghi của feature MUST là `tests/unit/test_capability_gate.py` (builder) và `tests/e2e/test_008_docs_entrypoints.py` (qa), cộng tệp spec/bằng chứng của chính feature; MUST NOT đổi `pyproject.toml`, `uv.lock`, ngưỡng 5%, hay tập test 008 khác. (AC-3)

<a id="yeu-cau-phi-chuc-nang-non-functional-requirements"></a>
### Yêu cầu phi chức năng (Non-Functional Requirements)

- **NFR-REL-001**: Phép dò năng lực không làm treo cổng.
  Ngưỡng: lời gọi `git` của phép dò có hạn mức ≤ 5 giây; ở mọi nhánh lỗi (`OSError`, `TimeoutExpired`, mã ≠ 0) phép dò trả `False` trong ≤ 5 giây, 0 ngoại lệ thoát ra.
  Đo bằng: test của FR-002 (bản giả `subprocess.run` ném lỗi; kiểm đối số `timeout` ≤ 5). (AC-2)
- **NFR-GATE-001**: Tỉ lệ loại theo năng lực không vượt ngưỡng của 006.
  Ngưỡng: tỉ lệ test bị loại ≤ 5% (0,05) trên mỗi phiên cổng `tests` và `e2e` ở bản archive không có `.git`; mẫu số của phiên ≥ 20 test thu thập.
  Đo bằng: `pytest --capability-report=<tệp>` rồi đọc trường `ratio`; test FR-003 kiểm `ratio` == 0,05 cho cấu hình 1/20. (AC-2)
- **NFR-QUAL-001**: Chất lượng mã kiểm thử.
  Ngưỡng: `ruff check` và `mypy --strict` xanh (0 lỗi) trên hai tệp đã sửa.
  Đo bằng: cổng `lint` (`uv run --isolated --with ruff ruff check .`) và cổng `typecheck` (`uv run --isolated --with mypy mypy --strict .`). (AC-3)

<a id="bat-bien-invariants"></a>
### Bất biến (Invariants)

- **INV-001**: Không che lỗi bằng test: MUST NOT thêm `skip`/`skipif`/`xfail`/`importorskip` và MUST NOT thêm nhánh dự phòng làm test INV-002 của 008 PASS khi thiếu lịch sử git; số test của hai tệp MUST NOT giảm; bản giả `subprocess.run` MUST được khôi phục sau mỗi test (kế thừa INV-006 của 006). (AC-2)
- **INV-002**: Thân hàm và các `assert` của test INV-002 của 008, cùng mọi test khác của `tests/e2e/test_008_docs_entrypoints.py`, MUST giữ nguyên; thay đổi duy nhất của tệp đó là một dòng decorator. (AC-1, AC-2)
- **INV-003**: Ngưỡng loại 5% của cổng năng lực, `pyproject.toml` và `uv.lock` MUST giữ nguyên. (AC-3)

<a id="success-criteria-mandatory"></a>
## Success Criteria *(mandatory)*

<a id="measurable-outcomes"></a>
### Measurable Outcomes

- **SC-001**: Ở môi trường có git, test INV-002 của 008 chạy thật và PASS: 1/1 lần, không bị loại (0 test bị loại vì `requires_git_history`). (AC-1)
- **SC-002**: Ở bản archive không có `.git`, đúng 1 test (INV-002 của 008) bị loại vì `requires_git_history`, báo cáo ghi lý do `Máy không có lịch sử git`, tỉ lệ loại ≤ 5%, 0 test PASS giả, 0 skip, 0 xfail. (AC-2)
- **SC-003**: `ai-sdlc verify --branch ai-sdlc/integration` xanh ở 5/5 cổng (`lint`, `tests`, `typecheck`, `e2e`, `risk_coverage`). (AC-3)
- **SC-004**: Phép dò được chứng minh ở 4/4 nhánh (mã 0, mã 128, `OSError`, `TimeoutExpired`) bằng test tự động, cộng 1 phép chạy pytest thật không có `.git`. (AC-1, AC-2)
- **SC-005**: `git diff --name-only` chỉ chứa hai tệp test, tệp của feature và bằng chứng; 0 thay đổi ở `pyproject.toml`, `uv.lock`, `tests/unit/capability_gate.py` (trừ khi FR-004 kích hoạt). (AC-3)
- **SC-006**: Báo cáo của lượt có câu giới hạn của FR-010. (AC-3)

<a id="out-of-scope"></a>
## Out of Scope

- Sửa `pyproject.toml` hoặc `uv.lock`.
- Nới ngưỡng loại 5% của cổng năng lực.
- Đổi tập test 008 khác, hay đổi thân hàm/assert của test INV-002 của 008.
- Nhánh dự phòng "chỉ kiểm tệp có trên đĩa" hay bất kỳ cách nào làm test INV-002 của 008 thành PASS khi không có lịch sử git; `skip`/`xfail`/`importorskip`.
- Đổi `tests/unit/capability_gate.py`, trừ khi test của feature chứng minh lỗi (FR-004).
- Chứng minh INV-002 của 008 trên bản archive không có `.git` (không thể; giới hạn ghi ở FR-010).
- Thêm hành vi sản phẩm, màn hình, endpoint hay thực thể dữ liệu mới; phân biệt kho git cha với kho của dự án (xem Edge Cases).

<a id="assumptions"></a>
## Assumptions

- Mã nguồn của cổng năng lực (`tests/unit/capability_gate.py`, `conftest.py` có `pytest_plugins = ["capability_gate"]`) và hai tệp test nằm trên nhánh tích hợp `ai-sdlc/integration` (@ffea840); nhánh hiện hành chỉ có `specs/`, `docs/`, nên việc viết và chạy test diễn ra ở worktree của task trên nhánh tích hợp.
- Phép dò hiện có dùng `git rev-parse --is-inside-work-tree` với `timeout=5` và `cwd` là gốc dự án (hai cấp trên `tests/unit/capability_gate.py`); spec này dựa vào hành vi đó, không đặc tả lại.
- Cổng `e2e` và `tests` chạy cả thư mục (không chạy riêng một tệp), nên mẫu số thu thập ≥ 20 và 1 test bị loại không vượt 5%; con số mẫu số thực chưa đo trong lượt đặc tả này (CHƯA KIỂM) và là việc đo của bước plan/QA.
- Bản archive của cổng không có `.git` và không nằm trong một cây làm việc git khác; điều này chưa được xác nhận bằng đo ở lượt đặc tả (CHƯA KIỂM).
