"""Panasonic VP-8122A legacy native GPIB driver, version 0.2.2."""
from .driver import (VP8122A, RFProfile, DriverError, NotConnected, TransportError,
                     UnsafeStateError, UnsupportedOperation)
from .protocol import NativeCommands, ProtocolValueError

__version__ = '0.2.2'
__all__ = ['VP8122A', 'RFProfile', 'DriverError', 'NotConnected', 'TransportError',
           'UnsafeStateError', 'UnsupportedOperation', 'NativeCommands', 'ProtocolValueError']
