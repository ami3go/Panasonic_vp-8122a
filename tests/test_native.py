"""Wire-exact offline coverage for the Panasonic native program grammar."""
import pytest

from panasonic_vp8122a.native import (
    MAX_PROGRAM_MESSAGE, Termination, encode_program_word, parse_status,
)
from panasonic_vp8122a import NativeCommands, ProtocolValueError


@pytest.mark.parametrize("term,want", [
    ("", b"FR1MZ"),
    ("\n", b"FR1MZ\n"),
    ("\r\n", b"FR1MZ\r\n"),
])
def test_native_golden_terminations(term, want):
    assert encode_program_word("FR1MZ", term) == want


@pytest.mark.parametrize("bad", [
    "*IDN?", "*RST", "OUTP ON", "FR1MZ,APON", "FR1MZ\nAPON",
    "FR1MZ\r\n", "FMé", "apon", "GTL", "", " A1",
])
def test_rejects_unsafe_or_non_native_raw_words(bad):
    with pytest.raises(ProtocolValueError):
        encode_program_word(bad)


def test_native_length_includes_delimiter():
    word = "FR" + "1" * (MAX_PROGRAM_MESSAGE - 2)
    assert len(encode_program_word(word)) == MAX_PROGRAM_MESSAGE
    with pytest.raises(ProtocolValueError):
        encode_program_word(word, Termination.CRLF)


def test_status_preserves_repeated_fields_and_wire_bytes():
    raw = b"FR87.50000MZ AP20.0DB AP50 AM30 COOF APON\n"
    result = parse_status(raw)
    assert result.raw == raw
    assert result.values("AP") == ("20.0DB", "50", "ON")
    assert [(f.index, f.prefix) for f in result.fields if f.prefix == "AP"] == [
        (1, "AP"), (2, "AP"), (5, "AP")
    ]


def test_status_rejects_non_ascii_and_bogus_fields():
    for raw in (b"", b"not native", b"AP", b"AP20\x00", b"AP20\xff", b"X" * 1025):
        with pytest.raises(ProtocolValueError):
            parse_status(raw)


@pytest.mark.parametrize("mode", [1, 2])
def test_no_claim_of_undocumented_talker_grammar(mode):
    result = parse_status(b"123\n", mode=mode)
    assert result.fields == ()
    assert result.raw == b"123\n"


def test_documented_numeric_range_corrections():
    assert NativeCommands.am_depth(125) == "AM125"
    assert NativeCommands.fm_deviation_khz(300) == "FM300"
    with pytest.raises(ProtocolValueError):
        NativeCommands.fm_deviation_khz(300.01)
    assert NativeCommands.total_fm_deviation(9.99) == "FT9.99"
    with pytest.raises(ProtocolValueError):
        NativeCommands.total_fm_deviation(100.1)
    assert NativeCommands.talker_mode(0) == "TM0"
    assert NativeCommands.talker_mode(2) == "TM2"


@pytest.mark.parametrize("method,args,golden", [
    ("frequency_hz", (10_000,), "FR0.01000MZ"),
    ("frequency_hz", (280_000_000,), "FR280.00000MZ"),
    ("level_dbuv", (-26,), "AP-26DB"),
    ("level_dbuv", (126,), "AP126DB"),
    ("level_dbm", (-133,), "AP-133DM"),
    ("level_dbm", (19,), "AP19DM"),
    ("impedance", (50,), "AP50"),
    ("impedance", (75,), "AP75"),
    ("output", (False,), "APOF"),
    ("output", (True,), "APON"),
    ("am_depth", (125,), "AM125"),
    ("am_depth", (0.5,), "AM0.5"),
    ("fm_deviation_khz", (0.01,), "FM0.01"),
    ("fm_deviation_khz", (9.99,), "FM9.99"),
    ("fm_deviation_khz", (10.1,), "FM10.1"),
    ("fm_deviation_khz", (300,), "FM300"),
    ("modulation_enabled", ("AM", False), "AMOF"),
    ("modulation_enabled", ("FM", True), "FMON"),
    ("modulation_source", ("AM", "T4"), "AMT4"),
    ("modulation_source", ("FM", "XD"), "FMXD"),
    ("stereo", ("OFF",), "MS00"),
    ("stereo", ("MONO_INT",), "MS01"),
    ("stereo", ("L_R_EXT",), "MS17"),
    ("preemphasis", (None,), "PR0"),
    ("preemphasis", (75,), "PR3"),
    ("clipper", (True,), "NPON"),
    ("clipper", (False,), "NPOF"),
    ("composite_level_mv", (9990,), "LV9990"),
    ("total_fm_deviation", (9.99,), "FT9.99"),
    ("total_fm_deviation", (10.1,), "FT10.1"),
    ("total_fm_deviation", (402,), "FT402"),
    ("talker_mode", (0,), "TM0"),
    ("talker_mode", (1,), "TM1"),
    ("talker_mode", (2,), "TM2"),
])
def test_all_supported_native_command_builders_have_golden_bytes(method, args, golden):
    value = getattr(NativeCommands, method)(*args)
    assert value == golden
    assert encode_program_word(value, "\r\n") == golden.encode("ascii") + b"\r\n"


@pytest.mark.parametrize("enabled,percent,expected", [
    (False, None, ("PLOF",)),
    (True, None, ("PLON",)),
    (True, 0, ("PL0", "PLON")),
    (True, 19.9, ("PL19.9", "PLON")),
])
def test_pilot_golden_command_sequences(enabled, percent, expected):
    actual = NativeCommands.pilot(enabled, percent)
    assert actual == expected
    for word in actual:
        assert encode_program_word(word) == word.encode("ascii")


@pytest.mark.parametrize("value", [300.01, 301, 999, -0.01, float("inf"), float("nan")])
def test_fm_deviation_above_manual_limits_rejected_before_io(value):
    with pytest.raises(ProtocolValueError):
        NativeCommands.fm_deviation_khz(value)


@pytest.mark.parametrize("value", [10.01, 99.99, 100.1, 402.1])
def test_total_fm_deviation_band_resolution_is_enforced(value):
    with pytest.raises(ProtocolValueError):
        NativeCommands.total_fm_deviation(value)
