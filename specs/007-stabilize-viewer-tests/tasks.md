---
id: "TASKS-007"
title: "Sửa gốc 2 test hiển thị/tiến trình làm đỏ cổng tests — Nhiệm vụ (Tasks)"
doc_type: tasks
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "007-stabilize-viewer-tests"
version: "1.1.0"
---

# Nhiệm vụ: Sửa gốc 2 test hiển thị/tiến trình làm đỏ cổng tests

- [Đầu vào](#dau-vao)
- [Quy ước task](#quy-uoc-task)
  - [Phụ thuộc chéo feature](#phu-thuoc-cheo-feature)
- [User story US2 — tiến trình View3D tách riêng không chập chờn (P1)](#user-story-us2-tien-trinh-view3d-tach-rieng-khong-chap-chon-p1)
- [User story US1 và US3 — viewer thật tất định, nguyên nhân được đo (P1)](#user-story-us1-va-us3-viewer-that-tat-dinh-nguyen-nhan-duoc-do-p1)
- [QA và review độc lập](#qa-va-review-doc-lap)
  - [Quyết định về vai `challenger`](#quyet-dinh-ve-vai-challenger)
- [Dependencies và wave](#dependencies-va-wave)
- [Điều kiện hoàn thành](#dieu-kien-hoan-thanh)
- [Phase 4: Convergence](#phase-4-convergence)

> Đích: `specs/007-stabilize-viewer-tests/tasks.md`. Sinh từ `spec.md` + `plan.md` + `research.md` + `data-model.md` HIỆN TẠI (viết lại hoàn toàn ở lượt 2026-10-12; spec 1.1.0, plan 1.1.0). Feature không có `contracts/` (không có giao diện bên ngoài) và không có màn hình ⇒ không có mã `API-*`, `UI-*`; không có kế hoạch hạ tầng ⇒ không có task `platform`.

<a id="dau-vao"></a>
## Đầu vào

- `spec.md` (FR-001…FR-008 · NFR-REL-001 · NFR-PERF-001 · NFR-QUAL-001 · INV-001…003 · AC-1…AC-5 của 007), `plan.md`, `research.md` (Q1 nguyên nhân T-B, Q2 giả thuyết H1…H5 và cây quyết định của T-A), `data-model.md`, `quickstart.md`.
- Mã AC-1, AC-2, FR-011, FR-014 **của 005** luôn viết kèm "của 005" / "005 AC-n" để không lẫn với AC-n của feature này (spec, Clarifications).
- Trạng thái nguyên nhân (theo mã đã gộp và verdict T704/T711): T-B (`T701`) — cuộc đua giữa "tạo đối tượng" và `.start()`, nguyên nhân ở kiểm thử, đã sửa; T-A (`T702`) — đo treo 2/5 lần chạy lệnh trực tiếp, nguyên nhân gốc ở `ViewerSink.show` (`src/mma_ai/visualization/viewer.py`, `set_texts` gọi trong khối `lock_ctx`), nên theo AC-5 phần `src/` thuộc task sửa gốc riêng `T706`, không thuộc task sửa kiểm thử. Môi trường cổng tests có hay không có cửa sổ GL dùng được vẫn **CHƯA KIỂM**.

<a id="quy-uoc-task"></a>
## Quy ước task

- **Dải mã `T701`…**: id task duy nhất toàn dự án; 007 dùng dải `T7xx` để không va với `T2xx`…`T5xx` của 001–005 và dải của 006. Mô tả task KHÔNG viết id task của feature khác; phụ thuộc chéo nằm ở cột `depends_on`.
- **Vùng ghi của feature (FR-007, INV-003)**: hai tệp integration `tests/integration/test_replay_viewer_real.py` và `tests/integration/test_viewer3d_train.py`, MỘT tệp E2E mới `tests/e2e/test_007_viewer_entrypoint.py` do `T705` (qa) thêm; `src/` KHÔNG đổi, TRỪ `src/mma_ai/visualization/viewer.py` (kèm `tests/unit/test_viewer.py`) và CHỈ qua task sửa gốc riêng `T706` khi đo chứng minh nguyên nhân ở đó (AC-5). Mỗi tệp một task chủ. Task hội tụ `T710` chỉ đổi chuỗi docstring ở test E2E của 003 (xem mục Phase 4). Id `T708` (docstring integration) và `T709` (khung gói) đã RÚT, không tái dùng: `003/AC-5` đã có sẵn 4 lần trong `tests/integration/test_train_stage.py` và bốn tệp khung gói đã có, giống hệt, trên `master` ⇒ hai task không tạo diff (`NO_OUTPUT_CHANGES`).
- Tự chốt: task `T705` sinh `tests/e2e/**` chạy trên entrypoint thật — luật lint NO_E2E bắt buộc; tệp mới chỉ là kiểm thử, không đụng `src/` (INV-003). Task `T706` là ngoại lệ `src/` duy nhất, đã được spec 1.1.0 cho phép theo AC-5.
- **Không `skip`/`skipif`/`xfail`/`importorskip` mới**, không giảm số kiểm thử, không nới khẳng định nghiệm thu (FR-004, FR-006, INV-001); dấu `pytest.mark.display` đã có trên T-A giữ nguyên.
- **Đo trước, sửa sau** (hiến chương II): task ghi mục `Nguyên nhân gốc` (kèm lệnh, số lần chạy, kết quả, thời gian, đầu ra lỗi, môi trường đo — có/không cửa sổ GL dùng được) và `BÀI HỌC` vào báo cáo `.ai/runs/*/reports/builder-*.md` TRƯỚC khi đổi tệp kiểm thử.
- **Mỗi lượt chạy test chỉ 1–2 lần** (giới hạn thời gian của yêu cầu); số lần còn lại để đủ ngưỡng NFR-REL-001 cộng dồn qua các lượt vào bằng chứng, không dồn vào một lượt.
- **Lệnh chung** (trong worktree của task, môi trường có `mujoco`, `myo-sim`, và `torch` nếu muốn chạy phần huấn luyện thật của T-B): `uv run --isolated --with pytest pytest -q -p no:cacheprovider <nodeid>`; lint `uv run --isolated --with ruff ruff check <hai tệp>`; kiểu `uv run --isolated --with mypy mypy --strict <hai tệp>`.
- **Nếu nguyên nhân nằm ở `src/`** (H1/H2 của research.md Q2): task sửa kiểm thử DỪNG, KHÔNG đổi `src/`, báo tệp, hàm, bằng chứng đo và đề xuất trong báo cáo (AC-5); phần độ cứng chẩn đoán của FR-002 vẫn được giữ; việc sửa `src/` chỉ qua task sửa gốc riêng có kiểm thử đỏ-trước-sửa (`T706`).

<a id="phu-thuoc-cheo-feature"></a>
### Phụ thuộc chéo feature

Hai tệp kiểm thử là sản phẩm của task cũ ở 003 và 005 (tệp tồn tại nhờ chúng, đã đóng). Cột `depends_on` khai các task chủ đó để task 007 đứng SAU việc sinh tệp, đúng quy tắc "một chủ một tệp, tuần tự":

- `tests/integration/test_viewer3d_train.py` — task chủ cũ `T333` (003, US5) ⇒ `T701` khai `T333`;
- `tests/integration/test_replay_viewer_real.py` — task chủ cũ `T519` (005, US1) ⇒ `T702` khai `T519`.

Không có hành vi sản phẩm nào đổi (chỉ sửa kiểm thử) nên không có test của task trước bị làm sai bởi bản sửa này; không cần task "cập nhật test cũ" nào khác.

<a id="user-story-us2-tien-trinh-view3d-tach-rieng-khong-chap-chon-p1"></a>
## User story US2 — tiến trình View3D tách riêng không chập chờn (P1)

**Mục tiêu**: `test_view3d_process_separate` chờ tiến trình View3D thực sự có PID (hạn mức hữu hạn 5 s) rồi mới khẳng định; xanh 5/5 lần, kể cả khi có tải CPU nền (AC-2, NFR-REL-001). Nguyên nhân đã xác định từ mã (research.md Q1) là cuộc đua giữa "tạo đối tượng" và `.start()`; task vẫn phải **tái hiện đỏ** trước khi sửa.

**Kiểm thử độc lập**: chạy riêng nodeid nhiều lần, một lượt kèm tải nền (số tiến trình bận ≥ số lõi logic).

- [x] T701 [US2] Sửa chờ tiến trình View3D khởi chạy có hạn mức — tests/integration/test_viewer3d_train.py

<a id="user-story-us1-va-us3-viewer-that-tat-dinh-nguyen-nhan-duoc-do-p1"></a>
## User story US1 và US3 — viewer thật tất định, nguyên nhân được đo (P1)

**Mục tiêu**: `test_real_viewer_plays_or_reports_no_display` chọn nhánh theo `display_available()` và kết thúc đúng hạn ở cả hai nhánh, hoặc — nếu đo cho thấy gốc ở `src/` — kiểm thử còn đỏ CÓ chẩn đoán và báo cáo nêu nguyên nhân (AC-1, AC-3, AC-5).

**Kiểm thử độc lập**: chạy riêng nodeid (có và không `-n auto`); nhánh không màn hình cưỡng bức `test_real_viewer_forced_no_display_reports_code_7` vẫn xanh và không đổi.

- [x] T702 [US1] [US3] Đo nguyên nhân quá hạn của viewer thật; sửa hạn mức/độ cứng chẩn đoán hoặc dừng-và-báo — tests/integration/test_replay_viewer_real.py

<a id="qa-va-review-doc-lap"></a>
## QA và review độc lập

- [x] T703 QA: chạy lặp độc lập hai nodeid theo NFR-REL-001 (5/5 mỗi kiểm thử; T-B thêm 5/5 có tải nền; một lượt cả hai tệp với `-n auto`), đo `--durations`, ghi bằng chứng cộng dồn — .ai/runs/*/reports/qa-007-reliability.md
- [x] T705 QA: kịch bản đầu-cuối (end-to-end, E2E) chạy trên entrypoint thật của viewer và theo dõi, ánh xạ AC-1/AC-2/AC-3 — tests/e2e/test_007_viewer_entrypoint.py
- [x] T704 Reviewer: đối chiếu diff và bằng chứng cổng với AC-1…AC-5, INV-001…003, NFR, ghi verdict — evidence/reviews/T704.verdict

<a id="quyet-dinh-ve-vai-challenger"></a>
### Quyết định về vai `challenger`

**KHÔNG DÙNG** vai `challenger`. Ba bất biến `INV-001…003` của spec là bất biến về **quy trình sửa kiểm thử** (không giảm số kiểm thử/độ chặt khẳng định, kiểm thử độc lập thứ tự và không để tiến trình mồ côi, vùng ghi đúng hai tệp), không phải bất biến của hàm nhận đầu vào người dùng nên không có vector/fuzz nào "đánh sập" được; chúng được kiểm tất định bằng quét `skip`/`xfail`/`importorskip`, `pytest --collect-only`, so diff với `outputs` và chạy lặp — việc của `T703` và `T704`. Dùng challenger chỉ thêm một lượt mà không thêm bằng chứng, và đổi cổng review thành nhất trí hai vai. Quyết định cũng được ghi ở `plan.md`. Lượt 2026-10-12 rà lại: hai task hội tụ mới (`T706` sửa `viewer.py`, `T707` sửa spec) không thêm bất biến nào, nên quyết định giữ nguyên — `T706` có ca thử đơn vị đỏ-trước-sửa của chính nó, `T711` là bằng chứng độc lập.

<a id="dependencies-va-wave"></a>
## Dependencies và wave

- Không có Wave 0: khung gói (`pyproject.toml`, `conftest.py`, `src/mma_ai/__init__.py`, `tests/unit/test_smoke_mma_ai.py`) đã có sẵn trên `master` nên không cần task dựng khung (id `T709` đã rút).
- Wave 1 (song song, độc lập — hai tệp, hai nguyên nhân): `T701`, `T702`.
- Wave 2: `T703`, `T705` (song song). Wave 3: `T704`.
- Hội tụ: `T706` (sau `T702`, `T707`), `T707` (sau `T704`), `T710` (sau `T337` của 003), cuối cùng `T711` (reviewer, phụ thuộc bắc cầu mọi task hội tụ).
- Không có task đổi hành vi mà test của feature trước đang khẳng định (`T706` chỉ đưa `set_texts`/`clear_texts` ra khỏi khối khoá, giữ nguyên hành vi HUD của 005) ⇒ không cần task "cập nhật test cũ"; ca thử hồi quy của `T706` nằm cùng task. Kiểm thử E2E (`T705`) viện dẫn lệnh thật thay cho bảng chuyển màn vì feature không có giao diện.

| id | mô tả | outputs | depends_on | role | độ khó |
|---|---|---|---|---|---|
| T701 | Sửa `test_view3d_process_separate` (T-B, US2). Bước 1 — đo và tái hiện đỏ: chạy riêng nodeid nhiều lần (kể cả khi có tải CPU nền) với bản gốc, ghi tỷ lệ đỏ; chốt `Nguyên nhân gốc` (giả thuyết ở research Q1: hàm tạo tiến trình thay thế đưa đối tượng vào danh sách ngay khi tạo, `.start()` do `mma_ai.monitoring.cli` gọi sau ở luồng khác; vòng chờ chỉ đợi "danh sách không rỗng" rồi kiểm `pid` ⇒ `pid is None` khi máy bận) vào báo cáo trước khi sửa. Bước 2 — sửa: thêm trợ giúp cục bộ `_wait_until_started(proc, timeout_s)` poll ngắn tới khi `proc.pid is not None`, trả sớm khi `proc.exitcode is not None` và báo riêng "đã thoát sớm" kèm mã thoát, hết hạn thì `pytest.fail` tiếng Việt "không khởi chạy được trong hạn mức"; hạn mức là hằng số đặt tên, hữu hạn (5 s), dùng thay cho kiểm `pid` ngay; giữ nguyên danh sách theo dõi và mọi khẳng định: đúng 1 tiến trình View3D, PID khác PID chính, đang sống, `terminate()` giữ nguyên `ui.json`, dừng sạch bằng `stop_event`, phần huấn luyện thật với `--view3d` mã 0 và có `latest.json`; không `skip`/`xfail`, không giảm số kiểm thử, không đổi `src/`. Phần tiến trình tách riêng ≤ 10 s (NFR-PERF-001). Giữ nguyên khẳng định tách tiến trình của 003 (FR-022 của 003, INV-005 của 003). Hiện thực FR-003 · FR-004 · FR-005 · FR-006 · FR-007 · FR-008 · INV-001 · INV-002 · INV-003 · NFR-PERF-001 · NFR-QUAL-001 · NFR-REL-001 · AC-2 · AC-3 · AC-4. Kiểm chứng: `uv run --isolated --with pytest pytest -q -p no:cacheprovider tests/integration/test_viewer3d_train.py::test_view3d_process_separate` (1–2 lần mỗi lượt), cộng `ruff check` và `mypy --strict` trên tệp. | tests/integration/test_viewer3d_train.py | T333 | builder | vừa |
| T702 | Sửa/chẩn đoán `test_real_viewer_plays_or_reports_no_display` (T-A, US1/US3). Bước 1 — ĐO, không đoán (research Q2): chạy riêng lệnh con nhánh có màn hình `python -m mma_ai.visualization.cli --episode … --config …` với `python -X faulthandler`, hạn mức 20 s, lấy ngăn xếp mọi luồng khi quá hạn, ghi thời gian từng giai đoạn và môi trường (`DISPLAY`, `WAYLAND_DISPLAY`, `MUJOCO_GL`, kết quả `display_available()`); chạy lặp một mình, dưới tải CPU nền và hai tiến trình viewer cùng lúc; kết luận H1…H5 vào báo cáo (`Nguyên nhân gốc`, `BÀI HỌC`), môi trường chưa đo ghi "CHƯA KIỂM". Bước 2 — theo cây quyết định: (a) gốc ở `src/` (H1 viewer treo lúc mở/đóng; H2 `display_available()` báo "có" mà không có cửa sổ GL dùng được, khoảng trống so với 005 FR-011/FR-014) ⇒ DỪNG sửa nhánh đó, không đổi `src/`, báo tệp, hàm, ngăn xếp/số đo, đề xuất (AC-5), kiểm thử ghi "còn đỏ vì nguyên nhân ở `src/`"; (b) gốc ở kiểm thử (H3 chậm dưới tải ⇒ hiệu chỉnh hạn mức theo p95 đo được, nêu căn cứ trong chú thích; H4 tranh chấp cửa sổ ⇒ khoá tệp nhẹ dưới thư mục tạm; H5 trạng thái GLFW của tiến trình pytest ⇒ chọn nhánh bằng tiến trình con ngắn có hạn mức). Trong mọi trường hợp thêm độ cứng chẩn đoán FR-002: trợ giúp cục bộ `_run_cli_bounded(cmd, timeout_s, env=None)` chạy `Popen(..., start_new_session=True)` + `communicate(timeout=…)`, quá hạn thì giết cả nhóm tiến trình, lấy đầu ra còn lại và `pytest.fail` tiếng Việt nêu lệnh, hạn mức, stdout/stderr (thay `TimeoutExpired` trần), dùng cho cả hai nhánh. Chọn nhánh vẫn bằng `display_available()` (không dò môi trường riêng). Giữ nguyên khẳng định: có màn hình thoát mã 0 trong hạn khai tường minh ≤ 25 s với đủ các mục "Tóm tắt phiên phát lại:", "Thời lượng mô phỏng=", "Thời gian thực=", "Tỷ lệ tốc độ=", "Số khung trễ="; không màn hình mã 7 trong ≤ 5 s kèm gợi ý `--headless` và nguyên nhân hiển thị tiếng Việt; `test_real_viewer_forced_no_display_reports_code_7` không đổi; không `skip`/`xfail`, không giảm số kiểm thử. Hiện thực FR-001 · FR-002 · FR-004 · FR-005 · FR-006 · FR-007 · FR-008 · INV-001 · INV-002 · INV-003 · NFR-PERF-001 · NFR-QUAL-001 · NFR-REL-001 · AC-1 · AC-3 · AC-4 · AC-5. Kiểm chứng: `uv run --isolated --with pytest pytest -q -p no:cacheprovider -m display tests/integration/test_replay_viewer_real.py` (1–2 lần mỗi lượt), cộng `ruff check` và `mypy --strict` trên tệp. | tests/integration/test_replay_viewer_real.py | T519 | builder | khó |
| T703 | QA độc lập: chạy lặp từng nodeid `tests/integration/test_viewer3d_train.py::test_view3d_process_separate` và `tests/integration/test_replay_viewer_real.py::test_real_viewer_plays_or_reports_no_display` riêng từng cái 5/5 lần liên tiếp (NFR-REL-001), thêm 5/5 lần cho T-B có tải CPU nền (số tiến trình bận ≥ số lõi logic), một lượt cả hai tệp với `-n auto` như cổng; ghi `--durations=5` (NFR-PERF-001), môi trường đo (có/không cửa sổ GL dùng được, `display_available()`), 0 lần quá hạn không có chẩn đoán; quét `skip`/`skipif`/`xfail`/`importorskip` mới trong hai tệp và `pytest --collect-only -q` số kiểm thử không giảm (INV-001); `git diff --name-only` chỉ gồm hai tệp kiểm thử cộng tệp E2E do T705 thêm mới, không có tệp trong `src/` (INV-003); không để tiến trình mồ côi sau khi chạy (INV-002). Nếu T702 kết luận gốc ở `src/` thì ghi T-A "còn đỏ vì nguyên nhân ở `src/`" kèm số đo, KHÔNG tuyên bố xanh. Mỗi lượt chạy 1–2 lần, cộng dồn bằng chứng. Hiện thực NFR-REL-001 · NFR-PERF-001 · INV-001 · INV-002 · INV-003 · AC-1 · AC-2 · AC-3 · AC-4 · AC-5 · FR-004 · FR-006. Kiểm chứng: báo cáo có số lần chạy, kết quả và thời gian của từng kiểm thử. | .ai/runs/*/reports/qa-007-reliability.md | T701; T702 | qa | vừa |
| T705 | QA E2E: viết `tests/e2e/test_007_viewer_entrypoint.py` chạy trên ENTRYPOINT THẬT, không mock, không import hàm nội bộ thay cho lệnh: (1) lệnh `python -m mma_ai.visualization.cli` ở nhánh cưỡng bức không màn hình (xoá `DISPLAY` và `WAYLAND_DISPLAY`) thoát mã 7 trong ≤ 5 s kèm gợi ý `--headless` bằng tiếng Việt (AC-1, AC-3); (2) cùng lệnh nhánh có màn hình chỉ chạy khi `display_available()` đúng, thoát mã 0 trong hạn ≤ 25 s với đủ mục tóm tắt phiên phát lại (AC-1, AC-3); (3) `python -m mma_ai.monitoring.cli` với `--view3d` khởi chạy tiến trình View3D riêng có PID khác PID chính, dừng sạch bằng tín hiệu và không để tiến trình mồ côi (AC-2). Mọi tiến trình con chạy có hạn mức hữu hạn, quá hạn thì giết cả nhóm tiến trình và `pytest.fail` tiếng Việt kèm đầu ra. Không `skip`/`xfail` mới; feature không có màn hình giao diện nên không có kịch bản chụp ảnh. Chỉ thêm tệp kiểm thử mới, `src/` KHÔNG đổi (INV-003). Hiện thực AC-1 · AC-2 · AC-3 · FR-001 · FR-003 · NFR-REL-001 · INV-002 · INV-003. Kiểm chứng: `uv run --isolated --with pytest pytest -q -p no:cacheprovider tests/e2e/test_007_viewer_entrypoint.py` (1–2 lần mỗi lượt), cộng `ruff check` và `mypy --strict` trên tệp. | tests/e2e/test_007_viewer_entrypoint.py | T701; T702 | qa | vừa |
| T704 | Reviewer: đối chiếu `spec.md`/`plan.md`/`tasks.md` với diff thật và bằng chứng cổng (`evidence/gates/*`) cùng báo cáo T703, ghi verdict APPROVE hoặc REQUEST_CHANGES nêu AC-1…AC-5, INV-001…003, NFR-REL-001/PERF-001/QUAL-001 đã được chứng minh bằng lần chạy ngoài hay chưa; xác nhận mục `Nguyên nhân gốc` khớp diff (không phải né triệu chứng), không `skip`/`xfail` mới, khẳng định nghiệm thu của 005 (AC-1, AC-2, FR-001/004/005/011/014) và tách tiến trình của 003 còn nguyên hoặc chặt hơn; nếu nguyên nhân ở `src/` thì xác nhận báo cáo nêu tệp, hàm, bằng chứng, đề xuất và `src/` không bị đổi; không tin lời khai của báo cáo task. Kiểm thêm kịch bản E2E của T705 chạy được trên entrypoint thật và `src/` không đổi. Hiện thực AC-1 · AC-2 · AC-3 · AC-4 · AC-5 · INV-001 · INV-002 · INV-003 · NFR-REL-001 · NFR-PERF-001 · NFR-QUAL-001 · FR-005 · FR-007. | evidence/reviews/T704.verdict | T701; T702; T703; T705 | reviewer | vừa |
| T706 | Sửa gốc ở `src/` làm cổng `tests` đỏ `EXIT_NONZERO` (cổng ghi FLAKY ở `test_real_viewer_plays_or_reports_no_display`: lệnh con `python -m mma_ai.visualization.cli` bị SIGKILL sau 25 s, stdout rỗng; T702 đo treo 2/5 lần chạy CLI trực tiếp; verdict T704 F-001 nêu chưa task nào nhận). Nguyên nhân gốc: `ViewerSink.show` gọi `self._handle.set_texts(...)` / `clear_texts()` ngay BÊN TRONG khối `with lock_ctx:` (viewer.py dòng 149–184, `set_texts` ở dòng 179). Sửa: giữ trong khối khoá chỉ phần ghi `qpos`/`act`/`mj_forward`/`user_scn`; đưa `set_texts`/`clear_texts` ra ngoài `lock_ctx` (trước `sync`), không đổi hành vi HUD (FR-005 của 005) và không đổi chữ ký `ViewerSink`. Thêm ca thử vào `tests/unit/test_viewer.py` dùng handle giả có `lock()` không tái nhập và cờ "đang giữ khoá" khẳng định `set_texts` được gọi khi KHÔNG giữ khoá (đỏ trước khi sửa). Sau sửa chạy `-n auto` hai tệp `tests/integration/test_replay_viewer_real.py` và `tests/integration/test_viewer3d_train.py` ≥ 5 lượt ghi kết quả vào báo cáo; không `skip`/`xfail`, không giảm số kiểm thử. Hiện thực AC-1 · AC-5 · NFR-REL-001 · FR-001 (007) và FR-005 · INV-002 (005). Kiểm chứng: `uv run --isolated --with pytest pytest -q -p no:cacheprovider tests/unit/test_viewer.py tests/integration/test_replay_viewer_real.py`, cộng `ruff check` và `mypy --strict`. | src/mma_ai/visualization/viewer.py; tests/unit/test_viewer.py | T512; T702; T707 | builder | vừa |
| T707 | SỬA ĐẶC TẢ: `spec.md` INV-003/FR-007 khai vùng sửa là "ĐÚNG hai tệp kiểm thử, 0 thay đổi `src/`", nhưng mã đã gộp có thêm `tests/e2e/test_007_viewer_entrypoint.py` (T705) và báo cáo QA, và nguyên nhân của T-A nằm ở `src/mma_ai/visualization/viewer.py` (AC-5; verdict T704 F-005, F-001). Sửa lại INV-003, FR-007 và mục Điều kiện hoàn thành của spec cho khớp: "hai tệp integration + một tệp e2e mới; `src/` chỉ đổi ở `src/mma_ai/visualization/viewer.py` khi đo chứng minh nguyên nhân ở đó (AC-5)"; bỏ ràng buộc "đúng hai tệp" khỏi tiêu chí `git diff --name-only`; giữ nguyên AC/FR khác. Kiểm chứng: đọc lại spec.md, không còn câu "đúng hai tệp" mâu thuẫn với T705/T706. | specs/007-stabilize-viewer-tests/spec.md | T704 | spec | dễ |
| T710 | QA: nối mã rủi ro `003/AC-5` nguyên văn vào docstring `test_ac_5_stage_not_implemented` của `tests/e2e/test_train_acceptance.py` (hiện chỉ ghi "AC-5" trần nên gate không nhận ra mã `003/AC-5`); kịch bản vẫn chạy lệnh huấn luyện thật với stage ngoài elbow, mã thoát 3, không tạo thư mục run; chỉ đổi chuỗi docstring/chú thích, KHÔNG đổi khẳng định, không `skip`/`xfail`, không giảm số kiểm thử; feature không có màn hình giao diện nên không có kịch bản chụp ảnh. Kiểm chứng: `uv run --isolated --with pytest pytest -q -p no:cacheprovider tests/e2e/test_train_acceptance.py -k "stage"` và `grep -n "003/AC-5" tests/e2e/test_train_acceptance.py` ≥ 1 kết quả. | tests/e2e/test_train_acceptance.py | T337 | qa | dễ |
| T711 | Reviewer: chấm phần mới của lượt hội tụ (sửa `src/` T706, sửa đặc tả T707, docstring `003/AC-5` T710) bằng diff thật và bằng chứng cổng; xác nhận T706 đưa `set_texts`/`clear_texts` ra khỏi khối khoá và ca thử hồi quy đỏ trước, xanh sau; T707 làm INV-003/FR-007 của spec khớp tệp E2E và ngoại lệ `viewer.py` theo AC-5; T710 chỉ đổi chuỗi docstring, không đổi khẳng định, không `skip`/`xfail`, số kiểm thử không giảm; ghi verdict APPROVE hoặc REQUEST_CHANGES, không tin lời khai báo cáo task. Hiện thực AC-1 · AC-5 · INV-001 · INV-003 · NFR-REL-001 · NFR-QUAL-001. | evidence/reviews/T711.verdict | T704; T706; T707; T710 | reviewer | vừa |

<a id="dieu-kien-hoan-thanh"></a>
## Điều kiện hoàn thành

- Mỗi kiểm thử có đúng một mục `Nguyên nhân gốc` kèm số lần chạy, kết quả đo trước/sau và môi trường đo (SC-004); môi trường chưa đo ghi "CHƯA KIỂM".
- `test_view3d_process_separate` xanh 5/5 (và 5/5 có tải nền); `test_real_viewer_plays_or_reports_no_display` xanh 5/5 **hoặc** ghi rõ "còn đỏ vì nguyên nhân ở `src/`" kèm bằng chứng và đề xuất (AC-5) — không có đường làm xanh bằng nới khẳng định, `skip`/`xfail`.
- Diff nằm trong vùng FR-007: hai tệp integration, tệp E2E mới, và (chỉ vì nguyên nhân T-A đo ở đó) `src/mma_ai/visualization/viewer.py` + `tests/unit/test_viewer.py`; 0 thay đổi ở tệp `src/` khác; số kiểm thử trong hai tệp không giảm; `ruff` và `mypy --strict` xanh.
- Trace: `docs/05-tracing/trace/007-stabilize-viewer-tests.md` — mỗi AC/FR/INV/NFR/SC có task và test mức entrypoint.
- Mọi verdict chặn merge (reviewer) đã được giải quyết.

<a id="phase-4-convergence"></a>
## Phase 4: Convergence

- [x] T706 [US1] Sửa nguyên nhân gốc ở `src/` làm cổng `tests` đỏ `EXIT_NONZERO`: đưa `set_texts`/`clear_texts` ra khỏi khối `lock_ctx` của `ViewerSink.show`, thêm ca thử hồi quy — src/mma_ai/visualization/viewer.py; tests/unit/test_viewer.py
- [x] T707 [US3] SỬA ĐẶC TẢ: chỉnh INV-003/FR-007 của spec.md cho khớp tệp e2e mới (T705) và ngoại lệ `src/mma_ai/visualization/viewer.py` theo AC-5 — specs/007-stabilize-viewer-tests/spec.md
- [ ] T710 QA: nối mã rủi ro `003/AC-5` nguyên văn vào docstring test E2E stage chưa triển khai (phần e2e) — tests/e2e/test_train_acceptance.py
- [x] T711 Reviewer: chấm phần mới của lượt hội tụ (T706…T710), phụ thuộc bắc cầu mọi task — evidence/reviews/T711.verdict

> Bỏ hai tư vấn (so chữ, sai): `specs/004-eval-vs-random-plots/quickstart.md` và `specs/005-replay-3d-muscle-demo/quickstart.md` mục `Điều kiện tiên quyết` chỉ là bước dựng môi trường (không phải kịch bản kiểm chứng), mã AC/INV nằm ở các kịch bản 1…N ngay sau; đồng thời hai tệp thuộc feature khác, ngoài vùng ghi của 007.
