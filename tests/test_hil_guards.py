"""Hardware-independent regression for HIL authorization and command allowlisting."""
import pytest

from tests.hil_support import (
    AUTHORIZATION,
    HILGateError,
    HILSettings,
    TalkerOnlyVisaTransport,
)


def valid_env(tmp_path):
    return {
        "VP8122A_HIL_AUTHORIZED": AUTHORIZATION,
        "VP8122A_HIL_RESOURCE": "GPIB0::2::INSTR",
        "VP8122A_HIL_EVIDENCE_DIR": str(tmp_path),
        "VP8122A_HIL_RUN_ID": "hil-sample-001",
        "VP8122A_HIL_SERIAL": "FRONT-PANEL-SERIAL-REQUIRED",
        "VP8122A_HIL_CONTROLLER": "GPIB-USB-CONTROLLER",
        "VP8122A_HIL_OPERATOR": "authorized-operator",
        "VP8122A_HIL_TERMINATION": "LF",
    }


def test_hil_authorization_failure_prevents_hardware_io(tmp_path):
    env = valid_env(tmp_path)
    del env["VP8122A_HIL_AUTHORIZED"]
    with pytest.raises(HILGateError, match="authorization"):
        HILSettings.from_environment(env)


@pytest.mark.parametrize("bad", [
    "USB0::1::INSTR", "GPIB0::2::SOCKET", "GPIB0::31::INSTR",
    "GPIB0::2::INSTR;*RST", "", "GPIB0::2::INSTR\n",
])
def test_hil_rejects_non_target_or_unsafe_resource(tmp_path, bad):
    env = valid_env(tmp_path)
    env["VP8122A_HIL_RESOURCE"] = bad
    with pytest.raises(HILGateError, match="GPIB"):
        HILSettings.from_environment(env)


@pytest.mark.parametrize("change", [
    {"CI": "true"},
    {"VP8122A_HIL_ALLOW_RF_ENABLE": "1"},
    {"VP8122A_HIL_MODES": "0,0"},
    {"VP8122A_HIL_MODES": "0,3"},
    {"VP8122A_HIL_TERMINATION": ""},
    {"VP8122A_HIL_TERMINATION": "AUTO"},
    {"VP8122A_HIL_TIMEOUT_MS": "0"},
    {"VP8122A_HIL_TIMEOUT_MS": "99999"},
    {"VP8122A_HIL_RUN_ID": "../unsafe"},
    {"VP8122A_HIL_SERIAL": ""},
    {"VP8122A_HIL_EVIDENCE_DIR": "/definitely/not/a/path"},
])
def test_hil_rejects_incomplete_or_unsafe_configuration(tmp_path, change):
    env = valid_env(tmp_path)
    env.update(change)
    with pytest.raises(HILGateError):
        HILSettings.from_environment(env)


def test_config_requires_separate_explicit_framing_and_bench_identity(tmp_path):
    env = valid_env(tmp_path)
    env["VP8122A_HIL_MODES"] = "0,1,2"
    config = HILSettings.from_environment(env)
    assert config.modes == (0, 1, 2)
    assert config.termination == "\n"
    assert config.timeout_ms == 2000


@pytest.mark.parametrize("data", [
    b"*IDN?", b"*RST\n", b"SYST:ERR?\n", b"OUTP ON\n",
    b"GTL", b"APOF\n", b"APON\n", b"FR1MZ\n",
    b"TM0", b"TM1\r\n", b"TM3\n", b"TM0\nAPOF",
])
def test_hil_transport_blocks_every_non_talker_payload_before_io(data):
    transport = TalkerOnlyVisaTransport(
        "GPIB0::2::INSTR", termination="\n", timeout_s=0.5
    )
    # Resource remains CREATED: exercising the guard never opens any VISA handle.
    with pytest.raises(HILGateError):
        transport.write(data)
    assert transport.attempted_bytes == []


def test_hil_talker_bytes_allowed_but_no_implicit_open():
    from scpi_driver_core.exceptions import NotConnectedError
    transport = TalkerOnlyVisaTransport(
        "GPIB0::2::INSTR", termination="\n", timeout_s=0.5
    )
    with pytest.raises(NotConnectedError):
        transport.write(b"TM0\n")
    assert transport.attempted_bytes == [b"TM0\n"]
