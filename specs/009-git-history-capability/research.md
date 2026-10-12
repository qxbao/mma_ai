---
id: "RESEARCH-009"
title: "Nghiên cứu Phase 0 — cách chứng minh phép dò lịch sử git và cách đo ở bản archive"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "009-git-history-capability"
version: "1.0.0"
---

# Research (Phase 0): chứng minh phép dò `requires_git_history`

- [Q1 — Thay `subprocess.run` ở đâu để chứng minh bốn nhánh? (FR-001, FR-002)](#q1-thay-subprocessrun-o-dau-de-chung-minh-bon-nhanh-fr-001-fr-002)
- [Q2 — Dựng phép chạy pytest "không có .git" thế nào cho đo đúng? (FR-003)](#q2-dung-phep-chay-pytest-khong-co-git-the-nao-cho-do-dung-fr-003)
- [Q3 — Tỉ lệ loại 5% có đủ chỗ cho test INV-002 của 008? (NFR-GATE-001)](#q3-ti-le-loai-5-co-du-cho-cho-test-inv-002-cua-008-nfr-gate-001)
- [Q4 — Tái hiện AC-2 trên một "bản archive" thật ở bước QA](#q4-tai-hien-ac-2-tren-mot-ban-archive-that-o-buoc-qa)
- [Tổng hợp việc còn mở (không chặn plan)](#tong-hop-viec-con-mo-khong-chan-plan)


Quy ước nhãn: **ĐÃ ĐỌC** = rút ra từ việc đọc mã trên nhánh tích hợp `ai-sdlc/integration` @ffea840, chưa chạy trên mã đó; **ĐÃ ĐO** = có lần chạy thật trong lượt này (ghi rõ lệnh); **CHƯA KIỂM** = chưa làm. Mã nguồn bộ cổng năng lực không có ở nhánh hiện hành (`master` chỉ có `specs/`, `docs/`), nên việc đọc đi qua `git show ai-sdlc/integration:<đường dẫn>`.

<a id="q1-thay-subprocessrun-o-dau-de-chung-minh-bon-nhanh-fr-001-fr-002"></a>
## Q1 — Thay `subprocess.run` ở đâu để chứng minh bốn nhánh? (FR-001, FR-002)

**ĐÃ ĐỌC** — `_capability_available("requires_git_history")` trong `tests/unit/capability_gate.py`:

```text
completed = subprocess.run(["git","rev-parse","--is-inside-work-tree"], capture_output=True,
                           check=False, timeout=5, cwd=<gốc dự án = parents[2] của tệp>)
return completed.returncode == 0          # except (OSError, subprocess.TimeoutExpired): return False
```

- Mô-đun `capability_gate` làm `import subprocess` rồi gọi `subprocess.run(...)`, nên `monkeypatch.setattr(capability_gate.subprocess, "run", giả)` (hoặc `monkeypatch.setattr("capability_gate.subprocess.run", giả)`) thay đúng tên được gọi. `subprocess` là cùng một đối tượng mô-đun ở mọi nơi ⇒ bản giả có hiệu lực toàn tiến trình trong thời gian test; `monkeypatch` tự khôi phục sau test (INV-001, Edge Case "khôi phục").
- `capability_gate` import được vì `conftest.py` ở gốc đặt `tests/unit` vào `sys.path` và khai `pytest_plugins = ["capability_gate"]`; test dùng `import capability_gate` (không dùng `from tests.unit …`).
- Bản giả trả `subprocess.CompletedProcess(args=[…], returncode=0|128)` hoặc ném `OSError`/`subprocess.TimeoutExpired("git", 5)`. Bản giả ghi lại `kwargs` để kiểm `timeout` hữu hạn ≤ 5 (NFR-REL-001) và `cwd` là một đường dẫn (không kiểm giá trị tuyệt đối — hiến chương VI: không ghi đường dẫn máy riêng vào test).
- `_capability_available` là hàm riêng (tiền tố `_`); test gọi trực tiếp vì yêu cầu gốc nêu đúng tên hàm này. mypy `--strict` chấp nhận gọi hàm riêng của mô-đun khác (không phải lỗi kiểu); `ruff` mặc định `E,F,I` không bật quy tắc truy cập riêng.

**Quyết định**: bốn test đơn vị nhỏ (một test mỗi nhánh: `0`, `128`, `OSError`, `TimeoutExpired`), dùng chung một bản giả dựng từ hàm trợ giúp trong tệp test; không đổi `capability_gate.py` (FR-004).

<a id="q2-dung-phep-chay-pytest-khong-co-git-the-nao-cho-do-dung-fr-003"></a>
## Q2 — Dựng phép chạy pytest "không có .git" thế nào cho đo đúng? (FR-003)

**ĐÃ ĐỌC** — phép dò cố định `cwd` ở `Path(__file__).resolve().parents[2]` (gốc dự án suy từ vị trí tệp plugin), **không** theo thư mục hiện hành của pytest. Hệ quả: test hiện có (`_run_pytest` trong `test_capability_gate.py`) chạy `cwd=tmp_path` nhưng nạp plugin từ `tests/unit` thật ⇒ phép dò vẫn hỏi git ở **gốc dự án thật**. Nếu test AC-2 chỉ đổi `cwd`, ở máy có git phép dò trả `True`, test gắn dấu **chạy** thay vì bị loại, và test hoặc đỏ vì sai kỳ vọng, hoặc (tệ hơn) xanh vì không đo gì.

**ĐÃ ĐO** (lệnh: `PYTHONPATH=<cây tạm>/tests/unit uv run --isolated --no-project --with pytest python -m pytest -p capability_gate -q -p no:cacheprovider <thư mục test>`, trong cây tạm ngoài mọi kho git): đặt bản sao `capability_gate.py` ở `<gốc tạm>/tests/unit/capability_gate.py` ⇒ `parents[2]` là `<gốc tạm>`, `git rev-parse` ở đó thoát 128 ⇒ test gắn `requires_git_history` bị loại, đầu ra có nguyên văn `Kiểm thử bị loại theo năng lực: 1/1 …` và `test_example.py::test_git [requires_git_history]: Máy không có lịch sử git`. Cách này đo đúng phép dò thật (cùng mã, không bản giả) và không phụ thuộc máy có git hay không.

**Quyết định** cho test FR-003:

1. Trong `tmp_path` dựng cây `gốc/tests/unit/capability_gate.py` (chép từ tệp thật qua `shutil.copyfile`) và thư mục `gốc/work/` chứa `test_example.py` (1 test gắn dấu + 19 test thường, cùng khuôn `_run_pytest` hiện có).
2. Chạy `sys.executable -m pytest -p capability_gate -q -p no:cacheprovider --capability-report=<tệp> gốc/work` với `PYTHONPATH=gốc/tests/unit` (không thêm `src` — phép dò git không import `mma_ai`).
3. Môi trường con: **xoá** `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE` (nếu cổng chạy dưới hook của git) và đặt `GIT_CEILING_DIRECTORIES=<cha của gốc>` để `git` không leo lên kho cha nếu `TMPDIR` nằm trong một kho (Edge Case "kho cha" áp cho chính test này).
4. Khẳng định: mã thoát 0; `1 deselected`/"19 passed"; dòng "bị loại" có `requires_git_history` + `Máy không có lịch sử git`; báo cáo JSON `collected == 20`, `deselected == 1`, `ratio ≈ 0.05`, `items[0].marker == "requires_git_history"`, `items[0].reason == "Máy không có lịch sử git"`; đầu ra **không** có `skipped`, `xfailed`.
5. **Điều kiện tiên quyết có sẵn trên máy khác**: nếu máy của test không thể chạy pytest con vì thiếu plugin thì đó là lỗi môi trường chung, không phải trường hợp bị loại — không thêm cơ chế bỏ qua (INV-001).

Phương án đã loại: (a) chỉ đổi `cwd` — đo nhầm kho thật (nêu trên); (b) thêm biến môi trường cưỡng bức "không có git" vào `capability_gate.py` — đổi mã cổng ngoài phạm vi (FR-004, Out of Scope) và để lộ cửa che lỗi; (c) xoá `git` khỏi `PATH` — chỉ chạm nhánh `OSError`, không chạm nhánh mã 128 của git thật, và làm hỏng việc chạy `sys.executable`/`uv` ở môi trường con khác.

<a id="q3-ti-le-loai-5-co-du-cho-cho-test-inv-002-cua-008-nfr-gate-001"></a>
## Q3 — Tỉ lệ loại 5% có đủ chỗ cho test INV-002 của 008? (NFR-GATE-001)

**ĐÃ ĐỌC** — `pytest_sessionfinish`: phiên đỏ khi `report["ratio"] > maximum` (so sánh **lớn hơn nghiêm ngặt**), mặc định `maximum = 0.05`; `ratio = deselected / collected`. Do đó 1/20 = 0,05 **không** vượt (đủ cho cấu hình FR-003), và cần mẫu số ≥ 20 cho mỗi test bị loại thêm.

**ĐÃ ĐỌC** — số test thu thập ước lượng ở `tests/e2e/` trên nhánh tích hợp (đếm hàm `test_*` và bội số của `parametrize` đọc được): `test_008_docs_entrypoints.py` ≈ 24 (4 + 1 + 1 + 1 + 1 + 6 + 3 + 1 + 6), `test_007_viewer_entrypoint.py` 3, `test_env_acceptance.py` 5, `test_evaluate_acceptance.py` 5, `test_platform_acceptance.py` 5, `test_replay_acceptance.py` 5, `test_train_acceptance.py` 7 ⇒ **≥ 54** (CHƯA KIỂM bằng `--collect-only`). 1/54 ≈ 1,9% ≤ 5%. Chạy riêng `test_008_docs_entrypoints.py` (≈ 24) cho 1/24 ≈ 4,2% ≤ 5%: vẫn qua.

**ĐÃ ĐỌC** — không test nào trong `tests/e2e/` mang dấu năng lực khác (tìm `pytest.mark.requires_*|windows_only|posix_only|linux_only|macos_only|display` chỉ ra các tệp ở `tests/challenge`, `tests/integration`, `tests/unit`); trên Linux phiên `e2e` chỉ có đúng 1 test bị loại do feature này. Phiên `tests` (`--ignore=tests/e2e`) không chứa test INV-002 của 008 nên không thêm tỉ lệ nào do feature.

**Rủi ro còn lại** (ghi ở plan): nếu một test e2e mới có dấu năng lực được thêm bởi feature khác, ngân sách 5% của phiên `e2e` giảm; CHƯA KIỂM bằng số đếm thật — QA đo bằng `--collect-only` và `--capability-report` (quickstart, kịch bản 2).

<a id="q4-tai-hien-ac-2-tren-mot-ban-archive-that-o-buoc-qa"></a>
## Q4 — Tái hiện AC-2 trên một "bản archive" thật ở bước QA

Cách tái hiện không cần cổng toàn hệ: `git archive ai-sdlc/integration | tar -x -C <thư mục sạch>` (không có `.git`), rồi áp thay đổi của task vào thư mục đó (hoặc `git archive` từ nhánh task đã có W-2), chạy `pytest tests/e2e --capability-report=<tệp>` ở đó và đọc báo cáo. Kỳ vọng: test INV-002 của 008 nằm trong `items`, `ratio` ≤ 0,05, các test khác của tệp PASS. **CHƯA KIỂM** — lượt đặc tả không dựng môi trường có `mujoco`/`myo-sim`; việc chạy là của QA/builder.

<a id="tong-hop-viec-con-mo-khong-chan-plan"></a>
## Tổng hợp việc còn mở (không chặn plan)

| # | Việc | Nhãn | Ai làm |
|---|---|---|---|
| O-1 | Đếm thật số test thu thập của phiên `e2e` trên nhánh tích hợp (`--collect-only`) để xác nhận mẫu số ≥ 20 | CHƯA KIỂM | qa |
| O-2 | Xác nhận bản archive của cổng không nằm trong một cây làm việc git khác | CHƯA KIỂM | qa/platform |
| O-3 | Chạy `ai-sdlc verify --branch ai-sdlc/integration` sau khi hai việc vào nhánh (AC-3) | CHƯA KIỂM | cổng máy |
