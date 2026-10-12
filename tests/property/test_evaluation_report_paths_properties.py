"""Kiểm thử thuộc tính 006 INV-005 AC-4 cho đường dẫn trong báo cáo."""

from __future__ import annotations

import random
import string

from mma_ai.compat.pathrules import to_record_path


def test_006_inv_005_ac_4_windows_report_paths_are_portable() -> None:
    rng = random.Random(630)
    alphabet = string.ascii_letters + string.digits + "_-"

    for _ in range(100):
        parts = [
            "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 16)))
            for _ in range(4)
        ]
        windows_path = "C:\\" + "\\".join(parts[:-1]) + "\\" + parts[-1] + ".pt"

        result = to_record_path(windows_path)

        assert result == "/".join([*parts[:-1], parts[-1] + ".pt"])
        assert ":" not in result
        assert "\\" not in result
        assert not result.startswith("/")
