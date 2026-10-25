"""Panasonic VP-8122A legacy native GPIB driver, version 0.2.8."""
from .driver import (VP8122A, RFProfile, DriverError, NotConnected, TransportError,
                     UnsafeStateError, UnsupportedOperation)
from .protocol import NativeCommands, ProtocolValueError
from .native import NativeStatus, NativeField, Termination, encode_program_word, parse_status

__version__ = '0.2.8'
__all__ = ['VP8122A', 'RFProfile', 'DriverError', 'NotConnected', 'TransportError',
           'UnsafeStateError', 'UnsupportedOperation', 'NativeCommands', 'ProtocolValueError']
