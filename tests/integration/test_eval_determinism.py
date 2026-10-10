"""Kiểm thử tích hợp tính tái lập của phân hệ đánh giá qua dòng lệnh (T421).

Hiện thực và xác minh toàn diện các yêu cầu kỹ thuật, bất biến miền và tiêu chuẩn chất lượng:
- 004 NFR-REPRO-001, 004 INV-007, 004 AC-1: Tính tái lập (reproducibility) của lượt đánh giá
  theo hạt giống (seed) trên cùng loại thiết bị tính toán:
  Hai lượt đánh giá cùng điểm kiểm tra (checkpoint), cùng cấu hình, cùng hạt giống cho chuỗi
  hành động của chính sách ngẫu nhiên (random policy) giống hệt (0 khác biệt) và mọi chỉ số,
  khoảng tin cậy (confidence interval - CI) lệch tuyệt đối <= 1e-6.
- 004 INV-007, 004 FR-003, 004 AC-1: Hai hạt giống đánh giá khác nhau (khác cờ --eval-seed)
  sinh ra chuỗi hành động của chính sách ngẫu nhiên khác nhau, chứng minh hạt giống thực sự
  chi phối hành vi lấy mẫu.
- 004 FR-005, 004 NFR-STAT-001: Tính tất định (determinism) của thuật toán lấy mẫu lại
  bootstrap (bootstrap resampling) với hạt giống cố định cho cùng khoảng tin cậy.
- Bài học builder: Khẳng định độc lập (independent assertion) trên nền tảng (base) đảm bảo bộ
  kiểm thử không bị bỏ qua toàn bộ khi thiếu phụ thuộc tuỳ chọn (optional dependency) PyTorch.
"""

from __future__ import annotations

import csv
import json
import math

import numpy as np
import pytest
from eval_fixtures import make_run_dir, run_cli

from mma_ai.evaluation.eval_config import EvalConfig
from mma_ai.evaluation.metrics import summarize
from mma_ai.evaluation.policies import RandomPolicy
from mma_ai.evaluation.rollout import EpisodeRecord
from mma_ai.evaluation.stats import bootstrap_mean_ci, newcombe_difference, wilson_interval


