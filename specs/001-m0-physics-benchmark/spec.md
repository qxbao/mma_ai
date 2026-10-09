---
id: "SPEC-001"
title: "M0 — Thiết lập môi trường & Benchmark vật lý — Spec"
doc_type: spec
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "001-m0-physics-benchmark"
version: "1.0.0"
---

# Feature Specification: M0 — Thiết lập môi trường & Benchmark vật lý (Setup & Physics Benchmark)

- [Bối cảnh (Context)](#boi-canh-context)
- [Clarifications](#clarifications)
- [User Scenarios & Testing *(mandatory)*](#user-scenarios-testing-mandatory)
  - [User Story 1 - Chạy được mô hình cơ–xương điều khiển bằng cơ, không đồ hoạ (Priority: P1)](#user-story-1-chay-duoc-mo-hinh-coxuong-dieu-khien-bang-co-khong-do-hoa-priority-p1)
  - [User Story 2 - Smoke test phát hiện NaN/Inf và lỗi vật lý (Priority: P1)](#user-story-2-smoke-test-phat-hien-naninf-va-loi-vat-ly-priority-p1)
  - [User Story 3 - Báo cáo hiệu năng mô phỏng (steps/second) (Priority: P2)](#user-story-3-bao-cao-hieu-nang-mo-phong-stepssecond-priority-p2)
  - [User Story 4 - Ghi nhận bộ nhớ RAM đỉnh và bộ nhớ GPU (Priority: P2)](#user-story-4-ghi-nhan-bo-nho-ram-dinh-va-bo-nho-gpu-priority-p2)
  - [User Story 5 - Hướng dẫn cài lại môi trường từ đầu (Priority: P2)](#user-story-5-huong-dan-cai-lai-moi-truong-tu-dau-priority-p2)
  - [User Story 6 - Báo cáo nghiệm thu M0 (Priority: P3)](#user-story-6-bao-cao-nghiem-thu-m0-priority-p3)
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


**Feature Branch**: `001-m0-physics-benchmark`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "MASTER PLAN — MMA AI EVOLUTION LAB (MMA-AI-LAB v1.0). Phạm vi lượt này: chỉ Milestone M0 (Setup & Physics Benchmark) theo mục XVI của yêu cầu gốc."

<a id="boi-canh-context"></a>
## Bối cảnh (Context)

Dự án MMA-AI-LAB nghiên cứu hành vi đối kháng tự phát (emergent combat behavior) của hai võ sĩ 3D điều khiển bằng tín hiệu kích hoạt cơ (muscle activation), học bằng học tăng cường (Reinforcement Learning — RL). Toàn bộ kế hoạch chia thành các cột mốc M0–M9; **lượt này chỉ đặc tả M0**: dựng nền tảng tối thiểu và chứng minh bằng đo đạc thật rằng một mô hình cơ–xương chạy được trên máy mục tiêu (Lenovo Legion Pro 5 — RTX 5060 8GB VRAM, Ryzen 9 HX, RAM 32GB) trước khi bất kỳ cột mốc nào sau đó được bắt đầu.

Người dùng của M0 là **nhà nghiên cứu / kỹ sư dự án** (một người, chạy qua dòng lệnh, không có giao diện đồ hoạ cho người dùng cuối). Kết quả M0 là cổng chặn: M1 trở đi chỉ được bắt đầu khi M0 đạt đủ tiêu chí nghiệm thu.

<a id="clarifications"></a>
## Clarifications

- Tự chốt: Mã tiêu chí chấp nhận được đánh số AC-1…AC-5 theo đúng thứ tự năm gạch đầu dòng "Acceptance Criteria" của M0 trong yêu cầu gốc — yêu cầu gốc không tự gán mã. Không gộp, không bỏ tiêu chí nào.
- Tự chốt: M0 không có giao diện đồ hoạ cho người dùng cuối (chỉ dòng lệnh và báo cáo văn bản), nên không có màn hình/E2E/ảnh chụp; ảnh chụp 3D bằng MuJoCo Viewer nằm ngoài M0 (xem Out of Scope).
- Tự chốt: Tần suất của từng User Story suy từ nghiệp vụ nghiên cứu (yêu cầu gốc không nêu): chạy smoke test và benchmark lặp lại mỗi khi đổi môi trường/phiên bản thư viện.
- Tự chốt: Mô hình "MyoElbow 6 cơ" lấy từ tài nguyên MyoSuite/MyoSim chính thức; nếu bản cài thực tế không có đúng mô hình 6 cơ thì xử lý theo Edge Case tương ứng, không thay bằng mô hình tự chế không có cơ.
- Tự chốt: Môi trường dò được ở thời điểm đặc tả là Linux gốc với Python 3.12.3 và chưa dò thấy công cụ NVIDIA; yêu cầu gốc nhắm Windows 11 + WSL2 Ubuntu và Python 3.11. Việc chọn phiên bản Python/CUDA cuối cùng thuộc bước plan, dựa trên kiểm tra tương thích thật (không giả định).
- Tự chốt: Khi GPU không khả dụng, AC-4 → ghi "chưa đạt" (không ghi "đạt") và cổng M0 chỉ đóng khi phép đo GPU thật chạy được trên máy đích; phần CPU vẫn hoàn tất và báo cáo — lý do: INV-001 và nguyên tắc "bằng chứng thắng lời khai" của constitution; rẻ nếu sai (chỉ đổi một nhãn trạng thái).
- Tự chốt: AC-3 → không đặt ngưỡng steps/second tối thiểu, chỉ yêu cầu số đo thật dương kèm độ phân tán — lý do: yêu cầu gốc chỉ đòi báo cáo con số đo được và cấm giả định thời gian huấn luyện; ngưỡng là quyết định của cột mốc sau, rẻ nếu sửa.
- Tự chốt: "Lỗi vật lý" trong AC-2 → cảnh báo (warning) hoặc ngoại lệ do bộ mô phỏng MuJoCo phát ra trong lúc chạy, tính là không đạt — lý do: tập quán dùng cơ chế cảnh báo của MuJoCo làm tín hiệu mất ổn định; chi tiết cách bắt thuộc bước plan.
- Tự chốt: Số bước mỗi mẫu, số mẫu ngẫu nhiên và số lần lặp cụ thể (≥ 5 theo NFR-PERF-001) → để bước plan chọn theo đo thực tế — lý do: chi tiết thực thi rẻ nếu sai, không đổi mô hình dữ liệu hay phạm vi.
- Kết luận phân loại: rà 10 nhóm phân loại mơ hồ, không có điểm nào đủ cả ba điều kiện (quyết định nghiệp vụ của khách · không có tập quán ngành · sai thì đắt) nên không đặt câu hỏi cho người.

<a id="user-scenarios-testing-mandatory"></a>
## User Scenarios & Testing *(mandatory)*

<a id="user-story-1-chay-duoc-mo-hinh-coxuong-dieu-khien-bang-co-khong-do-hoa-priority-p1"></a>
### User Story 1 - Chạy được mô hình cơ–xương điều khiển bằng cơ, không đồ hoạ (Priority: P1)

**Tần suất**: hằng tuần — nhà nghiên cứu chạy khi vừa cài/đổi môi trường hoặc đổi phiên bản thư viện, khoảng 1–3 lần mỗi tuần trong giai đoạn M0.

Nhà nghiên cứu cài môi trường, nạp mô hình khuỷu tay MyoElbow có 6 cơ (muscle actuator), chạy mô phỏng không đồ hoạ (headless) với các tín hiệu kích hoạt cơ hợp lệ trong khoảng [0, 1], rồi kiểm tra trạng thái khớp, trạng thái actuator và giá trị lực cơ sinh ra.

**Why this priority**: Đây là nền móng của cả dự án. Không có ít nhất một mô hình cơ–xương chạy được thì mọi cột mốc sau (học điều khiển tay, giữ thăng bằng, đối kháng) đều vô nghĩa. Đây cũng là MVP độc lập có giá trị: một môi trường mô phỏng cơ có thể chạy lại.

**Independent Test**: Chạy lệnh smoke test từ môi trường sạch; kết quả cho biết mô hình nạp thành công, số cơ, số khớp, và lực/trạng thái đọc được sau khi chạy với tín hiệu kích hoạt hợp lệ.

**Acceptance Scenarios**:

1. **Given** môi trường đã cài xong và mô hình MyoElbow có 6 cơ có sẵn, **When** nhà nghiên cứu nạp mô hình và chạy mô phỏng headless với vector kích hoạt 6 phần tử nằm trong [0, 1], **Then** mô phỏng chạy hết số bước yêu cầu mà không lỗi, và báo cáo cho thấy mô hình có đúng 6 cơ được điều khiển bằng kích hoạt cơ, không phải bằng bộ điều khiển vị trí khớp. (AC-1)
2. **Given** mô phỏng đang chạy với kích hoạt cơ khác nhau giữa các cơ, **When** nhà nghiên cứu đọc trạng thái sau mỗi lượt chạy, **Then** báo cáo liệt kê góc/vận tốc khớp, mức kích hoạt từng cơ và lực từng cơ, và lực cơ nằm trong giới hạn lực tối đa mà mô hình khai báo. (AC-1)
3. **Given** vector kích hoạt có phần tử nằm ngoài [0, 1], **When** nhà nghiên cứu đưa vào mô phỏng, **Then** hệ thống từ chối (hoặc ghi nhận rõ ràng là không hợp lệ) thay vì chạy âm thầm. (AC-1)

---

<a id="user-story-2-smoke-test-phat-hien-naninf-va-loi-vat-ly-priority-p1"></a>
### User Story 2 - Smoke test phát hiện NaN/Inf và lỗi vật lý (Priority: P1)

**Tần suất**: hằng tuần — nhà nghiên cứu chạy sau mỗi thay đổi môi trường hoặc cấu hình, khoảng 3–5 lần mỗi tuần.

Nhà nghiên cứu chạy một smoke test duy nhất; test chạy mô phỏng với nhiều mẫu kích hoạt hợp lệ (bao gồm kích hoạt bằng 0, bằng 1 và ngẫu nhiên có seed cố định) và kiểm tra toàn bộ đại lượng đo được (vị trí, vận tốc, lực, kích hoạt) không chứa NaN hoặc Inf và không phát sinh cảnh báo/lỗi vật lý.

**Why this priority**: Một mô phỏng sinh NaN/Inf sẽ làm hỏng mọi huấn luyện sau đó mà khó truy vết; phải chặn từ M0.

**Independent Test**: Chạy smoke test, đọc kết quả đếm NaN/Inf và kết luận đạt/không đạt.

**Acceptance Scenarios**:

1. **Given** mô hình muscle-driven đã nạp, **When** smoke test chạy mô phỏng với các mẫu kích hoạt hợp lệ, **Then** số giá trị NaN và số giá trị Inf trong mọi đại lượng đo được đều bằng 0 và smoke test kết thúc ở trạng thái đạt. (AC-2)
2. **Given** smoke test phát hiện ít nhất một giá trị NaN hoặc Inf, **When** test kết thúc, **Then** test báo không đạt, nêu đại lượng, bước mô phỏng và mẫu kích hoạt gây ra, và thoát với mã lỗi khác 0. (AC-2)
3. **Given** cùng seed và cùng cấu hình, **When** smoke test chạy hai lần liên tiếp, **Then** hai lần cho cùng kết luận đạt/không đạt và cùng số đếm NaN/Inf. (AC-2)

---

<a id="user-story-3-bao-cao-hieu-nang-mo-phong-stepssecond-priority-p2"></a>
### User Story 3 - Báo cáo hiệu năng mô phỏng (steps/second) (Priority: P2)

**Tần suất**: hằng tuần — nhà nghiên cứu chạy benchmark khoảng 1–2 lần mỗi tuần, và mỗi khi đổi phần cứng/cấu hình thời gian bước.

Nhà nghiên cứu chạy benchmark và nhận báo cáo số bước vật lý mô phỏng mỗi giây (physics steps/second) trên CPU, kèm cấu hình đo (bước thời gian vật lý, số bước, số lần lặp, phiên bản thư viện, thông tin phần cứng).

**Why this priority**: Con số này quyết định mọi quyết định sau về số môi trường song song, tần số policy và thời gian huấn luyện; yêu cầu gốc cấm giả định thời gian huấn luyện trước khi đo.

**Independent Test**: Chạy lệnh benchmark; báo cáo có số steps/second thật, đo lặp lại, kèm cấu hình đo.

**Acceptance Scenarios**:

1. **Given** mô hình muscle-driven đã nạp và smoke test đã đạt, **When** nhà nghiên cứu chạy benchmark headless trên CPU, **Then** xuất báo cáo chứa số physics steps/second đo thực tế (một số dương, kèm đơn vị), số lần lặp đo và độ phân tán giữa các lần lặp. (AC-3)
2. **Given** báo cáo benchmark vừa tạo, **When** nhà nghiên cứu mở nó, **Then** báo cáo ghi rõ bước thời gian vật lý, số bước mỗi lần đo, phiên bản các thư viện chính, mã định danh/hash của mô hình và thông tin CPU, đủ để lặp lại phép đo. (AC-3)

---

<a id="user-story-4-ghi-nhan-bo-nho-ram-dinh-va-bo-nho-gpu-priority-p2"></a>
### User Story 4 - Ghi nhận bộ nhớ RAM đỉnh và bộ nhớ GPU (Priority: P2)

**Tần suất**: hằng tuần — cùng lúc với benchmark, khoảng 1–2 lần mỗi tuần.

Trong cùng lần chạy benchmark, nhà nghiên cứu nhận được RAM đỉnh (peak RAM) của tiến trình và thông tin bộ nhớ GPU (GPU memory), đồng thời xác nhận GPU CUDA nhìn thấy được và tensor tính toán chạy được trên GPU.

**Why this priority**: Ngân sách hiệu năng (RAM 32GB, VRAM 8GB) là ràng buộc cứng của dự án; phải có số đo gốc để biết còn dư địa cho các cột mốc sau.

**Independent Test**: Chạy benchmark; báo cáo có hai mục: peak RAM và GPU memory (hoặc thông báo rõ GPU không khả dụng).

**Acceptance Scenarios**:

1. **Given** máy có GPU NVIDIA và driver hoạt động, **When** benchmark kết thúc, **Then** báo cáo ghi peak RAM (MB hoặc GB) của tiến trình và GPU memory (tổng, đã dùng đỉnh) cùng tên GPU, và xác nhận một phép tính nhỏ trên GPU chạy thành công. (AC-4)
2. **Given** máy không có GPU khả dụng hoặc driver lỗi, **When** benchmark chạy, **Then** báo cáo vẫn ghi peak RAM, và mục GPU ghi rõ "không khả dụng" kèm nguyên nhân thay vì để trống hoặc ghi số bịa; phần CPU vẫn hoàn tất. (AC-4)

---

<a id="user-story-5-huong-dan-cai-lai-moi-truong-tu-dau-priority-p2"></a>
### User Story 5 - Hướng dẫn cài lại môi trường từ đầu (Priority: P2)

**Tần suất**: hiếm — nhà nghiên cứu hoặc người cộng tác mới, khoảng 1 lần mỗi vài tháng hoặc khi đổi máy.

Một người khác (hoặc chính nhà nghiên cứu trên máy sạch) làm theo tài liệu hướng dẫn để dựng lại môi trường, chạy smoke test và benchmark và thu cùng loại kết quả, mà không cần hỏi thêm.

**Why this priority**: Tái lập (reproducibility) là yêu cầu xuyên suốt; môi trường M0 phải dựng lại được, với phiên bản thư viện đã khoá sau khi smoke test thành công.

**Independent Test**: Làm theo tài liệu trên môi trường sạch (hoặc môi trường ảo mới) đến khi smoke test đạt; ghi lại bước nào mơ hồ.

**Acceptance Scenarios**:

1. **Given** máy sạch đáp ứng yêu cầu tiên quyết nêu trong tài liệu, **When** nhà nghiên cứu làm đúng từng bước hướng dẫn cài lại môi trường, **Then** smoke test đạt và benchmark chạy xong mà không cần thao tác nào ngoài tài liệu. (AC-5)
2. **Given** tài liệu hướng dẫn, **When** người đọc tìm phần kiểm tra GPU/CUDA và phần xử lý sự cố thường gặp, **Then** tài liệu có các phần đó, ghi rõ lệnh nào chưa triển khai ở M0 là "chưa triển khai", và có tệp khoá phiên bản (lockfile) được tạo sau khi smoke test thành công. (AC-5)

---

<a id="user-story-6-bao-cao-nghiem-thu-m0-priority-p3"></a>
### User Story 6 - Báo cáo nghiệm thu M0 (Priority: P3)

**Tần suất**: hiếm — một lần khi đóng cột mốc M0 (và lặp lại nếu cấu hình thay đổi đáng kể).

Nhà nghiên cứu nhận báo cáo cấu hình–test–hiệu năng–hướng dẫn khởi động theo mẫu báo cáo cột mốc của dự án, nêu rõ tiêu chí nào đạt/chưa đạt, kết quả test thực tế (không phải giả định) và đề xuất cột mốc tiếp theo.

**Why this priority**: Là cổng quyết định có được sang M1 hay không; phụ thuộc vào kết quả của các story trên.

**Independent Test**: Đọc báo cáo và đối chiếu từng tiêu chí AC-1…AC-5 với bằng chứng (đầu ra lệnh, tệp báo cáo) nó trích dẫn.

**Acceptance Scenarios**:

1. **Given** US1–US5 đã chạy, **When** báo cáo nghiệm thu được tạo, **Then** mỗi tiêu chí AC-1…AC-5 có trạng thái đạt/chưa đạt kèm bằng chứng, và thành phần nào chưa chạy được thì ghi rõ lỗi và giới hạn thay vì mô tả là đã hoàn thành. (AC-1, AC-2, AC-3, AC-4, AC-5)

---

<a id="edge-cases"></a>
### Edge Cases

- Mô hình MyoElbow 6 cơ không có trong bản MyoSuite/MyoSim đã cài, hoặc số cơ khác 6: smoke test báo không đạt, nêu số cơ tìm thấy, không thay bằng mô hình không có cơ. (AC-1)
- Mô hình được điều khiển bằng bộ điều khiển vị trí/joint motor thay cho cơ: kiểm tra bị coi là không đạt; chỉ cơ (muscle actuator) mới được tính cho tiêu chí muscle-driven. (AC-1)
- Vector kích hoạt sai kích thước (khác 6 phần tử) hoặc chứa NaN: bị từ chối với thông báo rõ. (AC-1)
- Kích hoạt toàn 0 và toàn 1 kéo khớp tới giới hạn: mô phỏng phải ổn định, không sinh NaN/Inf, lực không vượt giới hạn lực mô hình. (AC-2)
- Phiên bản thư viện không tương thích với nhau hoặc với Python đích: bước cài dừng với lỗi nêu rõ cặp xung đột, không tự giả định tương thích. (AC-5)
- Máy không có GPU, driver cũ, hoặc WSL2 không nhìn thấy GPU: phần GPU báo "không khả dụng" kèm nguyên nhân, phần CPU vẫn hoàn tất, không bịa số. (AC-4)
- Benchmark bị nhiễu do tải nền (CPU bận): báo cáo ghi độ phân tán giữa các lần lặp để người đọc nhận ra phép đo không đáng tin. (AC-3)
- Cùng seed chạy hai lần cho kết quả mô phỏng khác nhau (không tất định): ghi nhận trong báo cáo như một giới hạn, không che giấu. (INV-002)
- Báo cáo nghiệm thu có ô nào chưa chạy thật: phải ghi "chưa chạy" thay vì điền giá trị giả định. (INV-001)
- Đường dẫn tuyệt đối riêng của máy hoặc bí mật xuất hiện trong báo cáo/tài liệu: không được phép. (INV-003)

<a id="requirements-mandatory"></a>
## Requirements *(mandatory)*

<a id="functional-requirements"></a>
### Functional Requirements

- **FR-001**: Hệ thống MUST kiểm tra và ghi nhận môi trường thực tế trước khi cài: hệ điều hành/WSL2, phiên bản Python, driver NVIDIA và phiên bản CUDA khả dụng; mục nào không dò được MUST được ghi là "không dò được", không đoán. (AC-4, AC-5)
- **FR-002**: Hệ thống MUST xác định tập phiên bản thư viện tương thích bằng kiểm tra thực tế (không giả định) cho MuJoCo, MyoSuite/MyoSim, PyTorch và các thư viện nền thật sự cần cho M0; MUST khoá phiên bản vào lockfile chỉ sau khi smoke test thành công. (AC-5)
- **FR-003**: Hệ thống MUST cung cấp một repository Python tối thiểu cho M0 có cấu hình dự án, các tệp cấu hình mô phỏng, mã nguồn thật cho nạp và chạy mô hình, và thư mục kiểm thử; MUST NOT tạo hàng loạt tệp rỗng hay mô phỏng giả (mock physics) thay mô phỏng thật. (AC-1)
- **FR-004**: Hệ thống MUST nạp được mô hình MyoElbow 6 cơ từ tài nguyên MyoSuite/MyoSim và xác nhận số cơ, số khớp, giới hạn góc khớp và giới hạn lực của mô hình sau khi nạp. (AC-1)
- **FR-005**: Hệ thống MUST chạy mô phỏng headless với vector kích hoạt cơ có số phần tử bằng số cơ (6) và mỗi giá trị trong [0, 1]; MUST từ chối vector sai kích thước, ngoài khoảng hoặc chứa NaN/Inf. (AC-1)
- **FR-006**: Hệ thống MUST điều khiển mô hình chỉ bằng kích hoạt cơ; MUST NOT dùng bộ điều khiển vị trí khớp hoặc joint motor thay cơ trong đường chạy chính của M0. (AC-1)
- **FR-007**: Hệ thống MUST đọc và báo cáo trạng thái khớp (góc, vận tốc), trạng thái actuator (kích hoạt từng cơ) và giá trị lực cơ sau khi chạy mô phỏng. (AC-1)
- **FR-008**: Hệ thống MUST cung cấp smoke test chạy bằng một lệnh, quét toàn bộ đại lượng đo được tìm NaN và Inf trên các mẫu kích hoạt (toàn 0, toàn 1, ngẫu nhiên có seed) và các cảnh báo/lỗi vật lý; MUST thoát mã khác 0 khi không đạt. (AC-2)
- **FR-009**: Smoke test MUST báo số NaN và số Inf bằng số đếm cụ thể; tiêu chí đạt là cả hai bằng 0. (AC-2)
- **FR-010**: Hệ thống MUST cung cấp benchmark chạy bằng một lệnh đo physics steps/second trên CPU, headless, lặp nhiều lần và báo cáo giá trị trung tâm cùng độ phân tán. (AC-3)
- **FR-011**: Báo cáo benchmark MUST ghi cấu hình đo: bước thời gian vật lý, số bước mỗi lần đo, số lần lặp, seed, phiên bản thư viện chính, hash mô hình và thông tin CPU/phần cứng. (AC-3)
- **FR-012**: Benchmark MUST ghi peak RAM của tiến trình mô phỏng. (AC-4)
- **FR-013**: Hệ thống MUST kiểm tra GPU CUDA nhìn thấy được, chạy một phép tính tensor nhỏ trên GPU, và ghi GPU memory (tên GPU, tổng, đỉnh đã dùng); khi GPU không khả dụng MUST ghi rõ "không khả dụng" kèm nguyên nhân và vẫn hoàn tất phần CPU. (AC-4)
- **FR-014**: Hệ thống MUST xuất báo cáo M0 dưới dạng tệp có thể lưu trữ (văn bản có cấu trúc) trong thư mục logs/báo cáo, đủ đối chiếu với từng tiêu chí AC-1…AC-5. (AC-3, AC-4)
- **FR-015**: Hệ thống MUST có tài liệu hướng dẫn cài lại môi trường (README): yêu cầu tiên quyết, các bước cài, kiểm tra GPU/CUDA, chạy smoke test và benchmark, xử lý sự cố thường gặp, cách dùng lockfile. (AC-5)
- **FR-016**: Hệ thống MUST ghi rõ trong tài liệu và đầu ra CLI những lệnh của mục XIII yêu cầu gốc chưa triển khai ở M0 (huấn luyện, đánh giá, replay) là "chưa triển khai", thay vì để lệnh chạy giả. (AC-5)
- **FR-017**: Hệ thống MUST có bộ unit test cho các phần M0 (nạp mô hình, kiểm tra hợp lệ vector kích hoạt, phát hiện NaN/Inf, tính và định dạng báo cáo) và chạy được bằng một lệnh test; smoke test hồi quy (regression) được tính là một phần bộ test. (AC-1, AC-2)
- **FR-018**: Mỗi lần chạy smoke test/benchmark MUST lưu: seed, cấu hình, phiên bản thư viện, hash mô hình và kết quả, để kiểm chứng lại. (AC-3, AC-5)
- **FR-019**: Hệ thống MUST NOT bắt đầu hoặc bao gồm PPO, mô hình toàn thân, đối kháng MMA, hoặc rule engine trong M0 (xem Out of Scope). (AC-1)
- **FR-020**: Báo cáo nghiệm thu M0 MUST theo mẫu báo cáo cột mốc của dự án (Milestone · thành phần hoàn thành · tệp tạo/sửa · cách chạy · test đã chạy và kết quả · benchmark · vấn đề còn lại · tiêu chí đạt/chưa đạt · đề xuất cột mốc tiếp theo), phân biệt rõ kết quả đo thực tế với giả định, và nêu lỗi/giới hạn của thành phần chưa chạy được. (AC-1, AC-2, AC-3, AC-4, AC-5)

<a id="yeu-cau-phi-chuc-nang-non-functional-requirements"></a>
### Yêu cầu phi chức năng (Non-Functional Requirements)

- **NFR-REL-001**: Độ tin cậy số học (numerical reliability) của smoke test. Ngưỡng: 0 giá trị NaN và 0 giá trị Inf trên mọi mẫu kích hoạt đã thử. Đo bằng: `python scripts/smoke_test.py` (thoát mã 0 và số đếm NaN/Inf in ra bằng 0). (AC-2)
- **NFR-PERF-001**: Độ tin cậy của phép đo hiệu năng. Ngưỡng: ≥ 5 lần lặp đo cho mỗi con số steps/second, kèm độ phân tán giữa các lần lặp. Đo bằng: `python scripts/benchmark.py` (báo cáo ghi số lần lặp). (AC-3)
- **NFR-REPRO-001**: Tính tái lập (reproducibility) của smoke test. Ngưỡng: 0 khác biệt về kết luận đạt/không đạt và số đếm NaN/Inf giữa 2 lần chạy cùng seed. Đo bằng: `python -m pytest` (test tất định theo seed). (AC-2)
- **NFR-DOC-001**: Đầy đủ của báo cáo nghiệm thu. Ngưỡng: 5/5 tiêu chí AC-1…AC-5 có trạng thái và bằng chứng. Đo bằng: kiểm tra báo cáo M0 trong `logs/` bằng `python -m pytest`. (AC-1, AC-2, AC-3, AC-4, AC-5)

<a id="bat-bien-invariants"></a>
### Bất biến (Invariants)

- **INV-001**: Mọi con số trong báo cáo (steps/second, RAM, GPU memory, số NaN/Inf) MUST đến từ phép đo thực tế của lần chạy đó; số không đo được MUST ghi "không đo được" hoặc "chưa chạy", không điền giá trị giả định.
- **INV-002**: Với cùng seed, cùng cấu hình và cùng phiên bản thư viện, kết luận đạt/không đạt và số đếm NaN/Inf của smoke test MUST giống nhau giữa các lần chạy.
- **INV-003**: Tài liệu, báo cáo và mã trong repo MUST NOT chứa bí mật hay đường dẫn tuyệt đối riêng của máy một người.
- **INV-004**: Trong đường chạy chính của M0, mọi actuator của mô hình MUST là cơ (muscle actuator); số actuator không phải cơ MUST bằng 0 và được ghi trong báo cáo. Vector kích hoạt hợp lệ là [0, 1]; giá trị hiệu dụng sau khi bộ mô phỏng kẹp theo dải điều khiển của mô hình MUST được ghi cạnh giá trị yêu cầu. (AC-1)

<a id="key-entities-include-if-feature-involves-data"></a>
### Key Entities *(include if feature involves data)*

- **Mô hình cơ–xương (Musculoskeletal model)**: mô hình MyoElbow gồm khớp, phân đoạn xương và 6 cơ (muscle actuator); thuộc tính chính: số cơ, số bậc tự do, giới hạn góc khớp, giới hạn lực cơ, hash mô hình.
- **Vector kích hoạt cơ (Muscle activation vector)**: danh sách 6 giá trị trong [0, 1], một giá trị cho mỗi cơ; là đầu vào điều khiển duy nhất của mô hình.
- **Kết quả smoke test (Smoke test result)**: đạt/không đạt, số NaN, số Inf, cảnh báo vật lý, mẫu kích hoạt đã thử, seed.
- **Báo cáo benchmark (Benchmark report)**: physics steps/second, số lần lặp, độ phân tán, peak RAM, GPU memory, cấu hình đo, phiên bản thư viện, thông tin phần cứng.
- **Hồ sơ môi trường (Environment profile)**: hệ điều hành/WSL2, phiên bản Python, driver NVIDIA, phiên bản CUDA, tập phiên bản thư viện đã khoá trong lockfile.
- **Báo cáo nghiệm thu M0 (M0 acceptance report)**: trạng thái đạt/chưa đạt của AC-1…AC-5 kèm bằng chứng và vấn đề còn lại.

<a id="success-criteria-mandatory"></a>
## Success Criteria *(mandatory)*

<a id="measurable-outcomes"></a>
### Measurable Outcomes

- **SC-001**: Ít nhất 1 mô hình cơ–xương điều khiển bằng cơ (MyoElbow, 6 cơ) chạy hết một phiên mô phỏng headless với kích hoạt hợp lệ mà không lỗi. (AC-1)
- **SC-002**: Smoke test báo 0 giá trị NaN và 0 giá trị Inf trên mọi mẫu kích hoạt đã thử, và 0 lỗi vật lý. (AC-2)
- **SC-003**: Có 1 báo cáo hiệu năng chứa số physics steps/second đo thực tế, lặp lại nhiều lần với độ phân tán được báo cáo. (AC-3)
- **SC-004**: Có 1 báo cáo ghi peak RAM và GPU memory (hoặc "không khả dụng" kèm nguyên nhân) từ cùng lần đo. (AC-4)
- **SC-005**: Một người làm đúng hướng dẫn trên môi trường sạch dựng lại được môi trường đến lúc smoke test đạt mà không cần thao tác nào ngoài tài liệu. (AC-5)
- **SC-006**: 100% tiêu chí AC-1…AC-5 có trạng thái đạt/chưa đạt kèm bằng chứng trong báo cáo nghiệm thu; không có tiêu chí nào được tuyên bố đạt khi chưa chạy thật.

<a id="out-of-scope"></a>
## Out of Scope

- Huấn luyện PPO hoặc bất kỳ thuật toán RL nào (bắt đầu từ M1).
- Mô hình toàn thân (full-body) và mô hình chi dưới MyoLeg26.
- Môi trường MMA, lồng bát giác (arena), rule engine, self-play, opponent pool.
- Reward, observation system cho đối kháng, constrained RL.
- Lớp sinh lý (physiology): mỏi cơ, năng lượng, damage proxy (M2 trở đi).
- Replay 3D và MuJoCo Viewer (chỉ cần headless ở M0).
- MJX-Warp và đo GPU physics (M9); M0 chỉ đo CPU.
- Benchmark nhiều môi trường song song 1, 2, 4, 8 (thuộc kế hoạch hiệu năng sau M0).
- Các lệnh huấn luyện, đánh giá, replay của mục XIII yêu cầu gốc (ghi "chưa triển khai").
- Tuyên bố tính chính xác sinh học của mô hình hoặc hiệu quả với người thật.

<a id="assumptions"></a>
## Assumptions

- Người dùng là một nhà nghiên cứu/kỹ sư vận hành qua dòng lệnh; không có người dùng cuối hay giao diện đồ hoạ.
- Mô hình MyoElbow 6 cơ có sẵn trong gói MyoSuite/MyoSim chính thức; nếu không, xử lý theo Edge Case, không tự chế mô hình thay thế.
- Môi trường đích là máy Lenovo Legion Pro 5 (RTX 5060 8GB VRAM, Ryzen 9 HX, RAM 32GB), Windows 11 + WSL2 Ubuntu, Python 3.11 làm mục tiêu ban đầu; môi trường phát triển hiện tại (Linux, Python 3.12.3, chưa dò thấy NVIDIA) có thể khác và sẽ được ghi nhận trung thực trong hồ sơ môi trường.
- Phiên bản thư viện tương thích được xác định bằng kiểm tra thực tế ở bước plan; M0 chỉ dùng các thư viện thật sự cần.
- Dữ liệu checkpoint và log nằm trên SSD cục bộ.
- Số liệu hiệu năng của M0 chỉ có giá trị cho đúng cấu hình đo và không dùng để suy ra thời gian huấn luyện.
