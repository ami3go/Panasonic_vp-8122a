# Implementation Task — Automated Native GPIB Command HIL Verification for Panasonic VP-8122A

**Task ID:** VP8122A-AUTO-HIL-NATIVE-01  
**Priority:** CRITICAL — Native command conformance, hardware state, RF safety, GPIB transport qualification  
**Repository:** https://github.com/ami3go/Panasonic_vp-8122a  
**Shared core:** https://github.com/ami3go/scpi-driver-core  
**Source reference:** [Doc/GPIB/COMMAND_REFERENCE.md](../Doc/GPIB/COMMAND_REFERENCE.md)  
**Existing HIL checklist:** [docs/HIL_QUALIFICATION.md](../docs/HIL_QUALIFICATION.md)  
**Initial readback-only suite:** [tests/test_hil_authorized.py](../tests/test_hil_authorized.py) and [tests/hil_support.py](../tests/hil_support.py)  
**Target version:** increment from the latest actual version on every changed repository; v0.2.6 introduces the guarded readback-only baseline.  
**Qualification status:** No actual VP-8122A HIL measurements have been recorded. Do not imply otherwise.

## Mission

Implement a comprehensive, fully automated and independently auditable HIL qualification system that checks the Panasonic VP-8122A's **native Panasonic GPIB** listener and talker commands against the scanned manufacturer excerpts and the current driver. Perform actual code, tests, source tracing, bench adapter development, CI, review, GitHub PR and eligible software-only merge operations. Do not stop at analysis.

