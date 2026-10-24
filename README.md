# Panasonic VP-8122A — native GPIB RF generator driver

Version **0.2.1**: offline-tested driver-hardening candidate. **NOT HIL-QUALIFIED**.

The VP-8122A uses legacy GP-IB native program words, **not standard SCPI**. The driver does not send `*IDN?` on connection. It uses compact command candidates consistent with historic messages (`FR...MZ`, `AP...DB`, `APOF`), but command acceptance and RF output safety require an actual VP-8122A and supported GPIB adapter to verify.

## Installation

`python -m pip install -e '.[test]'` (Python 3.10+, a VISA backend such as NI-VISA and a GPIB controller also required for live hardware). There is no `src/` packaging layout; the package is `panasonic_vp8122a/` at the root.

## Example (RF remains off)

```python
from panasonic_vp8122a import RFProfile, VP8122A

with VP8122A('GPIB0::2::INSTR') as rf:
    rf.configure(RFProfile(frequency_hz=531_000, level_dbuv=20.0, am_depth_percent=30))
    # RF output is NOT enabled. OFF remains UNCONFIRMED without hardware readback.
```

Enabling RF requires a *separate explicit call* to `rf.enable_output(authorized=True)` after `configure`; use only with properly terminated and rated RF connections. Resource name is **never auto-selected**. `read_status()` reads directly in talker mode rather than doing an undocumented write/query. `return_local()` sends a bus-level GPIB GTL operation via VISA, not a text command.

## Safety and known limits

* **Hardware qualification blocked.** No real VP-8122A or USB-GPIB controller was available for this implementation. Native command delimiters, accepted precision, EOI, response framing, state readback, and actual RF OFF behavior have not been proven. A successful VISA `write()` does not guarantee safe output.
* Strict validation rejects non-finite/out-of-range/unsupported values without silently clamping them. Driver assumes provisional limits adapted from historical source; cross-mode combinations without qualified behavior are rejected.
* `configure()` sends an OFF candidate first, validates the entire profile before I/O, and attempts OFF again after failures. A failed OFF attempt leaves `UNKNOWN` state. Automatic retries of state-changing commands are forbidden.
* `close()` attempts RF OFF and closes instrument resources; on failure it raises an error and reports `DISCONNECTED_RF_UNKNOWN`. When caller owns the ResourceManager, it is not closed.
* PyVISA write/read termination is configurable, defaults to no appended write termination, and **must be qualified on the actual GPIB backend**. The historical 250 ms pacing is provisional and configurable.

## Verification

`python -m pytest -q` runs deterministic transport mocks and serialization/safety checks **without instruments**. Run physical qualification separately with the checklist in [docs/HIL_QUALIFICATION.md](docs/HIL_QUALIFICATION.md).

Original review: [review and 22 findings](task/VP8122A_DEEP_REVIEW_2026-10-24.md). Implemented changes and deferred evidence are tracked in [docs/REMEDIATION_STATUS.md](docs/REMEDIATION_STATUS.md).
