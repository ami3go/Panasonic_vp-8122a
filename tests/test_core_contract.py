"""Core-native Panasonic contract tests (no physical hardware)."""
from __future__ import annotations

from threading import Thread

import pytest
from hypothesis import given, strategies as st

from panasonic_vp8122a import (
    NativeCommands,
    ProtocolValueError,
    RFProfile,
    UnsafeStateError,
    VP8122A,
)
from panasonic_vp8122a.native import encode_program_word, parse_status
from scpi_driver_core.transport import MockTransport, TransportState


def create_driver(*, termination: str = ""):
    transport = MockTransport(timeout_s=0.1)
    device = VP8122A(
        "GPIB0::2::INSTR",
        transport=transport,
        settle_seconds=0,
        timeout_ms=100,
        write_termination=termination,
    )
    return device, transport


def asserted_native_only(transport: MockTransport) -> list[bytes]:
    commands = [operation.data for operation in transport.operations if operation.kind == "write"]
    assert commands
    for command in commands:
        assert command[:1] != b"*"
        assert b"SYST:" not in command and b"OUTP" not in command
        assert b"GTL" not in command
    return commands


@pytest.mark.parametrize("ending", ["", "\n", "\r\n"])
def test_raw_bytes_and_no_scpi_in_full_lifecycle(ending: str):
    device, transport = create_driver(termination=ending)
    device.connect()
    assert transport.written == b""
    transport.feed(b"FR87.50000MZ AP20DB AP50 APON\n")
    assert device.read_status().startswith("FR87.50000MZ")
    assert device.last_native_status is not None
    assert device.last_native_status.values("AP") == ("20DB", "50", "ON")
    assert device.configure(RFProfile(531000, 20))[0] == "FR0.53100MZ"
    assert b"APON" not in transport.written
    device.close()
    commands = asserted_native_only(transport)
    assert commands[0] == b"TM0" + ending.encode("ascii")
    assert commands[-1] == b"APOF" + ending.encode("ascii")
    assert transport.release_count == 1


def test_invalid_preflight_has_zero_transport_io():
    device, transport = create_driver()
    device.connect()
    with pytest.raises(ProtocolValueError):
        device.configure(RFProfile(531000, 999))
    assert transport.written == b""
    device.close()


def test_unknown_rf_after_timed_out_enable_is_not_replayed():
    device, transport = create_driver()
    device.connect()
    device.configure(RFProfile(531000, 20))
    transport.fail_next_write(TimeoutError("write may have been transmitted"))
    with pytest.raises(UnsafeStateError):
        device.enable_output(authorized=True)
    assert device.state == "UNKNOWN"
    assert transport.state is TransportState.FAULTED
    assert b"APON" not in transport.written
    # Explicit reconnect starts in UNKNOWN; never replays old profile/ON.
    old_writes = transport.written
    device.connect()
    assert transport.written == old_writes
    assert device.state == "CONNECTED_UNKNOWN"
    with pytest.raises(UnsafeStateError):
        device.enable_output(authorized=True)
    device.close()


def test_read_timeout_never_sends_scpi_or_autorecovers():
    device, transport = create_driver()
    device.connect()
    with pytest.raises(Exception):
        device.read_status()
    assert transport.state is TransportState.FAULTED
    assert transport.written == b"TM0"
    with pytest.raises(UnsafeStateError):
        device.close()
    assert transport.release_count >= 1


def test_borrowed_resources_are_independent():
    first, a = create_driver()
    second, b = create_driver()
    first.connect()
    second.connect()
    first.close()
    assert b.state is TransportState.OPEN
    second.configure(RFProfile(531000, 20))
    assert b"FR0.53100MZ" in b.written
    second.close()


@given(st.integers(min_value=0, max_value=99999))
@pytest.mark.property
def test_program_payload_is_bounded_and_7bit(value: int):
    word = NativeCommands.talker_mode(value % 3)
    for terminator in ("", "\n", "\r\n"):
        data = encode_program_word(word, terminator)
        assert len(data) <= 255
        assert all(byte < 128 for byte in data)


