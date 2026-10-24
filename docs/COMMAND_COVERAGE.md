# Panasonic VP-8122A — GP-IB command coverage

**As of 2026-10-24; baseline source:** [`src/PANASONIC_VP_8122A.py`](../src/PANASONIC_VP_8122A.py).  
**Scope:** command families evidenced by current code, archived command scans and the driver's sample status line. See [full native GP-IB reference](VP8122A_GPIB_COMMAND_REFERENCE.md) for provenance, candidate spellings, limitations and exact documented examples.

**Implementation labels:** `Builder only` = methods return command strings but validity/transport/end-to-end behavior is not verified; `Missing` = no dedicated builder; `Incorrect` = current implementation uses a wrong interface mechanism. `Partial` = builder exists but evidence shows missing observed forms. **All families are HIL-UNVERIFIED.** A returned string is not a qualified working driver operation.

| Family | Function | Current code / API | Coverage | Exact wire grammar verified? | HIL |
|---|---|---|---|---|---|
| `FR` | RF carrier frequency | `storage.freq.MHz/kHz.val()` | Builder only | **No — intra-word space** | Not run |
| `AP` | RF amplitude, impedance and output mode | `storage.output` | Builder only | **No — intra-word space** | Not run |
| `CO` | Continuous/control output | `storage.control_out` | Builder only | **No — RF switching semantics ambiguous** | Not run |
| `AM` | AM depth and source | `storage.am` | Builder only | **No — intra-word space** | Not run |
| `FM` | FM deviation and source | `storage.fm` | Builder only | **No — intra-word space** | Not run |
| `MS` | Main/sub stereo selection | `storage.main_and_sub_ch` | Partial | **No — `MS100PC` absent** | Not run |
| `PL` | Pilot level and enable | `storage.pilot_signal` | Builder only | **No — intra-word space** | Not run |
| `FT` | Total FM deviation | `storage.total_fm_deviation` | Builder only | **No — limits unverified** | Not run |
| `LV` | Composite output level | `storage.composite_sign_out_level` | Builder only | **No — limits unverified** | Not run |
| `PR` | FM pre-emphasis | `storage.fm_stereo_pre_emphasis` | Builder only | **No — intra-word space** | Not run |
| `NP` | Negative peak clipper | `storage.neg_peak_clipper` | Builder only | **No — intra-word space** | Not run |
| `SC` | SCA signal | — | Missing | No | Not run |
| `RC` | Preset memory recall | — | Missing | No | Not run |
| `ST` | Preset memory store | — | Missing | No | Not run |
| `TM` | GPIB talker modes | — | Missing | **Related manual examples only** | Not run |
| `EM` | Observed status element | — | Missing | No | Not run |
| `DR` | Drive reverse-frequency | — | Missing | **Related manual example only** | Not run |
| `AS` | Observed status element | — | Missing | No | Not run |
| `NT` | Observed status element | — | Missing | No | Not run |
| `P1` | Observed status element / port 1 | — | Missing | No | Not run |
| `P2` | Observed status element / port 2 | — | Missing | No | Not run |
| `GTL` | IEEE-488 Go To Local (bus command, not program code) | `com_interface.disconnect()` | **Incorrect** | **Known type mismatch** | Not run |

**Inventory summary:** 21 observed native program-code families: **10 builder-only**, **1 partial**, **10 missing**, plus **1 incorrectly treated bus command** (`GTL`). **0/21** native families qualified by instrument hardware tests. This is a count of *observed families*, **not total manufacturer command count** or percentage of complete command/mode coverage.

## Coverage blockers (highest priority first)

1. **P0 — Exact grammar:** current builder serializes `FR 1MZ` rather than the manual example `FR1MZ`; resolve delimiter, unit/number formatting and EOI policy against VP-8122A-specific pages and adapter capture before claiming support.
2. **P0 — RF-safe operation:** differentiate RF ON/OFF from `CO` continuous-output control, prove an independent RF-off state, and avoid enabling RF automatically.
3. **P0 — GPIB lifecycle:** stop mandatory `*IDN?`; correctly perform interface GTL and safe resource disposal.
4. **P1 — Read/status:** implement and qualify native talker `TM`/status receive handling; do not invent SCPI `?` forms.
5. **P1 — Feature completeness:** implement missing `SC`, `RC`, `ST`, `DR`, `EM`, `AS`, `NT`, `P1`, `P2` only after command descriptions and parameter domains are checked; extend `MS` if status documentation confirms `MS100PC`.
6. **P1 — Golden vectors:** offline exact bytes and argument-boundary tests for each supported command, then separately authorized HIL reads/measurements and retained transcripts.

## Release interpretation

- A source-level command generator is **not** proof that a command works on the instrument.
- Exact grammar and **physical RF OFF confirmation** are independent release gates.
- “Not run” must remain separate from PASS/FAIL; nothing has been labeled hardware-qualified.
- For provenance and the complete working inventory, read [native GP-IB command reference](VP8122A_GPIB_COMMAND_REFERENCE.md).