def test_determinism_contract_independent_assertion() -> None:
    """004 NFR-REPRO-001, 004 INV-007, 004 FR-005, 004 AC-1: Khẳng định độc lập trên base.

    Bảo đảm bộ kiểm thử không bị bỏ qua toàn bộ khi thiếu phụ thuộc tuỳ chọn PyTorch.
    Xác minh cấu hình mặc định, tính tất định thuần tuý của RandomPolicy và thuật toán bootstrap.
    """
    # 1. Xác minh cấu hình đánh giá mặc định đáp ứng đầy đủ tham số tái lập theo hợp đồng
    cfg = EvalConfig.load()
    assert cfg.seeds.episode_base == 12345, (
        f"Hạt giống cơ sở tập phim (episode_base) mặc định 12345, nhận {cfg.seeds.episode_base}"
    )
    assert cfg.seeds.random_policy == 12345, (
        f"Hạt giống random_policy mặc định 12345, nhận {cfg.seeds.random_policy}"
    )
    assert cfg.stats.bootstrap_seed == 0, (
        f"Hạt giống bootstrap mặc định phải là 0 nhưng nhận {cfg.stats.bootstrap_seed}"
    )
    assert cfg.stats.bootstrap_resamples == 10000, (
        f"Số lần bootstrap mặc định phải là 10000 nhưng nhận {cfg.stats.bootstrap_resamples}"
    )

    # Xác minh tính đồng bộ của hạt giống ngẫu nhiên khi ghi đè episode_base
    # (004 INV-007, 004 NFR-REPRO-001)
    cfg_override = EvalConfig.load(overrides={"seeds.episode_base": 2000})
    assert cfg_override.seeds.episode_base == 2000, "episode_base phải nhận giá trị ghi đè 2000"
    assert cfg_override.seeds.random_policy == 2000, (
        f"004 INV-007: Khi ghi đè seeds.episode_base (qua cờ --eval-seed), "
        f"seeds.random_policy phải đồng bộ với episode_base (2000), "
        f"nhưng nhận {cfg_override.seeds.random_policy}"
    )

    # 2. 004 INV-007: Khẳng định tính tất định độc lập của RandomPolicy với cùng seed
    pol1 = RandomPolicy(seed=12345, act_dim=6)
    pol2 = RandomPolicy(seed=12345, act_dim=6)
    dummy_obs = np.zeros(14, dtype=np.float64)

    actions1 = [pol1.act(dummy_obs) for _ in range(25)]
    actions2 = [pol2.act(dummy_obs) for _ in range(25)]

    for a1, a2 in zip(actions1, actions2, strict=True):
        np.testing.assert_array_equal(
            a1,
            a2,
            err_msg="004 INV-007: Cùng seed phải sinh chuỗi hành động ngẫu nhiên giống hệt",
        )
        assert np.all(a1 >= 0.0) and np.all(a1 <= 1.0), (
            "004 INV-003: Mọi hành động kích thích cơ bắp phải thuộc [0, 1]^6"
        )

    # 3. 004 INV-007: Khẳng định hai seed khác nhau sinh chuỗi hành động khác nhau
    pol_diff = RandomPolicy(seed=54321, act_dim=6)
    action_diff = pol_diff.act(dummy_obs)
    assert not np.array_equal(actions1[0], action_diff), (
        "004 INV-007: Khác seed phải sinh hành động ngẫu nhiên khác nhau"
    )

    # 4. 004 FR-005, 004 NFR-STAT-001: Khẳng định tính tất định của thuật toán bootstrap giải tích
    data_sample = np.array([0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 1.0], dtype=np.float64)
    low_a, high_a = bootstrap_mean_ci(data_sample, level=0.95, resamples=2000, seed=42)
    low_b, high_b = bootstrap_mean_ci(data_sample, level=0.95, resamples=2000, seed=42)
    assert low_a == low_b and high_a == high_b, (
        "004 FR-005: Cùng seed và resamples phải sinh khoảng tin cậy bootstrap bit-bit giống nhau"
    )

    # Khác seed bootstrap sinh khoảng tin cậy khác biệt nhẹ
    low_c, high_c = bootstrap_mean_ci(data_sample, level=0.95, resamples=2000, seed=99)
    assert (low_a != low_c) or (high_a != high_c), (
        "Khác bootstrap seed phải cho khoảng tin cậy khác nhau"
    )

    # 5. Khẳng định tính tất định của khoảng Wilson và hiệu Newcombe
    w_low_1, w_high_1 = wilson_interval(20, 50, level=0.95)
    w_low_2, w_high_2 = wilson_interval(20, 50, level=0.95)
    assert math.isclose(w_low_1, w_low_2, abs_tol=1e-12)
    assert math.isclose(w_high_1, w_high_2, abs_tol=1e-12)

    n_diff_1, n_low_1, n_high_1 = newcombe_difference(30, 50, 10, 50, level=0.95)
    n_diff_2, n_low_2, n_high_2 = newcombe_difference(30, 50, 10, 50, level=0.95)
    assert math.isclose(n_diff_1, n_diff_2, abs_tol=1e-12)
    assert math.isclose(n_low_1, n_low_2, abs_tol=1e-12)
    assert math.isclose(n_high_1, n_high_2, abs_tol=1e-12)


