---
id: "PLAN-007"
title: "Sửa gốc 2 test hiển thị/tiến trình — Kế hoạch triển khai (Implementation plan)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "007-stabilize-viewer-tests"
version: "1.1.0"
---

# Implementation Plan: Sửa gốc 2 test hiển thị/tiến trình làm đỏ cổng tests

- [Summary](#summary)
- [Technical Context](#technical-context)
- [Constitution Check](#constitution-check)
- [Phụ thuộc](#phu-thuoc)
- [Kiến trúc & tách trách nhiệm](#kien-truc-tach-trach-nhiem)
  - [Quyết định thiết kế](#quyet-dinh-thiet-ke)
- [Project Structure](#project-structure)
  - [Documentation (this feature)](#documentation-this-feature)
  - [Source Code (repository root) — chỉ phần 007 chạm tới](#source-code-repository-root-chi-phan-007-cham-toi)
- [Lệnh build / test](#lenh-build-test)
- [Truy vết yêu cầu → thiết kế](#truy-vet-yeu-cau-thiet-ke)
- [Rủi ro & việc CHƯA KIỂM](#rui-ro-viec-chua-kiem)
- [Quyết định ở bước tasks](#quyet-dinh-o-buoc-tasks)
- [Quyết định về vai `challenger`](#quyet-dinh-ve-vai-challenger)
- [Phản biện plan_lint](#phan-bien-plan-lint)
- [Complexity Tracking](#complexity-tracking)


**Branch**: `007-stabilize-viewer-tests` (tên thư mục feature; không tạo nhánh git) | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: `specs/007-stabilize-viewer-tests/spec.md` (bản hiện tại; không còn câu hỏi mở; Q-0001/Q-0002 không áp dụng — xem Clarifications của spec).

<a id="summary"></a>
## Summary

Feature sửa hai tệp kiểm thử integration (cộng một tệp e2e mới của QA) để cổng tests cho kết quả tất định; `src/` chỉ đổi ở `src/mma_ai/visualization/viewer.py` khi đo chứng minh nguyên nhân T-A nằm ở đó (spec 1.1.0, INV-003, AC-5); không thêm hành vi sản phẩm. Hai kiểm thử có hai nguyên nhân độc lập và hai hướng sửa khác nhau (chi tiết và căn cứ ở [research.md](research.md)):

- **T-B `test_view3d_process_separate` (US2, AC-2)** — nguyên nhân đã xác định được từ mã (đọc, chưa chạy): hàm tạo tiến trình thay thế của kiểm thử đưa tiến trình vào danh sách ngay khi **tạo**, còn `.start()` do `mma_ai.monitoring.cli` gọi **sau đó** ở luồng khác; vòng chờ của kiểm thử chỉ đợi "danh sách không rỗng" rồi kiểm `pid` ngay ⇒ khi luồng chưa kịp `.start()` (máy bận) thì `pid is None`. Sửa: chờ có hạn mức cho tới khi tiến trình **thực sự có PID** (hoặc đã thoát sớm), rồi mới khẳng định. Lỗi nằm ở kiểm thử, không ở `src/`.
- **T-A `test_real_viewer_plays_or_reports_no_display` (US1, AC-1)** — nguyên nhân **CHƯA ĐO** (môi trường dựng được ở lượt đặc tả không có `mujoco`). Giả thuyết xếp theo khả năng và cách phân biệt ở research.md Q2. Việc đầu tiên của builder là **đo, không đoán** (FR-005): chạy riêng, có dấu vết ngăn xếp khi treo. Có cây quyết định: nguyên nhân ở kiểm thử (hạn mức/độ chịu tải/tranh chấp giữa các cửa sổ song song) ⇒ sửa kiểm thử; nguyên nhân ở `src/` (viewer treo lúc mở/đóng, hoặc `display_available()` báo "có" mà không có cửa sổ GL dùng được — khoảng trống so với 005 FR-011/FR-014) ⇒ **DỪNG và báo** (AC-5), không sửa `src/`, không che.
- **Độ cứng chung (FR-002)**: lệnh con luôn chạy qua hạn mức hữu hạn, dọn cả nhóm tiến trình khi quá hạn, và lỗi nêu lệnh, hạn mức, đầu ra đã thu được — kiểm thử đỏ có chẩn đoán chứ không treo.
- **Không che lỗi (FR-004, FR-006)**: không `skip`/`xfail` mới, mọi khẳng định nghiệm thu giữ nguyên hoặc chặt hơn; dấu `pytest.mark.display` đã có giữ nguyên.

<a id="technical-context"></a>
## Technical Context

**Language/Version**: Python 3.11 (kế thừa 001; `requires-python = ">=3.11,<3.13"`)

**Primary Dependencies**: không thêm phụ thuộc; dùng `pytest`, `subprocess`, `multiprocessing`, `threading`, `time` của thư viện chuẩn và các mô-đun dự án đã được hai kiểm thử import (`mma_ai.visualization.display`, `mma_ai.monitoring.cli`, `mma_ai.monitoring.viewer3d`).

**Storage**: không; kiểm thử chỉ ghi dưới `tmp_path` (INV-002).

**Testing**: `pytest` (cổng tests của `.ai/profile.yml`: `pytest -n auto --ignore=tests/e2e`, tức **chạy song song nhiều tiến trình** — một yếu tố cần đo khi phân tích T-A); `ruff check`; `mypy --strict`.

**Target Platform**: Linux gốc (máy phát triển, ĐÃ ĐO ở 005 có `DISPLAY=:0`); môi trường của cổng tests CHƯA ĐO có cửa sổ GL dùng được hay không; WSL2/macOS/Windows ngoài phạm vi (thuộc 006).

**Project Type**: sửa kiểm thử của thư viện + CLI nghiên cứu hiện có.

**Performance Goals**: NFR-PERF-001 của spec (T-A ≤ 25 s có màn hình / ≤ 5 s không màn hình ở lệnh con; T-B phần tiến trình tách riêng ≤ 10 s, chờ khởi chạy ≤ 5 s).

**Constraints**: chỉ hai tệp kiểm thử được ghi; không `src/`; không skip/xfail; mỗi lượt builder chạy test 1–2 lần (cộng dồn bằng chứng); thông báo tiếng Việt.

**Scale/Scope**: 2 tệp kiểm thử, ước ≤ 120 dòng đổi (thêm hàm trợ giúp chờ tiến trình + hàm chạy lệnh con có dọn); 0 tệp mới ở `src/`.

<a id="constitution-check"></a>
## Constitution Check

*Cổng: qua trước Phase 0; kiểm lại sau Phase 1.* Nguồn: `.specify/memory/constitution.md` v1.0.0.

| Nguyên tắc | Đánh giá | Cách plan đáp ứng |
|---|---|---|
| I. Bằng chứng thắng lời khai | Đạt | "Xanh" chỉ khi lệnh `pytest <nodeid>` lặp theo NFR-REL-001 cho kết quả xanh, do cổng máy ghi vào `evidence/`; nguyên nhân thật được chứng minh bằng số đo (research.md), không bằng lời. |
| II. Test trước, sửa sau | Đạt | Đối tượng của feature chính là test; trước khi sửa phải tái hiện đỏ (T-B: tái hiện cửa sổ giữa "tạo" và `.start()`; T-A: tái hiện quá hạn hoặc ghi rõ "không tái hiện được trên môi trường đo"). Không `skip`/`xfail`/`importorskip` mới; số kiểm thử không giảm (INV-001). Mục `Nguyên nhân gốc` và `BÀI HỌC` nằm trong báo cáo/commit của task. |
| III. Lát cắt nhỏ, một vai một task | Đạt | Hai task độc lập (mỗi kiểm thử một tệp, một chủ); vùng ghi đúng hai tệp. Hai tệp này đã có chủ ở feature cũ (003 T333, 005 T519) — các task đó đã đóng; bước tasks của 007 khai tệp là `outputs` của task sửa. |
| IV. Bất biến và NFR có mã | Đạt | INV-001…003, NFR-REL-001/PERF-001/QUAL-001 khai ở spec và được tham chiếu 1:1 ở bảng truy vết dưới; mỗi NFR có ngưỡng số và lệnh đo. |
| V. Không đổi cái không được yêu cầu | Đạt | Không `src/`, không lockfile, không cấu hình framework, không phụ thuộc mới; việc đáng làm ngoài phạm vi (xem Rủi ro) chỉ ghi đề xuất. |
| VI. Bí mật chỉ qua biến môi trường | Đạt (không áp dụng) | Không có bí mật; tài liệu không ghi đường dẫn tuyệt đối của máy. |
| VII. Nhánh bảo vệ | Đạt | Làm trên nhánh task; không push/merge vào nhánh bảo vệ. |
| VIII. Tài liệu sinh từ mã và bằng chứng | Đạt | Số đo (tỷ lệ đỏ trước/sau, thời gian) lấy từ đầu ra lệnh và `evidence/`, không viết tay. |
| IX. Mỗi tài liệu MỘT chỗ | Đạt | Tài liệu theo feature chỉ ở `specs/007-…/`; không đổi aggregate/INV/NFR của bounded context nên không đụng `docs/02-strategic`, `docs/03-tactical`; không có API và không có thực thể dữ liệu bền vững ⇒ không sinh `contracts/`; `data-model.md` chỉ ghi đối tượng tạm của kiểm thử. |

Kiểm lại sau Phase 1: không phát sinh vi phạm; không có mục nào cần ghi vào Complexity Tracking.

<a id="phu-thuoc"></a>
## Phụ thuộc

- Mã nguồn kiểm thử nằm ở nhánh tích hợp (`ai-sdlc/integration`): `src/mma_ai/visualization/{cli,replay,playback,viewer,display}.py`, `src/mma_ai/monitoring/{cli,viewer3d}.py`, `tests/integration/train_fixtures.py`. Chỉ **đọc**.
- 005 (AC-1, AC-2, FR-001/004/005/011/014) và 003 (FR-022, INV-005 và yêu cầu chạy không màn hình) là nguồn của các khẳng định phải giữ nguyên (FR-004 của spec này).

<a id="kien-truc-tach-trach-nhiem"></a>
## Kiến trúc & tách trách nhiệm

Không có thành phần sản phẩm mới. Hai thay đổi nằm trong tệp kiểm thử, mỗi tệp một hàm trợ giúp cục bộ (không tạo mô-đun dùng chung — tránh mở rộng vùng ghi):

| Tệp | Trợ giúp thêm (tên gợi ý, builder chốt) | Trách nhiệm | FR/AC |
|---|---|---|---|
| `tests/integration/test_viewer3d_train.py` | `_wait_until_started(proc, timeout_s)` | Poll (`time.sleep` ngắn) tới khi `proc.pid is not None`; trả sớm nếu `proc.exitcode is not None` (đã thoát sớm); hết hạn ⇒ `pytest.fail` bằng tiếng Việt "không khởi chạy được trong hạn mức". Hằng số hạn mức đặt tên rõ ở đầu hàm kiểm thử. | FR-003, AC-2 |
| `tests/integration/test_replay_viewer_real.py` | `_run_cli_bounded(cmd, timeout_s, env=None)` | Chạy lệnh con bằng `Popen(..., start_new_session=True)` + `communicate(timeout=…)`; quá hạn ⇒ giết cả nhóm tiến trình, lấy đầu ra còn lại, `pytest.fail` nêu lệnh, hạn mức, stdout/stderr. Dùng cho cả nhánh có màn hình lẫn không màn hình. | FR-002, AC-1 |

Nhánh có màn hình của T-A **chỉ** thêm các thay đổi bổ sung sau khi đo (research.md Q2): hạn mức hiệu chỉnh theo số đo (không phải con số đoán), và — chỉ khi đo chứng minh tranh chấp giữa các cửa sổ chạy song song — một khoá tệp nhẹ dưới thư mục tạm của hệ thống để nối tiếp các lần mở viewer thật. Không đổi nội dung khẳng định.

<a id="quyet-dinh-thiet-ke"></a>
### Quyết định thiết kế

- **D1 — Chờ có điều kiện thay vì ngủ cố định**: poll tới điều kiện "có PID" với hạn mức, không `sleep` một lần; hạn mức rộng cho máy bận nhưng hữu hạn (5 s, ≥ 10× thời gian khởi tạo tiến trình thường gặp) — tất định theo trạng thái, không theo thời gian.
- **D2 — Giữ nguyên danh sách theo dõi**: hàm tạo tiến trình thay thế vẫn ghi nhận đối tượng ngay khi tạo (để biết "đã tạo"), nhưng điều kiện đi tiếp là "đã có PID", không phải "đã được tạo".
- **D3 — Dọn theo nhóm tiến trình**: viewer thật có thể sinh luồng/tiến trình con; `start_new_session=True` rồi giết cả nhóm để không để lại cửa sổ mồ côi làm hỏng lần chạy sau (INV-002).
- **D4 — Đo trước, sửa sau cho T-A**: không viết bản sửa T-A trước khi có số đo (FR-005, hiến chương II); nếu đo cho thấy nguyên nhân ở `src/` thì tệp T-A **không** đổi ngoài phần độ cứng chẩn đoán FR-002 (phần này không làm xanh giả: kiểm thử vẫn đỏ nhưng có chẩn đoán) — và báo theo AC-5.
- **D5 — Một nguồn sự thật cho chọn nhánh**: giữ `display_available()` làm điều kiện chọn nhánh; không thêm dò biến môi trường riêng.

<a id="project-structure"></a>
## Project Structure

<a id="documentation-this-feature"></a>
### Documentation (this feature)

```text
specs/007-stabilize-viewer-tests/
├── spec.md
├── plan.md            # tệp này
├── research.md        # Phase 0: nguyên nhân, giả thuyết, cách đo, cây quyết định
├── data-model.md      # Phase 1: đối tượng tạm của kiểm thử (không có thực thể bền vững)
├── quickstart.md      # Phase 1: kịch bản kiểm chứng theo AC
├── request.link
└── checklists/
    └── requirements.md
```

`data-model.md` chỉ mô tả đối tượng tạm trong kiểm thử; không có `contracts/` (không có giao diện bên ngoài) — không tạo thư mục rỗng.

<a id="source-code-repository-root-chi-phan-007-cham-toi"></a>
### Source Code (repository root) — chỉ phần 007 chạm tới

```text
tests/integration/
├── test_replay_viewer_real.py    # T-A: thêm _run_cli_bounded; hiệu chỉnh theo số đo (nếu nguyên nhân ở kiểm thử)
└── test_viewer3d_train.py        # T-B: thêm _wait_until_started; sửa đoạn "Chờ tiến trình 3D được khởi chạy"
tests/e2e/test_007_viewer_entrypoint.py   # QA: kịch bản trên entrypoint thật (task T705)
src/mma_ai/visualization/viewer.py        # CHỈ đổi qua task sửa gốc T706 (AC-5): set_texts/clear_texts ra khỏi lock_ctx
tests/unit/test_viewer.py                 # ca thử hồi quy của T706
src/                                      # mọi tệp khác KHÔNG đổi (INV-003)
```

<a id="lenh-build-test"></a>
## Lệnh build / test

Không có bước build. Chạy trong worktree của task (cần môi trường có `mujoco`, `myo-sim`, `torch` cho phần huấn luyện thật của T-B, theo `pyproject.toml` của nhánh tích hợp):

```text
# T-B (nhanh; có phần huấn luyện thật nếu có torch)
uv run --isolated --with pytest pytest -q -p no:cacheprovider tests/integration/test_viewer3d_train.py::test_view3d_process_separate

# T-A (viewer thật; đo thời gian từng bước, xem research.md Q2)
uv run --isolated --with pytest pytest -q -p no:cacheprovider -m display tests/integration/test_replay_viewer_real.py

# Cả hai tệp, như cổng (song song)
uv run --isolated --with pytest --with pytest-xdist pytest -q -p no:cacheprovider -n auto tests/integration/test_replay_viewer_real.py tests/integration/test_viewer3d_train.py

# Lint, kiểu
uv run --isolated --with ruff ruff check tests/integration/test_replay_viewer_real.py tests/integration/test_viewer3d_train.py
uv run --isolated --with mypy mypy --strict tests/integration/test_replay_viewer_real.py tests/integration/test_viewer3d_train.py
```

<a id="truy-vet-yeu-cau-thiet-ke"></a>
## Truy vết yêu cầu → thiết kế

| Mã | Thiết kế / nơi hiện thực | Kiểm bằng |
|---|---|---|
| AC-1, FR-001, FR-002, FR-008 | `_run_cli_bounded` + hạn mức; chọn nhánh bằng `display_available()` (D2/D3/D5) | `pytest tests/integration/test_replay_viewer_real.py` lặp theo NFR-REL-001 |
| AC-2, FR-003 | `_wait_until_started` (D1/D2) | `pytest …::test_view3d_process_separate` lặp, có và không tải CPU nền |
| AC-3, FR-005 | research.md (đo trước/sau, môi trường đo) + báo cáo task | số đo trong báo cáo/`evidence/` |
| AC-4, FR-004, FR-006, FR-007, INV-001, INV-003 | giữ khẳng định; vùng ghi hai tệp | so diff với `outputs`; quét `skip`/`xfail`/`importorskip` trong hai tệp; đếm kiểm thử không giảm |
| AC-5, FR-007 | cây quyết định ở research.md Q2 | báo cáo nêu tệp, hàm, bằng chứng, đề xuất |
| INV-002 | `tmp_path`, dọn nhóm tiến trình, `stop_event` | chạy lặp và chạy cả bộ không để tiến trình mồ côi |
| NFR-REL-001 | lặp 5/5 (và 5/5 có tải nền cho T-B) | `pytest` lặp; `stress`/vòng lặp nền |
| NFR-PERF-001 | hạn mức tường minh trong hai kiểm thử | `pytest --durations=5` |
| NFR-QUAL-001 | — | `ruff check`, `mypy --strict` trên hai tệp |

<a id="rui-ro-viec-chua-kiem"></a>
## Rủi ro & việc CHƯA KIỂM

- **T-A chưa đo**: lượt đặc tả không dựng được môi trường có `mujoco`; mọi giả thuyết về T-A ở research.md là **CHƯA KIỂM** cho tới khi builder đo. Môi trường cổng tests có hay không có cửa sổ GL dùng được cũng CHƯA KIỂM.
- **Khả năng cao nguyên nhân T-A ở `src/`**: 005/research.md đã ĐO viewer thụ động thoát chập chờn (sập `SIGSEGV` hoặc treo lúc dọn dẹp ở nhiều lần chạy) và `launch_passive` có thể kết thúc cả tiến trình khi không khởi tạo được GLFW; nếu đo xác nhận thì AC-5 áp dụng (T-A còn đỏ có chẩn đoán, báo cáo kèm đề xuất cho vai khác). Đây là kết quả hợp lệ của feature, không phải thất bại của kế hoạch.
- **`-n auto`**: cổng chạy song song; nhiều tiến trình có thể cùng mở cửa sổ viewer thật hoặc cùng chiếm CPU lúc nạp `mujoco`; cần đo cả khi chạy một mình và khi chạy song song để tách "chậm" khỏi "treo".
- **Đề xuất ngoài phạm vi (không làm ở đây)**: hàm mục tiêu của tiến trình trong T-B là hàm lồng nhau nên không dùng được với phương thức khởi tạo `spawn` (macOS/Windows) — thuộc `006-cross-platform-support`; ghi để vai đó xử lý.
- **Số "5 lần" của NFR-REL-001** là tự chốt; nâng nếu số đo cho thấy tỷ lệ đỏ gốc thấp hơn 1/5.

<a id="quyet-dinh-o-buoc-tasks"></a>
## Quyết định ở bước tasks

- Hai task kiểm thử độc lập (T-B nhanh, có thể làm trước; T-A đo trước rồi mới sửa); mỗi task có `outputs` đúng một tệp; không dùng `depends_on` giữa hai task. Hai task này `depends_on` task chủ cũ của tệp (003/005) và khung gói `T709`.
- Task hội tụ: `T706` (builder, sửa `viewer.py` theo AC-5 sau khi `T702` đo), `T707` (spec, chỉnh INV-003/FR-007), `T708`/`T710` (nối mã `003/AC-5` vào docstring test của 003: integration do builder, e2e do qa vì builder không ghi được `tests/e2e/**`), `T709` (khung gói), `T711` (reviewer). `T705` (qa, e2e) và `T704` (reviewer) đứng sau `T701`/`T702`.
- Task T-A gồm hai bước ghi trong mô tả: (1) đo và ghi nguyên nhân; (2) sửa hoặc dừng-và-báo theo cây quyết định. Nếu dừng-và-báo thì task kết thúc với báo cáo, không tạo diff ngoài phần độ cứng FR-002.
- Task cuối: chạy lặp theo NFR-REL-001 và gom bằng chứng (không có tệp mã; chỉ evidence do cổng sinh).
- Không có task giao diện, hạ tầng hay khách duyệt.

<a id="quyet-dinh-ve-vai-challenger"></a>
## Quyết định về vai `challenger`

- Tự chốt: **KHÔNG dùng** vai `challenger` — INV-001…003 là bất biến về quy trình sửa kiểm thử (không giảm số kiểm thử/độ chặt khẳng định, độc lập thứ tự và không để tiến trình mồ côi, vùng ghi đúng hai tệp), không phải bất biến của hàm nhận đầu vào mà vector/fuzz đánh sập được; chúng được kiểm tất định bằng quét `skip`/`xfail`/`importorskip`, `pytest --collect-only`, so diff với `outputs` và chạy lặp (task QA và reviewer). Dùng challenger chỉ thêm một lượt mà không thêm bằng chứng và đổi cổng review thành nhất trí hai vai.

<a id="phan-bien-plan-lint"></a>
## Phản biện plan_lint

- Phản biện: kế hoạch có thể bị coi là "né" T-A bằng hạn mức lớn hơn. Đáp: hạn mức chỉ được đổi khi số đo chứng minh lệnh con **kết thúc** nhưng chậm hơn hạn cũ; lệnh con treo thật thì kiểm thử vẫn đỏ có chẩn đoán và áp dụng AC-5 — không có đường nào làm xanh bằng cách nới.
- Phản biện: `_wait_until_started` có thể che lỗi "tiến trình không bao giờ khởi chạy". Đáp: hết hạn thì kiểm thử đỏ với thông điệp riêng (Acceptance Scenario 4 của US2); hạn mức hữu hạn.
- Phản biện: máy báo `NO_E2E` (không task `qa` nào sinh `tests/e2e/**`). Đáp (đã đổi so với bản 1.0.0): có task `T705` của `qa` sinh `tests/e2e/test_007_viewer_entrypoint.py` chạy lệnh thật `python -m mma_ai.visualization.cli` / `python -m mma_ai.monitoring.cli` bằng tiến trình con; tệp này nằm trong vùng ghi FR-007/INV-003 của spec 1.1.0 nên `NO_E2E` không còn. `lý do` bản cũ (không thêm tệp e2e) bị thay vì mã đã gộp có tệp đó.
- Phản biện: một tệp khoá chung giữa các kiểm thử làm kiểm thử phụ thuộc thứ tự. Đáp: chỉ thêm khi số đo chứng minh tranh chấp; khoá nối tiếp chứ không đổi thứ tự, và kiểm thử vẫn độc lập (INV-002).

<a id="complexity-tracking"></a>
## Complexity Tracking

Không có vi phạm hiến chương cần biện minh.
