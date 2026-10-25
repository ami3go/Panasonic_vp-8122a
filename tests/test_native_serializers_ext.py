"""Extended native serializer tests for new methods."""
import pytest
from decimal import Decimal

from panasonic_vp8122a import NativeCommands, ProtocolValueError
from hypothesis import given, strategies as st


@pytest.mark.parametrize("value,expected", [
    (10, "FR10KZ"),
    (1500, "FR1500KZ"),
    (Decimal('531.25'), "FR531.25KZ"),
    (280000, "FR280000KZ"),
])
def test_frequency_khz_golden(value, expected):
    assert NativeCommands.frequency_khz(value) == expected


@pytest.mark.parametrize("value", [
    9.99, 280000.01, Decimal('140000.015'), Decimal('150000.01'), '1500', True, float('nan'), float('inf')
])
def test_frequency_khz_rejections(value):
    with pytest.raises(ProtocolValueError):
        NativeCommands.frequency_khz(value)


@pytest.mark.parametrize("value,expected", [
    (Decimal('0.000050'), "AP0.000050MV"),
    (2000, "AP2000MV"),
    (Decimal('12.5'), "AP12.5MV"),
])
def test_level_mv_golden(value, expected):
    assert NativeCommands.level_mv(value) == expected


@pytest.mark.parametrize("value", [
    Decimal('0.000049'), Decimal('2000.000001'), Decimal('1.0000001')
])
def test_level_mv_rejections(value):
    with pytest.raises(ProtocolValueError):
        NativeCommands.level_mv(value)


@pytest.mark.parametrize("value,expected", [
    (Decimal('0.050'), "AP0.050UV"),
    (2000000, "AP2000000UV"),
])
def test_level_uv_golden(value, expected):
    assert NativeCommands.level_uv(value) == expected


@pytest.mark.parametrize("value", [
    Decimal('0.049'), 2000001, Decimal('1.0001')
])
def test_level_uv_rejections(value):
    with pytest.raises(ProtocolValueError):
        NativeCommands.level_uv(value)


@pytest.mark.parametrize("enabled,expected", [
    (True, "COON"),
    (False, "COOF"),
])
def test_continuous_control_golden(enabled, expected):
    assert NativeCommands.continuous_control(enabled) == expected


@pytest.mark.parametrize("value", [1, 'ON'])
def test_continuous_control_rejections(value):
    with pytest.raises(ProtocolValueError):
        NativeCommands.continuous_control(value)


@pytest.mark.parametrize("direction,expected", [
    ('UP', "COUP"),
    ('DN', "CODN"),
])
def test_continuous_step_golden(direction, expected):
    assert NativeCommands.continuous_step(direction) == expected


@pytest.mark.parametrize("value", ['up', 'UPP', ''])
def test_continuous_step_rejections(value):
    with pytest.raises(ProtocolValueError):
        NativeCommands.continuous_step(value)


@pytest.mark.parametrize("value,expected", [
    (0, "CO0"),
    (Decimal('2.5'), "CO2.5"),
    (10, "CO10"),
])
def test_continuous_decrement_db_golden(value, expected):
    assert NativeCommands.continuous_decrement_db(value) == expected


@pytest.mark.parametrize("value", [-0.1, 10.1, Decimal('2.55')])
def test_continuous_decrement_db_rejections(value):
    with pytest.raises(ProtocolValueError):
        NativeCommands.continuous_decrement_db(value)


@pytest.mark.property
@given(st.integers(0, 100).map(lambda n: Decimal(n) / 10))
def test_continuous_decrement_db_property(value):
    """Every value in the range serializes to 'CO' + format(value, 'f') and contains no space."""
    result = NativeCommands.continuous_decrement_db(value)
    expected = 'CO' + format(value, 'f')
    assert result == expected
    assert ' ' not in result


def test_no_spaces_in_outputs():
    """Assert that NONE of the new outputs contains a space character."""
    # Test all new methods return strings without spaces
    assert ' ' not in NativeCommands.frequency_khz(1500)
    assert ' ' not in NativeCommands.level_mv(12.5)
    assert ' ' not in NativeCommands.level_uv(12.5)
    assert ' ' not in NativeCommands.continuous_control(True)
    assert ' ' not in NativeCommands.continuous_step('UP')
    assert ' ' not in NativeCommands.continuous_decrement_db(2.5)