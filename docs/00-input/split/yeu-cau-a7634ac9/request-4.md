---
id: "REQ-0104"
title: "Là nhà nghiên cứu RL, tôi cần xem replay 3D và demo khuỷu tay do cơ điều khiển để kiểm bằng mắt"
doc_type: request
owner_agent: spec
track: "G"
stop_at: ""
status: draft
updated: "2026-10-09"
---

# Yêu cầu: Replay 3D và demo điều khiển bằng cơ

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

Dự án MMA-AI-LAB (mô phỏng cơ–xương 3D, học tăng cường): Milestone M1 — Single-Arm Muscle Control, feature kế tiếp sau `001-m0-physics-benchmark` (M0 đã có spec+plan; M1 phụ thuộc M0 đạt nghiệm thu). Yêu cầu gốc: `docs/00-input/yeu-cau-a7634ac9.md`; nguồn đầy đủ: `docs/00-input/` hoặc `/home/baodq/Downloads/writing-block.md` (mục X "M1", XI, XIII). Đây là con 4/4 của M1, cần checkpoint/policy từ con 2. Chạy tách khỏi huấn luyện vì đồ hoạ nặng không chạy cùng lúc với train (master plan XI.8). Kiến trúc: `visualization/replay.py`, `scripts/replay.py`.

<a id="2-nguoi-dung-va-tinh-huong"></a>
## 2. Người dùng và tình huống

| Ai | Làm gì | Bao lâu một lần | Nỗi đau hiện tại |
|---|---|---|---|
| Nhà nghiên cứu RL | Mở replay 3D một episode đã ghi hoặc chạy policy trực tiếp để xem tay với tới mục tiêu | Sau mỗi run | Chỉ có số liệu, chưa thấy được hành vi cơ–xương |
| Người xem demo | Xem khuỷu tay chuyển động do kích hoạt cơ, thấy mức activation | Khi trình bày | Khó chứng minh "điều khiển bằng cơ" một cách trực quan |

<a id="3-ket-qua-mong-muon-do-duoc"></a>
## 3. Kết quả mong muốn — đo được

- KQ-1: Lệnh replay mở MuJoCo Viewer và phát lại một episode đã lưu, không lỗi.
- KQ-2: Demo chạy policy từ checkpoint, hiển thị chuyển động khuỷu tay và mục tiêu.
- KQ-3: Có chế độ không màn hình (kiểm tra dữ liệu episode hoặc xuất khung) để kiểm thử tự động [KHÔNG BIẾT: định dạng].
- KQ-4: Replay cho thấy/ghi lại 6 giá trị activation theo thời gian, chứng minh điều khiển bằng cơ.

<a id="4-pham-vi"></a>
## 4. Phạm vi

<a id="trong"></a>
### Trong
- Định dạng lưu episode (trạng thái, hành động, activation, mục tiêu, seed) và `scripts/replay.py --episode <path>`.
- Phát lại 3D bằng MuJoCo Viewer; chạy demo từ checkpoint.
- Hiển thị mục tiêu và activation của 6 cơ; ghi lại để con 3 hoặc người dùng dùng.
- Xử lý máy không có màn hình/WSL không có display: báo lỗi rõ hoặc chế độ thay thế.

<a id="ngoai"></a>
### Ngoài
- Huấn luyện (con 2), đánh giá/biểu đồ (con 3), môi trường (con 1).
- Quay video chất lượng cao, giao diện web, đối thủ/arena, M2–M9.

<a id="5-rang-buoc"></a>
## 5. Ràng buộc

- Kỹ thuật: MuJoCo Viewer; Python 3.11; chạy trên WSL2 Ubuntu / Linux; không bắt buộc GPU.
- Phi chức năng: không chạy cùng lúc với huấn luyện nặng; replay mượt ở tốc độ thời gian thực [KHÔNG BIẾT: ngưỡng FPS].
- Dữ liệu: episode file đủ seed và hash XML để phát lại đúng mô hình.
- Phạm vi: CHỈ M1. M2–M9 (mỏi cơ, cân bằng, locomotion, toàn thân, hai võ sĩ, self-play, MJX) chỉ là lộ trình/ràng buộc, KHÔNG đặc tả hay lập kế hoạch chi tiết.
- Quy tắc: không dùng position controller thay cơ; policy chỉ xuất kích thích cơ `u_i ∈ [0,1]`, không điều khiển trực tiếp lực hay toạ độ tay (master plan mục 5.2).
- Thời gian/ngân sách: [KHÔNG BIẾT] — không tự giả định thời gian huấn luyện trước khi benchmark (master plan XI.10).

<a id="6-tieu-chi-chap-nhan"></a>
## 6. Tiêu chí chấp nhận

- AC-1: Cho episode đã lưu · Khi chạy `python scripts/replay.py --episode <path>` · Thì MuJoCo Viewer mở và phát lại chuyển động khuỷu tay.
- AC-2: Cho checkpoint · Khi chạy demo · Thì khuỷu tay chuyển động tới mục tiêu và hiển thị activation 6 cơ.
- AC-3: Cho môi trường không có display · Khi chạy replay · Thì báo lỗi rõ hoặc chạy chế độ không màn hình, không treo.
- AC-4: Cho episode có hash XML khác mô hình hiện tại · Khi replay · Thì cảnh báo lệch mô hình, không phát lại sai ngầm.
- AC-5: Cho đường dẫn episode không tồn tại · Khi replay · Thì báo lỗi rõ, mã thoát khác 0.

<a id="7-tai-lieu-kem-theo"></a>
## 7. Tài liệu kèm theo

| Tệp | Nội dung | Đã chuyển .md? |
|---|---|---|
| `docs/00-input/yeu-cau-a7634ac9.md` | Yêu cầu gốc M1 | có (.md) |
| `/home/baodq/Downloads/writing-block.md` | Master plan: X M1, XI, XIII | có (.md) |

<a id="8-cau-hoi-con-mo"></a>
## 8. Câu hỏi còn mở

- Replay phát từ episode đã ghi, chạy live policy, hay cả hai? [KHÔNG BIẾT] — mặc định đề xuất cả hai.
- WSL2 có WSLg/display để mở viewer? [KHÔNG BIẾT]
