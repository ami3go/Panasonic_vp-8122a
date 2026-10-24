# Panasonic VP-8122A — native GPIB RF generator driver

Version **0.2.5**: native-byte transport with gated talker-only HIL verification suite. **NOT HIL-QUALIFIED**.

The VP-8122A uses legacy GP-IB native program words, **not standard SCPI**. The driver does not send `*IDN?` on connection. It uses compact command candidates consistent with historic messages (`FR...MZ`, `AP...DB`, `APOF`), but command acceptance and RF output safety require an actual VP-8122A and supported GPIB adapter to verify.

**Core migration:** using scpi-driver-core v0.1.0.dev12 at the pinned merged commit, through VisaTransport and ScpiClient byte-level APIs. [Implementation specification](task/VP8122A_SCPI_DRIVER_CORE_MIGRATION_TASK.md). RF/HIL qualification is still blocked.

## Native GPIB command coverage (from `Doc/GPIB/`)

The instrument uses **native GP-IB program codes, not SCPI**. The source-backed [full command reference and per-variant coverage matrix](Doc/GPIB/COMMAND_REFERENCE.md) transcribes all **18 readable image excerpts** (19 discovered; `FM2.png` returned no image bytes). Coverage means **code representation, not an instrument/HIL pass**.

**Legend:** **Encoded** = all core variants visible in reviewed excerpts are produced by `NativeCommands`; **Partial** = some variants or workflows are absent or supported only by the historical compatibility builder; **Missing** = not implemented in the modern serializer. Even **Encoded** entries remain **not HIL-qualified**.

| Native command family | Instrument function | Driver coverage | Key limitation |
|---|---|---|---|
| `FR` | RF frequency in MHz/kHz | Partial | `FR...MZ` encoded; `FR...KZ` absent |
| `AP` | RF level, ON/OFF, 50/75 Ω | Partial | dBm/dBµV encoded; mV/µV level formats missing |
| `LE` | Alternative RF level/output header | Missing | `LE` alias not emitted |
| `EM` | EMF/open-end level display | Missing | `EMON`/`EMOF` not exposed |
| `CO` | Continuous output-level control | Partial (legacy) | ON/OFF, UP/DN, 0–10 dB in historical builder only; **not RF OFF** |
| `AM` | AM depth, ON/OFF, source | Partial | Manual range 0–125% now enforced; high-level sources remain limited |
| `FM` | FM deviation, ON/OFF, source | Partial | Manual upper limit 300 kHz now enforced; modes remain partial |
| `MS` | Main/subchannel mono/stereo modes | Partial | Mode values encoded; M+S ratio and mode combinations incomplete |
| `PL` | Pilot level and ON/OFF | Partial | Core values encoded; explicit optional `PC` suffix and profile integration absent |
| `FT` | Total FM deviation | Partial | Three precision bands now encoded; high-level setter missing |
| `PR` | Pre-emphasis OFF / 25 / 50 / 75 µs | Encoded | No dedicated high-level operation |
| `SC` | SCA signal ON/OFF | Missing | Not exposed |
| `LV` | Composite signal output level | Encoded | No dedicated high-level operation |
| `NP` | Negative peak clipper ON/OFF | Encoded | Source is TM0 status description; HIL acceptance unknown |
| `RC` | Preset memory recall 00–99 | Missing | Recall can alter output; guard before adding |
| `ST` | Preset memory store 00–99 | Missing | Nonvolatile write; explicit authorization required |
| `TM` | Talker mode selection 0/1/2 | Partial | `TM0`/`TM1`/`TM2` selector and bounded native talker read; TM1/TM2 typed grammar pending |
| `DR` | Relay-drive reverse frequency | Missing | Appears in TM0 output; input grammar not validated |
| `AS` | Memory auto-sequence mode | Missing | TM0 status only |
| `NT` | Auto-sequence interval | Missing | TM0 status only |
| `P1` | External control port 1 | Missing | TM0 status only; potential external actuation |
| `P2` | External control port 2 | Missing | TM0 status only; potential external actuation |

