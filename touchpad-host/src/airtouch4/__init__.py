"""Clean AirTouch 4 internal RS485 protocol primitives.

This package is the start of a Python replacement-touchscreen host. Runtime
behaviour is derived from the AirTouch touchscreen APK and validated with
internal main-board bus captures.
"""

from .constants import ADDRESS_NAMES, COMMAND_NAMES
from .packet import (
    AirTouchPacket,
    PacketParseError,
    build_packet,
    crc16_modbus,
    extract_packets,
    hex_bytes,
    parse_packet,
)
from .payloads import decode_capture_payload, decode_mainboard_payload

__all__ = [
    "ADDRESS_NAMES",
    "COMMAND_NAMES",
    "AirTouchPacket",
    "PacketParseError",
    "build_packet",
    "crc16_modbus",
    "extract_packets",
    "hex_bytes",
    "parse_packet",
    "decode_capture_payload",
    "decode_mainboard_payload",
]
