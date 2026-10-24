# Changelog

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
