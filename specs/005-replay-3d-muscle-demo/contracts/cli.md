---
id: "CLI-005"
title: "M1 (4/4) — Hợp đồng dòng lệnh"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "005-replay-3d-muscle-demo"
version: "1.0.0"
---

# Hợp đồng — dòng lệnh replay / demo

Không có dịch vụ mạng, không điểm HTTP, không phân quyền (lệnh cục bộ, không vai/khoá/token) ⇒ không `rbac.md`. "Hợp đồng dây" gồm (1) MỘT lệnh CLI, (2) các tệp có khuôn JSON Schema (draft 2020-12, ví dụ ở `examples/`, test `test_contract_examples_replay`): [episode.schema.json](episode.schema.json) (đầu vào của `--episode` và đầu ra của `--save-episode`), [replay-summary.schema.json](replay-summary.schema.json) (đầu ra của `--headless`), [replay-config.schema.json](replay-config.schema.json). Tên trường KHÔNG chép ở đây — xem schema. Mọi tệp trong `examples/` là **ví dụ minh hoạ khuôn**, không phải kết quả đo (hash trong đó là giá trị giả).

## Lệnh (CMD)

| Mã | Lệnh | Vào | Ra | Aggregate · sự kiện · quyền | FR / AC |
|---|---|---|---|---|---|
| `CMD-VIS-0001` | `python scripts/replay.py (--episode PATH \| --checkpoint PATH) [--headless] [--save-episode PATH] [--speed X] [--loop] [--allow-model-mismatch] [--split train\|test] [--target-index N] [--seed N] [--config PATH]` | `--episode`: tệp theo [episode.schema.json](episode.schema.json); `--checkpoint`: tệp `.pt` hoặc `checkpoints/latest.json` của một run (con 2, chỉ đọc); cấu hình `configs/replay.yaml` ([replay-config.schema.json](replay-config.schema.json)); cờ dòng lệnh ghi đè khoá cùng tên (`playback.speed`, `playback.loop`, `demo.*`) | Có màn hình: cửa sổ MuJoCo Viewer (mục tiêu + bảng 6 activation) và một dòng tóm tắt tiếng Việt cuối phiên (thời lượng mô phỏng, thời gian thực, tỷ lệ, khung trễ). `--headless`: tóm tắt JSON theo [replay-summary.schema.json](replay-summary.schema.json) trên **stdout** (thông báo cho người đọc ở **stderr**). `--save-episode`: một tệp episode mới | aggregate: Phiên phát · không phát sự kiện (không có `EVT-*`) · không `PERM-*` | FR-001…FR-018 / AC-1…AC-5 |

### Quy tắc của `replay.py`

