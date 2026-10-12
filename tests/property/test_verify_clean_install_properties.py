"""Thuộc tính (property) INV-003 cho tính nguyên vẹn của bản ghi cũ."""

import random
from pathlib import Path

import pytest

from mma_ai.compat import fsio
from mma_ai.compat.fsio import AtomicWriteError
from mma_ai.environment.verify_clean_install import main


def successful_runner(
    cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None
) -> int:
    return 0


def test_inv_003_generated_previous_records_survive_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-003: 100 nội dung byte cũ được giữ nguyên khi thay thế thất bại."""
    project_root = tmp_path
    (project_root / "uv.lock").write_text("# lockfile\n", encoding="utf-8")
    output_path = project_root / "result.json"

    def fail_replace(source: str | Path, destination: str | Path) -> None:
        raise PermissionError("locked")

    assert fsio.replace_atomic.__kwdefaults__ is not None
    monkeypatch.setitem(fsio.replace_atomic.__kwdefaults__, "replace", fail_replace)
    rng = random.Random(631)

    for _ in range(100):
        previous = rng.randbytes(rng.randrange(257))
        output_path.write_bytes(previous)

        with pytest.raises(AtomicWriteError):
            main(
                argv=[],
                runner=successful_runner,
                project_root=project_root,
                output_path=output_path,
            )

        assert output_path.read_bytes() == previous
        assert sorted(path.name for path in project_root.iterdir()) == [
            "result.json",
            "uv.lock",
        ]
