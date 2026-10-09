---
status: approved
parent: docs/00-input/yeu-cau-a7634ac9.md
children:
  - id: 1
    file: request-1.md
    title: Môi trường khuỷu tay điều khiển bằng cơ và tập mục tiêu
    blocked_by: []
    module: M01
    context: elbow-environment
  - id: 2
    file: request-2.md
    title: Huấn luyện PPO, checkpoint, TensorBoard và hồ sơ tái lập
    blocked_by: [1]
    module: M02
    context: training
  - id: 3
    file: request-3.md
    title: Đánh giá so với random policy và biểu đồ loss/reward/activation
    blocked_by: [2]
    module: M03
    context: evaluation
  - id: 4
    file: request-4.md
    title: Replay 3D bằng MuJoCo Viewer và demo điều khiển bằng cơ
    blocked_by: [2]
    module: M04
    context: visualization
---

# Cây tách yêu cầu M1 — Single-Arm Muscle Control

Yêu cầu gốc: `docs/00-input/yeu-cau-a7634ac9.md` (track G, kế thừa sang mọi con). Phạm vi CHỈ M1; M2–M9 ngoài phạm vi.
M1 phụ thuộc M0 (`specs/001-m0-physics-benchmark`) đạt nghiệm thu — ràng buộc ngoài cây này, ghi ở mục 5 của từng con.

| Con | Mục tiêu | AC chính | blocked_by | Lý do ranh giới (sở hữu dữ liệu) |
|---|---|---|---|---|
| 1. Môi trường khuỷu tay | Nạp MyoElbow 6 muscle actuators, môi trường Gymnasium (observation · action `u∈[0,1]^6` · reward · mục tiêu), tập mục tiêu train/test tách bạch, quyết định ghim `gymnasium` vs `myosuite` | Nạp 6 cơ; không position controller; obs/action hợp lệ, không NaN; tập test không giao tập train | — | Sở hữu định nghĩa nhiệm vụ (không gian obs/action, reward, tập mục tiêu); mọi con khác tiêu thụ |
| 2. Huấn luyện PPO | PPO (actor/critic MLP 2×256, chuẩn hoá obs, gradient clipping), checkpoint định kỳ, TensorBoard, CLI `train.py --stage elbow --seed 42`, lưu seed/config/version/hash XML | Train chạy được; lưu/nạp checkpoint khôi phục đúng; hồ sơ thí nghiệm đủ trường; cùng seed ⇒ tái lập | 1 | Sở hữu policy, checkpoint, nhật ký train và hồ sơ thí nghiệm |
| 3. Đánh giá & biểu đồ | `evaluate.py` so policy đã học với random policy trên tập mục tiêu kiểm thử chưa dùng khi train; biểu đồ loss · reward · activation | Policy tốt hơn random có kiểm định/khoảng tin cậy; có 3 biểu đồ; kết quả lưu | 2 | Sở hữu kết quả đánh giá và báo cáo; chỉ đọc checkpoint |
| 4. Replay 3D & demo | Replay episode trong MuJoCo Viewer, demo khuỷu tay do cơ điều khiển, hiển thị activation | Mở được replay 3D từ checkpoint/episode; demo chạy bằng cơ; không viewer nặng khi train | 2 | Sở hữu lớp hiển thị; tách khỏi train theo Performance Budget (mục XI.8) |

## Ghi chú cho người duyệt

- Cắt theo ranh giới sở hữu dữ liệu: môi trường (con 1) → policy/checkpoint (con 2) → kết quả đánh giá (con 3) và lớp hiển thị (con 4). Con 3 và 4 độc lập nhau, cùng chỉ cần checkpoint từ con 2 nên song song được.
- Mỗi con có giá trị riêng khi xong (con 1: nhiệm vụ chạy được với policy ngẫu nhiên; con 2: có policy lưu được; con 3: bằng chứng học được; con 4: quan sát được bằng mắt).
- Module `M01..M04` là đề xuất theo nghiệp vụ (khách không nêu module); sửa được bằng `ai-sdlc split --set-module <id>=<Mxx>`.
- Quyết định mở: xung đột `myosuite` (cần `gymnasium<1.3`) — giao con 1 chốt ở plan; con 2–4 kế thừa kết quả.
