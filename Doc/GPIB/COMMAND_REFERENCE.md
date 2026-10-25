# Panasonic VP-8122A — Native GPIB Command Reference and Driver Coverage

**Source review:** 2026-10-24 · **Driver branch:** `feat/v0.2.0-gpib-driver-hardening` · **Driver version:** 0.2.2 documentation/coverage update.

> **Protocol classification:** VP-8122A native 7-bit ASCII GP-IB program codes, **not SCPI**. A leading `*` common command or SCPI subsystem syntax is not inferred. This document is a manual transcription of the 18 readable command/interface images under `Doc/GPIB/`, compared with the modern `panasonic_vp8122a/` code and legacy compatibility module. All examples are **program-code candidates**, not proof of actual device acceptance or measured RF output.

## Source inventory and provenance

19 known images in `Doc/GPIB/` were identified from GitHub history (initial documentation import, later `FR.png`, `MS.png`, `AP_LE.png`). The content API returned **zero encoded bytes for `FM2.png`**; its content cannot be verified. Other images were manually visually reviewed.

| Source | Manual section / table | Coverage |
|---|---|---|
| [`FR.png`](FR.png) | Table 4-3 | RF frequency |
| [`AP_LE.png`](AP_LE.png) | Table 4-7 | RF output amplitude, units, impedance, enable, EMF display |
| [`CO.png`](CO.png) | Table 4-9 | Continuous level control |
| [`AM.png`](AM.png) | Table 4-13 | AM modulation |
| [`MS.png`](MS.png) | Table 4-16 | Main/subchannel stereo modes |
| [`FM.png`](FM.png) | Table 4-25 | FM modulation / limits |
| [`FM2.png`](FM2.png) | Unreadable / empty API response | **Not inspected; cannot claim complete source coverage** |
| [`PL.png`](PL.png) | Table 4-31 | Pilot signal |
| [`FT.png`](FT.png) | Table 4-34 | Total FM deviation |
| [`PR.png`](PR.png) | Table 4-36 | Pre-emphasis |
| [`SC.png`](SC.png) | Table 4-38 | SCA signal |
| [`LV.png`](LV.png) | Table 4-40 | Composite signal output level |
| [`RC_ST.png`](RC_ST.png) | Table 4-42 | Preset recall/store |
| [`cmds.png`](cmds.png) | Section 6-2, table 6-1 | IEEE-488 interface capabilities |
| [`GTL.png`](GTL.png) | IEEE-488 bus management reference | Addressed/universal interface commands |
| [`commands.png`](commands.png) | Section 6-8 | Input grammar/terminators |
| [`TM0.png`](TM0.png) | Section 6-9 | Talker modes TM0, TM1, TM2 |
| [`TM0_replay.png`](TM0_replay.png) | Section 6-9, fields 1–16 | TM0 status output layout |
| [`TM0_replay_.png`](TM0_replay_.png) | Section 6-9, fields 17–25 | TM0 status output layout continuation |

The separate [`Doc/Desible_IDN_on_USBGPIB.txt`](../Desible_IDN_on_USBGPIB.txt) describes a USB–GPIB adapter and examples involving other instruments. It is **not** a VP-8122A command list.

## Transport and input-format rules — explicit manual statements

- Program messages consist of **7-bit ASCII**, up to **255 bytes** per message, see [`commands.png`](commands.png).
- Documented end-of-message delimiters: **CRLF (0D 0A)**, **LF (0A)** or the GPIB **EOI** interface signal.
- Program words may be adjacent or separated by a **comma** or **space between complete program words**. An internal space inside `FR1MZ` or `AP-20DM` is **not established**.
- Manufacturer example: `FR1MZ,AP-20DM,FM2.5` then CRLF. Meaning: 1 MHz, −20 dBm, 2.5 kHz FM deviation.
- The current driver uses individual VISA `write()` operations, normally with **empty write termination**. Whether that drives EOI correctly depends on backend and still requires instrument/adapter qualification.
- The talker section describes **TM0 (setup state)**, **TM1 (total FM deviation)** and **TM2 (external-control port 2 data)**. The instrument returns **LF and EOI simultaneously**. Selecting `TM0` is a device-dependent *program command*; reading the resulting talker stream is a separate GPIB read.
- The interface capabilities are **SH1, AH1, T7, L3, SR0, RL1, PP0, DC1, DT0, C0**; notably there is **no service-request capability, parallel poll, or device trigger** in the manual table.

