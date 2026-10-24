# VP-8122A v0.2.4 native-GPIB core migration — software review and gate record

**Date:** 2026-10-24  
**Task:** VP8122A-SCPI-CORE-MIGRATION-01  
**Status:** Software implementation under regression verification; **NOT hardware/HIL qualified**  
**Review method:** Static architecture/implementation review and fault-injection CI, with follow-up fixes. This is **not** an external human review or instrument-level measurement.

## Architecture / public contract matrix

| Concern | Before: PR #4 / v0.2.3 | After: PR #8 / v0.2.4 | Compatibility risk / disposition |
|---|---|---|---|
| Root import and `RFProfile` | `panasonic_vp8122a.VP8122A`, `RFProfile` | Preserved | No `src/` layout introduced |
| Historical import | `src.PANASONIC_VP_8122A` | Preserved; `com_interface` uses modern driver | Raw writes still require explicit authorization |
| Device transport | Hand-written `PyVISA.ResourceManager` / `inst.write`, `inst.read` | `VisaTransport` and `ScpiClient.write_bytes/read_bytes` | Controlled, intentional byte-I/O migration |
| Resource ownership | Factory-created manager was explicitly closed | Core treats process manager as borrowed/shared | Intentional ownership behavior change; documented |
| Pacing | Explicit `clock` after each `inst.write()` | `ScpiClient.minimum_interval_s`; `clock` injected as pacing sleep | Different placement, must verify real timing in HIL |
| Native program termination | PyVISA `write_termination` | Explicit 7-bit ASCII raw bytes, EOI/LF/CRLF | EOI bus assertion remains HIL prerequisite |
| Native talker read | Raw `inst.read()` with no TM mode selection | Native `TM0` mode selection, then bounded byte read | **Intentional visible behavior change:** status read sends `TM0` |
| Status parsing | Lossy two-letter dictionary | Ordered `NativeStatus.fields` plus preserved `raw`; compatibility `status_fields()` remains lossy | TM0 exact 25-field grammar and TM1/TM2 mode-specific meaning unqualified |
| Addressed GTL | Direct `control_ren(address_gtl)` | Core `VisaTransport.go_to_local_addressed()` | Shared core v0.1.0.dev12, native bus command only |
| RF enable | `enable_output(authorized=True)` | Preserved | Cannot auto-enable during open/reconnect |
| Uncertain output | `OFF_UNCONFIRMED` / `UNKNOWN` | Preserved, RF ON failure remains `UNKNOWN` | Neither state is physical measurement |
| Errors | Panasonic `TransportError` wrapping PyVISA | Same API, wrapping core transport errors with original `__cause__` | Caller can inspect cause, no blind retry |
| Session / health | Own lifecycle | Own explicit driver lifecycle with core transport/client | Avoids `ScpiSession` default `*IDN?` health probe |
| Release status | Not HIL-qualified | Not HIL-qualified | Hardware approval remains blocked |

## Core applicability and dependency

Core `ScpiClient.write_bytes`, `read_bytes`, locking and per-I/O timeout, plus `VisaTransport` byte framing / buffer invalidation and resource cleanup, were reusable without core protocol changes. Exactly one verified generic infrastructure gap was addressed: `go_to_local()` previously invoked `deassert_gtl`, whereas native Panasonic needs opt-in addressed `address_gtl` without changing REN globally.

