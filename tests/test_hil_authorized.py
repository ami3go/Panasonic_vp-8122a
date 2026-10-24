"""Physical GPIB tests are NEVER run by ordinary offline CI.

Run only on an isolated RF bench after confirming output cabling,
terminator/EOI settings and an independent RF measurement device.
"""
import os

import pytest

from panasonic_vp8122a import VP8122A


@pytest.mark.hardware
@pytest.mark.timeout(45)
def test_authorized_native_talker_only():
    if os.getenv("VP8122A_HIL_AUTHORIZED") != "ISOLATED_RF_BENCH_APPROVED":
        pytest.skip("explicit physical RF bench authorization required")
    resource = os.getenv("VP8122A_HIL_RESOURCE", "")
    if not resource.startswith("GPIB") or not resource.endswith("::INSTR"):
        pytest.skip("explicit GPIB instrument VISA address required")

    device = VP8122A(resource, timeout_ms=2000)
    try:
        device.connect()  # no SCPI, no enable
        raw = device.read_status(mode=0)  # sends native TM0 and reads talker
        assert raw and device.last_native_status is not None
        assert device.last_native_status.mode == 0
        assert device.state != "RF_ON_UNCONFIRMED"
    finally:
        # Candidate RF OFF command, not a measured safe output.
        device.close()
