"""Panasonic native GPIB messages and ordered talker output.

Only a *single* program word is encoded by default. EOI is an IEEE-488
bus-level signal supplied by the VISA controller, never an ASCII suffix.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from .protocol import ProtocolValueError

MAX_PROGRAM_MESSAGE = 255
MAX_TALKER_RESPONSE = 1024
_WORD = re.compile(r"[A-Z][A-Z0-9][A-Z0-9.+-]*\Z", re.ASCII)
_FAMILIES = frozenset((
    "FR", "AP", "LE", "EM", "CO", "AM", "FM", "MS", "PL", "FT", "PR",
    "SC", "LV", "NP", "RC", "ST", "TM", "DR", "AS", "NT", "P1", "P2",
))
_FIELD = re.compile(r"([A-Z][A-Z0-9])(.+)\Z", re.ASCII)


class Termination(str, Enum):
    EOI = ""
    LF = "\n"
    CRLF = "\r\n"


def encode_program_word(word: str, termination: str = "") -> bytes:
    """Return exactly the native bytes, rejecting raw-message injection."""
    if not isinstance(word, str) or not _WORD.fullmatch(word):
        raise ProtocolValueError("one compact 7-bit ASCII Panasonic program word required")
    if word[:2] not in _FAMILIES:
        raise ProtocolValueError("unknown Panasonic native program code family")
    if termination not in ("", "\n", "\r\n"):
        raise ProtocolValueError("termination must be EOI, LF or CRLF")
    payload = (word + termination).encode("ascii")
    if len(payload) > MAX_PROGRAM_MESSAGE:
        raise ProtocolValueError("native program message exceeds 255 bytes")
    return payload


@dataclass(frozen=True)
class NativeField:
    index: int
    prefix: str
    value: str
    raw: str


@dataclass(frozen=True)
class NativeStatus:
    mode: int
    raw: bytes
    fields: tuple[NativeField, ...]

    @property
    def text(self) -> str:
        return self.raw.decode("ascii")

    def values(self, prefix: str) -> tuple[str, ...]:
        return tuple(field.value for field in self.fields if field.prefix == prefix)


def parse_status(raw: bytes, *, mode: int = 0) -> NativeStatus:
    """Preserve positional TM0 repeats and the original bytes.

    Only TM0 uses the generic two-character-field parser. Other talker modes
    have different semantics and must be decoded by mode-specific functions.
    """
    if type(mode) is not int or mode not in (0, 1, 2):
        raise ProtocolValueError("unknown native talker mode")
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_TALKER_RESPONSE:
        raise ProtocolValueError("native status is empty or oversized")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ProtocolValueError("native status is not 7-bit ASCII") from exc
    if "\x00" in text or "\r" in text.rstrip("\r\n"):
        raise ProtocolValueError("native status contains invalid control bytes")
    if mode != 0:
        # Keep raw reply without inventing a TM1/TM2 grammar.
        return NativeStatus(mode=mode, raw=raw, fields=())
    tokens = re.split(r"[,\s]+", text.strip())
    fields = []
    for index, token in enumerate(tokens):
        match = _FIELD.fullmatch(token)
        if match is None:
            raise ProtocolValueError("malformed TM0 native field")
        fields.append(NativeField(index, match.group(1), match.group(2), token))
    return NativeStatus(mode=mode, raw=raw, fields=tuple(fields))