The generic core change [scpi-driver-core PR #12](https://github.com/ami3go/scpi-driver-core/pull/12) was merged first as `1e03b6837f96f200dc28233490639f2f080e1791` (v0.1.0.dev12). Core CI and N6700 compatibility passed before merge. Driver pins this exact Git commit; no Panasonic command strings or hardware safety rules were added to core.

## Review findings and disposition

| ID | Severity | Finding | Disposition | Evidence |
|---|---|---|---|---|
| VPM-01 | P0 protocol | SCPI session default `*IDN?` would be invalid for native Panasonic | **Addressed by architecture:** no `ScpiSession`; only core byte methods, negative no-SCPI tests | `driver.py`, `tests/test_core_contract.py` |
| VPM-02 | P1 bus isolation | GTL global REN deassert differs from addressed bus command | **Fixed in core** opt-in capability; remains HIL-unqualified | core PR #12; `return_local()` |
| VPM-03 | P1 status integrity | Dictionary keyed by native two-letter prefix loses repeated fields | **Fixed** new ordered typed record preserving original bytes; dictionary retained for compatibility only | `native.py`, property tests |
| VPM-04 | P1 status state | No explicit native TM mode | **Fixed:** send `TM0/1/2` before read, no SCPI query | `read_status`, byte vector tests |
| VPM-05 | P1 source ranges | AM 100 instead of 125; FM 999 instead of 300; FT incorrect resolution bands | **Corrected** serializer limits; HIL acceptance pending | `protocol.py`, `tests/test_native.py` |
| VPM-06 | P1 framing | No 255-byte wire cap or native ASCII enforcement | **Fixed** pure native serializer, terminator included in length | `encode_program_word`, golden tests |
| VPM-07 | P0 safety | Auto RF ON, SCPI probes, mutation retries, or replay on reconnect | **No such behavior introduced**; explicit RF authorization, uncertainty and fault tests | `driver.py`, `tests/test_core_contract.py` |
| VPM-08 | P1 resource ownership | Closing a shared PyVISA manager could break other sessions | **Fixed** via borrowed-manager ownership in core; documented behavior change for `manager_factory` | core tests + driver mocks |
| VPM-09 | P1 response desynchronization | Malformed native read may leave stale bytes for subsequent operation | **Fixed** retain raw evidence, then invalidate transport and mark UNKNOWN | `read_status`, fault test |
| VPM-10 | P1 legacy behavior | Historical `storage().go_to_local.str()` returns `GTL` literal, which must never reach instrument writes | **Fixed** authorized compatibility `send("GTL")` dispatches bus addressed GTL | legacy adapter + regression |
| VPM-11 | P1 integration | Mock/text VISA tests do not exercise actual core byte API | **Fixed offline** raw mock tests + PyVISA-sim integration and Python 3.10–3.13 CI | test suite and workflow |
| VPM-12 | P1 timing | ScpiClient pacing may consume wall-clock time outside low-level per-operation timeout; no full platform-independent hard interruption of blocked VISA call | **Partially mitigated** explicit profile deadline and pytest-timeout guards; real backend timeout still HIL-dependent | `configure()`, core transports |
| VPM-13 | P0 hardware | `APOF` acceptance and independently measured RF OFF not demonstrated | **BLOCKED: HIL required.** No software inference is accepted as physical confirmation | `docs/HIL_QUALIFICATION.md` |
| VPM-14 | P1 protocol | TM0 complete 25-field positional schema (including adjacent packed fields) not qualified; TM1/TM2 typed semantics absent | **Deferred**, preserve ordered raw evidence and avoid invented typed interpretations | `native.py`, HIL task |
| VPM-15 | P1 implementation breadth | Not all 22 command families have complete serializers / safe high-level actions or golden vectors | **Deferred** unsupported variants must remain clearly indicated in README / manufacturer reference | `Doc/GPIB/COMMAND_REFERENCE.md`, README |

## Validation / CI gate

- Core CI across Python 3.10–3.13 and N6700 downstream compatibility: successful before PR #12 merge.
- Driver offline CI across Python 3.10–3.13: see the **latest** [PR #8 checks](https://github.com/ami3go/Panasonic_vp-8122a/pull/8/checks); do not infer that earlier green runs cover a later commit.
- A fully recorded earlier green development run (`63b1840ae49dd0829f45b7e56bc1bf71a35c71db`) reported **88% statement coverage** (driver 86%, native 97%, protocol 86%); coverage changes after fixes and expanded tests, so prefer the latest workflow artifact.
- Hardware HIL: **NOT EXECUTED**, authorized bench unavailable; separate tests marked `hardware` and excluded from CI.
- No claim that emulator or VISA-sim asserts EOI, true RF OFF, or accepted status field semantics on physical VP-8122A.

## Remaining release gates

1. Validate latest driver PR's Python CI, integration and coverage after review changes and repair any software P0/P1 failures.
2. Finish full manufacturer reference work / complete supported native-family golden vectors before claiming full command coverage. Keep unimplemented families absent rather than guessing writes (notably RC/ST/P1/P2).
3. Confirm EOI and native GPIB talker framing with a physical controller and compare TM0 real status field ordering to full manual fields.
4. Confirm addressed GTL and REN isolation on a multi-instrument bus; approve RF OFF semantics independently with an RF measurement instrument.
5. Complete authorized fault injection and signed hardware qualification evidence, then separately authorize a HIL-qualified release.

**Decision:** Software-only merging is eligible after a fully green head CI and reviewer gate. Physical qualification and an unattended RF-safe release are NOT eligible.
