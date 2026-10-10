"""Kiểm thử tích hợp qua giao diện dòng lệnh (CLI) đánh giá thật (T415).

Hiện thực và xác minh toàn diện các yêu cầu chức năng, bất biến miền và tiêu chí chấp nhận:
- 004 FR-001, 004 AC-1, US1: Đánh giá chính sách đã học (learned policy) so sánh đối chuẩn
  với chính sách ngẫu nhiên (random policy) trên cùng tập mục tiêu kiểm thử.
- 004 FR-002, 004 INV-002: Hai chính sách chạy trên cùng danh sách mục tiêu theo cùng thứ tự,
  cùng số tập phim (episodes), mỗi mục tiêu một tập phim cho mỗi chính sách.
- 004 FR-003, 004 INV-003: Mọi hành động kích thích cơ bắp (muscle excitation) u_i thuộc [0, 1]^6,
  tuyệt đối không điều khiển trực tiếp lực hay toạ độ tay.
- 004 FR-004, 004 FR-005, 004 NFR-STAT-001: Báo cáo đầy đủ bảy nhóm chỉ số kèm khoảng tin cậy
  (confidence interval - CI) 95% cho tỷ lệ thành công và các giá trị trung bình.
- 004 FR-006, 004 SC-001: Kết luận 'tốt hơn' hoặc 'không tốt hơn' theo tiêu chí định sẵn;
  kết luận 'không tốt hơn' vẫn kết thúc với mã thoát 0 hợp chuẩn.
- 004 FR-007, 004 INV-006: Tiêu chí so sánh cố định trong cấu hình và báo cáo; từ chối mọi
  cờ dòng lệnh cố tình ghi đè tiêu chí với mã thoát 2.
- 004 FR-016: Tập phim mất ổn định vật lý (PhysicsInstabilityError) được đếm vào tỷ lệ bất thường
  (abnormal rate), tính là không tới mục tiêu và không làm dừng lượt đánh giá.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from eval_fixtures import make_run_dir, run_cli

from mma_ai.environment.errors import PhysicsInstabilityError
from mma_ai.environment.single_agent import ElbowReachEnv
from mma_ai.evaluation.cli import _build_parser, main
from mma_ai.evaluation.stats import Verdict

# Danh sách 6 cơ bắp chuẩn của mô hình khớp khuỷu tay 1 bậc tự do
_SIX_MUSCLE_NAMES = (
    "BIClong",
    "BICshort",
    "BRA",
    "TRIlong",
    "TRIlat",
    "TRImed",
)


def test_cli_smoke_contract_independent_assertion() -> None:
    """004 FR-001, 004 FR-007, 004 INV-003, 004 INV-006, 004 AC-1: Khẳng định độc lập CLI.

    Bảo đảm bộ kiểm thử không bị bỏ qua toàn bộ khi thiếu phụ thuộc tùy chọn.
    Xác minh bộ phân tích cú pháp CLI hỗ trợ đủ cờ hợp đồng, nghiêm cấm cờ ghi đè
    tiêu chí kết luận, nghiêm cấm cờ nhận lực/toạ độ tay, và cấu hình đóng gói hợp chuẩn.
    """
    # 1. Kiểm tra bộ phân tích cú pháp CLI hỗ trợ đủ các cờ hợp đồng
    parser = _build_parser()
    all_flags = {flag for action in parser._actions for flag in action.option_strings}

    expected_flags = {
        "--checkpoint",
        "--config",
        "--out",
        "--repeats",
        "--eval-seed",
        "--runs-dir",
    }
    assert expected_flags.issubset(all_flags), f"Thiếu cờ: {expected_flags - all_flags}"

    # 2. INV-006: Nghiêm cấm mọi cờ ghi đè tiêu chí kết luận (criterion) hay mức tin cậy
    forbidden_criterion_flags = {
        "--criterion",
        "--confidence-level",
        "--primary-metric",
        "--rule",
        "--alpha",
    }
    for flag in forbidden_criterion_flags:
        assert flag not in all_flags, f"Phát hiện cờ bị cấm theo INV-006: {flag}"

    # 3. INV-003: Nghiêm cấm mọi cờ nhận hành động thô hay toạ độ tay
    forbidden_action_flags = {
        "--action",
        "--actions",
        "--target-pos",
        "--hand-pos",
        "--force",
        "--ctrl",
    }
    for flag in forbidden_action_flags:
        assert flag not in all_flags, f"Phát hiện cờ bị cấm theo INV-003: {flag}"

    # 4. Xác thực tệp cấu hình đóng gói sẵn eval_elbow.yaml
    root_dir = Path(__file__).resolve().parents[2]
    eval_yaml_path = root_dir / "src" / "mma_ai" / "evaluation" / "eval_elbow.yaml"
    assert eval_yaml_path.is_file(), f"Không tìm thấy cấu hình đánh giá: {eval_yaml_path}"
    raw_cfg = yaml.safe_load(eval_yaml_path.read_text(encoding="utf-8"))
    assert isinstance(raw_cfg, dict), "Cấu hình eval_elbow.yaml phải là ánh xạ (mapping)"
    assert raw_cfg["criterion"]["primary_metric"] == "success_rate"
    assert raw_cfg["criterion"]["confidence_level"] == 0.95
    assert raw_cfg["episodes"]["repeats"] == 1
    assert raw_cfg["episodes"]["min_targets"] == 2


@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def shared_eval_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Thực thi duy nhất một lượt đánh giá CLI thật hoàn chỉnh với mô hình MuJoCo thật (T415).

    Chia sẻ kết quả dữ liệu (báo cáo report.json và nhật ký episodes.csv) giữa các bài kiểm thử
    để tối ưu hoá thời gian thực thi của bộ kiểm thử mà vẫn bảo đảm tính toàn vẹn end-to-end.
    """
    pytest.importorskip("torch", reason="Cần PyTorch để thực hiện nạp checkpoint và suy luận")
    pytest.importorskip("pandas", reason="Cần pandas để xử lý chỉ số và dữ liệu nhật ký")
    pytest.importorskip("matplotlib", reason="Cần matplotlib để kết xuất bộ ba biểu đồ")

    tmp_dir = tmp_path_factory.mktemp("cli_eval_integration")
    run_dir = make_run_dir(tmp_dir, seed=42)
    latest_ckpt = run_dir / "checkpoints" / "latest.json"

    # Thực thi dòng lệnh đánh giá qua tiến trình con không màn hình (headless subprocess)
    cli_result = run_cli(["--checkpoint", str(latest_ckpt)])
    assert cli_result.returncode == 0, (
        f"Lệnh CLI đánh giá thất bại với mã {cli_result.returncode}.\n"
        f"Stdout: {cli_result.stdout}\nStderr: {cli_result.stderr}"
    )

    # Định vị thư mục kết quả đánh giá runs/<run_id>/eval/<eval_id>/
    eval_base_dir = run_dir / "eval"
    assert eval_base_dir.is_dir(), f"Thư mục eval không được tạo tại: {eval_base_dir}"
    subdirs = [p for p in eval_base_dir.iterdir() if p.is_dir() and not p.name.startswith(".tmp-")]
    assert len(subdirs) == 1, f"Kỳ vọng đúng 1 thư mục hoàn tất, tìm thấy: {subdirs}"
    eval_dir = subdirs[0]

    # Đọc báo cáo hoàn chỉnh report.json
    report_file = eval_dir / "report.json"
    assert report_file.is_file(), f"Không tìm thấy tệp report.json: {report_file}"
    report_data = json.loads(report_file.read_text(encoding="utf-8"))

    # Đọc nhật ký chi tiết các tập phim episodes.csv
    episodes_file = eval_dir / "episodes.csv"
    assert episodes_file.is_file(), f"Không tìm thấy tệp episodes.csv: {episodes_file}"
    with episodes_file.open("r", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))

    return {
        "run_dir": run_dir,
        "eval_dir": eval_dir,
        "latest_ckpt": latest_ckpt,
        "report": report_data,
        "episodes": csv_rows,
        "cli_result": cli_result,
    }