def test_bootstrap_seed_fixed_gives_same_ci() -> None:
    """004 FR-005, 004 NFR-STAT-001, 004 AC-1: Bootstrap seed cố định cho cùng khoảng tin cậy.

    Kiểm tra độc lập trên pipeline tính toán chỉ số summarize():
    Với cùng danh sách bản ghi tập phim (EpisodeRecord) và cấu hình EvalConfig có
    stats.bootstrap_seed xác định, các chỉ số có khoảng tin cậy bootstrap
    (khoảng cách cuối và phần thưởng trung bình) được tái lập chính xác 100%.
    """
    cfg = EvalConfig.load()

    # Xây dựng danh sách bản ghi tập phim mẫu
    records: list[EpisodeRecord] = []
    for i in range(20):
        records.append(
            EpisodeRecord(
                policy="random",
                episode=i,
                target_index=i,
                seed=1000 + i,
                reached=(i % 4 == 0),
                end_reason="reached" if (i % 4 == 0) else "max_actions",
                abnormal=False,
                final_distance_m=0.015 + 0.005 * (i % 5),
                return_=-10.0 + 2.0 * i,
                effort=0.3 + 0.02 * (i % 3),
                act_m0=0.2,
                act_m1=0.25,
                act_m2=0.3,
                act_m3=0.35,
                act_m4=0.4,
                act_m5=0.45,
                n_steps=100,
                nan_count=0,
                inf_count=0,
            )
        )

    summary_1 = summarize(records, cfg)
    summary_2 = summarize(records, cfg)

    # 1. Kiểm tra tỷ lệ thành công (Wilson interval giải tích)
    assert summary_1.success_rate.value == summary_2.success_rate.value
    assert summary_1.success_rate.ci_low == summary_2.success_rate.ci_low
    assert summary_1.success_rate.ci_high == summary_2.success_rate.ci_high

    # 2. Kiểm tra khoảng cách cuối (Bootstrap mean CI)
    assert summary_1.final_distance_m.value is not None
    assert summary_2.final_distance_m.value is not None
    assert math.isclose(
        summary_1.final_distance_m.value, summary_2.final_distance_m.value, abs_tol=1e-12
    )
    assert summary_1.final_distance_m.ci_low == summary_2.final_distance_m.ci_low
    assert summary_1.final_distance_m.ci_high == summary_2.final_distance_m.ci_high

    # 3. Kiểm tra phần thưởng trung bình (Bootstrap mean CI)
    assert summary_1.mean_return.value is not None
    assert summary_2.mean_return.value is not None
    assert math.isclose(
        summary_1.mean_return.value, summary_2.mean_return.value, abs_tol=1e-12
    )
    assert summary_1.mean_return.ci_low == summary_2.mean_return.ci_low
    assert summary_1.mean_return.ci_high == summary_2.mean_return.ci_high

    # 4. Khi thay đổi bootstrap_seed trong cấu hình, khoảng tin cậy bootstrap sẽ có sự thay đổi
    custom_dict = cfg.as_dict()
    custom_dict["stats"]["bootstrap_seed"] = 9999
    cfg_diff_bootstrap = EvalConfig._validate_and_build(custom_dict)
    summary_diff = summarize(records, cfg_diff_bootstrap)

    assert (summary_1.final_distance_m.ci_low != summary_diff.final_distance_m.ci_low) or (
        summary_1.final_distance_m.ci_high != summary_diff.final_distance_m.ci_high
    ), "Khác bootstrap_seed phải cho khoảng tin cậy bootstrap khác nhau"


