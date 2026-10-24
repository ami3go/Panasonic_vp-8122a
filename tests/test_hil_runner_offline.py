"""No-hardware regressions for the opt-in GPIB HIL orchestrator."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from tests.hil_runner import execute
from tests.hil_support import HILGateError, HILSettings, TalkerOnlyVisaTransport


@pytest.mark.parametrize("environment", [
    {"GITHUB_ACTIONS": "true"}, {"GITLAB_CI": "true"},
    {"TF_BUILD": "true"}, {"BUILDKITE": "true"},
    {"JENKINS_URL": "https://ci.example/"},
])
def test_hardware_authorization_is_denied_in_additional_ci_environments(
    tmp_path, environment
):
    from tests.test_hil_guards import valid_env
    variables = valid_env(tmp_path)
    variables.update(environment)
    with pytest.raises(HILGateError, match="CI"):
        HILSettings.from_environment(variables)


def test_unselected_talker_mode_blocked_before_backend():
    from scpi_driver_core.exceptions import NotConnectedError
    transport = TalkerOnlyVisaTransport(
        "GPIB0::2::INSTR", termination="\n", timeout_s=0.5, allowed_modes=(0,)
    )
    with pytest.raises(HILGateError):
        transport.write(b"TM1\n")
    assert transport.attempted_bytes == []
    with pytest.raises(NotConnectedError):
        transport.write(b"TM0\n")
    assert transport.attempted_bytes == [b"TM0\n"]


@pytest.mark.parametrize("modes", [(0, 0), (0, 3), (), (True,), (0, "1")])
def test_invalid_explicit_talker_permissions_rejected(modes):
    with pytest.raises(HILGateError):
        TalkerOnlyVisaTransport(
            "GPIB0::2::INSTR", termination="\n",
            timeout_s=0.5, allowed_modes=modes
        )


def test_hil_runner_produces_reports_but_never_claims_physical_pass(
    tmp_path, monkeypatch
):
    from tests import hil_runner
    def mocked_run(*args, **kwargs):
        assert kwargs["timeout"] == 40
        assert kwargs["capture_output"] is True
        assert "-m" in args[0]
        assert "hardware" in args[0]
        return subprocess.CompletedProcess(args[0], 1, "1 failed", "meter unavailable")
    monkeypatch.setattr(hil_runner.subprocess, "run", mocked_run)
    settings = HILSettings(
        resource="GPIB0::2::INSTR", evidence_dir=tmp_path,
        run_id="unit-run-01", instrument_serial="synthetic",
        controller="synthetic", operator="test-only", termination="\n",
        modes=(0,), timeout_ms=1000
    )
    result = execute(settings=settings, report_dir=tmp_path)
    assert result == 1
    reports = list(tmp_path.glob("vp8122a_qualification_unit-run-01.*"))
    assert {x.suffix for x in reports} == {".json", ".csv", ".md", ".xml"}
    evidence = json.loads(next(x for x in reports if x.suffix == ".json").read_text())
    assert evidence["execution"]["pytest_exit_code"] == 1
    assert evidence["execution"]["physical_rf_qualified"] is False
    assert evidence["physical_qualified_families"] == []
    assert not any(c["physical_hil_status"] == "PASS" for c in evidence["cases"])


def test_run_id_scopes_evidence_and_excludes_prior_runs(tmp_path):
    from tests.hil_reporting import load_talker_observations
    for run_id in ("run-A", "run-B"):
        data = {"result": "OBSERVED", "talker_mode": 0,
                "requested_tx_hex": ["544d300a"]}
        (tmp_path / f"vp8122a_{run_id}_tm0_record.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
    assert len(load_talker_observations(tmp_path, run_id="run-A")) == 1
    assert len(load_talker_observations(tmp_path, run_id="run-B")) == 1
    with pytest.raises(ValueError, match="unsafe run ID"):
        load_talker_observations(tmp_path, run_id="../x")
