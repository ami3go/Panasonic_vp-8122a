"""Explicit, serialized GPIB transport and RF output lifecycle for VP-8122A."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable
import logging
import math
import time

from .protocol import NativeCommands, ProtocolValueError
from .native import NativeStatus, encode_program_word, parse_status, MAX_TALKER_RESPONSE
from scpi_driver_core import ScpiClient
from scpi_driver_core.transport import VisaTransport, ReadMode, ReadRequest, TransportState

log = logging.getLogger(__name__)


class DriverError(RuntimeError):
    """Driver failure (do not treat as a successful instrument operation)."""


class NotConnected(DriverError):
    pass


class TransportError(DriverError):
    pass


class UnsafeStateError(DriverError):
    """RF may still be energized; output state must be externally confirmed."""


class UnsupportedOperation(DriverError):
    pass


@dataclass(frozen=True)
class RFProfile:
    frequency_hz: int
    level_dbuv: float
    impedance_ohm: int = 50
    am_depth_percent: float | None = None
    fm_deviation_khz: float | None = None
    stereo_mode: str = 'OFF'

    def commands(self) -> tuple[str, ...]:
        """Validate the WHOLE profile before any physical I/O."""
        c = NativeCommands
        if self.am_depth_percent is not None and self.fm_deviation_khz is not None:
            raise ProtocolValueError('simultaneous AM and FM requires model-specific qualification')
        if self.stereo_mode != 'OFF' and (self.am_depth_percent is not None or self.fm_deviation_khz is not None):
            raise ProtocolValueError('stereo with modulation requires model-specific qualification')
        parts = [c.frequency_hz(self.frequency_hz), c.impedance(self.impedance_ohm),
                 c.level_dbuv(self.level_dbuv), c.stereo(self.stereo_mode)]
        if self.am_depth_percent is not None:
            parts += [c.am_depth(self.am_depth_percent), c.modulation_source('AM', 'T1'), c.modulation_enabled('AM', True)]
        else:
            parts.append(c.modulation_enabled('AM', False))
        if self.fm_deviation_khz is not None:
            parts += [c.fm_deviation_khz(self.fm_deviation_khz), c.modulation_source('FM', 'T1'), c.modulation_enabled('FM', True)]
        else:
            parts.append(c.modulation_enabled('FM', False))
        return tuple(parts)


class VP8122A:
    """Panasonic native GPIB driver using scpi-driver-core byte-level I/O.

    All output states are software evidence, never RF power measurements.
    No SCPI probe, IEEE-488.2 identity, error queue or implicit reconnect.
    """

    def __init__(
        self,
        resource_name: str,
        *,
        resource_manager: Any = None,
        manager_factory: Callable[[], Any] | None = None,
        timeout_ms: int = 2000,
        settle_seconds: float = 0.25,
        write_termination: str = "",
        read_termination: str | None = None,
        clock: Callable[[float], None] = time.sleep,
        transport: Any = None,
        profile_timeout_s: float = 30.0,
    ) -> None:
        if not isinstance(resource_name, str) or not resource_name.strip():
            raise ValueError("explicit VISA resource_name required")
        if type(timeout_ms) is not int or not 100 <= timeout_ms <= 120000:
            raise ValueError("timeout_ms out of range")
        if isinstance(settle_seconds, bool) or not isinstance(settle_seconds, (int, float)) or not math.isfinite(settle_seconds) or not 0 <= settle_seconds <= 60:
            raise ValueError("settle_seconds out of range")
        if write_termination not in ("", "\n", "\r\n"):
            raise ValueError("native termination must be EOI, LF or CRLF")
        if read_termination not in (None, "\n", "\r", "\r\n"):
            raise ValueError("unvalidated read termination")
        if isinstance(profile_timeout_s, bool) or not isinstance(profile_timeout_s, (int, float)) or not math.isfinite(profile_timeout_s) or profile_timeout_s <= 0:
            raise ValueError("profile_timeout_s must be finite and positive")
        if transport is not None and (resource_manager is not None or manager_factory is not None):
            raise ValueError("injected transport cannot be combined with a resource manager")
        self.resource_name = resource_name
        self.timeout_ms = timeout_ms
        self.settle_seconds = float(settle_seconds)
        self.write_termination = write_termination
        self.read_termination = read_termination
        self._clock = clock
        self._manager_factory = manager_factory
        self._resource_manager = resource_manager
        self._transport = transport
        self._client: ScpiClient | None = None
        self._lock = RLock()
        self._profile_timeout_s = float(profile_timeout_s)
        self.state = "DISCONNECTED"
        self.last_status: str | None = None
        self.last_native_status: NativeStatus | None = None

    def _prepare_client(self) -> ScpiClient:
        if self._client is None:
            if self._transport is None:
                manager = self._resource_manager
                if manager is None and self._manager_factory is not None:
                    manager = self._manager_factory()
                self._transport = VisaTransport(
                    self.resource_name,
                    timeout_s=self.timeout_ms / 1000.0,
                    resource_manager=manager,
                )
            self._client = ScpiClient(
                self._transport,
                timeout_s=self.timeout_ms / 1000.0,
                minimum_interval_s=self.settle_seconds or None,
                sleep=self._clock,
            )
        return self._client

    @property
    def connected(self) -> bool:
        return self._transport is not None and self._transport.state is TransportState.OPEN

    @property
    def transport(self) -> Any:
        """Underlying generic byte transport, never a raw VISA resource."""
        return self._transport

    @property
    def client(self) -> ScpiClient | None:
        """Shared core execution client; does not issue SCPI probes."""
        return self._client

    def connect(self) -> 'VP8122A':
        with self._lock:
            if self.connected:
                return self
            try:
                self._prepare_client().transport.open()
            except Exception as exc:
                self.state = "DISCONNECTED_RF_UNKNOWN"
                raise TransportError(f"Unable to open {self.resource_name}") from exc
            # An opened VISA session does not establish the physical RF state.
            self.state = "CONNECTED_UNKNOWN"
            return self

    def _require_connected(self) -> ScpiClient:
        if not self.connected or self._client is None:
            raise NotConnected("Instrument not connected")
        return self._client

    def _write(self, cmd: str, *, timeout_s: float | None = None) -> None:
        """One native command only; never automatically retry a mutation."""
        data = encode_program_word(cmd, self.write_termination)
        client = self._require_connected()
        try:
            client.write_bytes(data, timeout_s=timeout_s)
            log.debug("VP-8122A program word %s", cmd[:2])
        except Exception as exc:
            self.state = "UNKNOWN"
            raise TransportError(f"GPIB write failed: {cmd[:2]}") from exc

    def output_off(self, *, timeout_s: float | None = None) -> None:
        with self._lock:
            self._require_connected()
            try:
                self._write(NativeCommands.output(False), timeout_s=timeout_s)
                self.state = "OFF_UNCONFIRMED"
            except Exception as exc:
                self.state = "UNKNOWN"
                raise UnsafeStateError("RF OFF was not physically confirmed") from exc

    def configure(self, profile: RFProfile) -> tuple[str, ...]:
        if not isinstance(profile, RFProfile):
            raise TypeError("profile must be RFProfile")
        commands = profile.commands()  # validate ALL setpoints before any I/O
        for command in commands:
            encode_program_word(command, self.write_termination)
        with self._lock:
            client = self._require_connected()
            # Enforce a single budget across the entire RF mutation sequence.
            deadline = time.monotonic() + self._profile_timeout_s

            def remaining() -> float:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise TimeoutError("RF profile operation deadline expired")
                return min(left, self.timeout_ms / 1000.0)

            with client.operation_lock():
                try:
                    self.output_off(timeout_s=remaining())
                    for command in commands:
                        self._write(command, timeout_s=remaining())
                    self.state = "CONFIGURED_OFF_UNCONFIRMED"
                except Exception as exc:
                    # Never reopen/fault-recover automatically merely to retry OFF.
                    if self.connected:
                        try:
                            self.output_off(timeout_s=remaining())
                        except Exception:
                            self.state = "UNKNOWN"
                    else:
                        self.state = "UNKNOWN"
                    raise UnsafeStateError(
                        "RF configuration failed; hardware OFF remains unconfirmed"
                    ) from exc
        return commands

    def enable_output(self, *, authorized: bool = False) -> None:
        if authorized is not True:
            raise PermissionError("Explicit authorized=True required to enable RF")
        with self._lock:
            if self.state != "CONFIGURED_OFF_UNCONFIRMED":
                raise UnsafeStateError("Configure a validated profile before enabling RF")
            try:
                self._write(NativeCommands.output(True))
                self.state = "RF_ON_UNCONFIRMED"
            except Exception as exc:
                self.state = "UNKNOWN"
                # The previous ON write may have succeeded before timeout.
                # Never blindly replay it, or claim a successful OFF.
                raise UnsafeStateError("RF enable failed; output state UNKNOWN") from exc

    def read_status(self, *, mode: int = 0) -> str:
        """Select native talker mode, then read one bounded END-delimited reply."""
        word = NativeCommands.talker_mode(mode)
        with self._lock:
            client = self._require_connected()
            with client.operation_lock():
                deadline = time.monotonic() + self.timeout_ms / 1000.0

                def left() -> float:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError("native talker read deadline expired")
                    return remaining

                try:
                    self._write(word, timeout_s=left())
                    raw = client.read_bytes(
                        ReadRequest(
                            mode=ReadMode.BACKEND_DEFINED_MESSAGE,
                            maximum_size=MAX_TALKER_RESPONSE,
                        ),
                        timeout_s=left(),
                    )
                    status = parse_status(raw, mode=mode)
                except Exception as exc:
                    self.last_native_status = None
                    raise TransportError("GPIB native talker status failed") from exc
                self.last_status = status.text
                self.last_native_status = status
                return status.text

    def status_fields(self) -> dict[str, str]:
        """Backward-compatible, intentionally lossy last-value-per-prefix view.

        Use last_native_status.fields for lossless ordered TM0 data.
        """
        self.read_status(mode=0)
        assert self.last_native_status is not None
        return {field.prefix: field.value for field in self.last_native_status.fields}

    def return_local(self) -> None:
        """Addressed IEEE-488 GTL; never send ASCII 'GTL'."""
        with self._lock:
            self._require_connected()
            addressed = getattr(self._transport, "go_to_local_addressed", None)
            if not callable(addressed):
                raise UnsupportedOperation("Transport lacks addressed IEEE-488 GTL capability")
            try:
                addressed()
            except Exception as exc:
                self.state = "UNKNOWN"
                raise TransportError("GPIB addressed GTL failed") from exc

    def close(self, *, return_local: bool = False) -> None:
        with self._lock:
            failure: Exception | None = None
            had_connection = self.connected
            if had_connection:
                try:
                    self.output_off()
                except Exception as exc:
                    failure = exc
                if return_local and self.connected:
                    try:
                        self.return_local()
                    except Exception as exc:
                        failure = failure or exc
            elif self.state in ("UNKNOWN", "RF_ON_UNCONFIRMED"):
                failure = UnsafeStateError("RF output unknown during faulted close")
            # Regardless of OFF/GTL errors, release the resource, never the
            # shared PyVISA ResourceManager used by other sessions.
            try:
                if self._transport is not None:
                    self._transport.close()
            except Exception as exc:
                failure = failure or exc
            finally:
                self.state = (
                    "DISCONNECTED_RF_UNKNOWN" if failure is not None
                    else "DISCONNECTED_OFF_UNCONFIRMED" if had_connection
                    else "DISCONNECTED"
                )
            if failure is not None:
                raise UnsafeStateError(
                    "Close completed with unresolved RF/bus state"
                ) from failure

    def __enter__(self) -> 'VP8122A':
        return self.connect()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        try:
            self.close()
        except Exception:
            if exc is None:
                raise
            log.exception("Additional failure during VP-8122A cleanup")
        return False

    @staticmethod
    def available_resources(manager: Any) -> tuple[str, ...]:
        """Explicit, opt-in resource listing; never auto-select a device."""
        return tuple(manager.list_resources())
