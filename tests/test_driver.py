import pytest
from panasonic_vp8122a import VP8122A, RFProfile, NativeCommands, ProtocolValueError, UnsafeStateError, NotConnected


class FakeInstrument:
    def __init__(self, *, fail_at=0, status='FR87.50000MZ AP20.0DB COOF'):
        self.writes=[]
        self.fail_at=fail_at
        self.status=status
        self.timeout=None
        self.write_termination=None
        self.read_termination=None
        self.closed=False
        self.local=[]
    def write(self, cmd):
        self.writes.append(cmd)
        if self.fail_at and len(self.writes)==self.fail_at:
            raise TimeoutError('injected')
    def read(self): return self.status
    def close(self): self.closed=True
    def control_ren(self, op): self.local.append(op)


class FakeRM:
    def __init__(self, inst): self.inst=inst; self.closed=False; self.resources=[]
    def open_resource(self, resource):
        self.resources.append(resource)
        return self.inst
    def close(self): self.closed=True
    def list_resources(self): return ('GPIB0::2::INSTR',)


def driver(inst=None, **kw):
    inst = inst or FakeInstrument()
    rm = FakeRM(inst)
    return VP8122A('GPIB0::2::INSTR', resource_manager=rm, settle_seconds=0, **kw),inst,rm


def test_vectors_compact():
    c=NativeCommands
    assert c.frequency_hz(531000)=='FR0.53100MZ'
    assert c.level_dbuv(20)=='AP20DB'
    assert c.level_dbm(-20)=='AP-20DM'
    assert c.impedance(50)=='AP50'
    assert c.output(False)=='APOF'
    assert c.output(True)=='APON'
    assert c.am_depth(30)=='AM30'
    assert c.fm_deviation_khz(2.5)=='FM2.5'
    assert c.modulation_enabled('AM', True)=='AMON'
    assert c.modulation_source('FM','T1')=='FMT1'
    assert c.pilot(True,10)==('PL10','PLON')
    assert c.preemphasis(50)=='PR2'

@pytest.mark.parametrize('value', [float('nan'), float('inf'), -27, 127, True, '20', 2.333])
def test_strict_level(value):
    with pytest.raises(ProtocolValueError): NativeCommands.level_dbuv(value)

@pytest.mark.parametrize('hz', [1, 9990, 280000010, True, 10.5, 12345])
def test_frequency_validation(hz):
    with pytest.raises(ProtocolValueError): NativeCommands.frequency_hz(hz)


def test_no_idn_and_no_enable_on_connect():
    d,inst,rm=driver()
    with d:
        assert inst.writes==[]
        assert d.state=='CONNECTED_UNKNOWN'
    assert inst.writes==['APOF']
    assert inst.closed
    assert not rm.closed  # injected external RM is caller-owned


def test_requires_connection():
    d,inst,_=driver()
    with pytest.raises(NotConnected): d.output_off()
    assert not inst.writes


def test_safe_profile_and_explicit_enable():
    d,inst,_=driver()
    with d:
        result=d.configure(RFProfile(531000, 20, am_depth_percent=30))
        assert inst.writes[0]=='APOF'
        assert inst.writes[-1]=='FMOf'.upper()
        assert all(' ' not in c for c in inst.writes)
        assert result[0]=='FR0.53100MZ'
        assert d.state=='CONFIGURED_OFF_UNCONFIRMED'
        with pytest.raises(PermissionError): d.enable_output()
        assert 'APON' not in inst.writes
        d.enable_output(authorized=True)
        assert inst.writes[-1]=='APON'
    assert inst.writes[-1]=='APOF'


def test_preflight_rejects_no_io():
    d,inst,_=driver()
    with d:
        with pytest.raises(ProtocolValueError): d.configure(RFProfile(531000,200))
        with pytest.raises(ProtocolValueError): d.configure(RFProfile(531000,20,am_depth_percent=20,fm_deviation_khz=20))
        assert inst.writes==[]


def test_fault_recovery_and_state():
    d,inst,_=driver(FakeInstrument(fail_at=3))
    d.connect()
    with pytest.raises(UnsafeStateError): d.configure(RFProfile(531000,20))
    assert inst.writes[0]=='APOF'
    assert inst.writes[-1]=='APOF'
    assert 'APON' not in inst.writes
    assert d.state=='OFF_UNCONFIRMED'
    d.close()


def test_off_failure_keeps_uncertain_state():
    d,inst,_=driver(FakeInstrument(fail_at=1))
    d.connect()
    with pytest.raises(UnsafeStateError): d.output_off()
    assert d.state=='UNKNOWN'
    d.close()


def test_status_reads_without_query():
    d,inst,_=driver()
    d.connect()
    assert d.status_fields()=={'FR':'87.50000MZ','AP':'20.0DB','CO':'OF'}
    assert inst.writes==[]
    d.close()


def test_return_local_uses_bus_api(monkeypatch):
    import sys, types
    constants=types.SimpleNamespace(RENLineOperation=types.SimpleNamespace(address_gtl=object()))
    monkeypatch.setitem(sys.modules, 'pyvisa', types.SimpleNamespace(constants=constants))
    monkeypatch.setitem(sys.modules, 'pyvisa.constants', constants)
    d,inst,_=driver()
    d.connect()
    d.return_local()
    assert inst.local==[constants.RENLineOperation.address_gtl]
    assert 'GTL' not in inst.writes
    d.close()


def test_owned_manager_closes_on_exit():
    inst=FakeInstrument()
    rm=FakeRM(inst)
    with VP8122A('GPIB0::2::INSTR',manager_factory=lambda:rm,settle_seconds=0): pass
    assert rm.closed


def test_close_failure_never_silent():
    d,inst,_=driver(FakeInstrument(fail_at=1))
    d.connect()
    with pytest.raises(UnsafeStateError): d.close()
    assert inst.closed
    assert d.state=='DISCONNECTED_RF_UNKNOWN'
