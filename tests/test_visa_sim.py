"""PyVISA-sim exercises the real driver->core->PyVISA call path."""
from pathlib import Path

import pytest

from panasonic_vp8122a import VP8122A


@pytest.mark.visa_sim
def test_native_talker_and_safe_close_through_pyvisa_sim():
    import pyvisa

    fixture = Path(__file__).parent / "fixtures" / "panasonic_sim.yaml"
    manager = pyvisa.ResourceManager(str(fixture) + "@sim")
    try:
        driver = VP8122A(
            "GPIB::2::INSTR", resource_manager=manager,
            write_termination="\n", settle_seconds=0,
        )
        driver.connect()
        status = driver.read_status()
        assert status.startswith("FR87.50000MZ")
        assert driver.last_native_status is not None
        assert driver.last_native_status.values("AP") == ("20DB", "50", "ON")
        # No RF-on action, and not a SCPI command or identity request.
        driver.close()
    finally:
        manager.close()
