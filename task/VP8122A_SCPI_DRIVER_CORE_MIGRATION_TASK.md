# Implementation Prompt — VP-8122A Migration to scpi-driver-core

**Task ID:** VP8122A-SCPI-CORE-MIGRATION-01  
**Priority:** HIGH — transport correctness, lifecycle, protocol integrity, RF safety  
**Task document version:** 1.0, 2026-10-24  
**Target repository:** https://github.com/ami3go/Panasonic_vp-8122a  
**Shared dependency:** https://github.com/ami3go/scpi-driver-core  
**Existing driver development PR:** https://github.com/ami3go/Panasonic_vp-8122a/pull/4  
**Hardware qualification tracker:** https://github.com/ami3go/Panasonic_vp-8122a/issues/5  
**Starting driver reference:** v0.2.2 candidate on `feat/v0.2.0-gpib-driver-hardening`, commit must be freshly fetched  
**Core reference:** `main`, observed at `9c5dd50a03031f65e1aa5cf13832db7372f043b9`, package metadata `0.1.0.dev11`; refresh before starting  
**Implementation branch after prerequisites:** `feat/vp8122a-scpi-core-transport-migration` (adapt if existing)

## Mission

Act as a senior Python software architect, IEEE-488/GPIB protocol engineer, instrument automation engineer, functional-safety reviewer, test engineer and GitHub maintainer.

Perform **actual implementation, tests, independent review, correction, PR creation, CI verification, and merge of eligible changes**. Do not stop at a proposed plan. Execute tasks **one at a time** in the ordering and dependency gates below, prioritizing correctness, hardware safety and backward compatibility over speed.

**Critical distinction:** The Panasonic VP-8122A speaks **Panasonic native GP-IB 7-bit ASCII program codes**, NOT modern SCPI. The shared `scpi-driver-core` may supply its **byte transport, timeouts, locking, session lifecycle, error translation, tracing and simulation**. Its IEEE-488.2 *common-command* layer, SCPI identity helpers, SCPI error queues and standard command parser must **not** be applied to this instrument without documentary proof.

### Non-negotiable rules

1. NEVER send `*IDN?`, `*RST`, `*CLS`, `*OPC?`, `SYST:ERR?`, generic `OUTP`, or another SCPI probe merely because core exposes a helper. Neither a successful connection nor a health check may write unsupported SCPI.
2. Preserve native code families and byte-for-byte command formatting; no conversion to SCPI syntax, and no silent fix of unresolved manual/firmware differences.
3. Preserve explicit RF-enable authorization, strict preflight validation, OFF-first configuration, output-UNKNOWN handling, no blind retry of mutating commands, and no auto-restore of RF ON following reconnect.
4. **No accidental energization:** default offline/mock and connection/discovery/status-only paths must not enable RF. Physical HIL execution only with separately authorized bench setup; otherwise prepare the HIL suite without running it.
5. Reuse **existing core public APIs**; do not build a second generic transport, retry, lock or session framework.
6. Keep the **driver package at repository root** (`panasonic_vp8122a/`), not in a `src/` layout. Core's existing `src/scpi_driver_core/` layout is out of scope.
7. Every change requires a version increment in the affected repository, changelog, tests, independently reviewed PR and recorded outcome. Do not change the core for Panasonic-only behavior.
8. Preserve old imports (`src.PANASONIC_VP_8122A`), Python 3.10–3.13 compatibility and existing documented safety behavior, except explicitly approved breaking changes.
9. Long-running or blocking test stages must use watchdog/timeouts. Never let a test, GitHub job poll, VISA operation, mutex wait or physical HIL script hang without a bound. Use `pytest-timeout` (finite per-test/session limits) and platform/job timeouts; report expiry as failure.
10. Independently review each stage, fix P0/P1 regressions, run the relevant tests, and merge **only** when the documented gate passes. A green offline suite is not evidence of RF output safety.

## 0. Baseline and source verification — mandatory first stage

Fetch fresh `main` and all open PR branches of **both repositories**. Inspect the *effective* code, not memory of a previous snapshot:

