"""Kiểm thử đầu-cuối cho năm tiêu chí chấp nhận của đánh giá policy (T424).

Các ca này gọi đúng entrypoint ``python -m mma_ai.evaluation.cli`` trong tiến
trình con.  Bộ chạy E2E của cổng không tự chọn extra tùy chọn, nên lớp bao bọc
gọi ``uv run --isolated --extra rl --extra eval`` từ manifest đã khóa.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _run_worker(tmp_path: Path, mode: str) -> dict[str, Any]:
    """Chạy dữ kiện thật trong môi trường có extra đánh giá và trả JSON kiểm chứng."""
    worker = r'''
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
mode = sys.argv[2]
sys.path.insert(0, str(root / "tests" / "integration"))
from eval_fixtures import make_run_dir, run_cli

work = Path(sys.argv[3])
run_dir = make_run_dir(work / mode, seed=42, with_log=True)
checkpoint = run_dir / "checkpoints" / "latest.json"
if mode == "success":
    result = run_cli(["--checkpoint", str(checkpoint), "--eval-seed", "12345"])
    eval_dirs = sorted(
        path for path in (run_dir / "eval").iterdir()
        if path.is_dir() and not path.name.startswith(".tmp-")
    )
    eval_dir = eval_dirs[0] if eval_dirs else None
    report = (
        json.loads((eval_dir / "report.json").read_text(encoding="utf-8"))
        if eval_dir
        else None
    )
    print(json.dumps({
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "run_dir": str(run_dir),
        "eval_dir": str(eval_dir) if eval_dir else None,
        "report": report,
    }, ensure_ascii=False))
elif mode == "leak":
    result = run_cli(["--checkpoint", str(checkpoint), "--eval-seed", "42"])
    print(json.dumps({
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "eval_exists": (run_dir / "eval").exists(),
        "episodes": len(list(run_dir.rglob("episodes.csv"))),
    }, ensure_ascii=False))
else:
    missing = run_dir / "checkpoints" / "khong-ton-tai.pt"
    result = run_cli(["--checkpoint", str(missing)])
    print(json.dumps({
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "eval_exists": (run_dir / "eval").exists(),
        "episodes": len(list(run_dir.rglob("episodes.csv"))),
        "pngs": len(list(run_dir.rglob("*.png"))),
    }, ensure_ascii=False))
'''
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    completed = subprocess.run(
        [
            "uv",
            "run",
            "--isolated",
            "--extra",
            "rl",
            "--extra",
            "eval",
            "python",
            "-c",
            worker,
            str(PROJECT_ROOT),
            mode,
            str(tmp_path),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    assert completed.returncode == 0, (
        f"Tiến trình dựng kiểm thử E2E lỗi {completed.returncode}:\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    return cast(dict[str, Any], json.loads(completed.stdout))


@pytest.fixture(scope="module")  # type: ignore[untyped-decorator]
def evaluated_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Tạo một lượt đánh giá thật duy nhất, tái sử dụng cho AC-1 đến AC-3."""
    payload = _run_worker(tmp_path_factory.mktemp("e2e_evaluate"), "success")
    assert payload["returncode"] == 0, (
        f"CLI đánh giá lỗi {payload['returncode']}:\n{payload['stderr']}\n{payload['stdout']}"
    )
    assert payload["report"] is not None and payload["eval_dir"] is not None
    return payload


def _capture_chart(chart: Path, name: str) -> None:
    """Đưa ảnh biểu đồ do entrypoint thật sinh vào cổng capture khi cổng đã cấp đường dẫn."""
    capture_dir = os.environ.get("AI_SDLC_CAPTURE_DIR")
    if not capture_dir:
        return
    destination = Path(capture_dir)
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(chart, destination / name)


def test_ac_1_evaluate_both_policies(evaluated_run: dict[str, Any]) -> None:
    """AC-1, FR-001..FR-004, INV-002, SC-001: CLI thật đo hai policy cùng tập mục tiêu."""
    report = evaluated_run["report"]
    assert "KẾT QUẢ ĐÁNH GIÁ CHÍNH SÁCH" in evaluated_run["stdout"]
    policies = report["policies"]
    assert set(policies) == {"learned", "random"}
    for name in ("learned", "random"):
        result = policies[name]
        assert result["success_rate"]["ci_low"] <= result["success_rate"]["value"]
        assert result["success_rate"]["value"] <= result["success_rate"]["ci_high"]
        assert len(result["activation_per_muscle"]) == 6

    eval_dir = Path(evaluated_run["eval_dir"])
    rows = (eval_dir / "episodes.csv").read_text(encoding="utf-8").splitlines()[1:]
    learned = [row.split(",") for row in rows if row.startswith("learned,")]
    random = [row.split(",") for row in rows if row.startswith("random,")]
    assert len(learned) == len(random) == 50
    assert [row[2:4] for row in learned] == [row[2:4] for row in random]


def test_ac_2_verdict_with_ci(evaluated_run: dict[str, Any]) -> None:
    """AC-2, FR-005..FR-007, NFR-STAT-001, INV-006, SC-002: verdict theo CI khai trước."""
    report = evaluated_run["report"]
    criterion = report["criterion"]
    comparison = report["comparison"]
    assert criterion["primary_metric"] == "success_rate"
    assert criterion["confidence_level"] == pytest.approx(0.95)
    assert comparison["ci_low"] <= comparison["difference"] <= comparison["ci_high"]
    assert comparison["better"] is (comparison["ci_low"] > 0.0)
    assert "kết luận" in evaluated_run["stdout"].lower()


def test_ac_3_three_charts(evaluated_run: dict[str, Any]) -> None:
    """AC-3, FR-010..FR-012, NFR-HEADLESS-001, SC-003: đủ ba PNG headless khác rỗng."""
    report = evaluated_run["report"]
    assert report["charts"]["status"] == "complete"
    eval_dir = Path(evaluated_run["eval_dir"])
    for chart_name in ("loss", "reward", "activation"):
        chart = eval_dir / "charts" / f"{chart_name}.png"
        assert chart.read_bytes().startswith(PNG_MAGIC)
        assert chart.stat().st_size > len(PNG_MAGIC)
        _capture_chart(chart, f"AC-3-{chart_name}-headless.png")


def test_ac_4_no_overlap_with_train(tmp_path: Path) -> None:
    """AC-4, FR-008..FR-009, INV-001, SC-004: ghi kiểm tách và chặn seed trùng trước episode."""
    successful = _run_worker(tmp_path, "success")
    assert successful["returncode"] == 0
    disjointness = successful["report"]["disjointness"]
    assert disjointness["passed"] is True
    assert disjointness["n_train_targets"] > 0
    assert disjointness["n_eval_targets"] > 0
    assert 42 in disjointness["train_seeds"]
    assert 42 not in range(*disjointness["eval_seed_range"])

    leaking = _run_worker(tmp_path, "leak")
    assert leaking["returncode"] == 5
    assert "42" in leaking["stderr"]
    assert leaking["eval_exists"] is False
    assert leaking["episodes"] == 0


def test_ac_5_bad_checkpoint(tmp_path: Path) -> None:
    """AC-5, FR-015, INV-004, SC-005: checkpoint thiếu không để lại kết quả trông hợp lệ."""
    result = _run_worker(tmp_path, "missing")
    assert result["returncode"] == 4
    assert "không tồn tại" in result["stderr"].lower()
    assert "KẾT QUẢ ĐÁNH GIÁ CHÍNH SÁCH" not in result["stdout"]
    assert result["eval_exists"] is False
    assert result["episodes"] == 0
    assert result["pngs"] == 0
