"""Authorized real-instrument VP-8122A talker-mode HIL smoke tests.

Use: python -m pytest -q -m hardware tests/test_hil_authorized.py
No writes other than TM0/TM1/TM2 are possible through its transport.
"""
import pytest

from tests.hil_support import HILSettings, probe_talker_mode


@pytest.mark.hardware
@pytest.mark.timeout(25)
@pytest.mark.parametrize("mode", [0, 1, 2])
def test_authorized_native_talker_only(mode):
    settings = HILSettings.from_environment()
    if mode not in settings.modes:
        pytest.skip(f"TM{mode} not explicitly enabled by VP8122A_HIL_MODES")

    record, path = probe_talker_mode(settings, mode)

    # This is protocol observation, NOT measured RF OFF or electrical release.
    assert record["result"] == "OBSERVED"
    assert record["raw_rx_hex"]
    assert record["qualification"] == "PROTOCOL_OBSERVATION_ONLY"
    assert record["rf_output_measured"] is False
    assert path.is_file()
