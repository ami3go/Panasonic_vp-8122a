# VP-8122A — Automated Native GPIB HIL Protocol Verification

**Introduced in development v0.2.6. Hardware status: NOT EXECUTED / NOT RF QUALIFIED.**

## Protocol boundary

The Panasonic VP-8122A speaks **native Panasonic GPIB**, **not SCPI**. The shared transport library's name does not authorize any SCPI identity, error, reset or output command on this instrument. The v0.2.6 HIL suite sends only TM0, TM1 or TM2 native talker-selection program words and receives bounded replies. It does not enable RF, configure a profile, verify OFF electrically, or change presets.

## Offline verification

    python -m pip install -e '.[test]'
    python -m pytest -q -m 'not hardware'
    python -m pytest -q tests/test_hil_guards.py

Offline tests enforce authorization, reject CI runs, verify resource/address parsing, native command allowlisting, and negative SCPI and RF mutation tests.

## Physical bench prerequisites

- Actual VP-8122A with a reviewed, isolated RF load/attenuator, independent RF monitoring and physical emergency power disconnect; instrument output may already be ON at test start.
- Qualified GPIB adapter/backend, known resource, manual/controller termination requirements, operator authorization, actual front-panel serial, controller model and run ID.
- Run exclusively on a manually controlled local bench; CI runs are refused even with explicit markers.
- Use a pre-existing local evidence directory and keep its contents for independent review.
- EOI-only, LF and CRLF are three **alternatives**; select only the one documented for the actual controller. Do not automatically sweep delimiters.

## Example authorized local run

Replace every sample field with the independently checked bench value:

    mkdir -p ./hil-evidence
    export VP8122A_HIL_AUTHORIZED=ISOLATED_RF_BENCH_APPROVED
    export VP8122A_HIL_RESOURCE='GPIB0::2::INSTR'
    export VP8122A_HIL_EVIDENCE_DIR="$PWD/hil-evidence"
    export VP8122A_HIL_RUN_ID='bench-run-001'
    export VP8122A_HIL_SERIAL='ENTER-ACTUAL-FRONT-PANEL-SERIAL'
    export VP8122A_HIL_CONTROLLER='ENTER-ACTUAL-GPIB-CONTROLLER'
    export VP8122A_HIL_OPERATOR='ENTER-AUTHORIZED-OPERATOR'
    export VP8122A_HIL_TERMINATION='LF'
    export VP8122A_HIL_MODES='0'
    export VP8122A_HIL_TIMEOUT_MS='2000'
    python -m pytest -q -m hardware tests/test_hil_authorized.py

Default mode is TM0 only. Only set VP8122A_HIL_MODES='0,1,2' after expressly authorizing the other two talker modes. Permitted termination names are EOI, LF, CRLF. Never set VP8122A_HIL_ALLOW_RF_ENABLE; it is rejected.

## Fail-closed behavior

- Instrument I/O is unreachable until an explicit GPIB primary-address resource, authorization value, metadata, run ID and existing evidence directory pass validation.
- A subclass of core VisaTransport blocks all write payloads except the exact authorized TM0/TM1/TM2 with selected delimiter. Attempts to transmit APOF, APON, GTL-as-text, FR, *IDN?, *RST, SYST:ERR?, OUTP or a multi-command string fail **before** VISA.
- The actual test runs the public Panasonic driver status API. The core transport resource is then closed directly. The driver close() method is intentionally **not** called because it would issue the unqualified APOF RF mutation and violate readback-only testing.
- Finite VISA read/write deadlines and pytest-timeout watchdog guard execution. Any malformed or missing reply faults the attempt rather than silently claiming success.
- Always close resource regardless of test outcome; best-effort, uniquely named JSON evidence is written including failed attempts.

## Evidence and limits

Each mode yields an append-only, uniquely named JSON file with UTC timestamp, operator-supplied identities, driver version, requested host TX bytes in hex, raw reply bytes in hex, mode, parsed ordered TM0 fields and outcome OBSERVED or INCONCLUSIVE.

**Requested host bytes are not confirmed bus trace bytes.** The evidence explicitly reports eoi_verified_by_bus_analyzer=false, rf_output_measured=false and rf_off_confirmed=false. Observed talker output does not qualify electrical OFF, RF generation, GPIB EOI or physical safety.

## Command coverage at this stage

| Family | v0.2.6 physical suite | Requirement for full qualification |
|---|---|---|
| TM | Prepared TM0/TM1/TM2 native readback-only tests | Authorized bench run, actual instrument trace and LF/EOI verification |
| FR, AP, AM, FM, MS | Not tested | Safe RF load, separately authorized configuration, independent calibrated RF measurement |
| PL, FT, PR, LV, NP | Not tested | Appropriate modulation/composite measurement, documented source variants |
| LE, EM, CO, SC | Not tested | Resolve missing/partial implementation and verify accepted variants |
| RC, ST, DR, AS, NT, P1, P2 | Blocked | Dedicated nonvolatile/external-I/O risk approval and exact manual input grammar |
| Addressed GTL/REN | Not tested on hardware | Controller bus trace, multi-instrument isolation |

The [full native reference](../Doc/GPIB/COMMAND_REFERENCE.md) documents 22 families but does not establish that any are hardware qualified. The [full automated qualification task](../task/VP8122A_AUTOMATED_NATIVE_GPIB_HIL_TASK.md) specifies the future externally measured active RF phases.

**Never mark HIL PASS from software simulation, a successful VISA write, or front-panel status alone.**


## v0.2.8 automated readback execution and reports (NOT RF qualified)

The source-controlled matrix at tests/hil/command_matrix.json catalogs 45 variants in 22 command families. The only physically selectable cases are TM0/TM1/TM2. Documented RF command examples are serialization fixtures, not dispatch instructions. Status-only fields have no TX vector and IEEE-488 bus operations are separate.

After completing all v0.2.6 isolated-bench authorization steps above, run:

    python -m tests.hil_runner --report-dir "$VP8122A_HIL_EVIDENCE_DIR"

The runner validates the local authorization, starts the talker-only pytest suite under a finite outer subprocess deadline, and emits distinct JSON/CSV/Markdown/JUnit XML reports for the configured run ID, even when pytest fails. It never sends RF ON, candidate RF OFF, SCPI, preset or external-port writes.

To rebuild reports without VISA or hardware, first create an output directory, then run:

    python -m tests.hil_reporting --evidence-dir ./hil-evidence --output-dir ./hil-reports --run-id YOUR_RUN_ID

Previously recorded talker observations are filtered by exact run ID. An OBSERVED reply does not establish bus EOI, physical output status or measured RF and remains INCONCLUSIVE for physical qualification. No active RF measurement adapter is approved or enabled in this release.
