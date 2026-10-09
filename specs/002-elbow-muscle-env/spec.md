---
id: "SPEC-002"
title: "M1 (1/4) — Môi trường khuỷu tay điều khiển bằng 6 cơ & tập mục tiêu train/test — Spec"
doc_type: spec
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "002-elbow-muscle-env"
version: "1.0.0"
---

# Feature Specification: M1 (1/4) — Môi trường khuỷu tay điều khiển bằng cơ & tập mục tiêu train/test

- [Bối cảnh (Context)](#boi-canh-context)
- [Clarifications](#clarifications)
- [User Scenarios & Testing *(mandatory)*](#user-scenarios-testing-mandatory)
  - [User Story 1 - Môi trường khuỷu tay chỉ điều khiển bằng 6 cơ (Priority: P1)](#user-story-1-moi-truong-khuyu-tay-chi-dieu-khien-bang-6-co-priority-p1)
  - [User Story 2 - Observation/action xác định và được kiểm tra tự động (Priority: P1)](#user-story-2-observationaction-xac-dinh-va-duoc-kiem-tra-tu-dong-priority-p1)
  - [User Story 3 - Tập mục tiêu train và test tách bạch, tất định theo seed (Priority: P1)](#user-story-3-tap-muc-tieu-train-va-test-tach-bach-tat-dinh-theo-seed-priority-p1)
  - [User Story 4 - Reward và điều kiện kết thúc episode cấu hình được (Priority: P2)](#user-story-4-reward-va-dieu-kien-ket-thuc-episode-cau-hinh-duoc-priority-p2)
  - [User Story 5 - Quyết định phiên bản gymnasium/myosuite và cài được trong môi trường sạch (Priority: P2)](#user-story-5-quyet-dinh-phien-ban-gymnasiummyosuite-va-cai-duoc-trong-moi-truong-sach-priority-p2)
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

**Feature Branch**: `002-elbow-muscle-env` (tên thư mục feature; không tạo nhánh git mới)

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "REQ-0101 — Là nhà nghiên cứu RL, tôi cần môi trường khuỷu tay điều khiển bằng 6 cơ và tập mục tiêu train/test tách bạch để huấn luyện và đánh giá chính đáng. Con 1/4 của Milestone M1 (Single-Arm Muscle Control); nguồn: `docs/00-input/split/yeu-cau-a7634ac9/request-1.md`."

<a id="boi-canh-context"></a>
## Bối cảnh (Context)

Dự án MMA-AI-LAB (mô phỏng cơ–xương 3D, học tăng cường — RL) đi theo các cột mốc M0–M9. Feature này là **con 1/4 của M1 — Single-Arm Muscle Control**, kế tiếp `001-m0-physics-benchmark` (M1 chỉ được coi là xong khi M0 đạt nghiệm thu). Nó là **nền tảng** của ba con còn lại: huấn luyện PPO (con 2), đánh giá và biểu đồ (con 3), replay/demo (con 4) đều dùng chung môi trường và tập mục tiêu ở đây; bản thân feature này không phụ thuộc con nào.

Mô hình mục tiêu là khuỷu tay MyoElbow (`myoelbow_1dof6muscles.xml`, gói `myo-sim==0.2.3`, đã xác nhận ở research của 001): 1 bậc tự do (khớp khuỷu, giới hạn góc [0, 2,26893] rad), 6 cơ Hill. Người dùng là **nhà nghiên cứu RL** (tạo môi trường, reset với mục tiêu, bước mô phỏng bằng vector kích thích 6 cơ) và **người đánh giá** (lấy tập mục tiêu kiểm thử cố định, chưa dùng khi train). Nỗi đau hiện tại: chưa có môi trường chuẩn Gymnasium để PPO và đánh giá dùng chung, và dễ rò rỉ mục tiêu train sang test nếu không tách từ gốc.

<a id="clarifications"></a>
## Clarifications

- Tự chốt: Mã tiêu chí chấp nhận giữ nguyên AC-1…AC-5 của yêu cầu REQ-0101 (mục 6), không gộp, không bỏ; mỗi AC có ít nhất một Acceptance Scenario ghi đúng mã.
- Tự chốt: Không có giao diện đồ hoạ cho người dùng cuối (chỉ thư viện + dòng lệnh, chạy không đồ hoạ); do đó không có màn hình/E2E/ảnh chụp trong feature này. Replay 3D thuộc con 4 (Out of Scope).
- Tự chốt: Tần suất của từng User Story suy từ bảng "Người dùng và tình huống" của yêu cầu (mỗi lần train/đánh giá) — mỗi lần train hoặc đánh giá là một lần tạo môi trường; số lần mỗi tuần ước lượng ghi ở từng story.
- Tự chốt: Quyết định ghim `gymnasium<1.3` theo MyoSuite hay bỏ MyoSuite → để bước plan quyết định bằng kiểm tra cài thật (đã đo sơ bộ ngày 2026-10-09: `myosuite==3.0.0` yêu cầu `gymnasium<1.3`, nên không thể cùng `gymnasium==1.4.0`) — lý do: là quyết định kỹ thuật cần chứng minh bằng cài trong môi trường ảo sạch (AC-5); spec chỉ đòi kết quả là có quyết định, có lý do, cài được.
- Tự chốt: Công thức reward và ngưỡng "tới mục tiêu" → reward gồm hai thành phần có trọng số cấu hình được (thành phần tiến tới mục tiêu và thành phần phạt kích hoạt/nỗ lực); "tới mục tiêu" khi khoảng cách đầu mút tay–mục tiêu ≤ dung sai, mặc định khởi đầu 0,02 m. Giá trị trọng số và dung sai là tham số khởi tạo cấu hình được, chốt số cuối ở plan sau khi đo hình học cánh tay — lý do: yêu cầu gốc đã đòi "tham số cấu hình được" và master plan XI.10 cấm giả định; sai thì chỉ đổi một giá trị cấu hình.
- Tự chốt: Kích thước tập mục tiêu → mặc định khởi đầu 200 mục tiêu train và 50 mục tiêu test, cấu hình được — lý do: yêu cầu để mở; đủ để thống kê so sánh với random policy ở con 3, đổi số không đổi cấu trúc.
- Tự chốt: Vì khuỷu tay chỉ có 1 bậc tự do, đầu mút tay (site `wrist`) chỉ di chuyển trên một cung 1 chiều (đo 2026-10-09: dây cung ≈ 0,477 m giữa hai giới hạn khớp). Mục tiêu luôn được sinh sao cho **với tới được** (là vị trí đầu mút tay ở một góc khớp nằm trong giới hạn), không sinh mục tiêu 3D tuỳ ý — lý do: mục tiêu không với tới được làm mọi so sánh train/test vô nghĩa; không thêm thực thể hay FR mới ngoài "bộ sinh mục tiêu" của yêu cầu.
- Tự chốt: "Tập train ∩ tập test = ∅" được hiểu chặt hơn trùng giá trị chính xác: mọi cặp (mục tiêu train, mục tiêu test) cách nhau ít nhất một khoảng cách tối thiểu cấu hình được (> 0, mặc định khởi đầu bằng dung sai "tới mục tiêu") để một mục tiêu test không thể bị coi là đã thấy khi train do sai số dấu phẩy động hay do nằm trong dung sai — lý do: bảo vệ mục đích gốc (chống rò rỉ) mà không đổi định nghĩa giao rỗng.
- Tự chốt: Bố cục observation = góc khớp (1) + vận tốc khớp (1) + kích hoạt 6 cơ (6) + vị trí đầu mút tay (3) + vị trí mục tiêu (3) = 14 phần tử; chuẩn hoá về miền có cận hữu hạn đã khai báo. Số 14 là phép cộng của chính các thành phần trong yêu cầu (mô hình có 1 bậc tự do), không thêm thành phần mới.
- Tự chốt: Bước vật lý và nhịp policy → tham số cấu hình khởi tạo 0,0025 s và 16 bước vật lý mỗi hành động (≈ 25 Hz) theo yêu cầu; gán qua cấu hình cho mô phỏng, không sửa tệp XML; chưa benchmark nên không suy ra thời gian huấn luyện.
- Tự chốt: Episode kết thúc theo hai cách phân biệt rõ: "terminated" khi tới mục tiêu và "truncated" khi hết số hành động tối đa (mặc định khởi đầu 100 hành động ≈ 4 s ở 25 Hz, cấu hình được). Khi mô phỏng mất ổn định số (NaN/Inf/cảnh báo vật lý) môi trường báo lỗi rõ thay vì tiếp tục âm thầm.
- Kết luận phân loại: rà các điểm mơ hồ còn lại, không điểm nào đủ cả ba điều kiện (quyết định nghiệp vụ của người dùng · không có tập quán ngành · sai thì đắt) nên không đặt câu hỏi chờ người trả lời; ba câu hỏi mở của yêu cầu (§8) đều đã được xử lý ở các dòng Tự chốt trên.

<a id="user-scenarios-testing-mandatory"></a>
## User Scenarios & Testing *(mandatory)*

<a id="user-story-1-moi-truong-khuyu-tay-chi-dieu-khien-bang-6-co-priority-p1"></a>
### User Story 1 - Môi trường khuỷu tay chỉ điều khiển bằng 6 cơ (Priority: P1)

**Tần suất**: hằng ngày — nhà nghiên cứu RL tạo môi trường mỗi lần train/đánh giá/gỡ lỗi, khoảng 5–10 lần mỗi ngày trong giai đoạn M1.

Nhà nghiên cứu tạo môi trường Gymnasium nạp mô hình MyoElbow; môi trường có đúng 6 muscle actuators, action là vector kích thích `u ∈ [0,1]^6`, lực cơ do mô hình tính; không có position controller hay motor khớp thay cơ. Hash SHA-256 của tệp XML mô hình được tính và đưa vào thông tin môi trường để ghi vào hồ sơ thí nghiệm.

**Why this priority**: Đây là nền móng của con 2–4; không có môi trường chỉ điều khiển bằng cơ thì PPO, đánh giá và replay đều vô nghĩa. Là MVP độc lập: một môi trường mô phỏng cơ có thể tạo, reset và bước được.

**Independent Test**: Tạo môi trường, đọc số actuator, loại actuator, action space, hash XML; không cần tập mục tiêu hay reward.

**Acceptance Scenarios**:

1. **Given** mô hình MyoElbow, **When** nạp môi trường, **Then** có đúng 6 muscle actuators và action space là `[0,1]^6`. (AC-1)
2. **Given** môi trường đã nạp, **When** nhà nghiên cứu truy vấn thông tin mô hình, **Then** nhận được hash SHA-256 của tệp XML đã nạp và tên 6 cơ theo thứ tự chỉ số, đủ để ghi vào hồ sơ thí nghiệm. (AC-1)
3. **Given** cấu hình đúng, **When** quan sát cấu trúc điều khiển của môi trường, **Then** không có position controller hay joint motor thay cơ; mọi actuator là muscle actuator và lực cơ do mô hình tính từ kích thích. (AC-4)
4. **Given** môi trường đang chạy, **When** một hành động `u ∈ [0,1]^6` được đưa vào, **Then** môi trường chỉ ghi kích thích cơ và để mô phỏng tiến lên; không ghi trực tiếp lực cơ, góc khớp hay toạ độ tay. (AC-4)

---

<a id="user-story-2-observationaction-xac-dinh-va-duoc-kiem-tra-tu-dong-priority-p1"></a>
### User Story 2 - Observation/action xác định và được kiểm tra tự động (Priority: P1)

**Tần suất**: hằng ngày — mỗi lần train/đánh giá chạy hàng nghìn bước qua môi trường; nhà nghiên cứu chạy bộ kiểm tra tự động khoảng 5–10 lần mỗi ngày khi đổi mã.

Nhà nghiên cứu reset môi trường với seed rồi chạy episode bằng hành động ngẫu nhiên; mỗi observation có đúng chiều, không NaN/Inf và không ngoài khoảng đã khai báo, kiểm bằng test tự động.

**Why this priority**: PPO và đánh giá sẽ chạy hàng triệu bước; observation sai chiều/NaN làm hỏng huấn luyện mà khó truy vết.

**Independent Test**: Chạy rollout kiểm thử với hành động ngẫu nhiên có seed; test báo chiều, số NaN/Inf, số giá trị ngoài khoảng.

**Acceptance Scenarios**:

1. **Given** môi trường đã reset với seed, **When** chạy episode với hành động ngẫu nhiên, **Then** observation đúng chiều, không NaN/Inf, không ngoài khoảng. (AC-2)
2. **Given** observation vừa sinh, **When** kiểm tra từng thành phần, **Then** nó gồm góc khớp, vận tốc khớp, kích hoạt từng cơ, vị trí đầu mút tay và vị trí mục tiêu, đã chuẩn hoá về miền có cận hữu hạn đã khai báo, chiều là 14. (AC-2)
3. **Given** một rollout kiểm thử chạy headless, **When** rollout kết thúc, **Then** số NaN và số Inf trong mọi observation, reward và trạng thái mô phỏng đo được bằng 0. (AC-2)
4. **Given** hành động có số phần tử khác 6, chứa NaN/Inf hoặc ngoài `[0,1]`, **When** đưa vào môi trường, **Then** môi trường từ chối với thông báo nêu giá trị và lý do, không chạy âm thầm. (AC-1)

---

<a id="user-story-3-tap-muc-tieu-train-va-test-tach-bach-tat-dinh-theo-seed-priority-p1"></a>
### User Story 3 - Tập mục tiêu train và test tách bạch, tất định theo seed (Priority: P1)

**Tần suất**: hằng ngày — người đánh giá và nhà nghiên cứu lấy tập mục tiêu mỗi lần train/đánh giá, khoảng 3–6 lần mỗi ngày; sinh lại tập khi đổi seed hay kích thước.

Bộ sinh mục tiêu sinh tập train và tập test từ một seed; cùng seed cho cùng kết quả; hai tập không giao nhau nên mục tiêu của test chưa từng xuất hiện khi train. Môi trường có thể chọn lấy mục tiêu từ tập train hoặc tập test.

**Why this priority**: Đánh giá "tốt hơn random policy trên tập mục tiêu kiểm thử" (con 3) chỉ chính đáng khi test không rò rỉ từ train; phải tách từ gốc chứ không sửa sau.

**Independent Test**: Sinh tập hai lần với cùng seed, so sánh bằng nhau, tính giao train ∩ test bằng test.

**Acceptance Scenarios**:

1. **Given** cùng seed, **When** sinh tập mục tiêu hai lần, **Then** kết quả giống nhau; và tập train ∩ tập test = ∅. (AC-3)
2. **Given** tập mục tiêu đã sinh, **When** kiểm tra mọi cặp (mục tiêu train, mục tiêu test), **Then** không cặp nào trùng hoặc gần hơn khoảng cách tối thiểu cấu hình được. (AC-3)
3. **Given** môi trường được cấu hình lấy mục tiêu từ tập test, **When** reset nhiều lần với các seed khác nhau, **Then** mọi mục tiêu nhận được đều thuộc tập test và không mục tiêu nào thuộc tập train. (AC-3)
4. **Given** hai seed khác nhau, **When** sinh tập mục tiêu, **Then** cả hai tập vẫn không giao nhau (mỗi seed tự đảm bảo giao rỗng của chính nó). (AC-3)

---

<a id="user-story-4-reward-va-dieu-kien-ket-thuc-episode-cau-hinh-duoc-priority-p2"></a>
### User Story 4 - Reward và điều kiện kết thúc episode cấu hình được (Priority: P2)

**Tần suất**: hằng tuần — nhà nghiên cứu chỉnh trọng số reward, dung sai, số hành động tối đa khoảng 1–3 lần mỗi tuần khi tinh chỉnh huấn luyện.

Reward gồm thành phần tiến tới mục tiêu và thành phần phạt kích hoạt/nỗ lực, với trọng số cấu hình được; episode kết thúc khi tới mục tiêu (terminated) hoặc hết số hành động tối đa (truncated).

**Why this priority**: Cần cho PPO (con 2) nhưng chưa cần để chứng minh nền tảng; công thức cuối chốt ở plan và chỉnh được.

**Independent Test**: Chạy episode với hành động cố định, so reward khi tay gần/xa mục tiêu và khi đổi trọng số phạt.

**Acceptance Scenarios**:

1. **Given** hai trạng thái chỉ khác nhau ở khoảng cách tới mục tiêu, **When** tính reward, **Then** trạng thái gần mục tiêu hơn có thành phần tiến tới cao hơn, và reward ở cả hai trạng thái hữu hạn (không NaN/Inf). (AC-2)
2. **Given** hai hành động chỉ khác nhau ở độ lớn kích hoạt cơ, **When** tính reward với trọng số phạt > 0, **Then** hành động kích hoạt lớn hơn bị phạt nhiều hơn; đặt trọng số phạt bằng 0 thì thành phần phạt biến mất. (AC-2)
3. **Given** khoảng cách đầu mút tay–mục tiêu ≤ dung sai, **When** bước kết thúc, **Then** episode báo terminated; khi đạt số hành động tối đa mà chưa tới mục tiêu thì báo truncated. (AC-2)

---

<a id="user-story-5-quyet-dinh-phien-ban-gymnasium-myosuite-va-cai-duoc-trong-moi-truong-sach-priority-p2"></a>
### User Story 5 - Quyết định phiên bản gymnasium/myosuite và cài được trong môi trường sạch (Priority: P2)

**Tần suất**: hiếm — nhà nghiên cứu hoặc người cộng tác mới, khoảng 1 lần mỗi vài tháng hoặc khi đổi máy.

Có một quyết định phiên bản ghi rõ lý do (ghim `gymnasium` theo MyoSuite hay bỏ MyoSuite và dùng `myo-sim` + `gymnasium` mới); làm theo quyết định đó trong môi trường ảo sạch thì cài và chạy được môi trường; dependency được khoá vào lockfile sau smoke test.

**Why this priority**: Tái lập là yêu cầu xuyên suốt, nhưng quyết định chỉ cần đúng một lần và không chặn việc viết môi trường.

**Independent Test**: Tạo môi trường ảo mới, cài theo quyết định, chạy smoke test của môi trường.

**Acceptance Scenarios**:

1. **Given** môi trường ảo sạch, **When** cài theo quyết định phiên bản, **Then** cài và chạy được môi trường; lý do chọn được ghi lại. (AC-5)
2. **Given** quyết định phiên bản, **When** người đọc tìm lý do, **Then** thấy phương án đã chọn, phương án đã loại và bằng chứng cài thật (lệnh/đầu ra), không phải giả định tương thích. (AC-5)
3. **Given** smoke test của môi trường đã đạt, **When** khoá dependency, **Then** lockfile ghi đúng các phiên bản đã cài thành công. (AC-5)

---

<a id="edge-cases"></a>
### Edge Cases

- Mô hình nạp được không có đúng 6 muscle actuators (hoặc có actuator không phải cơ): môi trường từ chối khởi tạo, nêu số cơ và số actuator không phải cơ tìm thấy; không thay bằng mô hình có motor. (AC-1)
- Hành động sai kích thước (khác 6 phần tử), chứa NaN/Inf hoặc có phần tử ngoài `[0,1]`: bị từ chối với thông báo nêu giá trị vi phạm. (AC-1)
- MuJoCo kẹp kích thích về dải điều khiển của mô hình (đo ở 001: `[0.001, 1]`): giá trị hiệu dụng sau kẹp được ghi nhận bên cạnh giá trị yêu cầu, không che giấu. (AC-1)
- Mô phỏng sinh NaN/Inf hoặc cảnh báo vật lý giữa episode: môi trường báo lỗi rõ (nêu bước, đại lượng) thay vì trả observation hỏng. (AC-2)
- `step` được gọi trước `reset`, hoặc sau khi episode đã kết thúc: báo lỗi sử dụng rõ ràng thay vì trả kết quả vô nghĩa. (AC-2)
- Reset với seed `None`: vẫn chọn được mục tiêu hợp lệ từ tập đã chọn và ghi nhận seed thực dùng; reset hai lần với cùng seed cho cùng mục tiêu. (AC-3)
- Cấu hình khiến không thể tách hai tập với khoảng cách tối thiểu train–test (ví dụ khoảng cách tối thiểu lớn hơn bề rộng khả dụng của cung với tới được, hoặc kích thước tập bằng 0): bộ sinh báo lỗi nêu giới hạn vi phạm, không giảm khoảng cách âm thầm. (INV-001)
- Cùng seed nhưng khác kích thước tập: được phép cho tập khác nhau, nhưng mỗi tập vẫn giao rỗng giữa train và test. (INV-001)
- Mục tiêu sinh ra nằm ngoài tầm với của đầu mút tay (không ứng với góc khớp nào trong giới hạn): không được xuất hiện trong tập nào. (AC-3)
- Mọi điều khiển đi qua kích thích cơ; mã thử ghi thẳng vào góc khớp, lực hay toạ độ tay để "dịch chuyển" tay: bị coi là vi phạm và không có đường API cho việc đó. (INV-003)
- Observation vượt cận khai báo do vận tốc khớp đột biến: giá trị bị chuẩn hoá/kẹp về cận hoặc môi trường báo lỗi rõ; không trả giá trị ngoài cận. (INV-004)
- Hai lần dựng cùng cấu hình trên cùng môi trường cho hash XML khác nhau: báo cáo ghi như một bất thường, không che giấu. (AC-1)

<a id="requirements-mandatory"></a>
## Requirements *(mandatory)*

<a id="functional-requirements"></a>
### Functional Requirements

- **FR-001**: Hệ thống MUST nạp mô hình MyoElbow (`myoelbow_1dof6muscles.xml` từ gói `myo-sim==0.2.3`) qua MuJoCo và xác nhận có đúng 6 muscle actuators; MUST từ chối khởi tạo khi số cơ khác 6 hoặc khi có actuator không phải cơ. (AC-1, AC-4)
- **FR-002**: Hệ thống MUST cung cấp một môi trường một agent theo giao diện Gymnasium (`reset(seed)`, `step(action)`, action/observation space) trong mô-đun `single_agent.py`, chạy headless, không dùng pixel observation. (AC-1, AC-2)
- **FR-003**: Action space MUST là `u ∈ [0,1]^6` (một kích thích cho mỗi cơ); MUST từ chối hành động sai kích thước, chứa NaN/Inf hoặc ngoài `[0,1]` với thông báo nêu giá trị vi phạm. (AC-1)
- **FR-004**: Môi trường MUST chỉ nhận kích thích cơ làm đầu vào điều khiển; MUST NOT dùng position controller hoặc joint motor thay cơ và MUST NOT ghi trực tiếp lực cơ, góc khớp hay toạ độ tay; lực cơ MUST do mô hình MuJoCo tính. (AC-4)
- **FR-005**: Observation MUST gồm góc khớp, vận tốc khớp, trạng thái kích hoạt từng cơ, vị trí đầu mút tay và vị trí mục tiêu; MUST có chiều xác định (14), cận hữu hạn đã khai báo cho từng thành phần, và được chuẩn hoá về các cận đó. (AC-2)
- **FR-006**: Hệ thống MUST kiểm tra observation trước khi trả về (đúng chiều, không NaN/Inf, không ngoài cận) và MUST báo lỗi rõ khi mô phỏng mất ổn định (NaN/Inf hoặc cảnh báo vật lý) thay vì trả giá trị hỏng. (AC-2)
- **FR-007**: Hệ thống MUST cung cấp bộ kiểm tra tự động (test) cho chiều, NaN/Inf và ngoài khoảng của observation/action trên rollout hành động ngẫu nhiên có seed. (AC-2)
- **FR-008**: Reward MUST gồm thành phần tiến tới mục tiêu và thành phần phạt kích hoạt/nỗ lực, mỗi thành phần có trọng số cấu hình được; reward MUST hữu hạn ở mọi bước. (AC-2)
- **FR-009**: Episode MUST kết thúc terminated khi khoảng cách đầu mút tay–mục tiêu ≤ dung sai (cấu hình được) và truncated khi đạt số hành động tối đa (cấu hình được); hai trạng thái MUST phân biệt được ở đầu ra của `step`. (AC-2)
- **FR-010**: Bộ sinh mục tiêu MUST sinh mục tiêu **với tới được** (ứng với một góc khớp trong giới hạn), tất định theo seed: cùng seed và cùng cấu hình cho cùng danh sách mục tiêu. (AC-3)
- **FR-011**: Hệ thống MUST sinh hai tập mục tiêu train và test từ một seed với giao rỗng (mọi cặp train–test cách nhau ít nhất khoảng cách tối thiểu cấu hình được > 0); kích thước mỗi tập cấu hình được. (AC-3)
- **FR-012**: Môi trường MUST cho chọn nguồn mục tiêu là tập train hoặc tập test; khi chọn test MUST NOT bao giờ chọn mục tiêu của tập train, và ngược lại. `reset` MUST báo (qua info) tập nguồn, chỉ số mục tiêu và seed thực dùng. (AC-3)
- **FR-013**: Hệ thống MUST tính hash SHA-256 của tệp XML mô hình đã nạp và đưa vào thông tin môi trường để ghi vào hồ sơ thí nghiệm. (AC-1)
- **FR-014**: Các tham số của môi trường — bước vật lý (khởi đầu 0,0025 s), số bước vật lý mỗi hành động (khởi đầu 16), trọng số reward, dung sai, số hành động tối đa, kích thước và khoảng cách tối thiểu của tập mục tiêu — MUST nằm ở một cấu hình duy nhất, không rải hằng số trong mã; bước vật lý MUST đặt qua cấu hình, không sửa tệp XML. (AC-2)
- **FR-015**: Hệ thống MUST có một quyết định phiên bản `gymnasium` và `myosuite` ghi rõ phương án chọn, phương án loại, lý do và bằng chứng cài thật. (AC-5)
- **FR-016**: Hệ thống MUST cài và chạy được môi trường trong một môi trường ảo sạch theo quyết định phiên bản; MUST khoá dependency vào lockfile chỉ sau khi smoke test của môi trường đạt, không tự giả định phiên bản tương thích. (AC-5)

<a id="yeu-cau-phi-chuc-nang-non-functional-requirements"></a>
### Yêu cầu phi chức năng (Non-Functional Requirements)

- **NFR-REL-001**: Độ tin cậy số học của môi trường trong rollout kiểm thử. Ngưỡng: 0 giá trị NaN và 0 giá trị Inf trong observation, reward và trạng thái mô phỏng trên rollout kiểm thử ≥ 10 episode với hành động ngẫu nhiên có seed. Đo bằng: `python -m pytest` (bộ test rollout của môi trường). (AC-2)
- **NFR-REPRO-001**: Tính tất định của bộ sinh mục tiêu. Ngưỡng: 0 khác biệt giữa hai lần sinh tập mục tiêu với cùng seed và cấu hình; giao train ∩ test có 0 phần tử. Đo bằng: `python -m pytest` (test sinh tập hai lần và tính giao). (AC-3)
- **NFR-HEADLESS-001**: Chạy không đồ hoạ. Ngưỡng: môi trường tạo, reset và bước được khi không có màn hình (biến `DISPLAY` không đặt) với mã thoát 0. Đo bằng: `python -m pytest` (test chạy với `DISPLAY` bỏ đặt). (AC-2)
- **NFR-INST-001**: Cài được trong môi trường ảo sạch. Ngưỡng: `lệnh` cài theo quyết định phiên bản kết thúc mã thoát 0 và bộ test của môi trường xanh. Đo bằng: lệnh cài của lockfile (`uv sync`) rồi `python -m pytest` trong môi trường ảo mới. (AC-5)

<a id="bat-bien-invariants"></a>
### Bất biến (Invariants)

- **INV-001**: Tập mục tiêu train và tập mục tiêu test MUST có giao rỗng, và mọi cặp (train, test) MUST cách nhau ít nhất khoảng cách tối thiểu cấu hình được (> 0); môi trường ở chế độ test MUST NOT bao giờ chọn mục tiêu train. (AC-3)
- **INV-002**: Với cùng seed và cùng cấu hình, danh sách mục tiêu của từng tập, và mục tiêu được chọn ở `reset(seed)` MUST giống nhau giữa các lần chạy. (AC-3)
- **INV-003**: Đường điều khiển duy nhất của mô hình MUST là kích thích cơ `u_i ∈ [0,1]`; mọi actuator của mô hình MUST là muscle actuator (số actuator không phải cơ = 0); policy MUST NOT điều khiển trực tiếp lực hay toạ độ tay. (AC-4)
- **INV-004**: Mọi observation trả ra MUST có đúng chiều đã khai báo, hữu hạn (không NaN/Inf) và nằm trong cận đã khai báo; observation vi phạm MUST bị chặn bằng lỗi rõ ràng chứ không trả ra. (AC-2)

<a id="key-entities-include-if-feature-involves-data"></a>
### Key Entities *(include if feature involves data)*

- **Môi trường khuỷu tay (Elbow environment)**: môi trường một agent theo Gymnasium nạp MyoElbow; thuộc tính chính: 6 muscle actuators, action space `[0,1]^6`, observation 14 chiều, nguồn mục tiêu (train hoặc test), hash XML, cấu hình.
- **Mục tiêu (Target)**: một vị trí 3 chiều với tới được của đầu mút tay (ứng với một góc khớp trong giới hạn); có chỉ số trong tập của nó.
- **Tập mục tiêu (Target set)**: danh sách mục tiêu thuộc đúng một trong hai vai trò train hoặc test, sinh theo seed; hai tập của cùng một seed có giao rỗng.
- **Cấu hình môi trường (Environment config)**: bước vật lý, số bước vật lý mỗi hành động, trọng số reward, dung sai, số hành động tối đa, kích thước và khoảng cách tối thiểu của tập mục tiêu.
- **Hồ sơ mô hình (Model record)**: hash SHA-256 của tệp XML, tên 6 cơ theo thứ tự chỉ số, số actuator không phải cơ; dùng để ghi vào hồ sơ thí nghiệm.

<a id="success-criteria-mandatory"></a>
## Success Criteria *(mandatory)*

<a id="measurable-outcomes"></a>
### Measurable Outcomes

- **SC-001**: Môi trường nạp mô hình khuỷu tay với đúng 6 muscle actuators, action space `[0,1]^6`, và chạy headless với 0 NaN/Inf trong rollout kiểm thử. (AC-1, AC-2)
- **SC-002**: Observation/action có chiều và miền giá trị xác định, được kiểm tra tự động trên chiều, NaN và ngoài khoảng, với 0 vi phạm trên rollout kiểm thử. (AC-2)
- **SC-003**: Tập mục tiêu train và test sinh theo seed, hai lần sinh cùng seed giống nhau và giao nhau = rỗng, kiểm tra được bằng test. (AC-3)
- **SC-004**: Không có position controller thay cơ trong môi trường; lực cơ do mô hình tính, kiểm bằng test cấu trúc điều khiển. (AC-4)
- **SC-005**: Có quyết định phiên bản `gymnasium`/`myosuite` ghi rõ lý do và chứng minh cài được trong môi trường ảo sạch. (AC-5)

<a id="out-of-scope"></a>
## Out of Scope

- Thuật toán PPO (con 2).
- Checkpoint (con 2).
- TensorBoard (con 2).
- Evaluate (con 3).
- Biểu đồ (con 3).
- Replay/demo (con 4).
- Mỏi cơ.
- Damage proxy.
- M2–M9 (mỏi cơ, cân bằng, locomotion, toàn thân, hai võ sĩ, self-play, MJX): chỉ là lộ trình/ràng buộc, không đặc tả hay lập kế hoạch chi tiết.

<a id="assumptions"></a>
## Assumptions

- Người dùng là nhà nghiên cứu RL và người đánh giá vận hành qua thư viện/dòng lệnh; không có người dùng cuối hay giao diện đồ hoạ.
- M0 (`001-m0-physics-benchmark`) đã có spec + plan; feature này chỉ được coi là hoàn tất khi M0 đạt nghiệm thu, nhưng việc đặc tả không bị chặn bởi M0.
- Mô hình `myoelbow_1dof6muscles.xml` có sẵn trong `myo-sim==0.2.3` (đã xác nhận ở research của 001: `nu = 6`, 1 bậc tự do, site `wrist` làm đầu mút tay, cả 6 actuator là cơ Hill của MuJoCo).
- Repo greenfield; Python 3.11, MuJoCo, PyTorch, Gymnasium là nền kỹ thuật; phiên bản `gymnasium`/`myosuite` do plan quyết định bằng kiểm tra cài thật.
- Thời gian/ngân sách huấn luyện [KHÔNG BIẾT]; không suy ra thời gian huấn luyện từ bất kỳ con số nào trước khi benchmark (master plan XI.10).
- Chỉ M1; M2–M9 không được đặc tả hay lập kế hoạch ở đây.
