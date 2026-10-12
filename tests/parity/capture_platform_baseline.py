"""006: tái tạo mốc Linux (baseline) bằng cùng bộ kiểm thử đầu-cuối (E2E).

Không phải bộ E2E thứ hai; gọi đúng hàm điều phối CLI của T638.
Chỉ ghi dữ liệu mẫu (fixture) trong tests/e2e/data, không ghi bằng chứng của cổng.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def main() -> None:
    """Chạy mã trước compat và lưu mốc đã bỏ đường dẫn riêng của máy."""
    assert sys.platform == "linux", "Mốc phải được đo trên Linux thật"
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "platform_acceptance", root / "tests/e2e/test_platform_acceptance.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    work = Path(tempfile.mkdtemp(prefix=".T638-baseline-", dir=root / "tests/e2e"))
    try:
        archive = work / "baseline.tar"
        subprocess.run(
            [
                "git",
                "archive",
                "--format=tar",
                "--output",
                str(archive),
                module.BASELINE_SHA,
                "src",
            ],
            cwd=root,
            check=True,
        )
        with tarfile.open(archive) as source:
            source.extractall(path=work / "baseline", filter="data")
        records = module._exercise_entrypoints(work / "run", work / "baseline/src")
        artifact = {
            "sha": module.BASELINE_SHA,
            "os": "linux",
            "command": "uv run --isolated --with pytest --extra rl --extra eval python "
            "tests/parity/capture_platform_baseline.py",
            "exit_codes": {
                key: records[key]["returncode"] for key in ("train", "demo", "replay", "benchmark")
            },
            **{key: records[key] for key in ("manifest", "summary", "report")},
        }
        artifact["manifest"]["config"]["paths"]["runs_dir"] = "runs/moc-linux"
        artifact["summary"]["source"]["episode_path"] = "runs/moc-linux/episode.json"
        module.BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
        module.BASELINE_FILE.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({"sha": module.BASELINE_SHA, "exit_codes": artifact["exit_codes"]}))
    finally:
        shutil.rmtree(work)


if __name__ == "__main__":
    main()
