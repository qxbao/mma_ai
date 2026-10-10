---
id: "SPEC-006"
title: "Hỗ trợ đa nền tảng (Windows · Linux/WSL2 · macOS) cho mma_ai — Spec"
doc_type: spec
owner_agent: spec
status: draft
updated: "2026-10-11"
feature: "006-cross-platform-support"
version: "1.0.1"
---

# Feature Specification: Hỗ trợ đa nền tảng cho mma_ai (Windows · Linux/WSL2 · macOS)

- [Bối cảnh (Context)](#boi-canh-context)
- [Clarifications](#clarifications)
- [User Scenarios & Testing *(mandatory)*](#user-scenarios-testing-mandatory)
  - [User Story 1 - Chạy train, evaluate, replay/demo, benchmark bằng `python -m mma_ai…` trên Windows gốc, Linux và macOS (Priority: P1)](#user-story-1-chay-train-evaluate-replaydemo-benchmark-bang-python-m-mma-ai-tren-windows-goc-linux-va-macos-priority-p1)
  - [User Story 2 - RAM đỉnh được đo đúng đơn vị trên cả ba hệ điều hành (Priority: P1)](#user-story-2-ram-dinh-duoc-do-dung-don-vi-tren-ca-ba-he-dieu-hanh-priority-p1)
  - [User Story 3 - Dò màn hình theo từng OS để viewer 3D MuJoCo chạy khi có màn hình (Priority: P1)](#user-story-3-do-man-hinh-theo-tung-os-de-viewer-3d-mujoco-chay-khi-co-man-hinh-priority-p1)
  - [User Story 4 - Đường dẫn, ghi tệp nguyên tử, symlink, UTF-8 và xuống dòng hoạt động trên cả ba OS (Priority: P1)](#user-story-4-duong-dan-ghi-tep-nguyen-tu-symlink-utf-8-va-xuong-dong-hoat-dong-tren-ca-ba-os-priority-p1)
  - [User Story 5 - Cài đặt tái lập trên Windows bằng uv/pip và kiểm môi trường bằng `scripts/check_env.py` (Priority: P1)](#user-story-5-cai-dat-tai-lap-tren-windows-bang-uvpip-va-kiem-moi-truong-bang-scriptscheck-envpy-priority-p1)
  - [User Story 6 - CI ma trận Linux/macOS/Windows và test đánh dấu năng lực (Priority: P2)](#user-story-6-ci-ma-tran-linuxmacoswindows-va-test-danh-dau-nang-luc-priority-p2)
  - [User Story 7 - Người dùng Linux, WSL2 và macOS không bị đổi hành vi (Priority: P2)](#user-story-7-nguoi-dung-linux-wsl2-va-macos-khong-bi-doi-hanh-vi-priority-p2)
  - [Edge Cases](#edge-cases)
- [Requirements *(mandatory)*](#requirements-mandatory)
  - [Functional Requirements](#functional-requirements)
  - [Yêu cầu phi chức năng (Non-Functional Requirements)](#yeu-cau-phi-chuc-nang-non-functional-requirements)
  - [Bất biến (Invariants)](#bat-bien-invariants)
  - [Key Entities *(include if feature involves data)*](#key-entities-include-if-feature-involves-data)
- [Success Criteria *(mandatory)*](#success-criteria-mandatory)
  - [Measurable Outcomes](#measurable-outcomes)
- [Out of Scope](#out-of-scope)
- [Assumptions](#assumptions)
- [Dev](#dev)
  - [Hiện trạng](#hien-trang)
  - [Thay đổi](#thay-doi)
  - [Tái dùng](#tai-dung)
- [QC](#qc)
  - [Phạm vi hồi quy](#pham-vi-hoi-quy)
  - [Test đặc trưng (characterization) phải có TRƯỚC khi đổi hành vi](#test-dac-trung-characterization-phai-co-truoc-khi-doi-hanh-vi)
  - [Dữ liệu cũ phải còn đọc được](#du-lieu-cu-phai-con-doc-duoc)

**Feature Branch**: `006-cross-platform-support` (tên thư mục feature; không tạo nhánh git mới)

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "Yêu cầu: Hỗ trợ đa nền tảng cho mma_ai (Windows là môi trường chính của người dùng; Linux/WSL2 và macOS phải tiếp tục/được hỗ trợ)." Nguồn: yêu cầu nhập trực tiếp ở lượt đặc tả gọn (không có tệp trong `docs/00-input/`); khảo sát hiện trạng: `docs/00-survey/mma-ai-cross-platform.md` (điểm neo F-001…F-011).

<a id="boi-canh-context"></a>
## Bối cảnh (Context)

Dự án MMA-AI-LAB (mô phỏng cơ–xương 3D, học tăng cường — RL) đã có mã và test cho M0–M1 (`001`…`005`), nhưng **chỉ được viết và kiểm trên Linux/WSL2 Ubuntu**. Khảo sát (`docs/00-survey/mma-ai-cross-platform.md`) và rà soát mã ở bước này cho thấy mã gắn POSIX ở nhiều chỗ: nhập `resource` vô điều kiện (không có trên Windows), đọc `ru_maxrss` theo đơn vị KiB của Linux (macOS trả byte), dò màn hình chỉ bằng `DISPLAY`/`WAYLAND_DISPLAY` (không tồn tại trên Windows/macOS), kiểm đường dẫn tuyệt đối chỉ bằng ký tự `/`, tìm Python của venv ở `bin/python` (Windows là `Scripts`), và bộ test dùng `resource.setrlimit`, `symlink_to` mà không kiểm năng lực. Chưa có `scripts/check_env.py`, hướng dẫn cài trên Windows hay CI nào.

Người dùng là **nhà nghiên cứu/kỹ sư dự án**, chạy mọi thứ qua dòng lệnh. Họ nói **Windows 11 là môi trường chính** (gốc hay WSL2 chưa rõ); Linux/WSL2 phải **tiếp tục** chạy và macOS phải **được hỗ trợ**. Nỗi đau hiện tại: trên Windows gốc, `python -m mma_ai.learning.cli` sập ngay khi nạp mô-đun đo tài nguyên; trên macOS, RAM đỉnh báo sai 1024 lần; viewer 3D bị chặn vì "không có `DISPLAY`" dù máy có màn hình; không có cách nhanh để biết máy mình đã cài đúng chưa.

Feature này **không thêm năng lực nghiệp vụ** nào cho M1: nó làm cho năng lực đã có chạy giống nhau trên ba hệ điều hành, thêm lớp tương thích (compatibility layer) cho các điểm gắn nền tảng, thêm lệnh kiểm môi trường, tài liệu cài đặt Windows và CI ma trận. Hành vi nghiệm thu của `001`…`005` **không đổi** trên Linux.

<a id="clarifications"></a>
## Clarifications

- Q: Giao diện quan sát (C-0009) thuộc phạm vi vì chính người dùng đã đưa vào phạm vi con 2; vì vậy không phải mở rộng phạm vi do agent tự thêm. Hình thức giao diện (TensorBoard + bảng điều khiển web nhẹ, MuJoCo Viewer đọc checkpoint mới nhất, hay cả hai) là quyết định kỹ thuật được yêu cầu giao cho bước plan — cần người dùng xác nhận phạm vi — Lý do → A: Đồng ý (người dùng, C-0010): giao diện quan sát training thuộc phạm vi con 2; hình thức (TensorBoard, dashboard web nhẹ, MuJoCo Viewer đọc checkpoint mới nhất, hoặc kết hợp) để bước plan quyết định, kèm lý do và chi phí đo được; chỉ-đọc, chạy tiến trình riêng, không kéo chậm vòng train. (người, Q-0001)
- Tự chốt: Ảnh hưởng của Q-0001 (thuộc `003-ppo-train-repro`) lên feature này → ranh giới: giao diện quan sát training (gồm cửa sổ 3D `monitoring/viewer3d.py`) vẫn thuộc con 2; feature này **chỉ** làm lớp phát hiện màn hình mà nó dùng chạy đúng trên Windows/macOS (F-004), không đổi hình thức, phạm vi hay hành vi chỉ-đọc của giao diện đó — lý do: yêu cầu đa nền tảng không đòi thêm giao diện; đổi hình thức giao diện sẽ là mở rộng phạm vi.
- Tự chốt: Yêu cầu gốc không đánh mã `AC-n`; sáu kết quả mong muốn đo được (a)–(f) ở mục 3 của yêu cầu được đánh mã **AC-1…AC-6 theo đúng thứ tự** — (a)→AC-1 (CLI chạy trên ba OS), (b)→AC-2 (đo RAM đỉnh), (c)→AC-3 (dò màn hình và viewer 3D), (d)→AC-4 (đường dẫn, ghi nguyên tử, symlink, UTF-8, xuống dòng), (e)→AC-5 (cài đặt tái lập và `scripts/check_env.py`), (f)→AC-6 (CI ma trận và test đánh dấu năng lực). Không gộp, không bỏ; mỗi AC có ít nhất một Acceptance Scenario ghi đúng mã và chép nguyên con số của yêu cầu — lý do: cổng đối chiếu mã/con số cần mã ổn định; thứ tự của yêu cầu là thứ tự duy nhất không gây tranh cãi.
- Tự chốt: "Windows gốc hay WSL2 là chính?" (yêu cầu mục 2 và 6 cho phép spec xử lý cả hai) → **cả hai đều là đích nghiệm thu, vai trò khác nhau** (người dùng đã xác nhận Windows native là môi trường chính — Q-0002, C-0036): *Windows gốc* (PowerShell/cmd, Python 3.11–3.12 của Windows) là đích tham chiếu mới và là nơi mọi thay đổi của feature phải được chứng minh; *WSL2* là môi trường **Linux** (cùng nhánh mã Linux) cộng một vài điều kiện riêng — nhận diện được là `wsl2` ở báo cáo môi trường, có thể không có màn hình (không WSLg) nên đường `--headless` phải chạy được, và cảnh báo khi thư mục run nằm trên ổ Windows gắn vào WSL2 — lý do: yêu cầu nói rõ "[KHÔNG BIẾT] … spec phải hỏi/xử lý cả hai"; hai môi trường dùng hai nhánh mã khác nhau nên bỏ một nhánh là bỏ một lớp người dùng.
- Tự chốt: "Có máy Windows để chạy CI/kiểm tay không?" → spec **không giả định** có máy Windows của nhóm: bằng chứng nghiệm thu đòi hỏi là **ô CI trên runner Windows do dịch vụ CI cung cấp** (AC-6); kiểm tay trên Windows 11 thật (viewer 3D có màn hình, CUDA) là bước người ghi ở `quickstart.md`, đánh dấu CHƯA KIỂM cho tới khi có lần chạy thật — lý do: CI ma trận do yêu cầu đòi (AC-6) là phương tiện duy nhất tự động hoá được; repo hiện **chưa có remote** nên chưa chạy được workflow thật ở máy phát triển (chỉ kiểm tĩnh cấu trúc).
- Tự chốt: "GPU trên Windows (CUDA) có bắt buộc?" → **không bắt buộc** (người dùng xác nhận CUDA tuỳ chọn, máy của họ có CUDA — Q-0002, C-0036): đường CPU là đường nghiệm thu bắt buộc trên cả ba OS; CUDA là tuỳ chọn có hướng dẫn và được `check_env` báo (có/không, tên GPU) — lý do: yêu cầu nêu "torch CPU/CUDA" như hai phương án cài đặt, và ngoài phạm vi có "GPU AMD/Metal"; CI trên runner thường không có GPU nên không thể bắt buộc.
- Tự chốt: "macOS cần hỗ trợ ở mức chạy hay chỉ không lỗi?" → **mức chạy** (người dùng xác nhận macOS phải chạy tốt — Q-0002, C-0036) cho đường CPU trên Apple Silicon (arm64): train, evaluate, replay/demo `--headless`, benchmark chạy và bộ test chạy trong CI; viewer 3D chạy khi có màn hình **qua `mjpython`** (ràng buộc của MuJoCo trên macOS, xem nguồn ở research Q4); macOS Intel (x86_64) không thuộc cấu hình đã kiểm vì `uv.lock` không có wheel `torch` cho nó — lý do: yêu cầu (a) đòi "chạy được … macOS"; dải wheel trong khoá là bằng chứng đo được cho phạm vi hỗ trợ.
- Tự chốt: Quy ước đơn vị RAM → giữ nguyên **`ram_peak_mb` tính bằng MiB (1 MB := 1 048 576 byte)** như hiện nay (Linux: `ru_maxrss` KiB ÷ 1024); macOS: byte ÷ 1 048 576; Windows: `PeakWorkingSetSize` (byte) ÷ 1 048 576; không đo được thì `null` tường minh — lý do: không đổi khuôn hồ sơ run (không đổi dữ liệu cũ); đơn vị gốc mỗi OS do yêu cầu (b) nêu.
- Tự chốt: Mâu thuẫn giữa hiến chương II ("KHÔNG thêm mới cơ chế bỏ qua: skip, xfail") và yêu cầu (f) ("test cần GPU/màn hình được đánh dấu và bỏ qua có chủ đích, không xfail/skip để che lỗi") → **hiến chương thắng**: test cần năng lực được gắn dấu năng lực (capability marker) và bị **loại khỏi bộ chạy khi thu thập (deselect)** nếu máy không có năng lực đó, kèm danh sách và lý do in ra báo cáo; **không** thêm `pytest.skip`, `skipif`, `xfail` hay `importorskip` mới — lý do: loại có điều kiện và có báo cáo là "bỏ qua có chủ đích" mà vẫn không che lỗi (INV-006); các `xfail`/`importorskip` đã có từ trước giữ nguyên nghĩa, không sửa trong feature này.
- Tự chốt: Phạm vi các CLI cần chạy trên ba OS (AC-1): mọi CLI `python -m mma_ai…` tồn tại ở thời điểm thi công — train (`mma_ai.learning.cli`), benchmark (`mma_ai.learning.benchmark`), so sánh run (`mma_ai.learning.compare_cli`), quan sát (`mma_ai.monitoring.cli`), evaluate (`mma_ai.evaluation`) và replay/demo (`mma_ai.visualization`). Các tệp evaluate/replay hiện đang bị xoá ở trạng thái staged trong cây làm việc dùng chung (do vai khác); feature này **không khôi phục hay sửa** chúng ở lượt đặc tả, chỉ đòi chúng chạy được trên ba OS khi tồn tại ở nhánh tích hợp — lý do: hiến chương III (vùng ghi từng vai); AC-1 nói "train, evaluate, replay/demo, benchmark" nên không thể bỏ chúng khỏi tiêu chí.
- Tự chốt: Ma trận CI → **ba OS × hai phiên bản Python (3.11, 3.12) = 6 ô**; nhà cung cấp CI là GitHub Actions với runner Linux/macOS/Windows do dịch vụ cung cấp — lý do: yêu cầu ràng buộc "Python 3.11–3.12" và đòi ma trận ba OS; GitHub Actions có sẵn runner cả ba OS mà nhóm không phải tự dựng hạ tầng; đổi nhà cung cấp chỉ đổi tệp cấu hình, không đổi tiêu chí.
- Tự chốt: Các con số ngưỡng của NFR (sai số RAM [0,9 ; 1,3], thời gian dò màn hình ≤ 5 s, thử lại ghi ≤ 5 lần/≤ 1,0 s, tỷ lệ test bị loại ≤ 5%, `check_env` ≤ 30 s) → là **giá trị đề xuất đo được**, lấy từ: số đo Linux đã chạy ở bước này (cấp phát 256 MiB đã chạm ⇒ đỉnh RAM tăng 256,02 MiB), ngưỡng đã có của `005` (5 s), và ngân sách CI; riêng trên Windows/macOS chúng CHƯA KIỂM bằng máy thật — lý do: master plan XI.10 cấm giả định về phần cứng chưa đo; nên ngưỡng được kiểm trong CI và hiệu chỉnh bằng một thay đổi tên riêng nếu số đo thật khác.
- Q: Mọi mục thêm ở bước này đều **dẫn xuất trực tiếp từ một trong sáu kết quả (a)–(f)**, không phải mở rộng phạm vi: ép UTF-8 cho đầu ra chuẩn, spawn của multiprocessing, tìm Python của venv theo OS (verify_clean_install), kiểm đường dẫn tuyệt đối theo mọi OS và .gitattributes đặt xuống dòng LF thuộc (a)/(d); khai báo năng lực (symlink, đường dẫn dài) thuộc (d)/(e)/(f); các Key Entity là mô hình hoá của "lớp tương thích", "báo cáo check_env" và "CI ma trận" mà yêu cầu nêu tên — cần người dùng xác nhận phạm vi — Lý do → A: Đồng ý (người dùng, C-0036): các mục thêm đều dẫn xuất từ (a)–(f), thuộc phạm vi Trong theo Default proposal. Xác nhận kèm: Windows native là môi trường chính, CUDA tuỳ chọn (máy người dùng có CUDA), macOS phải chạy tốt. (người, Q-0002)
- Kết luận phân loại: rà các điểm mơ hồ còn lại, không điểm nào đủ cả ba điều kiện (quyết định nghiệp vụ của người dùng · không có tập quán ngành · sai thì đắt) và không có quyết định mở rộng phạm vi do agent tự thêm; bốn câu hỏi [KHÔNG BIẾT] của yêu cầu (mục 6) đã được xử lý ở các dòng trên; nên không có điểm nào cần dừng chờ người trả lời; điểm xác nhận phạm vi duy nhất còn lại (Q-0002) đã được người dùng trả lời ở dòng `Q:` phía trên và không còn dấu chờ nào trong tệp này.

<a id="user-scenarios-testing-mandatory"></a>
## User Scenarios & Testing *(mandatory)*

<a id="user-story-1-chay-train-evaluate-replaydemo-benchmark-bang-python-m-mma-ai-tren-windows-goc-linux-va-macos-priority-p1"></a>
### User Story 1 - Chạy train, evaluate, replay/demo, benchmark bằng `python -m mma_ai…` trên Windows gốc, Linux và macOS (Priority: P1)

**Tần suất**: hằng ngày — nhà nghiên cứu/kỹ sư chạy các lệnh này nhiều lần mỗi ngày (khoảng 5–20 lần), phần lớn trên Windows 11.

Người dùng mở terminal trên Windows 11 (PowerShell), kích hoạt môi trường, chạy `python -m mma_ai.learning.cli …` (train), `python -m mma_ai.evaluation…` (evaluate), `python -m mma_ai.visualization…` (replay/demo), `python -m mma_ai.learning.benchmark …`. Mỗi lệnh chạy trọn như trên Linux và cho cùng mã thoát, cùng khuôn đầu ra.

**Why this priority**: AC-1 là lý do tồn tại của feature; hiện trên Windows gốc lệnh train sập ngay khi nạp mô-đun đo tài nguyên.

**Independent Test**: Trên mỗi OS, chạy từng lệnh với cấu hình smoke; so mã thoát, khoá JSON của `manifest`/báo cáo với kết quả trên Linux.

**Acceptance Scenarios**:

1. **Given** Windows 11 gốc đã cài môi trường theo hướng dẫn, **When** chạy `python -m mma_ai.learning.cli` với cấu hình smoke, **Then** lệnh không lỗi nhập mô-đun, huấn luyện xong, ghi `manifest.json` hợp khuôn và thoát mã 0. (AC-1)
2. **Given** cùng cấu hình smoke và cùng seed trên Windows gốc, Linux và macOS, **When** chạy train, evaluate, replay/demo `--headless` và benchmark, **Then** mỗi lệnh thoát cùng mã như trên Linux và đầu ra có cùng tập khoá và cùng kiểu dữ liệu (chỉ các trường nền tảng tường minh như tên OS và đơn vị đo thực được phép khác). (AC-1)
3. **Given** mọi mô-đun `mma_ai.*`, **When** nhập từng mô-đun trên Windows gốc, Linux và macOS, **Then** 0 mô-đun lỗi nhập vì thiếu thư viện chỉ có ở một OS (ví dụ `resource`). (AC-1)
4. **Given** chạy ở Windows hoặc macOS, nơi tiến trình con được tạo bằng `spawn`, **When** train sinh tiến trình giao diện quan sát và tiến trình viewer 3D, **Then** các tiến trình con khởi động được và kết thúc gọn khi train xong hoặc bị ngắt. (AC-1)
5. **Given** Linux (kể cả WSL2), **When** chạy toàn bộ test M0–M1 hiện có, **Then** 100% test đang xanh vẫn xanh và số test thu thập không giảm. (AC-1)

---

<a id="user-story-2-ram-dinh-duoc-do-dung-don-vi-tren-ca-ba-he-dieu-hanh-priority-p1"></a>
### User Story 2 - RAM đỉnh được đo đúng đơn vị trên cả ba hệ điều hành (Priority: P1)

**Tần suất**: hằng ngày — mỗi lần train ghi một hồ sơ run có `ram_peak_mb`, khoảng 5–20 lần mỗi ngày.

Mô-đun `mma_ai.learning.resources` không còn `import resource` vô điều kiện. `ram_peak_mb` trong hồ sơ run là số MiB đúng trên Linux (KiB), macOS (byte) và Windows (API riêng).

**Why this priority**: AC-2; là nguyên nhân sập trực tiếp trên Windows (F-001) và gây số sai 1024 lần trên macOS.

**Independent Test**: Test đơn vị tiêm giá trị gốc của từng OS vào hàm quy đổi và kiểm kết quả; test thật cấp phát 256 MiB đã chạm và kiểm mức tăng của đỉnh RAM.

**Acceptance Scenarios**:

1. **Given** Windows gốc (không có mô-đun `resource`), **When** nhập `mma_ai.learning.resources` và gọi `collect_resources()`, **Then** không có `ImportError`, và `ram_peak_mb` là số dương lấy từ API đo bộ nhớ riêng của Windows (đỉnh working set), hoặc `null` nếu API thất bại — không bao giờ là số ước lượng. (AC-2)
2. **Given** giá trị gốc `ru_maxrss` = 262 144 trên Linux (đơn vị KiB), **When** quy đổi, **Then** `ram_peak_mb` = 256,0 MB (sai số ≤ 0,001). (AC-2)
3. **Given** giá trị gốc `ru_maxrss` = 268 435 456 trên macOS (đơn vị byte), **When** quy đổi, **Then** `ram_peak_mb` = 256,0 MB (sai số ≤ 0,001) — không phải 262 144 MB. (AC-2)
4. **Given** giá trị gốc đỉnh working set = 268 435 456 byte trên Windows, **When** quy đổi, **Then** `ram_peak_mb` = 256,0 MB (sai số ≤ 0,001). (AC-2)
5. **Given** một tiến trình cấp phát và chạm 256 MiB bộ nhớ, **When** đo `ram_peak_mb` trước và sau, **Then** mức tăng nằm trong [230,4 ; 332,8] MB trên Windows gốc, Linux và macOS. (AC-2)
6. **Given** `build_manifest` được gọi mà không truyền hồ sơ tài nguyên, **When** nó tự thu tài nguyên (F-002), **Then** `manifest.json` trên cả ba OS có trường `ram_peak_mb` và khuôn hồ sơ không đổi so với trước. (AC-2)

---

<a id="user-story-3-do-man-hinh-theo-tung-os-de-viewer-3d-mujoco-chay-khi-co-man-hinh-priority-p1"></a>
### User Story 3 - Dò màn hình theo từng OS để viewer 3D MuJoCo chạy khi có màn hình (Priority: P1)

**Tần suất**: hằng ngày — nhà nghiên cứu mở viewer 3D (cửa sổ quan sát train, replay/demo) khoảng 2–6 lần mỗi ngày, chủ yếu trên Windows 11.

Việc "có màn hình hay không" được quyết định bằng một phép dò theo OS: Linux/WSL2 xét `DISPLAY`/`WAYLAND_DISPLAY` rồi thử khởi tạo GLFW; Windows/macOS **không** đọc hai biến đó mà dò bằng chính GLFW. Cả ba nơi đang tự dò (F-003, F-004, F-005) dùng chung kết quả.

**Why this priority**: AC-3; hiện trên Windows/macOS viewer train và benchmark luôn báo "không có màn hình" dù máy có màn hình.

**Independent Test**: Test đơn vị tiêm hồ sơ nền tảng giả (windows/macos/linux/wsl2) và kết quả GLFW giả; test thật chạy phép dò trên từng OS và đo thời gian.

**Acceptance Scenarios**:

1. **Given** Windows hoặc macOS có màn hình và **không** đặt `DISPLAY`/`WAYLAND_DISPLAY`, **When** gọi phép dò màn hình, **Then** kết quả là khả dụng và viewer 3D được phép mở. (AC-3)
2. **Given** Windows hoặc macOS **không** có màn hình khởi tạo được (GLFW không khởi tạo được hoặc không có màn hình chính), **When** gọi phép dò, **Then** kết quả là không khả dụng kèm lý do tiếng Việt nêu rõ và gợi ý `--headless`, hoàn tất trong ≤ 5 s, không treo. (AC-3)
3. **Given** Windows hoặc macOS có `DISPLAY=:99` đặt lung tung nhưng màn hình thật hoạt động, **When** dò, **Then** biến đó bị bỏ qua và kết quả vẫn là khả dụng. (AC-3)
4. **Given** Linux hoặc WSL2 và cả `DISPLAY` lẫn `WAYLAND_DISPLAY` đều bỏ đặt, **When** dò, **Then** kết quả là không khả dụng nêu cả hai biến (hành vi hiện có không đổi). (AC-3)
5. **Given** cùng một máy, **When** so kết quả của `display_available()` (replay), `View3D.has_display()` (quan sát train) và `evaluate_view3d_status()` (benchmark), **Then** cả ba cho cùng kết luận có/không có màn hình. (AC-3)
6. **Given** máy có màn hình, **When** chạy replay/demo hoặc viewer quan sát train, **Then** cửa sổ MuJoCo Viewer mở và phát được; trên macOS điều này yêu cầu chạy bằng `mjpython` — nếu chạy bằng `python` thường, lệnh báo lỗi tiếng Việt nêu cách chạy bằng `mjpython`, thoát mã khác 0 và không treo. (AC-3)
7. **Given** không có màn hình và có `--headless`, **When** chạy replay/demo, **Then** đường không màn hình chạy xong mã 0 trên cả ba OS mà không nạp GLFW hay viewer. (AC-3)

---

<a id="user-story-4-duong-dan-ghi-tep-nguyen-tu-symlink-utf-8-va-xuong-dong-hoat-dong-tren-ca-ba-os-priority-p1"></a>
### User Story 4 - Đường dẫn, ghi tệp nguyên tử, symlink, UTF-8 và xuống dòng hoạt động trên cả ba OS (Priority: P1)

**Tần suất**: hằng ngày — mọi lần train/evaluate/replay đều ghi checkpoint, manifest, báo cáo, episode; khoảng 5–20 lần mỗi ngày.

Mọi tệp do hệ thống ghi nguyên tử (`os.replace`) kể cả khi Windows giữ khoá tạm thời; đường dẫn tuyệt đối bị từ chối theo mọi dạng của cả hai họ OS; dữ liệu ghi ra là UTF-8 và xuống dòng LF như nhau trên ba OS; tiếng Việt in ra console/pipe không làm sập lệnh; năng lực symlink được kiểm thay vì giả định.

**Why this priority**: AC-4; các tệp này là bằng chứng tái lập của M1 — một bản ghi dở dang hoặc khác byte giữa các OS làm hỏng đối chiếu.

**Independent Test**: Test tiêm lỗi (đích đang mở, hết quyền ghi, ngắt giữa chừng), test quét byte `\r` trong tệp đã ghi, chạy CLI với `PYTHONIOENCODING=cp1252`, và test năng lực symlink.

**Acceptance Scenarios**:

1. **Given** tệp đích `manifest.json` đang được một tiến trình khác giữ mở trên Windows (không cho thay thế), **When** ghi manifest mới, **Then** hệ thống thử lại tối đa 5 lần trong tổng ≤ 1,0 s; nếu vẫn không được thì báo lỗi tiếng Việt nêu đường dẫn đích và nguyên nhân, **bản cũ giữ nguyên từng byte** và không còn tệp tạm. (AC-4)
2. **Given** ghi checkpoint, manifest, tiến độ, báo cáo benchmark và episode, **When** quá trình bị ngắt hoặc thay thế thất bại ở bất kỳ bước nào, **Then** tệp đích hoặc là bản cũ đầy đủ hoặc là bản mới đầy đủ, không bao giờ là bản dở dang, trên cả ba OS. (AC-4)
3. **Given** các giá trị cấu hình đường dẫn (ví dụ `paths.runs_dir`), **When** truyền năm dạng tuyệt đối: bắt đầu bằng `/`, bắt đầu bằng `\`, dạng UNC (hai dấu `\` đầu), ổ đĩa kèm `\`, và ổ đĩa không kèm dấu phân cách (kiểu `X:ten`), **Then** 5/5 dạng bị từ chối với lỗi cấu hình tiếng Việt nêu giá trị, trên cả ba OS (kiểm theo luật chứ không theo OS đang chạy). (AC-4)
4. **Given** bản ghi hồ sơ (manifest, episode, tóm tắt) có trường đường dẫn, **When** sinh trên Windows, **Then** mọi đường dẫn là tương đối và dùng dấu `/`, không có `\` và không có ký tự ổ đĩa. (AC-4)
5. **Given** ghi manifest, jsonl chỉ số, tiến độ và báo cáo có chuỗi tiếng Việt (ví dụ "Cánh tay duỗi tới mục tiêu"), **When** đọc lại byte thô trên Windows gốc, Linux và macOS, **Then** tệp là UTF-8 không BOM, 0 byte `\r`, và nội dung giống hệt nhau từng byte với cùng đầu vào. (AC-4)
6. **Given** đầu ra chuẩn được chuyển hướng sang pipe/tệp với bảng mã không phải UTF-8 (mô phỏng bằng `PYTHONIOENCODING=cp1252`), **When** mọi lệnh `python -m mma_ai…` in thông báo tiếng Việt, **Then** 0 lần `UnicodeEncodeError` và đầu ra giải mã đúng bằng UTF-8. (AC-4)
7. **Given** máy không có quyền tạo symlink (Windows không bật Developer Mode, không phải quản trị), **When** chạy mã sản phẩm và bộ test, **Then** mã sản phẩm không phụ thuộc symlink; test cần symlink được loại có báo cáo và lý do; ở máy có quyền, các test đó chạy và xanh. (AC-4)
8. **Given** thư mục run nằm trong cây có đường dẫn dài hơn giới hạn 260 ký tự của Windows khi chưa bật đường dẫn dài, **When** tạo run hoặc ghi checkpoint, **Then** lỗi nêu độ dài đường dẫn và gợi ý (bật đường dẫn dài hoặc rút ngắn thư mục gốc), không tạo cấu trúc dở dang. (AC-4)

---

<a id="user-story-5-cai-dat-tai-lap-tren-windows-bang-uvpip-va-kiem-moi-truong-bang-scriptscheck-envpy-priority-p1"></a>
### User Story 5 - Cài đặt tái lập trên Windows bằng uv/pip và kiểm môi trường bằng `scripts/check_env.py` (Priority: P1)

**Tần suất**: hiếm — mỗi máy mới hoặc mỗi lần đổi phụ thuộc, khoảng 1 lần mỗi vài tuần; `check_env` thêm khi gặp lỗi lạ (hằng tuần khi triển khai).

Người dùng làm theo tài liệu cài đặt Windows (uv hoặc pip; torch CPU hoặc CUDA; mujoco; myo-sim) và chạy `python scripts/check_env.py`; lệnh báo đúng OS (windows/linux/wsl2/macos), phiên bản Python và các gói, thiết bị torch, năng lực màn hình/symlink/đường dẫn dài/đo RAM/UTF-8, và thoát mã 0 khi đủ điều kiện chạy.

**Why this priority**: AC-5; không có cách cài và kiểm thì ba OS chỉ tồn tại trên giấy.

**Independent Test**: Chạy `scripts/check_env.py --json` trên từng OS và hợp schema; chạy với hồ sơ OS giả; chạy với Python ngoài khoảng và gói thiếu.

**Acceptance Scenarios**:

1. **Given** máy Windows 11 mới có Python 3.11 hoặc 3.12 và uv, **When** làm đúng các lệnh trong tài liệu cài đặt (cài phụ thuộc cơ sở, tuỳ chọn extra `rl` cho torch CPU), **Then** môi trường được dựng từ `uv.lock` không lỗi giải quyết phụ thuộc và `python scripts/check_env.py` thoát mã 0. (AC-5)
2. **Given** môi trường đã cài, **When** chạy `python scripts/check_env.py --json`, **Then** đầu ra là một JSON hợp khuôn báo cáo môi trường với `os.kind` ∈ {`windows`, `linux`, `wsl2`, `macos`} đúng với máy đang chạy. (AC-5)
3. **Given** WSL2 Ubuntu, **When** chạy `check_env`, **Then** `os.kind` là `wsl2` (không phải `linux`) và, nếu `DISPLAY`/`WAYLAND_DISPLAY` chưa đặt, năng lực màn hình là không khả dụng kèm gợi ý `--headless` nhưng lệnh vẫn thoát mã 0. (AC-5)
4. **Given** Python 3.13 hoặc 3.10, hoặc thiếu `mujoco`/`myo-sim`, **When** chạy `check_env`, **Then** lệnh thoát mã khác 0 với thông báo tiếng Việt nêu gói/phiên bản thiếu và khoảng yêu cầu 3.11–3.12. (AC-5)
5. **Given** chưa cài extra `rl` (không có torch), **When** chạy `check_env`, **Then** `torch` là `null` với cảnh báo "không train được", không phải lỗi, mã thoát 0. (AC-5)
6. **Given** máy có GPU NVIDIA và đã cài torch CUDA theo tài liệu, **When** chạy `check_env`, **Then** `torch_device.kind` = `cuda` kèm tên GPU; máy không có GPU thì `cpu` và vẫn mã 0 — CUDA không bắt buộc. (AC-5)
7. **Given** tài liệu cài đặt, **When** đọc, **Then** có đủ hướng dẫn cho Windows gốc (uv và pip), WSL2 và macOS, nêu cách chọn torch CPU/CUDA, cách chạy viewer 3D trên macOS bằng `mjpython`, và mọi đường dẫn trong đó là tương đối. (AC-5)

---

<a id="user-story-6-ci-ma-tran-linuxmacoswindows-va-test-danh-dau-nang-luc-priority-p2"></a>
### User Story 6 - CI ma trận Linux/macOS/Windows và test đánh dấu năng lực (Priority: P2)

**Tần suất**: hằng ngày — mỗi lần đẩy thay đổi lên nhánh tích hợp (khoảng 3–10 lần mỗi ngày) do kỹ sư dự án; người xem kết quả là maintainer.

Mỗi lần đẩy mã, CI chạy ma trận ba OS × Python 3.11/3.12: dựng môi trường từ `uv.lock`, chạy `check_env`, rồi bộ test. Test cần GPU/màn hình/symlink/OS riêng mang dấu năng lực và bị loại có báo cáo khi máy thiếu năng lực đó; không có `xfail`/`skip` nào được thêm để che lỗi.

**Why this priority**: AC-6; là cách duy nhất ngăn thụt lùi đa nền tảng, nhưng hoãn được sau khi mã chạy (P1).

**Independent Test**: Kiểm tĩnh tệp workflow (ma trận, bước, lệnh); chạy bộ test với năng lực giả để kiểm cơ chế loại; quét diff tìm `skip`/`xfail` mới.

**Acceptance Scenarios**:

1. **Given** tệp cấu hình CI, **When** đọc ma trận, **Then** có đủ 6 ô: {Linux, macOS, Windows} × {Python 3.11, Python 3.12}, mỗi ô chạy `check_env` rồi toàn bộ test (trừ test cần năng lực bị loại). (AC-6)
2. **Given** một ô CI không có màn hình/GPU, **When** chạy test, **Then** các test mang dấu `requires_display`/`requires_cuda` bị **loại khi thu thập** (không phải skip), danh sách và lý do từng test in ở báo cáo cuối, và số bị loại ≤ 5% số test thu thập. (AC-6)
3. **Given** một test mang dấu năng lực nhưng không nêu lý do, **When** thu thập, **Then** bộ test thất bại ngay ở bước thu thập (không loại im lặng). (AC-6)
4. **Given** diff của thay đổi, **When** quét, **Then** 0 `pytest.skip`, `skipif`, `xfail`, `importorskip` mới được thêm. (AC-6)
5. **Given** 6 ô CI, **When** chạy trên nhánh tích hợp, **Then** 6/6 ô xanh. (AC-6)
6. **Given** các test hiện dùng `resource.setrlimit` (F-015) và `symlink_to` (F-016), **When** chạy trên Windows, **Then** chúng không vỡ vì lỗi nền tảng: bị loại có báo cáo (không có năng lực tương ứng) chứ không đỏ và không bị `xfail`. (AC-6)

---

<a id="user-story-7-nguoi-dung-linux-wsl2-va-macos-khong-bi-doi-hanh-vi-priority-p2"></a>
### User Story 7 - Người dùng Linux, WSL2 và macOS không bị đổi hành vi (Priority: P2)

**Tần suất**: hằng ngày — mọi người dùng hiện có chạy các lệnh như trước, khoảng 5–20 lần mỗi ngày.

Người dùng Linux/WSL2 hiện tại không thấy khác biệt: cùng mã thoát, cùng đầu ra, cùng đơn vị RAM, cùng thông điệp lỗi. macOS có cùng hành vi như Linux ở mọi chỗ không gắn nền tảng.

**Why this priority**: Ràng buộc "không phá hành vi Linux hiện có" của yêu cầu; giá trị bảo vệ chứ không thêm năng lực.

**Independent Test**: Test đặc trưng (characterization) ghi hành vi Linux hiện tại **trước** khi sửa; chạy lại sau sửa; so mốc số test.

**Acceptance Scenarios**:

1. **Given** Linux, **When** chạy toàn bộ test M0–M1 sau thay đổi, **Then** mọi test xanh trước vẫn xanh và số test thu thập không giảm so với mốc trước thay đổi. (AC-1)
2. **Given** Linux với giá trị `ru_maxrss` bất kỳ, **When** quy đổi, **Then** kết quả bằng đúng công thức cũ (KiB ÷ 1024) — dữ liệu hồ sơ cũ vẫn đọc và so sánh được. (AC-2)
3. **Given** Linux có/không có `DISPLAY`, **When** dò màn hình, **Then** kết quả và lý do giống hệt trước thay đổi. (AC-3)
4. **Given** WSL2, **When** chạy `check_env` và train, **Then** nó dùng cùng nhánh mã Linux (không mã riêng cho WSL2 ngoài nhận diện và cảnh báo). (AC-5)

---

<a id="edge-cases"></a>
### Edge Cases

- Windows không đủ quyền tạo symlink: mã sản phẩm không dùng symlink; test cần symlink bị loại có lý do thay vì đỏ (AC-4).
- Đích JSON đang được tiến trình khác (hoặc phần mềm diệt virus/lập chỉ mục) giữ mở trên Windows nên `os.replace` ném lỗi quyền: thử lại có giới hạn rồi báo lỗi; bản cũ nguyên vẹn, tệp tạm được dọn (INV-003).
- Tệp tạm được tạo **cùng thư mục** với đích để thay thế không bắt qua hai ổ đĩa (Windows không `os.replace` xuyên ổ đĩa) (INV-003).
- Đường dẫn dài hơn 260 ký tự khi Windows chưa bật đường dẫn dài: lỗi nêu độ dài và gợi ý; `check_env` cảnh báo trước (AC-4).
- WSL2 mà thư mục run nằm trên ổ Windows gắn vào WSL2 (đường dẫn dưới thư mục gắn ổ): vẫn chạy nhưng `check_env` cảnh báo về hiệu năng và quyền tệp; không coi là lỗi (AC-5).
- WSL2 không có WSLg (không có `DISPLAY`/`WAYLAND_DISPLAY`): đường không màn hình phải chạy được và thông báo gợi ý `--headless` (INV-004).
- Windows ở phiên không có màn hình tương tác (chạy qua dịch vụ, SSH hoặc runner không giao diện): GLFW không khởi tạo được hoặc không có màn hình chính ⇒ không khả dụng, không treo (INV-004).
- macOS chạy viewer bằng `python` thường thay vì `mjpython`: lỗi tiếng Việt nêu cách chạy bằng `mjpython`, mã khác 0, không treo, không để cửa sổ dở dang (AC-3).
- macOS Intel (x86_64) hoặc Windows ARM64: không thuộc cấu hình đã kiểm vì khoá thiếu wheel `torch`; `check_env` báo "không thuộc cấu hình đã kiểm" chứ không giả vờ hỗ trợ (AC-5).
- Python ngoài khoảng 3.11–3.12 (3.10, 3.13): `check_env` thất bại nêu khoảng yêu cầu; không thử chạy tiếp (AC-5).
- Console Windows dùng bảng mã cũ hoặc đầu ra bị chuyển hướng sang pipe: tiếng Việt vẫn in được (AC-4).
- Cây mã được lấy về Windows với xuống dòng CRLF (cấu hình git tự đổi): các tệp YAML/JSON cấu hình vẫn đọc được; tệp do hệ thống ghi luôn LF (INV-005).
- Hệ tệp không phân biệt hoa/thường (Windows, macOS mặc định): tên tệp và thư mục do hệ thống sinh không có hai tên chỉ khác hoa/thường, và va chạm tên run vẫn được phát hiện bằng tạo thư mục loại trừ (INV-001).
- `multiprocessing` dùng `spawn` (Windows, macOS): hàm đích và đối số của tiến trình con phải nhập và tuần tự hoá (pickle) được; tiến trình con không chạy lại điểm vào chính (AC-1).
- Máy không đo được RAM đỉnh (API Windows thất bại): `ram_peak_mb` là `null` tường minh, không phải 0 và không ước lượng (INV-007).
- Phép dò màn hình gặp ngoại lệ lạ từ GLFW hoặc từ API hệ điều hành: coi là không khả dụng kèm lý do chứa chi tiết, không làm sập lệnh (INV-004).
- Test cần GPU trên máy không có CUDA, test cần màn hình trên máy không màn hình: bị loại có lý do, không đỏ, không skip, không xfail (INV-006).
- Hồ sơ run cũ (ghi trước thay đổi, `ram_peak_mb` theo MiB đúng công thức Linux) vẫn đọc được và so sánh được với hồ sơ mới (INV-007).

<a id="requirements-mandatory"></a>
## Requirements *(mandatory)*

<a id="functional-requirements"></a>
### Functional Requirements

- **FR-001**: Mọi CLI `python -m mma_ai…` của M0–M1 (train, evaluate, replay/demo, benchmark, so sánh run, quan sát) MUST chạy trọn và cho cùng mã thoát, cùng khuôn đầu ra trên Windows gốc, Linux (kể cả WSL2) và macOS Apple Silicon với cấu hình smoke; hành vi nghiệm thu của `001`…`005` MUST không đổi. (AC-1)
- **FR-002**: Hệ thống MUST có một lớp tương thích (compatibility layer) làm nơi **duy nhất** chứa mọi phân nhánh theo hệ điều hành; mã nghiệp vụ (`learning`, `evaluation`, `visualization`, `monitoring`, `environment`) MUST gọi lớp này thay vì tự kiểm `sys.platform` hay tự dò. Lớp này MUST nhận diện nền tảng thành một trong `windows`, `linux`, `wsl2`, `macos`. (AC-1, AC-3)
- **FR-003**: Không mô-đun `mma_ai.*` nào được nhập thư viện chỉ có ở một OS (ví dụ `resource`, `fcntl`, `msvcrt`, `winreg`) ở mức mô-đun; nhập chỉ xảy ra trong nhánh OS tương ứng, lười. Nhập từng mô-đun `mma_ai.*` MUST thành công trên cả ba OS. (AC-1, AC-2)
- **FR-004**: `mma_ai.learning.resources` MUST đo RAM đỉnh theo OS: Linux dùng `ru_maxrss` đơn vị KiB; macOS dùng `ru_maxrss` đơn vị byte; Windows dùng API riêng của Windows trả đỉnh working set (byte) mà không thêm phụ thuộc nặng. Kết quả MUST là `ram_peak_mb` tính bằng MiB; không đo được thì `null` tường minh. (AC-2)
- **FR-005**: Phép dò màn hình MUST là một hàm dùng chung theo OS: Linux/WSL2 xét `DISPLAY`/`WAYLAND_DISPLAY` rồi thử khởi tạo GLFW; Windows và macOS MUST NOT đọc `DISPLAY`/`WAYLAND_DISPLAY` mà dò bằng GLFW (khởi tạo được và có màn hình chính). Kết quả gồm cờ khả dụng và lý do tiếng Việt kèm gợi ý `--headless`; hoàn tất ≤ 5 s, không treo, ngoại lệ lạ coi là không khả dụng. (AC-3)
- **FR-006**: `display_available()`, `View3D.has_display()` và `evaluate_view3d_status()` MUST dùng chung phép dò của FR-005 và cho cùng kết luận; hành vi trên Linux MUST không đổi (cùng kết quả và cùng lý do với trước). (AC-3)
- **FR-007**: Viewer 3D MuJoCo (replay/demo và cửa sổ quan sát train) MUST mở được khi phép dò báo có màn hình trên Windows, Linux/WSL2 và macOS; trên macOS, khi không chạy bằng `mjpython`, hệ thống MUST báo lỗi tiếng Việt nêu cách chạy bằng `mjpython` và thoát mã khác 0 thay vì treo hay sập. (AC-3)
- **FR-008**: Đường không màn hình (`--headless`) MUST chạy xong trên cả ba OS mà không nạp GLFW hay viewer, kể cả khi thiếu thư viện hiển thị. (AC-3)
- **FR-009**: Mọi nơi ghi tệp dữ liệu (checkpoint `.pt`/`.meta`/`latest`, manifest, tiến độ, báo cáo benchmark, episode, `ui.json`, kết quả `verify_clean_install`) MUST ghi nguyên tử qua một cơ chế dùng chung: ghi tệp tạm cùng thư mục, `fsync` tệp, rồi `os.replace`; trên Windows MUST thử lại có giới hạn (tối đa 5 lần, tổng chờ ≤ 1,0 s) khi gặp lỗi quyền tạm thời, sau đó báo lỗi nêu đường dẫn đích; thất bại MUST giữ nguyên bản cũ và dọn tệp tạm. Hành vi trên Linux MUST không đổi. (AC-4)
- **FR-010**: Kiểm đường dẫn tuyệt đối trong cấu hình và bản ghi MUST nhận diện cả dạng POSIX và dạng Windows (bắt đầu `/` hoặc `\`, UNC, ổ đĩa kèm hoặc không kèm dấu phân cách) **bất kể OS đang chạy**; các chỗ đang chỉ kiểm bằng `/` hoặc cắt `/` ở đầu MUST được thay bằng luật này. (AC-4)
- **FR-011**: Đường dẫn ghi vào hồ sơ run, manifest, episode và tóm tắt MUST là tương đối và dùng dấu `/` trên mọi OS. (AC-4)
- **FR-012**: Mọi thao tác đọc/ghi văn bản MUST chỉ định rõ `encoding="utf-8"` (không BOM) và mọi tệp văn bản do hệ thống ghi MUST dùng xuống dòng LF trên mọi OS (không dịch `\n` thành `\r\n`); đọc MUST chấp nhận cả LF và CRLF. (AC-4)
- **FR-013**: Mọi điểm vào `python -m mma_ai…` và `scripts/*.py` MUST đặt đầu ra chuẩn và đầu ra lỗi sang UTF-8 (thay ký tự không mã hoá được thay vì ném lỗi) ngay lúc khởi động, để thông báo tiếng Việt không làm sập lệnh khi bảng mã console/pipe không phải UTF-8. (AC-4)
- **FR-014**: Hệ thống MUST có phép kiểm năng lực symlink (thử tạo thật trong thư mục tạm) và phép kiểm hỗ trợ đường dẫn dài trên Windows; mã sản phẩm MUST NOT yêu cầu symlink. (AC-4, AC-6)
- **FR-015**: Tiến trình con tạo bằng `multiprocessing` (giao diện quan sát, viewer 3D) MUST khởi động và kết thúc đúng dưới phương thức `spawn` (mặc định của Windows và macOS): hàm đích ở cấp mô-đun, đối số tuần tự hoá được, điểm vào có bảo vệ `__main__`; hành vi Linux không đổi. (AC-1)
- **FR-016**: Công cụ xác minh cài đặt sạch (`verify_clean_install`) MUST tìm Python của môi trường ảo theo OS (thư mục `Scripts` của Windows, `bin` của Linux/macOS). (AC-1, AC-5)
- **FR-017**: Hệ thống MUST cung cấp `python scripts/check_env.py [--json]` báo: loại OS (`windows`/`linux`/`wsl2`/`macos`), phiên bản và kiến trúc, phiên bản Python và khoảng yêu cầu 3.11–3.12, phiên bản `mujoco`/`myo-sim`/`gymnasium`/`numpy`/`torch` (null nếu chưa cài), thiết bị torch (`cpu`/`cuda` + tên GPU), năng lực (màn hình, symlink, đường dẫn dài, đo RAM, UTF-8 đầu ra), và từng phép kiểm `ok`/`warn`/`fail`; thoát 0 khi không có `fail`, khác 0 khi có; thông báo tiếng Việt; đầu ra `--json` hợp khuôn máy đọc được. (AC-5)
- **FR-018**: Hệ thống MUST có tài liệu cài đặt cho Windows gốc (uv và pip), WSL2 và macOS: dựng môi trường từ khoá phụ thuộc, chọn torch CPU hay CUDA, chạy `check_env`, chạy viewer 3D (kể cả `mjpython` trên macOS), xử lý quyền symlink và đường dẫn dài trên Windows; mọi lệnh trong tài liệu phải chạy được trên đúng OS nó nêu. (AC-5)
- **FR-019**: Phụ thuộc MUST giữ Python `>=3.11,<3.13`, không thêm phụ thuộc nặng; khoá `uv.lock` MUST giải quyết được cho Windows, Linux và macOS Apple Silicon. (AC-5)
- **FR-020**: Hệ thống MUST có tệp cấu hình CI chạy ma trận {Linux, macOS, Windows} × {Python 3.11, Python 3.12}: dựng môi trường từ `uv.lock`, chạy `check_env`, chạy bộ test, in danh sách test bị loại theo năng lực. (AC-6)
- **FR-021**: Hệ thống MUST có bộ dấu năng lực (capability marker) cho test — tối thiểu `requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `posix_only`, `linux_only` (dấu `display` hiện có giữ nguyên nghĩa) — và cơ chế **loại khi thu thập** các test mà máy thiếu năng lực; mỗi dấu MUST kèm lý do, thiếu lý do là lỗi thu thập; việc loại MUST được báo cáo (tên test, lý do); MUST NOT dùng `skip`/`skipif`/`xfail`. (AC-6)
- **FR-022**: Các test hiện có gắn nền tảng (`import resource` + `setrlimit`, `symlink_to`, dò màn hình bằng biến môi trường, kỳ vọng "không có màn hình" của `display_available()`) MUST được sửa để chạy đúng trên ba OS bằng dấu năng lực hoặc bằng tiêm hồ sơ nền tảng giả — không đổi nghĩa khẳng định gốc; bộ cách ly biến môi trường của test MUST xử lý phép dò theo OS chứ không chỉ xoá `DISPLAY`/`WAYLAND_DISPLAY`. (AC-6)
- **FR-023**: Hệ thống MUST có bộ test tự động cho: nhận diện nền tảng (bốn loại), quy đổi RAM theo từng OS, phép dò màn hình theo OS, ghi nguyên tử (kể cả tiêm lỗi), kiểm đường dẫn tuyệt đối năm dạng, UTF-8/LF, ép UTF-8 đầu ra, năng lực symlink, `spawn`, `check_env` (khuôn + OS + lỗi), cơ chế loại theo năng lực, tệp CI, và nhập mọi mô-đun; test theo nhánh OS MUST chạy được ở mọi OS bằng hồ sơ nền tảng giả, và test thật theo OS chạy trên ô CI tương ứng. (AC-1, AC-2, AC-3, AC-4, AC-5, AC-6)
- **FR-024**: Mọi lỗi và thông báo hướng tới người dùng MUST bằng tiếng Việt, nêu giá trị và ngữ cảnh (đường dẫn, OS, phiên bản); đường dẫn trong tài liệu, báo cáo `check_env` và bản ghi MUST là tương đối hoặc không chứa thư mục riêng của máy. (AC-4, AC-5)

<a id="yeu-cau-phi-chuc-nang-non-functional-requirements"></a>
### Yêu cầu phi chức năng (Non-Functional Requirements)

- **NFR-PARITY-001**: Không thụt lùi hành vi Linux và không che lỗi bằng test.
  Ngưỡng: 0 test M0–M1 đang xanh chuyển đỏ trên Linux; số test thu thập (lệnh `test_count_command` của `.ai/profile.yml`) không nhỏ hơn mốc trước thay đổi; 0 `pytest.skip`/`skipif`/`xfail`/`importorskip` mới trong diff.
  Đo bằng: `uv run --isolated --with pytest pytest -q -p no:cacheprovider --ignore=tests/e2e` và `test_count_command`; test quét diff (`test_no_new_skip_xfail`). (AC-1, AC-6)
- **NFR-RAM-001**: Độ đúng của RAM đỉnh trên ba OS.
  Ngưỡng: quy đổi giá trị gốc 262 144 KiB (Linux), 268 435 456 byte (macOS), 268 435 456 byte (Windows) đều cho 256,0 MB với sai số ≤ 0,001 (3/3); đo thật khi cấp phát và chạm 256 MiB: mức tăng `ram_peak_mb` ∈ [230,4 ; 332,8] MB (tức [0,9 ; 1,3] × 256) trên 3/3 hệ điều hành.
  Đo bằng: `python -m pytest tests/unit/test_compat_memory.py` (tiêm giá trị gốc) và test thật chạy trên từng ô CI. (AC-2)
- **NFR-DISPLAY-001**: Phép dò màn hình không treo.
  Ngưỡng: phép dò hoàn tất ≤ 5 s trên 100% lần chạy ở cả ba OS, kể cả khi không có màn hình, `DISPLAY` hỏng hoặc GLFW ném ngoại lệ; 0 lần treo.
  Đo bằng: `python -m pytest tests/unit/test_compat_display.py` (đo thời gian, đồng hồ thật) và ô CI từng OS. (AC-3)
- **NFR-IO-001**: Ghi nguyên tử bền khi lỗi.
  Ngưỡng: trong 4 ca tiêm lỗi (đích đang bị giữ mở, thư mục đích không ghi được, ngắt giữa chừng sau khi ghi tệp tạm, `os.replace` thất bại) đích giữ nguyên từng byte và 0 tệp tạm còn lại ở 4/4 ca; thử lại ≤ 5 lần với tổng chờ ≤ 1,0 s trước khi báo lỗi.
  Đo bằng: `python -m pytest tests/unit/test_compat_fsio.py` và test tích hợp trên ô CI Windows. (AC-4)
- **NFR-ENC-001**: Dữ liệu và đầu ra di động.
  Ngưỡng: 0 byte `\r` và 0 BOM trong mọi tệp JSON/JSONL/YAML/Markdown do hệ thống ghi; 100% các tệp đó là UTF-8 hợp lệ; chạy mọi CLI với `PYTHONIOENCODING=cp1252` cho 0 `UnicodeEncodeError`; cùng đầu vào cho tệp giống hệt từng byte giữa ba OS.
  Đo bằng: `python -m pytest tests/integration/test_cross_platform_cli_utf8.py tests/unit/test_compat_fsio.py`. (AC-4)
- **NFR-ENV-001**: `check_env` nhanh và đúng khuôn.
  Ngưỡng: `scripts/check_env.py` thoát ≤ 30 s; `--json` hợp khuôn `check-env-report.schema.json` trong 100% ca thử; `os.kind` đúng ở 4/4 hồ sơ OS giả lập và ở 1/1 OS thật của mỗi ô CI.
  Đo bằng: `python -m pytest tests/unit/test_env_report.py tests/integration/test_check_env_cli.py` và ô CI. (AC-5)
- **NFR-CI-001**: CI ma trận đủ và xanh.
  Ngưỡng: ma trận có đúng 6 ô (3 OS × Python 3.11, 3.12); 6/6 ô xanh trên nhánh tích hợp; số test bị loại theo năng lực ≤ 5% số test thu thập trên mỗi ô và 100% test bị loại có lý do trong báo cáo.
  Đo bằng: `python -m pytest tests/integration/test_ci_workflow.py` (kiểm tĩnh ma trận) và kết quả chạy của dịch vụ CI. (AC-6)

<a id="bat-bien-invariants"></a>
### Bất biến (Invariants)

- **INV-001**: Cùng đầu vào hợp lệ MUST cho cùng mã thoát, cùng tập khoá và kiểu của đầu ra, cùng thông điệp nghiệp vụ trên Windows, Linux (kể cả WSL2) và macOS; chỉ các trường nền tảng tường minh (tên OS, đơn vị đo thực) được khác; tên tệp/thư mục do hệ thống sinh MUST không phụ thuộc phân biệt hoa/thường. (AC-1)
- **INV-002**: Nhập (`import`) mọi mô-đun `mma_ai.*` MUST thành công trên mọi OS được hỗ trợ và MUST NOT nạp thư viện chỉ có ở một OS ở mức mô-đun. (AC-1, AC-2)
- **INV-003**: Tệp đích của mọi lần ghi dữ liệu MUST hoặc là bản cũ nguyên vẹn hoặc là bản mới đầy đủ; thất bại MUST giữ bản cũ, dọn tệp tạm và nêu ngữ cảnh; tệp tạm MUST nằm cùng thư mục với đích. (AC-4)
- **INV-004**: Khi không xác định được một năng lực (màn hình, symlink, đường dẫn dài, API đo RAM), hệ thống MUST coi là KHÔNG khả dụng kèm lý do tiếng Việt, MUST NOT treo, MUST NOT mở cửa sổ/viewer nửa vời. (AC-3, AC-4)
- **INV-005**: Tệp văn bản do hệ thống ghi MUST là UTF-8 không BOM, xuống dòng LF; đường dẫn trong bản ghi MUST tương đối và dùng `/`; cùng nội dung ⇒ cùng byte trên mọi OS. (AC-4)
- **INV-006**: Không che lỗi bằng test: MUST NOT thêm `skip`/`skipif`/`xfail`/`importorskip`; việc loại test theo năng lực MUST là loại khi thu thập, mỗi test bị loại MUST có dấu năng lực và lý do, và MUST được báo cáo. (AC-6)
- **INV-007**: `ram_peak_mb` MUST là MiB quy đổi từ đơn vị gốc của đúng OS; không đo được MUST là `null` tường minh (không 0, không ước lượng); công thức Linux MUST không đổi để hồ sơ run cũ vẫn so sánh được. (AC-2)

<a id="key-entities-include-if-feature-involves-data"></a>
### Key Entities *(include if feature involves data)*

- **Hồ sơ nền tảng (Platform profile)**: kết quả nhận diện máy đang chạy — loại OS (`windows`/`linux`/`wsl2`/`macos`), bản phát hành OS, kiến trúc, phiên bản Python; là đầu vào duy nhất cho mọi phân nhánh theo OS và tiêm giả được trong test.
- **Năng lực (Capability)**: một khả năng của máy — màn hình, symlink, đường dẫn dài, đo RAM, UTF-8 đầu ra, CUDA — gồm cờ khả dụng và lý do tiếng Việt khi không khả dụng.
- **Báo cáo môi trường (Environment report)**: kết quả của `check_env` — hồ sơ nền tảng, phiên bản gói, thiết bị torch, các năng lực, danh sách phép kiểm `ok`/`warn`/`fail` và kết luận tổng; có khuôn JSON Schema.
- **Dấu năng lực (Capability marker)**: nhãn gắn vào test cho biết năng lực test cần (kèm lý do); đầu vào của cơ chế loại khi thu thập và của báo cáo test bị loại.
- **Ô ma trận CI (CI matrix cell)**: một tổ hợp OS × phiên bản Python của CI, với kết quả `check_env`, kết quả test và danh sách test bị loại.

<a id="success-criteria-mandatory"></a>
## Success Criteria *(mandatory)*

<a id="measurable-outcomes"></a>
### Measurable Outcomes

- **SC-001**: Trên Windows gốc, Linux và macOS, 100% CLI trong FR-001 thoát cùng mã như trên Linux với cấu hình smoke, và 100% mô-đun `mma_ai.*` nhập được. (AC-1)
- **SC-002**: `ram_peak_mb` quy đổi đúng 3/3 đơn vị gốc (KiB, byte, đỉnh working set) về 256,0 MB, và mức tăng đo thật khi cấp phát 256 MiB nằm trong [230,4 ; 332,8] MB trên 3/3 OS. (AC-2)
- **SC-003**: Phép dò màn hình cho kết luận đúng trên 3/3 OS (có màn hình ⇒ khả dụng không cần biến môi trường trên Windows/macOS; không màn hình ⇒ không khả dụng ≤ 5 s kèm gợi ý `--headless`), và cả ba nơi dò cho cùng kết luận. (AC-3)
- **SC-004**: 100% lần ghi tệp ở bốn ca tiêm lỗi giữ nguyên bản cũ và không để tệp tạm; 5/5 dạng đường dẫn tuyệt đối bị từ chối; 0 byte `\r` và 0 `UnicodeEncodeError` ở mọi CLI. (AC-4)
- **SC-005**: Làm theo tài liệu cài đặt trên Windows gốc dựng được môi trường và `python scripts/check_env.py` thoát mã 0 với `os.kind` = `windows`; trên WSL2 báo `wsl2`; trên macOS báo `macos`; trên Linux báo `linux`. (AC-5)
- **SC-006**: CI chạy 6/6 ô (3 OS × Python 3.11, 3.12) xanh, test bị loại theo năng lực ≤ 5% mỗi ô và 100% có lý do; 0 `skip`/`xfail` mới. (AC-6)

<a id="out-of-scope"></a>
## Out of Scope

- Hỗ trợ GPU AMD và Metal (chỉ CUDA là GPU được hướng dẫn; còn lại đường CPU).
- Đóng gói installer (không làm trình cài đặt `.exe`/`.msi`/`.dmg`; cài bằng uv/pip).
- M2–M9 (mỏi cơ, cân bằng, locomotion, toàn thân, hai võ sĩ, self-play, MJX): chỉ là lộ trình/ràng buộc, không đặc tả hay lập kế hoạch chi tiết.
- Windows ARM64 và macOS Intel (x86_64): không thuộc cấu hình đã kiểm (khoá `uv.lock` thiếu wheel `torch` cho macOS Intel); `check_env` chỉ báo, không hứa hỗ trợ.
- Sửa các lỗi sản phẩm mà test thử thách đã ghi nhận bằng `xfail` hiện hữu (ví dụ tập mục tiêu quá lớn, `stage` chứa dấu phân cách đường dẫn): feature này chỉ làm các test đó không vỡ vì lỗi nền tảng, không đổi nghĩa khẳng định của chúng.
- Đổi phiên bản phụ thuộc hoặc đổi thuật toán/mô hình/reward của M0–M1.
- Dựng hình ngoài màn hình (xuất khung ảnh/video không màn hình): không làm (kế thừa quyết định của `005`).

<a id="assumptions"></a>
## Assumptions

- Người dùng là nhà nghiên cứu/kỹ sư dự án, chạy qua dòng lệnh; không có giao diện người dùng mới; không có người dùng cuối nào khác.
- Python 3.11–3.12 trên cả ba OS; công cụ cài đặt chính là uv, pip là phương án thay thế có hướng dẫn; macOS Apple Silicon là cấu hình macOS đã kiểm.
- Dải wheel trong `uv.lock` (đã đo: có `win_amd64`, `macosx_*_arm64`, `manylinux_*_x86_64` cho `mujoco`, `torch`, `glfw`; `myo-sim` là gói thuần Python) là bằng chứng ban đầu cho việc cài được trên ba OS; việc cài thật trên Windows/macOS CHƯA KIỂM ở bước này vì máy phát triển là Linux.
- Hành vi GLFW/MuJoCo/myo-sim trên Windows và macOS gốc, và wheel `torch` của PyPI cho Windows là bản CPU (cỡ ≈ 124 MB trong khoá, so với ≈ 555 MB của bản Linux có thư viện CUDA đi kèm) — suy từ kích thước, CHƯA KIỂM; chỉ CI hoặc thiết bị thật chứng minh được.
- Máy phát triển hiện tại là Linux; Windows 11 (gốc và WSL2) và macOS chưa có máy của nhóm — bằng chứng nghiệm thu cho hai OS này là ô CI tương ứng; repo chưa có remote nên workflow CI chỉ kiểm tĩnh tại thời điểm đặc tả.
- Các tệp evaluate/replay hiện bị xoá ở trạng thái staged trong cây làm việc dùng chung; spec giả định chúng có mặt ở nhánh tích hợp khi thi công (đồng bộ với vai chủ), và không khôi phục chúng ở đây.
- Cấu hình smoke của M1 (train/evaluate/replay) đủ nhỏ để chạy trên runner CI CPU; thời lượng cụ thể CHƯA KIỂM.
- Chỉ nền tảng và tương thích; không đổi năng lực nghiệp vụ M0–M1; M2–M9 không được đặc tả hay lập kế hoạch ở đây.

<a id="dev"></a>
## Dev

*(Track M — sửa hệ đang chạy; bằng chứng hiện trạng lấy từ `docs/00-survey/mma-ai-cross-platform.md` (F-001…F-011) và rà soát `rg` ở bước này (F-012…F-020). Dòng có "(+)" là phát hiện thêm ngoài khảo sát.)*

<a id="hien-trang"></a>
### Hiện trạng

| Mã | file:dòng | Hành vi hiện tại |
|---|---|---|
| F-001 | `src/mma_ai/learning/resources.py:8,77-79` | Nhập `resource` vô điều kiện; `_peak_ram_mb` lấy `ru_maxrss / 1024` (đúng cho Linux/KiB, sai 1024 lần trên macOS, không chạy được trên Windows). |
| F-002 | `src/mma_ai/learning/manifest.py:362-364` | `build_manifest` không có hồ sơ tài nguyên thì nhập lười `collect_resources` và gọi F-001. |
| F-003 | `src/mma_ai/visualization/display.py:34,60,80-81` | `display_available()` gọi `glfw.init()` thật, nhưng chỉ đọc `DISPLAY`/`WAYLAND_DISPLAY` để soạn thông điệp lý do. |
| F-004 | `src/mma_ai/monitoring/viewer3d.py:48-50` | `View3D.has_display()` chỉ kiểm `DISPLAY` hoặc `WAYLAND_DISPLAY`. |
| F-005 | `src/mma_ai/learning/benchmark.py:139-146` | `evaluate_view3d_status()` tự dò bằng cùng hai biến môi trường. |
| F-006 | `src/mma_ai/learning/run_dir.py:19-37` | `create_run_dir` nối `stage` vào `Path`, tạo thư mục loại trừ; tên run `YYYYMMDDTHHMMSSZ_<stage>_s<seed>` không chứa `:`. |
| F-007 | `checkpoint.py:338-400`, `manifest.py:502-509`, `progress.py:86-90`, `visualization/episode.py:713-721`, `benchmark.py:215-222`, `monitoring/cli.py:117-125` | Mẫu "ghi tệp tạm + `fsync` + `os.replace`" lặp ở 6 tệp (≥ 8 chỗ gọi); không xử lý `PermissionError` của Windows; `monitoring/cli.py:119` dùng `write_text` không đặt `newline`. |
| F-008 | `src/mma_ai/learning/cli.py:148-160` | Sinh tiến trình quan sát bằng `sys.executable -m mma_ai.monitoring.cli`, không ghép lệnh shell (đã đa nền tảng). |
| F-009 | `src/mma_ai/evaluation/runner.py`, `evaluation/cli.py` (HEAD, đang xoá staged) | CLI evaluate; chưa kiểm trên Windows/macOS. |
| F-010 | `src/mma_ai/visualization/replay.py`, `visualization/cli.py` (HEAD, đang xoá staged) | CLI replay/demo; gọi F-003 trước viewer. |
| F-011 | `pyproject.toml:5,22,48`; không có `scripts/`, `.github/` | Python `>=3.11,<3.13`; extra `rl` có `torch` không phân loại CPU/CUDA; marker `display` chỉ nói `DISPLAY`/`WAYLAND_DISPLAY`; chưa có `check_env`, workflow CI, tài liệu cài đặt Windows. |
| F-012 (+) | `evaluation/eval_config.py:450,460`; `learning/manifest.py:176,205,212,248`; `learning/trainer.py:150`; `visualization/recorder.py:97,112` | Kiểm "tuyệt đối" bằng `startswith("/")` và làm tương đối bằng `lstrip("/")`: không bắt được ổ đĩa/UNC/`\` của Windows. |
| F-013 (+) | `src/mma_ai/environment/verify_clean_install.py:144` | `py_bin = venv_path / "bin" / "python"`: sai trên Windows (`Scripts\python.exe`). |
| F-014 (+) | `src/mma_ai/monitoring/cli.py:132-139`; `monitoring/cli.py:28` | `multiprocessing.Process(target=_run_viewer3d_process, args=(str,))`: đích ở cấp mô-đun nên có khả năng chạy được dưới `spawn` nhưng chưa có test nào chạy dưới `spawn`. |
| F-015 (+) | `tests/challenge/test_env_invariants.py:230-238` | Test `xfail` không nghiêm ngặt chạy mã con có `import resource` + `resource.setrlimit(RLIMIT_AS…)`: không chạy được trên Windows; `RLIMIT_AS` không đáng tin trên macOS. |
| F-016 (+) | `tests/challenge/test_train_invariants.py:763-775` | Test tạo symlink trực tiếp bằng `symlink_to`, không kiểm năng lực; mã sản phẩm không có `symlink`/`is_symlink` (xác nhận bằng `rg`). |
| F-017 (+) | `conftest.py:17-33`; `tests/unit/test_display.py:51-75`; `tests/integration/test_viewer3d.py:211-217` | Cách ly và kỳ vọng "không có màn hình" chỉ bằng xoá `DISPLAY`/`WAYLAND_DISPLAY`; trên Windows/macOS phép dò GLFW không phụ thuộc hai biến này nên test sẽ sai. |
| F-018 (+) | `src/mma_ai/learning/metrics_log.py:57`; `monitoring/cli.py:119`; `benchmark.py:221` | `open("a")`/`write_text` văn bản không đặt `newline` ⇒ Windows ghi `\r\n` vào jsonl/json. |
| F-019 (+) | `src/mma_ai/learning/cli.py:172-213` | Ghi tiếng Việt qua `sys.stderr.write` không ép UTF-8 ⇒ pipe/console bảng mã cũ trên Windows có thể ném `UnicodeEncodeError`. |
| F-020 (+) | `uv.lock` (mục `torch`, `mujoco`, `glfw`) | Có wheel `win_amd64` và `macosx_*_arm64` cho `torch` 2.14.1, `mujoco` 3.15.0, `glfw` 2.10.2; không có wheel `torch` cho macOS Intel. |

<a id="thay-doi"></a>
### Thay đổi

| Mã | Quyết định | AC liên quan |
|---|---|---|
| F-001 | **change**: bỏ nhập vô điều kiện; quy đổi theo OS (Linux KiB, macOS byte, Windows đỉnh working set); `null` khi không đo được | AC-2 |
| F-002 | **keep**: giữ luồng, hưởng hành vi mới của F-001 | AC-2 |
| F-003 | **change**: phép dò theo OS dùng chung (lớp tương thích); giữ thông điệp Linux | AC-3 |
| F-004 | **change**: `has_display()` gọi phép dò chung; không đổi hình thức giao diện (Q-0001) | AC-3 |
| F-005 | **change**: `evaluate_view3d_status()` gọi phép dò chung | AC-3 |
| F-006 | **keep**: giữ tạo thư mục loại trừ; thêm test tên run hợp lệ ở cả ba OS và test tiêm lỗi đường dẫn dài | AC-4 |
| F-007 | **change**: gom về một cơ chế ghi nguyên tử dùng chung có thử lại trên Windows; Linux giữ nguyên hành vi | AC-4 |
| F-008 | **keep** | AC-1 |
| F-009 | **change** (khi tệp có mặt): chỉ sửa điểm gắn nền tảng (đường dẫn, F-012, ép UTF-8) | AC-1, AC-4 |
| F-010 | **change** (khi tệp có mặt): gọi phép dò chung, ép UTF-8, thông báo macOS `mjpython` | AC-1, AC-3 |
| F-011 | **change**: thêm dấu năng lực vào `pyproject.toml`; **add**: `scripts/check_env.py`, `.github/workflows/`, tài liệu cài đặt | AC-5, AC-6 |
| F-012 | **change**: thay bằng luật đường dẫn tuyệt đối/tương đối theo mọi OS | AC-4 |
| F-013 | **change**: tìm Python venv theo OS | AC-1, AC-5 |
| F-014 | **keep** mã; **add** test chạy dưới `spawn` | AC-1 |
| F-015 | **change**: gắn dấu `linux_only` có lý do; không đổi nghĩa khẳng định | AC-6 |
| F-016 | **change**: gắn dấu `requires_symlink` có lý do; không đổi nghĩa khẳng định | AC-4, AC-6 |
| F-017 | **change**: cách ly và test dùng hồ sơ nền tảng giả/phép dò thay vì chỉ biến môi trường | AC-3, AC-6 |
| F-018 | **change**: ghi văn bản với xuống dòng LF cố định | AC-4 |
| F-019 | **change**: ép UTF-8 đầu ra chuẩn ở mọi điểm vào | AC-4 |
| F-020 | **keep**: giữ khoá; **add**: `uv lock --check` trong CI | AC-5, AC-6 |

<a id="tai-dung"></a>
### Tái dùng

| Thứ cần | Có sẵn? (đường dẫn) | Quyết định | Lý do |
|---|---|---|---|
| Đo RAM đỉnh | `src/mma_ai/learning/resources.py::_peak_ram_mb` | thêm nhánh giữ mặc định Linux | Hàm đã là nơi duy nhất đo RAM; chỉ cần phân nhánh OS, Linux không đổi. |
| Phép dò màn hình | `src/mma_ai/visualization/display.py::display_available` (+ `DisplayStatus`) | dùng lại, trích phần dò vào lớp tương thích | Đã có kiểu `DisplayStatus` và test; hai nơi dò còn lại (F-004, F-005) tự dò bằng biến môi trường nên phải gọi phép chung. |
| Ghi tệp nguyên tử | Mẫu `.tmp + fsync + os.replace` lặp ở 6 tệp (F-007) | tạo mới một cơ chế dùng chung | Không có hàm dùng chung; sửa riêng từng bản sao để thêm thử lại Windows là 8+ chỗ lệch nhau. |
| Chuẩn hoá đường dẫn trong bản ghi | `src/mma_ai/visualization/summary.py:45-52` (đổi `\` thành `/`, tương đối theo thư mục làm việc) | dùng lại logic | Đã làm đúng ý FR-011 cho tóm tắt; mở rộng thành hàm dùng chung cho manifest/episode/recorder. |
| Kiểm đường dẫn tuyệt đối | Không có (chỉ `startswith("/")`, F-012) | tạo mới | Không có sẵn luật nhận diện cả hai họ OS. |
| Kiểm môi trường nhanh | `src/mma_ai/environment/verify_clean_install.py` | tạo mới `check_env` | `verify_clean_install` dựng venv tạm và chạy toàn bộ pytest (chậm, mục đích khác) — không phủ được "báo OS/năng lực trong ≤ 30 s". Dùng lại cách đọc phiên bản gói bằng siêu dữ liệu gói. |
| Điểm vào CLI `main(argv)` | `learning/cli.py:230`, `learning/benchmark.py:432`, `monitoring/cli.py:68`, `learning/compare_cli.py:71` | dùng lại, thêm một lời gọi ép UTF-8 ở đầu | Đã có khung `main`; chỉ thêm một bước khởi động. |
| Dấu test | `pyproject.toml:48` marker `display`; `conftest.py:17` bộ cách ly | thêm nhánh giữ mặc định | Giữ nghĩa dấu `display` hiện có (cho phép biến môi trường); thêm dấu `requires_*` và cơ chế loại. |
| CI | Không có (`.github/` không tồn tại) | tạo mới | Chưa từng có. |
| Tài liệu cài đặt | Không có | tạo mới | Chưa từng có. |
| Cài torch CPU/CUDA | `pyproject.toml:22` extra `rl` (torch không ràng buộc nguồn) | dùng lại extra `rl`, hướng dẫn chọn CUDA bằng tuỳ chọn công cụ (plan quyết định) | Không đổi phụ thuộc ngoài phạm vi (hiến chương V); phương án thay đổi `pyproject.toml` được so sánh ở research Q8. |

<a id="qc"></a>
## QC

<a id="pham-vi-hoi-quy"></a>
### Phạm vi hồi quy

Consumer tầng 1 đọc từ import/gọi theo dòng mã (chỉ mục GitNexus của dự án chưa có nên không có đồ thị đầy đủ):

| Thay đổi | Consumer tầng 1 | Test hồi quy hiện có phải xanh |
|---|---|---|
| F-001/F-002 (RAM) | `learning/manifest.py:362`; `learning/benchmark.py` (đọc `ram_peak_mb`); `learning/trainer.py` | `tests/unit/test_resources.py`, `tests/unit/test_manifest.py`, `tests/integration/test_train_cli.py`, `tests/integration/test_manifest_contract.py` |
| F-003/F-004/F-005 (màn hình) | replay HEAD; `monitoring/viewer3d.py`; `learning/benchmark.py`; `learning/cli.py` (sinh UI) | `tests/unit/test_display.py`, `tests/integration/test_viewer3d.py`, `tests/integration/test_viewer3d_train.py`, `tests/unit/test_benchmark_logic.py`, `tests/integration/test_train_headless.py` |
| F-007 (ghi nguyên tử) | checkpoint, manifest, progress, episode, benchmark, `ui.json` | `tests/unit/test_checkpoint.py`, `tests/unit/test_manifest.py`, `tests/unit/test_progress.py`, `tests/unit/test_episode.py`, `tests/integration/test_resume.py`, `tests/property/test_manifest_properties.py` |
| F-012 (đường dẫn) | `evaluation/eval_config.py`; `learning/manifest.py`; `learning/trainer.py`; `visualization/recorder.py` | `tests/unit/test_eval_config.py`, `tests/unit/test_manifest.py`, `tests/unit/test_trainer.py`, `tests/unit/test_recorder.py` |
| F-013 (venv) | `verify_clean_install.main` | `tests/unit/test_verify_clean_install.py` |
| F-018/F-019 (LF, UTF-8) | `metrics_log`, `monitoring/cli`, `benchmark`, mọi CLI | `tests/unit/test_metrics_log.py`, `tests/unit/test_watch_cli.py`, `tests/unit/test_train_cli_args.py` |
| F-015/F-016/F-017 (test) | bộ test thử thách và cách ly môi trường | `tests/challenge/*`, `tests/unit/test_display.py`, toàn bộ bộ test (vì `conftest.py` đổi) |

<a id="test-dac-trung-characterization-phai-co-truoc-khi-doi-hanh-vi"></a>
### Test đặc trưng (characterization) phải có TRƯỚC khi đổi hành vi

- Ghi lại hành vi Linux hiện tại bằng test xanh trên mã cũ: quy đổi `ru_maxrss` KiB → MiB (giá trị mẫu), thông điệp và kết quả của `display_available()` khi `DISPLAY` bỏ đặt/đặt hỏng, kết quả `View3D.has_display()` và `evaluate_view3d_status()` theo biến môi trường, đầu ra của năm cách ghi nguyên tử (byte của tệp đích), lỗi cấu hình khi `runs_dir` bắt đầu bằng `/`.
- Sau đó mới đổi mã; các test đặc trưng phải xanh nguyên văn trên Linux sau thay đổi (INV-001, INV-007).

<a id="du-lieu-cu-phai-con-doc-duoc"></a>
### Dữ liệu cũ phải còn đọc được

- Hồ sơ run, `manifest.json`, checkpoint, `latest.json`, jsonl chỉ số và episode đã ghi trước thay đổi (Linux, `ram_peak_mb` MiB theo công thức cũ, đường dẫn tương đối dùng `/`) vẫn đọc và so sánh được; không đổi khuôn JSON của `001`…`005` (kiểm bằng các test hợp đồng hiện có).
- Tệp cấu hình YAML/JSON có xuống dòng CRLF vẫn đọc được (FR-012).
