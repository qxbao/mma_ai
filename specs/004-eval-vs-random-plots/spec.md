---
id: "SPEC-004"
title: "M1 (3/4) — Đánh giá policy so với random policy và biểu đồ loss/reward/activation — Spec"
doc_type: spec
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "004-eval-vs-random-plots"
version: "1.0.0"
---

# Feature Specification: M1 (3/4) — Đánh giá policy so với random policy và biểu đồ loss/reward/activation

- [Bối cảnh (Context)](#boi-canh-context)
- [Clarifications](#clarifications)
- [User Scenarios & Testing *(mandatory)*](#user-scenarios-testing-mandatory)
  - [User Story 1 - Đánh giá policy đã học và random policy trên cùng tập mục tiêu kiểm thử (Priority: P1)](#user-story-1-danh-gia-policy-da-hoc-va-random-policy-tren-cung-tap-muc-tieu-kiem-thu-priority-p1)
  - [User Story 2 - Kết luận "tốt hơn random" theo tiêu chí khai trước, kèm khoảng tin cậy (Priority: P1)](#user-story-2-ket-luan-tot-hon-random-theo-tieu-chi-khai-truoc-kem-khoang-tin-cay-priority-p1)
  - [User Story 3 - Ba biểu đồ loss, reward, activation từ log của run (Priority: P1)](#user-story-3-ba-bieu-do-loss-reward-activation-tu-log-cua-run-priority-p1)
  - [User Story 4 - Tập đánh giá không giao tập train (Priority: P1)](#user-story-4-tap-danh-gia-khong-giao-tap-train-priority-p1)
  - [User Story 5 - Kết quả đánh giá lưu cùng hồ sơ run (Priority: P2)](#user-story-5-ket-qua-danh-gia-luu-cung-ho-so-run-priority-p2)
  - [User Story 6 - Checkpoint không tồn tại hoặc hỏng thì báo lỗi, không in kết quả giả (Priority: P2)](#user-story-6-checkpoint-khong-ton-tai-hoac-hong-thi-bao-loi-khong-in-ket-qua-gia-priority-p2)
  - [Edge Cases](#edge-cases)
- [Requirements *(mandatory)*](#requirements-mandatory)
  - [Functional Requirements](#functional-requirements)
  - [Yêu cầu phi chức năng (Non-Functional Requirements)](#yeu-cau-phi-chuc-nang-non-functional-requirements)
  - [Bất biến (Invariants)](#bat-bien-invariants)
  - [Key Entities *(include if feature involves data)*](#key-entities-include-if-feature-involves-data)
- [Success Criteria *(mandatory)*](#success-criteria-mandatory)
  - [Measurable Outcomes](#measurable-outcomes)
- [Out of Scope](#out-of-scope)
- [Assumptions](#assumptions)

**Feature Branch**: `004-eval-vs-random-plots` (tên thư mục feature; không tạo nhánh git mới)

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "REQ-0103 — Là nhà nghiên cứu RL, tôi cần đánh giá policy đã học so với random policy trên mục tiêu chưa dùng khi train và xem biểu đồ loss/reward/activation. Con 3/4 của Milestone M1 (Single-Arm Muscle Control); nguồn: `docs/00-input/split/yeu-cau-a7634ac9/request-3.md`."

<a id="boi-canh-context"></a>
## Bối cảnh (Context)

Dự án MMA-AI-LAB (mô phỏng cơ–xương 3D, học tăng cường — RL) đi theo các cột mốc M0–M9. Feature này là **con 3/4 của M1 — Single-Arm Muscle Control**. Nó kế tiếp `002-elbow-muscle-env` (con 1: môi trường khuỷu tay điều khiển bằng 6 cơ và hai tập mục tiêu train/test) và `003-ppo-train-repro` (con 2: huấn luyện PPO, checkpoint, nhật ký train, hồ sơ run); M1 chỉ được coi là xong khi M0 (`001-m0-physics-benchmark`) đạt nghiệm thu. Con 3 **chỉ đọc** checkpoint và nhật ký của con 2 và tập mục tiêu kiểm thử của con 1, và **cung cấp** kết quả đánh giá cùng biểu đồ — con 4 (replay 3D & demo) độc lập với con 3.

Người dùng là **nhà nghiên cứu RL**: sau mỗi run huấn luyện, chạy `python scripts/evaluate.py --checkpoint <path>` rồi xem biểu đồ. Nỗi đau hiện tại: chưa có bằng chứng định lượng rằng policy đã học được hơn hành động ngẫu nhiên. Master plan 9.4 đòi đánh giá trên random policy và trên các seed chưa dùng khi train; master plan XII đòi phân biệt kết quả đo thực tế với giả định. Feature này **đo và báo cáo trung thực**: nó không bảo đảm policy "tốt", chỉ cho biết policy có tốt hơn random theo một tiêu chí khai trước hay không, kèm khoảng tin cậy.

<a id="clarifications"></a>
## Clarifications

- Tự chốt: Mã tiêu chí chấp nhận giữ nguyên AC-1…AC-5 của yêu cầu REQ-0103 (mục 6), không gộp, không bỏ; mỗi AC có ít nhất một Acceptance Scenario ghi đúng mã. Bốn kết quả mong muốn KQ-1…KQ-4 được phủ bởi AC-1…AC-4 và FR-013 (KQ-4: lưu cùng hồ sơ run).
- Tự chốt: Giao diện quan sát thời gian thực (C-0009, đã được người dùng xác nhận qua Q-0001 cho `003-ppo-train-repro`) thuộc phạm vi **con 2**, không thuộc con 3 → con 3 chỉ tạo biểu đồ tĩnh (tệp ảnh) sau khi run kết thúc hoặc từ log đã ghi, không dựng bảng điều khiển hay giao diện thời gian thực — lý do: yêu cầu REQ-0103 (§4 "Ngoài") không có giao diện; thêm sẽ là mở rộng phạm vi.
- Tự chốt: Tiêu chí "tốt hơn random" khai trước (KQ-2, câu hỏi mở §8) → **chỉ số chính là tỷ lệ tới mục tiêu**; policy học được coi là tốt hơn random khi **cận dưới của khoảng tin cậy 95% cho hiệu (tỷ lệ tới mục tiêu của policy học được − của random policy) lớn hơn 0**. Mức tin cậy 95% hai phía (tương ứng mức ý nghĩa một phía 0,025 cho phát biểu "tốt hơn") và chỉ số chính đều là giá trị cấu hình được, ghi vào báo cáo *trước khi chạy* và không đổi sau khi thấy kết quả. Khoảng cách cuối episode là chỉ số phụ, được báo cáo kèm khoảng tin cậy nhưng không quyết định kết luận — lý do: "tới mục tiêu" là định nghĩa nhiệm vụ của con 1 (khoảng cách ≤ dung sai); một chỉ số chính duy nhất tránh chọn chỉ số theo kết quả (so sánh nhiều lần); phương pháp tính khoảng tin cậy chọn ở plan nhưng MUST tất định theo seed.
- Tự chốt: Số episode của lượt đánh giá (KQ-2, câu hỏi mở §8) → **một episode cho mỗi mục tiêu của tập kiểm thử, cho mỗi policy**, tức số episode mỗi policy bằng kích thước tập kiểm thử (mặc định khởi đầu của con 1: 50 mục tiêu); số lần lặp mỗi mục tiêu (`repeats`) cấu hình được, mặc định 1. Policy học được dùng hành động xác định (giá trị trung bình, không lấy mẫu); random policy dùng hành động ngẫu nhiên có seed cố định. Hai policy dùng cùng danh sách mục tiêu theo cùng thứ tự (so sánh ghép cặp theo mục tiêu). Spec KHÔNG khẳng định 50 episode đủ để phát hiện chênh lệch nhỏ — khoảng tin cậy rộng được báo cáo như vốn có — lý do: yêu cầu để mở; tập kiểm thử là thứ con 1 đã cố định; master plan XI.10 cấm giả định kết quả.
- Tự chốt: "Random policy" → ở mỗi bước lấy mẫu độc lập đều từ `[0,1]^6` (kích thích 6 cơ), seed cố định từ cấu hình đánh giá (mặc định khởi đầu 12345), cùng không gian hành động và cùng giới hạn episode với policy học được — lý do: baseline đơn giản nhất, tái lập bằng seed; không có đường điều khiển nào ngoài kích thích cơ (master plan 5.2).
- Tự chốt: "Seed chưa dùng khi train" (AC-4) → seed đánh giá (seed khởi tạo episode và seed của random policy) MUST khác mọi seed dùng khi train run đó (seed gốc, và seed các run cha nếu train tiếp, đọc từ hồ sơ run của con 2). Mặc định khởi đầu của seed đánh giá (12345) khác seed ví dụ của train (42); nếu cấu hình trùng, lệnh từ chối — lý do: yêu cầu §5 "tập đánh giá không giao tập train".
- Tự chốt: "Không mục tiêu nào trùng tập train" (AC-4) → kiểm theo đúng định nghĩa chặt của con 1 (INV-001 của `002-elbow-muscle-env`): giao rỗng và mọi cặp (mục tiêu train, mục tiêu đánh giá) cách nhau ít nhất khoảng cách tối thiểu của con 1. Kiểm được thực hiện **mỗi lần đánh giá** trước khi chạy episode đầu, trên tập train xác lập từ cấu hình của chính run đó. Nếu không thiết lập được tập train của run (hồ sơ thiếu thông tin) thì từ chối đánh giá, không đánh giá "không kiểm" — lý do: chống rò rỉ là mục đích của AC-4; đánh giá không kiểm được là thứ không đáng tin.
- Tự chốt: "Kết thúc bất thường" (mục 4 Trong) → episode không kết thúc theo hai cách bình thường của con 1 (terminated khi tới mục tiêu · truncated khi hết số hành động tối đa) mà bị cắt do môi trường báo mất ổn định số/vật lý (NaN/Inf, cảnh báo vật lý). Episode như vậy được đếm vào "tỷ lệ kết thúc bất thường", tính là **không tới mục tiêu**, loại khỏi thống kê khoảng cách cuối (vì không có khoảng cách hợp lệ), và không làm dừng cả lượt đánh giá — lý do: một episode hỏng không được che giấu cũng không được biến cả lượt thành vô ích.
- Tự chốt: "Mức kích hoạt/nỗ lực" → hai số đo trên mỗi episode: mức kích hoạt trung bình của từng cơ trong 6 cơ và nỗ lực trung bình (trung bình theo bước của mức kích hoạt trung bình 6 cơ); báo cáo trung bình theo episode và trên toàn tập — lý do: yêu cầu liệt kê "mức kích hoạt/nỗ lực"; dùng đúng đại lượng mà reward phạt của con 1 đã dùng nên so sánh được.
- Tự chốt: Tần suất ghi activation để vẽ (câu hỏi mở §8) → biểu đồ activation vẽ từ chính nhật ký con 2 đã ghi (một điểm cho mỗi lượt cập nhật, trung bình trên các bước của lượt, 6 đường cho 6 cơ); con 3 KHÔNG đòi con 2 ghi thêm hay thay đổi tần suất ghi — lý do: con 3 chỉ đọc nhật ký (ranh giới sở hữu dữ liệu); tần suất ghi của con 2 đủ cho xu hướng theo thời gian.
- Tự chốt: Nơi lưu kết quả đánh giá (KQ-4) → trong thư mục run chứa checkpoint, ở mục riêng `eval/` có mã định danh lần đánh giá duy nhất; không sửa, không ghi đè bất kỳ tệp nào con 2 đã ghi (hồ sơ run, checkpoint, nhật ký) và không ghi đè kết quả đánh giá cũ. Khi checkpoint không nằm trong thư mục run, lệnh cần nơi ghi do người dùng chỉ định rõ, nếu không thì từ chối — lý do: INV-001 của con 2 coi thư mục run đã tạo là bất biến; kết quả đánh giá là bản ghi *thêm* cạnh run chứ không phải sửa run.
- Tự chốt: Mã thoát của CLI → 0 khi lượt đánh giá hoàn tất và đã lưu kết quả (bất kể kết luận "tốt hơn" hay "không tốt hơn": kết luận là kết quả đo, không là lỗi); khác 0 khi checkpoint không tồn tại/hỏng (AC-5), cấu hình không hợp lệ, tập đánh giá giao tập train, hay không tạo được biểu đồ; giá trị số cụ thể chốt ở plan — lý do: yêu cầu chỉ đòi "khác 0" cho checkpoint lỗi; trộn kết luận vào mã thoát làm mọi lệnh đánh giá một policy chưa tốt trông như lỗi hệ thống.
- Tự chốt: Biểu đồ không tạo được (log thiếu, hỏng, hoặc run chưa có dữ liệu) → lệnh báo rõ biểu đồ nào không tạo được và vì sao, kết quả đánh giá số vẫn được lưu và ghi `charts` = không hoàn tất kèm lý do, mã thoát khác 0; không vẽ biểu đồ rỗng giả như thành công — lý do: master plan XII và yêu cầu §5 ("thành phần chưa chạy được phải báo lỗi và giới hạn, không mô tả là đã xong").
- Tự chốt: Cách chứng minh cơ chế so sánh (AC-2) trong bộ test → vì một checkpoint train ngắn không bảo đảm tốt hơn random, bộ test chứng minh cơ chế kết luận bằng các policy có chất lượng đã biết (ví dụ policy kịch bản chắc chắn tới mục tiêu và policy chắc chắn không tới) cùng giao diện nạp policy; kết quả trên checkpoint thật được báo cáo như đo được, không được tự khẳng định trước — lý do: master plan XII; test phải xanh/đỏ đúng cơ chế chứ không phụ thuộc may rủi huấn luyện.
- Kết luận phân loại: rà các điểm mơ hồ còn lại, không điểm nào đủ cả ba điều kiện (quyết định nghiệp vụ của người dùng · không có tập quán ngành · sai thì đắt), và không có quyết định mở rộng phạm vi nào do agent tự thêm (không thêm giao diện, không thêm baseline ngoài random, không thêm chỉ số ngoài danh sách mục 4); nên không có điểm nào cần dừng chờ người trả lời. Hai câu hỏi mở của yêu cầu (§8) đã được xử lý ở các dòng Tự chốt trên.

<a id="user-scenarios-testing-mandatory"></a>
## User Scenarios & Testing *(mandatory)*

<a id="user-story-1-danh-gia-policy-da-hoc-va-random-policy-tren-cung-tap-muc-tieu-kiem-thu-priority-p1"></a>
### User Story 1 - Đánh giá policy đã học và random policy trên cùng tập mục tiêu kiểm thử (Priority: P1)

**Tần suất**: hằng ngày — nhà nghiên cứu RL chạy đánh giá sau mỗi run huấn luyện, khoảng 2–6 lần mỗi ngày trong giai đoạn M1.

Nhà nghiên cứu chạy `python scripts/evaluate.py --checkpoint <path>`. Lệnh nạp policy từ checkpoint, chạy nó và một random policy trên cùng tập mục tiêu kiểm thử (mỗi mục tiêu một episode), rồi in và lưu chỉ số của từng policy: tỷ lệ thành công (tới mục tiêu), khoảng cách cuối episode, reward trung bình, mức kích hoạt/nỗ lực, tỷ lệ episode kết thúc bất thường, số NaN/Inf — kèm khoảng tin cậy.

**Why this priority**: Đây là MVP của feature: không có lệnh đánh giá chạy được thì không có bằng chứng định lượng nào (KQ-1).

**Independent Test**: Chạy lệnh trên một checkpoint hợp lệ (có thể từ lượt train ngắn); kiểm lệnh kết thúc mã 0 và đầu ra có đủ chỉ số của cả hai policy trên cùng tập mục tiêu.

**Acceptance Scenarios**:

1. **Given** checkpoint đã train, **When** chạy `python scripts/evaluate.py --checkpoint <path>` trên tập mục tiêu kiểm thử, **Then** lệnh in và lưu chỉ số của policy đã học và của random policy trên cùng tập mục tiêu, với cùng số episode, mỗi mục tiêu của tập một episode cho mỗi policy. (AC-1)
2. **Given** kết quả của một lượt đánh giá, **When** đọc chỉ số của mỗi policy, **Then** có đủ bảy nhóm chỉ số: tỷ lệ thành công, khoảng cách cuối, reward trung bình, mức kích hoạt/nỗ lực (kèm 6 cơ), tỷ lệ episode kết thúc bất thường, số NaN và số Inf; các chỉ số tỷ lệ và trung bình có khoảng tin cậy 95%. (AC-1)
3. **Given** cả hai policy đang chạy, **When** quan sát hành động đưa vào môi trường, **Then** mọi hành động của cả hai đều là kích thích cơ `u_i ∈ [0,1]` cho 6 cơ, không có đường điều khiển trực tiếp lực hay toạ độ tay. (AC-1)
4. **Given** một random policy với seed cố định, **When** chạy lượt đánh giá hai lần với cùng checkpoint và cấu hình, **Then** chuỗi hành động ngẫu nhiên và mọi chỉ số giống nhau giữa hai lần. (AC-1)
5. **Given** một episode bị môi trường báo mất ổn định, **When** lượt đánh giá chạy tiếp, **Then** episode đó được đếm là kết thúc bất thường (không tới mục tiêu), lượt đánh giá không dừng, và tỷ lệ kết thúc bất thường phản ánh nó. (AC-1)

---

<a id="user-story-2-ket-luan-tot-hon-random-theo-tieu-chi-khai-truoc-kem-khoang-tin-cay-priority-p1"></a>
### User Story 2 - Kết luận "tốt hơn random" theo tiêu chí khai trước, kèm khoảng tin cậy (Priority: P1)

**Tần suất**: hằng ngày — mỗi lượt đánh giá cho một kết luận; nhà nghiên cứu đọc kết luận khoảng 2–6 lần mỗi ngày.

Từ kết quả hai policy, lệnh đưa ra kết luận "policy đã học tốt hơn random" / "không tốt hơn" theo tiêu chí đã khai *trước khi chạy* (chỉ số chính, mức tin cậy 95%, quy tắc cận dưới của khoảng tin cậy của hiệu lớn hơn 0), kèm giá trị hiệu và khoảng tin cậy. Tiêu chí được ghi trong báo cáo.

**Why this priority**: Đây là mục tiêu cốt lõi (KQ-2): chỉ số riêng lẻ không trả lời "học được hơn ngẫu nhiên chưa", kết luận có ý nghĩa thống kê thì có.

**Independent Test**: Cho hai bộ kết quả tổng hợp có đáp án đã biết (một bộ rõ ràng tốt hơn, một bộ không tốt hơn); kiểm kết luận và khoảng tin cậy đúng, rồi kiểm tiêu chí được ghi trong báo cáo trước kết quả.

**Acceptance Scenarios**:

1. **Given** kết quả của hai policy trên cùng tập mục tiêu, **When** so sánh, **Then** báo cáo nêu rõ policy đã học tốt hơn random policy hay không theo tiêu chí khai trước — chỉ số chính là tỷ lệ tới mục tiêu, tốt hơn khi cận dưới của khoảng tin cậy 95% của hiệu lớn hơn 0 — kèm giá trị hiệu và khoảng tin cậy 95% của nó. (AC-2)
2. **Given** một policy chắc chắn tới mọi mục tiêu và một random policy gần như không tới mục tiêu nào, **When** so sánh, **Then** kết luận là "tốt hơn" và cận dưới khoảng tin cậy của hiệu lớn hơn 0. (AC-2)
3. **Given** hai policy có kết quả tới mục tiêu giống hệt nhau, **When** so sánh, **Then** kết luận là "không tốt hơn" và khoảng tin cậy của hiệu chứa 0. (AC-2)
4. **Given** một lượt đánh giá, **When** đọc báo cáo, **Then** tiêu chí (chỉ số chính, mức tin cậy, quy tắc kết luận) nằm trong báo cáo và đã có trong cấu hình trước khi episode đầu tiên chạy; không có đường nào thay đổi tiêu chí sau khi có kết quả. (AC-2)
5. **Given** khoảng tin cậy rộng do ít episode, **When** báo cáo, **Then** kết luận "không tốt hơn" được nêu kèm khoảng tin cậy đúng như tính được, không bị làm đẹp. (AC-2)

---

<a id="user-story-3-ba-bieu-do-loss-reward-activation-tu-log-cua-run-priority-p1"></a>
### User Story 3 - Ba biểu đồ loss, reward, activation từ log của run (Priority: P1)

**Tần suất**: hằng ngày — nhà nghiên cứu xem biểu đồ sau mỗi run, khoảng 2–6 lần mỗi ngày.

Từ nhật ký huấn luyện của run chứa checkpoint (TensorBoard hoặc CSV/JSONL do con 2 ghi), lệnh tạo ba tệp ảnh: biểu đồ loss, biểu đồ reward và biểu đồ activation của 6 cơ, không cần màn hình.

**Why this priority**: Là đầu ra thứ hai của yêu cầu (KQ-3); biểu đồ cho thấy huấn luyện diễn ra thế nào, bổ sung cho con số đánh giá.

**Independent Test**: Cho nhật ký của một run (từ lượt train ngắn hoặc nhật ký mẫu cùng định dạng), tạo biểu đồ và kiểm có đúng 3 tệp ảnh hợp lệ, mỗi ảnh đúng nội dung.

**Acceptance Scenarios**:

1. **Given** log của một run, **When** tạo biểu đồ, **Then** có ba tệp ảnh: ảnh loss, ảnh reward, ảnh activation. (AC-3)
2. **Given** ảnh activation, **When** xem, **Then** có đủ 6 đường, mỗi đường cho một trong 6 cơ, có nhãn tên cơ, trục bước/lượt huấn luyện và trục mức kích hoạt. (AC-3)
3. **Given** ảnh loss và ảnh reward, **When** xem, **Then** mỗi ảnh có trục với tên đại lượng và đơn vị/bước, và chuỗi vẽ khớp số điểm của chuỗi trong log (số điểm trong ảnh được kiểm bằng dữ liệu vẽ, không bằng mắt). (AC-3)
4. **Given** máy không có màn hình (`DISPLAY` bỏ đặt), **When** tạo biểu đồ, **Then** vẫn tạo đủ ba ảnh và mã thoát 0. (AC-3)
5. **Given** log thiếu một đại lượng (ví dụ không có chuỗi activation), **When** tạo biểu đồ, **Then** báo rõ biểu đồ nào không tạo được và vì sao, mã thoát khác 0, không có ảnh rỗng giả thay cho ảnh đó. (AC-3)

---

<a id="user-story-4-tap-danh-gia-khong-giao-tap-train-priority-p1"></a>
### User Story 4 - Tập đánh giá không giao tập train (Priority: P1)

**Tần suất**: hằng ngày — phép kiểm chạy tự động trong mỗi lượt đánh giá, khoảng 2–6 lần mỗi ngày (và trong bộ test tự động mỗi lần đổi mã).

Trước khi chạy episode đầu tiên, lệnh kiểm rằng không mục tiêu nào và không seed nào của lượt đánh giá trùng với tập train của run (mục tiêu train, seed train). Phát hiện trùng thì dừng, không đánh giá.

**Why this priority**: Đánh giá trên dữ liệu đã dùng khi train là đánh giá giả; đây là điều kiện để mọi kết luận ở Story 2 có nghĩa.

**Independent Test**: Cấu hình đánh giá cố ý dùng seed trùng seed train, và một cấu hình ép tập đánh giá giao tập train; kiểm cả hai bị từ chối; với cấu hình đúng, kiểm tra giao rỗng đạt.

**Acceptance Scenarios**:

1. **Given** tập đánh giá và tập train của run, **When** kiểm tra, **Then** không mục tiêu nào trùng và không seed nào trùng: giao mục tiêu rỗng, mọi cặp (train, đánh giá) cách nhau ít nhất khoảng cách tối thiểu của con 1, và seed đánh giá khác mọi seed train của run. (AC-4)
2. **Given** cấu hình có seed đánh giá bằng seed train của run, **When** chạy đánh giá, **Then** lệnh từ chối với thông báo nêu seed trùng, mã thoát khác 0, không chạy episode nào. (AC-4)
3. **Given** một tập đánh giá có ít nhất một mục tiêu nằm trong khoảng cách tối thiểu của một mục tiêu train, **When** chạy đánh giá, **Then** lệnh từ chối nêu mục tiêu vi phạm, không chạy episode nào. (AC-4)
4. **Given** một lượt đánh giá đã hoàn tất, **When** đọc báo cáo, **Then** báo cáo ghi kết quả phép kiểm giao rỗng (số mục tiêu đã kiểm, khoảng cách nhỏ nhất đo được giữa tập train và tập đánh giá, seed đánh giá, seed train). (AC-4)

---

<a id="user-story-5-ket-qua-danh-gia-luu-cung-ho-so-run-priority-p2"></a>
### User Story 5 - Kết quả đánh giá lưu cùng hồ sơ run (Priority: P2)

**Tần suất**: hằng ngày — mỗi lượt đánh giá sinh một bản ghi lưu cạnh run; nhà nghiên cứu đối chiếu khoảng 2–6 lần mỗi ngày.

Mỗi lượt đánh giá lưu kết quả (chỉ số, kết luận, tiêu chí, kiểm giao rỗng, đường dẫn biểu đồ) cạnh hồ sơ run, kèm seed của run và checkpoint được dùng, để mở lại sau này mà biết chính xác kết quả ứng với checkpoint nào.

**Why this priority**: KQ-4: kết quả không truy vết được về checkpoint là kết quả không dùng được; xếp P2 vì lưu chỉ có giá trị sau khi Story 1–2 chạy được.

**Independent Test**: Chạy đánh giá hai lần rồi mở thư mục run: có hai bản ghi riêng, mỗi bản ghi nêu đúng checkpoint (tên và hash nội dung) và seed của run; hồ sơ run của con 2 không đổi.

**Acceptance Scenarios**:

1. **Given** một lượt đánh giá hoàn tất, **When** mở thư mục run chứa checkpoint, **Then** có bản ghi kết quả đánh giá nêu seed của run, định danh và hash nội dung của checkpoint được dùng, seed đánh giá, cấu hình đánh giá và chỉ số. (AC-1)
2. **Given** hai lượt đánh giá liên tiếp trên cùng checkpoint, **When** liệt kê thư mục `eval/`, **Then** có hai mục khác nhau và nội dung lượt trước không đổi. (AC-1)
3. **Given** hồ sơ run, checkpoint và nhật ký do con 2 ghi, **When** một lượt đánh giá chạy xong, **Then** các tệp này giữ nguyên nội dung (so sánh hash trước/sau). (AC-1)

---

<a id="user-story-6-checkpoint-khong-ton-tai-hoac-hong-thi-bao-loi-khong-in-ket-qua-gia-priority-p2"></a>
### User Story 6 - Checkpoint không tồn tại hoặc hỏng thì báo lỗi, không in kết quả giả (Priority: P2)

**Tần suất**: hiếm — gõ nhầm đường dẫn hoặc dùng checkpoint dở dang, khoảng 1 lần mỗi vài tuần.

Khi `--checkpoint` trỏ tới tệp không tồn tại, hỏng hoặc thiếu thành phần, lệnh báo lỗi rõ nguyên nhân, thoát với mã khác 0, và không in hay lưu bất kỳ chỉ số nào.

**Why this priority**: Master plan XII: không được mô tả thành phần chưa chạy là đã xong; giá trị thấp hơn các story đường chạy chính.

**Independent Test**: Gọi lệnh với đường dẫn không tồn tại, với tệp rỗng, và với checkpoint bị cắt cụt; kiểm thông báo, mã thoát và không có tệp kết quả.

**Acceptance Scenarios**:

1. **Given** checkpoint không tồn tại, **When** chạy evaluate, **Then** báo lỗi nêu đường dẫn không tồn tại, mã thoát khác 0, không in bất kỳ chỉ số nào. (AC-5)
2. **Given** checkpoint hỏng hoặc thiếu thành phần, **When** chạy evaluate, **Then** báo lỗi nêu nguyên nhân (hỏng, hay thiếu thành phần nào), mã thoát khác 0, không in kết quả giả. (AC-5)
3. **Given** lệnh thoát vì lỗi checkpoint, **When** kiểm thư mục run, **Then** không có bản ghi kết quả đánh giá, không có biểu đồ, và không có thư mục `eval/` mới dở dang. (AC-5)

---

<a id="edge-cases"></a>
### Edge Cases

- Checkpoint có hash XML mô hình khác với mô hình của môi trường hiện tại: từ chối đánh giá và nêu hai hash (policy không còn khớp mô hình, kết quả sẽ vô nghĩa). (AC-5)
- Checkpoint lưu bởi phiên bản thư viện khác: cảnh báo rõ phiên bản lưu và phiên bản hiện tại, vẫn đánh giá nếu cấu trúc khớp; báo cáo ghi cả hai phiên bản. (AC-1)
- Tập mục tiêu kiểm thử rỗng hoặc ít hơn số tối thiểu để tính khoảng tin cậy (cấu hình được, mặc định khởi đầu 2): từ chối với thông báo nêu số mục tiêu, không đưa kết luận. (AC-2)
- Số lần lặp mỗi mục tiêu hoặc số episode ≤ 0, mức tin cậy ngoài (0,1), hoặc chỉ số chính không thuộc danh sách chỉ số: cấu hình bị từ chối trước khi chạy, nêu giá trị sai. (AC-2)
- Tỷ lệ tới mục tiêu của cả hai policy cùng bằng 0 hoặc cùng bằng 1: khoảng tin cậy vẫn tính được (không chia cho 0, không NaN), kết luận "không tốt hơn", báo cáo ghi nguyên nhân. (AC-2)
- Policy học được cho ra hành động ngoài `[0,1]^6` hoặc chứa NaN/Inf: hành động bị chặn tại biên đánh giá, episode đếm là kết thúc bất thường, số NaN/Inf tăng; không để môi trường từ chối hành động của policy mà lượt đánh giá sụp. (INV-003)
- Tất cả episode của một policy đều kết thúc bất thường: khoảng cách cuối không có số hợp lệ nào — báo cáo ghi "không có dữ liệu" tường minh (`null`) cho các chỉ số khoảng cách, không ghi 0 hay NaN. (AC-1)
- Cấu hình đánh giá khai tập train hoặc môi trường khác với môi trường của run (khác hash XML, khác dung sai tới mục tiêu): từ chối, vì hai policy sẽ không còn so được với run. (INV-002)
- Run của checkpoint không có tập train thiết lập được (hồ sơ thiếu cấu hình môi trường hoặc seed): từ chối đánh giá thay vì đánh giá không kiểm giao rỗng. (INV-001)
- Hai lần chạy cùng checkpoint, cùng cấu hình, cùng seed: chỉ số giống nhau trong dung sai; hai lần chạy khác seed đánh giá: chuỗi của random policy khác nhau. (INV-007)
- Nhật ký train của run còn đang ghi (run `running`) hoặc dừng giữa chừng (`error`/`interrupted`): vẫn vẽ phần đã có và ghi trạng thái run vào báo cáo; không báo là "run hoàn chỉnh". (AC-3)
- Nhật ký có chuỗi loss chứa NaN/Inf (run lỗi): điểm không hữu hạn không bị vẽ im lặng thành 0; báo cáo ghi số điểm bị bỏ và lý do. (AC-3)
- Thư mục `eval/` không ghi được (đĩa đầy, hết quyền): lệnh báo lỗi rõ và thoát khác 0, không in kết quả như thể đã lưu. (INV-004)
- Lệnh bị ngắt giữa chừng (Ctrl-C): không để lại bản ghi kết quả dở dang trông như hợp lệ. (INV-004)
- Đánh giá không bao giờ ghi vào checkpoint, hồ sơ run hay nhật ký train của con 2. (INV-005)
- Hai policy không bao giờ được so trên hai tập mục tiêu hay hai thứ tự khác nhau. (INV-002)

<a id="requirements-mandatory"></a>
## Requirements *(mandatory)*

<a id="functional-requirements"></a>
### Functional Requirements

- **FR-001**: Hệ thống MUST cung cấp lệnh `python scripts/evaluate.py --checkpoint <path>` nạp policy từ checkpoint của con 2 (chỉ đọc) và đánh giá nó cùng một random policy trên tập mục tiêu kiểm thử của con 1, in và lưu chỉ số của cả hai policy. (AC-1)
- **FR-002**: Hai policy MUST được chạy trên cùng danh sách mục tiêu theo cùng thứ tự, với cùng cấu hình môi trường và cùng giới hạn episode, mỗi mục tiêu của tập một episode cho mỗi policy (số lần lặp mỗi mục tiêu cấu hình được, mặc định 1). (AC-1)
- **FR-003**: Policy học được MUST dùng hành động xác định; random policy MUST lấy mẫu hành động đều từ `[0,1]^6` với seed cố định lấy từ cấu hình; mọi hành động của cả hai MUST là kích thích cơ `u_i ∈ [0,1]` cho 6 cơ, MUST NOT dùng position controller thay cơ và MUST NOT điều khiển trực tiếp lực hay toạ độ tay. (AC-1)
- **FR-004**: Hệ thống MUST tính cho mỗi policy: tỷ lệ thành công (tới mục tiêu), khoảng cách cuối episode, reward trung bình, mức kích hoạt/nỗ lực (kèm kích hoạt từng cơ trong 6 cơ), tỷ lệ episode kết thúc bất thường, số NaN và số Inf; việc tính các chỉ số này MUST nằm ở mô-đun chỉ số `metrics.py`. (AC-1)
- **FR-005**: Hệ thống MUST tính khoảng tin cậy 95% (mức cấu hình được) cho tỷ lệ thành công, khoảng cách cuối và reward trung bình của từng policy, và cho hiệu giữa hai policy; việc tính MUST tất định theo seed cấu hình; phương pháp tính MUST được ghi tên trong báo cáo. (AC-1, AC-2)
- **FR-006**: Hệ thống MUST đưa ra kết luận "policy đã học tốt hơn random policy" hoặc "không tốt hơn" theo tiêu chí khai trước: chỉ số chính là tỷ lệ tới mục tiêu, kết luận "tốt hơn" khi và chỉ khi cận dưới của khoảng tin cậy 95% của hiệu (policy học được − random policy) lớn hơn 0; kèm giá trị hiệu và khoảng tin cậy. (AC-2)
- **FR-007**: Tiêu chí kết luận (chỉ số chính, mức tin cậy, quy tắc) MUST được đọc từ cấu hình đánh giá và ghi vào báo cáo; MUST NOT có đường nào thay đổi tiêu chí sau khi có kết quả; báo cáo MUST nêu cả khi kết luận là "không tốt hơn". (AC-2)
- **FR-008**: Trước khi chạy episode đầu tiên, hệ thống MUST kiểm tập đánh giá không giao tập train của run: giao mục tiêu rỗng và mọi cặp (mục tiêu train, mục tiêu đánh giá) cách nhau ít nhất khoảng cách tối thiểu của con 1; seed đánh giá (seed khởi tạo episode và seed random policy) MUST khác mọi seed train của run (cả các run cha khi train tiếp); vi phạm MUST làm lệnh dừng với lỗi rõ, mã thoát khác 0, không chạy episode nào. (AC-4)
- **FR-009**: Khi không thiết lập được tập train hoặc seed train của run (hồ sơ run thiếu thông tin), hệ thống MUST từ chối đánh giá thay vì bỏ qua phép kiểm giao rỗng. (AC-4)
- **FR-010**: Hệ thống MUST tạo ba biểu đồ lưu thành tệp ảnh — loss, reward, activation của 6 cơ — từ nhật ký huấn luyện của run chứa checkpoint (TensorBoard hoặc CSV/JSONL do con 2 ghi); activation MUST có 6 đường có nhãn tên cơ; việc đọc nhật ký và chuẩn bị dữ liệu vẽ MUST nằm ở mô-đun `metrics.py`. (AC-3)
- **FR-011**: Việc tạo biểu đồ MUST chạy không cần màn hình; khi nhật ký thiếu một đại lượng, hỏng hoặc rỗng, hệ thống MUST báo rõ biểu đồ nào không tạo được và vì sao, MUST NOT tạo ảnh rỗng thay thế, MUST vẫn lưu kết quả đánh giá số, ghi `charts` = không hoàn tất kèm lý do và thoát với mã khác 0. (AC-3)
- **FR-012**: Điểm không hữu hạn (NaN/Inf) trong nhật ký MUST NOT bị vẽ thành giá trị giả; số điểm bị bỏ và lý do MUST được ghi vào báo cáo. (AC-3)
- **FR-013**: Mỗi lượt đánh giá MUST lưu một bản ghi kết quả trong thư mục run chứa checkpoint, ở mục `eval/<mã lần đánh giá>/` duy nhất (không ghi đè), gồm: seed của run, định danh và hash nội dung của checkpoint được dùng, hash XML mô hình, seed đánh giá, cấu hình đánh giá đầy đủ, kết quả phép kiểm giao rỗng, chỉ số hai policy, kết luận, đường dẫn tương đối tới ba biểu đồ, trạng thái của run lúc đánh giá, phiên bản thư viện. Khi checkpoint không nằm trong thư mục run, hệ thống MUST yêu cầu nơi ghi được chỉ định rõ, nếu không thì từ chối. (AC-1)
- **FR-014**: Hệ thống MUST NOT sửa, ghi đè hay xoá hồ sơ run, checkpoint hoặc nhật ký train mà con 2 đã ghi; mọi đầu ra của con 3 là tệp mới trong `eval/`. (AC-1)
- **FR-015**: Khi `--checkpoint` không tồn tại, hỏng, thiếu thành phần, khác cấu trúc mạng hoặc khác hash XML mô hình, hệ thống MUST in lỗi nêu nguyên nhân, thoát với mã khác 0, và MUST NOT in hay lưu bất kỳ chỉ số, kết luận, biểu đồ hoặc thư mục `eval/` dở dang nào. (AC-5)
- **FR-016**: Episode bị môi trường báo mất ổn định số/vật lý MUST được đếm là kết thúc bất thường, tính là không tới mục tiêu, loại khỏi thống kê khoảng cách cuối, và MUST NOT làm dừng lượt đánh giá; số NaN/Inf phát hiện trong quan sát, hành động hoặc reward MUST được đếm vào báo cáo. (AC-1)
- **FR-017**: Chỉ số không có dữ liệu hợp lệ (ví dụ mọi episode kết thúc bất thường) MUST được ghi tường minh `null` kèm lý do, MUST NOT ghi 0 hay NaN; mọi tệp kết quả MUST là JSON hợp lệ không chứa NaN/Infinity. (AC-1)
- **FR-018**: Cấu hình đánh giá — seed đánh giá, số lần lặp mỗi mục tiêu, mức tin cậy, chỉ số chính, số mục tiêu tối thiểu, seed của khoảng tin cậy, nguồn nhật ký, thư mục ghi — MUST nằm ở một cấu hình duy nhất lưu nguyên văn vào bản ghi kết quả; cấu hình sai (giá trị ≤ 0, mức tin cậy ngoài (0,1), thiếu khoá) MUST bị từ chối trước khi chạy episode đầu. (AC-2, AC-4)
- **FR-019**: Báo cáo MUST phân biệt rõ số liệu đo thực tế bởi lượt đánh giá với giả định hay cấu hình; MUST ghi đủ giới hạn của kết luận (số episode, độ rộng khoảng tin cậy) và MUST NOT khẳng định chất lượng policy ngoài kết quả đo. (AC-2)
- **FR-020**: Hệ thống MUST cung cấp bộ test tự động cho: đủ chỉ số hai policy trên cùng tập mục tiêu, kết luận bằng policy có chất lượng đã biết, khoảng tin cậy trên dữ liệu có đáp án, ba biểu đồ (kể cả khi thiếu nhật ký), kiểm giao rỗng, checkpoint không tồn tại/hỏng, và tính tái lập theo seed. (AC-1, AC-2, AC-3, AC-4, AC-5)

<a id="yeu-cau-phi-chuc-nang-non-functional-requirements"></a>
### Yêu cầu phi chức năng (Non-Functional Requirements)

- **NFR-REPRO-001**: Tính tái lập của lượt đánh giá theo seed trên cùng loại thiết bị.
  Ngưỡng: hai lượt đánh giá cùng checkpoint, cùng cấu hình, cùng seed, cùng loại thiết bị cho chuỗi hành động random policy giống hệt (0 khác biệt) và mọi chỉ số, khoảng tin cậy lệch tuyệt đối ≤ 1×10⁻⁶; hai seed đánh giá khác nhau cho chuỗi hành động random policy khác nhau.
  Đo bằng: `python -m pytest` (test chạy hai lượt đánh giá cùng seed và khác seed). (AC-1, AC-2)
- **NFR-REL-001**: Độ tin cậy số học của báo cáo.
  Ngưỡng: 0 giá trị NaN và 0 giá trị Inf trong mọi trường số của bản ghi kết quả và báo cáo in ra; số NaN/Inf phát hiện trong dữ liệu episode được đếm và ghi, không đưa vào chỉ số.
  Đo bằng: `python -m pytest` (test hợp đồng bản ghi kết quả theo JSON Schema, quét giá trị không hữu hạn). (AC-1)
- **NFR-HEADLESS-001**: Đánh giá và vẽ biểu đồ chạy không đồ hoạ.
  Ngưỡng: lượt đánh giá kèm ba biểu đồ chạy hết khi biến `DISPLAY` không đặt, mã thoát 0, đủ 3 tệp ảnh khác rỗng.
  Đo bằng: `python -m pytest` (test chạy evaluate với `DISPLAY` bỏ đặt). (AC-3)
- **NFR-STAT-001**: Tính đúng của khoảng tin cậy và kết luận.
  Ngưỡng: trên 100% bộ dữ liệu tổng hợp trong bộ test có đáp án đã biết (gồm trường hợp tỷ lệ 0 và 1), kết luận khớp đáp án và khoảng tin cậy luôn hữu hạn, nằm trong miền giá trị hợp lệ của chỉ số (tỷ lệ trong [0,1]; hiệu tỷ lệ trong [−1,1]).
  Đo bằng: `python -m pytest` (test khoảng tin cậy và kết luận trên dữ liệu tổng hợp). (AC-2)

<a id="bat-bien-invariants"></a>
### Bất biến (Invariants)

- **INV-001**: Tập đánh giá MUST NOT giao tập train: giao mục tiêu rỗng, mọi cặp (train, đánh giá) cách nhau ít nhất khoảng cách tối thiểu của con 1, và seed đánh giá khác mọi seed train của run; phép kiểm chạy trước episode đầu và không thiết lập được thì không đánh giá. (AC-4)
- **INV-002**: Hai policy MUST được so trên cùng tập mục tiêu, cùng thứ tự, cùng cấu hình môi trường và cùng giới hạn episode; môi trường đánh giá MUST có hash XML bằng hash trong hồ sơ run. (AC-1)
- **INV-003**: Mọi hành động của cả hai policy MUST nằm trong `[0,1]^6` và là kích thích cơ; không có đường điều khiển trực tiếp lực hay toạ độ tay (kế thừa INV-003 của con 1 và INV-002 của con 2). (AC-1)
- **INV-004**: Khi lỗi (checkpoint lỗi, tập giao nhau, cấu hình sai, không ghi được), hệ thống MUST thoát mã khác 0 và MUST NOT để lại hay in kết quả đánh giá trông như hợp lệ; bản ghi kết quả chỉ xuất hiện khi lượt đánh giá hoàn tất. (AC-5)
- **INV-005**: Đánh giá MUST chỉ đọc đối với checkpoint, hồ sơ run và nhật ký train của con 2; kết quả của con 3 MUST ghi vào tệp mới, không ghi đè kết quả đánh giá cũ. (AC-1)
- **INV-006**: Tiêu chí kết luận MUST được khai trước khi episode đầu chạy và MUST NOT đổi theo kết quả; báo cáo MUST ghi nguyên tiêu chí đã dùng. (AC-2)
- **INV-007**: Với cùng checkpoint, cấu hình và seed trên cùng loại thiết bị, random policy MUST sinh cùng chuỗi hành động và lượt đánh giá MUST cho cùng chỉ số trong dung sai của NFR-REPRO-001. (AC-1)

<a id="key-entities-include-if-feature-involves-data"></a>
### Key Entities *(include if feature involves data)*

- **Lượt đánh giá (Evaluation run)**: một lần thực thi `evaluate.py` cho một checkpoint; có mã định danh duy nhất, thư mục riêng trong `eval/` của run, trạng thái (hoàn tất · lỗi) và cấu hình đánh giá.
- **Tập đánh giá (Evaluation set)**: danh sách mục tiêu kiểm thử của con 1 cùng seed đánh giá; có kết quả phép kiểm giao rỗng với tập train của run.
- **Kết quả theo policy (Policy result)**: chỉ số của một policy (học được hoặc random) trên tập đánh giá: tỷ lệ thành công, khoảng cách cuối, reward trung bình, kích hoạt/nỗ lực, tỷ lệ kết thúc bất thường, số NaN/Inf, cùng khoảng tin cậy.
- **Kết luận so sánh (Comparison verdict)**: hiệu giữa hai policy trên chỉ số chính, khoảng tin cậy của hiệu, tiêu chí khai trước và kết luận "tốt hơn" hay "không tốt hơn".
- **Báo cáo đánh giá (Evaluation report)**: bản ghi đầy đủ của một lượt: định danh run và checkpoint, seed, cấu hình, phép kiểm giao rỗng, hai Kết quả theo policy, Kết luận so sánh, trạng thái biểu đồ, phiên bản thư viện, giới hạn của kết luận.
- **Bộ biểu đồ (Chart set)**: ba tệp ảnh loss, reward, activation (6 cơ) vẽ từ nhật ký huấn luyện của run, kèm số điểm đã vẽ và số điểm bị bỏ.

<a id="success-criteria-mandatory"></a>
## Success Criteria *(mandatory)*

<a id="measurable-outcomes"></a>
### Measurable Outcomes

- **SC-001**: Lệnh `python scripts/evaluate.py --checkpoint <path>` trên checkpoint hợp lệ kết thúc mã 0 và in/lưu chỉ số của policy đã học và random policy trên cùng tập mục tiêu kiểm thử, mỗi mục tiêu một episode cho mỗi policy, với khoảng tin cậy 95% cho các chỉ số tỷ lệ và trung bình. (AC-1)
- **SC-002**: Mỗi báo cáo nêu rõ kết luận "tốt hơn" hay "không tốt hơn" theo tiêu chí khai trước (cận dưới khoảng tin cậy 95% của hiệu tỷ lệ tới mục tiêu > 0), kèm hiệu và khoảng tin cậy; trên bộ test có đáp án đã biết kết luận đúng 100%. (AC-2)
- **SC-003**: Mỗi lượt đánh giá trên run có nhật ký đủ tạo đúng 3 tệp ảnh khác rỗng (loss, reward, activation 6 cơ), kể cả khi không có màn hình. (AC-3)
- **SC-004**: 100% lượt đánh giá chạy phép kiểm giao rỗng trước episode đầu; giao mục tiêu = 0 phần tử, seed đánh giá không trùng seed train; vi phạm thì 0 episode được chạy. (AC-4)
- **SC-005**: Checkpoint không tồn tại hoặc hỏng cho mã thoát khác 0, thông báo nêu nguyên nhân, và 0 chỉ số, 0 biểu đồ, 0 bản ghi kết quả được tạo. (AC-5)
- **SC-006**: Mỗi bản ghi kết quả nêu seed của run và định danh + hash checkpoint được dùng; 100% tệp con 2 đã ghi giữ nguyên hash sau lượt đánh giá. (AC-1)

<a id="out-of-scope"></a>
## Out of Scope

- Huấn luyện và checkpoint (con 2).
- Môi trường và tập mục tiêu (con 1): feature này chỉ tiêu thụ, không định nghĩa hay sinh lại tập mục tiêu ngoài việc dựng lại để kiểm giao rỗng.
- Viewer 3D và replay (con 4).
- Frozen old policies, opponent pool, win rate (self-play, M5+).
- Biến thể vật lý và robustness (M5+).
- M2–M9 (mỏi cơ, cân bằng, locomotion, toàn thân, hai võ sĩ, self-play, MJX): chỉ là lộ trình/ràng buộc, không đặc tả hay lập kế hoạch chi tiết.

<a id="assumptions"></a>
## Assumptions

- Người dùng là nhà nghiên cứu RL vận hành qua dòng lệnh; không có người dùng cuối nào khác và không có giao diện đồ hoạ tương tác (biểu đồ là tệp ảnh).
- Con 1 (`002-elbow-muscle-env`) và con 2 (`003-ppo-train-repro`) hiện mới có spec + plan, chưa có mã; con 3 chỉ hoàn tất khi con 2 đã xanh và M0 đạt nghiệm thu, nhưng việc đặc tả không bị chặn. Con 3 giả định (CHƯA KIỂM) rằng con 2 cung cấp: nạp checkpoint chỉ-đọc cho suy luận, hồ sơ run (seed, cấu hình, hash XML mô hình, trạng thái) và nhật ký có chuỗi loss, reward, activation của 6 cơ; con 1 cung cấp tập mục tiêu kiểm thử, chọn được từng mục tiêu, và thông tin để dựng lại tập train của run. Phần nào hai con kia chưa cung cấp được thì bước plan ghi rõ và giao việc bổ sung đọc-chỉ về nơi chủ sở hữu.
- Python 3.11; NumPy/Pandas cho phân tích; biểu đồ headless; phần cứng đích RTX 5060 8GB, Ryzen 9 HX, 32GB RAM — đánh giá dùng suy luận và không cần GPU.
- Thời gian/ngân sách [KHÔNG BIẾT]: spec không nêu số episode "đủ" hay thời gian chạy; số liệu thời gian (nếu có) do máy đo và ghi trong báo cáo, không suy ra từ con số nào khác (master plan XI.10).
- Spec không khẳng định policy đã học đạt chất lượng nào: kết luận "tốt hơn random" là kết quả đo của từng lượt đánh giá; một checkpoint train ngắn có thể cho kết luận "không tốt hơn" và đó là kết quả hợp lệ.
- Mặc định khởi đầu (số mục tiêu kiểm thử 50, dung sai tới mục tiêu 0,02 m, mức tin cậy 95%) là giá trị cấu hình được, chốt lại ở plan sau khi đo; đổi số không đổi cấu trúc.
- Đường dẫn gốc của các run là cấu hình được và tương đối; không dùng đường dẫn tuyệt đối riêng của máy trong tài liệu hay bản ghi.
- Chỉ M1; M2–M9 không được đặc tả hay lập kế hoạch ở đây.