- Driver `README.md`, `VERSION`, `pyproject.toml`, `CHANGELOG.md`, `panasonic_vp8122a/{driver,protocol,__init__}.py`, `src/PANASONIC_VP_8122A.py`, tests, examples and CI.
- `Doc/GPIB/COMMAND_REFERENCE.md` and original source scans under `Doc/GPIB/`, plus `docs/HIL_QUALIFICATION.md`, `docs/REMEDIATION_STATUS.md`, previous deep review and issue #5.
- Core `src/scpi_driver_core/transport/{base,models,visa}.py`, `src/scpi_driver_core/scpi/client.py`, `src/scpi_driver_core/scpi/codec.py`, `src/scpi_driver_core/session/session.py`, `AGENTS.md`, `docs/testing.md`, `docs/acceptance.md` and tests.
- Record current commit SHAs, precise installed/importable package versions, code/test baselines and dependency graph.
- Core package metadata was at `0.1.0.dev11` while root `README.md` and module `__version__` were outdated at last inspection. Resolve based on the actual code and package metadata, not stale prose. Do not pin to a stale dev release without testing the installed wheel.

Confirm the base feature PR #4 and v0.2.2 changes are either already merged into `main` or use a clean **dependent branch/PR** against its latest head. Avoid accidentally duplicating its diffs or overwriting concurrent changes. If baseline is unstable, fix verified regressions first.

Record a baseline **comparison matrix** for exported methods, exact command bytes, output-state transitions, exceptions and resource ownership. Re-run the current 34-test offline regression baseline (or its updated equivalent) before implementation; record observed actual results rather than assuming the previous count.

**Gate G0:** clean reproducible baseline; all important changes and incomplete HIL evidence identified.

## 1. Verify architecture fit (design before coding)

Use this separation:

~~~text
VP8122A / RFProfile / legacy compatibility        ← Panasonic semantics and electrical safety
    NativeCommands / native talker-status parser   ← Panasonic-only 7-bit GP-IB grammar
    bounded native execution adapter               ← explicit delimiter, EOI, pacing and read profile
    ScpiClient.write_bytes()/read_bytes()           ← generic operation locking, IDs, timing
    optional ScpiSession.open(probe=False)          ← generic lifecycle; NEVER default probe
    VisaTransport                                   ← shared bounded byte-level VISA resource
    PyVISA / GP-IB controller                       ← selected hardware backend
~~~

### Existing public core APIs verified at planning time

- `VisaTransport(resource_name, timeout_s=..., resource_manager=...)`, `open()`, `close()`, `write(bytes)`, `read(ReadRequest(...))`, `operation_lock()`, `go_to_local()`.
- `ScpiClient(transport, minimum_interval_s=..., timeout_s=...)` exposes `write_bytes()`, `read_bytes()`, `operation_lock()`, `transport` and `is_open`.
- `ReadRequest(mode=ReadMode.BACKEND_DEFINED_MESSAGE, maximum_size=...)` supports bounded VISA-message reading. `ReadMode.UNTIL_TERMINATOR` is an alternative only where that framing is actually appropriate.
- `ScpiSession(alias, client)` with `open(probe=False)` avoids its automatic connect-time probe. **DANGER:** `ScpiSession` defaults `health_query="*IDN?"`; `check_communication()`, `get_identity()` and `Ieee4882` can send unsupported SCPI. Do not call these on this driver. Verify every recovery/health path and its side effects.
- `VisaTransport.go_to_local()` currently uses `control_ren(RENLineOperation.deassert_gtl)`; this might differ from old driver `address_gtl` and can change REN/local behavior for other instruments sharing a bus. Bench qualification and a scoped policy are mandatory.

**Recommended:** Start with raw byte methods on `ScpiClient` and `VisaTransport`, with a small driver-owned native executor. Use `ScpiSession` only if its probe/identity/reconnect semantics can be configured safely; otherwise keep a small driver-local lifecycle wrapper, document why, and use transport/client mechanisms without duplicating core internals.

