import pytest
from src.PANASONIC_VP_8122A import storage, com_interface


def test_legacy_builder_compact_and_validated():
    cmd=storage()
    assert cmd.freq.MHz.val(0.531)=='FR0.53100MZ'
    assert cmd.output.set_dBuV.val(20)=='AP20DB'
    assert cmd.output.off()=='APOF'
    assert cmd.am.set1kHz()=='AMT1'
    assert cmd.main_and_sub_ch.MONO_INT()=='MS01'
    with pytest.raises(ValueError): cmd.freq.MHz.val(0)


def test_legacy_send_requires_explicit_authorization():
    class FakeRM:
        def open_resource(self, resource):
            class Inst:
                timeout=None
                write_termination=None
                def write(self, x): pass
                def close(self): pass
            return Inst()
    client=com_interface('GPIB0::2::INSTR',resource_manager=FakeRM(),settle_seconds=0).init()
    with pytest.raises(PermissionError): client.send('APON')
    client.disconnect()
