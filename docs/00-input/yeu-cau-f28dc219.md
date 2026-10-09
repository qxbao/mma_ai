---
id: REQUEST-00-input-yeu-cau-f28dc219
title: 'Yêu cầu: Huấn luyện PPO, checkpoint và hồ sơ tái lập'
doc_type: request
owner_agent: spec
status: draft
updated: '2026-10-09'
track: "G"
---
Yêu cầu con 2/4 của M1 (REQ-0102). ---

# Yêu cầu: Huấn luyện PPO, checkpoint và hồ sơ tái lập

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
- [BỔ SUNG TỪ NGƯỜI DÙNG (C-0009) — giao diện quan sát huấn luyện](#bo-sung-tu-nguoi-dung-c-0009-giao-dien-quan-sat-huan-luyen)

<a id="1-boi-canh"></a>
## 1. Bối cảnh

Dự án MMA-AI-LAB (mô phỏng cơ–xương 3D, học tăng cường): Milestone M1 — Single-Arm Muscle Control, feature kế tiếp sau `001-m0-physics-benchmark` (M0 đã có spec+plan; M1 phụ thuộc M0 đạt nghiệm thu). Yêu cầu gốc: `docs/00-input/yeu-cau-a7634ac9.md`; nguồn đầy đủ: `docs/00-input/` hoặc `/home/baodq/Downloads/writing-block.md` (mục X "M1", IX 9.1 PPO, XII, XIII). Đây là con 2/4 của M1, cần môi trường khuỷu tay ở con 1. PPO là thuật toán baseline (master plan 9.1); phần cứng: RTX 5060 8GB, Ryzen 9 HX, 32GB RAM.

<a id="2-nguoi-dung-va-tinh-huong"></a>
## 2. Người dùng và tình huống

| Ai | Làm gì | Bao lâu một lần | Nỗi đau hiện tại |
|---|---|---|---|
| Nhà nghiên cứu RL | Chạy `python scripts/train.py --stage elbow --seed 42`, theo dõi TensorBoard, tiếp tục từ checkpoint | Mỗi thí nghiệm | Chưa có pipeline train; kết quả khó tái lập nếu không lưu seed/config/phiên bản |

<a id="3-ket-qua-mong-muon-do-duoc"></a>
## 3. Kết quả mong muốn — đo được

- KQ-1: Lệnh train chạy hết một lượt train ngắn (smoke) không lỗi, 0 NaN/Inf trong loss và tham số.
- KQ-2: Checkpoint lưu định kỳ; nạp lại cho ra policy cho cùng hành động (trong dung sai số) trên cùng observation.
- KQ-3: Mỗi lần chạy lưu đủ: seed, config, phiên bản thư viện, hash XML, checkpoint, reward metrics.
- KQ-4: Cùng seed + cùng cấu hình ⇒ đường reward đầu kỳ giống nhau trong dung sai đã khai [KHÔNG BIẾT: ngưỡng].

<a id="4-pham-vi"></a>
## 4. Phạm vi

<a id="trong"></a>
### Trong
- PPO continuous action: actor MLP 2×256, critic MLP 2×256, chuẩn hoá observation, gradient clipping (`ppo.py`).
- Checkpoint định kỳ + lưu/nạp (gồm trạng thái bộ chuẩn hoá observation, optimizer, seed).
- TensorBoard logging (loss, reward, activation) — dữ liệu phục vụ biểu đồ ở con 3.
- CLI `python scripts/train.py --stage elbow --seed 42`; các stage khác ghi rõ "chưa triển khai".
- Hồ sơ thí nghiệm (run manifest); test seed xác định, test lưu/nạp checkpoint.
- Báo cáo env steps/second và wall-clock thời gian train (master plan XI).

<a id="ngoai"></a>
### Ngoài
- Định nghĩa môi trường/reward (con 1); evaluate so random và vẽ biểu đồ (con 3); replay/demo (con 4).
- Tối ưu nhiều môi trường song song (chỉ benchmark 1/2/4/8 nếu cần cho quyết định); self-play, M2–M9.

<a id="5-rang-buoc"></a>
## 5. Ràng buộc

- Kỹ thuật: PyTorch (CUDA khi có), TensorBoard, Python 3.11; mặc định headless, bắt đầu một môi trường; mạng nhỏ.
- Phi chức năng: logs/checkpoint trên SSD; không chạy đồ hoạ nặng cùng lúc; ghi CPU/GPU/RAM/VRAM.
- Dữ liệu: mỗi run một thư mục chứa seed · config · version thư viện · hash XML · checkpoint · metrics; không ghi đè run cũ.
- Phạm vi: CHỈ M1. M2–M9 (mỏi cơ, cân bằng, locomotion, toàn thân, hai võ sĩ, self-play, MJX) chỉ là lộ trình/ràng buộc, KHÔNG đặc tả hay lập kế hoạch chi tiết.
- Quy tắc: không dùng position controller thay cơ; policy chỉ xuất kích thích cơ `u_i ∈ [0,1]`, không điều khiển trực tiếp lực hay toạ độ tay (master plan mục 5.2).
- Thời gian/ngân sách: [KHÔNG BIẾT] — không tự giả định thời gian huấn luyện trước khi benchmark (master plan XI.10).

<a id="6-tieu-chi-chap-nhan"></a>
## 6. Tiêu chí chấp nhận

- AC-1: Cho môi trường xanh · Khi chạy `python scripts/train.py --stage elbow --seed 42` · Thì huấn luyện chạy được, ghi log TensorBoard và checkpoint định kỳ.
- AC-2: Cho checkpoint đã lưu · Khi nạp lại · Thì policy cho cùng hành động xác định trên cùng observation mẫu và có thể train tiếp.
- AC-3: Cho một run xong · Khi mở thư mục run · Thì có seed, config, phiên bản thư viện, hash XML, checkpoint, reward metrics.
- AC-4: Cho hai run cùng seed/cấu hình · Khi so sánh · Thì kết quả nằm trong dung sai tái lập đã khai.
- AC-5: Cho `--stage balance` (hoặc stage chưa hỗ trợ) · Khi gọi CLI · Thì báo rõ "chưa triển khai", mã thoát khác 0.
- AC-6: Cho cấu hình MLP · Khi kiểm tra mạng · Thì actor và critic đều 2 lớp × 256, có chuẩn hoá observation và gradient clipping.

<a id="7-tai-lieu-kem-theo"></a>
## 7. Tài liệu kèm theo

| Tệp | Nội dung | Đã chuyển .md? |
|---|---|---|
| `docs/00-input/yeu-cau-a7634ac9.md` | Yêu cầu gốc M1 | có (.md) |
| `/home/baodq/Downloads/writing-block.md` | Master plan: IX 9.1, XII, XIII | có (.md) |

<a id="8-cau-hoi-con-mo"></a>
## 8. Câu hỏi còn mở

- Siêu tham số PPO (learning rate, clip, số bước/lượt, tổng bước) và tần số checkpoint? [KHÔNG BIẾT] — cần benchmark.
- Tự cài PPO hay dùng thư viện (vd Stable-Baselines3)? [KHÔNG BIẾT] — plan quyết định, phải thoả actor/critic 2×256.
- Dung sai tái lập GPU vs CPU? [KHÔNG BIẾT]

<a id="bo-sung-tu-nguoi-dung-c-0009-giao-dien-quan-sat-huan-luyen"></a>
## BỔ SUNG TỪ NGƯỜI DÙNG (C-0009) — giao diện quan sát huấn luyện
Người dùng yêu cầu: MỌI bước huấn luyện phải có giao diện hiển thị để người QUAN SÁT được khi đang train (không chỉ đọc log sau). Đưa vào phạm vi con 2 (và là ràng buộc cho mọi stage train sau này):
- KQ/AC mới: trong lúc `train.py --stage elbow` chạy, người mở được một giao diện (cổng/URL hoặc cửa sổ) thấy tiến trình theo thời gian thực: reward, loss, activation 6 cơ, env steps/s, số bước đã chạy / tổng, trạng thái checkpoint; cập nhật định kỳ; xem được mà không dừng train.
- Có thể gồm hiển thị 3D khuỷu tay đang được policy điều khiển (cập nhật từ checkpoint/trạng thái mới nhất). TUÂN thủ master plan XI.8: train vẫn mặc định headless, giao diện 3D chạy ở TIẾN TRÌNH RIÊNG, bật/tắt được, không kéo chậm vòng train; nêu rõ chi phí (CPU/GPU/VRAM) và đo trong benchmark.
- Hình thức (TensorBoard + dashboard nhẹ trên web, MuJoCo Viewer đọc checkpoint mới nhất, hay cả hai) là CÂU HỎI cho plan quyết định; plan phải nêu phương án chọn, lý do và chi phí. Giao diện chỉ ĐỌC dữ liệu train, không điều khiển/không sửa policy.
- Phạm vi vẫn CHỈ M1; giao diện này không thay replay 3D/demo của con 4 (con 4 vẫn là replay episode đã lưu).