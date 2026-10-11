"""Trace: API-PLT-0005 / INV-003 / INV-005 / AC-4."""

import random
from importlib import import_module, util
from pathlib import Path


def test_inv_003_generated_byte_payloads_replace_atomically(tmp_path: Path) -> None:
    module_spec = util.find_spec("mma_ai.compat.fsio")
    assert module_spec is not None, "Thiếu mô-đun fsio cho INV-003"
    module = import_module("mma_ai.compat.fsio")
    write_bytes = getattr(module, "write_bytes_atomic", None)
    assert callable(write_bytes), "Thiếu API write_bytes_atomic cho INV-003"

    rng = random.Random(608)
    for index in range(100):
        payload = rng.randbytes(rng.randint(0, 2048))
        destination = tmp_path / f"payload-{index}.bin"
        destination.write_bytes(b"old")

        write_bytes(destination, payload)

        assert destination.read_bytes() == payload
        assert all(path.suffix != ".tmp" for path in tmp_path.iterdir())