def test_both_policies_same_targets(shared_eval_run: dict[str, Any]) -> None:
    """004 FR-001, 004 FR-002, 004 INV-002, 004 AC-1: Cùng tập mục tiêu và cùng thứ tự.

    Kiểm tra:
    - Cùng số tập phim = số mục tiêu kiểm thử × số lần lặp (repeats=1 -> 50 tập phim mỗi policy).
    - Mỗi mục tiêu kiểm thử được chạy đúng một tập phim cho mỗi chính sách.
    - Thứ tự các mục tiêu kiểm thử và hạt giống khởi tạo hoàn toàn đồng nhất giữa hai chính sách.
    """
    rows: list[dict[str, str]] = shared_eval_run["episodes"]
    learned_rows = [r for r in rows if r["policy"] == "learned"]
    random_rows = [r for r in rows if r["policy"] == "random"]

    # 1. Số tập phim bằng nhau và khớp số mục tiêu kiểm thử
    assert len(learned_rows) == 50, f"Số tập phim learned phải là 50, nhận {len(learned_rows)}"
    assert len(random_rows) == 50, f"Số tập phim random phải là 50, nhận {len(random_rows)}"

    # 2. Mỗi mục tiêu trong tập kiểm thử (chỉ mục 0..49) xuất hiện đúng một lần cho mỗi chính sách
    learned_targets = [int(r["target_index"]) for r in learned_rows]
    random_targets = [int(r["target_index"]) for r in random_rows]
    expected_targets = list(range(50))

    assert sorted(learned_targets) == expected_targets, (
        "Chính sách learned không bao phủ đầy đủ toàn bộ 50 mục tiêu kiểm thử"
    )
    assert sorted(random_targets) == expected_targets, (
        "Chính sách random không bao phủ đầy đủ toàn bộ 50 mục tiêu kiểm thử"
    )

    # 3. INV-002: Ghép cặp nhất quán — cùng thứ tự mục tiêu và cùng hạt giống theo từng cặp tập phim
    for i in range(50):
        l_target = int(learned_rows[i]["target_index"])
        r_target = int(random_rows[i]["target_index"])
        assert l_target == r_target, (
            f"Lệch thứ tự mục tiêu tại tập phim {i}: learned={l_target}, random={r_target}"
        )

        l_seed = int(learned_rows[i]["seed"])
        r_seed = int(random_rows[i]["seed"])
        assert l_seed == r_seed, (
            f"Lệch hạt giống ngẫu nhiên tại tập phim {i}: learned={l_seed}, random={r_seed}"
        )