- **Chế độ**: đúng một trong `--episode` (phát lại episode đã lưu) hoặc `--checkpoint` (demo). Thiếu cả hai hoặc có cả hai ⇒ mã 2 (AC-5). `--split`, `--target-index`, `--seed` chỉ có nghĩa ở `--checkpoint`; dùng với `--episode` ⇒ mã 2.
- **Thứ tự bắt buộc** (mỗi bước dừng lệnh nếu lỗi và *trước* mọi ghi đĩa hay mở cửa sổ): (1) nạp và kiểm cấu hình + tham số; (2) nạp nguồn — `--episode`: đọc và kiểm theo FR-009; `--checkpoint`: nạp policy chỉ-đọc và kiểm hash XML; (3) kiểm lệch mô hình (INV-001); (4) không `--headless`: kiểm màn hình (`display_available()`); (5) demo: chạy trọn episode bằng policy trên môi trường của con 1 (mất ≪ 1 s); (6) nếu có `--save-episode`: ghi nguyên tử *trước* khi mở cửa sổ (đóng cửa sổ hay Ctrl-C về sau không làm mất tệp); (7) `--headless`: in tóm tắt; ngược lại: mở viewer và phát. Demo luôn **chạy trọn episode rồi mới phát** bằng đúng đường phát của `--episode` ⇒ cái nhìn thấy khi demo trùng với tệp episode lưu ra.
- `--headless`: không nhập `glfw`, không gọi `mujoco.viewer`; `--episode` + `--headless` không cần `torch`; `--checkpoint` + `--headless` cần extra `rl` của 003 và có thể kèm `--save-episode`. `--speed`, `--loop` bị bỏ qua (ghi cảnh báo).
- `--save-episode PATH`: chỉ ghi khi được chỉ định, **không bao giờ ghi ngầm**; `PATH` đã tồn tại ⇒ mã 8 (không ghi đè); thư mục cha chưa có thì tạo; chỉ dùng được với `--checkpoint` (episode vừa sinh). Tên khuyến nghị `*.episode.json`.
- `--speed X`: hệ số tốc độ > 0 (mặc định 1,0 = thời gian thực); `--loop`: phát lặp tới khi đóng cửa sổ. Không có cờ → giữ khung cuối tới khi đóng cửa sổ (`playback.hold_after_end_s: null`).
- `--allow-model-mismatch`: chỉ tiếp tục khi hash XML lệch **và** cấu trúc tương thích (số khớp, số cơ, tên cơ); cảnh báo "MÔ HÌNH LỆCH" hiện liên tục trong cửa sổ và nằm trong `warnings` của tóm tắt. Cấu trúc không tương thích ⇒ vẫn mã 6. Đây là cờ duy nhất làm yếu một kiểm tra an toàn.
- Khi episode ngắn hơn 1 s mô phỏng, lệnh in thời lượng mô phỏng và gợi ý `--speed 0.1` / `--loop` (stderr).
- Mọi lỗi in tiếng Việt, nêu giá trị/ngữ cảnh (đường dẫn, hai hash, trường sai, thành phần thiếu).
- Chỉ đọc: lệnh không sửa bất kỳ tệp nào của run hay episode nguồn; đầu ra duy nhất là tệp do `--save-episode` chỉ định (INV-005).
- Viewer đã mở ⇒ `scripts/replay.py` xả stdout/stderr, đóng handle rồi `os._exit(mã)` để mã thoát không phụ thuộc bước dọn dẹp đồ hoạ (research Q3); các đường không mở viewer thoát bình thường.

### Mã thoát

| Mã | Ý nghĩa |
|---|---|
| 0 | xong: phát hết/người dùng đóng cửa sổ, hoặc `--headless` hoàn tất, và episode đã lưu nếu được yêu cầu |
| 1 | lỗi không lường trước, hoặc mô phỏng demo mất ổn định số/vật lý (phần đã chạy không được báo là đã tới mục tiêu) |
| 2 | tham số hoặc cấu hình không hợp lệ (thiếu/có cả `--episode` và `--checkpoint`, hệ số tốc độ ≤ 0, chỉ số mục tiêu ngoài phạm vi, cờ sai chế độ, thiếu khoá cấu hình) |
| 4 | checkpoint không dùng được (không tồn tại, hỏng, thiếu thành phần, khác cấu trúc mạng, khác hash XML) |
| 5 | episode không dùng được (không tồn tại, không đọc được, hỏng, sai khuôn, giá trị không hữu hạn, phiên bản định dạng lạ) |
| 6 | lệch mô hình: hash XML khác (không có cờ chấp nhận) hoặc cấu trúc không tương thích (kể cả có cờ) |
| 7 | không có màn hình hoặc viewer không khởi tạo được, và không chọn `--headless` |
| 8 | không ghi được episode (đường dẫn đã tồn tại, thiếu quyền, đĩa đầy) |
| 130 | bị ngắt bằng Ctrl-C — không để lại tệp episode dở dang |

Mã 3 ("chưa triển khai") của stub 001 không còn dùng ở đây.

## Quy tắc xuyên suốt

- Hành động trong demo luôn là `u_i ∈ [0,1]` cho 6 cơ do policy xuất (INV-002); không có cờ nào nhận hành động, lực hay toạ độ tay; replay chỉ đặt trạng thái đã ghi để vẽ.
- Đường dẫn trong mọi bản ghi là tương đối so với gốc dự án hoặc thư mục run, không tuyệt đối riêng của máy (constitution VI).
- Giá trị không áp dụng ghi tường minh `null` (hành động ở khung 0, `source` khi không từ checkpoint, `end_reason` khi chưa kết thúc), không bỏ trường, không NaN/Infinity (INV-003, NFR-REL-001).
- Nhãn hiển thị = tên cơ trong `model.muscle_names` của episode; dây chỉ mang chỉ số (`activation[i]`), nhãn chỉ gắn ở HUD từ `muscle_names` (không có bảng ánh xạ nhãn khác).
