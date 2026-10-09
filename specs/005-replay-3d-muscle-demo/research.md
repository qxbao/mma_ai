---
id: "RES-005"
title: "M1 (4/4) — Nghiên cứu Phase 0 (Research)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "005-replay-3d-muscle-demo"
version: "1.0.0"
---

# Nghiên cứu Phase 0 — M1 (4/4): Replay 3D và demo điều khiển bằng cơ

- [Q1. MuJoCo Viewer: kiểu mở, vẽ mục tiêu, hiển thị activation (FR-001, FR-004, FR-005)](#q1-mujoco-viewer-kieu-mo-ve-muc-tieu-hien-thi-activation-fr-001-fr-004-fr-005)
- [Q2. Phát hiện "không có màn hình" (FR-011, NFR-HEADLESS-001)](#q2-phat-hien-khong-co-man-hinh-fr-011-nfr-headless-001)
- [Q3. Mã thoát khi dọn dẹp đồ hoạ (FR-014, AC-1)](#q3-ma-thoat-khi-don-dep-do-hoa-fr-014-ac-1)
- [Q4. Định dạng episode (FR-007, FR-008, FR-009, INV-003, NFR-REL-001)](#q4-dinh-dang-episode-fr-007-fr-008-fr-009-inv-003-nfr-rel-001)
- [Q5. Bộ lập nhịp thời gian thực (FR-006, NFR-PERF-001)](#q5-bo-lap-nhip-thoi-gian-thuc-fr-006-nfr-perf-001)
- [Q6. Lấy trạng thái từ môi trường để ghi episode (FR-007, FR-003, INV-002)](#q6-lay-trang-thai-tu-moi-truong-de-ghi-episode-fr-007-fr-003-inv-002)
- [Q7. Kiểm lệch mô hình khi phát lại (FR-012, INV-001)](#q7-kiem-lech-mo-hinh-khi-phat-lai-fr-012-inv-001)
- [Q8. Chế độ không màn hình: kiểm dữ liệu thay vì xuất khung (FR-010, KQ-3)](#q8-che-do-khong-man-hinh-kiem-du-lieu-thay-vi-xuat-khung-fr-010-kq-3)
- [Q9. Cách kiểm thử phần viewer mà không bỏ qua test (FR-019, hiến chương II)](#q9-cach-kiem-thu-phan-viewer-ma-khong-bo-qua-test-fr-019-hien-chuong-ii)
- [Q10. Phụ thuộc, cấu hình, ranh giới với 003 (FR-015, FR-017)](#q10-phu-thuoc-cau-hinh-ranh-gioi-voi-003-fr-015-fr-017)
- [Q11. Còn mở (chuyển thành việc triển khai bắt buộc có ghi kết quả)](#q11-con-mo-chuyen-thanh-viec-trien-khai-bat-buoc-co-ghi-ket-qua)


Mục "ĐÃ ĐO" là kết quả chạy thật ngày 2026-10-09 trên máy phát triển: Linux gốc (kernel 7.0, **không phải WSL**), `DISPLAY=:0` có X server thật, Python 3.11.15 do `uv` cấp, **chưa có NVIDIA**, trong môi trường ảo tạm: `mujoco 3.15.0`, `myo-sim 0.2.3`, `numpy`, `jsonschema`. Mã thăm dò chạy ở thư mục tạm, KHÔNG nằm trong repo. Mục "CHƯA KIỂM" là việc phải xác minh ở bước triển khai — plan không giả định kết quả. Con số thời gian chỉ để đặt cỡ độ lớn, KHÔNG phải cam kết hay dự báo (master plan XI.10). Spec KHÔNG khẳng định policy học được tốt; nghiên cứu này chỉ chọn cách hiển thị và lưu.

<a id="q1-mujoco-viewer-kieu-mo-ve-muc-tieu-hien-thi-activation-fr-001-fr-004-fr-005"></a>
## Q1. MuJoCo Viewer: kiểu mở, vẽ mục tiêu, hiển thị activation (FR-001, FR-004, FR-005)

- **Quyết định**: dùng `mujoco.viewer.launch_passive(model, data)` — tiến trình của ta giữ vòng lặp phát: mỗi khung đặt trạng thái (`qpos`, `qvel`, `act`) vào `MjData`, gọi `mj_forward`, cập nhật cảnh phụ, rồi `handle.sync()`. Mục tiêu vẽ bằng một hình cầu trong `handle.user_scn` (`mjv_initGeom`, màu tách biệt khỏi thân); 6 activation hiện bằng `handle.set_texts(...)` (bảng chữ: tên cơ, giá trị 3 chữ số, thanh khối ký tự); cảnh báo "MÔ HÌNH LỆCH" cũng là một dòng `set_texts` luôn hiện. `launch` kiểu chặn (viewer tự chạy mô phỏng) bị loại vì nó chạy vật lý riêng, không phát lại trạng thái đã ghi.
- **Căn cứ (ĐÃ ĐO)**: `Handle` của `mujoco 3.15.0` có `user_scn`, `lock`, `sync`, `set_texts`, `set_figures`, `set_images`, `is_running`, `close`. Mở cửa sổ mất ≈ 0,53 s. Trong 3 s, vòng lặp "đặt `qpos` → `mj_forward` → ghi 1 hình cầu vào `user_scn` → `set_texts` → `sync` → ngủ 1/60 s" chạy **123 vòng** (≈ 41 vòng/s với nhịp ngủ 1/60 s ⇒ chi phí cập nhật + đồng bộ ≈ 7–8 ms/vòng, bỏ phần ngủ). Đặt trạng thái + `mj_forward` cho 100 khung mất 0,0007 s tổng (≈ 7 µs/khung) — không đáng kể so với đồ hoạ.
- **Căn cứ (ĐÃ ĐO) về mô hình**: `myoelbow_1dof6muscles.xml` có `nq = nv = 1`, `nu = 6`, `na = 6` (mỗi cơ một trạng thái kích hoạt `act`), 6 cơ `TRIlong, TRIlat, TRImed, BIClong, BICshort, BRA`, site `wrist` có (`site_xpos` cho đầu mút tay), SHA-256 bắt đầu `384dcb555561287f` (khớp `002-elbow-muscle-env/research.md`).
- **Phương án đã loại**: (a) vẽ activation bằng `set_figures` (đồ thị đường theo thời gian) — API có nhưng cấu hình `mjvFigure` rườm rà; chuỗi theo thời gian đã nằm trong tệp episode và tóm tắt, bảng chữ đủ cho "thấy 6 giá trị"; để dành làm cải tiến sau, không là yêu cầu; (b) tô màu cơ theo activation bằng cờ trực quan hoá actuator của MuJoCo — **CHƯA KIỂM** có hiển thị cơ khuỷu hay không và không cho số; (c) dựng cửa sổ bằng thư viện khác (Open3D, PyVista) — thêm phụ thuộc, yêu cầu ghi "MuJoCo Viewer".

<a id="q2-phat-hien-khong-co-man-hinh-fr-011-nfr-headless-001"></a>
## Q2. Phát hiện "không có màn hình" (FR-011, NFR-HEADLESS-001)

- **Quyết định**: `display_available()` gọi `glfw.init()` **trong chính tiến trình** (nhập `glfw` chỉ ở đường có viewer, không ở `--headless`): trả `True` thì gọi `glfw.terminate()` và cho mở viewer; trả `False` (kèm cảnh báo của glfw đã bị chặn) thì báo lỗi tiếng Việt và thoát. Không dựa chỉ vào biến môi trường `DISPLAY`/`WAYLAND_DISPLAY`, vì biến đặt nhưng màn hình hỏng (`DISPLAY=:99`) cũng phải được bắt.
- **Căn cứ (ĐÃ ĐO)**: `glfw.init()` trả `1` sau 0,033 s khi `DISPLAY=:0`; trả `0` sau 0,027 s khi `DISPLAY=:99` (không tồn tại) và khi `DISPLAY` và `WAYLAND_DISPLAY` bỏ đặt — **không treo, không crash**, chỉ in cảnh báo `GLFWError`. Ngược lại, nếu bỏ qua bước kiểm và gọi thẳng `launch_passive` khi không có màn hình, MuJoCo in `ERROR: could not initialize GLFW` bằng tiếng Anh từ mã C rồi **kết thúc tiến trình mã 1 sau ≈ 0,45 s** (đo ở cả hai trường hợp) — không bắt được bằng `try/except` Python và không có thông báo tiếng Việt. Vì vậy bước kiểm trước là bắt buộc, không phải tuỳ chọn.
- **CHƯA KIỂM**: WSL2/WSLg (không có máy WSL để đo); trường hợp `glfw.init()` thành công nhưng `launch_passive` vẫn thất bại (driver GL hỏng) — thiết kế bọc việc mở viewer và xử lý lỗi Python nếu có, nhưng nếu MuJoCo lại kết thúc tiến trình từ mã C thì không có cách chặn trong tiến trình; ghi vào rủi ro.
- **Phương án đã loại**: chạy viewer trong tiến trình con để bắt cái chết của nó — tăng độ phức tạp (truyền episode, đồng bộ) đổi lấy một ca hiếm chưa quan sát được; đoán theo `DISPLAY` thuần — bỏ sót ca hiển thị hỏng.

<a id="q3-ma-thoat-khi-don-dep-do-hoa-fr-014-ac-1"></a>
## Q3. Mã thoát khi dọn dẹp đồ hoạ (FR-014, AC-1)

- **Phát hiện quan trọng (ĐÃ ĐO)**: ngay cả viewer "trần" (mở `launch_passive`, `sync` 1,5 s, đóng bằng `with`) khi thoát tiến trình Python thường **sập `SIGSEGV` (mã 139) cả 3/3 lần**; thêm `user_scn`/`set_texts` cũng 3/3 lần mã 139. Các biến thể khác (`gc.collect()`, `close()` + `del`) cho kết quả **không ổn định**: mã 0, 1, 124 (treo tới khi `timeout` giết) và 139 (tổng 9 lần chạy, chỉ 1 lần mã 0). Chương trình "in xong rồi thoát" mà mã thoát là 139 sẽ vi phạm AC-1 ("không lỗi") và làm mọi kịch bản tự động hoá vô nghĩa.
- **Quyết định**: đường có viewer tính sẵn mã thoát đúng, **xả stdout/stderr, đóng `handle` rồi gọi `os._exit(mã)`** để bỏ qua bước dọn dẹp của thư viện. Đã đo cách này: **3/3 lần mã 0**, không treo. Đường không viewer (`--headless`, lỗi trước khi mở) thoát bình thường bằng `sys.exit` (không đụng GL). Hàm điều phối `run_replay(args) -> int` KHÔNG tự gọi `os._exit` (test gọi được và đọc mã); chỉ `scripts/replay.py` làm việc đó, và chỉ khi viewer đã được mở.
- **CHƯA KIỂM**: nguyên nhân gốc (driver GL của máy này, phiên bản `glfw`/`mujoco`, hay X server) và việc nó có tái diễn trên máy đích (RTX 5060) hay WSLg. Bản vá không phụ thuộc nguyên nhân gốc nên vẫn đúng nếu lỗi biến mất; nhưng không dùng nó để che lỗi thật: mã thoát vẫn lấy từ kết quả phát.
- **Phương án đã loại**: bỏ qua mã 139 vì "đã phát xong" — trái AC-1; chạy viewer trong tiến trình con rồi coi mã con là nhiễu — như Q2, thêm phức tạp không cần.

<a id="q4-dinh-dang-episode-fr-007-fr-008-fr-009-inv-003-nfr-rel-001"></a>
## Q4. Định dạng episode (FR-007, FR-008, FR-009, INV-003, NFR-REL-001)

- **Quyết định**: **một tệp JSON** (`*.episode.json`) theo khuôn `contracts/episode.schema.json` (JSON Schema draft 2020-12): phần đầu (phiên bản định dạng, thời điểm tạo, seed, mô hình: SHA-256 XML, tên 6 cơ, số khớp; mục tiêu: vị trí, tập, chỉ số, dung sai; nguồn: checkpoint tên + hash hoặc `null`; thư viện; kết quả) và mảng `frames` — **mỗi khung ứng một hành động** (khung 0 là trạng thái sau `reset`, hành động `null`). Mỗi khung: `t_s`, `qpos[nq]`, `qvel[nv]`, `activation[6]`, `excitation[6]` (kích thích `u` đã áp; `null` ở khung 0), `fingertip_position_m[3]`, `distance_m`, `reward`. Ghi bằng `json.dumps(..., allow_nan=False)` qua tệp tạm rồi `os.replace` (nguyên tử); tệp đích đã có ⇒ từ chối.
- **Căn cứ (ĐÃ ĐO)**: 100 khung với 8 trường (`qpos`, `qvel`, `act`, `ctrl`, `u`, đầu mút tay, reward, khoảng cách) tuần tự hoá thành **37 907 byte** ≈ 379 byte/khung ⇒ episode dài nhất của con 1 (100 hành động) cỡ **vài chục KB**: đọc/ghi tức thì, mở bằng trình soạn thảo được, hợp khuôn bằng `jsonschema` như các hợp đồng 001–004. Mô phỏng 100 hành động (16 bước vật lý mỗi hành động) mất ≈ 0,011 s ⇒ demo không màn hình gần như tức thì.
- **Độ chi tiết thời gian**: lưu theo **hành động** (25 Hz, 0,04 s theo `002-elbow-muscle-env`), KHÔNG theo từng bước vật lý — vì (a) con 1 không công khai trạng thái giữa các bước vật lý và con 4 không được sửa vòng bước của nó; (b) cỡ tệp nhỏ. Khi phát, giữa hai khung liên tiếp **nội suy tuyến tính** `qpos` và `activation` theo thời gian để đạt nhịp hiển thị mượt (chuyển động 1 bậc tự do, khoảng 0,04 s giữa hai khung). **Hạn chế ghi vào tóm tắt/tài liệu**: hình giữa hai khung là nội suy, không phải trạng thái mô phỏng thật; khi cần chính xác tuyệt đối, dữ liệu gốc ở các khung.
- **Phương án đã loại**: `.npz`/Parquet — nhị phân, khó kiểm bằng mắt, khó hợp khuôn JSON Schema, không cần ở cỡ này; JSONL — không có phần đầu tự mô tả một tệp; ghi từng bước vật lý — cần hook vào vòng bước của con 1; pickle — không an toàn và không kiểm được hợp khuôn.
- **Dung sai số học**: `float` Python tuần tự hoá bằng `repr` nên đọc lại **đúng từng bit** (không mất độ chính xác), nên NFR-REPRO-001 (≤ 1×10⁻⁶) kiểm được trên tệp.

<a id="q5-bo-lap-nhip-thoi-gian-thuc-fr-006-nfr-perf-001"></a>
## Q5. Bộ lập nhịp thời gian thực (FR-006, NFR-PERF-001)

- **Quyết định**: `Pacer` nhận một **đồng hồ tiêm vào** (`clock()` trả giây đơn điệu, `sleep(s)`), mặc định `time.perf_counter`/`time.sleep`; thời điểm mục tiêu của khung hiển thị `i` là `t0 + (i · Δ_hiển_thị) / speed`; nếu trễ thì không ngủ và đếm khung trễ (không bỏ khung); cuối phiên trả `PlaybackStats{wall_s, sim_s, ratio, frames_late, max_late_ms}`. Nhịp hiển thị cấu hình được (`display_hz`, khởi đầu 60). Test dùng đồng hồ giả (tiến theo `sleep`), nên NFR-PERF-001 đo được tất định, không phụ thuộc máy.
- **Căn cứ (ĐÃ ĐO) về độ ngắn của episode**: theo `002-elbow-muscle-env/research.md`, khuỷu đi từ 0 tới ≈ 2,0 rad trong **4 hành động ≈ 0,16 s mô phỏng**; tối đa 100 hành động ≈ 4 s. Phát ở 1,0× một episode tới mục tiêu trong 0,16–0,5 s là **chớp mắt** — mắt người không "kiểm" được. Do đó spec thêm **hệ số tốc độ** (mặc định 1,0 giữ đúng "thời gian thực") và **lặp**; lệnh in thời lượng mô phỏng và gợi ý hệ số (ví dụ `--speed 0.1`) khi episode ngắn hơn 1 s. Khi `speed < 1`, tỷ lệ thời gian được tính theo thời gian mô phỏng *đã chia tốc độ* (NFR-PERF-001 áp ở speed = 1,0).
- **Chi phí khung (ĐÃ ĐO)**: ≈ 7–8 ms/vòng đồng bộ viewer (Q1) ≪ 16,7 ms của 60 Hz ⇒ ngân sách khung đủ trên máy này; trên máy yếu hơn, `frames_late > 0` sẽ lộ ra và được báo (FR-006), không im lặng.
- **Phương án đã loại**: ngủ cố định 1/60 s mỗi khung — trôi nhịp, không đo được; phát bằng cách chạy lại vật lý theo thời gian thật — đổi "phát lại" thành "mô phỏng lại", sai khi mô hình đã đổi (INV-001).

<a id="q6-lay-trang-thai-tu-moi-truong-de-ghi-episode-fr-007-fr-003-inv-002"></a>
## Q6. Lấy trạng thái từ môi trường để ghi episode (FR-007, FR-003, INV-002)

- **Vấn đề**: để ghi `qpos`, `qvel`, `act`, đầu mút tay mỗi hành động, bộ ghi cần đọc trạng thái mô phỏng. Hợp đồng đã công bố của con 1 (`002/contracts/python-api.md`) **không** có hàm công khai cho việc này; `info` của `step` có `distance_m`, `ctrl_requested`, `ctrl_effective`, `reward_*`, nhưng không có `qpos`/`act`/đầu mút. `002/research.md` Q5 chỉ nói `HeadlessSimulator` của 001 cho đọc `model`/`data`.
- **Quyết định**: đề xuất một **accessor đọc-chỉ** `ElbowReachEnv.read_state() -> StateSnapshot` trong `single_agent.py` của con 1 (trả bản sao `qpos`, `qvel`, `act`, `fingertip_position_m`, `target_position_m`, `time_s`; không cho ghi) — một task nhỏ thuộc chủ sở hữu (002), đứng sau task `single_agent.py` của 002 và TRƯỚC `recorder` của 005. Cùng mẫu với accessor `target_index` mà 004 đã xin (D-2): **chung một tệp, một chủ** — nếu 004 đã giao, 005 chỉ phụ thuộc, không làm trùng. `recorder` KHÔNG truy cập thuộc tính riêng (`_data`) và KHÔNG ghi vào `MjData` của môi trường (INV-002).
- **CHƯA KIỂM / phụ thuộc**: 002 chưa có mã. Nếu khi triển khai 002 đã có accessor tương đương (tên khác) thì 005 dùng tên đó; lệch ⇒ sửa ở 002, 005 không sao chép logic.
- **Phương án đã loại**: dựng lại `qpos`/`act` từ `obs` (obs có qpos chuẩn hoá, `act` ở chỉ số 2–7, đầu mút ở 8–10) — phải chép phép chuẩn hoá của con 1 (hằng số thứ hai, dễ trôi) và vẫn thiếu `qvel` chưa kẹp; chạy một `MjData` thứ hai trong con 4 để mô phỏng lại — hai nguồn sự thật cho vật lý.

<a id="q7-kiem-lech-mo-hinh-khi-phat-lai-fr-012-inv-001"></a>
## Q7. Kiểm lệch mô hình khi phát lại (FR-012, INV-001)

- **Quyết định**: `check_model(episode, model_info)` so (1) `episode.model.sha256` với SHA-256 XML của mô hình hiện tại (lấy từ `load_muscle_model` của 001, cùng nguồn mà `ElbowReachEnv.model_record()` dùng), (2) `nq`, `nv`, số cơ và `muscle_names` (thứ tự). Kết quả `ModelCheck{match, compatible, episode_sha256, current_sha256, reasons[]}`: `match=False` và `compatible=True` ⇒ dừng mặc định, chỉ tiếp tục khi có cờ `--allow-model-mismatch`; `compatible=False` ⇒ luôn dừng.
- **Căn cứ**: phát lại là đặt trực tiếp `qpos/act` lên `MjData` rồi `mj_forward`; mô hình khác (khớp, cơ, hình học) cho hình sai mà **không có lỗi nào** — đúng loại "sai ngầm" của AC-4. Cấu trúc (số khớp, số cơ, tên) quyết định việc đặt trạng thái có an toàn về chỉ số hay không.
- **Phương án đã loại**: chỉ cảnh báo rồi vẫn phát — trái "không phát lại sai ngầm"; coi mọi lệch là lỗi cứng không có cờ — không cho kiểm lại một episode cũ sau khi chủ ý đổi XML nhỏ (ví dụ màu), trong khi cờ tường minh + cảnh báo liên tục vẫn an toàn.

<a id="q8-che-do-khong-man-hinh-kiem-du-lieu-thay-vi-xuat-khung-fr-010-kq-3"></a>
## Q8. Chế độ không màn hình: kiểm dữ liệu thay vì xuất khung (FR-010, KQ-3)

- **Quyết định**: `--headless` = (a) với `--episode`: đọc + kiểm + `summarize_episode` ⇒ in JSON theo `contracts/replay-summary.schema.json`; (b) với `--checkpoint`: chạy một episode không viewer, lưu nếu có `--save-episode`, in cùng loại tóm tắt. Không nhập `glfw`, không gọi `mujoco.viewer` (kiểm bằng `test_headless_never_imports_viewer`).
- **Căn cứ (ĐÃ ĐO)** về xuất khung ngoài màn hình bằng `mujoco.Renderer`: với `MUJOCO_GL=glfw` và `DISPLAY=:0` dựng được ảnh (120×160×3); với `MUJOCO_GL=egl` lỗi `EGLError` ngay khi khởi tạo; với `MUJOCO_GL=osmesa` lỗi `AttributeError: 'NoneType' object has no attribute 'glGetError'` (thiếu thư viện OSMesa). Tức trên máy phát triển, dựng hình **không** có màn hình hiện **không khả dụng**; chỉ `glfw` chạy và nó cần màn hình. Hứa "xuất khung khi không có màn hình" sẽ là hứa điều không kiểm được (master plan XII).
- **Phương án đã loại**: xuất PNG khung bằng EGL/OSMesa — không khởi tạo được ở máy đo; xuất khung bằng GLFW offscreen — vẫn cần `DISPLAY` nên không giải quyết "không có màn hình"; dùng `Xvfb` — **không có** trên máy đo (`xvfb-run`, `Xvfb` không tìm thấy) và thêm phụ thuộc hệ điều hành.
- **Hệ quả cho kiểm thử**: tất cả AC chạy được tự động ở môi trường không màn hình trừ phần "viewer thật mở và phát"; phần đó có một test rẽ nhánh theo `display_available()` (Q9), không dùng cơ chế bỏ qua test.

<a id="q9-cach-kiem-thu-phan-viewer-ma-khong-bo-qua-test-fr-019-hien-chuong-ii"></a>
## Q9. Cách kiểm thử phần viewer mà không bỏ qua test (FR-019, hiến chương II)

- **Quyết định**: tách `play(episode, cfg, sink)` khỏi viewer qua giao diện `FrameSink` (`show(frame, hud)` · `is_open()` · `close()`): `ViewerSink` bọc MuJoCo Viewer (mỏng, Q1); bộ test dùng `RecordingSink` ghi lại dãy khung và nội dung HUD để khẳng định **thứ tự khung, mục tiêu, 6 giá trị activation bằng đúng dữ liệu episode, cảnh báo lệch mô hình** — không mock vật lý, chỉ thay *màn hình*. Phần "viewer thật" là **một test rẽ nhánh theo môi trường**: nếu `display_available()` thì chạy `scripts/replay.py --episode <path>` thật với cấu hình `viewer.hold_after_end_s: 0` (cửa sổ tự đóng sau khi phát) và khẳng định mã thoát 0 + tóm tắt `frames_shown == số khung`; nếu không có màn hình thì khẳng định đường AC-3 (mã khác 0 ≤ 5 s, thông báo). Cả hai nhánh là khẳng định thật, không `skip`/`xfail` (hiến chương II).
- **CHƯA KIỂM**: nhánh "có màn hình" trong CI (máy CI không màn hình sẽ chỉ chạy nhánh AC-3). Bằng chứng cho nhánh này đến từ lần chạy trên máy phát triển có màn hình, lưu ở `evidence/` do cổng sinh (hiến chương I).

<a id="q10-phu-thuoc-cau-hinh-ranh-gioi-voi-003-fr-015-fr-017"></a>
## Q10. Phụ thuộc, cấu hình, ranh giới với 003 (FR-015, FR-017)

- **Phụ thuộc**: **không thêm gói nào, không thêm extra**. `mujoco.viewer` và `glfw` đi kèm `mujoco` (ĐÃ ĐO: `import mujoco.viewer` chạy, `glfw` có sẵn); đường `--episode` chỉ cần `numpy` + `pyyaml` (+ `mujoco` để nạp mô hình khi có viewer/kiểm hash); đường `--checkpoint` cần extra `rl` của 003 (`torch`) — `import` lười trong `recorder`, nên `--episode`/`--headless` trên episode chạy khi chưa cài `torch` (`test_episode_path_does_not_import_torch`). `pyproject.toml` không đổi ⇒ không có tệp chung cần task chủ riêng (khác 003/004).
- **Cấu hình**: `src/mma_ai/visualization/replay.yaml` (cấu hình mặc định đóng gói; `--config PATH` để dùng tệp khác — xem plan.md, "Quyết định ở bước tasks") (khuôn `contracts/replay-config.schema.json`): `playback.{speed, loop, display_hz, hold_after_end_s}`, `demo.{split, target_index, seed}`, `hud.{decimals, bar_width}`, `logs`. Không có cờ nào ghi đè hành vi an toàn (kiểm hash, từ chối ghi đè) ngoài `--allow-model-mismatch`.
- **Ranh giới với 003**: `003-ppo-train-repro` đã kế hoạch `monitoring/viewer3d.py` (`View3D`, cửa sổ 3D đọc `latest.json` lúc đang train, `--view3d` của `train.py`/`watch_train.py`) — đó là giao diện quan sát **training** của con 2 (Q-0001) và **không** là replay. Con 4 không import, không sửa nó. Hai nơi cùng cần vẽ mục tiêu + bảng activation; vì con 4 `blocked_by` con 2 nên con 2 không thể phụ thuộc mô-đun của con 4 ⇒ **đề xuất riêng (không làm trong 005)**: sau khi 005 xong, con 2 có thể chuyển phần HUD dùng chung sang `visualization/hud.py` của 005; ghi ở rủi ro.

<a id="q11-con-mo-chuyen-thanh-viec-trien-khai-bat-buoc-co-ghi-ket-qua"></a>
## Q11. Còn mở (chuyển thành việc triển khai bắt buộc có ghi kết quả)

1. 001–003 chưa có mã (giao diện theo hợp đồng đã công bố — CHƯA KIỂM).
2. `ElbowReachEnv.read_state()` và `options["target_index"]` của 002 (Q6) — task đọc-chỉ ở chủ sở hữu.
3. Mã thoát khi thoát tiến trình có viewer (Q3) — nguyên nhân gốc và hành vi trên WSLg/RTX 5060 CHƯA KIỂM.
4. Viewer thật chưa được chạy tự động trong CI không màn hình (Q9).
5. WSL2/WSLg: chưa có máy để đo (spec Clarifications).
6. Ngưỡng khung/giây tuyệt đối: không đặt (spec); `frames_late`/`ratio` do máy đo trong phiên.

Không còn `[NEEDS CLARIFICATION]`.