def test_same_seed_same_actions_and_metrics(tmp_path_factory: pytest.TempPathFactory) -> None:
    """004 NFR-REPRO-001, 004 INV-007, 004 FR-005, 004 AC-1: Cùng seed cùng hành động và chỉ số.

    Thực thi hai lượt đánh giá dòng lệnh (CLI) liên tiếp trên cùng điểm kiểm tra (checkpoint),
    cùng cấu hình và cùng cờ --eval-seed:
    - Chuỗi hành động kích thích cơ bắp của chính sách ngẫu nhiên trong episodes.csv giống hệt
      từng phần tử (so sánh tuyệt đối ==).
    - Mọi chỉ số thống kê và khoảng tin cậy trong report.json lệch tuyệt đối <= 1e-6.
    - Hai lượt tạo hai thư mục kết quả riêng biệt không ghi đè lẫn nhau (INV-005).
    """
    pytest.importorskip("torch", reason="Cần PyTorch để nạp checkpoint và chạy suy luận mô hình")
    pytest.importorskip("pandas", reason="Cần pandas để xử lý bảng số liệu và chỉ số")
    pytest.importorskip("matplotlib", reason="Cần matplotlib để xuất biểu đồ đánh giá")

    tmp_dir = tmp_path_factory.mktemp("eval_determinism_same_seed")
    run_dir = make_run_dir(tmp_dir, seed=42)
    latest_ckpt = run_dir / "checkpoints" / "latest.json"

    eval_seed = 1000

    # Lượt 1: Chạy CLI với --eval-seed 1000
    res1 = run_cli(["--checkpoint", str(latest_ckpt), "--eval-seed", str(eval_seed)])
    assert res1.returncode in (0, 6), (
        f"Lượt 1 thất bại với mã {res1.returncode}.\nStdout: {res1.stdout}\nStderr: {res1.stderr}"
    )

    # Lượt 2: Chạy CLI với cùng --eval-seed 1000
    res2 = run_cli(["--checkpoint", str(latest_ckpt), "--eval-seed", str(eval_seed)])
    assert res2.returncode in (0, 6), (
        f"Lượt 2 thất bại với mã {res2.returncode}.\nStdout: {res2.stdout}\nStderr: {res2.stderr}"
    )

    # Kiểm tra tồn tại đúng 2 thư mục đánh giá hoàn tất trong eval/ (004 INV-005)
    eval_base_dir = run_dir / "eval"
    assert eval_base_dir.is_dir(), f"Thư mục eval không tồn tại: {eval_base_dir}"
    eval_subdirs = sorted(
        [p for p in eval_base_dir.iterdir() if p.is_dir() and not p.name.startswith(".tmp-")],
        key=lambda p: p.name,
    )
    assert len(eval_subdirs) == 2, (
        f"Kỳ vọng đúng 2 thư mục đánh giá độc lập nhưng tìm thấy: {[p.name for p in eval_subdirs]}"
    )

    dir1, dir2 = eval_subdirs[0], eval_subdirs[1]
    assert dir1.name != dir2.name, "Mã định danh hai lượt đánh giá không được trùng nhau"

    # Đọc nhật ký episodes.csv của hai lượt chạy
    ep_file1 = dir1 / "episodes.csv"
    ep_file2 = dir2 / "episodes.csv"
    assert ep_file1.is_file(), f"Không tìm thấy episodes.csv tại {ep_file1}"
    assert ep_file2.is_file(), f"Không tìm thấy episodes.csv tại {ep_file2}"

    with ep_file1.open("r", encoding="utf-8") as f1, ep_file2.open("r", encoding="utf-8") as f2:
        rows1 = list(csv.DictReader(f1))
        rows2 = list(csv.DictReader(f2))

    assert len(rows1) == len(rows2), "Số lượng tập phim giữa hai lượt chạy phải bằng nhau"
    assert len(rows1) > 0, "Tập phim không được rỗng"

    rand_rows1 = [r for r in rows1 if r["policy"] == "random"]
    rand_rows2 = [r for r in rows2 if r["policy"] == "random"]
    assert len(rand_rows1) == len(rand_rows2), "Số tập phim random policy phải bằng nhau"

    # 004 INV-007, 004 NFR-REPRO-001: Chuỗi hành động random policy phải giống hệt nhau từng phần tử
    action_columns = ["act_m0", "act_m1", "act_m2", "act_m3", "act_m4", "act_m5", "effort"]
    for idx, (r1, r2) in enumerate(zip(rand_rows1, rand_rows2, strict=True)):
        assert r1["seed"] == r2["seed"], f"Episode {idx}: Hạt giống phải trùng nhau"
        assert r1["n_steps"] == r2["n_steps"], f"Episode {idx}: Số bước mô phỏng phải trùng nhau"
        assert r1["reached"] == r2["reached"], f"Episode {idx}: Trạng thái reached phải trùng nhau"
        for col in action_columns:
            val1 = float(r1[col])
            val2 = float(r2[col])
            assert val1 == val2, (
                f"Episode {idx}: Cột {col} của random policy không đồng nhất bit-bit: "
                f"{val1} != {val2} (004 INV-007)"
            )

    # Đọc báo cáo report.json của hai lượt chạy
    rep_file1 = dir1 / "report.json"
    rep_file2 = dir2 / "report.json"
    assert rep_file1.is_file() and rep_file2.is_file()

    report1 = json.loads(rep_file1.read_text(encoding="utf-8"))
    report2 = json.loads(rep_file2.read_text(encoding="utf-8"))

    # 004 NFR-REPRO-001: Kiểm tra dung sai sai số tuyệt đối <= 1e-6 cho mọi chỉ số thống kê
    tolerance = 1e-6

    # So sánh các chỉ số của hai chính sách
    for pol_key in ("learned", "random"):
        pol_res1 = report1["policies"][pol_key]
        pol_res2 = report2["policies"][pol_key]

        metric_keys = [
            "success_rate",
            "final_distance_m",
            "mean_return",
            "effort",
            "abnormal_rate",
        ]
        for m_key in metric_keys:
            m1 = pol_res1[m_key]
            m2 = pol_res2[m_key]

            v1, v2 = m1.get("value"), m2.get("value")
            if v1 is not None and v2 is not None:
                assert math.isclose(float(v1), float(v2), abs_tol=tolerance), (
                    f"Chỉ số {pol_key}.{m_key}.value lệch ngoài dung sai: {v1} vs {v2}"
                )

            ci_low1, ci_low2 = m1.get("ci_low"), m2.get("ci_low")
            if ci_low1 is not None and ci_low2 is not None:
                assert math.isclose(float(ci_low1), float(ci_low2), abs_tol=tolerance), (
                    f"Chỉ số {pol_key}.{m_key}.ci_low lệch ngoài dung sai: {ci_low1} vs {ci_low2}"
                )

            ci_high1, ci_high2 = m1.get("ci_high"), m2.get("ci_high")
            if ci_high1 is not None and ci_high2 is not None:
                assert math.isclose(float(ci_high1), float(ci_high2), abs_tol=tolerance), (
                    f"Chỉ số {pol_key}.{m_key}.ci_high lệch ngoài dung sai: "
                    f"{ci_high1} vs {ci_high2}"
                )

    # So sánh kết quả đối chuẩn comparison
    comp1 = report1["comparison"]
    comp2 = report2["comparison"]
    assert comp1["better"] == comp2["better"]
    assert math.isclose(float(comp1["difference"]), float(comp2["difference"]), abs_tol=tolerance)
    assert math.isclose(float(comp1["ci_low"]), float(comp2["ci_low"]), abs_tol=tolerance)
    assert math.isclose(float(comp1["ci_high"]), float(comp2["ci_high"]), abs_tol=tolerance)