def test_all_metrics_present_with_ci(shared_eval_run: dict[str, Any]) -> None:
    """004 FR-004, 004 FR-005, 004 NFR-STAT-001, 004 AC-1: Đủ 7 nhóm chỉ số kèm khoảng tin cậy.

    Xác minh báo cáo có đầy đủ:
    1. Tỷ lệ thành công (success_rate) kèm khoảng tin cậy 95% Wilson.
    2. Khoảng cách cuối cùng (final_distance_m) kèm khoảng tin cậy 95% Bootstrap.
    3. Phần thưởng trung bình (mean_return) kèm khoảng tin cậy 95% Bootstrap.
    4. Nỗ lực điều khiển (effort) và kích hoạt của toàn bộ 6 cơ bắp (activation_per_muscle).
    5. Tỷ lệ kết thúc bất thường (abnormal_rate).
    6. Số lượng giá trị NaN (nan_count).
    7. Số lượng giá trị vô cực (inf_count).
    """
    report: dict[str, Any] = shared_eval_run["report"]
    policies = report.get("policies", {})
    assert "learned" in policies and "random" in policies, "Báo cáo phải chứa cả hai chính sách"

    # Kiểm tra danh sách 6 cơ bắp trong hồ sơ mô hình
    model_muscles = report.get("model", {}).get("muscle_names", [])
    assert len(model_muscles) == 6, f"Kỳ vọng 6 cơ bắp trong mô hình, thực tế: {model_muscles}"
    for muscle in _SIX_MUSCLE_NAMES:
        assert muscle in model_muscles, f"Thiếu tên cơ {muscle} trong danh sách cơ của mô hình"

    for pol_key in ("learned", "random"):
        pol_data = policies[pol_key]

        # Nhóm 1: Tỷ lệ thành công kèm CI [0, 1]
        sr = pol_data.get("success_rate", {})
        assert sr.get("value") is not None, f"Thiếu giá trị success_rate cho {pol_key}"
        assert 0.0 <= sr["value"] <= 1.0, f"success_rate ngoài khoảng [0, 1]: {sr['value']}"
        assert sr.get("ci_low") is not None and sr.get("ci_high") is not None
        assert 0.0 <= sr["ci_low"] <= sr["value"] <= sr["ci_high"] <= 1.0, (
            f"Khoảng tin cậy success_rate không hợp lệ: [{sr['ci_low']}, {sr['ci_high']}]"
        )

        # Nhóm 2: Khoảng cách cuối episode kèm CI Bootstrap
        dist = pol_data.get("final_distance_m", {})
        assert dist.get("value") is not None, f"Thiếu giá trị final_distance_m cho {pol_key}"
        assert dist["value"] >= 0.0, f"Khoảng cách không thể âm: {dist['value']}"
        assert dist.get("ci_low") is not None and dist.get("ci_high") is not None
        assert dist["ci_low"] <= dist["ci_high"], (
            f"Cận dưới CI khoảng cách lớn hơn cận trên: [{dist['ci_low']}, {dist['ci_high']}]"
        )

        # Nhóm 3: Phần thưởng trung bình kèm CI Bootstrap
        ret = pol_data.get("mean_return", {})
        assert ret.get("value") is not None, f"Thiếu giá trị mean_return cho {pol_key}"
        assert ret.get("ci_low") is not None and ret.get("ci_high") is not None
        assert ret["ci_low"] <= ret["ci_high"], (
            f"Cận dưới CI phần thưởng lớn hơn cận trên: [{ret['ci_low']}, {ret['ci_high']}]"
        )

        # Nhóm 4: Nỗ lực điều khiển và mức kích hoạt 6 cơ bắp (activation_per_muscle)
        eff = pol_data.get("effort", {})
        assert eff.get("value") is not None, f"Thiếu giá trị effort cho {pol_key}"
        assert eff["value"] >= 0.0, f"Nỗ lực không thể âm: {eff['value']}"

        acts = pol_data.get("activation_per_muscle", [])
        assert isinstance(acts, list) and len(acts) == 6, (
            f"activation_per_muscle phải là mảng 6 phần tử, nhận: {acts}"
        )
        for idx, act_val in enumerate(acts):
            assert act_val is not None, f"Giá trị kích hoạt cơ thứ {idx} không được để trống"
            assert 0.0 <= float(act_val) <= 1.0, (
                f"Kích hoạt cơ thứ {idx} ({model_muscles[idx]}) ngoài [0, 1]: {act_val}"
            )

        # Nhóm 5: Tỷ lệ kết thúc bất thường
        abn = pol_data.get("abnormal_rate", {})
        assert abn.get("value") is not None, f"Thiếu abnormal_rate cho {pol_key}"
        assert 0.0 <= abn["value"] <= 1.0

        # Nhóm 6 & 7: Số lượng NaN và Inf
        nan_count = pol_data.get("nan_count")
        assert nan_count is not None and nan_count >= 0
        inf_count = pol_data.get("inf_count")
        assert inf_count is not None and inf_count >= 0

    # Đối chiếu kết luận so sánh (comparison)
    comp = report.get("comparison", {})
    assert comp.get("metric") == "success_rate"
    assert comp.get("confidence_level") == 0.95
    assert comp.get("difference") is not None
    assert comp.get("ci_low") is not None and comp.get("ci_high") is not None
    assert comp["ci_low"] <= comp["ci_high"]
    assert isinstance(comp.get("better"), bool)