**22 header families:** 3 encoded · 9 partial · 10 missing. Native interface commands such as **GTL**, **SDC**, **DCL**, **UNL** and **LLO** are **IEEE-488 bus operations**, not ASCII instrument commands; see the [bus-command section](Doc/GPIB/COMMAND_REFERENCE.md#ieee-488-buscontrol-operations-not-vp-8122a-ascii-commands).

**Message format:** up to 255 ASCII bytes; CRLF, LF or EOI terminator; comma/space permitted between complete program words. The original manual gives `FR1MZ,AP-20DM,FM2.5` as an example. Actual GPIB adapter termination and RF electrical behavior still require bench qualification.

## Installation

`python -m pip install -e '.[test]'` (Python 3.10+, a VISA backend such as NI-VISA and a GPIB controller also required for live hardware). There is no `src/` packaging layout; the package is `panasonic_vp8122a/` at the root.

## Example (RF remains off)

```python
from panasonic_vp8122a import RFProfile, VP8122A

with VP8122A('GPIB0::2::INSTR') as rf:
    rf.configure(RFProfile(frequency_hz=531_000, level_dbuv=20.0, am_depth_percent=30))
    # RF output is NOT enabled. OFF remains UNCONFIRMED without hardware readback.
```

Enabling RF requires a *separate explicit call* to `rf.enable_output(authorized=True)` after `configure`; use only with properly terminated and rated RF connections. Resource name is **never auto-selected**. `read_status()` explicitly sends native `TM0` to select the talker-mode response, then performs an END-bounded read. The lossless ordered result is `last_native_status`; `status_fields()` retains its historical lossy dictionary API. It never sends `*IDN?` or a SCPI query. `return_local()` sends a bus-level GPIB GTL operation via VISA, not a text command.

## Safety and known limits

* **Hardware qualification blocked.** No real VP-8122A or USB-GPIB controller was available for this implementation. Native command delimiters, accepted precision, EOI, response framing, state readback, and actual RF OFF behavior have not been proven. A successful VISA `write()` does not guarantee safe output.
* Strict validation rejects non-finite/out-of-range/unsupported values without silently clamping them. Driver assumes provisional limits adapted from historical source; cross-mode combinations without qualified behavior are rejected.
* `configure()` sends an OFF candidate first, validates the entire profile before I/O, and attempts OFF again after failures. A failed OFF attempt leaves `UNKNOWN` state. Automatic retries of state-changing commands are forbidden.
* `close()` attempts RF OFF and closes instrument resources; on failure it raises an error and reports `DISCONNECTED_RF_UNKNOWN`. When caller owns the ResourceManager, it is not closed.
* Native write termination supports EOI-only (default), LF, or CRLF; no arbitrary SCPI separators. The core sends raw bytes with VISA terminations disabled. EOI generation by the selected controller and actual RF safety **must be qualified on hardware**. The historical 250 ms pacing is provisional and configurable.

## Verification

`python -m pytest -q` runs deterministic transport mocks and serialization/safety checks **without instruments**. Run physical qualification separately with the checklist in [docs/HIL_QUALIFICATION.md](docs/HIL_QUALIFICATION.md).

Original review: [review and 22 findings](task/VP8122A_DEEP_REVIEW_2026-10-24.md). Implemented changes and deferred evidence are tracked in [docs/REMEDIATION_STATUS.md](docs/REMEDIATION_STATUS.md).

## Core migration and CI (v0.2.4 development)

- Core prerequisite: [addressed GTL PR #12](https://github.com/ami3go/scpi-driver-core/pull/12), merged as `1e03b6837f96f200dc28233490639f2f080e1791`.
- Driver dependency pins that Git commit because this development-version package is not assumed published to PyPI. This requires Git access when installing.
- Supported operations use `ScpiClient.write_bytes/read_bytes` and `VisaTransport` resource ownership. No `ScpiSession` is instantiated, preventing default `*IDN?` health checks.
- One native word per write, 255-byte bound including LF/CRLF, ASCII-only and known prefixes. Native TM0 status preserves ordered repeated headers and raw bytes.
- The legacy `manager_factory` is accepted but core intentionally does **not** close any ResourceManager, even one it retrieves, because PyVISA may share a singleton across instruments.
- State after uncertain mutation is `UNKNOWN`, and a faulted transport is not automatically reconnected, retried or replayed. No result is a measured RF output level.
- Verify `pytest -m 'not hardware'` and CI across Python 3.10–3.13. Hardware/HIL remains separately gated.



## Automated native GPIB HIL verification (v0.2.5)

The [physical readback-only HIL suite](tests/test_hil_authorized.py) verifies Panasonic TM0/TM1/TM2 selection and bounded talker responses through the public driver and shared core. It requires manual local bench authorization and never sends SCPI, APOF, APON or RF configuration commands. The test intentionally releases the VISA transport without invoking driver close(), which would transmit the not-yet-electrically-qualified APOF candidate.

The [HIL automation runbook](docs/HIL_AUTOMATION.md) specifies explicit resource/authorization/environment variables, command allowlisting, evidence collection and the safe local command. The [full automated native-command qualification task](task/VP8122A_AUTOMATED_NATIVE_GPIB_HIL_TASK.md) covers future command-family HIL, independently measured RF OFF, spectrum/power measurement, controlled mutating operations, fault injection and reports.

Run offline guards without any instrument using `python -m pytest -q tests/test_hil_guards.py`. Physical tests remain excluded from ordinary CI. **No TM mode, RF output or native family is yet confirmed HIL-qualified on physical hardware.**
