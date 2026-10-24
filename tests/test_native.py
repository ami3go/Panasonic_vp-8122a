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
