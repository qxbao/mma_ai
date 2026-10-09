---
id: "DM-005"
title: "M1 (4/4) — Mô hình dữ liệu (Data model)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "005-replay-3d-muscle-demo"
version: "1.0.0"
---

# Mô hình dữ liệu — M1 (4/4)

- [Thực thể → đối tượng / tệp](#thuc-the-doi-tuong-tep)
- [Luật nhất quán mà JSON Schema không diễn đạt được (kiểm trong `read_episode`, FR-009)](#luat-nhat-quan-ma-json-schema-khong-dien-dat-duoc-kiem-trong-read-episode-fr-009)
- [Ánh xạ nhãn ↔ khoá](#anh-xa-nhan-khoa)
- [Trạng thái của một phiên `replay.py`](#trang-thai-cua-mot-phien-replaypy)
- [Tệp cấu hình và nơi dùng](#tep-cau-hinh-va-noi-dung)
- [Bất biến liên quan dữ liệu](#bat-bien-lien-quan-du-lieu)


Không có cơ sở dữ liệu ⇒ không có bảng `TBL-*`, không có index; không có `EVT-*`. Dữ liệu là đối tượng trong bộ nhớ và **tệp JSON** theo `contracts/*.schema.json`. Tên trường KHÔNG chép lại ở đây — xem schema; chỉ ghi luật và quan hệ. Mọi tệp trong `contracts/examples/` là **ví dụ minh hoạ khuôn**, không phải kết quả đo.

<a id="thuc-the-doi-tuong-tep"></a>
## Thực thể → đối tượng / tệp

| Thực thể (spec) | Đối tượng | Khuôn dây / tệp | Người ghi | Người đọc |
|---|---|---|---|---|
| Episode đã ghi | `Episode` | tệp `*.episode.json` — [episode.schema.json](contracts/episode.schema.json) | `record_episode` → `write_episode` (chỉ khi `--save-episode`) | `read_episode` (`--episode`), con 3 (tuỳ chọn), người dùng, test |
| Khung | `Frame` | phần tử của `episode.frames`; khung nội suy `frame_at(t)` chỉ tồn tại trong bộ nhớ | `record_episode` | `play`, `summarize_episode` |
| Phiên phát | `PlaybackStats` + `ModelCheck` | không có tệp riêng; kết quả vào tóm tắt | `play`, `check_model` | `summarize_episode`, stdout |
| Tóm tắt không màn hình | dict | stdout (`--headless`) — [replay-summary.schema.json](contracts/replay-summary.schema.json) | `summarize_episode` | người dùng, test |
| Cấu hình replay | `ReplayConfig` | `src/mma_ai/visualization/replay.yaml` — [replay-config.schema.json](contracts/replay-config.schema.json) | người dùng | `visualization.*` |

Quan hệ: một `Episode` có ≥ 1 `Frame` (khung 0 = sau `reset`); `Episode.source` trỏ tới một checkpoint của con 2 (qua tên + hash nội dung, không qua khoá ngoại) hoặc `null`; `Episode.model.sha256` so với mô hình hiện tại bằng `check_model`. Con 4 **không** thêm trường vào hồ sơ run của con 2.

<a id="luat-nhat-quan-ma-json-schema-khong-dien-dat-duoc-kiem-trong-read-episode-fr-009"></a>
## Luật nhất quán mà JSON Schema không diễn đạt được (kiểm trong `read_episode`, FR-009)

| # | Luật | Vi phạm ⇒ | Test |
|---|---|---|---|
| R1 | `outcome.n_actions = len(frames) − 1` | `EpisodeInvalid` nêu hai số | `test_episode::test_n_actions_matches_frames` |
| R2 | `frames[k].t_s` không giảm; `frames[0].t_s = 0`; hiệu hai khung liền kề ≈ `timing.action_dt_s` (dung sai 1×10⁻⁶ s) | `EpisodeInvalid` nêu chỉ số khung | `test_episode::test_time_monotonic` |
| R3 | `len(frames[k].qpos) = model.nq`, `len(frames[k].qvel) = model.nv` ở mọi khung | `EpisodeInvalid` | `test_episode::test_state_dims_match_model` |
| R4 | `frames[0].excitation = null` và `frames[k≥1].excitation ≠ null` | `EpisodeInvalid` | `test_episode::test_first_frame_has_no_action` |
| R5 | `muscle_names` đủ 6 tên khác nhau (schema đã ép; thêm: không có chuỗi rỗng sau khi cắt khoảng trắng) | `EpisodeInvalid` | `test_episode::test_muscle_names_unique` |
| R6 | `outcome.end_reason = "reached"` ⇔ `outcome.reached = true` ⇔ `terminated = true`; `"max_actions"` ⇔ `truncated = true` | `EpisodeInvalid` | `test_episode::test_outcome_consistent` |
| R7 | mọi số hữu hạn (`allow_nan=False` khi ghi; `parse_constant` từ chối `NaN`/`Infinity` khi đọc) | `EpisodeInvalid` nêu trường | `test_episode::test_nonfinite_rejected` |

<a id="anh-xa-nhan-khoa"></a>
## Ánh xạ nhãn ↔ khoá

Dây chỉ mang **chỉ số**: `activation[i]`, `excitation[i]` với `i ∈ 0…5`; **nhãn** là `model.muscle_names[i]` của chính episode (thứ tự cố định theo mô hình lúc ghi; ĐÃ ĐO với `myoelbow_1dof6muscles.xml`: `TRIlong, TRIlat, TRImed, BIClong, BICshort, BRA`). HUD gắn nhãn từ `muscle_names`, không có bảng nhãn thứ hai trong mã; so sánh với mô hình hiện tại là so *danh sách có thứ tự* (R5 + `check_model`).

<a id="trang-thai-cua-mot-phien-replaypy"></a>
## Trạng thái của một phiên `replay.py`

```text
khởi động → [tham số/cấu hình hợp lệ?]        --không--> mã 2
          → nạp nguồn (episode đọc được / checkpoint nạp được?) --không--> mã 5 | 4
          → kiểm lệch mô hình                  --lệch/không tương thích--> mã 6
          → --headless?                        --có--> tóm tắt (mã 0)
          → màn hình khả dụng?                 --không--> mã 7
          → [demo] chạy trọn episode → [có --save-episode] ghi nguyên tử --lỗi--> mã 8
          → mở viewer → phát (lặp nếu --loop) → giữ khung cuối → đóng cửa sổ → mã 0
```

Không có trạng thái bền; ngắt (Ctrl-C) ở bất kỳ nơi nào ⇒ xoá tệp tạm, mã 130.

<a id="tep-cau-hinh-va-noi-dung"></a>
## Tệp cấu hình và nơi dùng

| Tệp | Khoá (đủ trong schema) | Dùng bởi |
|---|---|---|
| `src/mma_ai/visualization/replay.yaml` | `playback.{speed, loop, display_hz, hold_after_end_s}`, `demo.{split, target_index, seed}`, `hud.{decimals, bar_width}`, `target_marker.{radius_m, rgba}` | `replay_config` → `playback`, `viewer`, `hud`, `replay` |

<a id="bat-bien-lien-quan-du-lieu"></a>
## Bất biến liên quan dữ liệu

INV-003 (episode tự đủ: seed · hash XML · 6 tên cơ · phiên bản · `null` tường minh) · INV-005 (chỉ đọc, không ghi đè) · INV-006 (làm tròn chỉ ở HUD) — khai ở `spec.md`; file này chỉ tham chiếu.
