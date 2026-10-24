"""Explicit, serialized GPIB transport and RF output lifecycle for VP-8122A."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable
import logging
import re
import time

from .protocol import NativeCommands, ProtocolValueError

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
    """Native GPIB driver; never energizes RF on connect or configure.

    No SCPI *IDN? probe. State names ending UNCONFIRMED are software estimates,
    *not* instrument readback. Use external RF measurement before trusting OFF.
    """
    def __init__(self, resource_name: str, *, resource_manager: Any = None,
                 manager_factory: Callable[[], Any] | None = None,
                 timeout_ms: int = 2000, settle_seconds: float = 0.25,
                 write_termination: str = '', read_termination: str | None = None,
                 clock: Callable[[float], None] = time.sleep):
        if not isinstance(resource_name, str) or not resource_name.strip():
            raise ValueError('explicit VISA resource_name required')
        if type(timeout_ms) is not int or not 100 <= timeout_ms <= 120000:
            raise ValueError('timeout_ms out of range')
        if isinstance(settle_seconds, bool) or not isinstance(settle_seconds, (int, float)) or not 0 <= settle_seconds <= 60:
            raise ValueError('settle_seconds out of range')
        if write_termination not in ('', '\n', '\r', '\r\n'):
            raise ValueError('unvalidated write termination')
        if read_termination not in (None, '\n', '\r', '\r\n'):
            raise ValueError('unvalidated read termination')
        self.resource_name, self.timeout_ms = resource_name, timeout_ms
        self.settle_seconds, self.write_termination = float(settle_seconds), write_termination
        self.read_termination, self._sleep = read_termination, clock
        self._rm = resource_manager
        self._owns_rm = False
        self._factory = manager_factory
        self._inst: Any = None
        self._lock = RLock()
        self.state = 'DISCONNECTED'
        self.last_status: str | None = None

    @property
    def connected(self) -> bool:
        return self._inst is not None

    def connect(self) -> 'VP8122A':
        with self._lock:
            if self.connected:
                return self
            if self._rm is None:
                if self._factory is None:
                    try:
                        import pyvisa
                    except ImportError as exc:
                        raise DriverError('Install pyvisa and an appropriate VISA backend') from exc
                    self._factory = pyvisa.ResourceManager
                self._rm = self._factory()
                self._owns_rm = True
            inst = None
            try:
                inst = self._rm.open_resource(self.resource_name)
                inst.timeout = self.timeout_ms
                inst.write_termination = self.write_termination
                if self.read_termination is not None:
                    inst.read_termination = self.read_termination
                self._inst = inst
                self.state = 'CONNECTED_UNKNOWN'
            except Exception as exc:
                if inst is not None:
                    try:
                        inst.close()
                    except Exception:
                        log.exception('Error closing partially opened instrument')
                if self._owns_rm:
                    try:
                        self._rm.close()
                    except Exception:
                        log.exception('Error closing resource manager')
                    self._rm = None
                    self._owns_rm = False
                raise TransportError(f'Unable to open {self.resource_name}') from exc
            return self

    def _require_connected(self) -> Any:
        if not self.connected:
            raise NotConnected('Instrument not connected')
        return self._inst

    def _write(self, cmd: str) -> None:
        inst = self._require_connected()
        if not isinstance(cmd, str) or not re.fullmatch(r'[A-Z0-9.+-]+', cmd):
            raise ProtocolValueError('not a single compact program word')
        try:
            inst.write(cmd)
            log.debug('VP-8122A program word %s', cmd)
            if self.settle_seconds:
                self._sleep(self.settle_seconds)
        except Exception as exc:
            self.state = 'UNKNOWN'
            raise TransportError(f'GPIB write failed: {cmd[:2]}') from exc

    def output_off(self) -> None:
        with self._lock:
            self._require_connected()
            try:
                self._write(NativeCommands.output(False))
                self.state = 'OFF_UNCONFIRMED'
            except Exception as exc:
                self.state = 'UNKNOWN'
                raise UnsafeStateError('RF OFF could not be confirmed; treat output as UNKNOWN') from exc

    def configure(self, profile: RFProfile) -> tuple[str, ...]:
        if not isinstance(profile, RFProfile):
            raise TypeError('profile must be RFProfile')
        commands = profile.commands()  # pure preflight, NO I/O yet
        with self._lock:
            self._require_connected()
            try:
                self.output_off()
                for command in commands:
                    self._write(command)
                self.state = 'CONFIGURED_OFF_UNCONFIRMED'
            except Exception as exc:
                try:
                    self.output_off()
                except UnsafeStateError:
                    self.state = 'UNKNOWN'
                raise UnsafeStateError('RF configuration failed; OFF not independently confirmed') from exc
        return commands

    def enable_output(self, *, authorized: bool = False) -> None:
        if authorized is not True:
            raise PermissionError('Explicit authorized=True required to enable RF')
        with self._lock:
            if self.state != 'CONFIGURED_OFF_UNCONFIRMED':
                raise UnsafeStateError('Configure a validated profile before enabling RF')
            try:
                self._write(NativeCommands.output(True))
                self.state = 'RF_ON_UNCONFIRMED'
            except Exception as exc:
                try:
                    self.output_off()
                except UnsafeStateError:
                    self.state = 'UNKNOWN'
                raise UnsafeStateError('RF enable failed; output status uncertain') from exc

    def read_status(self) -> str:
        """Read directly as a GPIB talker, without injecting *IDN? or '?' write."""
        with self._lock:
            inst = self._require_connected()
            try:
                raw = inst.read()
            except Exception as exc:
                raise TransportError('GPIB talker read failed; no automatic retry') from exc
            if not isinstance(raw, str) or not raw.strip():
                raise TransportError('Empty/malformed GPIB talker status')
            self.last_status = raw
            return raw

    def status_fields(self) -> dict[str, str]:
        """Parse recognized 2-letter prefixes; keep raw status for diagnostics."""
        raw = self.read_status()
        fields: dict[str, str] = {}
        for token in raw.strip().split():
            m = re.fullmatch(r'([A-Z]{2})(.+)', token)
            if m:
                fields[m.group(1)] = m.group(2)
        if not fields:
            raise TransportError(f'Unrecognized native talker response: {raw!r}')
        return fields

    def return_local(self) -> None:
        """GTL is a GPIB interface operation, NOT the text string 'GTL'."""
        with self._lock:
            inst = self._require_connected()
            if not hasattr(inst, 'control_ren'):
                raise UnsupportedOperation('VISA adapter does not implement GPIB control_ren')
            try:
                from pyvisa.constants import RENLineOperation
            except ImportError as exc:
                raise UnsupportedOperation('pyvisa required for GTL') from exc
            try:
                inst.control_ren(RENLineOperation.address_gtl)
            except Exception as exc:
                raise TransportError('GPIB return-to-local failed') from exc

    def close(self, *, return_local: bool = False) -> None:
        with self._lock:
            failure: Exception | None = None
            if self.connected:
                try:
                    self.output_off()
                except Exception as exc:
                    failure = exc
                try:
                    if return_local:
                        self.return_local()
                except Exception as exc:
                    failure = failure or exc
                try:
                    self._inst.close()
                except Exception as exc:
                    failure = failure or exc
                finally:
                    self._inst = None
            if self._owns_rm and self._rm is not None:
                try:
                    self._rm.close()
                except Exception as exc:
                    failure = failure or exc
                finally:
                    self._rm = None
                    self._owns_rm = False
            self.state = 'DISCONNECTED' if failure is None else 'DISCONNECTED_RF_UNKNOWN'
            if failure is not None:
                raise UnsafeStateError('Close finished with unresolved output/bus error') from failure

    def __enter__(self) -> 'VP8122A':
        return self.connect()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        try:
            self.close()
        except Exception:
            if exc is None:
                raise
            log.exception('Additional failure during VP-8122A cleanup')
        return False

    @staticmethod
    def available_resources(manager: Any) -> tuple[str, ...]:
        return tuple(manager.list_resources())