def test_actions_in_unit_interval(shared_eval_run: dict[str, Any]) -> None:
    """004 FR-003, 004 INV-003, 004 AC-1: Mọi hành động của cả hai chính sách đều trong [0, 1]^6.

    Đọc trực tiếp từ tệp episodes.csv để kiểm tra toàn bộ các giá trị kích hoạt cơ bắp
    act_m0 đến act_m5 của tất cả các tập phim thuộc cả hai chính sách.
    """
    rows: list[dict[str, str]] = shared_eval_run["episodes"]
    assert len(rows) > 0, "Tệp episodes.csv không có dữ liệu"

    for r in rows:
        policy_name = r["policy"]
        ep_idx = r["episode"]
        for m_idx in range(6):
            col_name = f"act_m{m_idx}"
            raw_val = r[col_name]
            act_val = float(raw_val)
            assert 0.0 <= act_val <= 1.0, (
                f"Phát hiện hành động cơ vi phạm INV-003: {col_name}={act_val} "
                f"ở chính sách '{policy_name}', tập phim {ep_idx} (kỳ vọng trong đoạn [0, 1])"
            )


def test_criterion_in_report_and_no_override_flag(shared_eval_run: dict[str, Any]) -> None:
    """004 FR-007, 004 INV-006, 004 AC-1: Tiêu chí trong báo cáo và cờ ghi đè bị từ chối mã 2.

    Kiểm tra:
    - Báo cáo lưu trữ nguyên văn tiêu chí đánh giá ban đầu từ cấu hình.
    - Mọi nỗ lực truyền cờ dòng lệnh ghi đè tiêu chí (--criterion, --confidence-level, ...)
      đều bị chặn tại biên và thoát với mã lỗi 2.
    """
    report: dict[str, Any] = shared_eval_run["report"]
    latest_ckpt: Path = shared_eval_run["latest_ckpt"]

    # 1. Tiêu chí kết luận được lưu nguyên văn trong cấu hình của báo cáo
    crit = report.get("config", {}).get("criterion", {})
    assert crit.get("primary_metric") == "success_rate"
    assert crit.get("confidence_level") == 0.95

    # 2. Cố tình truyền cờ ghi đè tiêu chí qua dòng lệnh phải bị từ chối với mã 2
    forbidden_flag_combinations = [
        ["--criterion", "mean_return"],
        ["--confidence-level", "0.99"],
        ["--primary-metric", "final_distance_m"],
    ]

    for extra_flags in forbidden_flag_combinations:
        run_res = run_cli(["--checkpoint", str(latest_ckpt), *extra_flags])
        assert run_res.returncode == 2, (
            f"Kỳ vọng mã thoát 2 khi truyền cờ cấm {extra_flags}, "
            f"thực tế nhận {run_res.returncode}.\nStderr: {run_res.stderr}"
        )
        assert (
            "unrecognized arguments" in run_res.stderr.lower()
            or "lỗi tham số" in run_res.stderr.lower()
        ), f"Thông báo lỗi không nêu rõ tham số không hợp lệ: {run_res.stderr}"


