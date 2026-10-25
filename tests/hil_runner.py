"""Opt-in real GPIB TM0/TM1/TM2 runner with automatic offline reporting.

Requires the preexisting HILSettings environment authorization. Does not grant
any RF mutation permission, and runs hardware tests only in a bounded subprocess.
"""
from __future__ import annotations

import argparse
from importlib import metadata
import platform
import subprocess
import sys
from pathlib import Path

from tests.hil_reporting import (
    build_report, load_matrix, load_talker_observations, write_reports,
)
from tests.hil_support import HILSettings

ROOT = Path(__file__).resolve().parents[1]


def execute(*, report_dir: Path, settings: HILSettings) -> int:
    """Run physically authorized native talker tests and preserve fail evidence."""
    command = [sys.executable, "-m", "pytest", "-q", "-m", "hardware",
               "tests/test_hil_authorized.py"]
    # Independent outer watchdog in addition to per-test pytest-timeout.
    deadline_s = 10 + 30 * len(settings.modes)
    exit_code = 124
    stdout = ""
    stderr = ""
    try:
        result = subprocess.run(
            command, cwd=ROOT, timeout=deadline_s, capture_output=True,
            text=True, check=False,
        )
        exit_code = result.returncode
        stdout = result.stdout[-50000:]
        stderr = result.stderr[-50000:]
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", "replace")[-50000:] if isinstance(exc.stdout, bytes) else (exc.stdout or "")[-50000:]
        stderr = (exc.stderr or b"").decode("utf-8", "replace")[-50000:] if isinstance(exc.stderr, bytes) else (exc.stderr or "")[-50000:]
        stderr += "\nOuter subprocess deadline expired: hardware state remains UNKNOWN.\n"
    # The evidence records are persisted independently by each hardware test.
    # No attempt is made to reset the VP-8122A or restore RF output.
    report = build_report(
        load_matrix(),
        load_talker_observations(settings.evidence_dir, run_id=settings.run_id),
        run_id=settings.run_id,
    )
    # A failed/expired subprocess may have accessed hardware before termination.
    # Do not quietly label the selected cases NOT_TESTED when RF/bus state is
    # uncertain. No automatic remediation command is permitted.
    if exit_code != 0:
        selected = {f"TM.{mode}" for mode in settings.modes}
        for row in report["cases"]:
            if row["case_id"] in selected and row["physical_hil_status"] == "NOT_TESTED":
                row["physical_hil_status"] = "INCONCLUSIVE"
                row["notes"] += "; runner failed or timed out before valid evidence"
    try:
        core_version = metadata.version("scpi-driver-core")
    except metadata.PackageNotFoundError:
        core_version = "UNKNOWN"
    report["execution"] = {
        "pytest_exit_code": exit_code,
        "pytest_stdout_tail": stdout,
        "pytest_stderr_tail": stderr,
        "outer_deadline_seconds": deadline_s,
        "python_version": platform.python_version(),
        "core_version": core_version,
        "resource": settings.resource,
        "controller_operator_supplied": settings.controller,
        "instrument_serial_operator_supplied": settings.instrument_serial,
        "operator": settings.operator,
        "authorized_modes": list(settings.modes),
        "measurement_reference": "NONE",
        "physical_rf_qualified": False,
        "bus_eoi_qualified": False,
    }
    paths = write_reports(report, report_dir)
    for ext, path in paths.items():
        print(f"{ext}: {path}")
    if stdout:
        print(stdout[-10000:])
    if stderr:
        print(stderr[-10000:], file=sys.stderr)
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Authorized physical native talker-only HIL; no RF mutation"
    )
    parser.add_argument("--report-dir", required=True, type=Path)
    args = parser.parse_args()
    # Authorization precedes subprocess or any possible physical operation.
    settings = HILSettings.from_environment()
    if not args.report_dir.is_dir():
        parser.error("report directory must already exist")
    return execute(report_dir=args.report_dir, settings=settings)


if __name__ == "__main__":
    raise SystemExit(main())