Do not subclass a SCPI command grammar or use `ScpiClient.query()` as a stand-in for native talker-mode reads. The driver generates messages and controls the read initiation policy.

Document proposed API call map and justify any additional abstraction with demonstrated reuse. Keep every physical setpoint, safety interlock, timeout/settling policy and readback interpretation in the Panasonic driver.

**Gate G1:** reviewed architecture that makes all unintended SCPI traffic impossible by construction.

## 2. Wire-level native-protocol conformance (pure offline)

Preserve `Doc/GPIB/COMMAND_REFERENCE.md` as command-coverage authority, and transcribe exact manual requirements into deterministic fixtures.

Manufacturer source excerpts state:

- 7-bit ASCII program messages; **255-byte maximum per message**.
- End-of-message delimiters **CRLF**, **LF** or **GP-IB EOI**.
- Multiple native codes may be concatenated, or separated by comma/space **between complete program codes**.
- Canonical manufacturer example: `FR1MZ,AP-20DM,FM2.5` with permitted terminator; no added space within `FR1MZ`.
- `TM0`, `TM1`, `TM2` select talker mode (setup state, total FM deviation or external-control port 2 data). Responses are 7-bit ASCII with LF + EOI.
- `TM0` status reports repeated headers (`AP`, `AM`, `FM`, `CO`, `PL`, etc.) in a positional sequence; a simple two-character-keyed dict **loses data**.

Actions:
1. Keep `NativeCommands` independent from `ScpiClient` and all VISA imports.
2. Implement/review an explicit native message encoder with delimiter policy `EOI | LF | CRLF`. If using core `write_bytes()`, append exactly the selected text delimiter; for EOI, verify backend END behavior rather than adding a fake ASCII token.
3. Enforce exact 7-bit ASCII and max payload length **including the actual appended terminator**. Reject non-ASCII, embedded CR/LF where not part of approved message termination, command injection and unsafe arbitrary raw messages.
4. Keep one command per transaction as initial safe mode. Allow command batching only when a manual-approved or HIL-qualified policy proves it safe, fits 255 bytes and preserves fault attribution.
5. Use manufacturer golden vectors for frequency, AP/LE amplitude and output enable, EM, CO, AM, FM, MS, pilot, FT, PR, SC, LV, NP, RC/ST memory, TM and status fields. Keep unsupported variants explicitly missing, not silently claimed implemented.
6. Parse native talker output into a **typed/ordered record**. Preserve repeated headers, raw response and unknown fields. Verify TM0 field count and order; do not confuse LF/EOI with data.
7. Preserve source-visible numeric ranges and address known v0.2.2 mismatches with independent tests: AM manual 0–125% versus driver 0–100%; FM maximum 300 kHz versus driver 999 kHz; FT three distinct precision bands; model-dependent RF frequency steps. Treat discrepancies as separate behavior changes with manual citations, not unreviewed migration side effects.

**Gate G2:** byte-exact deterministic golden tests, malformed-message tests, status round-trips and boundary property tests. No VISA or RF output needed.

## 3. Migrate transport, lifecycle and session semantics

Refactor `panasonic_vp8122a/driver.py` to delegate actual I/O to **core** `VisaTransport` and `ScpiClient.write_bytes/read_bytes`.

