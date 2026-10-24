# Panasonic VP-8122A — GPIB Python driver

Python/PyVISA prototype for the Panasonic VP-8122A AM/FM RF signal generator.

**Repository version:** 0.1.0 (documentation and review baseline; **not** a hardware-qualified driver release).

**Review and remediation plan:** [VP8122A deep driver review — 2026-10-24](task/VP8122A_DEEP_REVIEW_2026-10-24.md).

> **Safety / interoperability:** This code has known connection, GPIB command, resource-management and RF-safety issues. Do not use for unattended RF testing until the P0 findings are corrected and physical HIL tests pass. The VP-8122A uses legacy native GP-IB program codes; do not assume SCPI or `*IDN?` support.

Original note: 26.08.2021 — work in progress.
