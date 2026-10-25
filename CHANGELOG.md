## v0.2.7 (serializer coverage; NOT hardware-qualified) — 2026-10-25

- Add `NativeCommands.frequency_khz` (`FRxxKZ`, 10–280000 kHz, same 10/20 Hz step rule as `frequency_hz`).
- Add `NativeCommands.level_mv` (`APxxMV`, 0.000050–2000 mV) and `level_uv` (`APxxUV`, 0.050–2000000 µV).
- Add `NativeCommands.continuous_control`, `continuous_step` and `continuous_decrement_db` (`COON`/`COOF`, `COUP`/`CODN`, `CO0`–`CO10`); continuous level control is not RF output OFF.
- Ranges transcribed from manual tables 4-3, 4-7 and 4-9; golden-vector and Hypothesis tests added. Serializer-only: no high-level driver wiring, no change to RF enable/OFF behaviour. All limits remain NOT HIL-qualified.

## v0.2.6 (HIL test automation; NOT hardware-qualified) — 2026-10-24

- Add fail-closed readback-only physical HIL suite for native TM0/TM1/TM2, with exact authorized host-byte allowlisting and core transport cleanup that avoids unqualified APOF during passive reads.
- Add CLI bench identity/authorization/timeout/configuration gates and uniquely named JSON evidence preserving raw replies and ordered repeated TM0 fields.
- Add offline regression tests proving no SCPI probes, RF output mutations or ASCII bus commands can pass the HIL transport allowlist.
- Add full future automatic native-command HIL implementation task, detailed local runbook and clear separation of talker observations versus independently measured RF state.
- All hardware behavior, including EOI and RF physical OFF, remains NOT QUALIFIED. Software-only changes.

## v0.2.5 (documentation-only status update) — 2026-10-24

- Record verified merged native-GPIB migration to scpi-driver-core dev12 and up-to-date project status.
- Reconcile deep-review findings and open GitHub issue/PR disposition in docs.
- No runtime behavior changes; physical GPIB and RF safety remain **NOT HIL-QUALIFIED**.

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
