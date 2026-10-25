# VP-8122A Deep-Review Remediation Status — v0.2.5

**Current integration:** Software migration merged to `main` at `808a4dfba4242f8016b3bf4cbbf783eeafddd2f9` (functional v0.2.4). **This v0.2.5 revision updates documentation only.**

Current project overview: [PROJECT_STATUS.md](PROJECT_STATUS.md). Original audit: [deep review task](../task/VP8122A_DEEP_REVIEW_2026-10-24.md). Core migration review: [CORE_MIGRATION_REVIEW.md](CORE_MIGRATION_REVIEW.md).

| Review findings | Current disposition | Unclosed evidence |
|---|---|---|
| R-01 unsupported default `*IDN?` | **Fixed**: native-only byte client, no default SCPI health probes | Physical talker behavior HIL |
| R-02–R-03 broken example and variable scope | **Fixed in software** | Hardware read-only smoke |
| R-04 ASCII GTL | **Fixed in core dev12**: opt-in addressed GTL bus API | Real multi-instrument REN/GTL verification |
| R-05 swallowed query errors | **Fixed**: typed/bounded transport faults | Physical timeout injection |
| R-06 RF profile safety | **Software safeguards implemented**: OFF-first, explicit authorized ON, UNKNOWN on faults | **P0 independent RF OFF measurement** |
| R-07–R-09 command delimiters/talker read | **Implemented offline**: 7-bit native ASCII, 255 bytes, EOI/LF/CRLF, TM mode and bounded reads | **P0 real adapter EOI / response frame qualification** |
| R-10–R-11 numeric validation | **Fixed** strict finite numeric/Decimal rules | Manual and physical data-point golden verification |
| R-12–R-13 limits, resolution, impedance | **Partially validated against scans**, AM 125%, FM max 300 kHz, FT 3 bands corrected | Frequency bands, 50/75 Ω effects and RF measured limits |
| R-14 cross-mode combinations | **Safe defaults** reject some unqualified combinations | Device-accurate FM/RF/stereo/pilot rule set |
| R-15 explicit resource | **Fixed** | Actual controller compatibility |
| R-16 synchronization | **Fixed in software** using core locks/atomic operations | Real backend stress where necessary |
| R-17 native status reporting | **Fixed offline** with ordered status and raw bytes | Full 25-field TM0, TM1/TM2 typed grammar and hardware |
| R-18 packaging | **Implemented** root package and core dependency | Verify fresh install for release |
| R-19 regression/CI | **Implemented and passing on PR heads** (Python 3.10–3.13) | Full main coverage artifact, separately gated HIL |
| R-20–R-22 obsolete notes/examples | **Modernized where applicable**; legacy bridge retained | Review compatibility before final stable release |

## Active tracking

- [Issue #5](https://github.com/ami3go/Panasonic_vp-8122a/issues/5) **OPEN**: physical GPIB/RF output qualification and safety evidence, mandatory before unattended use.
- [Issue #6](https://github.com/ami3go/Panasonic_vp-8122a/issues/6) **OPEN**: numeric corrections are implemented in merged v0.2.4; do **not** close until remaining cross-field validation and associated acceptance/evidence are reconciled.
- [PR #7](https://github.com/ami3go/Panasonic_vp-8122a/pull/7) **OPEN** and overlaps the now-merged command reference. Compare unique contributions and then close/rebase appropriately; do not attempt a conflict merge.
- Command matrix remains **6 encoded / 6 partial / 10 missing** among 22 documented native header families, with **zero hardware-qualified**.
- The scanned `FM2.png` source remains unreadable from the GitHub content API and may contain additional material.

**Disposition:** Software core migration is merged, but the project remains **NOT HIL-QUALIFIED**. The driver cannot be called fully repaired or certified for unattended RF operation until the physical evidence gates pass.
