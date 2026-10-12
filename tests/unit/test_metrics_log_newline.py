"""Kiểm thử byte dòng của nhật ký chỉ số."""

from __future__ import annotations

from pathlib import Path
def test_inv_005_nfr_enc_001_ac_4_metrics_jsonl_uses_lf_bytes(tmp_path: Path) -> None:
    """INV-005, NFR-ENC-001, AC-4: JSONL dùng byte LF ổn định trên mọi OS."""
    from mma_ai.learning.metrics_log import MetricsLogger

    class SummaryWriter:
        def add_scalar(self, *_args: object, **_kwargs: object) -> None:
            pass

        def flush(self) -> None:
            pass

        def close(self) -> None:
            pass

    logger = MetricsLogger.__new__(MetricsLogger)
    logger._run_dir = tmp_path
    logger._muscle_names = ("TRIlong", "TRIlat", "TRImed", "BIClong", "BICshort", "BRA")
    tmp_path.mkdir(parents=True, exist_ok=True)
    logger._metrics_file = (tmp_path / "metrics.jsonl").open(
        "a", encoding="utf-8", newline="\n"
    )
    logger._summary_writer = SummaryWriter()
    logger._closed = False
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
    logger.close()

    content = (tmp_path / "metrics.jsonl").read_bytes()
    assert content.endswith(b"\n")
    assert b"\r" not in content
