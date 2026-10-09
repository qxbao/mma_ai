---
id: "SPEC-005"
title: "M1 (4/4) — Replay 3D và demo khuỷu tay do cơ điều khiển — Spec"
doc_type: spec
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "005-replay-3d-muscle-demo"
version: "1.0.0"
---

# Feature Specification: M1 (4/4) — Replay 3D và demo khuỷu tay do cơ điều khiển

- [Bối cảnh (Context)](#boi-canh-context)
- [Clarifications](#clarifications)
- [User Scenarios & Testing *(mandatory)*](#user-scenarios-testing-mandatory)
  - [User Story 1 - Phát lại 3D một episode đã lưu trong MuJoCo Viewer (Priority: P1)](#user-story-1-phat-lai-3d-mot-episode-da-luu-trong-mujoco-viewer-priority-p1)
  - [User Story 2 - Demo: chạy policy từ checkpoint và xem khuỷu tay tới mục tiêu (Priority: P1)](#user-story-2-demo-chay-policy-tu-checkpoint-va-xem-khuyu-tay-toi-muc-tieu-priority-p1)
  - [User Story 3 - Thấy và ghi lại 6 giá trị activation theo thời gian (Priority: P1)](#user-story-3-thay-va-ghi-lai-6-gia-tri-activation-theo-thoi-gian-priority-p1)
  - [User Story 4 - Episode lưu đủ thông tin để phát lại đúng mô hình (Priority: P1)](#user-story-4-episode-luu-du-thong-tin-de-phat-lai-dung-mo-hinh-priority-p1)
  - [User Story 5 - Máy không có màn hình: báo lỗi rõ hoặc chế độ không màn hình (Priority: P2)](#user-story-5-may-khong-co-man-hinh-bao-loi-ro-hoac-che-do-khong-man-hinh-priority-p2)
  - [User Story 6 - Episode lệch mô hình thì cảnh báo, không phát sai ngầm (Priority: P2)](#user-story-6-episode-lech-mo-hinh-thi-canh-bao-khong-phat-sai-ngam-priority-p2)
  - [User Story 7 - Episode hoặc checkpoint không dùng được thì báo lỗi, mã thoát khác 0 (Priority: P2)](#user-story-7-episode-hoac-checkpoint-khong-dung-duoc-thi-bao-loi-ma-thoat-khac-0-priority-p2)
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

**Feature Branch**: `005-replay-3d-muscle-demo` (tên thư mục feature; không tạo nhánh git mới)

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "REQ-0104 — Là nhà nghiên cứu RL, tôi cần xem replay 3D và demo khuỷu tay do cơ điều khiển để kiểm bằng mắt. Con 4/4 của Milestone M1 (Single-Arm Muscle Control); nguồn: `docs/00-input/split/yeu-cau-a7634ac9/request-4.md`."

<a id="boi-canh-context"></a>
## Bối cảnh (Context)

Dự án MMA-AI-LAB (mô phỏng cơ–xương 3D, học tăng cường — RL) đi theo các cột mốc M0–M9. Feature này là **con 4/4 của M1 — Single-Arm Muscle Control**. Nó kế tiếp `002-elbow-muscle-env` (con 1: môi trường khuỷu tay điều khiển bằng 6 cơ, tập mục tiêu train/test) và `003-ppo-train-repro` (con 2: huấn luyện PPO, checkpoint, hồ sơ run); M1 chỉ được coi là xong khi M0 (`001-m0-physics-benchmark`) đạt nghiệm thu. Con 4 **chỉ đọc** checkpoint/policy của con 2 và dùng môi trường của con 1 để chạy demo; nó **sở hữu lớp hiển thị**: định dạng lưu episode, lệnh `python scripts/replay.py` và việc phát lại 3D. Con 4 độc lập với con 3 (đánh giá & biểu đồ); episode mà con 4 ghi là dữ liệu con 3 hoặc người dùng có thể đọc.

Người dùng là **nhà nghiên cứu RL** (xem hành vi cơ–xương sau mỗi run) và **người xem demo** (xem khuỷu tay chuyển động do kích hoạt cơ, thấy mức activation, khi trình bày). Nỗi đau hiện tại: chỉ có số liệu, chưa thấy được hành vi; khó chứng minh "điều khiển bằng cơ" một cách trực quan. Đồ hoạ nặng được **tách khỏi huấn luyện**: replay là tiến trình riêng, chạy sau/ngoài train, không bao giờ nằm trong vòng train (master plan XI.8). Feature này **không bảo đảm policy "tốt"**: nó chỉ cho thấy đúng những gì đã ghi hoặc đúng những gì policy làm.

<a id="clarifications"></a>
## Clarifications

- Q: Giao diện quan sát (C-0009) thuộc phạm vi vì chính người dùng đã đưa vào phạm vi con 2; vì vậy không phải mở rộng phạm vi do agent tự thêm. Hình thức giao diện (TensorBoard + bảng điều khiển web nhẹ, MuJoCo Viewer đọc checkpoint mới nhất, hay cả hai) là quyết định kỹ thuật được yêu cầu giao cho bước plan — cần người dùng xác nhận phạm vi — Lý do → A: Đồng ý (người dùng, C-0010): giao diện quan sát training thuộc phạm vi con 2; hình thức (TensorBoard, dashboard web nhẹ, MuJoCo Viewer đọc checkpoint mới nhất, hoặc kết hợp) để bước plan quyết định, kèm lý do và chi phí đo được; chỉ-đọc, chạy tiến trình riêng, không kéo chậm vòng train. (người, Q-0001)
- Tự chốt: Ảnh hưởng của Q-0001 (thuộc `003-ppo-train-repro`) lên con 4 → ranh giới: giao diện **quan sát training** (kể cả cửa sổ 3D đọc checkpoint mới nhất lúc đang train) thuộc **con 2** và con 4 không sửa, không thay, không phụ thuộc nó; con 4 sở hữu **replay episode đã ghi + demo một episode từ checkpoint + định dạng episode**, chạy ở tiến trình riêng khi người dùng gọi `scripts/replay.py` — lý do: yêu cầu REQ-0104 (§4) liệt kê đúng ba việc này; Q-0001 giao hình thức giao diện training cho plan của con 2; thêm giao diện training vào con 4 sẽ là mở rộng phạm vi.
- Tự chốt: Mã tiêu chí chấp nhận giữ nguyên AC-1…AC-5 của yêu cầu REQ-0104 (mục 6), không gộp, không bỏ; mỗi AC có ít nhất một Acceptance Scenario ghi đúng mã. Bốn kết quả mong muốn KQ-1…KQ-4 được phủ bởi AC-1…AC-3 và FR-005/FR-007/FR-010 (KQ-3: chế độ không màn hình; KQ-4: 6 activation theo thời gian).
- Tự chốt: Replay từ episode đã ghi, chạy live policy, hay cả hai (câu hỏi mở §8) → **cả hai**, như mặc định yêu cầu đề xuất: `scripts/replay.py --episode <path>` phát lại episode đã lưu (AC-1); `scripts/replay.py --checkpoint <path>` chạy policy từ checkpoint trên môi trường của con 1 và hiển thị trực tiếp (AC-2). Hai chế độ loại trừ nhau trong một lần gọi — lý do: cả hai đều nằm trong mục "Trong" của yêu cầu; một lệnh duy nhất theo kiến trúc `scripts/replay.py` của master plan.
- Tự chốt: Máy có màn hình hay không (WSL2/WSLg — câu hỏi mở §8) → spec **không giả định** có màn hình; mã phải tự phát hiện lúc chạy và coi đường "không có màn hình" là đường chính thức (AC-3). Đã đo: máy phát triển hiện tại là Linux gốc (không phải WSL) có `DISPLAY=:0` và MuJoCo Viewer mở được; WSL2/WSLg **CHƯA KIỂM** — lý do: master plan XII cấm mô tả điều chưa kiểm chứng là đã chạy.
- Tự chốt: Chế độ không màn hình (KQ-3, "[KHÔNG BIẾT: định dạng]") → **`--headless` = kiểm dữ liệu episode và in tóm tắt máy đọc được** (số bước, thời lượng mô phỏng, hash mô hình khớp hay không, activation từng cơ: nhỏ nhất/lớn nhất/trung bình/cuối, kết quả episode). Nó cũng cho phép chạy demo không cần màn hình để **sinh và lưu** episode. **Không** làm "xuất khung ảnh/video không màn hình" — lý do: đã đo ở máy phát triển, dựng hình ngoài màn hình bằng EGL và OSMesa đều không khởi tạo được, còn bằng GLFW cần `DISPLAY`; hứa xuất khung khi không có màn hình là hứa điều không kiểm được; yêu cầu viết "kiểm tra dữ liệu episode **hoặc** xuất khung" nên chọn một đường là đủ.
- Tự chốt: Ngưỡng FPS "mượt" (§3 và §5, "[KHÔNG BIẾT: ngưỡng FPS]") → **không đặt ngưỡng khung/giây tuyệt đối** (chưa đo được trên phần cứng đích RTX 5060; master plan XI.10 cấm giả định); thay bằng ngưỡng đo được trên bộ lập nhịp: ở hệ số tốc độ 1,0 thời gian phát bằng thời gian mô phỏng với sai lệch ≤ 5% (NFR-PERF-001); khi khung dựng chậm hơn nhịp, phiên phát báo rõ tỷ lệ thực đo được thay vì im lặng — lý do: "mượt ở tốc độ thời gian thực" của yêu cầu đo được theo nhịp, còn FPS tuyệt đối phụ thuộc máy.
- Tự chốt: Episode ngắn (đã đo ở `002-elbow-muscle-env`: khuỷu đi từ 0 tới 2,0 rad trong 4 hành động ≈ 0,16 s mô phỏng; tối đa 100 hành động ≈ 4 s) → phát ở tốc độ thời gian thực mặc định (1,0×) có thể quá nhanh để "kiểm bằng mắt"; vì vậy phiên phát có **hệ số tốc độ** (mặc định 1,0) và **chế độ lặp** chỉnh được, cùng **giữ khung cuối** cho tới khi người dùng đóng cửa sổ; lệnh in thời lượng mô phỏng của episode và gợi ý hệ số tốc độ khi episode ngắn hơn 1 s — lý do: mục đích của yêu cầu là kiểm bằng mắt; đây là cách phát, không thêm thực thể, màn hình hay điểm API.
- Tự chốt: "Hash XML khác mô hình hiện tại" (AC-4, "cảnh báo lệch mô hình, không phát lại sai ngầm") → **mặc định dừng** với lỗi nêu cả hai hash và mã thoát khác 0, không mở viewer; người dùng có thể chấp nhận rủi ro bằng cờ tường minh, khi đó cảnh báo "MÔ HÌNH LỆCH" hiện liên tục trên cửa sổ và trong tóm tắt, và vẫn bị từ chối nếu cấu trúc không tương thích (số khớp hoặc số cơ khác) — lý do: phát lại trạng thái của mô hình này lên mô hình khác có thể cho hình sai mà trông hợp lệ; lệch được phép chỉ khi người dùng chủ động biết.
- Tự chốt: "6 giá trị activation" → là **trạng thái kích hoạt cơ** (đầu ra của động học kích hoạt, trong `[0,1]`, cùng đại lượng ở observation của con 1) cho từng cơ trong 6 cơ; kích thích `u_i` (hành động của policy) cũng được ghi vào episode nhưng thứ hiển thị là activation, kèm nhãn tên cơ — lý do: đây là đại lượng "cơ đang kích hoạt đến đâu" mà chứng minh điều khiển bằng cơ; `u` ghi để con 3 hoặc người dùng đối chiếu.
- Tự chốt: Mục tiêu và seed của demo → demo chạy **một episode** trên một mục tiêu chọn bằng chỉ số trong tập chọn được (mặc định tập kiểm thử của con 1, chỉ số 0) với seed cấu hình được (mặc định từ cấu hình replay); policy dùng hành động xác định — lý do: cùng checkpoint + seed + mục tiêu cho cùng episode (NFR-REPRO-001), và mặc định dùng tập kiểm thử để người xem demo thấy mục tiêu chưa dùng khi train.
- Tự chốt: Ghi episode → **không bao giờ ghi ngầm**: episode chỉ được lưu khi người dùng chỉ định đường dẫn; tệp đã tồn tại thì từ chối, không ghi đè — lý do: INV-001 của con 2 coi thư mục run là bất biến; không để con 4 sinh tệp ngoài ý muốn.
- Tự chốt: "Không chạy cùng lúc với huấn luyện nặng" (§5) → được bảo đảm bằng **thiết kế** (replay là tiến trình riêng, chỉ đọc, không import lớp huấn luyện, không sinh tải khi không được gọi), không bằng việc dò và chặn tiến trình train — lý do: dò tiến trình là thêm chức năng ngoài yêu cầu; master plan XI.8 đòi tách, không đòi chặn.
- Tự chốt: Mã thoát của CLI → 0 khi phát xong/người dùng đóng cửa sổ/chế độ không màn hình hoàn tất; khác 0 và phân biệt theo nguyên nhân (tham số sai, checkpoint không dùng được, episode không đọc được, lệch mô hình, không có màn hình, không ghi được); mã thoát phản ánh kết quả phát lại chứ **không** phản ánh lỗi dọn dẹp đồ họa lúc thoát tiến trình (đã đo: MuJoCo Viewer 3.15.0 làm tiến trình sập `SIGSEGV` lúc thoát trên máy phát triển — FR-014); giá trị số cụ thể chốt ở plan — lý do: yêu cầu chỉ đòi "khác 0" cho AC-3/AC-5; AC-1 đòi "không lỗi".
- Kết luận phân loại: rà các điểm mơ hồ còn lại, không điểm nào đủ cả ba điều kiện (quyết định nghiệp vụ của người dùng · không có tập quán ngành · sai thì đắt), và không có quyết định mở rộng phạm vi do agent tự thêm (không thêm giao diện web, không thêm quay video, không thêm đối thủ/arena, không thêm thực thể ngoài các Key Entities dẫn xuất từ mục 4 của yêu cầu); nên không có điểm nào cần dừng chờ người trả lời. Hai câu hỏi mở của yêu cầu (§8) và hai chỗ "[KHÔNG BIẾT]" (§3, §5) đã được xử lý ở các dòng trên.

<a id="user-scenarios-testing-mandatory"></a>
## User Scenarios & Testing *(mandatory)*

<a id="user-story-1-phat-lai-3d-mot-episode-da-luu-trong-mujoco-viewer-priority-p1"></a>
### User Story 1 - Phát lại 3D một episode đã lưu trong MuJoCo Viewer (Priority: P1)

**Tần suất**: hằng ngày — nhà nghiên cứu RL mở replay sau mỗi run, khoảng 2–6 lần mỗi ngày trong giai đoạn M1.

Nhà nghiên cứu chạy `python scripts/replay.py --episode <path>`. MuJoCo Viewer mở và phát lại chuyển động khuỷu tay đúng như đã ghi, kèm mục tiêu; sau khi hết episode, cửa sổ giữ khung cuối cho tới khi đóng.

**Why this priority**: Đây là MVP và là kết quả KQ-1: không phát lại được thì không "kiểm bằng mắt" được gì.

**Independent Test**: Với một episode hợp lệ (sinh bằng demo không màn hình), chạy lệnh trên máy có màn hình; kiểm cửa sổ mở, các khung phát đúng thứ tự từ khung đầu tới khung cuối, thoát mã 0.

**Acceptance Scenarios**:

1. **Given** một episode đã lưu, **When** chạy `python scripts/replay.py --episode <path>`, **Then** MuJoCo Viewer mở và phát lại chuyển động khuỷu tay theo đúng thứ tự các khung đã ghi, từ khung đầu đến khung cuối, không lỗi. (AC-1)
2. **Given** viewer đang phát, **When** quan sát, **Then** mục tiêu của episode hiện trong cảnh tại đúng vị trí đã ghi và đầu mút tay chuyển động theo trạng thái đã ghi. (AC-1)
3. **Given** episode đã phát hết, **When** không có thao tác, **Then** cửa sổ giữ khung cuối mở cho tới khi người dùng đóng; đóng cửa sổ thì lệnh thoát mã 0. (AC-1)
4. **Given** episode ngắn hơn 1 s mô phỏng, **When** phát, **Then** lệnh in thời lượng mô phỏng và gợi ý hệ số tốc độ; với hệ số tốc độ nhỏ hơn 1 hoặc chế độ lặp, viewer phát chậm hơn hoặc lặp lại mà không đổi dữ liệu episode. (AC-1)
5. **Given** chế độ phát thời gian thực (hệ số tốc độ 1,0), **When** phát một episode, **Then** thời gian phát bằng thời gian mô phỏng của episode với sai lệch trong ngưỡng của NFR-PERF-001, hoặc lệnh báo tỷ lệ thực đo được nếu khung dựng chậm hơn nhịp. (AC-1)

---

<a id="user-story-2-demo-chay-policy-tu-checkpoint-va-xem-khuyu-tay-toi-muc-tieu-priority-p1"></a>
### User Story 2 - Demo: chạy policy từ checkpoint và xem khuỷu tay tới mục tiêu (Priority: P1)

**Tần suất**: hằng tuần — nhà nghiên cứu hoặc người trình bày chạy demo khoảng 1–3 lần mỗi tuần khi báo cáo tiến độ.

Người dùng chạy `python scripts/replay.py --checkpoint <path>`. Lệnh nạp policy từ checkpoint của con 2, chạy một episode trên môi trường của con 1 với một mục tiêu và hiển thị trực tiếp khuỷu tay chuyển động tới mục tiêu cùng 6 giá trị activation.

**Why this priority**: KQ-2 và là cách chứng minh "điều khiển bằng cơ" cho người xem: chuyển động có được là do policy kích thích cơ, không do cách nào khác.

**Independent Test**: Với một checkpoint hợp lệ (có thể từ lượt train ngắn), chạy demo; kiểm khuỷu tay chuyển động, mục tiêu hiện, activation hiện, và mọi hành động đưa vào môi trường là kích thích cơ `u_i ∈ [0,1]`.

**Acceptance Scenarios**:

1. **Given** checkpoint hợp lệ, **When** chạy demo, **Then** khuỷu tay chuyển động theo policy trên một episode và mục tiêu của episode hiện trong cảnh; chuyển động kết thúc khi tới mục tiêu hoặc hết số hành động tối đa của môi trường. (AC-2)
2. **Given** demo đang chạy, **When** quan sát, **Then** 6 giá trị activation của 6 cơ hiện kèm tên cơ và cập nhật theo từng khung. (AC-2)
3. **Given** demo đang chạy, **When** kiểm hành động đưa vào môi trường, **Then** mọi hành động là kích thích cơ `u_i ∈ [0,1]` cho 6 cơ do policy xuất; không có đường điều khiển trực tiếp lực hay toạ độ tay và không có position controller thay cơ. (AC-2)
4. **Given** cùng checkpoint, cùng seed và cùng mục tiêu, **When** chạy demo hai lần, **Then** hai episode ghi ra giống nhau trong dung sai của NFR-REPRO-001. (AC-2)
5. **Given** người dùng chọn mục tiêu bằng chỉ số trong tập kiểm thử, **When** chạy demo, **Then** mục tiêu hiện trong cảnh đúng là mục tiêu có chỉ số đó của tập kiểm thử, và chỉ số cùng tập được ghi vào episode nếu có lưu. (AC-2)
6. **Given** người dùng chỉ định đường dẫn lưu episode, **When** demo kết thúc, **Then** episode được lưu đúng đường dẫn đó và phát lại được bằng `--episode`; nếu không chỉ định thì không có tệp nào được ghi. (AC-2)

---

<a id="user-story-3-thay-va-ghi-lai-6-gia-tri-activation-theo-thoi-gian-priority-p1"></a>
### User Story 3 - Thấy và ghi lại 6 giá trị activation theo thời gian (Priority: P1)

**Tần suất**: hằng ngày — mỗi lần xem replay hoặc demo đều thấy activation, khoảng 2–6 lần mỗi ngày.

Trong cả replay lẫn demo, người xem thấy mức activation của từng cơ trong 6 cơ thay đổi theo thời gian, có nhãn tên cơ; cùng chuỗi giá trị đó nằm trong episode đã lưu để con 3 hoặc người dùng đọc lại.

**Why this priority**: KQ-4: activation theo thời gian là bằng chứng "điều khiển bằng cơ" mà số liệu tổng hợp không cho thấy.

**Independent Test**: Phát một episode có activation biết trước; kiểm giá trị hiển thị ở khung k bằng giá trị đã ghi ở khung k, và kiểm tóm tắt không màn hình nêu đúng nhỏ nhất/lớn nhất/trung bình/cuối của từng cơ.

**Acceptance Scenarios**:

1. **Given** viewer đang phát một episode, **When** đọc phần hiển thị activation, **Then** có đủ 6 giá trị, mỗi giá trị gắn tên của một trong 6 cơ, thứ tự và tên khớp `muscle_names` ghi trong episode. (AC-1)
2. **Given** khung thứ k của episode, **When** hiển thị, **Then** 6 giá trị activation hiện đúng bằng 6 giá trị đã ghi ở khung k, và đổi theo khung khi phát. (AC-1)
3. **Given** demo đang chạy, **When** hiển thị, **Then** 6 giá trị activation hiện là activation của mô phỏng ở khung đó, và được ghi vào episode theo từng khung nếu có lưu. (AC-2)
4. **Given** chế độ không màn hình trên một episode, **When** in tóm tắt, **Then** tóm tắt nêu với từng cơ trong 6 cơ: giá trị nhỏ nhất, lớn nhất, trung bình và giá trị cuối của activation, khớp với tính tay từ dữ liệu episode. (AC-3)

---

<a id="user-story-4-episode-luu-du-thong-tin-de-phat-lai-dung-mo-hinh-priority-p1"></a>
### User Story 4 - Episode lưu đủ thông tin để phát lại đúng mô hình (Priority: P1)

**Tần suất**: hằng ngày — mỗi lần ghi một episode để xem lại hoặc chuyển cho người khác, khoảng 2–6 lần mỗi ngày.

Một episode lưu trạng thái theo thời gian, hành động, activation, mục tiêu, seed và hash XML mô hình, đủ để phát lại đúng mô hình và biết nó được sinh từ đâu.

**Why this priority**: Không có định dạng episode đủ thông tin thì replay (AC-1) và phát hiện lệch mô hình (AC-4) đều không làm được; đây là hợp đồng dữ liệu của con 4 với con 3 và với người dùng.

**Independent Test**: Lưu một episode từ demo không màn hình, đọc lại, và kiểm đủ các trường: các khung, hành động, activation 6 cơ, mục tiêu, seed, hash XML, tên cơ, phiên bản định dạng; kiểm không có NaN/Inf.

**Acceptance Scenarios**:

1. **Given** một episode vừa lưu, **When** đọc lại, **Then** có đủ: trạng thái khớp theo thời gian, hành động (kích thích 6 cơ), activation 6 cơ, vị trí mục tiêu, seed, hash XML của mô hình, tên 6 cơ, kết quả episode (kết thúc vì sao, khoảng cách cuối) và phiên bản định dạng. (AC-1)
2. **Given** episode lưu từ checkpoint, **When** đọc hồ sơ nguồn, **Then** nó nêu tên và hash nội dung của checkpoint đã sinh ra nó; với episode không sinh từ checkpoint, trường này là `null` tường minh. (AC-1)
3. **Given** episode đã lưu, **When** đọc hash XML trong episode, **Then** nó bằng hash XML của mô hình lúc ghi và là đầu vào của phép kiểm lệch mô hình khi phát lại. (AC-4)
4. **Given** quá trình ghi bị ngắt hoặc lỗi giữa chừng, **When** kiểm thư mục đích, **Then** không có tệp episode dở dang nào trông như hợp lệ. (AC-5)

---

<a id="user-story-5-may-khong-co-man-hinh-bao-loi-ro-hoac-che-do-khong-man-hinh-priority-p2"></a>
### User Story 5 - Máy không có màn hình: báo lỗi rõ hoặc chế độ không màn hình (Priority: P2)

**Tần suất**: hằng tuần — chạy qua SSH, CI hoặc máy không có hiển thị, khoảng 1–3 lần mỗi tuần.

Trên máy không có màn hình, lệnh replay không treo: nếu người dùng không chọn chế độ không màn hình, lệnh báo lỗi rõ bằng tiếng Việt và gợi ý chế độ đó; nếu chọn `--headless`, lệnh kiểm dữ liệu episode và in tóm tắt máy đọc được (hoặc chạy demo và lưu episode).

**Why this priority**: KQ-3 và AC-3; bộ test tự động chạy ở môi trường này nên nó cũng là nền kiểm thử của cả feature.

**Independent Test**: Với `DISPLAY` và `WAYLAND_DISPLAY` bỏ đặt, chạy `--episode` không kèm `--headless` (kiểm lỗi, mã thoát, thời gian) và kèm `--headless` (kiểm tóm tắt, mã 0).

**Acceptance Scenarios**:

1. **Given** môi trường không có màn hình, **When** chạy replay mà không chọn chế độ không màn hình, **Then** lệnh báo lỗi rõ nêu nguyên nhân (không có màn hình) và gợi ý `--headless`, thoát mã khác 0 trong thời gian ngắn, không treo và không để lại cửa sổ nào. (AC-3)
2. **Given** môi trường không có màn hình, **When** chạy `python scripts/replay.py --episode <path> --headless`, **Then** lệnh không mở viewer, kiểm dữ liệu episode, in tóm tắt đủ trường (số bước, thời lượng mô phỏng, trạng thái khớp mô hình, activation 6 cơ, kết quả episode) và thoát mã 0. (AC-3)
3. **Given** môi trường không có màn hình, **When** chạy `--checkpoint <path> --headless` kèm đường dẫn lưu episode, **Then** lệnh chạy policy một episode không cần màn hình, lưu episode và thoát mã 0. (AC-3)
4. **Given** có biến hiển thị nhưng màn hình không khởi tạo được (hiển thị hỏng hoặc không kết nối được), **When** chạy replay không kèm `--headless`, **Then** lệnh xử lý như trường hợp không có màn hình: báo lỗi rõ, mã khác 0, không treo, không sập tiến trình mà không giải thích. (AC-3)

---

<a id="user-story-6-episode-lech-mo-hinh-thi-canh-bao-khong-phat-sai-ngam-priority-p2"></a>
### User Story 6 - Episode lệch mô hình thì cảnh báo, không phát sai ngầm (Priority: P2)

**Tần suất**: hiếm — chỉ khi file XML mô hình đổi giữa lúc ghi và lúc xem, khoảng 1 lần mỗi vài tuần.

Khi hash XML trong episode khác hash XML của mô hình hiện tại, lệnh nói rõ lệch mô hình và dừng; người dùng chỉ tiếp tục khi chủ động chấp nhận, khi đó cảnh báo luôn hiện.

**Why this priority**: Phát lại trạng thái lên mô hình khác có thể ra hình sai mà trông hợp lệ — đúng loại lỗi "sai ngầm" cần chặn; xếp P2 vì chỉ xảy ra khi mô hình bị đổi.

**Independent Test**: Sửa hash XML trong một episode mẫu rồi phát lại: kiểm lệnh dừng, nêu cả hai hash, mã khác 0; với cờ chấp nhận thì kiểm cảnh báo hiển thị và có trong tóm tắt.

**Acceptance Scenarios**:

1. **Given** episode có hash XML khác mô hình hiện tại, **When** replay, **Then** lệnh cảnh báo lệch mô hình nêu cả hai hash, không mở viewer và không phát, thoát mã khác 0 — không phát lại sai ngầm. (AC-4)
2. **Given** cùng tình huống, **When** người dùng bật cờ chấp nhận lệch rõ ràng và cấu trúc mô hình tương thích, **Then** viewer phát kèm cảnh báo "MÔ HÌNH LỆCH" hiển thị liên tục và tóm tắt ghi `model_match = false`. (AC-4)
3. **Given** hash lệch và cấu trúc không tương thích (số khớp hoặc số cơ khác), **When** replay kể cả có cờ chấp nhận, **Then** lệnh vẫn từ chối và nêu lý do không tương thích. (AC-4)
4. **Given** chế độ không màn hình, **When** chạy trên episode lệch mô hình, **Then** tóm tắt (nếu có cờ chấp nhận) hoặc lỗi (nếu không) nêu rõ lệch và hai hash; không báo "khớp". (AC-4)

---

<a id="user-story-7-episode-hoac-checkpoint-khong-dung-duoc-thi-bao-loi-ma-thoat-khac-0-priority-p2"></a>
### User Story 7 - Episode hoặc checkpoint không dùng được thì báo lỗi, mã thoát khác 0 (Priority: P2)

**Tần suất**: hiếm — gõ nhầm đường dẫn hoặc dùng tệp dở dang, khoảng 1 lần mỗi vài tuần.

Khi `--episode` trỏ tới tệp không tồn tại, hỏng hoặc sai khuôn (và tương tự với `--checkpoint`), lệnh báo lỗi rõ nguyên nhân và thoát mã khác 0, không mở viewer, không in kết quả giả.

**Why this priority**: AC-5 và master plan XII: thành phần không chạy được phải báo lỗi, không mô tả như đã xong; giá trị thấp hơn các story đường chạy chính.

**Independent Test**: Gọi lệnh với đường dẫn không tồn tại, tệp rỗng, JSON cụt, và episode có giá trị không hữu hạn; kiểm thông báo, mã thoát và không có viewer.

**Acceptance Scenarios**:

1. **Given** đường dẫn episode không tồn tại, **When** replay, **Then** lệnh báo lỗi nêu đường dẫn không tồn tại, thoát mã khác 0, không mở viewer. (AC-5)
2. **Given** episode hỏng (không phải JSON hợp lệ, thiếu trường bắt buộc, độ dài các chuỗi không khớp, giá trị NaN/Inf hoặc activation ngoài `[0,1]`), **When** replay, **Then** lệnh nêu nguyên nhân cụ thể (trường nào, vì sao), thoát mã khác 0, không phát gì. (AC-5)
3. **Given** `--checkpoint` không tồn tại, hỏng hoặc thiếu thành phần, **When** chạy demo, **Then** lệnh nêu nguyên nhân, thoát mã khác 0, không mở viewer và không lưu episode. (AC-5)
4. **Given** lệnh được gọi mà không có `--episode` cũng không có `--checkpoint` (hoặc có cả hai), **When** chạy, **Then** lệnh báo lỗi tham số rõ ràng và thoát mã khác 0. (AC-5)

---

<a id="edge-cases"></a>
### Edge Cases

- Episode có số khớp/số cơ khác mô hình hiện tại dù hash trùng (tệp bị sửa tay): từ chối với thông báo nêu số khớp và số cơ mong đợi/thực có, không phát. (AC-4)
- Episode chỉ có một khung (episode kết thúc ngay khi vừa reset): phát được khung đó, thời lượng mô phỏng 0 s; không chia cho 0 khi tính nhịp hay tóm tắt. (AC-1)
- Episode có phiên bản định dạng không được hỗ trợ: từ chối nêu phiên bản đọc được và phiên bản gặp, không đoán. (AC-5)
- Episode có `muscle_names` không đủ 6 hoặc trùng tên: từ chối nêu số tên thực có. (AC-5)
- Đường dẫn lưu episode đã tồn tại, hoặc thư mục đích không ghi được (đĩa đầy, hết quyền): từ chối/báo lỗi rõ, không ghi đè, thoát mã khác 0, không in như thể đã lưu. (AC-5)
- Lệnh bị ngắt (Ctrl-C) khi đang ghi episode hoặc đang phát: không để lại tệp episode dở dang; thoát mã 130. (INV-004)
- Người dùng đóng cửa sổ viewer giữa chừng khi đang phát hoặc khi demo đang chạy: lệnh dừng gọn, thoát mã 0 (đóng là thao tác bình thường), và không lưu episode dở dang như thể đủ — nếu có yêu cầu lưu mà episode chưa kết thúc thì lưu phần đã chạy với kết quả `end_reason = null` hoặc từ chối, nhưng không ghi như đã tới mục tiêu. (AC-2)
- Policy trong demo cho ra hành động ngoài `[0,1]^6` hoặc chứa NaN/Inf: hành động bị chặn tại biên, episode kết thúc bất thường và được ghi nhận như vậy; viewer không treo và không hiển thị giá trị NaN. (INV-002)
- Môi trường báo mất ổn định số/vật lý trong lúc demo: demo dừng gọn, báo rõ, giữ phần đã chạy xem được nhưng không báo là đã tới mục tiêu; mã thoát phản ánh lỗi mô phỏng nếu lệnh không hoàn tất. (AC-2)
- Checkpoint có hash XML mô hình khác mô hình hiện tại: từ chối chạy demo, nêu hai hash (cùng quy tắc với con 2/con 3). (AC-5)
- Hệ số tốc độ ≤ 0 hoặc không phải số, hoặc chỉ số mục tiêu ngoài phạm vi của tập: từ chối trước khi mở viewer, nêu giá trị sai. (AC-5)
- Khung dựng chậm hơn nhịp thời gian thực (máy yếu, đồ hoạ phần mềm): phiên phát không bỏ khung âm thầm; thời gian thực đo được và tỷ lệ so với thời gian mô phỏng được báo cuối phiên. (AC-1)
- Chế độ không màn hình không bao giờ nạp đồ hoạ: kiểm bằng việc chạy được khi thiếu thư viện hiển thị. (AC-3)
- Giá trị không áp dụng trong episode (ví dụ hành động ở khung đầu, kết thúc chưa xác định, nguồn không phải checkpoint) ghi `null` tường minh, không bỏ trường, không NaN. (INV-003)
- Replay không bao giờ sửa, xoá hay ghi đè episode nguồn, checkpoint, hồ sơ run hay nhật ký train. (INV-005)
- Hiển thị activation làm tròn để đọc nhưng không làm đổi giá trị ghi trong tệp hay trong tóm tắt. (INV-006)

<a id="requirements-mandatory"></a>
## Requirements *(mandatory)*

<a id="functional-requirements"></a>
### Functional Requirements

- **FR-001**: Hệ thống MUST cung cấp lệnh `python scripts/replay.py --episode <path>` mở MuJoCo Viewer và phát lại một episode đã lưu theo đúng thứ tự các khung đã ghi, từ khung đầu tới khung cuối, không lỗi. (AC-1)
- **FR-002**: Hệ thống MUST cung cấp chế độ demo `python scripts/replay.py --checkpoint <path>`: nạp policy từ checkpoint của con 2 (chỉ đọc), chạy một episode trên môi trường của con 1 với một mục tiêu, và hiển thị trực tiếp chuyển động khuỷu tay tới mục tiêu trong MuJoCo Viewer; hai chế độ `--episode` và `--checkpoint` loại trừ nhau, thiếu cả hai hoặc có cả hai là lỗi tham số. (AC-2, AC-5)
- **FR-003**: Trong demo, mọi hành động đưa vào môi trường MUST là kích thích cơ `u_i ∈ [0,1]` cho 6 cơ do policy xuất, dùng hành động xác định; MUST NOT dùng position controller thay cơ và MUST NOT điều khiển trực tiếp lực hay toạ độ tay; replay chỉ đặt lại trạng thái đã ghi để vẽ, không chạy lại điều khiển. (AC-2)
- **FR-004**: Viewer MUST hiển thị mục tiêu của episode tại đúng vị trí đã ghi (replay) hoặc đã chọn (demo), tách biệt rõ với thân khuỷu tay, trong suốt phiên phát. (AC-1, AC-2)
- **FR-005**: Viewer MUST hiển thị 6 giá trị activation của 6 cơ kèm tên cơ, cập nhật theo từng khung, lấy đúng giá trị đã ghi (replay) hoặc đang mô phỏng (demo). (AC-1, AC-2)
- **FR-006**: Phiên phát MUST chạy ở tốc độ thời gian thực mặc định (hệ số 1,0), cho chỉnh hệ số tốc độ và chế độ lặp, và giữ khung cuối cho tới khi người dùng đóng cửa sổ; lệnh MUST in thời lượng mô phỏng và gợi ý hệ số tốc độ khi episode ngắn hơn 1 s; khi khung dựng chậm hơn nhịp, lệnh MUST báo tỷ lệ thời gian thực đo được thay vì im lặng. (AC-1)
- **FR-007**: Hệ thống MUST định nghĩa và đọc/ghi định dạng episode gồm tối thiểu: trạng thái khớp theo thời gian, hành động (kích thích 6 cơ), activation 6 cơ, vị trí mục tiêu (kèm tập và chỉ số nếu có), seed, hash XML của mô hình, tên 6 cơ, kết quả episode, hồ sơ nguồn (checkpoint đã sinh ra nó hoặc `null`) và phiên bản định dạng; định dạng có khuôn máy đọc được. (AC-1, AC-4)
- **FR-008**: Khi chỉ định đường dẫn lưu, hệ thống MUST lưu episode của demo đúng đường dẫn đó bằng cách ghi nguyên tử (không để tệp dở dang), MUST từ chối ghi đè tệp đã tồn tại, và MUST NOT ghi bất kỳ tệp episode nào khi không được chỉ định. (AC-2, AC-5)
- **FR-009**: Khi đọc episode, hệ thống MUST kiểm cấu trúc và nhất quán (đủ trường bắt buộc, độ dài các chuỗi khớp nhau, 6 cơ có tên không trùng, mọi giá trị số hữu hạn, activation trong `[0,1]`, phiên bản định dạng được hỗ trợ) và từ chối với thông báo nêu trường và lý do. (AC-5)
- **FR-010**: Hệ thống MUST cung cấp chế độ `--headless` không mở viewer và không nạp đồ hoạ: với `--episode`, kiểm dữ liệu và in tóm tắt máy đọc được (số bước, thời lượng mô phỏng, trạng thái khớp mô hình, hash hai bên, mục tiêu, seed, kết quả episode, và với từng cơ: activation nhỏ nhất/lớn nhất/trung bình/cuối); với `--checkpoint`, chạy một episode không cần màn hình và lưu theo FR-008 khi có đường dẫn. (AC-3)
- **FR-011**: Khi môi trường không có màn hình và không chọn `--headless`, hệ thống MUST báo lỗi rõ bằng tiếng Việt nêu nguyên nhân và gợi ý `--headless`, thoát mã khác 0 trong ≤ 5 s, không treo. Khi có biến hiển thị nhưng viewer không khởi tạo được, MUST xử lý như trường hợp không có màn hình. (AC-3)
- **FR-012**: Khi hash XML trong episode khác hash XML của mô hình hiện tại, hệ thống MUST cảnh báo lệch mô hình nêu cả hai hash và dừng với mã thoát khác 0 trước khi mở viewer; MUST cho phép tiếp tục chỉ qua một cờ tường minh, khi đó cảnh báo "MÔ HÌNH LỆCH" MUST hiển thị liên tục và có trong tóm tắt; MUST từ chối trong mọi trường hợp nếu cấu trúc không tương thích (số khớp, số cơ). (AC-4)
- **FR-013**: Khi `--episode` hoặc `--checkpoint` không tồn tại, không đọc được, hỏng, thiếu thành phần hoặc sai khuôn, hệ thống MUST in lỗi nêu nguyên nhân, thoát mã khác 0, và MUST NOT mở viewer hay in kết quả giả. Checkpoint của demo MUST được kiểm hash XML mô hình như ở con 2/con 3. (AC-5)
- **FR-014**: Mã thoát của lệnh MUST phản ánh kết quả phát lại/chạy demo chứ không phản ánh lỗi dọn dẹp đồ hoạ lúc thoát tiến trình; viewer đóng bình thường (người dùng đóng cửa sổ hoặc phát xong) MUST cho mã 0. (AC-1)
- **FR-015**: Replay MUST chạy ở tiến trình riêng, chỉ đọc mọi dữ liệu của run, và MUST NOT import lớp huấn luyện (`learning.trainer`, `learning.ppo`); đường `--episode` MUST NOT cần nạp thư viện học máy. (AC-1)
- **FR-016**: Demo MUST cho chọn mục tiêu bằng chỉ số trong một tập (mặc định tập kiểm thử của con 1, chỉ số 0) và seed (mặc định từ cấu hình); giá trị ngoài phạm vi MUST bị từ chối trước khi mở viewer. (AC-2, AC-5)
- **FR-017**: Cấu hình replay (hệ số tốc độ mặc định, chế độ lặp, thời gian giữ khung cuối, seed mặc định, tập mục tiêu mặc định, hằng số hiển thị) MUST nằm ở một tệp cấu hình duy nhất; giá trị sai (hệ số ≤ 0, thiếu khoá) MUST bị từ chối trước khi mở viewer. (AC-5)
- **FR-018**: Mọi lỗi và thông báo hướng tới người dùng MUST bằng tiếng Việt, nêu giá trị và ngữ cảnh (đường dẫn, hash, trường sai); đường dẫn trong tóm tắt và episode MUST là tương đối, không tuyệt đối riêng của máy. (AC-3, AC-5)
- **FR-019**: Hệ thống MUST cung cấp bộ test tự động cho: định dạng episode (ghi/đọc/hợp khuôn/từ chối hỏng), phát lại đúng thứ tự khung và activation hiển thị đúng giá trị, bộ lập nhịp, demo chỉ dùng kích thích cơ và tái lập theo seed, chế độ không màn hình (kể cả khi không có màn hình), lệch mô hình, và đường dẫn/checkpoint không tồn tại. (AC-1, AC-2, AC-3, AC-4, AC-5)

<a id="yeu-cau-phi-chuc-nang-non-functional-requirements"></a>
### Yêu cầu phi chức năng (Non-Functional Requirements)

- **NFR-PERF-001**: Nhịp phát thời gian thực của phiên phát.
  Ngưỡng: ở hệ số tốc độ 1,0, trên đồng hồ giả do test điều khiển, tỷ lệ thời gian phát / thời gian mô phỏng nằm trong [0,95 ; 1,05] trên 100% episode thử có thời lượng từ 0,2 s tới 4 s; khi khung dựng chậm hơn nhịp, tỷ lệ thực đo được MUST được báo (không im lặng, không bỏ khung âm thầm).
  Đo bằng: `python -m pytest` (test bộ lập nhịp với đồng hồ giả); tỷ lệ thực của phiên viewer thật ghi trong tóm tắt cuối phiên. (AC-1)
- **NFR-HEADLESS-001**: Đường không màn hình không treo và không cần đồ hoạ.
  Ngưỡng: khi `DISPLAY` và `WAYLAND_DISPLAY` bỏ đặt, `--headless` thoát mã 0 với tóm tắt đủ trường; không `--headless` thoát mã khác 0 trong ≤ 5 s với thông báo nêu nguyên nhân.
  Đo bằng: `python -m pytest` (test chạy lệnh với biến hiển thị bỏ đặt, đo thời gian thoát). (AC-3)
- **NFR-REPRO-001**: Tính tái lập của demo theo seed.
  Ngưỡng: hai lần demo không màn hình cùng checkpoint, cùng seed, cùng mục tiêu, cùng loại thiết bị cho chuỗi hành động giống hệt (0 khác biệt) và mọi trường số của episode lệch tuyệt đối ≤ 1×10⁻⁶.
  Đo bằng: `python -m pytest` (test chạy demo hai lần và so hai episode). (AC-2)
- **NFR-REL-001**: Độ tin cậy số học của episode và tóm tắt.
  Ngưỡng: 0 giá trị NaN và 0 giá trị Inf trong mọi tệp episode và tóm tắt do hệ thống ghi; episode nạp vào có giá trị không hữu hạn bị từ chối với mã thoát khác 0 trong 100% ca thử.
  Đo bằng: `python -m pytest` (test hợp đồng bằng JSON Schema và quét giá trị không hữu hạn). (AC-1, AC-5)

<a id="bat-bien-invariants"></a>
### Bất biến (Invariants)

- **INV-001**: Replay MUST NOT phát lại sai ngầm: episode có hash XML khác mô hình hiện tại MUST bị dừng (hoặc, chỉ khi người dùng bật cờ tường minh và cấu trúc tương thích, phát kèm cảnh báo liên tục); không có đường nào phát lệch mô hình mà không cảnh báo. (AC-4)
- **INV-002**: Đường điều khiển duy nhất trong demo là kích thích cơ `u_i ∈ [0,1]` cho 6 cơ do policy xuất; lớp hiển thị MUST NOT ghi lực, góc khớp hay toạ độ tay vào mô phỏng; replay chỉ đặt trạng thái đã ghi để vẽ (kế thừa INV-003 của con 1 và INV-002 của con 2). (AC-2)
- **INV-003**: Episode MUST tự đủ để phát lại đúng mô hình: luôn có seed, hash XML, tên 6 cơ và phiên bản định dạng; giá trị không áp dụng ghi `null` tường minh, không bỏ trường, không NaN/Infinity. (AC-1, AC-4)
- **INV-004**: Khi lỗi (không có màn hình, episode/checkpoint lỗi, lệch mô hình, không ghi được) hệ thống MUST thoát mã khác 0, MUST NOT treo, MUST NOT mở viewer nửa vời hay để lại tệp episode dở dang trông như hợp lệ. (AC-3, AC-5)
- **INV-005**: Replay và demo MUST chỉ đọc đối với checkpoint, hồ sơ run, nhật ký train và episode nguồn; mọi đầu ra là tệp mới do người dùng chỉ định, không ghi đè tệp đã tồn tại. (AC-1)
- **INV-006**: Giá trị activation hiển thị MUST bằng giá trị trong episode (replay) hoặc trong mô phỏng (demo); làm tròn chỉ ở hiển thị, không ở dữ liệu ghi hay tóm tắt. (AC-2)

<a id="key-entities-include-if-feature-involves-data"></a>
### Key Entities *(include if feature involves data)*

- **Episode đã ghi (Recorded episode)**: bản ghi một episode — phiên bản định dạng, seed, hash XML và tên 6 cơ của mô hình, mục tiêu (vị trí, tập, chỉ số), hồ sơ nguồn (checkpoint hoặc `null`), kết quả (kết thúc vì sao, khoảng cách cuối) và chuỗi khung.
- **Khung (Frame)**: một mốc thời gian của episode — thời điểm mô phỏng, trạng thái khớp, activation 6 cơ, kích thích 6 cơ đã áp (trống ở khung đầu), vị trí đầu mút tay, khoảng cách tới mục tiêu.
- **Phiên phát (Playback session)**: một lần chạy `replay.py` — chế độ (episode/demo, có màn hình/không), hệ số tốc độ, trạng thái khớp mô hình, thời gian thực đo được và tỷ lệ so với thời gian mô phỏng, nơi lưu episode (nếu có).
- **Tóm tắt không màn hình (Headless summary)**: kết quả JSON của `--headless` — số bước, thời lượng, kết quả khớp mô hình kèm hai hash, mục tiêu, seed, kết quả episode, thống kê activation theo từng cơ, cảnh báo.

<a id="success-criteria-mandatory"></a>
## Success Criteria *(mandatory)*

<a id="measurable-outcomes"></a>
### Measurable Outcomes

- **SC-001**: Lệnh `python scripts/replay.py --episode <path>` trên episode hợp lệ, ở máy có màn hình, mở MuJoCo Viewer, phát đủ 100% số khung đã ghi theo đúng thứ tự và thoát mã 0 khi đóng cửa sổ. (AC-1)
- **SC-002**: Lệnh demo từ checkpoint hợp lệ cho một episode mà 100% hành động đưa vào môi trường là kích thích cơ trong `[0,1]^6`, và hiển thị mục tiêu cùng 6 giá trị activation có tên cơ ở mọi khung. (AC-2)
- **SC-003**: Trên môi trường không có màn hình, 100% lần chạy replay hoặc kết thúc mã 0 với tóm tắt (có `--headless`) hoặc thoát mã khác 0 trong ≤ 5 s với thông báo rõ (không có `--headless`); 0 lần treo. (AC-3)
- **SC-004**: 100% episode có hash XML khác mô hình hiện tại bị dừng với cảnh báo nêu cả hai hash khi không có cờ chấp nhận; 0 trường hợp phát lệch mô hình mà không cảnh báo. (AC-4)
- **SC-005**: Đường dẫn episode hoặc checkpoint không tồn tại cho mã thoát khác 0 và thông báo nêu đường dẫn; 0 viewer mở, 0 tệp episode được ghi. (AC-5)
- **SC-006**: Mỗi tệp episode do hệ thống ghi hợp khuôn định dạng, có seed, hash XML, 6 tên cơ và activation 6 cơ cho mọi khung, và 0 giá trị NaN/Inf. (AC-1, AC-4)

<a id="out-of-scope"></a>
## Out of Scope

- Huấn luyện (con 2).
- Đánh giá và biểu đồ (con 3).
- Môi trường khuỷu tay và tập mục tiêu (con 1): feature này chỉ tiêu thụ, không định nghĩa hay sinh lại.
- Quay video chất lượng cao.
- Giao diện web.
- Đối thủ/arena.
- M2–M9 (mỏi cơ, cân bằng, locomotion, toàn thân, hai võ sĩ, self-play, MJX): chỉ là lộ trình/ràng buộc, không đặc tả hay lập kế hoạch chi tiết.
- Dựng hình ngoài màn hình (xuất khung ảnh hoặc video khi không có màn hình): không làm ở M1 — chế độ không màn hình là kiểm dữ liệu episode (xem Clarifications).
- Giao diện quan sát training và cửa sổ 3D đọc checkpoint mới nhất lúc đang train: thuộc con 2 (Q-0001).

<a id="assumptions"></a>
## Assumptions

- Người dùng là nhà nghiên cứu RL và người xem demo, vận hành qua dòng lệnh; không có người dùng cuối nào khác và không có giao diện web.
- Con 1 (`002-elbow-muscle-env`) và con 2 (`003-ppo-train-repro`) hiện mới có spec + plan, chưa có mã; con 4 chỉ chạy được trọn vẹn khi con 2 xanh và M0 đạt nghiệm thu, nhưng việc đặc tả không bị chặn. Con 4 giả định (CHƯA KIỂM) rằng con 1 cho đọc trạng thái mô phỏng ở mức chỉ-đọc (góc khớp, vận tốc, activation, đầu mút tay, mục tiêu) và chọn được mục tiêu theo chỉ số, còn con 2 cho nạp policy chỉ-đọc và hồ sơ run. Phần nào chưa có thì bước plan ghi rõ và giao việc bổ sung đọc-chỉ về nơi chủ sở hữu.
- Python 3.11; MuJoCo Viewer đi kèm gói `mujoco`; phần cứng đích RTX 5060 8GB, Ryzen 9 HX, 32GB RAM — replay không đòi GPU riêng. Đồ hoạ và chạy policy trong demo là tiến trình riêng, không chung tiến trình với huấn luyện.
- Máy có màn hình và máy không có màn hình đều là môi trường hợp lệ; việc mở viewer thật chỉ kiểm chứng được trên máy có màn hình. Môi trường WSL2/WSLg chưa được kiểm chứng (Clarifications).
- Thời gian/ngân sách [KHÔNG BIẾT]: spec không nêu số khung/giây hay thời gian chạy; số đo thời gian (nếu có) do máy đo và ghi trong tóm tắt, không suy ra từ con số khác (master plan XI.10).
- Spec không khẳng định policy đã học đạt chất lượng nào: demo cho thấy đúng những gì policy làm, kể cả khi nó không tới mục tiêu.
- Đường dẫn gốc của các run là cấu hình được và tương đối; không dùng đường dẫn tuyệt đối riêng của máy trong tài liệu hay bản ghi.
- Chỉ M1; M2–M9 không được đặc tả hay lập kế hoạch ở đây.
