---
id: "SPEC-003"
title: "M1 (2/4) — Huấn luyện PPO, checkpoint, hồ sơ tái lập & giao diện quan sát huấn luyện — Spec"
doc_type: spec
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "003-ppo-train-repro"
version: "1.0.0"
---

# Feature Specification: M1 (2/4) — Huấn luyện PPO, checkpoint, hồ sơ tái lập & giao diện quan sát huấn luyện

- [Bối cảnh (Context)](#boi-canh-context)
- [Clarifications](#clarifications)
- [User Scenarios & Testing *(mandatory)*](#user-scenarios-testing-mandatory)
  - [User Story 1 - Chạy huấn luyện PPO cho khuỷu tay bằng một lệnh (Priority: P1)](#user-story-1-chay-huan-luyen-ppo-cho-khuyu-tay-bang-mot-lenh-priority-p1)
  - [User Story 2 - Lưu, nạp checkpoint và train tiếp (Priority: P1)](#user-story-2-luu-nap-checkpoint-va-train-tiep-priority-p1)
  - [User Story 3 - Hồ sơ thí nghiệm đủ trường cho mỗi run (Priority: P1)](#user-story-3-ho-so-thi-nghiem-du-truong-cho-moi-run-priority-p1)
  - [User Story 4 - Cùng seed và cấu hình cho kết quả tái lập (Priority: P1)](#user-story-4-cung-seed-va-cau-hinh-cho-ket-qua-tai-lap-priority-p1)
  - [User Story 5 - Quan sát tiến trình huấn luyện theo thời gian thực (Priority: P1)](#user-story-5-quan-sat-tien-trinh-huan-luyen-theo-thoi-gian-thuc-priority-p1)
  - [User Story 6 - Mạng actor/critic đúng cấu hình đã khai (Priority: P2)](#user-story-6-mang-actorcritic-dung-cau-hinh-da-khai-priority-p2)
  - [User Story 7 - Stage chưa hỗ trợ báo rõ "chưa triển khai" (Priority: P2)](#user-story-7-stage-chua-ho-tro-bao-ro-chua-trien-khai-priority-p2)
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

**Feature Branch**: `003-ppo-train-repro` (tên thư mục feature; không tạo nhánh git mới)

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "REQ-0102 — Là nhà nghiên cứu RL, tôi cần huấn luyện PPO cho khuỷu tay, lưu/nạp checkpoint và hồ sơ thí nghiệm tái lập được. Con 2/4 của Milestone M1 (Single-Arm Muscle Control); nguồn: `docs/00-input/split/yeu-cau-a7634ac9/request-2.md`, kèm bổ sung của người dùng C-0009 (giao diện quan sát huấn luyện thời gian thực)."

<a id="boi-canh-context"></a>
## Bối cảnh (Context)

Dự án MMA-AI-LAB (mô phỏng cơ–xương 3D, học tăng cường — RL) đi theo các cột mốc M0–M9. Feature này là **con 2/4 của M1 — Single-Arm Muscle Control**, kế tiếp `002-elbow-muscle-env` (con 1: môi trường khuỷu tay điều khiển bằng 6 cơ và tập mục tiêu train/test); M1 chỉ được coi là xong khi M0 (`001-m0-physics-benchmark`) đạt nghiệm thu. Nó **tiêu thụ** môi trường của con 1 và **cung cấp** policy, checkpoint, nhật ký huấn luyện và hồ sơ thí nghiệm cho con 3 (đánh giá & biểu đồ) và con 4 (replay 3D & demo).

PPO là thuật toán baseline của dự án (master plan 9.1). Người dùng là **nhà nghiên cứu RL**: chạy một lệnh huấn luyện, theo dõi tiến trình, tiếp tục từ checkpoint, và cần mỗi lần chạy tái lập được. Nỗi đau hiện tại: chưa có pipeline huấn luyện; kết quả khó tái lập nếu không lưu seed, cấu hình và phiên bản; và người chạy chỉ biết huấn luyện đang diễn ra thế nào khi đọc log sau khi xong. Phần cứng đích: RTX 5060 8GB, Ryzen 9 HX, 32GB RAM.

Bổ sung C-0009 của người dùng (là một phần của yêu cầu con 2 và là ràng buộc cho mọi stage train sau này): **mọi bước huấn luyện phải có giao diện hiển thị để người quan sát được khi đang train**, không chỉ đọc log sau; giao diện chỉ đọc dữ liệu train, không điều khiển hay sửa policy, và không thay replay 3D/demo của con 4.

<a id="clarifications"></a>
## Clarifications

- Tự chốt: Mã tiêu chí chấp nhận giữ nguyên AC-1…AC-6 của yêu cầu REQ-0102 (mục 6), không gộp, không bỏ; mỗi AC có ít nhất một Acceptance Scenario ghi đúng mã. Bổ sung C-0009 của người dùng ("KQ/AC mới") được ghi thành **AC-7** (tiêu chí mới, nối tiếp AC-6) và FR riêng; nó không có trong tệp `request-2.md` mà đến từ chỉ dẫn bổ sung của người dùng nên được ghi nguồn ở đây.
- Q: Giao diện quan sát (C-0009) thuộc phạm vi vì chính người dùng đã đưa vào phạm vi con 2; vì vậy không phải mở rộng phạm vi do agent tự thêm. Hình thức giao diện (TensorBoard + bảng điều khiển web nhẹ, MuJoCo Viewer đọc checkpoint mới nhất, hay cả hai) là quyết định kỹ thuật được yêu cầu giao cho bước plan — cần người dùng xác nhận phạm vi — Lý do → A: Đồng ý (người dùng, C-0010): giao diện quan sát training thuộc phạm vi con 2; hình thức (TensorBoard, dashboard web nhẹ, MuJoCo Viewer đọc checkpoint mới nhất, hoặc kết hợp) để bước plan quyết định, kèm lý do và chi phí đo được; chỉ-đọc, chạy tiến trình riêng, không kéo chậm vòng train. (người, Q-0001)
- Tự chốt: Tự cài PPO hay dùng thư viện (ví dụ Stable-Baselines3) → để bước plan quyết định bằng kiểm tra cài thật, với điều kiện bắt buộc là thoả actor/critic 2×256, chuẩn hoá observation, gradient clipping, lưu/nạp đủ trạng thái — lý do: yêu cầu §8 giao plan quyết định; spec chỉ đặc tả hành vi và kết quả.
- Tự chốt: Siêu tham số PPO (tốc độ học, ngưỡng clip, số bước mỗi lượt, tổng số bước) và tần số checkpoint → là tham số cấu hình được trong một cấu hình duy nhất; giá trị khởi đầu thông dụng chốt ở plan và ghi rõ là chưa tinh chỉnh; mặc định khởi đầu tần số checkpoint là mỗi 10 lượt cập nhật — lý do: yêu cầu §8 ghi [KHÔNG BIẾT] cần benchmark; master plan XI.10 cấm giả định thời gian huấn luyện nên spec KHÔNG nêu tổng số bước hay thời gian huấn luyện đạt kết quả.
- Tự chốt: Lượt train ngắn (smoke) của KQ-1 → tối đa 4 096 bước môi trường (2 lượt cập nhật với 2 048 bước mỗi lượt), cấu hình được — lý do: yêu cầu để mở; đủ để kiểm đường chạy và NaN/Inf mà không giả định thời gian huấn luyện thật.
- Tự chốt: Dung sai nạp checkpoint (KQ-2, AC-2) → trên cùng thiết bị tính toán, sai khác tuyệt đối lớn nhất giữa hành động xác định (giá trị trung bình của policy, không lấy mẫu) trước khi lưu và sau khi nạp ≤ 1×10⁻⁶ trên mỗi phần tử, với một lô observation mẫu cố định gồm 64 observation — lý do: sai số dấu phẩy động đơn; số cấu hình được.
- Tự chốt: "Đường reward đầu kỳ" và dung sai tái lập (KQ-4, AC-4) → đường reward đầu kỳ là reward trung bình mỗi episode ở K lượt cập nhật đầu với K = min(10, số lượt thực chạy); hai run cùng seed, cùng cấu hình, cùng phiên bản thư viện, cùng loại thiết bị (cùng CPU hoặc cùng GPU) lệch nhau không quá 1×10⁻⁶ về sai số tương đối tại mỗi điểm — lý do: yêu cầu §8 ghi [KHÔNG BIẾT]; tính tất định trên cùng thiết bị là kỳ vọng thực tế, ngưỡng cấu hình được và chốt lại sau khi đo ở plan.
- Tự chốt: Tái lập giữa GPU và CPU (yêu cầu §8) → KHÔNG cam kết kết quả giống nhau giữa hai loại thiết bị; hồ sơ ghi loại thiết bị đã dùng và so sánh tái lập chỉ có nghĩa giữa hai run cùng loại thiết bị — lý do: thứ tự phép tính dấu phẩy động khác nhau giữa CPU và GPU, đòi bằng nhau là đòi thứ không đạt được; giá trị dung sai GPU↔GPU do plan đo.
- Tự chốt: Thư mục run → mỗi lần chạy `train.py` tạo MỘT thư mục run mới có mã định danh duy nhất (gồm thời điểm UTC, stage, seed); thư mục đã tồn tại KHÔNG bị ghi đè, nếu trùng thì tạo mã khác hoặc dừng với lỗi rõ. "Tiếp tục từ checkpoint" cũng tạo run mới, ghi run/checkpoint cha trong hồ sơ — lý do: ràng buộc dữ liệu của yêu cầu ("không ghi đè run cũ").
- Tự chốt: Mã thoát của CLI → 0 khi thành công; khác 0 cho stage chưa triển khai (AC-5) và cho mọi lỗi huấn luyện; giá trị số cụ thể chốt ở plan — lý do: yêu cầu chỉ đòi "khác 0".
- Tự chốt: Huấn luyện chỉ lấy mục tiêu từ **tập train** của con 1; tập test bị cấm dùng khi train — lý do: con 3 đánh giá trên tập mục tiêu kiểm thử "chưa dùng khi train" (yêu cầu gốc M1, con 3); rò rỉ ở đây làm hỏng đánh giá ở con 3.
- Tự chốt: Chuẩn hoá observation do PPO ở con 2 làm (ước lượng chạy trung bình/độ lệch chuẩn, nằm trong trạng thái checkpoint); môi trường con 1 chỉ trả observation đã có cận hữu hạn — lý do: nghiên cứu Phase 0 của con 1 đã giao việc này cho con 2, yêu cầu §4 đòi lưu trạng thái bộ chuẩn hoá trong checkpoint.
- Tự chốt: Mức cập nhật của giao diện quan sát (AC-7) → số liệu mới hiện lên giao diện trong tối đa 5 giây sau khi được ghi, cấu hình được; số liệu hiển thị tối thiểu gồm reward, loss, kích hoạt của 6 cơ, env steps/s, số bước đã chạy / tổng, trạng thái checkpoint — lý do: yêu cầu C-0009 liệt kê các số liệu này; "cập nhật định kỳ" cần một số đo được.
- Tự chốt: Ngân sách chi phí của giao diện quan sát → bật giao diện làm tốc độ huấn luyện (env steps/s) giảm không quá 10% so với tắt, cùng seed và cấu hình; giao diện 3D (nếu plan chọn) chạy ở tiến trình riêng, mặc định tắt, bật/tắt được — lý do: master plan XI.8 cấm mô phỏng đồ hoạ nặng cùng lúc với train và C-0009 đòi "không kéo chậm vòng train"; con số 10% là ngưỡng khởi đầu, đo trong benchmark và chốt lại ở plan.
- Tự chốt: Quyết định phiên bản `gymnasium` với thư viện PPO/`torch` (việc CHƯA KIỂM mà con 1 giao lại) → plan của feature này kiểm bằng cài thật; nếu buộc lùi `gymnasium` thì đổi ghim ở `pyproject.toml` và chạy lại kiểm cài sạch của con 1 — lý do: nghiên cứu Q1 của con 1.
- Kết luận phân loại: rà các điểm mơ hồ còn lại, không điểm nào đủ cả ba điều kiện (quyết định nghiệp vụ của người dùng · không có tập quán ngành · sai thì đắt), và không có quyết định mở rộng phạm vi nào do agent tự thêm (giao diện quan sát do chính người dùng đưa vào); nên không có điểm nào cần dừng chờ người trả lời. Ba câu hỏi mở của yêu cầu (§8) đều đã được xử lý ở các dòng Tự chốt trên.

<a id="user-scenarios-testing-mandatory"></a>
## User Scenarios & Testing *(mandatory)*

<a id="user-story-1-chay-huan-luyen-ppo-cho-khuyu-tay-bang-mot-lenh-priority-p1"></a>
### User Story 1 - Chạy huấn luyện PPO cho khuỷu tay bằng một lệnh (Priority: P1)

**Tần suất**: hằng ngày — nhà nghiên cứu RL chạy lượt train (smoke hoặc thật) khoảng 3–8 lần mỗi ngày trong giai đoạn M1.

Nhà nghiên cứu chạy `python scripts/train.py --stage elbow --seed 42` trên môi trường khuỷu tay xanh của con 1. Lệnh huấn luyện PPO với hành động liên tục (kích thích 6 cơ), ghi log TensorBoard (loss, reward, activation), lưu checkpoint định kỳ, và in báo cáo env steps/second cùng thời gian chạy thực (wall-clock) khi kết thúc.

**Why this priority**: Đây là MVP của feature: không có lệnh train chạy được thì không có policy, checkpoint hay hồ sơ nào.

**Independent Test**: Chạy lệnh ở chế độ smoke (cấu hình rút ngắn); kiểm lệnh kết thúc mã 0, thư mục run có log TensorBoard và ít nhất một checkpoint, 0 NaN/Inf.

**Acceptance Scenarios**:

1. **Given** môi trường khuỷu tay xanh (con 1), **When** chạy `python scripts/train.py --stage elbow --seed 42`, **Then** huấn luyện chạy được, ghi log TensorBoard và checkpoint định kỳ. (AC-1)
2. **Given** lượt train ngắn (smoke) cấu hình tối đa 4 096 bước môi trường, **When** lượt kết thúc, **Then** lệnh không lỗi (mã thoát 0) và số giá trị NaN/Inf trong loss và trong tham số mạng đo được bằng 0. (AC-1)
3. **Given** một run đã kết thúc, **When** đọc log TensorBoard của run, **Then** có chuỗi loss, reward và activation của 6 cơ theo bước, đủ để con 3 vẽ biểu đồ. (AC-1)
4. **Given** một run đã kết thúc, **When** đọc báo cáo cuối run, **Then** có env steps/second và thời gian chạy thực (wall-clock) do máy đo, không phải số giả định. (AC-3)
5. **Given** huấn luyện đang chạy, **When** quan sát các hành động mà policy đưa vào môi trường, **Then** mọi hành động đều là kích thích cơ `u_i ∈ [0,1]` cho 6 cơ, không có đường điều khiển trực tiếp lực hay toạ độ tay. (AC-1)

---

<a id="user-story-2-luu-nap-checkpoint-va-train-tiep-priority-p1"></a>
### User Story 2 - Lưu, nạp checkpoint và train tiếp (Priority: P1)

**Tần suất**: hằng ngày — nhà nghiên cứu nạp lại checkpoint để kiểm tra hoặc tiếp tục train khoảng 2–5 lần mỗi ngày; con 3 và con 4 cũng nạp checkpoint.

Checkpoint được lưu định kỳ trong lúc train, gồm trạng thái policy (actor), critic, bộ chuẩn hoá observation, optimizer và seed. Nạp lại checkpoint cho ra policy trả đúng hành động như trước khi lưu trên cùng observation, và có thể tiếp tục train.

**Why this priority**: Checkpoint là đầu ra giá trị nhất của huấn luyện; con 3 và con 4 chỉ đọc checkpoint. Lưu/nạp sai làm hỏng mọi bước sau mà khó phát hiện.

**Independent Test**: Lưu checkpoint từ một policy đang train, nạp vào policy mới, so hành động xác định trên một lô observation mẫu; sau đó train tiếp vài lượt.

**Acceptance Scenarios**:

1. **Given** checkpoint đã lưu, **When** nạp lại, **Then** policy cho cùng hành động xác định trên cùng observation mẫu (sai khác tuyệt đối ≤ 1×10⁻⁶ trên mỗi phần tử, lô 64 observation) và có thể train tiếp. (AC-2)
2. **Given** checkpoint đã nạp, **When** train tiếp từ đó, **Then** huấn luyện chạy, bộ chuẩn hoá observation và optimizer tiếp tục từ trạng thái đã lưu (không khởi tạo lại), và run mới ghi run/checkpoint cha trong hồ sơ. (AC-2)
3. **Given** huấn luyện đang chạy với tần số checkpoint cấu hình (mặc định khởi đầu mỗi 10 lượt cập nhật), **When** đến mốc, **Then** một checkpoint mới được ghi trọn vẹn rồi mới thay thế con trỏ "checkpoint mới nhất"; checkpoint cũ của run không bị ghi đè. (AC-1)
4. **Given** checkpoint bị hỏng hoặc thiếu thành phần (ví dụ thiếu trạng thái bộ chuẩn hoá), **When** nạp, **Then** báo lỗi nêu thành phần thiếu và không trả policy dùng được âm thầm. (AC-2)

---

<a id="user-story-3-ho-so-thi-nghiem-du-truong-cho-moi-run-priority-p1"></a>
### User Story 3 - Hồ sơ thí nghiệm đủ trường cho mỗi run (Priority: P1)

**Tần suất**: hằng ngày — mỗi lần train sinh một hồ sơ; nhà nghiên cứu mở hồ sơ để đối chiếu khoảng 3–8 lần mỗi ngày.

Mỗi run có một thư mục riêng chứa hồ sơ thí nghiệm (run manifest): seed, cấu hình, phiên bản thư viện, hash XML của mô hình, danh sách checkpoint, reward metrics; cùng thông tin phần cứng/tài nguyên (CPU, GPU, RAM, VRAM), env steps/second và wall-clock.

**Why this priority**: Không có hồ sơ thì kết quả không tái lập và không truy vết được; là mục tiêu khai báo của KQ-3.

**Independent Test**: Chạy smoke, mở thư mục run, kiểm hồ sơ theo khuôn (JSON Schema) và đối chiếu từng trường với giá trị thật.

**Acceptance Scenarios**:

1. **Given** một run đã xong, **When** mở thư mục run, **Then** có seed, config, phiên bản thư viện, hash XML, checkpoint, reward metrics. (AC-3)
2. **Given** hồ sơ của một run, **When** đối chiếu hash XML với hồ sơ mô hình của môi trường (con 1), **Then** hai hash SHA-256 giống nhau. (AC-3)
3. **Given** hồ sơ của một run, **When** đọc phần tài nguyên, **Then** có CPU, RAM và, khi máy có GPU, GPU và VRAM đỉnh; khi không có GPU thì trường GPU/VRAM ghi tường minh là không có (`null`), không bỏ trường. (AC-3)
4. **Given** hai run liên tiếp cùng stage và seed, **When** liệt kê thư mục run, **Then** có hai thư mục khác nhau và nội dung run trước không đổi. (AC-3)

---

<a id="user-story-4-cung-seed-va-cau-hinh-cho-ket-qua-tai-lap-priority-p1"></a>
### User Story 4 - Cùng seed và cấu hình cho kết quả tái lập (Priority: P1)

**Tần suất**: hằng tuần — nhà nghiên cứu kiểm tái lập khi đổi mã hoặc phiên bản thư viện, khoảng 1–3 lần mỗi tuần (và trong bộ test tự động mỗi lần đổi mã).

Hai run với cùng seed, cùng cấu hình, cùng phiên bản thư viện và cùng loại thiết bị cho đường reward đầu kỳ giống nhau trong dung sai đã khai. Dung sai và loại thiết bị được ghi trong hồ sơ.

**Why this priority**: Tái lập là yêu cầu xuyên suốt của dự án (master plan XII), nhưng cần có pipeline chạy được (Story 1) trước.

**Independent Test**: Chạy hai run smoke cùng seed/cấu hình rồi so đường reward của K lượt cập nhật đầu theo dung sai.

**Acceptance Scenarios**:

1. **Given** hai run cùng seed/cấu hình, **When** so sánh, **Then** kết quả nằm trong dung sai tái lập đã khai (đường reward đầu kỳ lệch ≤ 1×10⁻⁶ sai số tương đối tại mỗi điểm, K = min(10, số lượt thực chạy)). (AC-4)
2. **Given** hai run khác seed, **When** so sánh đường reward đầu kỳ, **Then** chúng khác nhau (chứng minh seed thực sự chi phối kết quả). (AC-4)
3. **Given** hồ sơ của hai run, **When** kiểm tra, **Then** hồ sơ ghi dung sai tái lập đã áp dụng và loại thiết bị (CPU/GPU) đã dùng. (AC-4)

---

<a id="user-story-5-quan-sat-tien-trinh-huan-luyen-theo-thoi-gian-thuc-priority-p1"></a>
### User Story 5 - Quan sát tiến trình huấn luyện theo thời gian thực (Priority: P1)

**Tần suất**: hằng ngày — nhà nghiên cứu mở giao diện quan sát mỗi lần train dài, khoảng 3–8 lần mỗi ngày; ràng buộc áp cho mọi stage train sau này.

Trong lúc `train.py --stage elbow` đang chạy, nhà nghiên cứu mở được một giao diện (cổng/URL hoặc cửa sổ) và thấy tiến trình theo thời gian thực: reward, loss, kích hoạt của 6 cơ, env steps/s, số bước đã chạy / tổng, trạng thái checkpoint; giao diện cập nhật định kỳ và xem được mà không dừng train. Giao diện chỉ đọc dữ liệu train. Hiển thị 3D khuỷu tay do policy điều khiển (nếu có) chạy ở tiến trình riêng, bật/tắt được; train vẫn mặc định headless.

**Why this priority**: Người dùng yêu cầu rõ ràng (C-0009) rằng mọi bước train phải quan sát được khi đang chạy; đây là tiêu chí chấp nhận mới AC-7.

**Independent Test**: Chạy train nền, mở giao diện, kiểm các số liệu liệt kê có mặt và đổi theo thời gian; so env steps/s khi bật/tắt giao diện.

**Acceptance Scenarios**:

1. **Given** `train.py --stage elbow` đang chạy, **When** nhà nghiên cứu mở giao diện quan sát, **Then** thấy reward, loss, kích hoạt của 6 cơ, env steps/s, số bước đã chạy / tổng và trạng thái checkpoint. (AC-7)
2. **Given** giao diện đang mở, **When** huấn luyện tiến thêm, **Then** số liệu cập nhật định kỳ (số liệu mới xuất hiện trong tối đa 5 giây sau khi được ghi) mà train không bị dừng. (AC-7)
3. **Given** cùng seed và cấu hình, **When** so env steps/s giữa lần bật giao diện và lần tắt giao diện, **Then** lần bật giảm không quá 10%, và chi phí CPU/GPU/VRAM của giao diện được đo và ghi lại. (AC-7)
4. **Given** giao diện quan sát đang mở, **When** người dùng thao tác trên giao diện, **Then** không có thao tác nào thay đổi policy, tham số, cấu hình hay tiến trình của lần train. (AC-7)
5. **Given** hiển thị 3D khuỷu tay được bật, **When** train chạy, **Then** hiển thị chạy ở tiến trình riêng, lấy trạng thái từ checkpoint/trạng thái mới nhất, tắt được mà không ảnh hưởng train; khi không bật, train chạy headless. (AC-7)

---

<a id="user-story-6-mang-actorcritic-dung-cau-hinh-da-khai-priority-p2"></a>
### User Story 6 - Mạng actor/critic đúng cấu hình đã khai (Priority: P2)

**Tần suất**: hiếm — nhà nghiên cứu kiểm khi đổi cấu hình mạng, khoảng 1–2 lần mỗi tuần (và trong bộ test tự động).

Cấu hình mạng khai rõ actor MLP 2 lớp × 256 và critic MLP 2 lớp × 256, có chuẩn hoá observation và gradient clipping; kiểm tra mạng đã dựng cho thấy đúng như khai.

**Why this priority**: Cấu hình do master plan 9.1 quy định, nhưng kiểm bằng test cấu trúc đơn giản, không chặn việc chạy train.

**Independent Test**: Dựng mạng từ cấu hình mặc định, đọc cấu trúc (số lớp ẩn, độ rộng), kiểm bộ chuẩn hoá và ngưỡng clip gradient.

**Acceptance Scenarios**:

1. **Given** cấu hình MLP, **When** kiểm tra mạng, **Then** actor và critic đều 2 lớp × 256, có chuẩn hoá observation và gradient clipping. (AC-6)
2. **Given** một bước cập nhật có gradient lớn, **When** kiểm tra chuẩn gradient sau clipping, **Then** nó không vượt ngưỡng clip đã cấu hình. (AC-6)
3. **Given** cấu hình khai độ rộng hoặc số lớp khác, **When** dựng mạng, **Then** cấu trúc thực tế theo cấu hình khai và hồ sơ run ghi cấu trúc đã dùng. (AC-6)

---

<a id="user-story-7-stage-chua-ho-tro-bao-ro-chua-trien-khai-priority-p2"></a>
### User Story 7 - Stage chưa hỗ trợ báo rõ "chưa triển khai" (Priority: P2)

**Tần suất**: hiếm — người dùng gõ nhầm hoặc thử stage sau này, khoảng 1 lần mỗi vài tuần.

CLI chỉ hỗ trợ `--stage elbow` ở M1; mọi stage khác (`balance`, `locomotion`, `selfplay`, hay giá trị lạ) báo rõ "chưa triển khai" và thoát với mã khác 0, không bắt đầu train và không tạo thư mục run giả.

**Why this priority**: Master plan XIII đòi lệnh chưa hỗ trợ phải ghi rõ chưa triển khai; giá trị thấp hơn các story đường chạy chính.

**Independent Test**: Gọi CLI với `--stage balance`, kiểm thông báo và mã thoát.

**Acceptance Scenarios**:

1. **Given** `--stage balance` (hoặc stage chưa hỗ trợ), **When** gọi CLI, **Then** báo rõ "chưa triển khai", mã thoát khác 0. (AC-5)
2. **Given** stage chưa hỗ trợ, **When** CLI thoát, **Then** không có thư mục run hay checkpoint nào được tạo. (AC-5)

---

<a id="edge-cases"></a>
### Edge Cases

- Loss hoặc tham số mạng xuất hiện NaN/Inf giữa lúc train: huấn luyện dừng với lỗi rõ (nêu lượt cập nhật, đại lượng), không ghi checkpoint chứa NaN/Inf và giữ nguyên checkpoint hợp lệ gần nhất; mã thoát khác 0. (AC-1)
- Môi trường (con 1) báo lỗi mất ổn định vật lý (NaN/Inf, cảnh báo vật lý) giữa lượt: lỗi được chuyển nguyên văn tới người chạy cùng bước huấn luyện, không nuốt âm thầm; run ghi trạng thái "lỗi". (AC-1)
- Ổ đĩa đầy hoặc không ghi được checkpoint: huấn luyện báo lỗi rõ và dừng, không tiếp tục chạy mà không có checkpoint như đã khai. (AC-1)
- Chạy hai lần liên tiếp cùng stage và seed: tạo hai thư mục run khác nhau, không ghi đè; mã định danh run trùng (cùng giây) vẫn cho thư mục khác nhau hoặc báo lỗi rõ. (INV-001)
- Nạp checkpoint có hình dạng mạng khác với cấu hình hiện tại (ví dụ độ rộng khác): báo lỗi nêu khác biệt, không nạp một nửa. (AC-2)
- Nạp checkpoint do phiên bản thư viện khác lưu: cảnh báo rõ phiên bản lưu và phiên bản hiện tại, vẫn cho nạp nếu cấu trúc khớp; hồ sơ run mới ghi cả hai phiên bản. (AC-2)
- Nạp checkpoint ghi hash XML khác với hash XML của mô hình hiện tại: từ chối train tiếp (hoặc cảnh báo rõ nếu chỉ nạp để suy luận) vì policy không còn khớp mô hình. (AC-2)
- Train tiếp từ checkpoint không bắt đầu lại từ seed ban đầu một cách im lặng: trạng thái sinh số ngẫu nhiên được khôi phục từ checkpoint, hồ sơ ghi seed gốc và seed tiếp tục. (INV-004)
- Máy không có GPU hoặc CUDA không dùng được: train chạy trên CPU, hồ sơ ghi loại thiết bị; không giả lập GPU và không lỗi. (AC-3)
- Máy không có màn hình (`DISPLAY` bỏ đặt): train và giao diện web (nếu dùng) vẫn chạy; chỉ hiển thị 3D cần màn hình và nếu thiếu thì báo rõ rằng 3D không khả dụng, không làm hỏng train. (AC-7)
- Cổng giao diện đã bị chiếm hoặc giao diện quan sát không khởi động được: train vẫn chạy bình thường, cảnh báo rõ lý do giao diện không có; không dừng train vì giao diện. (AC-7)
- Giao diện quan sát mở khi train chưa ghi số liệu nào hoặc đã kết thúc: hiển thị trạng thái "chưa có dữ liệu" hoặc "đã kết thúc" kèm số liệu cuối, không lỗi. (AC-7)
- Giao diện quan sát hoặc tiến trình 3D bị đóng đột ngột: lần train không bị ảnh hưởng (không dừng, không mất checkpoint). (INV-005)
- Mọi truy vấn hoặc thao tác từ giao diện chỉ đọc dữ liệu train; không có đường nào để giao diện ghi vào checkpoint, cấu hình hay tiến trình train. (INV-005)
- Huấn luyện lấy mục tiêu: mọi mục tiêu dùng khi train thuộc tập train của môi trường; không bao giờ bốc từ tập test. (INV-003)
- Policy cho ra hành động ngoài `[0,1]` trước khi ánh xạ (đầu ra thô của mạng): hành động đưa vào môi trường luôn nằm trong `[0,1]^6`; không để môi trường từ chối hành động của chính policy. (INV-002)
- Cấu hình khai tần số checkpoint bằng 0 hoặc tổng số bước ≤ 0: CLI từ chối với thông báo nêu giá trị không hợp lệ, không bắt đầu train. (AC-1)

<a id="requirements-mandatory"></a>
## Requirements *(mandatory)*

<a id="functional-requirements"></a>
### Functional Requirements

- **FR-001**: Hệ thống MUST cung cấp lệnh `python scripts/train.py --stage elbow --seed 42` chạy huấn luyện PPO hành động liên tục trên môi trường khuỷu tay của con 1; `--seed` MUST điều khiển mọi nguồn ngẫu nhiên của lần train. (AC-1)
- **FR-002**: Policy PPO MUST gồm actor MLP 2 lớp × 256 và critic MLP 2 lớp × 256, chuẩn hoá observation và gradient clipping; cấu trúc mạng MUST nằm ở cấu hình, không rải hằng số trong mã (mô-đun `ppo.py`). (AC-6)
- **FR-003**: Bộ chuẩn hoá observation MUST ước lượng thống kê trong lúc train, áp lên observation trước khi vào actor và critic, và thống kê MUST nằm trong trạng thái checkpoint. (AC-2, AC-6)
- **FR-004**: Gradient clipping MUST được áp ở mỗi bước cập nhật với ngưỡng cấu hình được, và chuẩn gradient sau clipping MUST không vượt ngưỡng. (AC-6)
- **FR-005**: Hành động đưa vào môi trường MUST là kích thích cơ `u_i ∈ [0,1]` cho 6 cơ; policy MUST NOT có đường điều khiển trực tiếp lực hay toạ độ tay, và MUST NOT dùng position controller thay cơ. (AC-1)
- **FR-006**: Hệ thống MUST lưu checkpoint định kỳ theo tần số cấu hình được (mặc định khởi đầu mỗi 10 lượt cập nhật); mỗi checkpoint MUST gồm trạng thái actor, critic, bộ chuẩn hoá observation, optimizer, seed và trạng thái sinh số ngẫu nhiên, cùng hash XML của mô hình và phiên bản thư viện. (AC-1, AC-2)
- **FR-007**: Hệ thống MUST ghi checkpoint trọn vẹn rồi mới công bố là mới nhất, MUST NOT ghi đè checkpoint cũ của cùng run, và MUST NOT ghi checkpoint chứa NaN/Inf. (AC-1, AC-2)
- **FR-008**: Hệ thống MUST nạp checkpoint để suy luận hoặc train tiếp; sau khi nạp, hành động xác định trên cùng observation mẫu MUST giống trước khi lưu trong dung sai đã khai (≤ 1×10⁻⁶ tuyệt đối trên mỗi phần tử, lô 64 observation); khi checkpoint hỏng, thiếu thành phần hoặc khác cấu trúc mạng MUST báo lỗi nêu nguyên nhân. (AC-2)
- **FR-009**: Train tiếp từ checkpoint MUST khôi phục optimizer, bộ chuẩn hoá observation và trạng thái sinh số ngẫu nhiên, và MUST tạo run mới có ghi run/checkpoint cha. (AC-2)
- **FR-010**: Hệ thống MUST ghi log TensorBoard gồm loss, reward và activation của 6 cơ theo bước, ở dạng đủ để con 3 vẽ biểu đồ loss · reward · activation. (AC-1)
- **FR-011**: Mỗi lần chạy MUST tạo một thư mục run mới, duy nhất, chứa hồ sơ thí nghiệm (run manifest) theo khuôn JSON Schema với: seed, cấu hình đầy đủ, phiên bản các thư viện, hash SHA-256 của XML mô hình, danh sách checkpoint, reward metrics; MUST NOT ghi đè thư mục run cũ. (AC-3)
- **FR-012**: Hồ sơ run MUST ghi thêm loại thiết bị tính toán (CPU/GPU) và tài nguyên: CPU, RAM, và GPU/VRAM đỉnh khi có GPU; trường không áp dụng MUST ghi tường minh `null`, không bỏ trường. (AC-3)
- **FR-013**: Hệ thống MUST báo cáo env steps/second và thời gian chạy thực (wall-clock) của lần train, do máy đo, và MUST NOT suy ra hay dự đoán thời gian huấn luyện từ số khác. (AC-3)
- **FR-014**: Hồ sơ run MUST ghi dung sai tái lập đã áp dụng và loại thiết bị; hệ thống MUST cung cấp phép so sánh hai run theo dung sai (đường reward đầu kỳ: K = min(10, số lượt thực chạy) lượt cập nhật đầu, lệch tương đối ≤ 1×10⁻⁶), chỉ có nghĩa giữa hai run cùng loại thiết bị. (AC-4)
- **FR-015**: CLI MUST chỉ hỗ trợ `--stage elbow`; stage `balance`, `locomotion`, `selfplay` và mọi giá trị chưa hỗ trợ MUST in thông báo rõ "chưa triển khai", thoát với mã khác 0 và không tạo thư mục run. (AC-5)
- **FR-016**: Huấn luyện MUST lấy mục tiêu chỉ từ tập train của môi trường (con 1) và MUST NOT dùng tập test. (AC-1)
- **FR-017**: Khi loss hoặc tham số xuất hiện NaN/Inf, hoặc môi trường báo mất ổn định, hoặc không ghi được checkpoint, hệ thống MUST dừng với lỗi rõ và mã thoát khác 0, ghi trạng thái lỗi vào hồ sơ run. (AC-1)
- **FR-018**: Tất cả siêu tham số — tốc độ học, ngưỡng clip PPO, số bước mỗi lượt, tổng số bước, tần số checkpoint, ngưỡng clip gradient, cấu trúc mạng, dung sai tái lập, chu kỳ cập nhật giao diện — MUST nằm ở một cấu hình duy nhất được lưu nguyên văn vào hồ sơ run; cấu hình sai (giá trị ≤ 0, thiếu khoá) MUST bị từ chối trước khi train. (AC-1, AC-3)
- **FR-019**: Hệ thống MUST cung cấp bộ test tự động cho: seed xác định (hai run cùng seed), lưu/nạp checkpoint, cấu trúc mạng 2×256 với chuẩn hoá và clipping, stage chưa triển khai, đủ trường hồ sơ run. (AC-2, AC-3, AC-4, AC-5, AC-6)
- **FR-020**: Trong lúc train đang chạy, hệ thống MUST cung cấp một giao diện quan sát mà người dùng mở được (cổng/URL hoặc cửa sổ) và thấy theo thời gian thực: reward, loss, kích hoạt của 6 cơ, env steps/s, số bước đã chạy / tổng, và trạng thái checkpoint; giao diện MUST cập nhật định kỳ và MUST xem được mà không dừng train. (AC-7)
- **FR-021**: Giao diện quan sát MUST chỉ đọc dữ liệu train; MUST NOT điều khiển, sửa policy, tham số, cấu hình hay tiến trình train. Yêu cầu này áp cho mọi stage train về sau. (AC-7)
- **FR-022**: Nếu có hiển thị 3D khuỷu tay do policy điều khiển, nó MUST chạy ở tiến trình riêng, bật/tắt được và mặc định tắt; train MUST mặc định headless; việc bật giao diện MUST NOT kéo chậm vòng train quá ngưỡng NFR-PERF-001. (AC-7)
- **FR-023**: Chi phí CPU/GPU/VRAM của giao diện quan sát MUST được đo trong benchmark và ghi vào hồ sơ benchmark; giao diện không khởi động được MUST NOT làm dừng train. (AC-7)
- **FR-024**: Hệ thống MUST ghi rõ hình thức giao diện quan sát đã chọn, lý do chọn và chi phí đo được trong kế hoạch của feature (quyết định thuộc plan). (AC-7)

<a id="yeu-cau-phi-chuc-nang-non-functional-requirements"></a>
### Yêu cầu phi chức năng (Non-Functional Requirements)

- **NFR-REL-001**: Độ tin cậy số học của lượt train ngắn (smoke).
  Ngưỡng: 0 giá trị NaN và 0 giá trị Inf trong loss và trong tham số mạng sau lượt smoke tối đa 4 096 bước môi trường, mã thoát 0.
  Đo bằng: `python -m pytest` (bộ test smoke train) và bộ đếm NaN/Inf trong hồ sơ run. (AC-1)
- **NFR-REPRO-001**: Tính tất định theo seed trên cùng loại thiết bị.
  Ngưỡng: lệch tương đối ≤ 1×10⁻⁶ tại mỗi điểm của đường reward đầu kỳ (K = min(10, số lượt thực chạy)) giữa hai run cùng seed, cấu hình, phiên bản thư viện, loại thiết bị; sai khác tuyệt đối ≤ 1×10⁻⁶ của hành động xác định sau lưu/nạp checkpoint.
  Đo bằng: `python -m pytest` (test hai run cùng seed; test lưu/nạp checkpoint). (AC-2, AC-4)
- **NFR-PERF-001**: Chi phí của giao diện quan sát đối với vòng train.
  Ngưỡng: env steps/s khi bật giao diện ≥ 90% env steps/s khi tắt (cùng seed, cùng cấu hình, cùng máy), tức giảm ≤ 10%.
  Đo bằng: script benchmark so sánh hai lần chạy bật/tắt giao diện, ghi vào hồ sơ benchmark (`python scripts/benchmark.py` hoặc lệnh tương đương do plan chốt). (AC-7)
- **NFR-PERF-002**: Độ trễ cập nhật của giao diện quan sát.
  Ngưỡng: ≤ 5 giây từ lúc số liệu được ghi đến lúc hiện trên giao diện (chu kỳ cập nhật cấu hình được).
  Đo bằng: test đo độ trễ giữa dấu thời gian ghi số liệu và dấu thời gian lần làm mới giao diện. (AC-7)
- **NFR-RES-001**: Ghi nhận tài nguyên trong hồ sơ run.
  Ngưỡng: 100% hồ sơ run có đủ các trường CPU, RAM, GPU, VRAM, env steps/second và wall-clock (trường không áp dụng ghi `null`).
  Đo bằng: `python -m pytest` (test hợp đồng hồ sơ run theo JSON Schema). (AC-3)
- **NFR-HEADLESS-001**: Train chạy không đồ hoạ.
  Ngưỡng: lượt smoke chạy hết khi biến `DISPLAY` không đặt, mã thoát 0.
  Đo bằng: `python -m pytest` (test chạy smoke với `DISPLAY` bỏ đặt). (AC-1, AC-7)

<a id="bat-bien-invariants"></a>
### Bất biến (Invariants)

- **INV-001**: Mỗi lần chạy train MUST có thư mục run riêng; thư mục run đã tồn tại MUST NOT bị ghi đè hoặc sửa bởi lần chạy khác (kể cả train tiếp từ checkpoint, vốn tạo run mới). (AC-3)
- **INV-002**: Mọi hành động policy đưa vào môi trường MUST nằm trong `[0,1]^6` và là kích thích cơ; policy MUST NOT điều khiển trực tiếp lực hay toạ độ tay (kế thừa INV-003 của con 1). (AC-1)
- **INV-003**: Huấn luyện MUST chỉ dùng mục tiêu thuộc tập train; tập test MUST NOT bao giờ xuất hiện trong lúc train (bảo vệ đánh giá ở con 3). (AC-1)
- **INV-004**: Checkpoint MUST đủ trạng thái để khứ hồi: nạp lại cho cùng hành động xác định (trong dung sai) và train tiếp liên tục (policy, critic, bộ chuẩn hoá observation, optimizer, seed, trạng thái sinh số ngẫu nhiên); checkpoint MUST NOT chứa NaN/Inf. (AC-2)
- **INV-005**: Giao diện quan sát MUST chỉ đọc; việc nó mở, đóng, lỗi hoặc không khởi động MUST NOT làm thay đổi policy, checkpoint, cấu hình hay làm dừng train. (AC-7)

<a id="key-entities-include-if-feature-involves-data"></a>
### Key Entities *(include if feature involves data)*

- **Lần chạy huấn luyện (Run)**: một lần thực thi `train.py` cho một stage và một seed; có mã định danh duy nhất, thư mục riêng, trạng thái (đang chạy · xong · lỗi) và run cha khi train tiếp.
- **Hồ sơ thí nghiệm (Run manifest)**: bản ghi theo khuôn JSON Schema của một run: seed, cấu hình đầy đủ, phiên bản thư viện, hash SHA-256 XML, danh sách checkpoint, reward metrics, loại thiết bị, tài nguyên (CPU/GPU/RAM/VRAM), env steps/second, wall-clock, dung sai tái lập.
- **Checkpoint**: trạng thái đã lưu của một run tại một mốc: actor, critic, bộ chuẩn hoá observation, optimizer, seed và trạng thái sinh số ngẫu nhiên, hash XML, phiên bản thư viện; con 3 và con 4 chỉ đọc.
- **Cấu hình huấn luyện (Training config)**: siêu tham số PPO, cấu trúc mạng (2×256), ngưỡng clip, tần số checkpoint, tổng số bước, dung sai tái lập, chu kỳ cập nhật giao diện; lưu nguyên văn trong hồ sơ.
- **Nhật ký huấn luyện (Training log)**: chuỗi loss, reward, activation của 6 cơ theo bước (TensorBoard) do run ghi; con 3 đọc để vẽ biểu đồ.
- **Ảnh chụp tiến trình (Progress snapshot)**: số liệu hiện thời của run (reward, loss, kích hoạt 6 cơ, env steps/s, số bước đã chạy / tổng, trạng thái checkpoint, dấu thời gian) mà giao diện quan sát đọc; chỉ đọc đối với giao diện.

<a id="success-criteria-mandatory"></a>
## Success Criteria *(mandatory)*

<a id="measurable-outcomes"></a>
### Measurable Outcomes

- **SC-001**: Lệnh `python scripts/train.py --stage elbow --seed 42` chạy hết lượt smoke (tối đa 4 096 bước môi trường) với mã thoát 0 và 0 NaN/Inf trong loss và tham số; thư mục run có log TensorBoard và ít nhất một checkpoint. (AC-1)
- **SC-002**: Nạp lại checkpoint cho hành động xác định giống trước khi lưu (sai khác tuyệt đối ≤ 1×10⁻⁶ trên mỗi phần tử, lô 64 observation) và train tiếp được. (AC-2)
- **SC-003**: Mỗi run có đủ 6 mục — seed, config, phiên bản thư viện, hash XML, checkpoint, reward metrics — cùng env steps/second và wall-clock, kiểm bằng test theo khuôn JSON Schema. (AC-3)
- **SC-004**: Hai run cùng seed/cấu hình/thiết bị cho đường reward đầu kỳ lệch ≤ 1×10⁻⁶ sai số tương đối (K = min(10, số lượt thực chạy)); hai run khác seed cho đường khác nhau. (AC-4)
- **SC-005**: `--stage balance` và mọi stage chưa hỗ trợ báo "chưa triển khai", mã thoát khác 0, không tạo thư mục run. (AC-5)
- **SC-006**: Actor và critic đều 2 lớp × 256, có chuẩn hoá observation và gradient clipping, kiểm bằng test cấu trúc. (AC-6)
- **SC-007**: Trong lúc train chạy, giao diện quan sát hiện reward, loss, kích hoạt 6 cơ, env steps/s, số bước đã chạy / tổng và trạng thái checkpoint, cập nhật trong tối đa 5 giây, và bật giao diện làm env steps/s giảm không quá 10%. (AC-7)

<a id="out-of-scope"></a>
## Out of Scope

- Định nghĩa môi trường và reward (con 1).
- Evaluate so với random policy và vẽ biểu đồ (con 3).
- Replay và demo (con 4); giao diện quan sát khi train không thay replay 3D/demo của con 4 (con 4 vẫn là replay episode đã lưu).
- Tối ưu nhiều môi trường song song (chỉ benchmark 1/2/4/8 nếu cần cho quyết định).
- Self-play.
- M2–M9 (mỏi cơ, cân bằng, locomotion, toàn thân, hai võ sĩ, self-play, MJX): chỉ là lộ trình/ràng buộc, không đặc tả hay lập kế hoạch chi tiết.

<a id="assumptions"></a>
## Assumptions

- Người dùng là nhà nghiên cứu RL vận hành qua dòng lệnh và một giao diện quan sát; không có người dùng cuối nào khác.
- Con 1 (`002-elbow-muscle-env`) cung cấp môi trường Gymnasium khuỷu tay, tập mục tiêu train/test và hồ sơ mô hình (hash XML); con 1 và M0 hiện mới có spec + plan, chưa có mã — feature này chỉ hoàn tất khi con 1 đã xanh và M0 đạt nghiệm thu, nhưng việc đặc tả không bị chặn.
- Python 3.11, PyTorch (CUDA khi có), TensorBoard; phần cứng đích RTX 5060 8GB, Ryzen 9 HX, 32GB RAM; mặc định headless, một môi trường, mạng nhỏ.
- Logs và checkpoint nằm trên SSD; đường dẫn gốc của các run là cấu hình được và không là đường dẫn tuyệt đối riêng của máy trong tài liệu.
- Thời gian/ngân sách huấn luyện [KHÔNG BIẾT]; không suy ra thời gian huấn luyện từ bất kỳ con số nào trước khi benchmark (master plan XI.10); spec không khẳng định policy đạt chất lượng nào — việc đó thuộc con 3.
- Không chạy đồ hoạ nặng cùng lúc với train (master plan XI.8); hiển thị 3D, nếu có, là tuỳ chọn ở tiến trình riêng.
- Chỉ M1; M2–M9 không được đặc tả hay lập kế hoạch ở đây.
