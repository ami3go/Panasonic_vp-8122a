"""VP-8122A native GPIB program-message encoder.

Historical examples show compact program words (FR87.5MZ, AP20DB, APOF).
The exact firmware/adapter acceptance is NOT qualified without HIL.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Union

Number = Union[int, float, Decimal]


class ProtocolValueError(ValueError):
    """A setting is invalid before any instrument I/O."""


def number(value: Number, *, lower: str, upper: str, places: int, name: str) -> str:
    if isinstance(value, (bool, str, bytes)):
        raise ProtocolValueError(f"{name} must be a finite number")
    try:
        val = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ProtocolValueError(f"{name} must be a finite number") from exc
    if not val.is_finite():
        raise ProtocolValueError(f"{name} must be finite")
    if val < Decimal(lower) or val > Decimal(upper):
        raise ProtocolValueError(f"{name} outside [{lower}, {upper}]: {value}")
    quantum = Decimal(1).scaleb(-places)
    if val != val.quantize(quantum):
        raise ProtocolValueError(f"{name} resolution exceeds {places} decimal places")
    return format(val, 'f')


class NativeCommands:
    """Compact native GP-IB serializer; all limits provisional until HIL."""

    @staticmethod
    def frequency_hz(hz: int) -> str:
        if isinstance(hz, bool) or not isinstance(hz, int):
            raise ProtocolValueError('frequency_hz must be an integer')
        if not 10_000 <= hz <= 280_000_000 or hz % (20 if hz > 140_000_000 else 10):
            raise ProtocolValueError('frequency_hz requires 10 Hz steps to 140 MHz, 20 Hz steps above 140 MHz')
        mhz = Decimal(hz) / Decimal(1_000_000)
        return f'FR{mhz:.5f}MZ'

    @staticmethod
    def level_dbuv(value: Number) -> str:
        return 'AP' + number(value, lower='-26', upper='126', places=1, name='level_dbuv') + 'DB'

    @staticmethod
    def level_dbm(value: Number) -> str:
        return 'AP' + number(value, lower='-133', upper='19', places=1, name='level_dbm') + 'DM'

    @staticmethod
    def impedance(ohm: int) -> str:
        if type(ohm) is not int or ohm not in (50, 75):
            raise ProtocolValueError('output impedance must be 50 or 75 ohm')
        return f'AP{ohm}'

    @staticmethod
    def output(enabled: bool) -> str:
        if type(enabled) is not bool:
            raise ProtocolValueError('enabled must be bool')
        return 'APON' if enabled else 'APOF'

    @staticmethod
    def am_depth(percent: Number) -> str:
        text = number(percent, lower='0', upper='100', places=1, name='am_depth_percent')
        if Decimal(text) % Decimal('0.5'):
            raise ProtocolValueError('AM depth step must be 0.5 percent')
        return 'AM' + text

    @staticmethod
    def fm_deviation_khz(khz: Number) -> str:
        text = number(khz, lower='0', upper='999', places=2, name='fm_deviation_khz')
        val = Decimal(text)
        resolution = Decimal('0.01') if val < 10 else (Decimal('0.1') if val < 100 else Decimal('1'))
        if val % resolution:
            raise ProtocolValueError(f'FM deviation step is {resolution} kHz in this band')
        return 'FM' + text

    @staticmethod
    def modulation_enabled(kind: str, enabled: bool) -> str:
        if kind not in ('AM', 'FM') or type(enabled) is not bool:
            raise ProtocolValueError('kind must be AM or FM and enabled must be bool')
        return kind + ('ON' if enabled else 'OF')

    @staticmethod
    def modulation_source(kind: str, source: str) -> str:
        if kind not in ('AM', 'FM') or source not in ('T1', 'T4', 'XD'):
            raise ProtocolValueError('unknown modulation source')
        return kind + source

    @staticmethod
    def stereo(mode: str) -> str:
        codes = {'OFF':'00','MONO_INT':'01','L_EQ_R_INT':'02','L_INT':'03',
                 'R_INT':'04','L_MINUS_R_INT':'05','MONO_EXT':'11',
                 'L_EQ_R_EXT':'12','L_EXT':'13','R_EXT':'14',
                 'L_MINUS_R_EXT':'15','L_R_EXT':'17'}
        if mode not in codes:
            raise ProtocolValueError('unknown stereo mode')
        return 'MS' + codes[mode]

    @staticmethod
    def pilot(enabled: bool, percent: Number | None = None) -> tuple[str, ...]:
        if type(enabled) is not bool:
            raise ProtocolValueError('pilot enabled must be bool')
        if percent is None:
            return ('PLON' if enabled else 'PLOF',)
        setting = 'PL' + number(percent, lower='0', upper='19.9', places=1, name='pilot_percent')
        return (setting, 'PLON' if enabled else 'PLOF')

    @staticmethod
    def preemphasis(us: int | None) -> str:
        mapping = {None: 0, 25: 1, 50: 2, 75: 3}
        if type(us) is bool or us not in mapping:
            raise ProtocolValueError('preemphasis must be None, 25, 50 or 75 us')
        return 'PR' + str(mapping[us])

    @staticmethod
    def clipper(enabled: bool) -> str:
        if type(enabled) is not bool:
            raise ProtocolValueError('clipper enabled must be bool')
        return 'NPON' if enabled else 'NPOF'

    @staticmethod
    def composite_level_mv(value: Number) -> str:
        return 'LV' + number(value, lower='0', upper='9990', places=0, name='composite_level_mv')

    @staticmethod
    def total_fm_deviation(value: Number) -> str:
        return 'FT' + number(value, lower='0', upper='402', places=1, name='total_fm_deviation')
