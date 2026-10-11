---
id: "SPEC-007"
title: "Sửa gốc 2 test hiển thị/tiến trình làm đỏ cổng tests — Spec"
doc_type: spec
owner_agent: spec
status: draft
updated: "2026-10-11"
feature: "007-stabilize-viewer-tests"
version: "1.1.0"
---

# Feature Specification: Sửa gốc 2 test hiển thị/tiến trình làm đỏ cổng tests

- [Bối cảnh (Context)](#boi-canh-context)
- [Clarifications](#clarifications)
- [User Scenarios & Testing *(mandatory)*](#user-scenarios-testing-mandatory)
  - [User Story 1 - Kiểm thử viewer thật cho kết quả tất định ở cả hai môi trường (Priority: P1)](#user-story-1-kiem-thu-viewer-that-cho-ket-qua-tat-dinh-o-ca-hai-moi-truong-priority-p1)
  - [User Story 2 - Kiểm thử tiến trình View3D tách riêng không chập chờn khi máy bận (Priority: P1)](#user-story-2-kiem-thu-tien-trinh-view3d-tach-rieng-khong-chap-chon-khi-may-ban-priority-p1)
  - [User Story 3 - Nguyên nhân thật được đo và ghi lại, không đoán (Priority: P1)](#user-story-3-nguyen-nhan-that-duoc-do-va-ghi-lai-khong-doan-priority-p1)
  - [User Story 4 - Không che lỗi, không nới nghiệm thu, `src/` chỉ đổi khi đo chứng minh (Priority: P1)](#user-story-4-khong-che-loi-khong-noi-nghiem-thu-src-chi-doi-khi-do-chung-minh-priority-p1)
  - [Edge Cases](#edge-cases)
- [Requirements *(mandatory)*](#requirements-mandatory)
  - [Functional Requirements](#functional-requirements)
  - [Yêu cầu phi chức năng (Non-Functional Requirements)](#yeu-cau-phi-chuc-nang-non-functional-requirements)
  - [Bất biến (Invariants)](#bat-bien-invariants)
- [Success Criteria *(mandatory)*](#success-criteria-mandatory)
  - [Measurable Outcomes](#measurable-outcomes)
- [Out of Scope](#out-of-scope)
- [Assumptions](#assumptions)


**Feature Branch**: `007-stabilize-viewer-tests` (tên thư mục feature; không tạo nhánh git mới)

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "Sửa gốc 2 test hiển thị/tiến trình đang làm đỏ cổng tests trên nhánh tích hợp" — nguồn: `docs/00-input/fast-run-20261011-36c037.md` (qua `request.link`).

<a id="boi-canh-context"></a>
## Bối cảnh (Context)

Cổng tests trên nhánh tích hợp đang đỏ vì hai kiểm thử tích hợp cho lớp hiển thị. Hai kiểm thử này bảo vệ các tiêu chí đã nghiệm thu của hai feature đã có: `005-replay-3d-muscle-demo` (phát lại 3D bằng MuJoCo Viewer thật) và `003-ppo-train-repro` (cửa sổ 3D chạy ở tiến trình riêng, tắt được mà không ảnh hưởng huấn luyện). Hai lần giao việc sửa trước (F006, F007) không để lại thay đổi nào: một lần bị đẩy lại để lập kế hoạch, một lần đỏ.

| # | Kiểm thử | Triệu chứng quan sát được ở cổng |
|---|---|---|
| T-A | `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` | Nhánh "có màn hình" chạy `python -m mma_ai.visualization.cli --episode … --config …` rồi quá hạn 25 s (`subprocess.TimeoutExpired`). |
| T-B | `tests/integration/test_viewer3d_train.py::test_view3d_process_separate` | `Process MMA-AI-View3D … .pid is None`: tiến trình View3D chưa khởi chạy tại thời điểm kiểm; chập chờn khi máy bận. |

Người dùng của feature này là **nhà nghiên cứu / kỹ sư dự án** (và các vai máy: qa, reviewer) cần cổng tests cho kết quả **tin được và lặp lại được**. Feature không thêm hành vi sản phẩm nào: nó làm cho phép kiểm đo đúng hành vi đã nghiệm thu, một cách tất định. Mọi bước chẩn đoán dựa trên mã/nhật ký thật; không giả định nguyên nhân khi chưa đo (hiến chương I, II).

<a id="clarifications"></a>
## Clarifications

- Tự chốt: Số hiệu feature → `007`, không phải `006` — lý do: nhánh tích hợp đã có `specs/006-cross-platform-support` (chưa có trên nhánh hiện hành); dùng `007` để hai thư mục không trùng khi gộp.
- Tự chốt: Vùng ghi sau khi gộp T705/T706 → sửa INV-003/FR-007/SC-005 từ "đúng hai tệp kiểm thử, 0 thay đổi `src/`" thành "hai tệp integration + một tệp e2e mới; `src/` chỉ đổi ở `src/mma_ai/visualization/viewer.py` khi đo chứng minh nguyên nhân ở đó (AC-5)"; AC/FR khác giữ nguyên — lý do: mã đã gộp có `tests/e2e/test_007_viewer_entrypoint.py` (T705) và bản sửa gốc `viewer.py` (T706, nguyên nhân T-A đo ở `ViewerSink.show`, verdict T704 F-001/F-005); giữ câu cũ sẽ mâu thuẫn với diff thật.
- Tự chốt: Mã tiêu chí → yêu cầu gốc không đánh mã AC; tự đặt AC-1…AC-5 theo năm điều kiện của yêu cầu (hai kiểm thử, nguyên nhân thật, không nới nghiệm thu, dừng nếu nguyên nhân ở `src/`). Các mã AC-1, AC-2, FR-011, FR-014 **của 005** luôn được viết kèm "của 005" hoặc "005 AC-n" để không lẫn với AC-n của feature này.
- Tự chốt: Q-0001 và Q-0002 trong khối "Câu trả lời của người dùng" của lượt này → không áp dụng cho feature này: Q-0001 đã được ghi ở `specs/003-ppo-train-repro/spec.md` và `specs/005-replay-3d-muscle-demo/spec.md`; Q-0002 thuộc `specs/006-cross-platform-support`, thư mục này không tồn tại ở nhánh hiện hành — lý do: không sao chép câu trả lời của người sang spec không bị chúng ảnh hưởng.
- Tự chốt: Hai kiểm thử là hai nguyên nhân độc lập → xử lý riêng từng kiểm thử, bằng chứng riêng; không giả định chung gốc — lý do: triệu chứng khác nhau (quá hạn vs. `pid is None`).
- Tự chốt: "Chạy nhiều lần" → mỗi kiểm thử được chạy riêng từng cái, lặp lại tới ngưỡng NFR-REL-001; mỗi lượt làm việc của builder chỉ chạy 1–2 lần (giới hạn thời gian của yêu cầu), số lần còn lại gom qua các lượt và ghi nối tiếp vào bằng chứng — lý do: yêu cầu đòi cả hai (nhiều lần để thấy chập chờn, nhưng 1–2 lần mỗi lượt để không quá thời gian).
- Tự chốt: Thế nào là "nhánh đúng theo `display_available()`" → hàm `display_available()` của lớp hiển thị là nguồn sự thật duy nhất để kiểm thử chọn nhánh (có màn hình / không màn hình); kiểm thử không tự suy diễn từ biến môi trường theo cách riêng — lý do: yêu cầu nêu đúng tên hàm này.
- Tự chốt: Khi đo cho thấy `display_available()` báo "có màn hình" nhưng viewer thật không khởi tạo/không kết thúc được (ví dụ GLFW khởi tạo được nhưng không tạo được cửa sổ GL) → đó là khoảng trống của mã nguồn so với 005 FR-011 ("có biến hiển thị nhưng viewer không khởi tạo được ⇒ xử lý như không có màn hình"), thuộc `src/` ⇒ áp dụng AC-5 (DỪNG và báo), không dùng việc né ở kiểm thử để che — lý do: yêu cầu cấm sửa `src/` và cấm xfail/skip/nới nghiệm thu.
- Kết luận phân loại: rà các điểm còn lại, không điểm nào cần người trả lời; không thêm Key Entity, không thêm endpoint hay màn hình, không thêm hành vi sản phẩm — đây là sửa kiểm thử nên không có quyết định mở rộng phạm vi.

<a id="user-scenarios-testing-mandatory"></a>
## User Scenarios & Testing *(mandatory)*

<a id="user-story-1-kiem-thu-viewer-that-cho-ket-qua-tat-dinh-o-ca-hai-moi-truong-priority-p1"></a>
### User Story 1 - Kiểm thử viewer thật cho kết quả tất định ở cả hai môi trường (Priority: P1)

**Tần suất**: hằng ngày — mỗi lượt cổng tests chạy trên nhánh tích hợp (vai qa/reviewer và nhà nghiên cứu, nhiều lần mỗi ngày).

Người chạy cổng tests chạy `test_real_viewer_plays_or_reports_no_display`. Kiểm thử chọn nhánh theo `display_available()`: có cửa sổ dùng được thì chạy viewer thật và phải kết thúc đúng hạn với đủ khẳng định nghiệm thu; không có thì kiểm đường lỗi không màn hình. Không có lần chạy nào treo tới quá hạn mà không có chẩn đoán.

**Why this priority**: Đây là bằng chứng nghiệm thu máy duy nhất của 005 AC-1/AC-2 trên viewer thật; đỏ ở đây chặn cổng tests của nhánh tích hợp.

**Independent Test**: Chạy riêng kiểm thử này một lần trên máy có màn hình dùng được và một lần trên môi trường không có màn hình; kiểm kết quả xanh, thời gian chạy trong hạn, và các khẳng định nguyên văn còn nguyên.

**Acceptance Scenarios**:

1. **Given** môi trường có cửa sổ GL dùng được (`display_available()` cho `available=True`), **When** chạy kiểm thử, **Then** lệnh `python -m mma_ai.visualization.cli --episode … --config …` kết thúc trong hạn mức khai tường minh của kiểm thử, thoát mã 0 và in đủ các mục "Tóm tắt phiên phát lại:", "Thời lượng mô phỏng=", "Thời gian thực=", "Tỷ lệ tốc độ=", "Số khung trễ=" (005 AC-1, AC-2, FR-001, FR-004, FR-005, FR-014). (AC-1)
2. **Given** môi trường không có màn hình dùng được (`display_available()` cho `available=False`), **When** chạy kiểm thử, **Then** lệnh thoát mã 7 trong ≤ 5 s, thông báo tiếng Việt có gợi ý `--headless` và nêu nguyên nhân màn hình/hiển thị (005 FR-011). (AC-1)
3. **Given** kiểm thử chạy lặp lại trên cùng một máy, **When** chạy tới số lần của NFR-REL-001, **Then** kết quả như nhau ở mọi lần: không lần nào quá hạn 25 s mà không kèm thông tin chẩn đoán. (AC-1)
4. **Given** lệnh con không kết thúc trong hạn, **When** hạn mức hết, **Then** kiểm thử dừng lệnh con, không để tiến trình mồ côi, và báo lỗi nêu lệnh, hạn mức, đầu ra đã thu được — kiểm thử đỏ có chẩn đoán chứ không treo. (AC-1)

---

<a id="user-story-2-kiem-thu-tien-trinh-view3d-tach-rieng-khong-chap-chon-khi-may-ban-priority-p1"></a>
### User Story 2 - Kiểm thử tiến trình View3D tách riêng không chập chờn khi máy bận (Priority: P1)

**Tần suất**: hằng ngày — mỗi lượt cổng tests, kể cả khi máy đang chạy nhiều việc song song.

Người chạy cổng tests chạy `test_view3d_process_separate`. Kiểm thử chờ tiến trình View3D thực sự khởi chạy, trong một hạn mức rõ rệt, rồi mới khẳng định nó có PID riêng, đang sống, và việc tắt nó không ảnh hưởng tiến trình quan sát hay huấn luyện.

**Why this priority**: Bảo vệ yêu cầu "cửa sổ 3D chạy ở tiến trình riêng, tắt được mà không ảnh hưởng huấn luyện" của 003; kết quả chập chờn làm mất niềm tin vào mọi lần đỏ khác của cổng.

**Independent Test**: Chạy riêng kiểm thử nhiều lần liên tiếp, trong đó có lượt chạy cùng lúc với tải CPU nền; kiểm xanh ở mọi lần.

**Acceptance Scenarios**:

1. **Given** lệnh quan sát được chạy với `--view3d`, **When** kiểm thử chờ tiến trình View3D khởi chạy, **Then** nó chờ có hạn mức khai tường minh cho tới khi tiến trình có PID, rồi khẳng định đúng 1 tiến trình, PID khác PID của tiến trình hiện tại, và tiến trình đang sống (003 FR-022). (AC-2)
2. **Given** máy đang bận (tải CPU nền), **When** chạy kiểm thử, **Then** kết quả vẫn xanh: việc kiểm PID không còn phụ thuộc tiến trình đã được khởi chạy xong hay chưa tại một thời điểm cố định. (AC-2)
3. **Given** tiến trình View3D bị `terminate()` giữa chừng, **When** kiểm thử tiếp tục, **Then** tiến trình dừng, `ui.json` còn nguyên, luồng quan sát dừng sạch bằng `stop_event` (003 INV-005). (AC-2)
4. **Given** tiến trình View3D thật sự không bao giờ khởi chạy trong hạn mức, **When** hạn mức hết, **Then** kiểm thử đỏ với thông báo nêu rõ "không khởi chạy được trong hạn mức", không phải lỗi `pid is None` mơ hồ. (AC-2)

---

<a id="user-story-3-nguyen-nhan-that-duoc-do-va-ghi-lai-khong-doan-priority-p1"></a>
### User Story 3 - Nguyên nhân thật được đo và ghi lại, không đoán (Priority: P1)

**Tần suất**: hiếm — một lần cho mỗi lần cổng đỏ vì hai kiểm thử này; người thực hiện là vai builder.

Người sửa chạy riêng từng kiểm thử, nhiều lần, ghi lại bằng chứng (lệnh, số lần chạy, kết quả, thời gian, đầu ra lỗi) và kết luận nguyên nhân cho từng kiểm thử trước khi sửa.

**Why this priority**: Hai lần sửa trước không có kết quả; sửa theo phỏng đoán là cách tái diễn vòng lặp đỏ.

**Independent Test**: Đọc báo cáo của lượt làm việc: mỗi kiểm thử có mục nguyên nhân kèm số lần chạy và kết quả đo; lệnh trong báo cáo chạy lại được và cho kết quả như đã ghi.

**Acceptance Scenarios**:

1. **Given** kiểm thử T-A đỏ, **When** người sửa chạy riêng nó, **Then** báo cáo nêu nguyên nhân thật của lần quá hạn (đo được: lệnh con dừng ở bước nào, thời gian từng bước) kèm số lần chạy và kết quả. (AC-3)
2. **Given** kiểm thử T-B chập chờn, **When** người sửa chạy riêng nó nhiều lần (kể cả khi máy bận), **Then** báo cáo nêu nguyên nhân thật của `pid is None` kèm số lần chạy, tỷ lệ đỏ trước sửa và tỷ lệ đỏ sau sửa. (AC-3)
3. **Given** nguyên nhân đã chốt, **When** đối chiếu với diff, **Then** thay đổi tác động đúng nguyên nhân đó, không phải một cách né triệu chứng. (AC-3)

---

<a id="user-story-4-khong-che-loi-khong-noi-nghiem-thu-src-chi-doi-khi-do-chung-minh-priority-p1"></a>
### User Story 4 - Không che lỗi, không nới nghiệm thu, `src/` chỉ đổi khi đo chứng minh (Priority: P1)

**Tần suất**: hiếm — kiểm một lần cho mỗi lượt sửa, bởi vai reviewer/challenger.

Reviewer so diff với nghiệm thu gốc: các khẳng định còn nguyên, không skip/xfail mới, vùng ghi đúng như khai ở FR-007 (hai tệp kiểm thử integration, một tệp e2e mới, `src/` chỉ đổi ở `viewer.py` khi đo chứng minh). Nếu nguyên nhân nằm ở `src/`, kiểm thử không được che bằng việc sửa kiểm thử: báo nguyên nhân kèm bằng chứng, và chỉ một task sửa gốc riêng, có kiểm thử đỏ-trước-sửa, mới được đổi `src/` (AC-5).

**Why this priority**: Hiến chương II cấm giảm test và thêm cơ chế bỏ qua; hiến chương III giới hạn vùng ghi; vi phạm làm xanh giả.

**Independent Test**: So diff của lượt sửa với danh sách khẳng định nghiệm thu của spec này (FR-004) và vùng ghi của task; chạy quét `skip`/`xfail` trên hai tệp.

**Acceptance Scenarios**:

1. **Given** diff của lượt sửa, **When** quét hai tệp kiểm thử, **Then** không có `skip`, `skipif`, `xfail` hay `pytest.importorskip` mới; các khẳng định của 005 AC-1/AC-2, 005 FR-001/FR-004/FR-005/FR-011/FR-014 và khẳng định tách tiến trình của 003 có mặt nguyên văn hoặc chặt hơn. (AC-4)
2. **Given** diff của lượt sửa, **When** so với vùng ghi khai ở FR-007, **Then** các tệp kiểm thử bị đổi chỉ gồm `tests/integration/test_replay_viewer_real.py`, `tests/integration/test_viewer3d_train.py`, tệp e2e mới `tests/e2e/test_007_viewer_entrypoint.py` và (khi sửa gốc ở `src/`) `tests/unit/test_viewer.py`; tệp trong `src/` chỉ có thể là `src/mma_ai/visualization/viewer.py`, kèm bằng chứng đo ở báo cáo. (AC-4, AC-5)
3. **Given** phép đo cho thấy nguyên nhân của một kiểm thử nằm ở `src/`, **When** người sửa kết luận, **Then** lượt làm việc dừng việc sửa kiểm thử đó, không đổi `src/`, và báo cáo nêu nguyên nhân (tệp, hàm, bằng chứng đo) cùng đề xuất sửa để người/vai khác quyết. (AC-5)
4. **Given** nguyên nhân của một kiểm thử nằm ở `src/` còn kiểm thử kia ở chính kiểm thử, **When** kết thúc lượt, **Then** kiểm thử nằm ở chính nó vẫn được sửa và chứng minh; kiểm thử nằm ở `src/` được ghi là "còn đỏ vì nguyên nhân ở `src/`" kèm bằng chứng — không bị che. (AC-5)

---

<a id="edge-cases"></a>
### Edge Cases

- Môi trường có `DISPLAY` đặt nhưng không có cửa sổ GL dùng được (GLFW khởi tạo được, tạo cửa sổ/ngữ cảnh GL thì không): kiểm thử không được treo; nếu `display_available()` cho `available=True` mà lệnh con không kết thúc, kết quả phải là lỗi có chẩn đoán trong hạn, và việc đó thuộc AC-5 nếu gốc ở `src/`. (AC-5)
- Lệnh con viewer thật không kết thúc và còn để lại tiến trình/cửa sổ: kiểm thử dừng và dọn tiến trình đó trước khi báo lỗi, để lần chạy sau không bị ảnh hưởng. (AC-1)
- Nhánh không màn hình được cưỡng bức bằng môi trường cách ly (`test_real_viewer_forced_no_display_reports_code_7`): vẫn xanh và không đổi. (AC-1)
- Hạn mức chờ tiến trình View3D phải đủ rộng cho máy bận nhưng hữu hạn; không được là vòng lặp vô hạn hay chờ không điều kiện. (AC-2)
- Tiến trình View3D tồn tại nhưng đã thoát trước khi kiểm `is_alive()`: kiểm thử báo rõ "đã thoát sớm" kèm mã thoát, không báo `pid is None`. (AC-2)
- Phần kiểm huấn luyện thật của T-B (khi có `torch`) chạy sau phần tiến trình tách riêng: giữ nguyên và không bị tiến trình/luồng còn sót lại của phần trước ảnh hưởng. (AC-2)
- Chạy một mình, chạy cùng cả bộ test, và chạy lặp: kết quả như nhau; kiểm thử không phụ thuộc thứ tự chạy hay trạng thái còn lại của lần trước. (AC-3)
- Kết quả đo ở máy có màn hình dùng được không suy ra cho cổng không có màn hình (và ngược lại): báo cáo ghi rõ môi trường đã đo; môi trường chưa đo ghi "CHƯA KIỂM". (AC-3)
- Việc sửa không được làm giảm số kiểm thử trong hai tệp. (INV-001)
- Kiểm thử không ghi tệp ngoài `tmp_path` và không đổi trạng thái toàn cục của tiến trình pytest sau khi kết thúc. (INV-002)

<a id="requirements-mandatory"></a>
## Requirements *(mandatory)*

<a id="functional-requirements"></a>
### Functional Requirements

- **FR-001**: Kiểm thử `test_real_viewer_plays_or_reports_no_display` MUST chọn nhánh theo `display_available()` và MUST cho kết quả xanh tất định ở cả hai nhánh: có màn hình (lệnh `python -m mma_ai.visualization.cli --episode … --config …` kết thúc trong hạn mức khai tường minh, mã 0, đủ các mục tóm tắt tiếng Việt) và không màn hình (mã 7 trong ≤ 5 s, thông báo tiếng Việt kèm `--headless`). (AC-1)
- **FR-002**: Mọi lệnh con mà hai kiểm thử khởi chạy MUST có hạn mức thời gian hữu hạn khai tường minh; khi quá hạn kiểm thử MUST dừng và dọn lệnh con, và MUST báo lỗi nêu lệnh, hạn mức và đầu ra đã thu được thay vì treo hoặc ném `TimeoutExpired` trần. (AC-1)
- **FR-003**: Kiểm thử `test_view3d_process_separate` MUST chờ tiến trình View3D khởi chạy (có PID) trong một hạn mức hữu hạn khai tường minh trước khi khẳng định PID, thay vì kiểm `pid` ngay sau khi tiến trình được tạo; khi hết hạn mà chưa khởi chạy, MUST báo lỗi nêu rõ nguyên nhân là "không khởi chạy được trong hạn mức". (AC-2)
- **FR-004**: Mọi khẳng định nghiệm thu hiện có MUST còn nguyên hoặc chặt hơn: 005 AC-1, AC-2, FR-001, FR-004, FR-005, FR-011, FR-014 (kể cả mã thoát 0, các mục tóm tắt tiếng Việt, mã thoát 7 trong ≤ 5 s, gợi ý `--headless`) và, ở T-B, đúng 1 tiến trình View3D, PID khác PID chính, tiến trình đang sống, `terminate()` không làm mất `ui.json`, huấn luyện thật với `--view3d` vẫn mã 0 và có `latest.json` (003 FR-022, INV-005). (AC-4)
- **FR-005**: Nguyên nhân thật của từng kiểm thử MUST được xác định bằng cách chạy riêng từng kiểm thử nhiều lần và MUST được ghi lại cùng bằng chứng (lệnh, số lần chạy, kết quả, thời gian, đầu ra lỗi, môi trường đo) trước khi sửa; bản sửa MUST tác động đúng nguyên nhân đã ghi. (AC-3)
- **FR-006**: Bản sửa MUST NOT dùng `skip`, `skipif`, `xfail`, `importorskip` mới hay bất kỳ cơ chế bỏ qua nào để che lỗi, và MUST NOT làm giảm số kiểm thử hay nới ngưỡng của khẳng định nghiệm thu. Dấu `pytest.mark.display` đã có trên T-A giữ nguyên. (AC-4)
- **FR-007**: Vùng sửa của feature MUST gồm hai tệp integration `tests/integration/test_replay_viewer_real.py` và `tests/integration/test_viewer3d_train.py` cộng một tệp e2e mới `tests/e2e/test_007_viewer_entrypoint.py` (QA, chạy trên entrypoint thật). `src/` MUST NOT bị đổi, TRỪ `src/mma_ai/visualization/viewer.py` (kèm ca thử đơn vị `tests/unit/test_viewer.py`) và CHỈ khi phép đo chứng minh nguyên nhân của kiểm thử nằm ở đó. Khi đo cho thấy nguyên nhân của một kiểm thử nằm ở `src/`, task sửa kiểm thử đó MUST dừng, MUST NOT sửa `src/`, và MUST báo nguyên nhân (tệp, hàm, bằng chứng đo, đề xuất) trong báo cáo; việc sửa `src/` thuộc một task sửa gốc riêng. (AC-4, AC-5)
- **FR-008**: Thông báo lỗi do kiểm thử sinh ra MUST bằng tiếng Việt, nêu giá trị và ngữ cảnh (lệnh, hạn mức, mã thoát, đầu ra), cùng văn phong với các kiểm thử hiện có. (AC-1, AC-2)

<a id="yeu-cau-phi-chuc-nang-non-functional-requirements"></a>
### Yêu cầu phi chức năng (Non-Functional Requirements)

- **NFR-REL-001**: Tính tất định của hai kiểm thử sau khi sửa.
  Ngưỡng: mỗi kiểm thử, chạy riêng từng cái, xanh 5/5 lần liên tiếp trên cùng môi trường đo; riêng `test_view3d_process_separate` xanh thêm 5/5 lần khi có tải CPU nền (số tiến trình bận ≥ số lõi logic); 0 lần quá hạn không có chẩn đoán.
  Đo bằng: `python -m pytest <nodeid>` lặp 5 lần mỗi kiểm thử (tối đa 1–2 lần mỗi lượt làm việc, cộng dồn bằng chứng qua các lượt); `stress`/vòng lặp tính toán nền cho phép đo có tải. (AC-1, AC-2)
- **NFR-PERF-001**: Hạn mức thời gian của kiểm thử không thành nguyên nhân đỏ.
  Ngưỡng: kiểm thử `test_real_viewer_plays_or_reports_no_display` kết thúc ≤ 25 s ở nhánh có màn hình và ≤ 5 s ở nhánh không màn hình (lệnh con); `test_view3d_process_separate` hoàn tất phần tiến trình tách riêng (trước phần huấn luyện thật) ≤ 10 s, trong đó hạn mức chờ khởi chạy ≤ 5 s.
  Đo bằng: `python -m pytest --durations=5 <nodeid>`. (AC-1, AC-2)
- **NFR-QUAL-001**: Chất lượng mã kiểm thử.
  Ngưỡng: lệnh kiểm kiểu và lint của dự án xanh (0 lỗi) trên hai tệp kiểm thử đã sửa.
  Đo bằng: `ruff check` và `mypy` theo cấu hình trong `pyproject.toml`. (AC-4)

<a id="bat-bien-invariants"></a>
### Bất biến (Invariants)

- **INV-001**: Số kiểm thử và độ chặt của các khẳng định nghiệm thu trong hai tệp MUST NOT giảm sau khi sửa; MUST NOT thêm cơ chế bỏ qua (hiến chương II). (AC-4)
- **INV-002**: Kiểm thử MUST độc lập với thứ tự chạy và với trạng thái còn lại của lần chạy trước: không để tiến trình, luồng hay tệp mồ côi ngoài `tmp_path`. (AC-1, AC-2)
- **INV-003**: Vùng ghi của feature MUST là hai tệp integration + một tệp e2e mới (xem FR-007); `src/` MUST NOT bị đổi, trừ `src/mma_ai/visualization/viewer.py` khi phép đo chứng minh nguyên nhân của T-A nằm ở đó (AC-5). Không ràng buộc "đúng hai tệp" ở tiêu chí `git diff --name-only`. (AC-4, AC-5)

<a id="success-criteria-mandatory"></a>
## Success Criteria *(mandatory)*

<a id="measurable-outcomes"></a>
### Measurable Outcomes

- **SC-001**: Cổng tests trên nhánh tích hợp xanh ở hai kiểm thử, xanh 5/5 lần liên tiếp ở mỗi kiểm thử khi chạy riêng, và 5/5 lần ở T-B khi có tải CPU nền; 0 lần đỏ chập chờn. (AC-1, AC-2)
- **SC-002**: 0 lần kiểm thử T-A treo tới quá hạn mà không có chẩn đoán; quá hạn (nếu còn) luôn đi kèm lệnh, hạn mức và đầu ra. (AC-1)
- **SC-003**: 100% khẳng định nghiệm thu nêu ở FR-004 còn nguyên hoặc chặt hơn; 0 `skip`/`xfail` mới; số kiểm thử trong hai tệp không giảm. (AC-4)
- **SC-004**: Mỗi kiểm thử có đúng một mục nguyên nhân thật trong báo cáo, kèm số lần chạy và kết quả đo trước/sau; mỗi mục đo ghi rõ môi trường (có/không màn hình dùng được). (AC-3)
- **SC-005**: `git diff --name-only` chỉ chứa hai tệp integration, tệp e2e mới, báo cáo QA và (khi nguyên nhân ở `src/`) `src/mma_ai/visualization/viewer.py` + `tests/unit/test_viewer.py`; 0 thay đổi ở tệp `src/` khác. Nếu có nguyên nhân ở `src/`, báo cáo nêu tệp, hàm, bằng chứng và đề xuất; kiểm thử liên quan được ghi là còn đỏ vì nguyên nhân đó cho tới khi task sửa gốc được chứng minh bằng lần chạy ngoài. (AC-4, AC-5)

<a id="out-of-scope"></a>
## Out of Scope

- Sửa `src/` ngoài `src/mma_ai/visualization/viewer.py` (kể cả các mô-đun còn lại của `mma_ai.visualization.*` và `mma_ai.monitoring.*`); với `viewer.py` chỉ sửa khi phép đo chứng minh nguyên nhân ở đó (AC-5), qua task sửa gốc riêng, không qua task sửa kiểm thử.
- Sửa các kiểm thử khác ngoài `test_replay_viewer_real.py`, `test_viewer3d_train.py`, tệp e2e mới `test_007_viewer_entrypoint.py` và ca thử `tests/unit/test_viewer.py` đi kèm bản sửa gốc ở `viewer.py`.
- `xfail`, `skip` hay bất kỳ cách bỏ qua nào để che lỗi hai kiểm thử.
- Nới khẳng định nghiệm thu: AC-1, AC-2, FR-011, FR-014 của 005 và yêu cầu tách tiến trình của 003.
- Thêm hành vi sản phẩm mới, màn hình mới, endpoint mới hay thực thể dữ liệu mới.
- Dựng môi trường màn hình ảo (Xvfb/EGL/OSMesa) cho cổng tests hay đổi cách cổng tests được chạy.
- Hỗ trợ đa nền tảng (thuộc `006-cross-platform-support`) và M2–M9.

<a id="assumptions"></a>
## Assumptions

- Mã nguồn của hai feature nằm trên nhánh tích hợp `ai-sdlc/integration` (nhánh hiện hành chỉ có `specs/`, `docs/`); việc sửa và chạy kiểm thử diễn ra trên worktree/nhánh của task, không trên nhánh chứa spec này.
- Máy phát triển là Linux gốc có `DISPLAY=:0` (đã ghi ở 005); môi trường cổng tests có thể không có cửa sổ GL dùng được dù có thể có biến hiển thị. Môi trường cổng chưa được đo trong lượt đặc tả này (CHƯA KIỂM) — spec không khẳng định nó có hay không có màn hình.
- Kiểm thử T-B chạy phần huấn luyện thật chỉ khi có `torch` (đã có trong mã hiện tại); điều kiện đó là một phần của kiểm thử gốc, không phải cơ chế che lỗi mới.
- Giá trị "5 lần liên tiếp" của NFR-REL-001 là ngưỡng tự chốt cân bằng giữa độ tin cậy và thời gian của lượt (mỗi lượt chỉ 1–2 lần chạy); có thể nâng sau khi có số đo thực.
- Hai kiểm thử không bị chặn bởi nhau và có thể sửa độc lập.
