# VP-8122A deep-review remediation status — v0.2.0

Target: `task/VP8122A_DEEP_REVIEW_2026-10-24.md` (reviewed baseline `0bc943e`).

| Findings | Fix status | Remaining verification |
|---|---|---|
| R-01 mandatory `*IDN?` | Code fixed: removed from connect | Verify actual talker/status mode in HIL |
| R-02/R-03 broken examples | Code fixed in new example | Fresh VISA bench smoke |
| R-04 GTL treated as ASCII | Code fixed with `control_ren(address_gtl)` | Confirm with exact adapter |
| R-05 swallowed exception | Code fixed: typed error; no blind retries | Inject hardware timeout |
| R-06 RF output transaction | Code fixed: OFF first, authorized ON, failure OFF attempt, uncertain state | Physical OFF verification needed |
| R-07/R-08 program grammar/EOI | Compact native serializer & configurable termination added | **NOT QUALIFIED** until manual/HIL byte traces |
| R-09 read as talker | Read method independent of write | **NOT QUALIFIED** actual talker output |
| R-10/R-11 validation | Code fixed with strict Decimal validation | Exact model resolution needs confirmation |
| R-12/R-13 range/resolution | Preliminary limits and 10-Hz encodability enforced | **NOT QUALIFIED** frequency bands/level/impedance |
| R-14 cross-mode combinations | Unsupported AM+FM, stereo+modulation fail before I/O | Exact permitted combinations manual/HIL |
| R-15 explicit VISA address | Code fixed (no fuzzy auto-open) | USB adapter path smoke |
| R-16 concurrency | RLock serializes commands & lifecycle | Stress with HIL backend |
| R-17 native talker raw/fields | Code fixed with preservation of raw status | Device-specific parser qualification |
| R-18 package | Root package & `pyproject.toml` added | Fresh install in CI |
| R-19 offline CI/tests | Mock/fault-injection tests and CI added | GitHub Actions and physical HIL not yet checked |
| R-20/R-21/R-22 stale material | Modern code/docs and corrected example | Historical module preserved separately until compatibility contract is resolved |

**Overall: software remediation candidate; hardware verification pending, NOT a qualified release.**
