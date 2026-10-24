# VP-8122A Python Driver — Independent Deep Review and Remediation Plan

**Review ID:** VP8122A-REVIEW-2026-10-24  
**Review date:** 2026-10-24  
**Target:** [Panasonic VP-8122A driver](https://github.com/ami3go/Panasonic_vp-8122a)  
**Baseline:** `main` at [`0bc943e58a3c501517a41fb1e3f78842eb80aacc`](https://github.com/ami3go/Panasonic_vp-8122a/commit/0bc943e58a3c501517a41fb1e3f78842eb80aacc) (2022-12-02)  
**Documentation/version change:** 0.1.0 — *first explicitly versioned review baseline*, not a functional driver release.  
**Disposition:** **DO NOT QUALIFY FOR UNATTENDED RF TESTING** until P0 gates and physical HIL evidence pass.  
**Scope:** Static inspection of `src/PANASONIC_VP_8122A.py`, `Examples/dev_init.py`, `README.md`, `.gitignore`, `Doc/Desible_IDN_on_USBGPIB.txt`, historical commits/PRs, and available independent instrument/manual references. No live instrument, USB–GPIB adapter, VISA stack, or hardware measurement was accessible. Tests were not executed.

## 1. Executive verdict

The code is a useful historical prototype with a hierarchical command builder covering output, RF frequency, AM/FM, stereo modes, pilot, total FM deviation, composite level, negative-peak clipper and pre-emphasis. It has significant protocol/lifecycle/safety gaps.

The central architectural mistake would be to treat the VP-8122A as an ordinary SCPI instrument. Its **legacy IEEE-488/GPIB device-dependent message syntax**, **talker/listener operation**, and **bus interface commands** require their own protocol adapter. Do not assume `*IDN?`, `SYST:ERR?`, `OUTP` or standard modern SCPI behavior.

### Confidence terminology

- **Confirmed code defect:** Provable directly from the current source, independently of a real device.
- **Strong protocol concern:** Contradicts an IEEE-488 mechanism or public VP-8122A example; requires bench confirmation for the exact adapter/firmware.
- **Verification gap:** Cannot declare correct or incorrect without an exact VP-8122A manual section or read-only hardware trace.

## 2. Findings register

| ID | Priority | Finding, evidence and impact | Required action |
|---|---|---|---|
| **R-01** | **P0** | **Legacy identification mismatch**: `com_interface.init()` unconditionally calls `self.inst.query("*IDN?")` ([source L52–68](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L52-L68)). A VP-8122A practitioner reports probable IEEE-488.2 identification incompatibility. Open may succeed but connect raises a timeout. **Strong protocol concern.** | Do not require `*IDN?`. Open chosen VISA resource, perform non-invasive link validation using a manufacturer-supported talker/status sequence, and report identity as user-configured/unverified where appropriate. |
| **R-02** | **P0** | **Broken initialization example**: `rf_init()` creates `com_interface()` then calls `send()` without `init()` ([example L6–11](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/Examples/dev_init.py#L6-L11)). `self.inst` is `None`; first send raises `AttributeError`. **Confirmed.** | Explicit `connect()`/`close()` lifecycle, context manager; example must connect before any write. |
| **R-03** | **P0** | **Unbound variables in example**: `set_freq_MHz()` refers to `rf` and `cmd` only defined as locals of `rf_init()` ([example L35–40](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/Examples/dev_init.py#L35-L40)). Calling it raises `NameError`. **Confirmed.** | Use an explicit driver instance and method, no ambient globals. |
| **R-04** | **P0** | **IEEE-488 GTL encoded as ASCII instrument data**: `disconnect()` calls `send("GTL")` ([source L100–101](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L100-L101)). GTL is an **addressed IEEE-488 bus interface command**, not a normal device-dependent text command. **Strong protocol concern.** | Implement optional local return using the VISA interface/control API supported by the backend; always close the instrument and resource manager in `finally`. Test GTL separately with the adapter. |
| **R-05** | **P0** | **All exceptions swallowed and ambiguous result**: `query()` bare `except:` retries 10 times, labels all failures timeout, waits five seconds after each failure, then implicitly returns `None` ([source L82–98](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L82-L98)). **Confirmed.** | Retry only documented transient VISA conditions, bound total deadline, raise typed exception with attempt count/cause; never silently return success-like `None`. |
| **R-06** | **P0** | **RF configuration lacks fail-safe transaction**: example changes modulation/frequency/level then enables RF; there is no guarded rollback if a middle step fails ([example L6–33](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/Examples/dev_init.py#L6-L33)). **Confirmed lack of safety mechanism.** | For explicitly authorized energized tests: confirm OFF, validate entire target profile, send mutations while RF OFF, confirm outcome where supported, then enable last. On error, attempt OFF and raise an error preserving safety-state uncertainty. Never auto-re-enable after reconnect. |
| **R-07** | **P0 / qualification blocker** | **Command token spacing is unverified**: `dig_param3.val()` generates `"FR 0.531MZ"` and `"AP 20.0DB"`, `on_off.on()` generates `"CO ON"` ([L117–157](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L117-L157)). A published VP-8122A example uses `FR1MZ,AP-20DM,FM2.5`; repository's own status string uses `FR87.50000MZ AP0.0DB ... COON`. Whether embedded spaces are accepted **has not been established**. | Introduce a reviewed protocol grammar and golden byte strings. No auto-removal of spaces until checked against VP-8122A documentation/hardware. Golden tests must cover every command class. |
| **R-08** | **P0 / qualification blocker** | **Termination and receive framing undefined**: PyVISA's termination, EOI/SEND_END, backend and timeout settings are commented out/defaulted ([L60–68](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L60-L68)); GPIB command delimiter/response policy not characterized. | Capture VISA write bytes, EOI state, CR/LF policy, talker response, timeout behavior with named adapter. Make termination adapter-configurable only among validated modes. |
| **R-09** | **P1** | **Non-idempotent/query semantics unknown**: `inst.query(cmd_str)` assumes a write-then-read transaction, whereas legacy instruments may output setup on being addressed as talker, with mode codes rather than `?` syntax. **Verification gap.** | Separate `write_program_code`, `read_status_as_talker` and `query` (only if proven); never retry a potentially state-mutating write implicitly. |
| **R-10** | **P1** | **Silent numerical clamping**: `range_check()` prints warnings and returns limits ([L30–37](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L30-L37)). A request for 20 dBm becomes 19 dBm instead of failing; no caller-visible proof. **Confirmed.** | Reject invalid values with typed `ValueError`/domain error by default; only expose an explicitly named separate clamp policy for non-safety use. |
| **R-11** | **P1** | **Numeric type and representation uncontrolled**: `val()` accepts booleans, arbitrary float precision, NaN and infinity and stringifies numeric values without instrument-specific resolution ([L125–127](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L125-L127)). **Confirmed.** | Reject bool/non-finite/non-numeric; use `Decimal` or carefully bounded integer units, canonical rounding and exact formatting; validate effective vs requested values. |
| **R-12** | **P1** | **Model-specific frequency quantization missing**: `frequency` allows any real number from 0.01–280 MHz ([L252–258](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L252-L258)). VP-8122A publication describes region-dependent RF resolution. | Verify exact VP-8122A range/step boundaries (including 140 MHz boundary), then reject/quantize explicitly; report `requested_hz` and `effective_hz`. |
| **R-13** | **P1** | **RF level and load conversions are not characterized**: four parameter builders encode dBm, dBµV, mV and µV ([L232–249](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L232-L249)); their min/max, 50/75 Ω applicability and numerical increments are untested. | Build a model/impedance-dependent capability table from manual; test physical readback at representative combinations. Never silently convert between RF units without impedance context. |
| **R-14** | **P1** | **AM/FM/stereo interaction lacks capability constraints**: user may request modulation combinations inconsistent with current stereo mode; no cross-field validation ([L193–212](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L193-L212)). | Validate mode/modulation/pilot/deviation jointly, including instrument-specific incompatibilities; document transition sequence. |
| **R-15** | **P1** | **Resource identity hardcoded to one adapter/serial**: `INSTRUMENT_VISA_ADDRESS` is a specific USB resource string and `list_resources` uses substring matching ([L19, L55–61](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L19-L61)). | Explicit optional resource name, discovery with unambiguous choice, read-only adapter probe, descriptive errors for zero or multiple matches; do not auto-open first instrument. |
| **R-16** | **P1** | **No explicit instrument state machine/thread-safety**: `send()` only writes then sleeps ([L70–73](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L70-L73)); simultaneous callers can interleave commands. | State model (`DISCONNECTED`/`CONNECTED`/`CONFIGURING`/`RF_ON`/`FAULT`), lock per session, disconnect policy, bounded configuration deadline and instrument-dependent settle. |
| **R-17** | **P1** | **No readback/evidence contract**: write methods do not return applied values, device error/status and verified output states. Source status sample is commented, not parsed or tested ([L24](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L24)). | Implement documented talker-mode parser, preserve raw string, typed observed state with parse failure distinct from unsafe hardware state. |
| **R-18** | **P1** | **Packaging/import story incomplete**: example mutates `sys.path` and imports `src.PANASONIC_VP_8122A` ([example L1–3](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/Examples/dev_init.py#L1-L3)); no `pyproject.toml` or dependency pin established in reviewed repository paths. | Convert to installable root package `panasonic_vp8122a/` (no `src/` layout), `pyproject.toml` with optional VISA backend, typed public API and retained deprecation bridge. |
| **R-19** | **P1** | **No demonstrated automated verification baseline**: reviewed source and example contain print/demo code but no assertions; conventional CI/test manifests were not found in inspected paths. This does **not** prove no tests exist elsewhere. | Create deterministic offline golden-vector/fault-injection tests and CI; inspect full repo tree before asserting file absence. |
| **R-20** | **P2** | **Copied oscilloscope material and unused constants**: `USER_REQUESTED_POINTS` (oscilloscope memory), `GLOBAL_TOUT` and HiSLIP/scope comments do not describe VP-8122A behavior ([L10–28](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/src/PANASONIC_VP_8122A.py#L10-L28)). | Remove stale material after documenting traceable original behavior; use actual GPIB timeout policy. |
| **R-21** | **P2** | **Sample units misleading**: example labels `0.531` MHz as “531 Hz” ([example L26–28](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e/Examples/dev_init.py#L26-L28)); this is **531 kHz**, a 1000× difference. **Confirmed.** | Correct comment and use `set_frequency_hz(531_000)`, with typed quantities or explicit units. |
| **R-22** | **P2** | **Maintenance/tooling debt**: PEP8 naming, magic delay, print-only diagnostics, no configurable logging, outdated docs, and adapter-specific `Doc/Desible_IDN_on_USBGPIB.txt` commands about a different device. | Isolate legacy notes, add accurate README/Quickstart/troubleshooting, structured logging with resource metadata redaction and supported Python/VISA matrix. |

## 3. Protocol evidence and unresolved questions

### 3.1 Known facts

1. A public VP-8122A user supplied a program message similar to `FR1MZ,AP-20DM,FM2.5`; the NI discussion explicitly warns that `*IDN?` may not be supported.
2. The VP-8122A operation manual is publicly listed in BAMA. Related Panasonic manuals describe a separation between device-dependent program codes and IEEE-488 interface commands. **Do not transfer another model's command ranges/syntax as fact**.
3. IEEE-488 **GTL** is an addressed command on the bus, not the ASCII characters `GTL` transmitted as a program code.
4. The repository itself contains scanned command pages under `Doc/GPIB/` and a native-looking status example beginning `FR87.50000MZ AP0.0DB ...`.
5. Adapter resource identity is not the instrument identity. A USB–GPIB converter may expose itself as `USB...::INSTR` and discover instruments in an adapter-specific way.

### 3.2 Protocol questions to close *before implementing protocol serializers*

- Does the VP-8122A accept whitespace **within** a program word (`FR 87.5MZ`) or only **between** complete words (`FR87.5MZ AP0DB`)?
- Are multi-command messages separated by comma, space, CR/LF, LF, or EOI? What is the documented maximum message length?
- What does the instrument emit as a talker? Can it be read by a standard VISA read without a preceding instrument write? Is `TM0` needed?
- Does it respond to any device-dependent identification/status command without switching output state?
- Which VISA backend and USB–GPIB adapters supply correct IEEE-488 bus controls (REN, GTL, IFC, SDC, EOI)?
- Which command explicitly enables/disables RF: `COON/COOF`, `APON/APOF` or both with different meaning?
- Which command payload ranges are valid for actual VP-8122A, and which depend on firmware/impedance/mode?
- Does the 250 ms pacing requirement apply per *program word*, per *program message*, or only selected operations? Measure; do not treat source comment as a verified data sheet specification.

**Classification:** Until documented or proven with a physical instrument, command spellings, terminations and accepted parameter precision are **unverified**, not “passed”.

### 3.3 Proposed golden vectors — hypotheses, not hardware-validated output

| Operation | Proposed candidate | Current code generated | Check |
|---|---|---|---|
| RF frequency 0.531 MHz | `FR0.531MZ` | `FR 0.531MZ` | Character-for-character command acceptance |
| RF level 20 dBµV | `AP20.0DB` | `AP 20.0DB` | Units, sign, numeric grammar, impedance |
| AM on | `AMON` | `AM ON` | Set/readback and effect |
| Control output off | `COOF` | `CO OF` | Physical RF output safety |
| 50 Ω | `AP50` | `AP 50` | Must distinguish impedance from RF level |
| Go-to-local | **IEEE-488 interface GTL** | ASCII `GTL` | Native GPIB management action |

Candidate spellings are suggested by the repository's status text and published user example; they must not be merged as proven behavior without bench evidence.

## 4. Target architecture (manufacturer-specific protocol retained)

Root package (no `src/` directory):

```text
panasonic_vp8122a/
    __init__.py
    driver.py                 # high-level safe RF operations
    legacy_protocol.py        # native GP-IB command serializer and parser
    visa_transport.py         # resource/session, EOI, GTL, timeouts
    capability.py             # numeric limits and cross-mode rules
    models.py                 # typed request/observed state
    errors.py                 # Connection, Protocol, Timeout, UnsafeState
tests/
    test_command_goldens.py
    test_validation.py
    test_transport_faults.py
    test_rf_safety.py
    test_legacy_status.py
    test_smoke_mock.py
    hil/                      # explicit hardware-only, never in default CI
Examples/
    safe_offline_demo.py
    authorized_rf_example.py
pyproject.toml
VERSION
README.md
```

Separate three layers: *pure command serialization* (no PyVISA import), *transport* (injected VISA resource), and *RF sequencing*. Reusing `scpi-driver-core` is defensible **only** for generic transport/session/error primitives that require no SCPI `*IDN?`, `*OPC?` or `SYST:ERR?`. Treat protocol inheritance as an explicit compatibility decision, not a default.

### Suggested API contract (illustrative, not implementation)

```python
with VP8122A.connect(resource="GPIB0::2::INSTR", output_policy="off") as rf:
    rf.configure(
        frequency_hz=531_000,
        level_dbuv=20.0,
        output_impedance_ohm=50,
        modulation=AM(depth_percent=30, source="internal_1khz"),
        enable_output=False,
    )
    # No RF energization without a separate explicit authorization action.
    # rf.enable_output(authorization=bench_authorization)
```

Important: even connect-time OFF requires documented/validated command support and explicit configuration of its safety policy; do not silently assume that an OFF command reached the instrument. If communication fails before OFF confirmation, report **UNKNOWN** safety state.

## 5. Mandatory design constraints

1. **Fail closed where possible, report unknown honestly:** On exceptions during an energized test, attempt explicit output OFF but report `OFF_UNCONFIRMED` until verified by supported status or independent measurement. Do not claim safe simply because a command write returned.
2. **Strict validation:** finite, integral where required, bounded and quantized; never replace requested setpoint invisibly. No bool, NaN, infinity or rounding by generic Python representation.
3. **No connect-time RF enable:** connection/discovery/status operations must be read-only unless user explicitly authorizes output changes. Do not auto-restore previous RF state on reconnect.
4. **No blind retries of mutations:** a timeout after a write leaves the state ambiguous. Retry read operations only when semantics prove it is safe.
5. **Deterministic deadlines:** bounded VISA read/write timeouts, whole-sequence deadline and cancellation; no sleep(5) × 10 silent loop.
6. **Single owner of instrument session:** synchronization/lock, serialized protocol interactions, robust `close()` even on failures.
7. **Traceability:** log timestamp, operation, requested/effective quantity, exact sent bytes where non-sensitive, backend, duration, response/raw status, fault class and state transition.
8. **Electrical confidence:** distinguish request accepted, front-panel/status readback, and externally measured RF output; none implies the others without evidence.
9. **Versioning:** increment package version for every merged code/docs change per project policy. First review version is `0.1.0`; next change should increment appropriately.
10. **No silent firmware assumptions:** preserve support for classic Panasonic native program codes, not SCPI replacements.

## 6. Ordered implementation plan — review and PR gates

### PR-A — Protocol characterization and offline fixture baseline (**P0**, prerequisite)

- Read the actual VP-8122A operation manual program-code and GP-IB interface chapters, especially status/talker/EOI/GTL examples, and repository `Doc/GPIB` images.
- Write `docs/VP8122A_PROTOCOL_MATRIX.md` with exact code, accepted range, unit, resolution, sample output and manual page.
- Add pure serializers with *manually reviewed* goldens and 100% coverage of documented command families.
- Record **UNVERIFIED** status for every command lacking an instrument trace.
- **Gate:** No unverified command considered correct merely because unit tests pass.

### PR-B — VISA session, identification and transport hardening (**P0**)

- Replace mandatory `*IDN?`, configure explicit resource selection, instrument-as-talker read flow and backend-validated EOI/CR/LF.
- Explicit connect/close/context manager; resource manager ownership semantics; correct GTL as bus command.
- Define typed failures (`ResourceNotFound`, `AmbiguousResource`, `ProtocolTimeout`, `UnsupportedInterfaceOperation`).
- Fault injection: unavailable VISA backend, missing resource, timeout, short write, disconnect, malformed readback.
- **Gate:** All offline tests pass; read-only connect/disconnect HIL pass with exact adapter and captured transcript.

### PR-C — Strict numeric validation and RF-output safety (**P0**)

- Extract capability table from authoritative VP-8122A manual; validate every command argument and cross-mode combination before I/O.
- Implement finite-range checks, exact resolution with requested/effective values, 50/75 Ω distinction.
- RF OFF / program / verify / separately authorize RF ON transactional sequence; failure path attempts OFF and reports uncertainty.
- Test injection at every sequence step and repeated/canceled/parallel requests.
- **Gate:** No invalid command reaches transport; RF never becomes ON after a failed or canceled request in mock; physical behavior independently checked in HIL.

### PR-D — Functional command completeness and readback (**P1**)

- Cover frequency, RF level, output impedance/state, AM/FM modulation, stereo, pilot, pre-emphasis, total FM deviation, composite output and clipper.
- Characterize status/talker parser and timeouts; preserve raw status for unrecognized revisions.
- Mark unimplemented features unsupported rather than presenting a command generator as tested driver support.
- **Gate:** all supported commands have manual reference, golden output, error test and at least one hardware verification.

### PR-E — Packaging, docs and CI (**P1**)

- Root `panasonic_vp8122a/` package, `pyproject.toml`, optional PyVISA dependency/backend instructions, Python type annotations.
- Keep legacy module as a compatible import shim with a deprecation notice; avoid breaking callers abruptly.
- Replace broken example with safe offline and explicitly authorized HIL examples; correct the 531 kHz comment.
- CI: supported Python matrix, lint/type checks, mock tests, coverage and packaging import checks; hardware tests opt-in only.
- **Gate:** fresh-venv `pip install .`, editable install, import, tests and examples validated.

### PR-F — Authorized physical bench qualification and release (**P0 release gate**)

- Use the actual VP-8122A, approved RF measurement instrument/attenuator and documented GPIB adapter.
- Capture exact commands, response strings, EOI/termination, RF level, impedance, AM/FM and stereo behavior, connect/close, local/remote behavior.
- Prove RF OFF before and after every test; independent output observation preferred.
- Maintain traceable test report, device firmware/config, adapter backend and driver version.
- **Gate:** independent reviewer approves all P0 outcomes and evidence; only then publish an instrument-qualified release.

PR-A, PR-B and PR-C should not be merged independently as production-ready until their shared protocol/safety contract is stable. PR-E documentation/testing scaffolding can begin in parallel.

## 7. Minimum deterministic test matrix

| Test | Input / injection | Required assertion |
|---|---|---|
| T-001 | `com_interface()` then `send("...")` without connect | Explicit not-connected error; no hidden `AttributeError` |
| T-002 | Multiple / absent VISA resources | Explicit selection error; never select arbitrary device |
| T-003 | Read-only connection on legacy GPIB | No unconditional `*IDN?`; no RF-on command |
| T-004 | Frequency / level / mode goldens | Exact bytes equal manual/qualified test vectors |
| T-005 | Negative, over-limit, bool, NaN, Inf, string | No transport write; typed validation error |
| T-006 | Boundary resolution (near 140 MHz etc.) | Explicit quantization/rejection with requested vs effective |
| T-007 | Timeout on status read | Typed bounded timeout, no infinite/bare-except loop |
| T-008 | Timeout after RF mutation | Do not auto-retry ambiguous command |
| T-009 | Exception at each profile programming step | Attempt RF OFF; mark state UNKNOWN if unconfirmed |
| T-010 | Concurrent configure/enable/disconnect | Serialized deterministic result; no unexpected RF ON |
| T-011 | Exit from `with` block under exception | Instrument and owned resource manager closed exactly once |
| T-012 | GTL requested by caller | Uses backend bus API, not ASCII text |
| T-013 | Malformed/unknown talker status | Retain raw bytes and raise parser error, not fabricated state |
| T-014 | Repeat run with same profile | Same wire bytes and effective setpoints |
| T-015 | Fresh env install & legacy import | No dynamic `sys.path` hack; documented compatibility |
| T-016 | HIL output OFF / RF level / modulation | Independent bench measurement plus timestamped transcript |

**Environment note:** The above is a proposed test plan, not a claim that tests were executed or hardware qualified.

## 8. Release and evidence criteria

### Release blockers

- [ ] R-01…R-08 resolved or explicitly documented as failed HIL gates.
- [ ] Manufacturer VP-8122A protocol matrix reviewed against authentic manual.
- [ ] Each supported command has golden vectors and bench evidence.
- [ ] Read-only and energized test paths separated by explicit authorization.
- [ ] Resource cleanup and output-safe failure cases verified.
- [ ] Automated regression and coverage baseline recorded.
- [ ] Fresh install and examples pass.
- [ ] Independent code/safety review performed after remediations.
- [ ] Version increment and changelog recorded with merged PR(s).

### Evidence bundle schema

```json
{
  "review_id": "VP8122A-REVIEW-2026-10-24",
  "baseline_sha": "0bc943e58a3c501517a41fb1e3f78842eb80aacc",
  "driver_version": "0.1.0-review-baseline",
  "model": "VP-8122A",
  "visa_backend": "NOT_TESTED",
  "adapter": "NOT_TESTED",
  "manual_reference": "UNVERIFIED_FOR_ALL_COMMANDS",
  "offline_tests": "NOT_RUN",
  "hardware_tests": "NOT_RUN",
  "rf_safety": "NOT_QUALIFIED",
  "release_gate": "BLOCKED"
}
```

## 9. Independent references and caveats

**Repository evidence**
- [Current driver source at review SHA](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e58a3c501517a41fb1e3f78842eb80aacc/src/PANASONIC_VP_8122A.py)
- [Current example at review SHA](https://github.com/ami3go/Panasonic_vp-8122a/blob/0bc943e58a3c501517a41fb1e3f78842eb80aacc/Examples/dev_init.py)
- [Legacy adapter notes](https://github.com/ami3go/Panasonic_vp-8122a/blob/main/Doc/Desible_IDN_on_USBGPIB.txt) — contains another instrument's USB resource and adapter-specific commands, not an approved VP-8122A procedure.
- [Command excerpt images](https://github.com/ami3go/Panasonic_vp-8122a/tree/main/Doc/GPIB).
- [Historical PR #1](https://github.com/ami3go/Panasonic_vp-8122a/pull/1), [PR #2](https://github.com/ami3go/Panasonic_vp-8122a/pull/2).

**External references**
- [BAMA VP-8122A Operation Manual collection](https://bama.edebris.com/manuals/panasonic/vp8122) — exact-model authoritative material listed but PDF content not exhaustively validated in this review.
- [NI Community VP-8122A LabVIEW/GPIB discussion](https://forums.ni.com/t5/LabVIEW/LabVIEW-driver-for-Panasonic-singal-generator-VP8122A/td-p/227759) — first-hand sample command and warning concerning unsupported `*IDN?`; anecdotal, not a replacement for manufacturer's manual.
- [Panasonic VP-8120A related model operation manual](https://manuals.repeater-builder.com/te-files/MISCELLANEOUS/PANASONIC%20VP-8120A%20Specification%20%26%20Operating.pdf) — contains VP-8122A-relevant sections; treat model-specific details with care.
- [Panasonic VP-8174A GP-IB program format](https://www.opweb.de/pdf/panasonic--vp-8174a--user--ID14369.pdf) — related model only, NOT evidence for VP-8122A acceptance of spacing/termination.
- [Panasonic VP-8193A GP-IB interface description](https://www.lost-manuals.com/pdf/panasonic--vp-8193a--user--ID16114.pdf) — related model only; general IEEE-488 interface behavior.

### What this review did *not* verify

No claim is made about actual hardware command acceptance, number of hidden/repository test files in the full Git tree, RF electrical performance, exact RF specifications on an unknown firmware revision, or whether `scpi-driver-core` has a transport-only API suitable for reuse. Close these with file-tree inspection, exact-manual proof and explicitly authorized bench testing.

**Bottom line:** Do not start with sweeping refactoring or speculative syntax replacement. First freeze protocol bytes, determine proper talker/termination/GTL semantics, and implement fail-safe transport and output transactions. Then modernize the public API, packaging and tests.
