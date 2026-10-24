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

## Migrated core driver qualification: v0.2.4 (NOT EXECUTED)

The offline suite covers the `VP8122A → ScpiClient → VisaTransport → PyVISA` stack and includes PyVISA-sim, but cannot prove the bus END line, addressed GTL, RF levels or actual RF OFF. The production driver does not send `*IDN?`, `*RST`, `*OPC?`, `SYST:ERR?`, `OUTP`, or ASCII `GTL`.

### Preconditions (stop unless all are satisfied)

- Obtain written authorization for RF generation, radio-frequency load, measurement equipment, limits and operator.
- Use a protected bench; ensure correctly rated termination, attenuator, external spectrum/RF meter and physical emergency power disconnect.
- Identify VISA address, controller model/firmware, PyVISA backend, serial number, instrument firmware/manual revision, cable/EOI behavior, test run ID and trace/log storage.
- Independently verify the manual's `APOF` / `APON` RF output semantics before any unattended configuration or enabling; baseline candidate OFF *cannot* be treated as measured safe OFF.
- Ensure the selected resource is addressed GPIB `::INSTR` and no other instrument shares unexpected side effects from REN / GTL operations.
- Set `VP8122A_HIL_AUTHORIZED=ISOLATED_RF_BENCH_APPROVED` and `VP8122A_HIL_RESOURCE=<explicit GPIB VISA resource>` only on this physically approved bench.

### Controlled qualification sequence

1. Run **read-only** bus open, `TM0` talker and END-bounded read, then measure the output during the CLOSE-time candidate `APOF` command. Record the raw bytes and physical RF measurement (do not assume `TM0` indicates physical RF state).
2. Verify three native terminator policies separately: EOI-only, LF, CRLF. Capture the actual GPIB END line on the controller or an IEEE-488 analyzer. Record byte-for-byte captures and observed status under each configuration.
3. Verify TM0 ordered field count/values and repeated `AP`, `AM`, `FM`, `CO` families against manual fields 1–25 and front-panel settings. Save full raw reply; verify TM1 and TM2 as distinct mode responses without applying the TM0 parser to them.
4. Request explicit addressed GTL and verify only the addressed VP-8122A changes remote/local state; a different instrument must remain unaffected. Compare with existing global REN deassert operation; do not issue a bus-wide command by accident.
5. With independent frequency/RF-level measurement and permission, verify 10 Hz/20 Hz RF band steps, AM up to 125%, FM at most 300 kHz, FT three resolution bands, 50/75 Ω behavior and profiles in the correct safe order.
6. Inject transport/read/write timeouts and unplug scenarios at each mutation boundary. Confirm no automatic retry of an ON command, no profile replay after reconnect, no SCPI probes, bounded cleanup and human-visible UNKNOWN states.
7. Exercise the `tests/test_hil_authorized.py` guarded suite only after separate approval. This suite is initial protocol reconnaissance, **not** full RF safety qualification. Add real measurement assertions, RF power tolerance, residual OFF limit, emergency OFF and proof of qualified command semantics before accepting the hardware release.
8. Attach signed raw GPIB captures, independent RF measurement results, operator, thresholds, environment and known discrepancies. Mark each requirement PASS / FAIL / NOT_TESTED / INCONCLUSIVE without promoting inferred OFF into confirmed OFF.

Do **not** run the HIL suite in GitHub Actions or an unattended runner.


## v0.2.6 hardware test entry point — protocol observation only

See [HIL automation runbook](HIL_AUTOMATION.md). The added TM0/TM1/TM2 physical readback-only tests explicitly do **not** send APOF, APON or RF configuration, and do **not** call VP8122A.close(), which would transmit unqualified APOF. Their core transport is released without any RF-off attempt. Separately measured, formally authorized APOF/electrical RF OFF remains a distinct future test phase described in the [full task](../task/VP8122A_AUTOMATED_NATIVE_GPIB_HIL_TASK.md). No physical measurements have been executed.