## Coverage legend

- **Covered (serializer)**: all data codes shown in the cited excerpt have a builder in `NativeCommands`, but may not have a high-level driver method and remain **hardware-unqualified**.
- **Partial**: some modes exist or a legacy builder exists, but not all documented variants, ranges or the complete talker workflow.
- **Missing**: no corresponding current `NativeCommands` builder or supported high-level operation.
- **Status only**: shown in the TM0 status layout; these excerpts alone **do not prove an accepted listener/write grammar**.
- **Bus**: IEEE-488 interface command, not an ASCII VP-8122A program word.

## Comprehensive native command coverage

Values and ranges below are transcribed from the cited manual screenshots. `xx` represents a numeric argument or enumerated code, **not literal text**. This table assesses software command coverage only.

| Family | Native command/data code from local manual | Purpose / constraints | Source | Modern v0.2.2 coverage | Gap / warning |
|---|---|---|---|---|---|
| **FR** | `FRxxMZ`, 0.01000–280.00000 MHz | RF frequency in MHz | [4-3](FR.png) | **Covered (serializer)** — `NativeCommands.frequency_hz()`, used by `RFProfile` | Exact device stepping still pending HIL |
| **FR** | `FRxxKZ`, 10.00000–280000.00 kHz | RF frequency in kHz | [4-3](FR.png) | **Covered (serializer)** — `NativeCommands.frequency_khz()` | HIL pending; no high-level driver method |
| **AP / LE** | `APxxDM` or `LExxDM`, −133.0–19.0 | Level in dBm | [4-7](AP_LE.png) | **Covered (serializer)** — `NativeCommands.level_dbm()` | `LE` alias not emitted; HIL pending |
| **AP / LE** | `APxxDB` or `LExxDB`, −26.0–126.0 | Level in dBµV | [4-7](AP_LE.png) | **Covered (serializer)** — `NativeCommands.level_dbuv()`, used by `RFProfile` | `LE` alias not emitted; HIL pending |
| **AP / LE** | `APxxMV`/`LExxMV`, 0.000050–2000 | Level in mV | [4-7](AP_LE.png) | **Covered (serializer)** — `NativeCommands.level_mv()` | `LE` alias not emitted; HIL pending |
| **AP / LE** | `APxxUV`/`LExxUV`, 0.050–2000000 | Level in µV | [4-7](AP_LE.png) | **Covered (serializer)** — `NativeCommands.level_uv()` | `LE` alias not emitted; HIL pending |
| **AP / LE** | `APON`, `APOF` (likewise `LEON`, `LEOF` where applicable) | RF output ON/OFF | [4-7](AP_LE.png) | **Partial** — `APON`/`APOF` via `VP8122A.enable_output()`/`output_off()` | `LE` alternative not emitted; **RF electrical OFF not HIL-qualified** |
| **AP / LE** | `AP50`, `AP75` (50/75) | RF output impedance | [4-7](AP_LE.png) | **Partial** — AP builder, used by `RFProfile` | `LE` alternative absent; bench behavior pending |
| **EM** | `EMON` (`EM1`), `EMOF` (`EM0`) | EMF/open-end level display mode | [4-7](AP_LE.png) | **Missing** | Separate from RF ON/OFF |
| **CO** | `COON`, `COOF` | Continuous attenuation-control function ON/OFF, **not RF output OFF** | [4-9](CO.png) | **Covered (serializer)** — `NativeCommands.continuous_control()` | HIL pending; no high-level driver method |
| **CO** | `COUP`, `CODN` | Adjust continuous level by 0.1 dB | [4-9](CO.png) | **Covered (serializer)** — `NativeCommands.continuous_step()` | HIL pending; no high-level driver method |
| **CO** | `COxx`, 0.0–10.0 dB | Continuous output-level decrement | [4-9](CO.png) | **Covered (serializer)** — `NativeCommands.continuous_decrement_db()` | HIL pending; no high-level driver method |
| **AM** | `AMON`, `AMOF`; `AMT4`, `AMT1`, `AMXD` | AM enable and 400 Hz / 1 kHz / external source | [4-13](AM.png) | **Covered (serializer)** | Source/mode combinations not all in high-level `RFProfile` |
| **AM** | `AMxx`, 0.0–125% | AM depth | [4-13](AM.png) | **Partial, mismatch** | **Current code rejects 100.5–125%; manual allows up to 125%.** |
| **FM** | `FMON`, `FMOF`; `FMT4`, `FMT1`, `FMXD` | FM enable and 400 Hz / 1 kHz / external source | [4-25](FM.png) | **Covered (serializer)** | Source selection in high-level profile fixed to internal 1 kHz |
| **FM** | `FMxx`: 0.00–9.99 / 10.0–99.9 / 100–300 kHz | FM deviation, precision depends on band | [4-25](FM.png) | **Partial, mismatch** | **Current serializer upper limit 999 kHz exceeds documented 300 kHz.** |
| **MS** | `MS00`, `MS01`–`MS05`, `MS11`–`MS15`, `MS17` | Main/subchannel OFF, internal/external mono/stereo configurations | [4-16](MS.png) | **Covered (serializer)** | High-level `RFProfile` deliberately rejects unqualified stereo/modulation combinations |
| **MS / ratio** | `MSxxPC`, 0.0–127 | M+S level ratio, shown in TM0 status | [6-9](TM0_replay.png) | **Missing** | Listed in status-output map, not separately proved as input command here |
| **PL** | `PLON`, `PLOF` | Pilot enable/disable | [4-31](PL.png) | **Covered (serializer)** | High-level configuration not wired |
| **PL** | `PLxx(PC)`, 0.0–19.9% | Pilot level ratio; `PC` unit is optional | [4-31](PL.png) | **Partial** | Builder emits unitless code; explicit `PC` variant not supported |
| **FT** | `FTxx`: 0.00–9.99 / 10.0–99.9 / 100–402 kHz | Total FM deviation with three numeric precision bands | [4-34](FT.png) | **Partial, mismatch** | Uses 1 decimal across entire range, rejects legal 0.01-kHz increments below 10 and allows non-integer values above 100 |
| **PR** | `PR0`, `PR1`, `PR2`, `PR3` | Pre-emphasis OFF / 25 µs / 50 µs / 75 µs | [4-36](PR.png) | **Covered (serializer)** | No high-level setter; actual mode restrictions still apply |
| **SC** | `SCON` (`SC1`), `SCOF` (`SC0`) | SCA signal ON/OFF | [4-38](SC.png) | **Missing** | Table error 68 says not available in mono FM mode or AM band |
| **LV** | `LVxx`, 0–9990 mV | Composite output signal level | [4-40](LV.png) | **Covered (serializer)** | No high-level setter or physical qualification |
| **RC** | `RC00`–`RC99` | Recall preset memory slot | [4-42](RC_ST.png) | **Missing** | A recall may change RF state: needs explicit safety design |
| **ST** | `ST00`–`ST99` | Store preset memory slot | [4-42](RC_ST.png) | **Missing** | Nonvolatile mutation: explicit authorization and write policy needed |
| **TM** | `TM0`, `TM1`, `TM2` | Select setup-state, total-FM-deviation or port-2 talker output | [6-9](TM0.png) | **Partial** | `read_status()` performs a read, but **does not select TM mode**; TM1/TM2 parsing missing |
| **NP** | `NPON`, `NPOF` | Negative peak clipper | [6-9](TM0_replay_.png) | **Covered (serializer)** | Command meaning taken from status map and historical source; manual input table not in scanned pages |
| **DR** | `DRxx` (status reports −280 to +280) | Relay-drive reverse-frequency threshold | [6-9](TM0_replay_.png) | **Missing — status only** | Input grammar/units and safety not independently extracted |
| **AS** | `AS0`–`AS3` (status values) | Auto-sequence operation mode | [6-9](TM0_replay_.png) | **Missing — status only** | Write grammar not established by status description |
| **NT** | `NTxx` (0.10–60.0) | Auto-sequence interval time | [6-9](TM0_replay_.png) | **Missing — status only** | Exact precision/input semantics need manual cross-reference |
| **P1** | `P1xx` (0–255) | External control output, port 1 | [6-9](TM0_replay_.png) | **Missing — status only** | May actuate external equipment; risk assessment necessary |
| **P2** | `P2xx` (0–255) | External control output, port 2 | [6-9](TM0_replay_.png) | **Missing — status only** | May actuate external equipment; risk assessment necessary |

