# VP-8122A — physical HIL qualification checklist

**State: NOT EXECUTED / BLOCKED.** Use an actual VP-8122A and qualified GP-IB interface. Unattended RF operation is not authorized merely by offline tests.

1. Record instrument serial and revision; PC OS, Python, PyVISA, VISA backend, GPIB controller type/firmware, selected VISA resource, driver version and manual edition/page.
2. With load properly terminated and external RF measurement instrument attached, prove the actual remote OFF command (`APOF` candidate) has the intended RF effect. Record RF residual, minimum-safe output and independent OFF confirmation. Stop if not verified.
3. Confirm exact native command syntax, permitted token separators, write termination/EOI, 250 ms pacing and talker read framing; record raw byte-level bus traces. Test both command-alone and selected multiple-command messages.
4. Establish accurate supported frequency/level ranges, quantization, 50/75 Ω effects, modulation modes, pilot, stereo and pre-emphasis from exact VP-8122A manual; verify displayed and measured values at boundaries.
5. Read-only connect/read/disconnect tests must not energize RF. Validate GPIB GTL and REN locally on adapter; test recovery from bus timeouts and USB disconnect.
6. With authorized test setup, inject errors after each output programming step, including before RF enable, during enable, during readback and while closing. Verify OFF physically; distinguish `OFF_UNCONFIRMED` from measured RF OFF.
7. Save raw and parsed status, write and read traces, requested vs measured RF frequency/amplitude/modulation, meter calibration, and pass/fail with thresholds approved *before* testing.
8. Review all results independently, record evidence and sign off before marking hardware-qualified. Do not assume `*IDN?`, `*OPC?` or `SYST:ERR?` support.