def test_diff_seed_diff_random_actions(tmp_path_factory: pytest.TempPathFactory) -> None:
    """004 NFR-REPRO-001, 004 INV-007, 004 FR-003, 004 AC-1: Khác seed sinh chuỗi hành động khác.

    Thực thi hai lượt đánh giá dòng lệnh (CLI) với hai hạt giống đánh giá khác nhau
    (--eval-seed 1000 và --eval-seed 2000).
    Xác minh: Chuỗi hành động kích thích cơ bắp của chính sách ngẫu nhiên (random policy)
    giữa hai lượt chạy thực sự khác biệt, chứng minh seed chi phối việc lấy mẫu hành động.
    """
    pytest.importorskip("torch", reason="Cần PyTorch để nạp checkpoint và chạy suy luận mô hình")
    pytest.importorskip("pandas", reason="Cần pandas để xử lý bảng số liệu và chỉ số")
    pytest.importorskip("matplotlib", reason="Cần matplotlib để xuất biểu đồ đánh giá")

    tmp_dir = tmp_path_factory.mktemp("eval_determinism_diff_seed")
    run_dir = make_run_dir(tmp_dir, seed=42)
    latest_ckpt = run_dir / "checkpoints" / "latest.json"

    # Lượt 1: Chạy với --eval-seed 1000
    res1 = run_cli(["--checkpoint", str(latest_ckpt), "--eval-seed", "1000"])
    assert res1.returncode in (0, 6)

    # Lượt 2: Chạy với --eval-seed 2000
    res2 = run_cli(["--checkpoint", str(latest_ckpt), "--eval-seed", "2000"])
    assert res2.returncode in (0, 6)

    eval_base_dir = run_dir / "eval"
    eval_subdirs = sorted(
        [p for p in eval_base_dir.iterdir() if p.is_dir() and not p.name.startswith(".tmp-")],
        key=lambda p: p.name,
    )
    assert len(eval_subdirs) == 2

    # Lấy thư mục ứng với từng seed
    dir_1000 = next(p for p in eval_subdirs if "_e1000" in p.name)
    dir_2000 = next(p for p in eval_subdirs if "_e2000" in p.name)

    with (dir_1000 / "episodes.csv").open("r", encoding="utf-8") as f1, (
        dir_2000 / "episodes.csv"
    ).open("r", encoding="utf-8") as f2:
        rows_1000 = [r for r in csv.DictReader(f1) if r["policy"] == "random"]
        rows_2000 = [r for r in csv.DictReader(f2) if r["policy"] == "random"]

    assert len(rows_1000) == len(rows_2000)
    assert len(rows_1000) > 0

    # 004 NFR-REPRO-001, 004 INV-007: Khác --eval-seed phải dẫn tới chuỗi hành động ngẫu nhiên khác
    differing_episodes = 0
    for r1, r2 in zip(rows_1000, rows_2000, strict=True):
        # Kiểm tra khác biệt trên các giá trị kích hoạt cơ bắp
        diff_in_actions = any(
            not math.isclose(float(r1[col]), float(r2[col]), abs_tol=1e-5)
            for col in ["act_m0", "act_m1", "act_m2", "act_m3", "act_m4", "act_m5", "effort"]
        )
        if diff_in_actions:
            differing_episodes += 1

    # Tối thiểu 90% số tập phim phải có hành động khác nhau khi khác hạt giống
    diff_ratio = differing_episodes / len(rows_1000)
    assert diff_ratio >= 0.9, (
        f"004 INV-007: Kỳ vọng đa số tập phim random policy có hành động khác biệt khi khác seed, "
        f"nhưng chỉ có {differing_episodes}/{len(rows_1000)} tập phim khác nhau "
        f"({diff_ratio * 100:.1f}%)"
    )
