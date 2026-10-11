import subprocess
import sys
from pathlib import Path


def test_train_script_help() -> None:
    """Verify the training script help for FR-001, 003/AC-1."""
    result = subprocess.run([sys.executable, "scripts/train.py", "--help"],
        cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True,
    )
    assert result.returncode == 0 and "--stage" in result.stdout