**The Panasonic VP-8122A is NOT a standard SCPI instrument.** The package name *scpi-driver-core* does not change its protocol. It may supply only byte-level VISA transport, deadlines, locking and tracing. **Never transmit** generic commands such as \`*IDN?\`, \`*RST\`, \`*CLS\`, \`*OPC?\`, \`SYST:ERR?\` or \`OUTP\` to the Panasonic. The *reference measurement instrument* may use SCPI if separately documented for that model.

## Hard safety rules

1. A generic automated test must **never enable RF**. Use explicit, separate, fail-closed physical-bench authorization for every state-mutating phase. Do not infer authorization from an environment variable alone; require an approved bench manifest, an externally measured RF-off baseline, actual physical load/attenuation and emergency stop, and separate active-test permission.
2. The initial HIL path is **readback-only**: native TM0/TM1/TM2 selection plus bounded talker read. It must not call \`VP8122A.close()\` because this currently attempts an unqualified \`APOF\`. Close only the core transport for readback-only exploration.
3. **No unsupported ASCII or bus commands.** GTL/REN/SDC/DCL are bus-level functions, never text commands; inspect the addressed GTL behavior on a multi-instrument bus. Do not call trigger/SRQ/serial-poll helpers that the VP-8122A manual does not support.
4. Never automatically send \`APON\`, restore RF ON on reconnect, retry a state-changing command or replay a profile after a timeout.
5. Never interpret a successful VISA write or TM0 status value as proof of RF physical OFF. Separate *requested*, *instrument-reported* and *externally measured* values.
6. Do not blindly batch commands, vary delimiters, change presets, access external digital ports or sweep operating ranges. Each command must be documented, validated and authorized under the selected test phase before sending.
7. Every bounded I/O operation requires a deadline and hardware tests require watchdogs. On faults record \`UNKNOWN\`/\`INCONCLUSIVE\`, preserve the evidence and release resources; never conceal test failures with retries.
8. Physical HIL tests must not run in GitHub Actions or normal CI, even when deliberately selecting test markers on a CI agent. No real instrument execution until hardware bench and external meter are available.

## Stage A — Verify latest baseline

- Refresh latest main, active PRs, driver/core versions, public interfaces, safety state machine, packaging and existing tests.
- Inspect \`NativeCommands\`, \`encode_program_word\`, \`parse_status\`, \`VP8122A.read_status\`, \`ScpiClient.write_bytes/read_bytes\`, \`VisaTransport\`, EOI and addressed GTL.
- Verify all available \`Doc/GPIB/\` manufacturer excerpts; \`FM2.png\` previously lacked usable API image content. Do not treat unsupported or status-only command strings as proven listener commands.
- Run baseline offline pytest and record head commit, Python/pytest versions, counts and coverage.
- Map existing 22 native header families with **individual variants** and specific manual page references.

## Stage B — Build a machine-readable verification matrix

Create \`tests/hil/command_matrix.json\` or \`yaml\` (validated with strict schema). Every row must contain:

- Family, variant, source excerpt/page, exact native program word or read mode, known numeric ranges/resolution, serializer/API method, expected host TX bytes for EOI/LF/CRLF.
- Physical side-effect risk: \`TALKER_SELECT\`, \`RF_CONFIG\`, \`RF_ENABLE\`, \`NONVOLATILE\`, \`EXTERNAL_IO\`, \`BUS_CONTROL\`, or \`UNVERIFIED_INPUT\`.
- Required authorization, known preconditions, readback verification method and available independent reference measurement.
- Unit/property test IDs, HIL case IDs, evidence files and qualification status.
- Exact statuses \`PASS\`, \`FAIL\`, \`INCONCLUSIVE\`, \`NOT_TESTED\`, \`UNSUPPORTED\`. Lack of external measurements may not produce \`PASS\` for physical behavior.

Prioritize the 22 native families from \`COMMAND_REFERENCE.md\`:

| Family | Planned safe verification | Default physical permission |
|---|---|---|
| \`TM\` | Select TM0/TM1/TM2, check raw ASCII and LF+EOI framing; preserve ordered duplicate headers | Readback-only with bench authorization |
| \`FR\` | Boundary stepping and counter/spectrum measurement | Active RF bench only |
| \`AP\`, \`LE\`, \`EM\` | Level units, impedance, output state with calibrated power reference | Active RF bench only |
| \`AM\`, \`FM\` | Depth/deviation, source selection, documented limits and measured modulation | Active RF bench only |
| \`MS\`, \`PL\`, \`FT\`, \`PR\` | Stereo/pilot/total-deviation/pre-emphasis | Mode-specific calibrated modulation measurement |
| \`CO\`, \`SC\`, \`LV\`, \`NP\` | Continuous attenuation, SCA, composite level, clipper | Individually approved circuit/measurement |
| \`RC\`, \`ST\` | Recall/store may alter output or nonvolatile memory | **NEVER in default HIL** |
| \`DR\`, \`AS\`, \`NT\` | Present in status map; input syntax may be unverified | **NEVER until manual/HIL source verified** |
| \`P1\`, \`P2\` | External port values may actuate equipment | **NEVER in default HIL** |

Preserve a separate bus-operation matrix: addressed GTL, REN, device clear. Do not count these as native ASCII families.

## Stage C — Deterministic offline enforcement

- Golden vectors for **every supported command variant**, including boundary/resolution values and correct 255-byte 7-bit ASCII program message with terminator.
- Reject control bytes, Unicode, unknown prefixes, malicious raw input, embedded commas/spaces/newlines, unsupported SCPI syntax and attempts to treat bus GTL as ASCII.
- Hypothesis property tests for legal/illegal numeric domains, native response tokens, ordered duplicate field retention, timeout/recovery and malformed framing.
- Mock/Scripted tests through the public driver and shared core; assert *zero SCPI sends* from constructor, connection, status, recovery, disconnect and error paths.
- PyVISA-sim integration for the byte-level path; never claim it proves hardware EOI or RF OFF.
- Windows/Linux Python 3.10–3.13 offline CI, coverage, build, packaging, traceback evidence; \`pytest-timeout\` protects deadlock-prone tests.

## Stage D — Physical readback-only HIL (implemented baseline)

Retain and harden \`tests/hil_support.py\`, \`tests/test_hil_authorized.py\` and their offline guard tests.

- Require explicit \`VP8122A_HIL_AUTHORIZED=ISOLATED_RF_BENCH_APPROVED\`, validated GPIB VISA resource, chosen delimiter, explicitly recorded operator, instrument serial, controller type, run ID and writable evidence directory.
- Reject execution on CI and reject any \`APOF\`, \`APON\`, \`FR\`, \`AP\`, SCPI or unsupported text at the transport boundary.
- For each explicitly selected mode \`TM0\`, \`TM1\`, \`TM2\`, issue exactly one native command using the real \`VP8122A.read_status(mode=...)\`, read within a bounded deadline, verify no unrequested bytes, preserve full raw response and repeated TM0 fields.
- Record requested host TX hex, raw reply hex, actual mode, parser fields, errors and timestamps. Mark \`eoi_verified_by_bus_analyzer=false\` until separately proven with an analyzer.
- Release the VISA resource **without performing \`VP8122A.close()\`** in this read-only phase. No physical RF state inference.
- Print actionable pytest failures and write append-only/uniquely named JSON evidence even for failures.

## Stage E — Independently measured RF-off qualification gate (NEW)

Before automating any output-programming sequence, integrate a separately documented calibrated RF reference:

- An appropriate RF power meter / spectrum analyzer and, where necessary, frequency counter or modulation analyzer, through explicitly selected VISA resources and **model-specific verified commands**. An HP 34401A DMM alone cannot validate RF power/frequency unless paired with a calibrated RF detector and documented conversion.
- Load/attenuator ratings, measurement port coupling, cable loss, uncertainty budget, external interlock and emergency stop must be reviewed and recorded.
- Measure physical pre-command RF state; do not assume OFF at connection. Verify the \`APOF\` candidate with an externally measured residual-RF limit approved before the run. Validate \`APON\` only in a separately authorized controlled RF phase.
- Check meter identity/health without contacting the Panasonic with SCPI. Abort on reference meter disconnect/stale data/out-of-calibration or if RF remains above approved limit.
- A hard software timeout cannot guarantee a blocked physical VISA backend can be force-stopped: the bench interlock must be independently operable.
- Record baseline and before/after measurements with timestamps, RF uncertainty and FAIL/INCONCLUSIVE reasons; do not mark \`OFF_CONFIRMED\` from command acknowledgment alone.

## Stage F — Controlled command-by-command HIL (NEW, privileged)

Once Stage E passes:

1. Load a signed/approved run plan defining *exactly which* command families/variants and limits are permitted. Reject all other writes.
2. Validate all requested values and command order before any state-changing I/O. Apply approved conservative setpoints, required settling and known output state. Never generate hazardous output beyond plan limits.
3. Execute **one command at a time** using native bytes and capture attempted TX, bus trace if analyzer available, instrument TM readback, external measurements, VISA errors, retries (must be zero for mutations), setpoint deltas and duration.
4. For FR/AP/AM/FM/FT boundaries, include nominal/min/max/step tests and forbidden-boundary negative tests. Run only documented compatible combinations.
5. Nonvolatile \`ST\`, state-changing \`RC\`, external-port \`P1/P2\`, auto-sequence \`AS/NT\`, and source-unverified inputs must remain blocked until dedicated test design, actuator isolation and explicit per-family authorization are approved.
6. After each permitted phase, **measure** RF off using qualified shutoff procedure. At any fault: stop transmitting subsequent commands, assert separate hardware interlock if available, record UNKNOWN and release resources. Never re-enable RF automatically.
7. Reject stale, truncated or ambiguous TM0 response fields. Compare ordered positional field names and repeated headers against the full manual status layout; do not use a prefix-only dictionary for proof.

## Stage G — Reliability, multiple sessions and faults

- Simulate failures at every stage: before/after host write, timeout mid-write, stale read, EOI missing, invalid status, controller power loss, reference meter loss, lock contention and cancellation.
- Maintain finite operation/profile/session timeouts with watchdog failure rather than hanging a runner.
- Verify independently owned VISA resources, borrowed resource-manager behavior, addressed GTL versus REN effect, and absence of automatic output-state restoration or command replay on recovery.
- Separate offline fault injection from physical fault-injection tests; dangerous bus disconnections need specific bench permission.

## Stage H — Evidence and command coverage

Generate machine-readable **JSON** plus **CSV**, **Markdown**, and **JUnit XML** for each run, including:
- Instrument and controller identity, driver/core versions and Git SHAs, time/host/backend, reference instrument/calibration and manual edition.
- Exact requested host TX bytes (not misreported as measured bus wire bytes), raw RX, parsed positional fields, optional captured EOI, external reference measurements with uncertainty, thresholds and deviation.
- Each case's preconditions, test/command IDs, side-effect risk, state before/after, timeout and failure reason.
- Per-family and per-variant qualification matrix separating builder/transport/TM readback/independent measurement/HIL.
- \`PASS\` requires objective approved acceptance evidence. Missing verification is \`NOT_TESTED\` or \`INCONCLUSIVE\`; missing device support is \`UNSUPPORTED\`.

Update the README native-command coverage table from source-controlled matrix without elevating 22-family software coverage to HIL qualification.

## Stage I — GitHub process and release

1. Implement in sequential, reviewable branches and PRs; version-bump and changelog each changed repository.
2. Run offline CI first. Do not use GitHub Actions runners for physical HIL.
3. Independently review protocol, transport, safety, test fixtures, evidence and installer changes. Fix every software P0/P1 finding before merge.
4. Merge only software-ready PRs with passing CI and documented limitations. Do not mark the release HIL-qualified until a real bench produces signed accepted measurements.
5. Present final status by stage, native command family, test result, coverage, commit, version, PR URL and merge status.

## Definition of done

**Software-only suite:** fail-closed read-only HIL, exact native TX allowlist, no SCPI sent to Panasonic, bounded talker reads, evidence files, offline guard/simulation tests and multi-version CI pass.

**Full HIL qualification:** all approved native commands have manufacturer-sourced expected bytes and actual physical behavior evidence; EOI/REN/GTL, RF output OFF, frequency/level/modulation, timeouts and interlocks verified on the real VP-8122A; status/coverage report signed. Unsupported or unverified features remain explicitly unqualified.

**Runbook:** [docs/HIL_AUTOMATION.md](../docs/HIL_AUTOMATION.md). Do not use instrument HIL commands without fulfilling its safety prerequisites.