- Constructor takes explicit VISA resource (no arbitrary scan/open), optional injected core `Transport` or test-double, explicit timeout, selected native delimiter/EOI and bounded pacing. Preserve old user-facing defaults unless incompatible with safety; document changes.
- `connect()`/`__enter__` uses `transport.open()` and **does not query `*IDN?` or send RF output changes**. No implicit identity validation or default SCPI health probes.
- `read_status()` requires correct TM selection and read sequencing, with a bounded `BACKEND_DEFINED_MESSAGE` request for GP-IB END-capable sessions; decode strictly and keep raw content.
- `close()`/context exit are idempotent, close only resources they own and propagate safety uncertainty correctly. The core `VisaTransport` treats PyVISA `ResourceManager` as borrowed even when created internally; do not double-close it or break sessions in other drivers.
- Core `operation_lock()` protects indivisible RF configuration/status sequences. Follow a single documented lock order across driver/core layers.
- Enforce finite operation and end-to-end profile deadlines, pacing and cancellation. Core handles transaction-level deadline/error translation; remove duplicate PyVISA-specific retry loops, bespoke locks and generic VISA resource managers unless a specific uncovered case requires them.
- After a write timeout or disconnect, consider physical output state **UNKNOWN**. Do not automatically reissue mutation, restart a profile, or re-enable RF after reconnection.
- Bound native status responses (e.g. documented maximum plus conservative response policy); on truncated/ambiguous response, invalidate transport as appropriate rather than parsing stale bytes.
- Distinguish a success-returning VISA `write` from confirmed RF OFF. Keep `OFF_UNCONFIRMED` and require independent HIL evidence before claiming actual OFF.

### Illustrative adapter pattern (not a drop-in production implementation)

~~~python
from scpi_driver_core import ScpiClient
from scpi_driver_core.transport import VisaTransport, ReadMode, ReadRequest

transport = VisaTransport("GPIB0::2::INSTR", timeout_s=2.0)
client = ScpiClient(transport, timeout_s=2.0, minimum_interval_s=0.25)
transport.open()  # no *IDN? or SCPI traffic

# Native message grammar and termination belong to the Panasonic layer.
client.write_bytes(b"FR1MZ\r\n")

# Native talker mode / EOI must first be configured according to the manual.
status_bytes = client.read_bytes(
    ReadRequest(mode=ReadMode.BACKEND_DEFINED_MESSAGE, maximum_size=512)
)

transport.close()
~~~

This shows available core APIs only. For real use choose exactly one qualified termination mode, ensure output safety and use `try/finally` or a context manager. It is **not** permission to send an RF command to an unqualified bench.

**Gate G3:** no direct PyVISA write/read duplicated in driver, offline fault injection and borrowed-manager tests pass, no unexpected SCPI bytes, deterministic trace.

## 4. RF-safety invariants and public API compatibility

Preserve existing public class contract `VP8122A`, `RFProfile`, `NativeCommands`, `ProtocolValueError` and safety-oriented exceptions, plus the legacy compatibility module. If necessary, add a deprecation adapter with user-visible release note rather than breaking imports.

Required invariant matrix:

| Action/fault | Required RF behavior / state |
|---|---|
| Constructor / discover / connect | No RF ON; no unsolicited SCPI query |
| Offline profile validation failure | Zero I/O |
| Configure allowed profile | Explicit OFF candidate before setpoint updates; never RF ON |
| Configure step failure | Attempt one bounded OFF where transport permits; state UNKNOWN unless proven |
| Enable without explicit authorization | Reject with zero RF writes |
| Enable with explicit authorization but no configured profile | Reject |
| Timeout during RF ON write | RF state UNKNOWN; no retry |
| Reconnect after failure | No previous profile replay or RF-ON restoration |
| Read status failure | Preserve raw evidence and transport fault; never fabricate confirmed OFF |
| Close/disconnect while RF may be on | Attempt qualified OFF policy when safely possible; always release transport; propagate uncertainty |
| Two concurrent sessions on one bus | No resource-manager close side effect or interleaved unsafe operations |

Evaluate whether default `close()` output-OFF writes remain appropriate in connection-only sessions, and ensure faulted transport cleanup cannot prevent resource release. RF physical state must not be confused with session/transport state.

Where `TM0` provides actual status fields, implement correlation between *requested*, *instrument-reported*, and *externally measured* values without conflating these evidence levels. `COOF` controls continuous attenuation, **not** RF output OFF. The candidate `APOF`/`APON` must have verified bus and electrical semantics before HIL approval.

**Gate G4:** safety fault-injection tests for each outgoing command boundary, cancellation, lock contention, timeout, reconnect and cleanup; no silent unsafe state.

## 5. Determine whether core needs changes — conditional dependency

