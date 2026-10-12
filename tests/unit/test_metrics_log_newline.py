"""Kiểm thử byte dòng của nhật ký chỉ số."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_regress_t621_inv_005_nfr_enc_001_ac_4_metrics_jsonl_uses_lf_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-005, NFR-ENC-001, AC-4: JSONL dùng byte LF ổn định trên mọi OS."""
    from mma_ai.learning.metrics_log import MetricsLogger

    class SummaryWriter:
        def add_scalar(self, *_args: object, **_kwargs: object) -> None:
            pass

        def flush(self) -> None:
            pass

        def close(self) -> None:
            pass

    real_open = Path.open

    def windows_text_open(
        path: Path,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> object:
        if (
            path == tmp_path / "metrics.jsonl"
            and "b" not in mode
            and newline != "\n"
        ):
            newline = "\r\n"
        return real_open(path, mode, buffering, encoding, errors, newline)

    monkeypatch.setattr(Path, "open", windows_text_open)
    monkeypatch.setattr(
        MetricsLogger,
        "_create_summary_writer",
        staticmethod(lambda _path: SummaryWriter()),
    )
    muscle_names = ("TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA")
    with MetricsLogger(tmp_path, muscle_names) as logger:
        logger.log_update(
            update=3,
            env_steps=6144,
            policy_loss=0.12,
            value_loss=0.34,
            entropy=0.56,
            mean_return=7.8,
            activations=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6),
            env_steps_per_second=42.0,
        )

    content = (tmp_path / "metrics.jsonl").read_bytes()
    assert content.endswith(b"\n")
    assert b"\r" not in content
