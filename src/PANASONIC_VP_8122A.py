"""Compatibility layer for the historical ``src.PANASONIC_VP_8122A`` path.

Modern callers should use ``panasonic_vp8122a``. Raw command execution requires
explicit ``authorized_raw=True`` because older scripts may energize RF.
"""
from __future__ import annotations

from types import SimpleNamespace
from panasonic_vp8122a import VP8122A, NativeCommands, UnsafeStateError
from panasonic_vp8122a.protocol import number


def _val(fn):
    return SimpleNamespace(val=fn)


def _switch(prefix):
    return SimpleNamespace(on=lambda: prefix+'ON', off=lambda: prefix+'OF')


def _modulation(prefix):
    return SimpleNamespace(
        set=_val(NativeCommands.am_depth if prefix=='AM' else NativeCommands.fm_deviation_khz),
        on=lambda: prefix+'ON', off=lambda: prefix+'OF',
        set1kHz=lambda: prefix+'T1', set400Hz=lambda: prefix+'T4',
        setExternal=lambda: prefix+'XD')


class storage:
    def __init__(self):
        self.go_to_local = SimpleNamespace(str=lambda: 'GTL')
        self.am = _modulation('AM')
        self.fm = _modulation('FM')
        self.control_out = SimpleNamespace(
            on=lambda: 'COON', off=lambda: 'COOF',
            up=lambda: 'COUP', down=lambda: 'CODN',
            set=_val(lambda x: 'CO' + number(x, lower='0', upper='10', places=1, name='continuous_control')))
        self.output = SimpleNamespace(
            on=lambda: 'APON', off=lambda: 'APOF',
            set_dBm=_val(NativeCommands.level_dbm),
            set_dBuV=_val(NativeCommands.level_dbuv),
            set_imp_50R=lambda: NativeCommands.impedance(50),
            set_imp_75R=lambda: NativeCommands.impedance(75))
        self.freq = SimpleNamespace(
            MHz=_val(lambda x: NativeCommands.frequency_hz(_to_hz(x, 1_000_000))),
            kHz=_val(lambda x: NativeCommands.frequency_hz(_to_hz(x, 1_000))))
        self.pilot_signal = SimpleNamespace(on=lambda: 'PLON', off=lambda: 'PLOF',
            set=_val(lambda x: NativeCommands.pilot(True,x)[0]))
        self.neg_peak_clipper = _switch('NP')
        self.total_fm_deviation = _val(NativeCommands.total_fm_deviation)
        self.composite_sign_out_level = _val(NativeCommands.composite_level_mv)
        self.fm_stereo_pre_emphasis = SimpleNamespace(
            OFF=lambda: NativeCommands.preemphasis(None),
            set_25uS=lambda: NativeCommands.preemphasis(25),
            set_50uS=lambda: NativeCommands.preemphasis(50),
            set_75uS=lambda: NativeCommands.preemphasis(75))
        self.main_and_sub_ch = SimpleNamespace(
            **{key: (lambda k=key: NativeCommands.stereo(k)) for key in
               ('OFF','MONO_INT','L_EQ_R_INT','L_INT','R_INT','L_MINUS_R_INT',
                'MONO_EXT','L_EQ_R_EXT','L_EXT','R_EXT','L_MINUS_R_EXT','L_R_EXT')})


def _to_hz(value, multiplier):
    from decimal import Decimal, InvalidOperation
    if isinstance(value, (str, bool)):
        raise ValueError('frequency must be numeric')
    try:
        hz = Decimal(str(value)) * multiplier
    except (InvalidOperation, TypeError) as exc:
        raise ValueError('invalid frequency') from exc
    if not hz.is_finite() or hz != hz.to_integral_value():
        raise ValueError('frequency must resolve to whole hertz')
    return int(hz)


class com_interface:
    def __init__(self, resource_name: str, **kwargs):
        self.cmd = storage()
        self._driver = VP8122A(resource_name, **kwargs)

    def init(self):
        self._driver.connect()
        return self

    def send(self, command: str, *, authorized_raw: bool = False):
        if not authorized_raw:
            raise PermissionError('Legacy raw send requires authorized_raw=True; use VP8122A.configure() instead')
        with self._driver._lock:
            self._driver._write(command)
            self._driver.state = 'UNKNOWN'

    def query(self, cmd_str: str | None = None):
        if cmd_str not in (None, 'STATUS'):
            raise ValueError('VP-8122A has no confirmed SCPI query syntax; use status read')
        return self._driver.read_status()

    def disconnect(self):
        self._driver.close()
