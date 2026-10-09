---
id: "REQ-0101"
title: "Là nhà nghiên cứu RL, tôi cần môi trường khuỷu tay điều khiển bằng 6 cơ và tập mục tiêu train/test tách bạch để huấn luyện và đánh giá chính đáng"
doc_type: request
owner_agent: spec
track: "G"
stop_at: ""
status: draft
updated: "2026-10-09"
---

# Yêu cầu: Môi trường khuỷu tay điều khiển bằng cơ

- [1. Bối cảnh](#1-boi-canh)
- [2. Người dùng và tình huống](#2-nguoi-dung-va-tinh-huong)
- [3. Kết quả mong muốn — đo được](#3-ket-qua-mong-muon-do-duoc)
- [4. Phạm vi](#4-pham-vi)
  - [Trong](#trong)
  - [Ngoài](#ngoai)
- [5. Ràng buộc](#5-rang-buoc)
- [6. Tiêu chí chấp nhận](#6-tieu-chi-chap-nhan)
- [7. Tài liệu kèm theo](#7-tai-lieu-kem-theo)
- [8. Câu hỏi còn mở](#8-cau-hoi-con-mo)

<a id="1-boi-canh"></a>
## 1. Bối cảnh

Dự án MMA-AI-LAB (mô phỏng cơ–xương 3D, học tăng cường): Milestone M1 — Single-Arm Muscle Control, feature kế tiếp sau `001-m0-physics-benchmark` (M0 đã có spec+plan; M1 phụ thuộc M0 đạt nghiệm thu). Yêu cầu gốc: `docs/00-input/yeu-cau-a7634ac9.md`; nguồn đầy đủ: `docs/00-input/` hoặc `/home/baodq/Downloads/writing-block.md` (mục X "M1", IX 9.1 PPO, XII, XIII). Repo greenfield, Python 3.11, MuJoCo, PyTorch, Gymnasium. Đây là con 1/4 của M1 (nền tảng, không phụ thuộc con nào). Mô hình mục tiêu: `myoelbow_1dof6muscles.xml` (gói `myo-sim==0.2.3`, đã xác nhận ở research của 001). Research của 001 ghi: `myosuite` ghim `gymnasium<1.3` xung đột với `gymnasium 1.4.0` — cần quyết định ở plan: ghim `gymnasium` theo MyoSuite hay bỏ MyoSuite và dùng `myo-sim` + `gymnasium` mới.

<a id="2-nguoi-dung-va-tinh-huong"></a>
## 2. Người dùng và tình huống

| Ai | Làm gì | Bao lâu một lần | Nỗi đau hiện tại |
|---|---|---|---|
| Nhà nghiên cứu RL | Tạo môi trường khuỷu tay, reset với mục tiêu, bước mô phỏng bằng vector kích thích 6 cơ | Mỗi lần train/đánh giá | Chưa có môi trường chuẩn Gymnasium để PPO và đánh giá dùng chung |
| Người đánh giá | Lấy tập mục tiêu kiểm thử cố định, chưa dùng khi train | Mỗi lần đánh giá | Dễ rò rỉ mục tiêu train sang test nếu không tách từ gốc |

<a id="3-ket-qua-mong-muon-do-duoc"></a>
## 3. Kết quả mong muốn — đo được

- KQ-1: Môi trường nạp mô hình khuỷu tay với đúng 6 muscle actuators và chạy headless, 0 NaN/Inf trong rollout kiểm thử.
- KQ-2: Observation/action có chiều và miền giá trị xác định, được kiểm tra tự động (chiều, NaN, ngoài khoảng).
- KQ-3: Tập mục tiêu train và test sinh theo seed, giao nhau = rỗng, kiểm tra được bằng test.
- KQ-4: Có quyết định phiên bản `gymnasium`/`myosuite` ghi rõ lý do và chứng minh cài được trong môi trường ảo sạch.

<a id="4-pham-vi"></a>
## 4. Phạm vi

<a id="trong"></a>
### Trong
- Nạp MyoElbow 6 muscle actuators qua MuJoCo; môi trường một agent theo Gymnasium (`single_agent.py`).
- Observation (góc/vận tốc khớp, trạng thái kích hoạt cơ, vị trí đầu mút tay và mục tiêu), chuẩn hoá, validation.
- Action `u ∈ [0,1]^6`; reward tiến tới mục tiêu (có thành phần phạt kích hoạt/nỗ lực, tham số cấu hình được).
- Bộ sinh mục tiêu; tách tập train / tập test theo seed; điều kiện kết thúc episode.
- Quyết định phiên bản `gymnasium` vs `myosuite`.
- Hash XML mô hình để ghi vào hồ sơ thí nghiệm.

<a id="ngoai"></a>
### Ngoài
- Thuật toán PPO, checkpoint, TensorBoard (con 2); evaluate và biểu đồ (con 3); replay/demo (con 4).
- Mỏi cơ, damage proxy, M2–M9.

<a id="5-rang-buoc"></a>
## 5. Ràng buộc

- Kỹ thuật: Python 3.11, MuJoCo, `myo-sim==0.2.3`, Gymnasium; khoá dependency vào lockfile sau smoke test; không tự giả định phiên bản tương thích.
- Phi chức năng: chạy headless; không dùng pixel observation ở baseline; timestep vật lý thử 0.0025 s, policy 25 Hz (16 bước vật lý/hành động) — tham số khởi tạo, cần benchmark.
- Dữ liệu: tập mục tiêu train/test không giao nhau (INV); seed xác định cho cùng kết quả sinh mục tiêu.
- Phạm vi: CHỈ M1. M2–M9 (mỏi cơ, cân bằng, locomotion, toàn thân, hai võ sĩ, self-play, MJX) chỉ là lộ trình/ràng buộc, KHÔNG đặc tả hay lập kế hoạch chi tiết.
- Quy tắc: không dùng position controller thay cơ; policy chỉ xuất kích thích cơ `u_i ∈ [0,1]`, không điều khiển trực tiếp lực hay toạ độ tay (master plan mục 5.2).
- Thời gian/ngân sách: [KHÔNG BIẾT] — không tự giả định thời gian huấn luyện trước khi benchmark (master plan XI.10).

<a id="6-tieu-chi-chap-nhan"></a>
## 6. Tiêu chí chấp nhận

- AC-1: Cho mô hình MyoElbow · Khi nạp môi trường · Thì có đúng 6 muscle actuators và action space là `[0,1]^6`.
- AC-2: Cho môi trường đã reset với seed · Khi chạy episode với hành động ngẫu nhiên · Thì observation đúng chiều, không NaN/Inf, không ngoài khoảng.
- AC-3: Cho cùng seed · Khi sinh tập mục tiêu hai lần · Thì kết quả giống nhau; và tập train ∩ tập test = ∅.
- AC-4: Cho cấu hình đúng · Khi quan sát cấu trúc điều khiển · Thì không có position controller thay cơ; lực cơ do mô hình tính.
- AC-5: Cho môi trường ảo sạch · Khi cài theo quyết định phiên bản · Thì cài và chạy được môi trường; lý do chọn được ghi lại.

<a id="7-tai-lieu-kem-theo"></a>
## 7. Tài liệu kèm theo

| Tệp | Nội dung | Đã chuyển .md? |
|---|---|---|
| `docs/00-input/yeu-cau-a7634ac9.md` | Yêu cầu gốc M1 | có (.md) |
| `specs/001-m0-physics-benchmark/research.md` | Q2 myo-sim vs myosuite, xung đột gymnasium | có (.md) |
| `/home/baodq/Downloads/writing-block.md` | Master plan MMA-AI-LAB | có (.md) |

<a id="8-cau-hoi-con-mo"></a>
## 8. Câu hỏi còn mở

- Ghim `gymnasium<1.3` theo MyoSuite hay bỏ MyoSuite? [KHÔNG BIẾT] — plan M1 quyết định.
- Công thức reward cụ thể và ngưỡng "tới mục tiêu" (dung sai khoảng cách)? [KHÔNG BIẾT]
- Kích thước tập mục tiêu train/test? [KHÔNG BIẾT]
