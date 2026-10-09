---
id: "RES-004"
title: "M1 (3/4) — Nghiên cứu Phase 0 (Research)"
doc_type: plan
owner_agent: spec
status: draft
updated: "2026-10-09"
feature: "004-eval-vs-random-plots"
version: "1.0.0"
---

# Nghiên cứu Phase 0 — M1 (3/4): Đánh giá so với random policy và biểu đồ

- [Q1. Phương pháp khoảng tin cậy và quy tắc kết luận (FR-005, FR-006, NFR-STAT-001)](#q1-phuong-phap-khoang-tin-cay-va-quy-tac-ket-luan-fr-005-fr-006-nfr-stat-001)
- [Q2. Đọc nhật ký huấn luyện của con 2 (FR-010, FR-012)](#q2-doc-nhat-ky-huan-luyen-cua-con-2-fr-010-fr-012)
- [Q3. Vẽ biểu đồ headless (FR-010, FR-011, NFR-HEADLESS-001)](#q3-ve-bieu-do-headless-fr-010-fr-011-nfr-headless-001)
- [Q4. Random policy, số episode và chọn từng mục tiêu (FR-002, FR-003, INV-002, INV-007)](#q4-random-policy-so-episode-va-chon-tung-muc-tieu-fr-002-fr-003-inv-002-inv-007)
- [Q5. Dựng lại tập train để kiểm giao rỗng (FR-008, FR-009, INV-001)](#q5-dung-lai-tap-train-de-kiem-giao-rong-fr-008-fr-009-inv-001)
- [Q6. Nơi lưu, ghi nguyên tử và không để lại kết quả dở dang (FR-013, FR-014, FR-015, INV-004, INV-005)](#q6-noi-luu-ghi-nguyen-tu-va-khong-de-lai-ket-qua-do-dang-fr-013-fr-014-fr-015-inv-004-inv-005)
- [Q7. Nạp checkpoint chỉ-đọc và mã thoát (FR-001, FR-015)](#q7-nap-checkpoint-chi-doc-va-ma-thoat-fr-001-fr-015)
- [Q8. Phụ thuộc và cài đặt (NFR-HEADLESS-001; ràng buộc "Python 3.11, NumPy/Pandas")](#q8-phu-thuoc-va-cai-dat-nfr-headless-001-rang-buoc-python-311-numpypandas)
- [Q9. Tái lập và dung sai (NFR-REPRO-001, INV-007)](#q9-tai-lap-va-dung-sai-nfr-repro-001-inv-007)
- [Q10. Quy mô tài liệu, kiến trúc & stack](#q10-quy-mo-tai-lieu-kien-truc-stack)
- [Q11. Giả định giao diện với 001/002/003 (CHƯA KIỂM — cả ba chưa có mã)](#q11-gia-dinh-giao-dien-voi-001002003-chua-kiem-ca-ba-chua-co-ma)
- [Tổng kết](#tong-ket)


Mục "ĐÃ ĐO" là kết quả chạy thật ngày 2026-10-09 trên máy phát triển (Linux gốc, Python 3.11.15 do `uv` cấp, **chưa có NVIDIA**, `DISPLAY` bỏ đặt) trong môi trường ảo tạm: `numpy 2.4.6`, `pandas 3.0.6`, `matplotlib 3.11.2`, `tensorboard 2.21.0`, `jsonschema`. Mã thăm dò chạy ở thư mục tạm, KHÔNG nằm trong repo. Mục "CHƯA KIỂM" là việc phải xác minh ở bước triển khai — plan không giả định kết quả. Con số thời gian ở đây chỉ để đặt cỡ độ lớn, KHÔNG phải cam kết hay dự báo (master plan XI.10). Spec KHÔNG khẳng định policy học được tốt; nghiên cứu này chỉ chọn cách đo.

<a id="q1-phuong-phap-khoang-tin-cay-va-quy-tac-ket-luan-fr-005-fr-006-nfr-stat-001"></a>
## Q1. Phương pháp khoảng tin cậy và quy tắc kết luận (FR-005, FR-006, NFR-STAT-001)

- **Quyết định**: chỉ số chính là **tỷ lệ tới mục tiêu**. Khoảng tin cậy của từng tỷ lệ: **Wilson score** (mức 95%, `z = 1,959964`). Khoảng tin cậy của **hiệu hai tỷ lệ**: **Newcombe (phương pháp 10, Wilson hỗn hợp)**: `d = p₁ − p₂`, cận dưới `d − √((p₁ − l₁)² + (u₂ − p₂)²)`, cận trên `d + √((u₁ − p₁)² + (p₂ − l₂)²)`. Kết luận "tốt hơn" khi và chỉ khi cận dưới > 0. Với chỉ số phụ là trung bình liên tục (khoảng cách cuối, reward, nỗ lực): **bootstrap phân vị** cho trung bình từng policy với `B = 10 000` lần lấy mẫu lại, seed riêng của cấu hình (`stats.bootstrap_seed`), không dùng cho kết luận.
- **Căn cứ (ĐÃ ĐO, mô phỏng đáp án)** với 50 episode mỗi policy, hiệu = policy học được − random:

  | Tình huống (thành công / 50) | Hiệu | Khoảng tin cậy 95% (Newcombe) | Kết luận |
  |---|---|---|---|
  | 50 vs 0 | 1,000 | [0,899 ; 1,000] | tốt hơn |
  | 30 vs 10 | 0,400 | [0,210 ; 0,552] | tốt hơn |
  | 20 vs 10 | 0,200 | [0,020 ; 0,364] | tốt hơn (sát ngưỡng) |
  | 15 vs 8 | 0,140 | [−0,026 ; 0,297] | không tốt hơn |
  | 10 vs 10 | 0,000 | [−0,157 ; 0,157] | không tốt hơn |
  | 0 vs 0 | 0,000 | [−0,071 ; 0,071] | không tốt hơn |
  | 50 vs 50 | 0,000 | [−0,071 ; 0,071] | không tốt hơn |

  Các trường hợp biên (0/0, 50/50) cho khoảng hữu hạn, không NaN, không chia cho 0 — đúng Edge Case của spec. Phương pháp giải tích nên **không phụ thuộc seed** và test so được với đáp án tính tay (NFR-STAT-001). Với 50 episode, trong các ca đã đo, hiệu 0,14 (15 vs 8) chưa đủ để kết luận "tốt hơn" còn hiệu 0,20 (20 vs 10) vừa đủ — con số này cho người đọc biết sức mạnh kiểm định thấp của 50 mục tiêu, được ghi trong `limits` của báo cáo chứ không giấu.
- **Phương án đã loại**: (a) bootstrap ghép cặp theo mục tiêu cho chỉ số chính — ĐÃ ĐO cho 50 vs 0 ra khoảng thoái hoá [1,0 ; 1,0] và 10 vs 10 ghép cặp giống hệt ra [0 ; 0], tức khẳng định chắc chắn tuyệt đối từ 50 mẫu — quá lạc quan và không ổn định ở biên; (b) kiểm định chính xác Fisher/z cho hai tỷ lệ — cần `scipy` (thêm phụ thuộc) trong khi Newcombe chỉ cần `numpy`; z-test Wald vỡ ở tỷ lệ 0/1; (c) kết luận theo chỉ số khoảng cách cuối — liên tục nhưng không phải định nghĩa nhiệm vụ của con 1, và có episode bất thường không có khoảng cách (spec Tự chốt).
- **Hạn chế đã biết (ghi vào báo cáo)**: Newcombe coi các episode độc lập. Khi `repeats > 1`, các lần lặp cùng mục tiêu không độc lập ⇒ đơn vị phân tích là **mục tiêu**: `n = số mục tiêu`, `k = tổng tỷ lệ thành công theo từng mục tiêu` (có thể không nguyên; Wilson/Newcombe vẫn tính được) và báo cáo ghi `ci_method` kèm cờ "xấp xỉ khi repeats > 1". Khuyến nghị và mặc định `repeats = 1`. Độ chính xác của xấp xỉ này **CHƯA KIỂM** thống kê chặt; không là điều kiện nghiệm thu.

<a id="q2-doc-nhat-ky-huan-luyen-cua-con-2-fr-010-fr-012"></a>
## Q2. Đọc nhật ký huấn luyện của con 2 (FR-010, FR-012)

- **Quyết định**: bộ đọc nằm ở `metrics.py` (hàm `read_training_log`), thứ tự ưu tiên cấu hình được (`logs.source: auto`): (1) `metrics.jsonl` của run (một dòng mỗi lượt cập nhật), (2) tfevents trong `tb/` đọc bằng `tensorboard.backend.event_processing.event_accumulator.EventAccumulator` (`size_guidance={"scalars": 0}` để không cắt mẫu). Kết quả là bảng `pandas.DataFrame` dài `(series, step, value)`. Nhóm đại lượng chọn theo **tiền tố thẻ** cấu hình được (`logs.tags`): `loss` ← thẻ bắt đầu `loss`, `reward` ← thẻ bắt đầu `reward`, `activation` ← thẻ bắt đầu `activation/` (mỗi thẻ một cơ, tên cơ lấy từ phần sau dấu `/` và đối chiếu với `model.muscle_names` của hồ sơ run).
- **Căn cứ (ĐÃ ĐO)**: ghi 8 000 sự kiện scalar (1 000 bước × thẻ `loss/policy`, `reward/mean_return`, `activation/m0…m5`) bằng `tensorboard.summary` **không cần `torch`**, đọc lại bằng `EventAccumulator`: đủ 1 000 điểm mỗi thẻ, đọc mất ≈ 0,12 s. Vậy đọc nhật ký chỉ cần `tensorboard` (đã có trong extra `rl`) và không buộc nạp `torch`. Phần `jsonl` chỉ cần `pandas`.
- **CHƯA KIỂM**: tên thẻ và cột thật mà con 2 ghi — `contracts/` của 003 mới ghi "loss, reward, `activation/<tên cơ>`" và không có khuôn cho `metrics.jsonl`. Vì vậy ánh xạ thẻ là cấu hình (không rải hằng số trong mã) và test `test_training_log` dùng nhật ký mẫu cùng định dạng; khi con 2 có mã mà tên thẻ lệch thì sửa **cấu hình** (hoặc bổ sung khuôn `metrics.jsonl` ở 003), không sửa thuật toán. Nếu thiếu một nhóm ⇒ báo rõ nhóm nào thiếu và liệt kê thẻ thực có (FR-011).
- **Phương án đã loại**: chỉ hỗ trợ tfevents — bắt buộc phụ thuộc đọc định dạng nhị phân khi JSONL đủ dùng; chỉ hỗ trợ JSONL — yêu cầu ghi nguồn "log TensorBoard/CSV"; đọc bằng `torch.utils.tensorboard` — kéo `torch` vào bước vẽ.

<a id="q3-ve-bieu-do-headless-fr-010-fr-011-nfr-headless-001"></a>
## Q3. Vẽ biểu đồ headless (FR-010, FR-011, NFR-HEADLESS-001)

- **Quyết định**: `matplotlib` với backend `Agg` (đặt tường minh trong `charts.py`, trước khi nhập `pyplot`), mỗi biểu đồ một hình riêng lưu PNG (`loss.png`, `reward.png`, `activation.png`), `dpi` cấu hình (mặc định 120). Loss: một đường cho mỗi thẻ `loss*`. Reward: thẻ `reward*`. Activation: đúng 6 đường, nhãn là tên cơ. Trục có nhãn "lượt cập nhật" (hoặc "bước" theo nguồn) và tên đại lượng. Điểm không hữu hạn bị loại khỏi dữ liệu vẽ **trước** khi vẽ và đếm vào `points_dropped` (FR-012).
- **Căn cứ (ĐÃ ĐO)**: với `DISPLAY` bỏ đặt, vẽ 3 hình (loss 1 đường, reward 1 đường, activation 6 đường, mỗi đường 1 000 điểm) và lưu PNG mất ≈ 0,25 s tổng; kích thước 38–52 KB mỗi ảnh, không lỗi. `matplotlib 3.11.2` + `pandas 3.0.6` + `numpy 2.4.6` cùng cài được trong một venv.
- **Kiểm "ảnh đúng nội dung" không bằng mắt**: `charts.py` trả cùng ảnh một đối tượng `ChartData` (chuỗi đã vẽ: tên đường, số điểm, bước đầu/cuối); test khẳng định số đường, nhãn và số điểm khớp log, và PNG hợp lệ (chữ ký PNG, kích thước > 0, đọc lại được bằng `matplotlib.image.imread`). Không viết trình kiểm ảnh riêng.
- **Phương án đã loại**: Plotly/Altair — thêm phụ thuộc và cần trình duyệt/kaleido để xuất ảnh tĩnh; xuất SVG — yêu cầu ghi "tệp ảnh", PNG mở được ở mọi nơi; tự động mở cửa sổ `plt.show()` — vi phạm headless.

<a id="q4-random-policy-so-episode-va-chon-tung-muc-tieu-fr-002-fr-003-inv-002-inv-007"></a>
## Q4. Random policy, số episode và chọn từng mục tiêu (FR-002, FR-003, INV-002, INV-007)

- **Quyết định**: `RandomPolicy(seed)` dùng `numpy.random.default_rng(seed)` và lấy `u ~ Uniform[0,1)^6` mỗi bước (độc lập giữa các bước); nó **không** nhìn observation. Policy học được gọi `act_deterministic(obs_raw)` của 003 (`load_policy`). Cả hai chạy bằng cùng `run_policy_on_targets(env, policy, targets, repeats)`: với mỗi mục tiêu thứ `i` của tập kiểm thử và mỗi lần lặp, `env.reset(seed=episode_base + k, options={"split": "test", "target_index": i})`, `k` đếm tuần tự. Số episode mỗi policy = `n_test × repeats`.
- **Căn cứ**: bảo đảm "mỗi mục tiêu đúng một lần" và "cùng thứ tự cho hai policy" (INV-002) chỉ khi chọn được chỉ số mục tiêu. Hợp đồng đã công bố của con 1 (`002/contracts/python-api.md`) cho `reset(seed, options={"split": ...})` và báo `target_index` trong `info`, nhưng **chưa** nêu tuỳ chọn ép `target_index`.
- **CHƯA KIỂM / phụ thuộc D-2**: cần con 1 hỗ trợ `options["target_index"]` (đọc-chỉ, không đổi hành vi mặc định). Việc này là task nhỏ trong đúng tệp của 002 (`single_agent.py`), đứng sau task của 002 (Quy tắc thứ tự ở `plan.md`). Không có phương án thay thế chấp nhận được: lặp `reset` đến khi gặp đủ chỉ số làm số episode không tất định và có thể không bao giờ phủ hết.
- **Tất định random policy**: seed của `RandomPolicy` lấy từ `seeds.random_policy` (mặc định 12345); mỗi lượt đánh giá tạo MỘT bộ sinh và dùng liên tục qua mọi episode theo thứ tự cố định ⇒ cùng cấu hình, cùng chuỗi hành động (INV-007).
- **Hành động hỏng**: tại biên đánh giá (`rollout.py`), trước khi gọi `env.step`, hành động được kiểm hữu hạn và nằm trong `[0,1]^6`; vi phạm ⇒ đếm vào `nan_count`/`inf_count` (nếu có), episode kết thúc bất thường, **không** gọi `env.step` với hành động sai (con 1 sẽ ném `ActivationError`). Policy học được từ 003 luôn ra `sigmoid(...) ∈ (0,1)` nên đường này chủ yếu để bắt policy kịch bản/lỗi.
- **Phương án đã loại**: lấy mẫu `env.action_space.sample()` — phụ thuộc seed của không gian chứ không của cấu hình đánh giá; random policy có nhớ (OU noise) — baseline "ngẫu nhiên" của yêu cầu không đòi.

<a id="q5-dung-lai-tap-train-de-kiem-giao-rong-fr-008-fr-009-inv-001"></a>
## Q5. Dựng lại tập train để kiểm giao rỗng (FR-008, FR-009, INV-001)

- **Quyết định**: `split_guard.check_disjoint(run_info, eval_cfg)`:
  1. Đọc hồ sơ run (`manifest.json` của 003): `seed`, `config.env_config` (đường dẫn tương đối tới cấu hình môi trường), `model.sha256`, `resumed_from`. Đi ngược chuỗi `resumed_from.run_id` trong cùng thư mục gốc `runs/` để gom **mọi seed train** (tối đa 100 bậc; thiếu hồ sơ cha ⇒ từ chối, FR-009).
  2. Dựng `TargetSetPair` bằng `TargetGenerator(model, cfg).generate(master_seed)` của con 1 từ cấu hình môi trường của run (`master_seed = default_seed` của cấu hình, như `make_env`), rồi kiểm: `model_sha256` của tập khớp hồ sơ; **giao mục tiêu train∩test rỗng** và `min_cross_distance_m ≥ min_separation_m` (đọc từ chính `TargetSetPair`, không tính lại bằng mã mới); tập đánh giá chính là `pair.test` (đúng chỉ số, đúng toạ độ); mọi seed episode `[episode_base, episode_base + n_episodes)` và seed random policy **không** thuộc tập seed train.
  3. Ghi vào báo cáo: số mục tiêu train/đánh giá, khoảng cách nhỏ nhất đo được, seed train, seed đánh giá, và `train_target_provenance` ∈ {`manifest_fingerprint`, `rebuilt_from_config`}.
- **Căn cứ**: `TargetSetPair` của con 1 đã mang `train`, `test`, `min_cross_distance_m` và `fingerprint_sha256`; con 3 chỉ tiêu thụ nên không tự tạo khái niệm mới. Mức kiểm "chặt hơn trùng giá trị" là đúng INV-001 của con 1.
- **CHƯA KIỂM / phụ thuộc D-1 (rủi ro trượt cấu hình)**: hồ sơ run của 003 hiện lưu **đường dẫn** `env_config` chứ chưa lưu băm nội dung cấu hình môi trường hay `fingerprint_sha256` của tập mục tiêu. Nếu tệp cấu hình môi trường bị sửa sau khi train, tập dựng lại có thể khác tập đã dùng khi train mà con 3 không thấy. Cách chặn ở feature này: (1) nếu hồ sơ run có trường `env.target_fingerprint_sha256` thì so với `fingerprint_sha256` của tập dựng lại và lệch ⇒ từ chối (`provenance = manifest_fingerprint`); (2) nếu hồ sơ chưa có trường đó thì dùng cấu hình hiện tại, ghi `provenance = rebuilt_from_config` kèm `fingerprint_sha256` vào báo cáo để người đọc đối chiếu, và cấu hình đánh giá cho phép ghim `expect_fingerprint_sha256` (lệch ⇒ từ chối). Đề xuất giao về nơi chủ sở hữu (003): ghi thêm hai trường đọc-chỉ vào hồ sơ run; đây là **đề xuất riêng**, không làm lẫn vào task của 004 (constitution V). Cả hai nhánh đều có test.
- **Phương án đã loại**: bỏ qua phép kiểm khi thiếu thông tin — trái FR-009; tự viết bộ sinh/kiểm khoảng cách riêng cho con 3 — nhân đôi logic của con 1 (hai nơi nói hai điều).

<a id="q6-noi-luu-ghi-nguyen-tu-va-khong-de-lai-ket-qua-do-dang-fr-013-fr-014-fr-015-inv-004-inv-005"></a>
## Q6. Nơi lưu, ghi nguyên tử và không để lại kết quả dở dang (FR-013, FR-014, FR-015, INV-004, INV-005)

- **Quyết định**: kết quả ghi trong `runs/<run_id>/eval/<eval_id>/` với `eval_id = <UTC YYYYMMDDTHHMMSSZ>_e<seed đánh giá>[-n]`. Quy trình: (1) mọi kiểm tra đầu vào (nạp checkpoint, cấu hình, giao rỗng) **trước** khi tạo bất kỳ thư mục nào; (2) tạo `eval/.tmp-<eval_id>/` bằng `os.mkdir`; (3) ghi `report.json` (ghi `.tmp` → `fsync` → thay thế), `episodes.csv`, biểu đồ vào đó; (4) `os.rename` thư mục tạm thành `eval/<eval_id>/` — **đổi tên là bước công bố duy nhất**; (5) lỗi hoặc Ctrl-C ⇒ xoá `.tmp-…` do chính lượt này tạo và thoát mã khác 0. Trùng `eval_id` ⇒ hậu tố `-2`, `-3`… tới 100.
- **Căn cứ**: spec đòi không có bản ghi hợp lệ khi lỗi (INV-004), không có thư mục `eval/` dở dang (AC-5), không sửa tệp của 003 (INV-005). `os.rename` thư mục cùng hệ tệp là nguyên tử trên Linux. Thư mục `.tmp-…` bắt đầu bằng dấu chấm nên `list` của con 4 và người dùng không nhầm là kết quả.
- **Nơi ghi khi checkpoint ngoài thư mục run**: lệnh cần `--out DIR` tường minh; thiếu ⇒ thoát mã 2 nêu cách khắc phục. Khi đó không có hồ sơ run để kiểm giao rỗng ⇒ **từ chối** (FR-009); `--out` chỉ đổi nơi ghi, không bỏ qua kiểm tra. (Phạm vi hẹp có chủ ý: chưa có yêu cầu đánh giá checkpoint "mồ côi".)
- **Kiểm không sửa tệp con 2**: test băm SHA-256 mọi tệp trong run trước/sau (ngoài `eval/`), khớp (INV-005).
- **Phương án đã loại**: ghi trực tiếp vào `eval/<eval_id>/` rồi xoá nếu lỗi — cửa sổ có kết quả dở dang nếu tiến trình bị `kill -9`; sửa `manifest.json` của run để thêm danh sách đánh giá — vi phạm INV-001 của 003.

<a id="q7-nap-checkpoint-chi-doc-va-ma-thoat-fr-001-fr-015"></a>
## Q7. Nạp checkpoint chỉ-đọc và mã thoát (FR-001, FR-015)

- **Quyết định**: dùng `load_checkpoint(path)` (kiểm đủ thành phần, hình dạng mạng, `model_sha256`) rồi `load_policy(path)` của `mma_ai.learning.checkpoint` (003, hợp đồng `contracts/python-api.md`). Mọi `CheckpointError` ⇒ in lỗi tiếng Việt nêu nguyên nhân, thoát **4** (cùng quy ước mã 4 "checkpoint không dùng được" của `train.py`), trước khi tạo thư mục kết quả. Đường nạp dùng `weights_only=True` do 003 bảo đảm.
- **Bảng mã thoát** (giá trị cụ thể là chi tiết hợp đồng ở `contracts/cli.md`, không là INV/NFR mới): 0 hoàn tất · 1 lỗi đánh giá không lường trước · 2 tham số/cấu hình không hợp lệ · 4 checkpoint không dùng được · 5 tập đánh giá giao tập train / seed trùng / không thiết lập được tập train · 6 đánh giá xong nhưng biểu đồ không đầy đủ (kết quả số đã lưu) · 7 không ghi được kết quả · 130 bị ngắt. Mã 3 của `train.py` ("stage chưa triển khai") không dùng.
- **CHƯA KIỂM / phụ thuộc D-3**: `load_policy` và hồ sơ run (`manifest.json`) của 003 theo hợp đồng đã công bố; 003 chưa có mã. Lệch giao diện khi triển khai ⇒ sửa ở nơi chủ sở hữu, 004 chỉ thêm accessor đọc-chỉ.
- **Phương án đã loại**: tự nạp tệp `.pt` trong con 3 — nhân đôi logic kiểm checkpoint của con 2; khi đó hai nơi kiểm khác nhau.

<a id="q8-phu-thuoc-va-cai-dat-nfr-headless-001-rang-buoc-python-311-numpypandas"></a>
## Q8. Phụ thuộc và cài đặt (NFR-HEADLESS-001; ràng buộc "Python 3.11, NumPy/Pandas")

- **Quyết định**: thêm extra `eval` vào `pyproject.toml`: `pandas`, `matplotlib`; `numpy` đã có từ 001. Chạy đánh giá cần `torch` (nạp policy) và `tensorboard` (đọc tfevents) nên lệnh dựng là `uv sync --extra dev --extra rl --extra eval`. **Không** thêm `scipy`, `seaborn`, `statsmodels`: Wilson/Newcombe/bootstrap tự cài trên `numpy` (vài chục dòng, có test đáp án tay). `jsonschema` đã ở extra `dev` của 003.
- **Căn cứ (ĐÃ ĐO)**: `uv pip install --dry-run "gymnasium>=1.4,<1.5" myo-sim==0.2.3 mujoco torch tensorboard pandas matplotlib jsonschema pyyaml` giải được 64 gói (`gymnasium==1.4.0`, `torch==2.14.1`, `numpy==2.4.6`, `pandas==3.0.6`, `matplotlib==3.11.2`), không xung đột; không cần lùi `gymnasium`. Kéo `scipy` vào là chi phí thừa so với giải tích.
- **Phương án đã loại**: lên `pandas` làm phụ thuộc lõi của gói — chỉ phần đánh giá cần, nên nằm trong extra; vendoring công thức kiểm định từ thư viện thống kê — nhân đôi mã khó kiểm.
- **CHƯA KIỂM**: khoá phiên bản `uv.lock` chỉ cập nhật sau khi smoke test đạt (quy ước của 002/003); phiên bản `matplotlib`/`pandas` trên máy đích (Blackwell) không liên quan GPU nên rủi ro thấp.

<a id="q9-tai-lap-va-dung-sai-nfr-repro-001-inv-007"></a>
## Q9. Tái lập và dung sai (NFR-REPRO-001, INV-007)

- **Quyết định**: tái lập dựa vào (a) seed `RandomPolicy`, (b) seed episode `episode_base + k` tường minh, (c) policy học được xác định, (d) `torch.set_num_threads(1)` và chế độ suy luận `torch.inference_mode()` trong lúc đánh giá, (e) Newcombe/Wilson giải tích, bootstrap có seed. Dung sai: chuỗi hành động random giống hệt (so từng phần tử bằng `==`); chỉ số lệch tuyệt đối ≤ 1×10⁻⁶ (kế thừa dung sai nạp checkpoint của 003).
- **Căn cứ (ĐÃ ĐO, thăm dò)**: phần thống kê là phép tính `numpy` thuần tuý không có nguồn ngẫu nhiên khi dùng giải tích; bootstrap với `default_rng(seed)` cho kết quả lặp lại bit-bit trong cùng phiên bản `numpy`. Tính tất định của vật lý MuJoCo theo seed đã đo ở 002 (Q2).
- **CHƯA KIỂM**: sai khác giữa hai loại thiết bị (CPU↔GPU) — **không cam kết** (kế thừa Clarifications của 003); chỉ so khi cùng loại thiết bị, báo cáo ghi loại thiết bị.

<a id="q10-quy-mo-tai-lieu-kien-truc-stack"></a>
## Q10. Quy mô tài liệu, kiến trúc & stack

- **Quyết định**: vẫn **một bounded context** (mô phỏng và huấn luyện cơ–xương, gói `mma_ai`); nhãn `context: evaluation` trong cây tách là nhãn mô-đun trong cùng gói, không phải dịch vụ riêng ⇒ không tạo `docs/02-strategic/`, `docs/03-tactical/`, `docs/01-intent/overview.md`; không phân quyền (lệnh dòng lệnh cục bộ, không máy chủ, không token) ⇒ không `rbac.md`. `docs/` hiện chỉ có `00-input/`. Hợp đồng dây gồm một CLI, tệp báo cáo JSON có khuôn, và API Python (`contracts/`).
- **Stack**: không đổi (`python-mujoco-cli`); thêm extra `eval`; không có preset kit mới ⇒ `.ai/stack-proposal.yml` chỉ thêm dòng căn cứ.
- **Phương án đã loại**: tách gói `evaluation` ra repo/dịch vụ — chưa có lý do; gộp `evaluation` vào `learning` — làm con 3 phụ thuộc trainer (con 3 chỉ đọc).

<a id="q11-gia-dinh-giao-dien-voi-001002003-chua-kiem-ca-ba-chua-co-ma"></a>
## Q11. Giả định giao diện với 001/002/003 (CHƯA KIỂM — cả ba chưa có mã)

| Mã | Thành phần cần | Nguồn | Nếu lệch |
|---|---|---|---|
| D-1 | `manifest.json`: `seed`, `config.env_config`, `model.sha256`, `status`, `resumed_from`; (đề xuất) `env.target_fingerprint_sha256` | 003 `contracts/run-manifest.schema.json` | thiếu trường đề xuất ⇒ nhánh `rebuilt_from_config` + cảnh báo |
| D-2 | `reset(seed, options={"split": "test", "target_index": i})`; `info.target_index` | 002 `contracts/python-api.md` (thiếu `target_index` trong `options`) | task nhỏ đọc-chỉ ở `single_agent.py` của 002 |
| D-3 | `load_checkpoint`, `load_policy(...).act_deterministic(obs_raw)` | 003 `contracts/python-api.md` | sửa ở 003; 004 chỉ gọi |
| D-4 | `TargetGenerator.generate`, `TargetSetPair.{train,test,min_cross_distance_m,fingerprint_sha256}`, `make_env`, `env.model_record()`, `ObservationLayout` (kích hoạt 6 cơ ở chỉ số 2–7), `info{reward_dist, reward_effort, distance_m, reached, ctrl_effective, end_reason}` | 002 `contracts/` | sửa ở 002 |
| D-5 | Tên thẻ/cột nhật ký: `loss…`, `reward…`, `activation/<tên cơ>` | 003 `plan.md` (FR-010) — chưa có khuôn cho `metrics.jsonl` | chỉnh cấu hình `logs.tags` |
| D-6 | `mma_ai.config`, `mma_ai.diagnostics.environment` (phiên bản thư viện), `mma_ai.reporting.runlog` (ghi JSON an toàn) | 001 | tái dùng, không sao chép |

<a id="tong-ket"></a>
## Tổng kết

Không còn câu hỏi chưa giải quyết. Việc CHƯA KIỂM giao thành bước triển khai bắt buộc có kết quả ghi lại: (1) D-1…D-6 ở bảng Q11 khi 001–003 có mã; (2) độ chính xác xấp xỉ khi `repeats > 1` (Q1); (3) tên thẻ nhật ký thật của con 2 (Q2); (4) kết quả đánh giá thực trên checkpoint thật — spec không khẳng định policy tốt hơn random, kết luận là số đo của từng lượt; (5) thời gian chạy một lượt đánh giá — do máy đo và ghi trong báo cáo, không dự báo trước.
