---
id: "RES-006"
title: "Hỗ trợ đa nền tảng — Nghiên cứu Phase 0 (Research)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-11"
feature: "006-cross-platform-support"
version: "1.1.0"
---

# Nghiên cứu Phase 0 — Hỗ trợ đa nền tảng (Windows · Linux/WSL2 · macOS)

- [Q1. Nơi đặt lớp tương thích (FR-002, INV-002)](#q1-noi-dat-lop-tuong-thich-fr-002-inv-002)
- [Q2. Nhận diện bốn loại nền tảng (FR-002, FR-017)](#q2-nhan-dien-bon-loai-nen-tang-fr-002-fr-017)
- [Q3. Đo RAM đỉnh theo OS (FR-004, INV-007, NFR-RAM-001)](#q3-do-ram-dinh-theo-os-fr-004-inv-007-nfr-ram-001)
- [Q4. Dò màn hình và viewer 3D theo OS (FR-005…FR-008, NFR-DISPLAY-001)](#q4-do-man-hinh-va-viewer-3d-theo-os-fr-005fr-008-nfr-display-001)
- [Q5. Ghi nguyên tử và thử lại trên Windows (FR-009, INV-003, NFR-IO-001)](#q5-ghi-nguyen-tu-va-thu-lai-tren-windows-fr-009-inv-003-nfr-io-001)
- [Q6. Đường dẫn tuyệt đối theo mọi OS và đường dẫn trong bản ghi (FR-010, FR-011)](#q6-duong-dan-tuyet-doi-theo-moi-os-va-duong-dan-trong-ban-ghi-fr-010-fr-011)
- [Q7. UTF-8, xuống dòng LF và đầu ra chuẩn (FR-012, FR-013, NFR-ENC-001)](#q7-utf-8-xuong-dong-lf-va-dau-ra-chuan-fr-012-fr-013-nfr-enc-001)
- [Q8. Cài đặt tái lập: uv/pip, torch CPU/CUDA (FR-018, FR-019, AC-5)](#q8-cai-dat-tai-lap-uvpip-torch-cpucuda-fr-018-fr-019-ac-5)
- [Q9. Test theo năng lực mà không dùng skip/xfail (FR-021, FR-022, INV-006)](#q9-test-theo-nang-luc-ma-khong-dung-skipxfail-fr-021-fr-022-inv-006)
- [Q10. CI ma trận (FR-020, NFR-CI-001)](#q10-ci-ma-tran-fr-020-nfr-ci-001)
- [Q11. `multiprocessing` dưới `spawn` (FR-015)](#q11-multiprocessing-duoi-spawn-fr-015)
- [Q12. Phạm vi các CLI và tệp đang bị xoá staged (FR-001, AC-1)](#q12-pham-vi-cac-cli-va-tep-dang-bi-xoa-staged-fr-001-ac-1)
- [Q13. Phạm vi bất định cần người xác nhận về sau (không chặn plan)](#q13-pham-vi-bat-dinh-can-nguoi-xac-nhan-ve-sau-khong-chan-plan)

Căn cứ: `spec.md` bản 1.0.1 (Q-0002 đã được người dùng trả lời: Windows gốc là môi trường chính, CUDA tuỳ chọn và máy người dùng có CUDA, macOS phải chạy tốt).

Quy ước nhãn: **ĐÃ ĐO** = số/hành vi quan sát được ở máy phát triển (Linux, Python 3.12.3) hoặc trong `uv.lock` ở bước này; **NGUỒN TÀI LIỆU** = lấy từ tài liệu chính thức của công cụ (chưa chạy trên OS đó); **CHƯA KIỂM** = chỉ CI hoặc thiết bị thật Windows/macOS chứng minh được. Không số nào dưới đây là cam kết hiệu năng.

<a id="q1-noi-dat-lop-tuong-thich-fr-002-inv-002"></a>
## Q1. Nơi đặt lớp tương thích (FR-002, INV-002)

- **Quyết định**: gói mới `src/mma_ai/compat/` (lá của đồ thị phụ thuộc: không nhập `learning`, `evaluation`, `visualization`, `monitoring`, `environment`, `physics`).
- **Vì sao không tên `platform`**: `mma_ai/platform/` sẽ che mô-đun chuẩn `platform` khi một tệp trong `src/mma_ai/` được chạy trực tiếp (thư mục của tệp vào đầu `sys.path`); `compat` không va chạm tên thư viện chuẩn nào.
- **Vì sao một gói chung thay vì sửa tại chỗ**: hiện có 3 nơi tự dò màn hình (F-003/F-004/F-005), ≥ 8 chỗ ghi nguyên tử (F-007) và 4 chỗ cắt `/` (F-012); sửa tại chỗ để lại 3 bản dò + 8 bản thử lại lệch nhau — đúng điều nhóm khảo sát cảnh báo ("chuỗi sửa dự kiến (1) platform facade").
- **Phương án loại**: thêm `psutil`/`platformdirs`/`portalocker` — loại, vì yêu cầu "không thêm phụ thuộc nặng" và mọi nhu cầu (RAM đỉnh, dò OS, thay thế tệp) đáp ứng được bằng thư viện chuẩn + `ctypes` ở nhánh Windows.

<a id="q2-nhan-dien-bon-loai-nen-tang-fr-002-fr-017"></a>
## Q2. Nhận diện bốn loại nền tảng (FR-002, FR-017)

- **Quyết định**: `detect_platform()` đọc `sys.platform`, `platform.release()`, `platform.machine()` và biến môi trường; trả `windows` khi `sys.platform == "win32"`, `macos` khi `darwin`, `wsl2` khi Linux và `platform.release()` chứa `wsl2` (hoặc chứa `microsoft` kèm biến `WSL_DISTRO_NAME`), còn lại `linux`. Mọi đầu vào tiêm được (tham số) để test dựng hồ sơ giả cho cả bốn loại trên bất kỳ OS nào.
- **ĐÃ ĐO**: máy phát triển cho `sys.platform == "linux"`, Python 3.12.3 (`python3 --version`); không phải WSL.
- **CHƯA KIỂM**: chuỗi `release` thật của WSL2 (dạng `…-microsoft-standard-WSL2` theo tài liệu Microsoft) và của Windows 11 (`10.0.2xxxx`) — ví dụ trong `contracts/examples/` là minh hoạ khuôn, không phải số đo.
- **`tested`**: `false` cho Windows ARM64 (`machine` = `ARM64`) và macOS Intel (`x86_64` trên `darwin`) vì khoá thiếu wheel `torch` cho hai tổ hợp này (xem Q8).

<a id="q3-do-ram-dinh-theo-os-fr-004-inv-007-nfr-ram-001"></a>
## Q3. Đo RAM đỉnh theo OS (FR-004, INV-007, NFR-RAM-001)

| OS | Nguồn | Đơn vị gốc | Quy đổi về MiB |
|---|---|---|---|
| Linux, WSL2 | `resource.getrusage(RUSAGE_SELF).ru_maxrss` | KiB | ÷ 1024 (giữ nguyên công thức hiện tại) |
| macOS | cùng lời gọi | byte | ÷ 1 048 576 |
| Windows | `GetProcessMemoryInfo` qua `ctypes` (kernel32/psapi), trường `PeakWorkingSetSize` | byte | ÷ 1 048 576 |

- **ĐÃ ĐO (Linux)**: nhập `resource` rồi cấp phát và chạm 256 MiB (`numpy.ones`) làm `ru_maxrss` tăng từ 30 440 lên 292 604 KiB, tức **+256,02 MiB** ⇒ công thức KiB ÷ 1024 đúng; và dải chấp nhận [0,9 ; 1,3] × 256 = [230,4 ; 332,8] MB chứa số đo với biên rộng.
- **NGUỒN TÀI LIỆU**: macOS trả `ru_maxrss` bằng byte còn Linux bằng KiB (trang `getrusage(2)` của hai hệ); Windows không có mô-đun `resource` (tài liệu thư viện chuẩn: mô-đun chỉ có trên Unix). **CHƯA KIỂM** trên máy macOS/Windows thật.
- **Nhập có điều kiện**: `import resource` chỉ nằm trong nhánh Linux/macOS của hàm, không ở mức mô-đun; `ctypes.windll` chỉ được tham chiếu trong nhánh Windows.
- **Phương án loại**: `psutil.Process().memory_info().peak_wset` — loại vì thêm phụ thuộc, và `psutil` không có đỉnh RSS trên Linux; `tracemalloc` — loại vì chỉ đo heap Python, không phải RSS.
- **Thất bại** (API Windows lỗi, `getrusage` ném ngoại lệ): trả `null` tường minh (INV-007); `check_env` ghi năng lực `ram_peak` không khả dụng kèm lý do.

<a id="q4-do-man-hinh-va-viewer-3d-theo-os-fr-005fr-008-nfr-display-001"></a>
## Q4. Dò màn hình và viewer 3D theo OS (FR-005…FR-008, NFR-DISPLAY-001)

- **Hiện trạng**: `display_available()` đã gọi `glfw.init()` thật (F-003) — là phép dò đúng cho mọi OS; hai nơi còn lại (F-004, F-005) chỉ xét biến môi trường POSIX. Trên Windows/macOS không có hai biến đó nên cả hai luôn báo "không có màn hình".
- **Quyết định**: một hàm `probe_display(profile)` trong `compat`:
  - Linux/WSL2: nếu cả `DISPLAY` và `WAYLAND_DISPLAY` đều trống ⇒ không khả dụng (không gọi GLFW — đúng hành vi hiện tại, lý do và thông điệp giữ nguyên chữ); ngược lại thử `glfw.init()` rồi `glfw.terminate()` như hiện nay.
  - Windows/macOS: **không đọc** hai biến; gọi `glfw.init()` và kiểm có màn hình chính (`glfw.get_primary_monitor()` khác rỗng) rồi `glfw.terminate()`.
  - Mọi ngoại lệ ⇒ không khả dụng kèm chi tiết (INV-004); hàm có tham số tiêm `glfw_init` để test.
  - `display_available()`, `View3D.has_display()`, `evaluate_view3d_status()` đều gọi hàm này.
- **ĐÃ ĐO (005)**: `glfw.init()` mất ≈ 0,03 s và trả 0 khi không có màn hình, không sập tiến trình (research Q2 của 005); đủ cho ngưỡng ≤ 5 s.
- **Tác động tới `View3D.has_display()` (quan sát train, F-004)**: hàm hiện là `staticmethod` rẻ (không nạp đồ hoạ). Nhánh Linux giữ đường tắt "biến môi trường trống ⇒ không khả dụng" (không nạp GLFW) nên không đổi; nhánh Windows/macOS phải nạp GLFW — chấp nhận được vì `View3D.run()` chạy trong tiến trình con riêng, sau cờ `--view3d` tường minh (Q-0001: chỉ-đọc, tiến trình riêng, không kéo chậm vòng train).
- **macOS và `mjpython` — NGUỒN TÀI LIỆU** (tài liệu Python của MuJoCo): "On MacOS, `launch_passive` requires that the user script is executed via a special `mjpython` launcher … The `mjpython` command is installed as part of the `mujoco` package", và `mjpython` là thay thế trực tiếp cho `python`. Thiết kế: trên macOS, trước khi mở viewer, nếu `launch_passive` ném `RuntimeError` có nhắc `mjpython` (hoặc trình thông dịch hiện tại không phải `mjpython`), `ViewerSink` chuyển thành `DisplayUnavailable` với thông điệp tiếng Việt nêu lệnh `mjpython -m …`, mã thoát như đường "không có màn hình" của 005 (không treo). **CHƯA KIỂM** trên macOS thật: chuỗi lỗi chính xác của MuJoCo và cách `mjpython` đặt `sys.executable` — vì vậy phép nhận diện dùng cả hai tín hiệu và có test giả lập cả hai.
- **WSL2**: dùng nhánh Linux; có WSLg thì `DISPLAY`/`WAYLAND_DISPLAY` được đặt và GLFW khởi tạo được (CHƯA KIỂM); không có thì đường `--headless` (đã là đường chính thức của 005).
- **Windows không có phiên tương tác** (dịch vụ, SSH, runner không giao diện): `glfw.init()` có thể thành công nhưng không có màn hình chính, hoặc thất bại ⇒ không khả dụng; **CHƯA KIỂM** hành vi thật trên runner CI Windows/macOS ⇒ test thật dùng dấu `requires_display` (Q9) theo chính phép dò này, nên đúng dù runner có hay không có màn hình.

<a id="q5-ghi-nguyen-tu-va-thu-lai-tren-windows-fr-009-inv-003-nfr-io-001"></a>
## Q5. Ghi nguyên tử và thử lại trên Windows (FR-009, INV-003, NFR-IO-001)

- **Hiện trạng ĐÃ ĐO (đọc mã)**: sáu tệp tự lặp mẫu `ghi .tmp cùng thư mục → fsync(file) → os.replace` (F-007); không nơi nào `fsync` thư mục (nên không gặp vấn đề "không mở được thư mục" của Windows) và tệp tạm nằm cùng thư mục với đích (nên `os.replace` không đi qua hai ổ đĩa).
- **Quyết định**: một `replace_atomic(src, dst)` + `write_text_atomic`/`write_bytes_atomic` dùng chung. Trên Windows, `PermissionError` từ `os.replace` được thử lại tối đa 5 lần với lịch chờ 0,05 → 0,10 → 0,20 → 0,20 s (tổng ≤ 0,55 s, trong ngưỡng 1,0 s của NFR-IO-001), vì đích đang mở bởi tiến trình khác hoặc phần mềm quét tệp là lỗi tạm thời; hết lượt thì xoá tệp tạm và ném lỗi nêu đường dẫn đích. Trên Linux/macOS **không** thử lại: một lần `os.replace` như hiện nay (INV-001).
- **NGUỒN TÀI LIỆU**: Python — `os.replace` thay thế tệp đích nguyên tử trên POSIX; trên Windows có thể lỗi nếu đích đang được mở không kèm quyền chia sẻ xoá/đổi tên. **CHƯA KIỂM** trên Windows thật: số lần thử lại cần và tần suất khoá giả; test thật dùng tiến trình giữ mở đích để tái hiện (ô CI Windows).
- **Phương án loại**: `MoveFileEx`/`ReplaceFile` qua `ctypes` — loại, vì `os.replace` đã gọi `MoveFileExW(MOVEFILE_REPLACE_EXISTING)`; `portalocker`/khoá tệp — loại, thêm phụ thuộc và không giải quyết khoá do bên thứ ba giữ.
- **Quyết định về diện sửa**: chuyển 6 tệp sang hàm dùng chung là sửa **cùng một việc** ở nhiều chỗ chứ không phải refactor toàn cục (hiến chương V); mỗi chỗ giữ nguyên thứ tự ghi/`fsync` hiện có (đặc trưng hoá bằng test byte-đích trước khi đổi — QC của spec).

<a id="q6-duong-dan-tuyet-doi-theo-moi-os-va-duong-dan-trong-ban-ghi-fr-010-fr-011"></a>
## Q6. Đường dẫn tuyệt đối theo mọi OS và đường dẫn trong bản ghi (FR-010, FR-011)

- **ĐÃ ĐO (Python 3.12.3, `pathlib`)**:

| Chuỗi | `PureWindowsPath.is_absolute()` | `drive` | `root` | `PurePosixPath.is_absolute()` |
|---|---|---|---|---|
| bắt đầu `/` | False | rỗng | `\` | True |
| bắt đầu `\` | False | rỗng | `\` | False |
| UNC (`\\máy\chia-sẻ\…`) | True | `\\máy\chia-sẻ` | `\` | False |
| ổ đĩa + `\` | True | `X:` | `\` | False |
| ổ đĩa không dấu phân cách (`X:ten`) | False | `X:` | rỗng | False |
| `runs`, `runs/a/b`, `runs\a` | False | rỗng | rỗng | False |

  ⇒ `is_absolute()` một mình không đủ: dạng `\…` và `X:ten` có `is_absolute() == False` nhưng vẫn phải bị từ chối.
- **Quyết định**: `is_absolute_any_os(s)` = đúng khi `PurePosixPath(s).is_absolute()` **hoặc** `PureWindowsPath(s)` có `drive` khác rỗng **hoặc** `root` khác rỗng. Luật này chạy giống nhau trên mọi OS (không phụ thuộc OS đang chạy), nên `tests/unit/test_compat_pathrules.py` kiểm được năm dạng trên Linux.
- **`to_record_path(path, base)`**: trả dạng tương đối so với `base` (mặc định thư mục làm việc), đổi `\` thành `/`, bỏ ổ đĩa/gốc; thay các cụm `str(p).lstrip("/")` (F-012) và mở rộng logic có sẵn của `summary.py:45-52`.
- **Tên run**: `create_run_dir` sinh `YYYYMMDDTHHMMSSZ_<stage>_s<seed>` — mẫu `strftime("%Y%m%dT%H%M%SZ")` không có dấu hai chấm nên hợp lệ trên Windows (ĐÃ ĐO: `src/mma_ai/learning/run_dir.py:23`); chỉ `stage` do người gọi truyền vào có thể chứa ký tự cấm, mà CLI ép `stage='elbow'` nên không đổi (lỗi `stage` đã ghi ở test `xfail` hiện hữu — ngoài phạm vi).
- **Đường dẫn dài (Windows)**: giới hạn mặc định 260 ký tự khi chưa bật `LongPathsEnabled` (khoá Registry nhánh `FileSystem`, đọc bằng `winreg` ở nhánh Windows). `check_env` báo `long_paths`; khi ghi thất bại vì tên quá dài, thông báo lỗi nêu độ dài. **CHƯA KIỂM** ngưỡng thực của Python trên Windows 11 (bản Python từ python.org và từ uv đã khai báo hỗ trợ đường dẫn dài trong manifest ứng dụng — cần kiểm).
- **Không phân biệt hoa/thường**: tên do hệ thống sinh đều chữ thường hoặc dấu thời gian (`latest.json`, `manifest.json`, `checkpoints`, `tb`); va chạm tên run vẫn do `mkdir` loại trừ quyết định (ĐÃ ĐO: `run_dir.py:26-29`).

<a id="q7-utf-8-xuong-dong-lf-va-dau-ra-chuan-fr-012-fr-013-nfr-enc-001"></a>
## Q7. UTF-8, xuống dòng LF và đầu ra chuẩn (FR-012, FR-013, NFR-ENC-001)

- **ĐÃ ĐO (Linux)**: `rg` toàn `src/` cho thấy mọi `read_text`/`write_text`/`open` văn bản đã đặt `encoding="utf-8"` (nên không có lỗi mã hoá ngầm theo locale); nhưng không nơi nào đặt `newline` ⇒ trên Windows, `write_text`/`open("w"|"a")` đổi `\n` thành `\r\n` (F-018: `metrics_log.py:57`, `monitoring/cli.py:119`, `benchmark.py:221`, …).
- **ĐÃ ĐO**: `Path.write_text(..., newline="\n")` hợp lệ ở Python 3.12.3 (tham số `newline` có từ 3.10, nằm trong khoảng 3.11–3.12) và ghi đúng byte `\n` (`b'a\nb\n'`).
- **ĐÃ ĐO**: `PYTHONIOENCODING=cp1252 python -c "print('Cánh tay duỗi tới mục tiêu')"` ném `UnicodeEncodeError: 'charmap' codec can't encode character 'ỗ'` ⇒ lỗi này tái hiện được trên Linux, nên test `PYTHONIOENCODING=cp1252` chạy ở cả ba OS và chứng minh F-019 mà không cần máy Windows.
- **Quyết định**: `ensure_utf8_stdio()` gọi `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` (và `stderr`) khi luồng hỗ trợ `reconfigure`; gọi ở đầu mỗi `main()` của CLI (`learning/cli.py:230`, `learning/benchmark.py:432`, `learning/compare_cli.py:71`, `monitoring/cli.py:68`, và `scripts/*.py`). Không đặt biến môi trường toàn cục `PYTHONUTF8` (không kiểm soát được tiến trình cha).
- **Đọc**: `read_text(encoding="utf-8")` chấp nhận cả LF và CRLF (chế độ văn bản phổ quát), nên cấu hình YAML/JSON checkout với CRLF vẫn đọc được. Hash XML mô hình (SHA-256 trên byte) lấy từ tệp trong gói `myo-sim` cài từ wheel — không qua `git autocrlf` — nên không đổi theo OS; **CHƯA KIỂM** trên Windows.
- **`.gitattributes`**: đặt `eol=lf` cho `*.py`, `*.yaml`, `*.yml`, `*.json`, `*.md`, `*.toml`, `*.xml` để cây mã checkout trên Windows không đổi byte của tệp mà test so sánh/băm; nhỏ, thuộc kết quả (d) của yêu cầu.

<a id="q8-cai-dat-tai-lap-uvpip-torch-cpucuda-fr-018-fr-019-ac-5"></a>
## Q8. Cài đặt tái lập: uv/pip, torch CPU/CUDA (FR-018, FR-019, AC-5)

- **ĐÃ ĐO (đọc `uv.lock`)**: `torch` 2.14.1 có wheel `win_amd64` (≈ 124 MB), `macosx_14_0_arm64` (≈ 127 MB) và `manylinux_2_28_x86_64` (≈ 555 MB) cho CPython 3.11/3.12; **không** có wheel macOS x86_64 cho `torch`. `mujoco` 3.15.0 có `win_amd64`, `macosx_11_0_arm64`, `manylinux_2_27_x86_64`; `glfw` 2.10.2 có `win_amd64`, `macosx_11_0_arm64`, `manylinux`; `myo-sim` 0.2.3 là gói thuần Python (`py3-none-any`). Khoá có ≥ 24 dòng `win_amd64` và ≥ 56 dòng `macosx`.
- **Suy ra (CHƯA KIỂM)**: kích thước wheel Windows nhỏ hơn nhiều so với wheel Linux (có thư viện CUDA đi kèm qua các gói `nvidia-*`) cho thấy bản Windows trên PyPI là bản CPU ⇒ cài mặc định từ khoá trên Windows là **CPU**; muốn CUDA phải lấy từ chỉ mục của PyTorch.
- **Phương án**:
  - **A (chọn)** — giữ `pyproject.toml` và `uv.lock` nguyên; CPU là đường mặc định (`uv sync --extra dev --extra rl --extra eval`); CUDA là bước tuỳ chọn có tài liệu: `uv pip install --reinstall --torch-backend=<cuXXX> torch` rồi chạy các lệnh sau bằng `uv run --no-sync` (để `uv run` không cài lại bản trong khoá). **NGUỒN TÀI LIỆU**: tuỳ chọn `--torch-backend` (`cpu`, `cu*`, `auto`) và biến `UV_TORCH_BACKEND` của `uv pip install` — tính năng thử nghiệm trong tài liệu uv. Giá trị `cuXXX` cho RTX 50-series (Blackwell) phải kiểm theo bản `torch` lúc viết tài liệu — **CHƯA KIỂM**.
  - **B** — thêm extra `rl-cpu`/`rl-cuda` với `[tool.uv.sources]` theo extra và `[tool.uv] conflicts` (mẫu có trong tài liệu uv). Loại ở bước này vì đổi `pyproject.toml` và sinh lại `uv.lock` (hiến chương V: không đổi phụ thuộc ngoài phạm vi; rủi ro làm đỏ test hiện có trong `test_dependency_*`), trong khi A đủ đáp ứng "có hướng dẫn". Ghi nhận như đề xuất riêng nếu người dùng muốn cài CUDA thành một lệnh.
  - **C** — chỉ mục theo `sys_platform` (mẫu `marker = "sys_platform == 'darwin'"`) — loại: gán cứng một bản CUDA cho mọi máy Linux/Windows, phá đường CPU.
- **Máy người dùng (Windows gốc, có CUDA — Q-0002)**: đường CUDA là đường tuỳ chọn nhưng là đường người dùng thật sự dùng, nên tài liệu cài đặt có mục "torch CUDA trên Windows" riêng và kịch bản kiểm tay ở `quickstart.md`; đường CPU vẫn là đường nghiệm thu bắt buộc vì CI không có GPU. GPU của người dùng là dòng RTX 50 (Blackwell): chọn `cuXXX` phải theo bản `torch` lúc viết tài liệu — **CHƯA KIỂM**.
- **pip**: `uv export --format requirements-txt` sinh tệp ràng buộc từ `uv.lock` rồi `pip install -r …` + `pip install -e . --no-deps` — tái lập yếu hơn uv (không kiểm băm theo từng nền tảng nếu bỏ `--require-hashes`) nên tài liệu coi pip là phương án thay thế.
- **Kiểm khoá cho ba OS**: `uv lock --check` trong CI; `uv sync --locked` ở từng ô — nếu khoá không giải quyết được cho một OS, ô đó đỏ (bằng chứng AC-5/AC-6).
- **`uv.toml` cục bộ**: tệp `uv.toml` (chế độ liên kết `symlink`) nằm trong `.git/info/exclude`, **không** được commit (ĐÃ ĐO: `git ls-files uv.toml` rỗng) nên không ảnh hưởng người dùng Windows; tài liệu cài đặt không được chỉ dẫn dùng nó.

<a id="q9-test-theo-nang-luc-ma-khong-dung-skipxfail-fr-021-fr-022-inv-006"></a>
## Q9. Test theo năng lực mà không dùng skip/xfail (FR-021, FR-022, INV-006)

- **Mâu thuẫn cần giải**: yêu cầu (f) nói "test cần GPU/màn hình được đánh dấu và bỏ qua có chủ đích, không xfail/skip để che lỗi"; hiến chương II cấm thêm cơ chế bỏ qua. Giải theo hiến chương (Clarifications của spec).
- **ĐÃ ĐO (nguyên mẫu trong thư mục tạm, pytest hiện hành)**: một `conftest.py` 15 dòng dùng `pytest_collection_modifyitems` + `config.hook.pytest_deselected(items=…)` cho kết quả `1 passed, 1 deselected` (test mang dấu `requires_display("lý do")` bị loại, không phải skip); dấu thiếu lý do làm `pytest.UsageError` ngay ở bước thu thập (không chạy test nào). Đó là cơ chế dự kiến.
- **Quyết định**: `tests/unit/capability_gate.py` (plugin nạp từ `conftest.py`) đăng ký dấu bằng `config.addinivalue_line` (không đổi `pyproject.toml`), đánh giá năng lực bằng chính `compat` (`probe_display`, `symlink_supported`, CUDA qua `torch.cuda.is_available()` nhập lười, `detect_platform`), loại test thiếu năng lực, in danh sách (tên test + lý do + tỷ lệ) ở `pytest_terminal_summary`, ghi tuỳ chọn ra tệp JSON (`--capability-report`) cho CI, và **làm phiên thất bại nếu tỷ lệ loại > 5%** (NFR-CI-001).
- **Bộ dấu**: `requires_display`, `requires_cuda`, `requires_symlink`, `windows_only`, `posix_only`, `linux_only`, `macos_only`; dấu `display` hiện có (cho phép biến môi trường hiển thị — `conftest.py:17`) giữ nguyên nghĩa.
- **Test hiện có phải sửa** (không đổi nghĩa khẳng định): `tests/challenge/test_env_invariants.py:230` (`import resource` + `RLIMIT_AS`) ⇒ `linux_only`, vì `RLIMIT_AS` không đáng tin trên macOS và không có trên Windows; `tests/challenge/test_train_invariants.py:763` (`symlink_to`) ⇒ `requires_symlink`; `tests/integration/test_viewer3d.py:211` (tự suy `has_display` từ biến môi trường) ⇒ `requires_display`; `tests/unit/test_display.py:51` (kỳ vọng không màn hình khi `DISPLAY` bỏ đặt) ⇒ tiêm hồ sơ nền tảng Linux giả, thêm test tiêm hồ sơ Windows/macOS với GLFW giả.
- **`importorskip`/`xfail` đã có**: giữ nguyên (không thêm, không bớt); CI cài đủ extra `rl` và `dev` nên các test dùng `importorskip("torch")` chạy thật.
- **Phương án loại**: `pytest.mark.skipif` theo `sys.platform` — loại (là skip); tách thư mục test theo OS — loại (nhân đôi test, vi phạm "một chỗ").

<a id="q10-ci-ma-tran-fr-020-nfr-ci-001"></a>
## Q10. CI ma trận (FR-020, NFR-CI-001)

- **Quyết định**: một workflow GitHub Actions, ma trận `os: [ubuntu-latest, macos-latest, windows-latest]` × `python: ["3.11", "3.12"]` (6 ô, `fail-fast: false`); mỗi ô: lấy mã, cài uv (`astral-sh/setup-uv`) với Python của ô, `uv lock --check`, `uv sync --locked --extra dev --extra rl --extra eval`, `uv run python scripts/check_env.py --json` (đẩy lên làm artefact), `uv run python -m pytest -q -p no:cacheprovider --ignore=tests/e2e --capability-report <tệp>`, rồi `uv run python -m pytest -q -p no:cacheprovider tests/e2e`; một job riêng chỉ chạy trên Linux 3.12 cho `ruff` và `mypy --strict` (cùng cổng với `.ai/profile.yml`). `macos-latest` là Apple Silicon (arm64) — khớp cấu hình macOS đã kiểm.
- **NGUỒN TÀI LIỆU / CHƯA KIỂM**: tên runner và hành động là của dịch vụ CI và có thể đổi; repo hiện **không có remote** (`git remote -v` rỗng, ĐÃ ĐO) nên chưa chạy thật được — bằng chứng ở bước này chỉ là kiểm tĩnh `test_ci_workflow` (ma trận đủ 6 ô, có `check_env`, có cờ `--locked`, không có `continue-on-error`, không `|| true`).
- **Shell của runner**: runner Windows dùng PowerShell mặc định; mọi bước workflow là lệnh một dòng `uv …`/`python …` không dùng cú pháp riêng của bash, nên chạy được ở cả ba shell; nếu lỗi trích dẫn xuất hiện thì đặt `shell: bash` ở bước đó — CHƯA KIỂM.
- **Ngân sách thời gian**: CHƯA KIỂM (huấn luyện smoke trên runner CPU, cài `torch` ≈ 124–555 MB mỗi ô); nếu vượt, giảm phạm vi test nặng bằng dấu — không đổi tiêu chí ma trận.
- **Cổng dự án**: `tests`, `lint`, `typecheck` trong `.ai/profile.yml` không đổi; CI là lớp bổ sung chứ không thay cổng máy.

<a id="q11-multiprocessing-duoi-spawn-fr-015"></a>
## Q11. `multiprocessing` dưới `spawn` (FR-015)

- **NGUỒN TÀI LIỆU**: phương thức khởi động mặc định là `spawn` trên Windows và macOS, `fork` trên Linux (Python 3.12).
- **ĐÃ ĐO**: `multiprocessing.get_start_method()` trên máy phát triển = `fork`. Chạy `get_context("spawn").Process(target=mma_ai.monitoring.cli._run_viewer3d_process, args=(<thư mục>,))` từ một tệp script có bảo vệ `__main__`: tiến trình con **khởi động được dưới `spawn` và gọi tới `viewer.run()`** (chứng tỏ hàm đích nhập và tuần tự hoá được); nó thoát mã 1 chỉ vì trình thông dịch hệ thống dùng để đo không có `mujoco` (`ModuleNotFoundError: mujoco`) — là hạn chế của phép đo, không phải của mã. Lần chạy đầu thất bại vì script nạp qua stdin (spawn cần tệp để chạy lại `__main__`), minh hoạ đúng ràng buộc "điểm vào có bảo vệ `__main__`".
- **Quyết định**: không đổi mã tạo tiến trình (Linux giữ `fork` mặc định — INV-001); thêm test chạy dưới `get_context("spawn")` ở cả ba OS để chứng minh tính nhập/tuần tự hoá (F-014). Nếu test đỏ trên Windows/macOS thì sửa hàm đích tại chỗ.
- **Dừng tiến trình**: `Process.terminate()` ở `monitoring/cli.py` là kết thúc cứng trên Windows và SIGTERM trên POSIX — chấp nhận được vì tiến trình con là chỉ-đọc (Q-0001).

<a id="q12-pham-vi-cac-cli-va-tep-dang-bi-xoa-staged-fr-001-ac-1"></a>
## Q12. Phạm vi các CLI và tệp đang bị xoá staged (FR-001, AC-1)

- **ĐÃ ĐO**: `git status` ở đầu lượt cho thấy `D` (xoá staged) với `src/mma_ai/evaluation/{charts,cli,metrics,report,runner}.py`, `src/mma_ai/visualization/{cli,replay}.py` và các test tương ứng; `eval_config.py`, `display.py`, `recorder.py` vẫn còn. Đó là việc của vai/nhánh khác trong cây dùng chung (hiến chương III).
- **Quyết định**: spec và plan nêu các CLI này là đích của AC-1 nhưng task của feature phải (a) phụ thuộc vào việc chúng có mặt ở nhánh tích hợp và (b) chỉ sửa điểm gắn nền tảng của chúng; không khôi phục tệp ở lượt này. Khi chưa có mặt, test AC-1 cho evaluate/replay nằm ở danh sách "chờ phụ thuộc" của `tasks.md`.

<a id="q13-pham-vi-bat-dinh-can-nguoi-xac-nhan-ve-sau-khong-chan-plan"></a>
## Q13. Phạm vi bất định cần người xác nhận về sau (không chặn plan)

- Máy Windows 11 thật của người dùng chạy viewer 3D và GPU CUDA RTX 5060, và macOS thật: kiểm tay, CHƯA KIỂM (người dùng xác nhận Windows gốc là chính và macOS phải chạy tốt — Q-0002).
- Số lần thử lại/độ trễ ghi tệp thực trên Windows có phần mềm diệt virus: hiệu chỉnh theo số đo CI.
- Chuỗi lỗi chính xác của `launch_passive` trên macOS khi thiếu `mjpython`: kiểm trên macOS thật hoặc CI.
