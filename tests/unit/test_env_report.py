"""Kiểm tra AC-5, INV-004 và hợp đồng API-PLT-0008."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from mma_ai.compat.env_report import build_environment_report, main, render_text
from mma_ai.compat.platform_info import PlatformProfile


def _profile(
    kind: str = "linux", tested: bool = True, version: tuple[int, int, int] = (3, 12, 1)
) -> PlatformProfile:
    return PlatformProfile(kind, "test-release", "x86_64", version, kind == "wsl2", tested)  # type: ignore[arg-type]


def _probes() -> dict[str, object]:
    return {
        "packages": {
            "mujoco": "3.1",
            "myo_sim": "0.2",
            "gymnasium": "1.4",
            "numpy": "2.0",
            "torch": None,
        },
        "display": {"available": True, "reason": None},
        "symlink": {"available": False, "reason": "Không tạo được liên kết."},
        "long_paths": {"available": True, "reason": None},
        "ram_peak": {"available": True, "reason": None},
        "utf8_stdio": {"available": True, "reason": None},
        "cwd": "/var/tmp/test/project",
    }


def test_wsl_kind_and_flag_agree() -> None:
    report = build_environment_report(_profile("wsl2"), probes=_probes())
    assert report["os"]["kind"] == "wsl2"
    assert report["os"]["is_wsl"] is True


def test_ac_5_report_matches_contract_schema() -> None:
    report = build_environment_report(_profile(), probes=_probes())
    schema_path = (
        Path(__file__).parents[2]
        / "specs"
        / "006-cross-platform-support"
        / "contracts"
        / "check-env-report.schema.json"
    )
    validate(report, json.loads(schema_path.read_text(encoding="utf-8")))


def test_python_range_check() -> None:
    for version, supported in [
        ((3, 10, 9), False),
        ((3, 11, 0), True),
        ((3, 12, 99), True),
        ((3, 13, 0), False),
    ]:
        report = build_environment_report(_profile(version=version), probes=_probes())
        assert report["python"]["supported"] is supported
        statuses = [
            check["status"] for check in report["checks"] if check["id"] == "python_version"
        ]
        assert statuses == (["ok"] if supported else ["fail"])


def test_torch_absent_is_warning() -> None:
    report = build_environment_report(_profile(), probes=_probes())
    assert report["packages"]["torch"] is None
    assert report["torch_device"] is None
    assert (
        next(check for check in report["checks"] if check["id"] == "package_torch")["status"]
        == "warn"
    )


def test_capability_reason_contract() -> None:
    report = build_environment_report(_profile(), probes=_probes())
    for capability in report["capabilities"].values():
        assert (capability["reason"] is None) is capability["available"]


def test_untested_configuration_warns() -> None:
    report = build_environment_report(_profile("windows", tested=False), probes=_probes())
    assert (
        next(check for check in report["checks"] if check["id"] == "tested_configuration")["status"]
        == "warn"
    )


def test_report_has_no_absolute_paths() -> None:
    probes = _probes()
    probes["display"] = {"available": False, "reason": "Lỗi tại /var/tmp/private/project/cache."}
    report = build_environment_report(_profile(), probes=probes)
    assert "/var/tmp/test/project" not in json.dumps(report)
    assert "/var/tmp/private/project" not in json.dumps(report)


def test_report_overall_matches_check_failures() -> None:
    for version in ((3, 10, 0), (3, 11, 2), (3, 12, 4), (3, 13, 1)):
        report = build_environment_report(_profile(version=version), probes=_probes())
        failed = any(check["status"] == "fail" for check in report["checks"])
        assert (report["overall"] == "fail") is failed


def test_render_text_has_one_line_per_check() -> None:
    report = build_environment_report(_profile(), probes=_probes())
    rendered = render_text(report)
    assert sum(
        line.startswith(("[ok]", "[CẢNH BÁO]", "[LỖI]")) for line in rendered.splitlines()
    ) == len(report["checks"])


def test_cli_json_is_single_object_and_exit_follows_overall(capsys) -> None:
    status = main(["--json"])
    captured = capsys.readouterr()
    decoded = json.loads(captured.out)
    assert decoded["overall"] in {"ok", "fail"}
    assert status == (1 if decoded["overall"] == "fail" else 0)
    assert captured.out.count("\n") == 1


def test_cli_unknown_option_returns_two(capsys) -> None:
    assert main(["--unknown"]) == 2
    assert "--unknown" in capsys.readouterr().err