**Coverage counts by 22 header families:** 3 have all shown core encodings in the modern serializer (`PR`, `LV`, `NP`), 9 are partial or legacy-only (`FR`, `AP`, `CO`, `AM`, `FM`, `MS`, `PL`, `FT`, `TM`), and 10 are absent from the modern serializer (`LE`, `EM`, `SC`, `RC`, `ST`, `DR`, `AS`, `NT`, `P1`, `P2`). **None of the families has passed physical VP-8122A HIL qualification**. Status-only entries do not establish supported write syntax.

## IEEE-488 bus/control operations (not VP-8122A ASCII commands)

The scanned [`GTL.png`](GTL.png) lists the following general bus operations. The capabilities and applicability of particular operations must be judged using [`cmds.png`](cmds.png).

| IEEE-488 operation | Purpose | Driver handling / qualification |
|---|---|---|
| **GTL** | Addressed Go To Local | **Implemented** through `VP8122A.return_local()` → PyVISA GPIB `control_ren(address_gtl)`. **Not** sent as ASCII `"GTL"`. HIL pending. |
| **SDC** | Selected Device Clear | No public driver wrapper; bus-level operation, **not ASCII** |
| **DCL** | Universal Device Clear | No public wrapper; dangerous global bus operation; device advertises DC1 |
| **UNL** | Unlisten | Controller/GPIB operation; no dedicated public wrapper |
| **LLO** | Local Lockout | Controller/GPIB operation; no dedicated public wrapper |
| **SPE / SPD** | Serial Poll Enable / Disable | No dedicated wrapper; instrument advertises **SR0** (no service-request capability); do not claim SRQ support |
| **GET** | Group Execute Trigger | General addressed command listed, but **device reports DT0 (no device-trigger capability)**; do not mark as supported VP-8122A trigger |