First build a core compatibility table:

| Requirement | Existing core candidate | Decision criteria |
|---|---|---|
| Byte-native VISA I/O | `VisaTransport.write/read` | Reuse |
| Operation IDs, pacing and locking | `ScpiClient.write_bytes/read_bytes/operation_lock` | Reuse if exact path is safe |
| Bounded GP-IB END read | `ReadRequest(BACKEND_DEFINED_MESSAGE)` | Test native talker behavior |
| Local-control bus command | `VisaTransport.go_to_local` | Inspect `deassert_gtl` vs desired addressed GTL |
| Connection lifecycle | `VisaTransport`, optional `ScpiSession.open(probe=False)` | Verify no SCPI probe anywhere |
| Health / reconnect / identity | `ScpiSession` defaults to `*IDN?` | Avoid or adapt **without** Panasonic-specific code in core |
| Trace/audit | Existing core tracing | Reuse without logging secrets or misreporting TX |
| Mutating command retry | `ReplayPolicy.NEVER` and core transport-fault semantics | Never automatically replay |

If a **generic** gap is actually demonstrated (e.g., bus-level *addressed* GTL vs REN deassertion, configurable protocol-agnostic probe callback or native talker operation that cannot be represented), create a **separate core PR first**:
- Unit/integration tests for multiple representative generic transports, not VP-8122A-only cases.
- No Panasonic command strings, RF policy, firmware special cases or dependency on this concrete driver.
- Update public documentation and compatibility notes; increment core version based on current metadata, not a hardcoded guess.
- Require independent review, green core CI and merged core PR **before** pinning the new core version in the driver.
- Do not expand the core into a general arbitrary-command descriptor DSL.

If current public core already supports all required behavior, explicitly record **“core changes unnecessary”** and make **no core PR**.

**Gate G5:** reusable generic core only, no new SCPI assumptions and no downstream regressions (especially N6700 driver compatibility).

## 6. Packaging, examples and developer experience

- Driver distribution `panasonic-vp8122a` retains root package `panasonic_vp8122a/`.
- Add a properly bounded dependency on the tested version of `scpi-driver-core[visa]`; do not depend directly on PyVISA unless there is a specific additional public API used by the driver. Document VISA backend requirements separately.
- Ensure no installation path implicitly falls back to a simulator on hardware failure.
- Preserve public import/class names, type signatures where possible, and add meaningful deprecations for changed aliases or exception types.
- Provide one **offline** no-hardware example and one read-only HIL preparation example; energized example must require explicit authorization and bench safeguards.
- Update README's **22-family command coverage table** with migration state, preserve distinctions `Encoded / Partial / Missing / HIL-unverified`. Do not equate core transport migration with completion of command families.
- Update `Doc/GPIB/COMMAND_REFERENCE.md` only if new validated evidence changes command support.
- Record source manual image links and remaining limitations (including unreadable `FM2.png`).
- Update version, changelog, `docs/REMEDIATION_STATUS.md` and HIL checklist.
- Ensure package build/editable install works from clean environment on Python 3.10–3.13.

**Gate G6:** fresh-env imports, package build, dependency pin, README examples, legacy examples and release metadata agree.

## 7. Full automated test plan and mandatory watchdogs

Reuse core's mandated layers from `AGENTS.md` / `docs/testing.md`, not an ad-hoc new suite:

