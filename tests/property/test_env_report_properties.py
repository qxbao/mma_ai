"""Thuộc tính AC-5 và INV-004 trên các hồ sơ môi trường được sinh."""

from __future__ import annotations

import random

from mma_ai.compat.env_report import build_environment_report
from mma_ai.compat.platform_info import PlatformProfile


def test_inv_004_capability_reason_tracks_availability_for_generated_states() -> None:
    generator = random.Random(604)
    versions = [
        (generator.randint(2, 4), generator.randint(0, 20), generator.randint(0, 99))
        for _ in range(150)
    ]
    for version in versions:
        profile = PlatformProfile("linux", "release", "machine", version, False, True)
        report = build_environment_report(
            profile,
            probes={
                "packages": {
                    "mujoco": None,
                    "myo_sim": None,
                    "gymnasium": None,
                    "numpy": None,
                    "torch": None,
                },
                "display": {
                    "available": generator.choice((True, False)),
                    "reason": "Màn hình không khả dụng.",
                },
                "symlink": {
                    "available": generator.choice((True, False)),
                    "reason": "Không tạo được symlink.",
                },
                "long_paths": {
                    "available": generator.choice((True, False)),
                    "reason": "Không đọc được cấu hình.",
                },
                "ram_peak": {
                    "available": generator.choice((True, False)),
                    "reason": "Không đo được RAM.",
                },
                "utf8_stdio": {
                    "available": generator.choice((True, False)),
                    "reason": "Không hỗ trợ UTF-8.",
                },
            },
        )
        assert all(
            (item["reason"] is None) is item["available"]
            for item in report["capabilities"].values()
        )
        has_failure = any(check["status"] == "fail" for check in report["checks"])
        assert (report["overall"] == "fail") is has_failure


def test_ac_5_wsl_windows_drive_warning_does_not_change_overall_to_failure() -> None:
    profile = PlatformProfile("wsl2", "release", "x86_64", (3, 12, 0), True, True)
    report = build_environment_report(
        profile,
        probes={
            "packages": {
                "mujoco": "3",
                "myo_sim": "0.2",
                "gymnasium": "1",
                "numpy": "2",
                "torch": None,
            },
            "display": {"available": True, "reason": None},
            "symlink": {"available": True, "reason": None},
            "long_paths": {"available": True, "reason": None},
            "ram_peak": {"available": True, "reason": None},
            "utf8_stdio": {"available": True, "reason": None},
            "cwd": chr(47) + "mnt/c/work/project",
        },
    )
    warning = next(check for check in report["checks"] if check["id"] == "wsl_windows_drive")
    assert warning["status"] == "warn"
    assert report["overall"] == "ok"
