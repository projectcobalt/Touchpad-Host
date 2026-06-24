"""Shared helpers for AirTouch 4 payload encoders and decoders."""

from __future__ import annotations

SENSOR_SELECTORS = {
    0x80: "ac_sensor",
    0x90: "touchpad_1",
    0x91: "touchpad_2",
    0xFD: "economy",
    0xFE: "average",
    0xFF: "auto",
}

for _sensor in range(32):
    SENSOR_SELECTORS.setdefault(_sensor, f"rf_sensor_{_sensor}")


def bit(byte: int, mask: int) -> bool:
    return (byte & mask) != 0


def u16be(data: bytes | bytearray, offset: int) -> int:
    return (data[offset] << 8) | data[offset + 1]


def bcd_string(data: bytes | bytearray) -> str:
    return "".join(f"{byte:02X}" for byte in data)


def signed_hex(byte: int) -> str:
    return f"0x{byte & 0xFF:02X}"


def parse_internal_temperature(byte: int) -> int | None:
    """Decode one-byte temperatures used in internal touchpanel frames."""
    if byte == 0xFF:
        return None
    if byte < 40:
        return byte - 25
    if byte < 231:
        return int((byte + 110) / 10)
    return byte - 197


def encode_internal_temperature(temperature: float) -> int:
    """Encode one-byte temperatures used in internal touchpanel frames."""
    rounded = round(temperature)
    if rounded < -25 or rounded > 58:
        raise ValueError("touchpad temperature must be between -25 and 58 degrees")
    if rounded < 15:
        return rounded + 25
    if rounded <= 34:
        return (rounded * 10) - 110
    return rounded + 197


def decode_api_temperature(encoded: int) -> float:
    """Decode the 11-bit AT4 client/API temperature format."""
    return ((encoded >> 5) - 500) / 10


def encode_api_temperature(temperature: float) -> int:
    return (round((temperature * 10) + 500) << 5) & 0xFFE0
