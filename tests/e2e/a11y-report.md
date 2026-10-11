# Báo cáo khả năng tiếp cận (accessibility) — dashboard PPO

## Phạm vi

Màn đã rà: `/` của `python -m mma_ai.monitoring.cli` (API-TRN-0002, AC-7).
Kiểm tra tĩnh dựa trên HTML/CSS tự chứa trong `src/mma_ai/monitoring/dashboard.py`; kiểm tra động nằm trong `test_ac_7_progress_ui_live` và chạy trên Chromium thật.

| Màn (UI-ID) | Tiêu chí WCAG | Phần tử | Bằng chứng | Mức | Ai sửa |
|---|---|---|---|---|---|
| Dashboard (API-TRN-0002) | 1.3.1, 2.4.6 | `h1`, các `h2` panel | `test_ac_7_progress_ui_live`: một `h1`, năm panel `h2` | A | Không có vi phạm |
| Dashboard (API-TRN-0002) | 1.4.10 | `html`, lưới `.grid` | Chromium 1280×800: `scrollWidth <= innerWidth` | AA | Không có vi phạm |
| Dashboard (API-TRN-0002) | 3.1.1 | `<html lang="vi">` | `test_ac_7_progress_ui_live` | A | Không có vi phạm |
| Dashboard (API-TRN-0002) | 4.1.3 | `#status-badge`, các metric cập nhật tự động | Rà tĩnh `dashboard.py`: trạng thái thay bằng JavaScript nhưng không có `aria-live`/`role="status"` | AA | builder |

Không có phần tử tương tác, biểu mẫu, modal hoặc ảnh trong dashboard hiện tại; vì vậy không có hành trình Tab/Esc hay `alt` để kiểm trong phạm vi màn này. Axe-core không được khai là dependency của dự án, nên không tự cài thêm.