The manual's status fields are **not automatically executable program commands**. Likewise, `*IDN?`, `*RST`, `SYST:ERR?`, and `OUTP:STAT` are conventional SCPI/IEEE-488.2 examples, **not established VP-8122A native commands**.

## Discrepancies and prioritized follow-up work

| Finding | Severity | Why it matters |
|---|---|---|
| AM depth upper bound **100 vs 125%** | P1 | `NativeCommands.am_depth` rejects the manual's upper 25% of valid range |
| FM deviation upper bound **999 vs 300 kHz** | **P0 safety/correctness** | `NativeCommands.fm_deviation_khz` can build illegal instrument requests |
| FT step/format **uniform 0.1** vs band-specific precision | P1 | Valid precision below 10 kHz rejected; fractional values above 100 kHz accepted |
| Missing **TM mode selection** | P1 | Readback meaning can depend on prior front-panel/previous-controller state |
| Missing `RC`, `ST`, `P1`, `P2` | P1/P2 | State-changing or external I/O commands require explicit authorization and HIL |
| Missing `SC`, `EM`, `LE`, `DR`, `AS`, `NT` | P2 | Feature/compatibility gaps; some known only from TM0 status fields |
| Missing `FR...KZ`, `AP...MV`, `AP...UV` | P2 | Documented alternative unit encodings not exposed |
| GPIB framing not verified | **P0 HIL gate** | Native grammar now described but backend EOI/terminator behavior not proven |
| `FM2.png` unavailable | Documentation gap | Does not count as reviewed; replace image or consult original manual |

**Release policy:** This is a code-coverage inventory, **not an HIL pass**. The prior [qualification checklist](../../docs/HIL_QUALIFICATION.md) remains mandatory. Follow-up implementation should use source-linked golden vectors and new version increments before changing serializers.

## Exact reference links

- [Repository scan directory](./).
- [Implementation: native serializer](../../panasonic_vp8122a/protocol.py).
- [Implementation: instrument session](../../panasonic_vp8122a/driver.py).
- [Implementation: historical compatibility builders](../../src/PANASONIC_VP_8122A.py).
- [Deep audit task](../../task/VP8122A_DEEP_REVIEW_2026-10-24.md).

**Source limits:** These pages are excerpts from an original manual, not the entire bound manual; a claim of *all possible* VP-8122A commands would require a full-page-by-page review of the complete VP-8122A operating manual. The table exhausts the header families directly identifiable in the available readable command and TM0 status images, not all conceivable firmware/program commands.