@given(
    st.lists(
        st.tuples(
            st.sampled_from(["AP", "FR", "AM", "FM", "CO"]),
            st.integers(min_value=0, max_value=999999),
        ),
        min_size=1,
        max_size=32,
    )
)
@pytest.mark.property
def test_tm0_parser_retains_every_field_and_order(fields):
    raw = (" ".join(key + str(value) for key, value in fields) + "\n").encode("ascii")
    parsed = parse_status(raw)
    assert [(f.prefix, f.value) for f in parsed.fields] == [
        (key, str(value)) for key, value in fields
    ]
    assert parsed.raw == raw


@given(st.text(min_size=0, max_size=300))
@pytest.mark.property
def test_random_untrusted_text_never_injects_newline(text: str):
    try:
        raw = encode_program_word(text, "\r\n")
    except ProtocolValueError:
        return
    assert raw.count(b"\r\n") == 1
    assert raw.endswith(b"\r\n")
    assert len(raw) <= 255


@pytest.mark.timeout(3)
def test_parallel_sessions_do_not_interleave_or_deadlock():
    a, ta = create_driver()
    b, tb = create_driver()
    errors = []

    def run(device):
        try:
            device.connect()
            device.configure(RFProfile(531000, 20))
            device.close()
        except Exception as exc:
            errors.append(exc)

    workers = [Thread(target=run, args=(x,), daemon=True) for x in (a, b)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=2)
    assert not errors
    assert all(not worker.is_alive() for worker in workers)
    assert b"APON" not in ta.written + tb.written


def test_malformed_talker_faults_resource_but_keeps_original_raw_evidence():
    device, transport = create_driver()
    device.connect()
    transport.feed(b"AP20DB !BROKEN\n")
    with pytest.raises(Exception):
        device.read_status()
    assert device.last_status == "AP20DB !BROKEN\n"
    assert device.last_native_status is None
    assert transport.state is TransportState.FAULTED
    assert transport.written == b"TM0"
    with pytest.raises(UnsafeStateError):
        device.close()


def test_outbound_non_native_programs_are_rejected_before_transport():
    device, transport = create_driver()
    device.connect()
    for command in ("*IDN?", "GTL", "OUTP:STAT 1", "FR1MZ\nAPON"):
        with pytest.raises(ProtocolValueError):
            device._write(command)
    assert transport.written == b""
    device.close()


def test_talker_mode_two_returns_raw_without_fake_tm0_decode():
    device, transport = create_driver()
    device.connect()
    transport.feed(b"123\n")
    assert device.read_status(mode=2) == "123\n"
    assert device.last_native_status is not None
    assert device.last_native_status.fields == ()
    assert transport.written == b"TM2"
    device.close()


def test_legacy_gtl_uses_addressed_operation_not_program_text():
    from src.PANASONIC_VP_8122A import com_interface

    class AddressedMock(MockTransport):
        def __init__(self):
            super().__init__()
            self.local_count = 0

        def go_to_local_addressed(self):
            self.local_count += 1

    transport = AddressedMock()
    legacy = com_interface(
        "GPIB0::2::INSTR", transport=transport, timeout_ms=100, settle_seconds=0,
    ).init()
    legacy.send("GTL", authorized_raw=True)
    assert transport.local_count == 1
    assert transport.written == b""
    legacy.disconnect()


@pytest.mark.timeout(3)
def test_profile_budget_includes_shared_core_pacing_wait():
    transport = MockTransport(timeout_s=0.1)
    device = VP8122A(
        "GPIB0::2::INSTR",
        transport=transport,
        timeout_ms=100,
        settle_seconds=0.02,
        profile_timeout_s=0.002,
    )
    device.connect()
    with pytest.raises(UnsafeStateError):
        device.configure(RFProfile(531000, 20))
    assert device.state != "CONFIGURED_OFF_UNCONFIRMED"
    assert b"APON" not in transport.written
    device.close()
