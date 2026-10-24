## v0.2.5 (software test preparation; NOT HIL-qualified) — 2026-10-24

- Add a fail-closed real-instrument native GPIB HIL readback-only test for TM0/TM1/TM2.
- Reject hardware HIL on CI, require explicit local authorization, VISA primary address, terminator, operator, serial, controller and evidence directory.
- Capture requested native bytes, raw replies, ordered status fields and JSON evidence without equating transport observations with measured RF state.
- Block all RF mutations, generic SCPI probes and ASCII GTL before physical VISA I/O; close only the transport during passive HIL, avoiding the unqualified driver-close APOF.
- Add offline safety-gate tests, HIL runbook and full staged automated HIL command-verification implementation task. No real hardware tests performed.

## v0.2.4 (development; NOT HIL-qualified) — 2026-10-24

- Add explicit native byte-level GPIB framing (EOI/LF/CRLF), 255-byte boundary enforcement, and ordered TM0 status model preserving repeated prefixes and raw bytes.
- Correct manual-documented AM upper limit 125%, FM maximum 300 kHz and three-band FT precision. Add TM0/TM1/TM2 mode serializer.
- Begin migration to core byte transport; addressed GTL prerequisite under scpi-driver-core PR #12.
- Physical RF safety, command acceptance, EOI and output OFF remain HIL-unqualified.

# Changelog

## 0.2.3 — 2026-10-24
- Add staged, repository-verified VP-8122A → scpi-driver-core implementation task with strict native GP-IB isolation, RF safety gates, API compatibility, watchdog regression tests, and conditional core PR requirements.
- Documentation/task-only change; the runtime migration is **not** implemented and HIL remains unqualified.

## 0.2.2 — 2026-10-24
- Transcribe 18 readable VP-8122A manual excerpts from Doc/GPIB into a source-linked native-command and GPIB interface reference.
- Add the 22-family implementation coverage table and explicit gaps to README.
- Document AM upper-limit (125% manual vs 100% code), FM upper-limit (300 kHz manual vs 999 kHz code), FT precision and missing TM selection as follow-up issues.
- Documentation-only inventory; **not hardware qualified**.

## 0.2.1 — 2026-10-24
- Tighten RF frequency step validation at 140 MHz and AM/FM modulation resolution.
- Track disconnected-but-OFF-unconfirmed state and verify VISA GTL result.
- Extend test fault coverage.

## 0.2.0 — 2026-10-24
- Add native VP-8122A command encoder, strict validation and RF profile model.
- Add explicit PyVISA resource handling, native talker reads, bus-level GTL and cleanup.
- Protect RF output with OFF-before-configuration and separately authorized RF ON.
- Add root-level installable package, offline tests, CI and physical HIL checklist.
- Preserve HIL/protocol uncertainty; **not hardware qualified**.

## 0.1.0 — 2026-10-24
- Independent review report and release-gate baseline.
