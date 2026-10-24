# VP-8122A Project Status — 2026-10-24

**Document version:** 0.2.5 (documentation-only update).  
**Runtime code baseline:** 0.2.4, `main@808a4dfba4242f8016b3bf4cbbf783eeafddd2f9`.  
**Core baseline:** `scpi-driver-core 0.1.0.dev12`, `main@1e03b6837f96f200dc28233490639f2f080e1791`.  
**Release classification:** **Software-integrated, NOT hardware/HIL-qualified, NOT cleared for unattended RF use.**

## Executive status

The native Panasonic VP-8122A driver has completed the *software* migration to the byte-level infrastructure of `scpi-driver-core`. The migration is merged on main via stacked driver PR #8 and consolidated PR #4. The prerequisite generic addressed IEEE-488 GTL capability is merged into the shared core via PR #12. The Panasonic protocol remains **native GP-IB**, not standard SCPI.

| Milestone | State | Evidence / limitation |
|---|---|---|
| Independent deep driver review | DONE | [Merged driver PR #3](https://github.com/ami3go/Panasonic_vp-8122a/pull/3) |
| Core infrastructure addressed GTL | MERGED | [Core PR #12](https://github.com/ami3go/scpi-driver-core/pull/12), `v0.1.0.dev12` |
| Native GPIB migration to core | MERGED | [Driver PR #8](https://github.com/ami3go/Panasonic_vp-8122a/pull/8) and [PR #4](https://github.com/ami3go/Panasonic_vp-8122a/pull/4) |
| Core VISA and byte execution | IMPLEMENTED | `VisaTransport` and `ScpiClient.write_bytes/read_bytes` |
| Native command / talker model | IMPLEMENTED, PARTIAL COVERAGE | 7-bit ASCII, 255-byte bound, EOI/LF/CRLF, native TM0/1/2 selection, ordered raw status |
| Numeric serializer limits (AM/FM/FT) | CODE FIXED | 125% AM, 300 kHz FM upper bound, piecewise FT precision; **hardware behavior not verified** |
| RF OFF-first/authorized-ON safeguards | SOFTWARE IMPLEMENTED | No automatic SCPI query, implicit RF ON, or blind mutation retry; physical OFF still unconfirmed |
| Offline Python regression and CI | PASS AT MERGED PR HEADS | Driver #8 and #4 GitHub Actions successful; core #12 successful. Default HIL tests excluded |
| Command coverage | INCOMPLETE | 22 documented header families: 3 encoded, 9 partial, 10 missing; 0 families physically qualified |
| Full physical GPIB + RF HIL | BLOCKED / NOT RUN | [Issue #5](https://github.com/ami3go/Panasonic_vp-8122a/issues/5) |
| Earlier AM/FM/FT issue cleanup | PARTIAL / ISSUE STILL OPEN | [Issue #6](https://github.com/ami3go/Panasonic_vp-8122a/issues/6): numerical portions fixed, cross-field/manual/HIL acceptance incomplete |
| Separate command-documentation PR | OPEN, NOT MERGED | [Driver PR #7](https://github.com/ami3go/Panasonic_vp-8122a/pull/7); superseded/overlapping content in current main; reconcile before closure |

## Verified tests and CI

- The PR #8 development head `e7e6e692c33db41b3e0b56b89595eb8785529d80` has a completed successful GitHub Actions workflow.
- Consolidated driver PR #4 head `06a7a47f9908da6f4d90fe1c2dd04fda1ad838ee` has a completed successful GitHub Actions workflow.
- Core PR #12 head `4b9fdf951dbe7dbcaa2b0141f5654a3678a401b1` has two completed successful GitHub Actions runs.
- The driver's CI workflow tests Python 3.10–3.13, runs offline pytest with coverage and builds a wheel.
- Test fixtures include `MockTransport`, native command golden vectors, Hypothesis coverage and PyVISA-sim; the `hardware` marker is excluded from default CI.
- The software migration review documents earlier statement coverage (88%, with later improvement indicated by PR notes). **A fresh exact coverage percentage for merged main is not established by this project-status read.** Obtain the CI coverage artifact before quoting a final figure.
- No actual VP-8122A bench, USB–GPIB adapter or RF reference measurement was connected during these checks; **HIL: NOT EXECUTED**.

## Current functional coverage

| Capability | Status | Follow-up |
|---|---|---|
| Explicit connection and clean transport closure | Implemented | Qualify selected VISA backend |
| Addressed GTL | Implemented in shared core | Verify on multi-instrument IEEE-488 bus |
| Compact Panasonic native output words | Implemented | Confirm wire/EOI/physical acceptance |
| TM0 ordered response / preservation of repeated prefixes | Implemented | Qualify actual 25-field status and TM1/TM2 responses |
| RF profile preflight and guarded enable | Implemented in software | Validate effective RF state electrically |
| Native program code families | 3 encoded / 9 partial / 10 missing | Prioritized additions with exact-manual golden vectors |
| Preset recall/store and external control | Not available in modern safe API | Needs authorization/interlock design |
| Unattended RF generation | **NOT PERMITTED / NOT QUALIFIED** | Explicit independently measured safety pass |

See [native command reference](../Doc/GPIB/COMMAND_REFERENCE.md), the [README feature coverage](../README.md), [migration review](CORE_MIGRATION_REVIEW.md), and [hardware qualification plan](HIL_QUALIFICATION.md).

## Outstanding work (prioritized)

| Priority | Task | Acceptance gate |
|---|---|---|
| **P0** | Confirm `APOF` actually disables RF output and `APON` enables it, with independent RF measurement | Prove OFF/ON with specified terminations, tolerance and fault injection, attach signed evidence |
| **P0** | Qualify native byte framing, EOI, LF/CRLF, TM0/talker response and bus-level GTL with actual GPIB adapter | Record byte-level captures and exact VISA/adapter/firmware versions |
| **P1** | Finish manual-specific AM/FM/stereo interlock and cross-field validation | No invalid combined setting transmitted; boundaries and acceptance goldens |
| **P1** | Qualify full TM0 positional status and typed TM1/TM2 grammar | Raw+typed parity, error handling, no loss of repeated fields |
| **P1** | Expand safely supported native commands | Tests and explicit permissions for recall/store, external I/O, and missing command variants |
| **P1** | Reconcile and disposition stale [PR #7](https://github.com/ami3go/Panasonic_vp-8122a/pull/7) and [issue #6](https://github.com/ami3go/Panasonic_vp-8122a/issues/6) | Preserve unique docs and remaining acceptance criteria; no blind closure |
| **P2** | Normalize version/report documentation and dependency publication strategy | Decide whether pinned Git SHA should transition to published core release once available |

### HIL release gate

Issue #5 remains open. Before RF hardware qualification, document exact instrument revision, operator authorization, GPIB resource/controller, independent RF measurement, test thresholds and safe physical abort. Exercise read-only reconnaissance first, then explicitly authorized RF verification. Do not interpret transport writes, a green mock suite or the `OFF_UNCONFIRMED` software state as proof that the signal generator is physically off.

**Status rule:** A software-integrated driver is not an RF-qualified instrument driver until the separate physical bench gates pass.


## HIL automation development v0.2.6 — 2026-10-24

- Added **software-tested** explicit authorization gates, native TM0/TM1/TM2 readback HIL harness and evidence support, with SCPI/RF mutation attempts blocked before VISA I/O.
- New documentation: [HIL automation runbook](HIL_AUTOMATION.md) and [full staged task](../task/VP8122A_AUTOMATED_NATIVE_GPIB_HIL_TASK.md).
- **Physical HIL remains NOT EXECUTED**. Actual EOI, TM status meaning and independently measured RF OFF are still release blockers. v0.2.5 was a documentation-only status update; v0.2.6 adds the HIL harness.