def test_abnormal_episode_counted_not_fatal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """004 FR-016, 004 AC-1: Mất ổn định vật lý (PhysicsInstabilityError) được đếm, lượt không dừng.

    Sử dụng monkeypatch tiêm ngoại lệ PhysicsInstabilityError vào ElbowReachEnv.step:
    - Lượt đánh giá không bị sụp đổ (thoát mã 0 thành công).
    - Tập phim gặp lỗi được đánh dấu abnormal=True và reached=False.
    - Tỷ lệ abnormal_rate trong báo cáo phản ánh chính xác sự cố bất thường.
    """
    pytest.importorskip("torch", reason="Cần PyTorch để thực hiện đánh giá")
    pytest.importorskip("pandas", reason="Cần pandas để xử lý chỉ số và dữ liệu nhật ký")
    pytest.importorskip("matplotlib", reason="Cần matplotlib để kết xuất biểu đồ")

    run_dir = make_run_dir(tmp_path / "abnormal_test_run", seed=42)
    latest_ckpt = run_dir / "checkpoints" / "latest.json"

    orig_step = ElbowReachEnv.step
    fault_injected = False

    def faulty_step(self: Any, action: Any) -> Any:
        nonlocal fault_injected
        # Tiêm ngoại lệ mất ổn định vật lý đúng một lần duy nhất tại bước thứ 3 của lượt chạy
        if not fault_injected:
            fault_injected = True
            raise PhysicsInstabilityError(
                "Mô phỏng mất ổn định vật lý MuJoCo qacc vượt ngưỡng (kiểm thử tích hợp T415)"
            )
        return orig_step(self, action)

    # Tiêm lỗi mất ổn định vào phương thức step của môi trường
    monkeypatch.setattr(ElbowReachEnv, "step", faulty_step)

    # Chạy CLI qua điểm vào main in-process
    exit_code = main(["--checkpoint", str(latest_ckpt)])
    assert exit_code == 0, f"Lượt đánh giá không được sụp đổ, nhận mã {exit_code}"
    assert fault_injected, "Lỗi mất ổn định vật lý phải được kích hoạt trong bài kiểm thử"

    # Đọc kết quả trong thư mục eval
    eval_base_dir = run_dir / "eval"
    subdirs = [p for p in eval_base_dir.iterdir() if p.is_dir() and not p.name.startswith(".tmp-")]
    assert len(subdirs) == 1
    eval_dir = subdirs[0]

    report_data = json.loads((eval_dir / "report.json").read_text(encoding="utf-8"))
    learned_abnormal_rate = report_data["policies"]["learned"]["abnormal_rate"]["value"]
    assert learned_abnormal_rate > 0.0, (
        f"Tỷ lệ abnormal_rate của learned phải > 0, nhận: {learned_abnormal_rate}"
    )

    # Xác minh trong episodes.csv
    with (eval_dir / "episodes.csv").open("r", encoding="utf-8") as f:
        ep_rows = list(csv.DictReader(f))

    abnormal_episodes = [r for r in ep_rows if r["abnormal"] == "True"]
    assert len(abnormal_episodes) >= 1, "Phải có ít nhất một tập phim được đánh dấu abnormal=True"

    first_abnormal = abnormal_episodes[0]
    assert first_abnormal["reached"] == "False", (
        "Tập phim bất thường phải tính là không tới mục tiêu"
    )
    assert first_abnormal["end_reason"] == "instability", "Lý do kết thúc phải là 'instability'"


