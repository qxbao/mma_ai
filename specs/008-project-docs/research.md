---
id: "RESEARCH-008"
title: "Bộ tài liệu dự án mma_ai — Nghiên cứu Phase 0"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-12"
feature: "008-project-docs"
version: "1.0.0"
---

# Research (Phase 0): Bộ tài liệu dự án mma_ai

- [Q1 — Viết lệnh chạy thế nào cho "chạy được" mà vẫn đúng 4 lệnh của yêu cầu?](#q1-viet-lenh-chay-the-nao-cho-chay-duoc-ma-van-dung-4-lenh-cua-yeu-cau)
- [Q2 — Nhóm cài đặt nào, và `ruff`/`mypy` đến từ đâu?](#q2-nhom-cai-dat-nao-va-ruffmypy-den-tu-dau)
- [Q3 — CHANGELOG 0.1.0 nên tóm tắt cái gì, cho đúng với mã hiện có?](#q3-changelog-010-nen-tom-tat-cai-gi-cho-dung-voi-ma-hien-co)
- [Q4 — Tình trạng nền tảng nên nói gì?](#q4-tinh-trang-nen-tang-nen-noi-gi)
- [Q5 — Mã thoát và cạm bẫy nào phải vào guide?](#q5-ma-thoat-va-cam-bay-nao-phai-vao-guide)
- [Q6 — Có cần tạo/đổi tài liệu `docs/02-strategic`, `docs/03-tactical`, `rbac`, `contracts` JSON schema, `.ai/stack-proposal.yml`?](#q6-co-can-taodoi-tai-lieu-docs02-strategic-docs03-tactical-rbac-contracts-json-schema-aistack-proposalyml)
- [Q7 — Cách kiểm độc lập các lệnh khi máy đo thiếu phụ thuộc/màn hình?](#q7-cach-kiem-doc-lap-cac-lenh-khi-may-do-thieu-phu-thuocman-hinh)


Không còn `NEEDS CLARIFICATION`. Các câu hỏi dưới đây là những điểm kỹ thuật tài liệu phải chốt trước khi viết; nguồn là mã/khảo sát (`docs/00-survey/mma-ai-project-docs.md`), không phải suy đoán.

<a id="q1-viet-lenh-chay-the-nao-cho-chay-duoc-ma-van-dung-4-lenh-cua-yeu-cau"></a>
## Q1 — Viết lệnh chạy thế nào cho "chạy được" mà vẫn đúng 4 lệnh của yêu cầu?

- **Decision**: giữ đúng 4 lệnh dạng `python …`; một dòng nói chạy trong môi trường đã `uv sync` (kích hoạt `.venv` hoặc đặt tiền tố `uv run`).
- **Rationale**: `pyproject.toml` dùng `hatchling` với `src/mma_ai` nên `python -m mma_ai.…` cần gói đã cài vào môi trường (`uv sync` cài gói ở chế độ dự án); `scripts/train.py` import `mma_ai.learning.cli` (đọc `scripts/train.py`) nên cũng cần môi trường đó.
- **Alternatives**: viết cả 4 lệnh với `uv run` (thêm tiền tố mỗi dòng, lệch yêu cầu "đúng 4 lệnh"); đặt `PYTHONPATH=src` (hack, không là cách cài chính thức).

<a id="q2-nhom-cai-dat-nao-va-ruffmypy-den-tu-dau"></a>
## Q2 — Nhóm cài đặt nào, và `ruff`/`mypy` đến từ đâu?

- **Decision**: README nêu `uv sync` + ba nhóm tuỳ chọn `rl` (`torch`, `tensorboard`), `eval` (`pandas`, `matplotlib`), `dev` (`pytest`, `jsonschema`) đúng `pyproject.toml`. Cú pháp cài nhóm: `uv sync --extra rl` (nhóm khai ở `[project.optional-dependencies]` nên là extra, không phải `--group`). CONTRIBUTING chạy lint/mypy qua `uv run --isolated --with ruff …` / `--with mypy …` giống cổng của dự án.
- **Rationale**: nhóm `dev` không có `ruff`/`mypy` (khảo sát, `pyproject.toml`); dặn người đọc `uv sync --extra dev` rồi gọi `ruff` sẽ lỗi.
- **Alternatives**: thêm `ruff`/`mypy` vào `dev` (đổi `pyproject.toml` — ngoài phạm vi, INV-002; ghi thành đề xuất).
- **Cần kiểm lúc viết**: lệnh `uv sync --extra rl` chạy được (CHƯA KIỂM ở lượt plan; reviewer đo ở Task 3 hoặc ghi "CHƯA KIỂM").

<a id="q3-changelog-010-nen-tom-tat-cai-gi-cho-dung-voi-ma-hien-co"></a>
## Q3 — CHANGELOG 0.1.0 nên tóm tắt cái gì, cho đúng với mã hiện có?

- **Decision**: gom theo năm spec M0–M1, ghi vào nhóm `Added`:
  - M0 (001): môi trường mô phỏng vật lý và kiểm tra sức khoẻ số học — theo `src/mma_ai/physics/{simulator,body_model,numeric_health}.py`.
  - M1 (002): môi trường khuỷu tay cơ bắp, tập mục tiêu train/test — `src/mma_ai/environment/`.
  - M1 (003): huấn luyện PPO, checkpoint, hồ sơ tái lập, giao diện quan sát (`--ui`, `--view3d`), đo hiệu năng — `src/mma_ai/learning/`, `src/mma_ai/monitoring/`.
  - M1 (004): đánh giá so với random và biểu đồ — `src/mma_ai/evaluation/`.
  - M1 (005): phát lại/demo 3D — `src/mma_ai/visualization/`.
  `[Unreleased]`: để trống hoặc trỏ spec 006 (đa nền tảng, đang làm) và 007 (ổn định test hiển thị) nếu đã có mã khi viết — kiểm `git log` lúc viết, không phỏng đoán.
- **Rationale**: spec 001 nhắc `scripts/check_env.py`, `scripts/benchmark.py`, `scripts/smoke_test.py`, nhưng `scripts/` hiện chỉ có `train.py` — CHANGELOG không được nêu script không tồn tại (INV-001, hiến chương I).
- **Alternatives**: chép nguyên danh sách FR từ spec (quá dài, vi phạm "tóm tắt"); ghi số test (cấm, hiến chương VIII).

<a id="q4-tinh-trang-nen-tang-nen-noi-gi"></a>
## Q4 — Tình trạng nền tảng nên nói gì?

- **Decision**: "Hiện nhắm Linux/WSL2. Windows và macOS đang được làm ở `specs/006-cross-platform-support`; chưa hứa chạy." Không nói "đang hỗ trợ một phần" trừ khi đọc lại hiện trạng 006 lúc viết xác nhận.
- **Rationale**: khảo sát ghi mã còn nhập `resource` POSIX (`src/mma_ai/learning/resources.py`) và phụ thuộc đồ hoạ; Q-0002 của người dùng đã xác nhận *mục tiêu* (Windows native chính, CUDA tuỳ chọn, macOS phải chạy tốt) thuộc spec 006, chưa là hiện trạng. Tài liệu của feature này không được hứa trước (INV-003).
- **Alternatives**: bỏ mục (yêu cầu đòi mục này); ghi mục tiêu 006 như đã đạt (sai).

<a id="q5-ma-thoat-va-cam-bay-nao-phai-vao-guide"></a>
## Q5 — Mã thoát và cạm bẫy nào phải vào guide?

- **Decision**: lấy từ docstring/mã (ghi ở `contracts/cli-commands.md`): train 0/1/2/3/4/130; evaluate 0/1/2/4/5/6/7/130 và checkpoint ngoài run cần `--out`; replay 0/1/2/4/5/6/7/8/130, chọn đúng một trong `--episode`/`--checkpoint`, thiếu màn hình ⇒ 7, `--headless`; benchmark `--repeats` ≥ 5 và thoát 0/1/2.
- **Rationale**: các điểm này là chỗ người mới vấp nhất (khảo sát "Bản đồ hành vi").
- **Alternatives**: chép toàn bộ `--help` (trùng nguồn, lệch khi mã đổi — vi phạm hiến chương IX); chỉ nêu mã thoát chung (không đủ để người đọc xử lý lỗi).

<a id="q6-co-can-taodoi-tai-lieu-docs02-strategic-docs03-tactical-rbac-contracts-json-schema-aistack-proposalyml"></a>
## Q6 — Có cần tạo/đổi tài liệu `docs/02-strategic`, `docs/03-tactical`, `rbac`, `contracts` JSON schema, `.ai/stack-proposal.yml`?

- **Decision**: Không. Feature không đổi aggregate/INV/NFR của bounded context, không có phân quyền, không có API có body (dự án không có HTTP route theo khảo sát), và stack đã chốt trong cấu hình dự án (`python-mujoco-cli`).
- **Rationale**: "Không tạo tài liệu rỗng cho có"; hiến chương IX.
- **Alternatives**: tạo `context-map.md` cho một context tài liệu (rỗng nghĩa).

<a id="q7-cach-kiem-doc-lap-cac-lenh-khi-may-do-thieu-phu-thuocman-hinh"></a>
## Q7 — Cách kiểm độc lập các lệnh khi máy đo thiếu phụ thuộc/màn hình?

- **Decision**: reviewer chạy `uv run --isolated python <lệnh> --help` trong worktree sạch (như khảo sát đã làm; thoát 0) và trích đầu ra vào báo cáo; lệnh không chạy được ghi "CHƯA KIỂM" kèm lỗi nguyên văn. Không chạy huấn luyện đầy đủ hay mở cửa sổ 3D (ngoài phạm vi kiểm của tài liệu).
- **Rationale**: NFR-DOC-001 chỉ đòi mỗi lệnh có `--help` hoặc mã khớp.
- **Alternatives**: chạy huấn luyện thật (tốn GB và thời gian, không cần để xác nhận cú pháp cờ).
