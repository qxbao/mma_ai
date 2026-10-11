---
id: "RESEARCH-007"
title: "Nghiên cứu Phase 0 — nguyên nhân hai test đỏ và cách đo"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-11"
feature: "007-stabilize-viewer-tests"
version: "1.0.0"
---

# Research (Phase 0): nguyên nhân hai test đỏ và cách đo

- [Q1 — Vì sao `test_view3d_process_separate` báo `pid is None`? (US2, AC-2)](#q1-vi-sao-test-view3d-process-separate-bao-pid-is-none-us2-ac-2)
- [Q2 — Vì sao nhánh "có màn hình" của `test_real_viewer_plays_or_reports_no_display` quá 25 s? (US1, AC-1, AC-3)](#q2-vi-sao-nhanh-co-man-hinh-cua-test-real-viewer-plays-or-reports-no-display-qua-25-s-us1-ac-1-ac-3)
- [Q3 — Hạn mức nào thì "tất định"?](#q3-han-muc-nao-thi-tat-dinh)
- [Q4 — Bằng chứng "xanh" tối thiểu?](#q4-bang-chung-xanh-toi-thieu)
- [Tổng hợp việc còn mở (không chặn plan)](#tong-hop-viec-con-mo-khong-chan-plan)


Quy ước nhãn: **ĐÃ ĐỌC** = rút ra từ việc đọc mã trên nhánh tích hợp, chưa chạy; **ĐÃ ĐO** = có số đo từ lần chạy (chỉ các số đã ghi ở research của 005 được dẫn lại); **CHƯA KIỂM** = chưa làm. Lượt đặc tả không dựng được môi trường có `mujoco`/`myo-sim` ở máy này nên **không có số đo mới**; mọi kết luận dưới đây là giả thuyết có căn cứ mã, chờ builder đo (FR-005).

<a id="q1-vi-sao-test-view3d-process-separate-bao-pid-is-none-us2-ac-2"></a>
## Q1 — Vì sao `test_view3d_process_separate` báo `pid is None`? (US2, AC-2)

- **Quyết định**: nguyên nhân là cuộc đua trong kiểm thử, sửa ở kiểm thử bằng cách chờ có điều kiện "đã có PID".
- **Căn cứ (ĐÃ ĐỌC)**:
  1. Kiểm thử thay `multiprocessing.Process` bằng hàm tạo; hàm này tạo đối tượng rồi **ngay lập tức** thêm vào `started_processes`, chưa gọi `.start()`.
  2. `mma_ai.monitoring.cli.main` (chạy trong một luồng riêng của kiểm thử) tạo `Process(... name="MMA-AI-View3D", daemon=True)` rồi **mới** gọi `.start()` ở dòng kế tiếp.
  3. Vòng chờ của kiểm thử là `while time.time() < deadline and not started_processes` — thoát ngay khi danh sách có phần tử, tức là **giữa bước tạo và bước `.start()`**; khẳng định `viewer_proc.pid is not None` đứng ngay sau. Với đối tượng chưa `.start()`, `pid` là `None` ⇒ đúng thông báo `Process MMA-AI-View3D … .pid is None` của cổng.
  4. Vì khoảng giữa hai dòng của `main` rất ngắn, lỗi chỉ lộ khi bộ lập lịch cắt luồng ở đó — tức **chập chờn khi máy bận**, khớp triệu chứng.
- **Không nằm ở `src/`**: `main` làm đúng việc (tạo rồi khởi chạy); không có hợp đồng nào bảo đảm "đối tượng đã tồn tại ⇒ đã có PID".
- **Cách đo xác nhận (builder)**: (a) tái hiện đỏ: chạy kiểm thử gốc nhiều lần dưới tải CPU nền và ghi tỷ lệ đỏ; hoặc tái hiện tất định bằng cách chèn độ trễ nhỏ giữa tạo và `.start()` **trong bản sao thử nghiệm ở `tmp`**, không trong `src/`; (b) sau sửa: cùng điều kiện, 0 lần đỏ.
- **Phương án đã xét**: (A) kiểm `proc.pid` rồi thử lại — chọn, dạng poll có hạn mức; (B) `time.sleep` cố định — loại (phụ thuộc thời gian, không tất định); (C) bọc `Process.start` để phát tín hiệu `threading.Event` khi đã khởi chạy — thêm đường vòng phức tạp hơn mà không chặt hơn; chỉ dùng nếu poll không đủ; (D) sửa `src/` để tạo-và-khởi chạy nguyên tử — ngoài phạm vi, không cần.
- **Điều kiện phụ**: hạn mức chờ PID hữu hạn 5 s (đủ rộng cho máy bận, hữu hạn để không treo); thoát sớm (`exitcode` không `None`) phải được báo riêng.

<a id="q2-vi-sao-nhanh-co-man-hinh-cua-test-real-viewer-plays-or-reports-no-display-qua-25-s-us1-ac-1-ac-3"></a>
## Q2 — Vì sao nhánh "có màn hình" của `test_real_viewer_plays_or_reports_no_display` quá 25 s? (US1, AC-1, AC-3)

- **Quyết định**: **CHƯA CÓ** — cần đo. Kế hoạch đo và cây quyết định dưới đây là sản phẩm của Phase 0.
- **Điều đã biết (ĐÃ ĐỌC)**:
  1. Kiểm thử dùng `subprocess.run(..., timeout=25.0)` và cấu hình `playback.hold_after_end_s: 0.1`; luồng phát: `play(...)` rồi giữ khung cuối ≈ 0,1 s (`ViewerSink.auto_close_on_hold` là `False`, nên vòng giữ khung chạy theo `hold_after_end_s`), sau đó `sink.close()`, in tóm tắt, trả 0; `cli.main` sau cùng gọi `os._exit(mã)` nếu viewer đã mở. Về mặt logic, một lần chạy bình thường chỉ mất cỡ nạp `mujoco` + dựng mô hình + mở cửa sổ + ≈ 0,2 s phát + đóng.
  2. `display_available()` chỉ kiểm `glfw.init()` có thành công không; **không** thử tạo cửa sổ hay ngữ cảnh GL. Nhánh "có màn hình" được chọn khi `glfw.init()` thành công, dù cửa sổ GL có tạo được hay không.
  3. `ViewerSink.__init__` gọi `mujoco.viewer.launch_passive(...)` không hạn mức; `close()` gọi `handle.close()`.
  4. Cổng tests chạy `pytest -n auto` (song song).
- **Điều đã đo ở 005 (dẫn lại, ĐÃ ĐO ở research của 005)**: `glfw.init()` ≈ 0,03 s; khi không khởi tạo được GLFW mà vẫn gọi `launch_passive` thì **MuJoCo kết thúc cả tiến trình mã 1 sau ≈ 0,45 s** (không phải treo); viewer thụ động thoát chập chờn — `SIGSEGV` (139) hoặc **treo tới khi bị giết** ở một số lần chạy; cách `os._exit(mã)` sau khi đóng `handle` đạt 3/3 lần mã 0.
- **Giả thuyết (CHƯA KIỂM), xếp theo cách phân biệt được bằng một lần đo**:

| # | Giả thuyết | Dấu hiệu khi đo | Thuộc về |
|---|---|---|---|
| H1 | Lệnh con **treo** trong `launch_passive` hoặc trong `handle.close()` (viewer thụ động của MuJoCo/GLFW), không tiến triển dù chờ lâu | ngăn xếp dừng ở `launch_passive`/`close`/`join`; CPU ≈ 0; không có dòng tóm tắt | `src/` (lớp bao viewer / FR-011, FR-014 của 005) ⇒ **AC-5** |
| H2 | `display_available()` báo "có" (GLFW khởi tạo được) nhưng **không có cửa sổ GL dùng được** ở môi trường cổng (ví dụ máy chủ X thiếu GLX/không có GPU, `MUJOCO_GL` lạ) ⇒ viewer không mở hoặc chờ mãi | ngăn xếp/đầu ra có lỗi GL/GLFW tạo cửa sổ; chạy tay cho cùng kết quả ở môi trường đó | `src/` (khoảng trống 005 FR-011: "có biến hiển thị nhưng viewer không khởi tạo được ⇒ như không có màn hình") ⇒ **AC-5** |
| H3 | **Chậm nhưng kết thúc**: nạp `mujoco` + dựng mô hình + mở cửa sổ khi nhiều worker `-n auto` cùng chiếm CPU/đĩa vượt 25 s | chạy một mình kết thúc nhanh (vài giây); chạy dưới tải/`-n auto` kết thúc sau 25 s nhưng có tóm tắt đầy đủ, mã 0 | kiểm thử (hạn mức/độ chịu tải) ⇒ sửa kiểm thử |
| H4 | **Tranh chấp giữa các cửa sổ viewer chạy song song** trên cùng màn hình/máy chủ X (nhiều worker cùng mở viewer thật) làm một số lần chậm hoặc treo | chạy một mình xanh; chạy hai tiến trình cùng lúc đỏ; khoá nối tiếp làm hết đỏ | kiểm thử (nối tiếp hoá) nếu chạy một mình luôn xanh; nếu vẫn treo ở một mình thì quay về H1 |
| H5 | Kiểm thử tự làm hỏng điều kiện: `display_available()` gọi `glfw.init()`/`terminate()` **trong tiến trình pytest** rồi mới chạy lệnh con, để lại trạng thái làm lệnh con chậm/treo | bỏ lời gọi này khỏi tiến trình pytest thì hết đỏ (đo bằng cách chạy lệnh con riêng) | kiểm thử (chọn nhánh bằng tiến trình con riêng) |

- **Cách đo (builder, mỗi lượt 1–2 lần chạy; ghi cộng dồn)**:
  1. **Một mình, có dấu vết**: chạy lệnh con của nhánh có màn hình bằng tay trong `tmp` với `python -X faulthandler`, hạn mức 20 s, rồi gửi `SIGABRT` khi quá hạn để lấy ngăn xếp mọi luồng (không sửa `src/`); ghi thời gian từng giai đoạn (nạp `mujoco`, dựng mô hình, mở viewer, phát, đóng) bằng dấu thời gian đầu ra/`strace -tt`/`-X importtime` tuỳ có sẵn. Ghi `DISPLAY`, `WAYLAND_DISPLAY`, `MUJOCO_GL`, `LIBGL_ALWAYS_SOFTWARE`.
  2. **Một mình, lặp**: 2 lần/lượt ⇒ ghi mã thoát, thời gian, có tóm tắt hay không.
  3. **Dưới tải**: cùng lệnh khi chạy kèm tải CPU nền và khi chạy hai tiến trình viewer cùng lúc (tách H3 với H4).
  4. **Kết luận** bằng cây quyết định dưới.
- **Cây quyết định (FR-007, AC-5)**:
  - Kết quả cho thấy H1 hoặc H2 (treo/không khởi tạo ở một mình, hoặc môi trường cổng không có cửa sổ GL dùng được nhưng mã vẫn chọn đường viewer) ⇒ **DỪNG sửa T-A**; không đổi `src/`; báo cáo nêu tệp, hàm (`ViewerSink.__init__`/`close`, `display_available`, `replay.py` bước 4/7.2), ngăn xếp/số đo, và **đề xuất** cho vai khác (ví dụ: `display_available()` thử tạo cửa sổ ẩn có hạn mức; hoặc `ViewerSink` chuyển lỗi khởi tạo thành mã 7). Chỉ giữ phần độ cứng chẩn đoán FR-002.
  - Kết quả cho thấy H3 ⇒ hiệu chỉnh hạn mức theo số đo (p95 dưới tải × hệ số an toàn, khai tường minh và nêu căn cứ trong chú thích) — không nới khẳng định nào.
  - Kết quả cho thấy H4 ⇒ nối tiếp hoá các lần mở viewer thật bằng khoá tệp nhẹ dưới thư mục tạm; vẫn đo lại.
  - Kết quả cho thấy H5 ⇒ chọn nhánh bằng cách gọi `display_available()` trong một tiến trình con ngắn có hạn mức, hoặc đổi thứ tự sao cho tiến trình pytest không giữ trạng thái GLFW.
  - Không tái hiện được đỏ ở bất kỳ phép đo nào ⇒ ghi "không tái hiện được trên môi trường đo (mô tả)" và vẫn áp dụng phần độ cứng FR-002; **không** tuyên bố đã sửa gốc.
- **Phương án đã xét cho cách chọn nhánh**: (a) giữ `display_available()` — chọn (D5); (b) tự thêm dò cửa sổ GL trong kiểm thử rồi chọn nhánh khác với CLI — loại: kiểm thử và CLI sẽ bất đồng nhánh (kiểm thử chọn "không màn hình" nhưng CLI vẫn đi đường viewer), tức là che khoảng trống của `src/`.

<a id="q3-han-muc-nao-thi-tat-dinh"></a>
## Q3 — Hạn mức nào thì "tất định"?

- **Quyết định**: hạn mức luôn là hằng số đặt tên, hữu hạn, có chú thích căn cứ; hết hạn ⇒ lỗi có chẩn đoán. Với T-B: 5 s chờ PID (D1). Với T-A: giữ 25 s cho tới khi có số đo; nếu đổi thì theo p95 đo được.
- **Rationale**: "tất định" nghĩa là kết quả phụ thuộc trạng thái (đã có PID, đã có tóm tắt), không phụ thuộc may rủi về thời gian; hạn mức chỉ là lưới an toàn có chẩn đoán.
- **Phương án đã xét**: không hạn mức (loại — treo vô hạn); hạn mức rất lớn (loại — che sự cố, kéo dài cổng).

<a id="q4-bang-chung-xanh-toi-thieu"></a>
## Q4 — Bằng chứng "xanh" tối thiểu?

- **Quyết định**: NFR-REL-001 (5/5 mỗi kiểm thử chạy riêng; T-B thêm 5/5 có tải nền) + quét `skip`/`xfail`/`importorskip` + so diff với `outputs` + `ruff`/`mypy` xanh; bằng chứng do cổng máy sinh ở `evidence/`.
- **Rationale**: chập chờn chỉ lộ khi lặp; cổng một lần xanh không chứng minh được gì (hiến chương I).
- **Phương án đã xét**: lặp 20 lần — chính xác hơn nhưng vượt giới hạn 1–2 lần/lượt của yêu cầu; để mở nâng ngưỡng sau khi có số đo.

<a id="tong-hop-viec-con-mo-khong-chan-plan"></a>
## Tổng hợp việc còn mở (không chặn plan)

- Số đo T-A (Q2) — CHƯA KIỂM; thuộc task thi công.
- Môi trường cổng có/không có cửa sổ GL dùng được — CHƯA KIỂM; báo cáo phải ghi môi trường đã đo.