def test_exit0_for_not_better_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """004 FR-001, 004 FR-006, 004 SC-001, 004 AC-1: Kết luận 'không tốt hơn' vẫn thoát mã 0.

    Xác minh:
    - Khi kết quả thống kê đưa ra kết luận better=False (không tốt hơn chính sách ngẫu nhiên).
    - Mã thoát của dòng lệnh CLI vẫn tuyệt đối là 0 (kết luận khoa học hợp lệ, không phải lỗi).
    - Đầu ra stdout in rõ chuỗi tóm tắt 'Không tốt hơn chính sách ngẫu nhiên'.
    """
    pytest.importorskip("torch", reason="Cần PyTorch để thực hiện đánh giá")
    pytest.importorskip("pandas", reason="Cần pandas để xử lý chỉ số và dữ liệu nhật ký")
    pytest.importorskip("matplotlib", reason="Cần matplotlib để kết xuất biểu đồ")

    run_dir = make_run_dir(tmp_path / "not_better_run", seed=42)
    latest_ckpt = run_dir / "checkpoints" / "latest.json"

    # Giả lập kết quả so sánh thống kê đưa ra kết luận không tốt hơn (better=False)
    def fake_decide(learned_res: Any, random_res: Any, level: float = 0.95) -> Verdict:
        return Verdict(
            better=False,
            difference=0.0,
            ci_low=-0.05,
            ci_high=0.05,
            method="newcombe_wilson_hybrid",
        )

    monkeypatch.setattr("mma_ai.evaluation.runner.decide", fake_decide)

    # Chạy CLI qua hàm main
    exit_code = main(["--checkpoint", str(latest_ckpt)])
    assert exit_code == 0, f"Kỳ vọng mã thoát 0 nhưng nhận {exit_code}"

    # Đọc kết quả trong thư mục eval
    eval_base_dir = run_dir / "eval"
    subdirs = [p for p in eval_base_dir.iterdir() if p.is_dir() and not p.name.startswith(".tmp-")]
    assert len(subdirs) == 1
    eval_dir = subdirs[0]

    report_data = json.loads((eval_dir / "report.json").read_text(encoding="utf-8"))
    assert report_data["comparison"]["better"] is False, (
        "Kết luận trong báo cáo phải là better=False"
    )
    assert report_data["status"] == "done", "Trạng thái báo cáo vẫn phải là 'done'"

    captured = capsys.readouterr()
    assert (
        "không tốt hơn" in captured.out.lower()
        or "not better" in captured.out.lower()
    ), "Đầu ra stdout phải nêu rõ kết luận không tốt hơn chính sách ngẫu nhiên"
