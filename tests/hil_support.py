"""Fail-closed, readback-only physical HIL helpers for Panasonic native GPIB.

This file is testing infrastructure, not a mechanism for energizing RF.
It permits ONLY native TM0, TM1 and TM2 writes. Never call VP8122A.close():
that public method intentionally attempts the unqualified APOF mutation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
from typing import Mapping

from panasonic_vp8122a import NativeCommands, VP8122A, __version__
from panasonic_vp8122a.native import encode_program_word
from scpi_driver_core.transport import VisaTransport


AUTHORIZATION = "ISOLATED_RF_BENCH_APPROVED"
_TERMINATION = {"EOI": "", "LF": "\n", "CRLF": "\r\n"}
_ADDRESS = re.compile(r"GPIB\d*::(?:[0-9]|[12][0-9]|30)::INSTR\Z", re.I)
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")


class HILGateError(RuntimeError):
    """Bench setup or explicit authorization is not sufficient for hardware I/O."""


@dataclass(frozen=True)
class HILSettings:
    resource: str
    evidence_dir: Path
    run_id: str
    instrument_serial: str
    controller: str
    operator: str
    termination: str
    modes: tuple[int, ...]
    timeout_ms: int

    @classmethod
    def from_environment(cls, env: Mapping[str, str] | None = None) -> HILSettings:
        variables = os.environ if env is None else env
        if (variables.get("CI", "").lower() in ("true", "1", "yes")
                or variables.get("GITHUB_ACTIONS", "").lower() == "true"
                or variables.get("GITLAB_CI", "").lower() == "true"
                or variables.get("TF_BUILD", "").lower() == "true"
                or variables.get("BUILDKITE", "").lower() == "true"
                or bool(variables.get("JENKINS_URL"))):
            raise HILGateError("physical HIL is forbidden on CI runners")
        if variables.get("VP8122A_HIL_AUTHORIZED") != AUTHORIZATION:
            raise HILGateError("explicit isolated-bench HIL authorization is required")
        if variables.get("VP8122A_HIL_ALLOW_RF_ENABLE"):
            raise HILGateError("talker-only HIL must never authorize RF enable")
        resource = variables.get("VP8122A_HIL_RESOURCE", "")
        if not _ADDRESS.fullmatch(resource):
            raise HILGateError("an explicit GPIB primary-address ::INSTR VISA resource is required")
        evidence_text = variables.get("VP8122A_HIL_EVIDENCE_DIR", "")
        if not evidence_text:
            raise HILGateError("an existing evidence directory is required")
        evidence_dir = Path(evidence_text).expanduser()
        if not evidence_dir.is_dir():
            raise HILGateError("evidence directory must exist before opening hardware")
        run_id = variables.get("VP8122A_HIL_RUN_ID", "")
        if not _RUN_ID.fullmatch(run_id):
            raise HILGateError("HIL run ID must contain 1-64 safe filename characters")
        instrument_serial = variables.get("VP8122A_HIL_SERIAL", "").strip()
        controller = variables.get("VP8122A_HIL_CONTROLLER", "").strip()
        operator = variables.get("VP8122A_HIL_OPERATOR", "").strip()
        if any(not value or len(value) > 128 for value in (instrument_serial, controller, operator)):
            raise HILGateError("operator, VP-8122A serial and GPIB controller identity are required")
        termination_name = variables.get("VP8122A_HIL_TERMINATION", "")
        if termination_name not in _TERMINATION:
            raise HILGateError("select EOI, LF or CRLF explicitly; never auto-sweep delimiters")
        modes_text = variables.get("VP8122A_HIL_MODES", "0")
        try:
            modes = tuple(int(part) for part in modes_text.split(","))
        except ValueError as exc:
            raise HILGateError("native talker modes must be 0, 1, or 2") from exc
        if not modes or len(set(modes)) != len(modes) or any(mode not in (0, 1, 2) for mode in modes):
            raise HILGateError("native talker modes must be unique entries from 0,1,2")
        try:
            timeout_ms = int(variables.get("VP8122A_HIL_TIMEOUT_MS", "2000"))
        except ValueError as exc:
            raise HILGateError("invalid VISA timeout") from exc
        if not 100 <= timeout_ms <= 10000:
            raise HILGateError("VISA timeout must be between 100 and 10000 ms")
        return cls(
            resource=resource,
            evidence_dir=evidence_dir,
            run_id=run_id,
            instrument_serial=instrument_serial,
            controller=controller,
            operator=operator,
            termination=_TERMINATION[termination_name],
            modes=modes,
            timeout_ms=timeout_ms,
        )


class TalkerOnlyVisaTransport(VisaTransport):
    """Auditable allowlist guarding every write *before* it reaches VISA.

    Captured writes are **attempted host bytes**, not a hardware bus trace or
    physical acceptance confirmation. The test never calls any SCPI helper.
    """

    def __init__(
        self, resource: str, *, termination: str, timeout_s: float,
        allowed_modes: tuple[int, ...] = (0, 1, 2),
    ) -> None:
        if (not allowed_modes or len(set(allowed_modes)) != len(allowed_modes)
                or any(type(mode) is not int or mode not in (0, 1, 2)
                       for mode in allowed_modes)):
            raise HILGateError("invalid explicit talker-mode allowlist")
        super().__init__(resource, timeout_s=timeout_s)
        self.attempted_bytes: list[bytes] = []
        self._allowed = frozenset(
            encode_program_word(NativeCommands.talker_mode(mode), termination)
            for mode in allowed_modes
        )

    def write(
        self, data: bytes, *, timeout_s: float | None = None, operation_id: str | None = None
    ):
        if type(data) is not bytes or data not in self._allowed:
            raise HILGateError("blocked non-talker write before VISA transmission")
        self.attempted_bytes.append(data)
        return super().write(data, timeout_s=timeout_s, operation_id=operation_id)


def _write_evidence(settings: HILSettings, mode: int, evidence: dict) -> Path:
    # Unique atomic file creation: never overwrite a previous qualification run.
    name = (
        f"vp8122a_{settings.run_id}_tm{mode}_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{time.time_ns()}.json"
    )
    output = settings.evidence_dir / name
    with output.open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return output


def probe_talker_mode(settings: HILSettings, mode: int) -> tuple[dict, Path]:
    """Exercise public VP8122A native talker read with NO RF output mutation.

    The device may already be producing RF when the test starts. It neither
    changes nor claims to confirm physical RF output state. The only program
    word transmitted is the requested TM mode. All errors are re-raised after
    best-effort evidence collection and transport-resource cleanup.
    """
    if mode not in settings.modes:
        raise HILGateError("mode not authorized by this HIL run")
    transport = TalkerOnlyVisaTransport(
        settings.resource,
        termination=settings.termination,
        timeout_s=settings.timeout_ms / 1000,
        allowed_modes=settings.modes,
    )
    device = VP8122A(
        settings.resource,
        transport=transport,
        timeout_ms=settings.timeout_ms,
        write_termination=settings.termination,
        settle_seconds=0.25,
    )
    evidence: dict = {
        "schema_version": 1,
        "result": "NOT_EVALUATED",
        "qualification": "PROTOCOL_OBSERVATION_ONLY",
        "driver_version": __version__,
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "resource": settings.resource,
        "instrument_serial_operator_supplied": settings.instrument_serial,
        "controller_operator_supplied": settings.controller,
        "operator": settings.operator,
        "talker_mode": mode,
        "termination": next(key for key, val in _TERMINATION.items() if val == settings.termination),
        "requested_tx_hex": [],
        "raw_rx_hex": None,
        "ordered_tm0_fields": [],
        "eoi_verified_by_bus_analyzer": False,
        "rf_output_measured": False,
        "rf_off_confirmed": False,
        "native_family_coverage": {"TM": "OBSERVED", "ALL_OTHER_FAMILIES": "NOT_TESTED"},
    }
    problem: Exception | None = None
    try:
        device.connect()
        result = device.read_status(mode=mode)
        parsed = device.last_native_status
        if parsed is None or not result or parsed.raw != result.encode("ascii"):
            raise AssertionError("native status and raw evidence disagree")
        if mode == 0 and not parsed.fields:
            raise AssertionError("TM0 produced no parseable native fields")
        evidence["raw_rx_hex"] = parsed.raw.hex()
        evidence["ordered_tm0_fields"] = [
            {"index": field.index, "prefix": field.prefix, "value": field.value, "raw": field.raw}
            for field in parsed.fields
        ]
        evidence["result"] = "OBSERVED"
    except Exception as exc:
        problem = exc
        evidence["result"] = "INCONCLUSIVE"
        evidence["error_type"] = type(exc).__name__
        evidence["error_message"] = str(exc)
        if device.last_status is not None:
            evidence["raw_rx_hex"] = device.last_status.encode(
                "ascii", errors="backslashreplace"
            ).hex()
    finally:
        evidence["requested_tx_hex"] = [item.hex() for item in transport.attempted_bytes]
        try:
            # Intentional: VP8122A.close() would transmit unqualified APOF.
            # This read-only test must instead release JUST the core transport.
            transport.close()
        except Exception as exc:
            evidence["result"] = "INCONCLUSIVE"
            evidence["close_error"] = repr(exc)
            if problem is None:
                problem = exc
        if transport.attempted_bytes != [
            encode_program_word(NativeCommands.talker_mode(mode), settings.termination)
        ]:
            evidence["result"] = "INCONCLUSIVE"
            if problem is None:
                problem = AssertionError("native talker TX differed from golden vector")
        path = _write_evidence(settings, mode, evidence)
    if problem is not None:
        raise AssertionError(f"native HIL mode {mode} failed; evidence: {path}") from problem
    return evidence, path
