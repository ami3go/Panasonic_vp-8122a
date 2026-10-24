# Panasonic VP-8122A — GPIB Python driver

Python/PyVISA prototype for the Panasonic VP-8122A AM/FM RF signal generator.

**Repository version:** 0.1.0 (documentation and review baseline; **not** a hardware-qualified driver release).

**Review and remediation plan:** [VP8122A deep driver review — 2026-10-24](task/VP8122A_DEEP_REVIEW_2026-10-24.md).

> **Safety / interoperability:** This code has known connection, GPIB command, resource-management and RF-safety issues. Do not use for unattended RF testing until the P0 findings are corrected and physical HIL tests pass. The VP-8122A uses legacy native GP-IB program codes; do not assume SCPI or `*IDN?` support.

Original note: 26.08.2021 — work in progress.

## Native GP-IB command reference and coverage

The VP-8122A uses **manufacturer-specific GP-IB program codes**, **not SCPI**. A method that builds a command string does **not** mean the instrument has accepted that exact wire format. The current baseline has unresolved word spacing, legacy identification, talker readout, GTL bus control and RF-output safety issues.

- [Native GP-IB command reference](docs/VP8122A_GPIB_COMMAND_REFERENCE.md) — observed code families, exact published examples, source provenance, complete builder mode map and known unknowns.
- [Command coverage and release blockers](docs/COMMAND_COVERAGE.md) — implementation gaps, grammar uncertainty and physical HIL status.
- [Original manual and GPIB excerpts](Doc/GPIB/) — archival evidence; these are not driver test results.

**Scope:** The table lists **21 command families identified in currently reviewed repository evidence**, plus `GTL`, which is an **IEEE-488 bus/interface command, not a native instrument program code**. This is **not an assertion of exhaustive manufacturer command coverage**: full exact-model manual transcription and hardware qualification remain pending. All rows are **not HIL tested**.

| Family | Function | Driver coverage | Bench-qualified? |
|---|---|---|---|
| `FR` | RF carrier frequency | Builder only | No |
| `AP` | RF amplitude, impedance and output mode | Builder only | No |
| `CO` | Continuous/control output | Builder only | No |
| `AM` | AM depth and source | Builder only | No |
| `FM` | FM deviation and source | Builder only | No |
| `MS` | Main/sub stereo selection | Partial | No |
| `PL` | Pilot level and enable | Builder only | No |
| `FT` | Total FM deviation | Builder only | No |
| `LV` | Composite output level | Builder only | No |
| `PR` | FM pre-emphasis | Builder only | No |
| `NP` | Negative peak clipper | Builder only | No |
| `SC` | SCA signal | Missing | No |
| `RC` | Preset memory recall | Missing | No |
| `ST` | Preset memory store | Missing | No |
| `TM` | GPIB talker modes | Missing | No |
| `EM` | Observed status element | Missing | No |
| `DR` | Drive reverse-frequency | Missing | No |
| `AS` | Observed status element | Missing | No |
| `NT` | Observed status element | Missing | No |
| `P1` | Observed status element / port 1 | Missing | No |
| `P2` | Observed status element / port 2 | Missing | No |
| `GTL` | IEEE-488 Go To Local (bus command, not program code) | **Incorrect** | No |

**Totals:** 10 builder-only families; 1 partially covered; 10 missing; 1 incorrectly implemented bus operation (`GTL`). **Instrument-verified: 0/21 native families.** The driver is not currently suitable for unattended or unverified RF tests. `*IDN?` is **not established** as supported by this legacy instrument despite being sent in the current connection code.
