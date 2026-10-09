---
id: "CLI-004"
title: "M1 (3/4) — Hợp đồng dòng lệnh"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "004-eval-vs-random-plots"
version: "1.0.0"
---

# Hợp đồng — dòng lệnh đánh giá

Không có dịch vụ mạng, không điểm HTTP, không phân quyền. "Hợp đồng dây" gồm (1) MỘT lệnh CLI, (2) các tệp kết quả có khuôn JSON Schema (draft 2020-12, ví dụ ở `examples/`, test `test_contract_examples_eval`; schema báo cáo nhúng cấu hình đánh giá nên test kiểm `report.config` bằng `eval-config.schema.json`). Tên trường KHÔNG chép ở đây — xem schema.

## Lệnh (CMD)

| Mã | Lệnh | Vào | Ra | Aggregate · sự kiện · quyền | FR / AC |
|---|---|---|---|---|---|
| `CMD-EVL-0001` | `python scripts/evaluate.py --checkpoint PATH [--config PATH] [--out DIR] [--repeats N] [--eval-seed N] [--runs-dir DIR]` | tệp checkpoint (`.pt`) hoặc con trỏ `checkpoints/latest.json` của một run; cấu hình `configs/eval_elbow.yaml` (khuôn [eval-config.schema.json](eval-config.schema.json)); cờ dòng lệnh ghi đè cấu hình và được lưu nguyên văn vào báo cáo | thư mục `runs/<run_id>/eval/<eval_id>/` gồm `report.json` ([eval-report.schema.json](eval-report.schema.json)), `episodes.csv`, `charts/{loss,reward,activation}.png`; tóm tắt bằng tiếng Việt trên stdout (chỉ số hai policy, kết luận, khoảng tin cậy, đường dẫn kết quả) | aggregate: Lượt đánh giá · không phát sự kiện (không có `EVT-*`) · không `PERM-*` | FR-001…FR-019 / AC-1…AC-5 |

### Quy tắc của `evaluate.py`

- **Thứ tự bắt buộc** (mỗi bước dừng lệnh nếu lỗi và *trước* mọi ghi đĩa): (1) nạp và kiểm cấu hình; (2) nạp checkpoint chỉ-đọc; (3) đọc hồ sơ run, kiểm hash XML; (4) kiểm giao rỗng tập train/seed (INV-001); (5) chạy episode hai policy; (6) tính chỉ số, khoảng tin cậy, kết luận; (7) đọc nhật ký, vẽ biểu đồ; (8) ghi vào thư mục tạm rồi đổi tên thành thư mục công bố (INV-004). Không tạo thư mục kết quả trước bước (8).
- `--checkpoint`: `.pt` hoặc `latest.json`. Không tồn tại / hỏng / thiếu thành phần / khác cấu trúc mạng / khác hash XML ⇒ lỗi nêu nguyên nhân, **mã 4**, không in chỉ số, không tạo thư mục `eval` (AC-5). Nếu checkpoint không nằm trong thư mục run (có `manifest.json` ở thư mục cha của `checkpoints/`) thì phải có `--out`; thiếu ⇒ mã 2. Có `--out` mà vẫn không thiết lập được tập train của run ⇒ mã 5 (FR-009).
- `--repeats`, `--eval-seed`, `--runs-dir`: ghi đè khoá cùng tên (`episodes.repeats`, `seeds.episode_base`, `paths.runs_dir`). Tiêu chí kết luận (`criterion.*`) **chỉ** đọc từ tệp cấu hình, không có cờ ghi đè khi chạy từng lượt để tiêu chí không bị sửa theo kết quả (INV-006); đổi tiêu chí = đổi tệp cấu hình, và tiêu chí đã dùng luôn nằm trong báo cáo.
- Mọi lỗi in tiếng Việt, nêu giá trị/ngữ cảnh (đường dẫn, seed trùng, mục tiêu vi phạm, thành phần thiếu, thẻ nhật ký thiếu).
- Chỉ đọc: lệnh không sửa bất kỳ tệp nào ngoài thư mục `eval` của run (INV-005).

### Mã thoát

| Mã | Ý nghĩa |
|---|---|
| 0 | lượt đánh giá hoàn tất, báo cáo và đủ ba biểu đồ đã lưu (**bất kể** kết luận "tốt hơn" hay "không tốt hơn") |
| 1 | lỗi đánh giá không lường trước (ví dụ môi trường ném lỗi ngoài lỗi mất ổn định đã xử lý) — không tạo kết quả |
| 2 | tham số hoặc cấu hình không hợp lệ (giá trị ≤ 0, mức tin cậy ngoài (0,1), thiếu khoá, thiếu `--out` cho checkpoint ngoài run, ít hơn `min_targets` mục tiêu) |
| 4 | checkpoint không dùng được (không tồn tại, hỏng, thiếu thành phần, khác cấu trúc, khác hash XML) |
| 5 | tập đánh giá giao tập train, seed đánh giá trùng seed train, hoặc không thiết lập được tập/seed train của run |
| 6 | đánh giá xong và kết quả số ĐÃ LƯU (`status: done_charts_incomplete`) nhưng không tạo đủ ba biểu đồ; stderr nêu biểu đồ nào và vì sao |
| 7 | không ghi được kết quả (đĩa đầy, thiếu quyền) — không tạo bản ghi nào |
| 130 | bị ngắt bằng Ctrl-C — thư mục tạm bị xoá, không có bản ghi |

Mã 3 của `train.py` ("stage chưa triển khai") không dùng ở đây.

## Quy tắc xuyên suốt

- Hành động của cả hai policy luôn là `u_i ∈ [0,1]` cho 6 cơ (INV-003); không có cờ nào nhận hành động hay toạ độ tay.
- Đường dẫn trong mọi bản ghi là tương đối so với thư mục run hoặc gốc dự án, không tuyệt đối riêng của máy (constitution VI).
- Giá trị không áp dụng ghi tường minh `null` kèm `reason`, không bỏ trường, không NaN/Infinity (FR-017).
