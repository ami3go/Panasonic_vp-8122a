# Panasonic VP-8122A v0.2.7 — Independent-style Software/HIL Safety Review

**Review date:** 2026-10-24  
**Target branch:** feat/v0.2.7-native-gpib-qualification-evidence  
**PR:** https://github.com/ami3go/Panasonic_vp-8122a/pull/12  
**Driver baseline:** main@843cbb9d9978277c402e7131073826622dcee0f9 (v0.2.6)  
**Core baseline:** main@1e03b6837f96f200dc28233490639f2f080e1791 (0.1.0.dev12)

> Scope is an **independent-style static review** of staged software changes. The reviewer has NO physical VP-8122A or independently captured RF/GPIB measurements. Review is not certification.

## Verification disposition

- 45 source-cited offline variant fixtures span the 22 currently documented native families. The 7 status-only/source-unverified variants contain no transmit vectors.
- Strict golden vectors are HOST bytes only. EOI is a GPIB bus signal, not an ASCII suffix and cannot be proven by the serializer.
- Physical runner remains TM0/TM1/TM2-only with per-selected-mode transport checks. No SCPI, APOF, APON, preset, RF configuration, external I/O or global bus mutations are permitted by that runner.
- Offline reporter preserves raw submitted records and ordered TM0 fields without reporting physical RF PASS from an OBSERVED response.
- External numeric measurement comparison uses conservative guard bands (absolute error plus expanded uncertainty <= tolerance), but is explicitly NOT a hardware pass without signed calibration and bench acceptance.
- Normal CI selects only non-hardware tests on Python 3.10, 3.11, 3.12 and 3.13; final GitHub check conclusion MUST be confirmed on actual PR head prior to software merge.

## Per-family matrix status (source-controlled)

| Family | Variants | Offline builder variants | Readback/status-only fixtures | Active RF/test permission | Physical HIL | Unmet acceptance |
|---|---:|---:|---:|---|---|---|
| FR | 2 | 1 | 0 | ACTIVE_RF_MEASURED | NOT_TESTED | Signed calibrated independent RF/frequency/modulation measurement and approved interlock |
| AP | 7 | 5 | 0 | ACTIVE_RF_MEASURED, DEDICATED_APPROVAL | NOT_TESTED | Signed calibrated independent RF/frequency/modulation measurement and approved interlock |
| LE | 6 | 0 | 0 | ACTIVE_RF_MEASURED, DEDICATED_APPROVAL | NOT_TESTED | Signed calibrated independent RF/frequency/modulation measurement and approved interlock |
| EM | 1 | 0 | 0 | ACTIVE_RF_MEASURED | NOT_TESTED | Signed calibrated independent RF/frequency/modulation measurement and approved interlock |
| CO | 4 | 0 | 0 | ACTIVE_RF_MEASURED | NOT_TESTED | Signed calibrated independent RF/frequency/modulation measurement and approved interlock |
| AM | 3 | 3 | 0 | ACTIVE_RF_MEASURED | NOT_TESTED | Signed calibrated independent RF/frequency/modulation measurement and approved interlock |
| FM | 3 | 3 | 0 | ACTIVE_RF_MEASURED | NOT_TESTED | Signed calibrated independent RF/frequency/modulation measurement and approved interlock |
| MS | 2 | 1 | 1 | ACTIVE_RF_MEASURED | NOT_TESTED | Signed calibrated independent RF/frequency/modulation measurement and approved interlock |
| PL | 2 | 2 | 0 | ACTIVE_RF_MEASURED | NOT_TESTED | Signed calibrated independent RF/frequency/modulation measurement and approved interlock |
| FT | 1 | 1 | 0 | ACTIVE_RF_MEASURED | NOT_TESTED | Signed calibrated independent RF/frequency/modulation measurement and approved interlock |
| PR | 1 | 1 | 0 | ACTIVE_RF_MEASURED | NOT_TESTED | Signed calibrated independent RF/frequency/modulation measurement and approved interlock |
| SC | 1 | 0 | 0 | ACTIVE_RF_MEASURED | NOT_TESTED | Signed calibrated independent RF/frequency/modulation measurement and approved interlock |
| LV | 1 | 1 | 0 | ACTIVE_RF_MEASURED | NOT_TESTED | Signed calibrated independent RF/frequency/modulation measurement and approved interlock |
| NP | 1 | 1 | 1 | SOURCE_UNVERIFIED | NOT_TESTED | Verify listener grammar, prevent external actuation |
| RC | 1 | 0 | 0 | DEDICATED_APPROVAL | NOT_TESTED | Isolated nonvolatile/state-change authorization |
| ST | 1 | 0 | 0 | DEDICATED_APPROVAL | NOT_TESTED | Isolated nonvolatile/state-change authorization |
| TM | 3 | 3 | 0 | TALKER_ONLY | NOT_TESTED | Actual TM0/1/2 reply, bus EOI capture and positional/adapter review |
| DR | 1 | 0 | 1 | SOURCE_UNVERIFIED | NOT_TESTED | Verify listener grammar, prevent external actuation |
| AS | 1 | 0 | 1 | SOURCE_UNVERIFIED | NOT_TESTED | Verify listener grammar, prevent external actuation |
| NT | 1 | 0 | 1 | SOURCE_UNVERIFIED | NOT_TESTED | Verify listener grammar, prevent external actuation |
| P1 | 1 | 0 | 1 | SOURCE_UNVERIFIED | NOT_TESTED | Verify listener grammar, prevent external actuation |
| P2 | 1 | 0 | 1 | SOURCE_UNVERIFIED | NOT_TESTED | Verify listener grammar, prevent external actuation |

## Findings and release gates

| Priority | Finding | Disposition |
|---|---|---|
| P0 | No independently measured RF OFF after APOF; APON effects unqualified | **RELEASE BLOCKER**: do not enable active test or unattended RF |
| P0 | No real GPIB EOI/termination or addressed GTL capture; bus analyzer unavailable | **RELEASE BLOCKER**: preserve host-only trace semantics |
| P0 | No verified interlock/load/attenuator + calibrated RF reference adapter for RF and modulation checks | **RELEASE BLOCKER**: active phases prohibited |
| P1 | Talker harness previously admitted any TM mode even if only one selected in HIL settings | FIXED: per-mode VISA allowlist and offline test |
| P1 | CI denial originally checked only the generic CI variable | FIXED: reject common GitHub/GitLab/Azure/Buildkite/Jenkins signals; local authorization still required |
| P1 | A runner failure/timeout could leave attempted physical tests labeled NOT_TESTED | FIXED: selected cases promoted to INCONCLUSIVE with hardware-state warning |
| P1 | Evidence could be mixed across run IDs when reprocessing folder | FIXED: CLI filters by explicit run ID |
| P1 | Exact TM0 25-field semantic mapping and TM1/TM2 decoding are not HIL-qualified | OPEN; raw ordered fields preserved, no claims of typed correctness |
| P1 | Calibration record identity, reference SCPI adapters and full uncertainty budgets are not implemented | OPEN; numeric helper alone never generates hardware PASS |
| P2 | FM2.png original scan unavailable and incomplete bound-manual inventory | OPEN; source-only statuses remain blocked |

## Review acceptance conditions

Software-only merge can be considered after all Python CI matrix jobs, package build and software test suite pass and this review is reconciled. Do not close hardware issue #5, claim certified RF OFF, allow output mutation through the talker HIL runner, or mark any source example as physically accepted. An approved signed plan and external actual bench evidence remain separate future tasks.

**Physical HIL qualification count: 0 / 22 families.**
