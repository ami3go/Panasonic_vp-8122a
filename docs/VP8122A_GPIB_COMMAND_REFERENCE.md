# Panasonic VP-8122A — Native GP-IB command reference

**Document status:** source-audited inventory, **not a hardware-qualified command manual**  
**Audit date:** 2026-10-24  
**Code baseline:** [`src/PANASONIC_VP_8122A.py`](../src/PANASONIC_VP_8122A.py) (repository v0.1.0 review baseline)  
**Coverage:** 21 instrument program-code families observed in the repository code/status sample or archival illustrations, plus IEEE-488 GTL (not a program code). This is *not* a declaration that every command in every VP-8122A firmware revision has been transcribed.

> **This instrument uses manufacturer-specific IEEE-488 (GP-IB) program codes, not SCPI.** Do **not** replace its codes with `SOUR:FREQ`, `OUTP`, `SYST:ERR?`, `*RST` or other SCPI spellings. `*IDN?` is attempted by the current driver but is **not established** as supported. Do not send any RF-affecting command without controlling the bench output state and independent verification.

## Evidence and interpretation

- **S1 — manufacturer document in the repo:** [`Doc/PANASONIC VP-8120A Specification & Operating.pdf`](../Doc/PANASONIC%20VP-8120A%20Specification%20%26%20Operating.pdf). The PDF includes sections describing the VP-8122A; Chapter 6 describes the program-code grammar and talker modes. This is a related-model-named file, so model/option-specific applicability still needs comparison with the exact VP-8122A manual.
- **S2 — scanned GP-IB command excerpts:** [`Doc/GPIB/`](../Doc/GPIB/). Files with labels corresponding to code families are linked from the table below. An image filename alone is **not** proof of a specific data range or spelling; inspect the image/manufacturer page before qualifying that detail.
- **S3 — actual Python source:** [`src/PANASONIC_VP_8122A.py`](../src/PANASONIC_VP_8122A.py); establishes **what the software emits**, not what the instrument accepts.
- **S4 — historical talker example:** a comment in that source contains `FR87.50000MZ AP0.0DB EMOF COON CO0.0 AP50 MS01 AM30.0 AMOF AMT1 FM40.0 FMON FMT1 MS100PC PR0 PL0.0 PLOF SCOF NPOF DR30 AS0 NT0.20 P1D0 P2D0`.
- **S5 — external user-reported command:** [NI VP-8122A discussion](https://forums.ni.com/t5/LabVIEW/LabVIEW-driver-for-Panasonic-singal-generator-VP8122A/td-p/227759), `FR1MZ,AP-20DM,FM2.5` (user report, not an instrument qualification).
- **S6 — exact-model manual archive:** [BAMA VP-8122A operation manual](https://bama.edebris.com/manuals/panasonic/vp8122/). An exact-model English manual is listed; completeness of this transcription has **not** been checked against every page in that manual.

**Evidence grades:** `MANUAL-EXAMPLE` = visually confirmed in S1, `SOURCE-EXAMPLE` = observed in S4 or S5, `BUILDER` = emitted by S3, `NAME-ONLY` = named in S2 or observable status but exact input grammar still to confirm. All are **HIL-UNVERIFIED** in this repository.

## Message syntax and bus behavior

The manufacturer material describes a program word as **header** (typically two uppercase letters), **data** (often digits or state token), and optional **unit code**. Illustrative manual program words are `FR1MZ`, `AP-20DM`, `FM2.5`, and `MS02`. The manual shows **spaces between complete program words**, e.g. `FR1MZ AP-20DM FM2.5` followed by CR/LF; the NI discussion gives a **comma-separated** variant. This does **not** establish that spaces *inside a word* are accepted. In contrast, the current `dig_param3` and `on_off` builders insert a space after the header (`FR 1MZ`, `AM ON`). Do not silently normalize this until the exact target/adapter is checked.

The manual's Chapter 6 describes talker modes set with `TM0`, `TM1`, `TM2`: mode 0 reports generator settings, mode 1 total FM deviation, mode 2 external port data. The manual describes 7-bit ASCII with EOI and LF on talker output; detailed write terminators and VISA adapter setup still require bench confirmation. The instrument should be assigned as a **GPIB talker** for an appropriate read, not necessarily sent a SCPI `?` query.

**GTL is not an ASCII instrument program word.** `GTL` (Go To Local) is an addressed IEEE-488 **bus interface command**. The existing `disconnect()` calls `send("GTL")`, which incorrectly treats it as ASCII device data. Correct execution requires a controller/backend-supported bus operation; normal resource cleanup must be separate.

## Command-family inventory and current wire-format risk

`<n>` = numeric argument; `xx` = documented data field not yet fully transcribed. Examples in the **Observed/candidate** column are **not safe validated writes**. Refer to the evidence grade and the unresolved grammar before use. No SCPI query forms are inferred.

| Family | Meaning / observed forms | Evidence | Current Python coverage | Reference |
|---|---|---|---|---|
| `FR` | RF frequency: `FR1MZ`, `FR87.50000MZ`; `MZ` MHz / `KZ` kHz | MANUAL-EXAMPLE, SOURCE-EXAMPLE, BUILDER | `freq.MHz.val`, `freq.kHz.val`; **spaced word**, generic float/clamp | [FR](../Doc/GPIB/FR.png) |
| `AP` | RF level: `AP-20DM` (dBm), `AP20.0DB` (dBµV), `MV`/`UV` candidates; impedance `AP50`/`AP75`; `APON`/`APOF` from builder only | MANUAL-EXAMPLE, SOURCE-EXAMPLE, BUILDER | dBm/dBµV/mV/µV, `50`/`75`, ON/OFF; **spaced word**, limits unqualified | [AP/LE](../Doc/GPIB/AP_LE.png) |
| `CO` | Continuous level/control output: `COON`, `COOF`, `CO0.0` observed; `COUP`, `CODN` generated candidates | SOURCE-EXAMPLE, BUILDER | ON/OFF, up/down, numeric `0–10`; **not proven to be RF-output enable** | [CO](../Doc/GPIB/CO.png) |
| `AM` | AM depth and control: `AM30.0`, `AMON`, `AMOF`, `AMT1`; `AMT4`, `AMXD` builder candidates | SOURCE-EXAMPLE, BUILDER | numeric `0–125`, ON/OFF, 1 kHz/400 Hz/external; range unqualified | [AM](../Doc/GPIB/AM.png) |
| `FM` | FM deviation and control: `FM40.0`, `FMON`, `FMT1`; `FMOF`, `FMT4`, `FMXD` builder candidates | SOURCE-EXAMPLE, BUILDER | numeric `0–300`, ON/OFF, 1 kHz/400 Hz/external; range/units unqualified | [FM](../Doc/GPIB/FM.png), [FM2](../Doc/GPIB/FM2.png) |
| `MS` | Stereo/main-sub source selection: `MS00`–`MS05`, `MS11`–`MS15`, `MS17`; status additionally contains `MS100PC` (not implemented) | SOURCE-EXAMPLE, BUILDER | twelve fixed mode methods; **missing observed extra mode/value form** | [MS](../Doc/GPIB/MS.png) |
| `PL` | Pilot on/off and level: `PL0.0`, `PLOF`, candidate `PLON`, `PL<n>` | SOURCE-EXAMPLE, BUILDER | ON/OFF and numeric `0–19.9`; unqualified resolution | [PL](../Doc/GPIB/PL.png) |
| `FT` | Total FM deviation: `FT<n>` | BUILDER, NAME-ONLY | numeric `0–402`; parameters not hardware validated | [FT](../Doc/GPIB/FT.png) |
| `LV` | Composite output level: `LV<n>` | BUILDER, NAME-ONLY | numeric `0–9990`; scale/resolution not hardware validated | [LV](../Doc/GPIB/LV.png) |
| `PR` | Pre-emphasis: `PR0` off, `PR1` 25 µs, `PR2` 50 µs, `PR3` 75 µs | MANUAL-EXAMPLE, SOURCE-EXAMPLE, BUILDER | four modes via dedicated methods; **spaced word** | [PR](../Doc/GPIB/PR.png) |
| `NP` | Negative peak clipper: `NPOF`, candidate `NPON` | SOURCE-EXAMPLE, BUILDER | ON/OFF | Source status sample |
| `SC` | SCA signal/control: `SCOF` observed; other states/data require manual verification | SOURCE-EXAMPLE, NAME-ONLY | **Not implemented** | [SC](../Doc/GPIB/SC.png) |
| `RC` | Preset memory recall: `RC...` family | NAME-ONLY | **Not implemented** | [RC/ST](../Doc/GPIB/RC_ST.png) |
| `ST` | Preset memory storage: `ST...` family | NAME-ONLY | **Not implemented** | [RC/ST](../Doc/GPIB/RC_ST.png) |
| `TM` | GP-IB talker mode: `TM0`, `TM1`, `TM2` (documented in related-model-named manual) | MANUAL-EXAMPLE | **Not implemented**; a generic `query()` is **not** a substitute | [TM0](../Doc/GPIB/TM0.png) |
| `EM` | `EMOF` occurs in recorded status; exact semantic alternatives untranscribed | SOURCE-EXAMPLE | **Not implemented** | Source status sample |
| `DR` | Relay-drive/reverse frequency: `DR30` observed; related-model manual shows `DR<n>[MZ]` and negative variants | SOURCE-EXAMPLE, MANUAL-EXAMPLE | **Not implemented** | Related manual §7-11, Table 7-6 |
| `AS` | `AS0` occurs in recorded status; exact parameter meaning unconfirmed | SOURCE-EXAMPLE | **Not implemented** | Source status sample |
| `NT` | `NT0.20` occurs in recorded status; exact parameter meaning unconfirmed | SOURCE-EXAMPLE | **Not implemented** | Source status sample |
| `P1` | `P1D0` occurs in recorded status; external control port 1 family candidate | SOURCE-EXAMPLE | **Not implemented** | Source status sample |
| `P2` | `P2D0` occurs in recorded status; external control port 2 family candidate | SOURCE-EXAMPLE | **Not implemented** | Source status sample |
| **GTL** | IEEE-488 addressed **interface** command — **not an ASCII program code** | MANUAL-EXAMPLE (IEEE-488 overview) | **Incorrectly** sent as ASCII in `disconnect()` | Related manual §5-4 |

### Complete `MS` mode map implemented by the existing builder

| Generated word (without builder's inserted space) | Current method | Driver interpretation |
|---|---|---|
| `MS00` | `main_and_sub_ch.OFF()` | Off |
| `MS01` | `MONO_INT()` | Internal mono |
| `MS02` | `L_eq_R_INT()` | Internal L = R |
| `MS03` | `L_INT()` | Internal L |
| `MS04` | `R_INT()` | Internal R |
| `MS05` | `L_eq_minusR_INT()` | Internal L = −R |
| `MS11` | `MONO_EXT()` | External mono |
| `MS12` | `L_eq_R_EXT()` | External L = R |
| `MS13` | `L_EXT()` | External L |
| `MS14` | `R_EXT()` | External R |
| `MS15` | `L_eq_minusR_EXT()` | External L = −R |
| `MS17` | `L_R_EXT()` | External independent L/R |

**Note:** Table reflects **current Python method names and values**, not a claim that every mode has been physically accepted. The `MS100PC` status element has no corresponding builder method; its meaning is not inferred.

## Actual current builder outputs vs published forms

| Operation | Current string (S3) | Manual/example spelling | Disposition |
|---|---|---|---|
| 1 MHz | `FR 1MZ` | `FR1MZ` | **Mismatch; not hardware tested** |
| −20 dBm | `AP -20DM` | `AP-20DM` | **Mismatch; not hardware tested** |
| AM on | `AM ON` | `AMON` in source status pattern | **Mismatch; not hardware tested** |
| Pre-emphasis 50 µs | `PR 2` | `PR2` | **Mismatch; not hardware tested** |
| Internal L = R | `MS 02` | `MS02` | **Mismatch; not hardware tested** |
| Return local | ASCII `GTL` | GPIB addressed bus GTL | **Incorrect operation type** |

The builder returns strings; transport `com_interface.send()` can issue them through PyVISA. **No automated golden-wire tests and no physical VP-8122A compatibility qualification exist in the audited baseline.** Connection currently attempts `*IDN?`, with likely legacy incompatibility, so a builder method existing does not imply a working end-to-end feature.

## Unresolved for an *exhaustive* command reference

1. Compare every archived [`Doc/GPIB`](../Doc/GPIB/) image and exact-model operation manual code-list/appendix; transcribe all codes, values, unit suffixes, resolution, context constraints, model options and page numbers. The current inventory is **traceable but not proven exhaustive**.
2. Record all available talker modes, output framing and error/status response examples, including differences between `TM0` and an explicit write/read query.
3. Establish exact accepted program delimiters (`CR/LF`, `LF`, EOI, commas, spaces) and prohibit unvalidated intra-word spaces.
4. Prove what actually turns **RF output OFF**, including `APOF` vs `COOF` semantics, with independent RF measurements. Do not assume a software `send()` is physical confirmation.
5. Distinguish RF level units, numerical limits and impedance/option-dependent ranges; validate 140 MHz region boundaries and invalid-input handling.
6. Build an automated inventory-vs-builder test and an optional, separately authorized HIL qualification table. No automatic RF-on HIL during discovery or documentation verification.

For the actionable coverage and prioritization view, see [COMMAND_COVERAGE.md](COMMAND_COVERAGE.md).