1. **pytest unit tests:** every native command vector, validation boundary, mode restrictions, profile serialization, parser field position, external control/preset authorization and output-state transitions.
2. **MockTransport / ScriptedScpiTransport:** exact native byte sequences, write/read errors, transport faulting and late replies, command pacing, timeout, caller cancellation, idempotent close/reopen. Scripted transport is a simulator, **not** SCPI syntax endorsement.
3. **Hypothesis:** numeric boundaries, NaN/Inf/bool exclusion, precision bands, encoding/termination/255-byte invariant, TM0 parser with duplicate headers, malformed status, command mutation/replay invariants.
4. **PyVISA-sim integration where applicable:** public `VP8122A -> ScpiClient -> VisaTransport -> PyVISA -> simulation`. A simulation backend might not model native GPIB EOI, REN or real talker mode; document unrepresentable cases and cover through transport doubles + physical HIL.
5. **pytest-timeout / concurrency watchdog:** finite limits per test and whole CI session, shortened timeouts for deadlock tests, parallel configure/read/close, forced backend hangs, lock ordering and fault recovery.
6. **Packaging / CI:** clean build, wheels/metadata, ruff/mypy if part of approved project baseline, Python 3.10–3.13, offline tests always run without attached instrument.
7. **HIL suite prepared but NOT auto-executed:** exact GPIB adapter/backend, byte-level trace for termination/EOI, talker modes, REN/GTL local control and output OFF, independent RF measurements, all tracked against issue #5.

All offline tests must assert **zero unintended `*IDN?` / `SYST:ERR?` / `*OPC?` traffic** throughout connect, readback, health checks, failure/recovery and close.

Collect: Python version, core version/commit, driver version/commit, VISA backend (sim or real), pytest versions, executed test count, coverage and failing seeds. Record "NOT RUN" for any skipped HIL case. Do not use a mock pass as evidence of a physical output state.

**Gate G7:** updated offline baseline green, new edge-case coverage, regression against legacy behavior, migration-specific safety tests and CI passed.

## 8. GitHub PR and merge sequence

Run each stage **sequentially**, never merge ahead of dependencies:

| PR | Deliverable | Dependency |
|---|---|---|
| PR-1 | Contract/baseline report, native goldens, protocol framing plan | G0 |
| PR-2 | Native serialization and positional status parsing fixes | PR-1 |
| PR-3 (conditional) | Generic core changes only if conclusively needed | PR-2 evidence |
| PR-4 | Replace driver transport/session internals with core APIs | PR-2, core PR if any |
| PR-5 | RF safety/concurrency/timeout behavior and legacy compatibility | PR-4 |
| PR-6 | CI, layered tests, packaging, examples, documentation and independent audit | PR-5 |
| HIL qualification | Separate explicitly authorized physical GP-IB/RF checks | Issue #5, no auto merge |

You may consolidate adjacent PRs if dependencies and independent review gates remain traceable, but **do not make one unreviewable giant PR**. At each PR:
- Apply version increment in changed repository.
- Run targeted tests, full relevant regression, formatting/type checks, package installation/build.
- Perform independent code and safety review with file/line citations, fix findings and rerun.
- Inspect GitHub status and only merge if all non-HIL mandatory gates are successful and no open P0/P1 software finding remains.
- Preserve full commit SHA, PR URL, version, observed tests and merge SHA in a report.
- Never force-merge an unknown/broken CI state. Do not claim HIL success without evidence.

If hardware is unavailable, **complete all possible offline PRs**, push and merge only those that are software-qualified, keep physical qualification blocked, and report exact remaining tests.

## 9. Definition of done and final report

The migration is **software complete** only when:
- Driver uses core transport and byte execution; no duplicated transport or unsupported SCPI traffic.
- Native Panasonic command grammar, terminations and talker semantics are preserved and tested offline.
- Strict validation, safe RF authorization and output-UNKNOWN fault behavior remain intact.
- No automatic RF enable or state restoration on reconnect.
- Old public imports and documented API behavior remain compatible or have explicit approved migration notes.
- Tests and CI run with finite watchdog limits, package installation succeeds on supported Python versions, exact versions are recorded.
- The updated 22-family matrix and issue #5 accurately distinguish implemented/unimplemented and HIL-unverified commands.
- Appropriate PRs are independently reviewed, corrected and merged with version increments.
- Remaining HIL protocol and electrical evidence is not misrepresented as complete.

Provide a final concise table with **stage, status, branch, PR, version, tests, CI, findings, merge result**, followed by a separately labeled **physical HIL blockers** section. State what code was actually changed rather than presenting plans as implementation.

**Do not substitute a generic SCPI rewrite for the native VP-8122A transport migration.**
