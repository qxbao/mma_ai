---
id: "REQ-0103"
title: "Là nhà nghiên cứu RL, tôi cần đánh giá policy đã học so với random policy trên mục tiêu chưa dùng khi train và xem biểu đồ loss/reward/activation"
doc_type: request
owner_agent: spec
track: "G"
stop_at: ""
status: draft
updated: "2026-10-09"
---

# Yêu cầu: Đánh giá so với random policy và biểu đồ

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

Dự án MMA-AI-LAB (mô phỏng cơ–xương 3D, học tăng cường): Milestone M1 — Single-Arm Muscle Control, feature kế tiếp sau `001-m0-physics-benchmark` (M0 đã có spec+plan; M1 phụ thuộc M0 đạt nghiệm thu). Yêu cầu gốc: `docs/00-input/yeu-cau-a7634ac9.md`; nguồn đầy đủ: `docs/00-input/` hoặc `/home/baodq/Downloads/writing-block.md` (mục X "M1", IX 9.4, XII). Đây là con 3/4 của M1, cần checkpoint và log từ con 2 và tập mục tiêu test từ con 1. Master plan 9.4: đánh giá trên random policy và các seed chưa dùng khi train.

<a id="2-nguoi-dung-va-tinh-huong"></a>
## 2. Người dùng và tình huống

| Ai | Làm gì | Bao lâu một lần | Nỗi đau hiện tại |
|---|---|---|---|
| Nhà nghiên cứu RL | Chạy `python scripts/evaluate.py --checkpoint <path>` rồi xem biểu đồ | Sau mỗi run | Chưa có bằng chứng định lượng rằng policy học được hơn ngẫu nhiên |

<a id="3-ket-qua-mong-muon-do-duoc"></a>
## 3. Kết quả mong muốn — đo được

- KQ-1: Báo cáo so sánh policy đã học vs random policy trên cùng tập mục tiêu kiểm thử: tỷ lệ tới mục tiêu và khoảng cách cuối episode, kèm khoảng tin cậy.
- KQ-2: Policy đã học tốt hơn random có ý nghĩa thống kê theo tiêu chí khai trước [KHÔNG BIẾT: mức ý nghĩa/số episode].
- KQ-3: Có 3 biểu đồ: loss, reward, activation cơ (6 cơ), lưu thành tệp ảnh.
- KQ-4: Kết quả đánh giá lưu cùng hồ sơ run (seed, checkpoint được dùng).

<a id="4-pham-vi"></a>
## 4. Phạm vi

<a id="trong"></a>
### Trong
- `scripts/evaluate.py --checkpoint <path>`; baseline random policy; tập mục tiêu và seed chưa dùng khi train.
- Chỉ số: tỷ lệ thành công, khoảng cách cuối, reward trung bình, mức kích hoạt/nỗ lực, tỷ lệ episode kết thúc bất thường, NaN/Inf count; khoảng tin cậy.
- Biểu đồ loss, reward, activation từ log TensorBoard/CSV (`metrics.py`).
- Lưu kết quả đánh giá vào hồ sơ run.

<a id="ngoai"></a>
### Ngoài
- Huấn luyện, checkpoint (con 2); môi trường (con 1); viewer 3D (con 4).
- Frozen old policies, opponent pool, win rate, biến thể vật lý, robustness (thuộc M5+).

<a id="5-rang-buoc"></a>
## 5. Ràng buộc

- Kỹ thuật: Python 3.11, NumPy/Pandas phân tích; biểu đồ headless (không cần màn hình).
- Phi chức năng: phân biệt rõ kết quả đo thực tế với giả định (master plan XII); thành phần chưa chạy được phải báo lỗi và giới hạn, không mô tả là đã xong.
- Dữ liệu: tập đánh giá không giao tập train; random policy dùng seed cố định để tái lập.
- Phạm vi: CHỈ M1. M2–M9 (mỏi cơ, cân bằng, locomotion, toàn thân, hai võ sĩ, self-play, MJX) chỉ là lộ trình/ràng buộc, KHÔNG đặc tả hay lập kế hoạch chi tiết.
- Quy tắc: không dùng position controller thay cơ; policy chỉ xuất kích thích cơ `u_i ∈ [0,1]`, không điều khiển trực tiếp lực hay toạ độ tay (master plan mục 5.2).
- Thời gian/ngân sách: [KHÔNG BIẾT] — không tự giả định thời gian huấn luyện trước khi benchmark (master plan XI.10).

<a id="6-tieu-chi-chap-nhan"></a>
## 6. Tiêu chí chấp nhận

- AC-1: Cho checkpoint đã train · Khi chạy evaluate trên tập mục tiêu kiểm thử · Thì in và lưu chỉ số của policy đã học và của random policy trên cùng tập.
- AC-2: Cho kết quả hai policy · Khi so sánh · Thì policy đã học tốt hơn random policy theo tiêu chí khai trước, kèm khoảng tin cậy.
- AC-3: Cho log của một run · Khi tạo biểu đồ · Thì có ảnh loss, reward, activation.
- AC-4: Cho tập đánh giá · Khi kiểm tra · Thì không mục tiêu/seed nào trùng tập train.
- AC-5: Cho checkpoint không tồn tại hoặc hỏng · Khi chạy evaluate · Thì báo lỗi rõ, mã thoát khác 0, không in kết quả giả.

<a id="7-tai-lieu-kem-theo"></a>
## 7. Tài liệu kèm theo

| Tệp | Nội dung | Đã chuyển .md? |
|---|---|---|
| `docs/00-input/yeu-cau-a7634ac9.md` | Yêu cầu gốc M1 | có (.md) |
| `/home/baodq/Downloads/writing-block.md` | Master plan: IX 9.4, X M1, XII | có (.md) |

<a id="8-cau-hoi-con-mo"></a>
## 8. Câu hỏi còn mở

- Tiêu chí "tốt hơn random": chỉ số chính, ngưỡng, số episode, kiểm định? [KHÔNG BIẾT]
- Tần suất ghi activation để vẽ (mỗi bước hay trung bình episode)? [KHÔNG BIẾT]
