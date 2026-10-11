"""Thuộc tính INV-005 cho đường dẫn bản ghi được sinh ngẫu nhiên."""

import random
import string
from importlib import import_module


def test_inv_005_generated_record_paths_remain_relative_and_portable() -> None:
    module = import_module("mma_ai.compat.pathrules")
    convert = getattr(module, "to_record_path", None)
    assert callable(convert), "Thiếu API to_record_path cho INV-005"
    rng = random.Random(607)
    alphabet = string.ascii_letters + string.digits + "_-"
    for _ in range(100):
        components = [
            "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 12)))
            for _ in range(4)
        ]
        result = convert("/".join(components), base="/workspace")
        assert result == "/".join(components)
        assert "\\" not in result
        assert ":" not in result
        assert not result.startswith("/")
