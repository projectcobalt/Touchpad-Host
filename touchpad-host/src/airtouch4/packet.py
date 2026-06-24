"""AirTouch 4 packet framing, CRC, and stream extraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .constants import address_name, command_name

NORMAL_PREFIX = b"\x55\x55"
RAW_PREFIX = b"\x55\x55\x55\xAA"


class PacketParseError(ValueError):
    """Raised when a byte sequence is not a complete AirTouch packet."""


def crc16_modbus(data: bytes | bytearray | memoryview) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def hex_bytes(data: Iterable[int]) -> str:
    return " ".join(f"{byte & 0xFF:02X}" for byte in data)


def _stuff_raw_body(frame: bytes) -> bytes:
    """Apply APK-style raw-mode stuffing after the 55 55 55 AA prefix."""
    if not frame.startswith(RAW_PREFIX):
        return frame
    out = bytearray(frame[:4])
    count_55 = 0
    for byte in frame[4:]:
        out.append(byte)
        if byte == 0x55:
            count_55 += 1
            if count_55 >= 3:
                out.append(0x00)
                count_55 = 0
        else:
            count_55 = 0
    return bytes(out)


def unstuff_raw_body(data: bytes) -> bytes:
    """Remove raw-mode 0x00 inserted after three consecutive 0x55 bytes."""
    if not data.startswith(RAW_PREFIX):
        return data
    out = bytearray(data[:4])
    count_55 = 0
    index = 4
    while index < len(data):
        byte = data[index]
        if count_55 >= 3 and byte == 0x00:
            count_55 = 0
            index += 1
            continue
        out.append(byte)
        if byte == 0x55:
            count_55 += 1
        else:
            count_55 = 0
        index += 1
    return bytes(out)


@dataclass(frozen=True)
class AirTouchPacket:
    dest: int
    src: int
    packet_id: int
    command: int
    payload: bytes = b""
    raw_mode: bool = False
    crc_received: int | None = None
    crc_calculated: int | None = None
    stream_offset: int = 0

    @property
    def crc_ok(self) -> bool:
        return self.crc_received is not None and self.crc_received == self.crc_calculated

    @property
    def command_name(self) -> str:
        return command_name(self.command)

    @property
    def dest_name(self) -> str:
        return address_name(self.dest)

    @property
    def src_name(self) -> str:
        return address_name(self.src)

    def encode(self, *, raw_mode: bool | None = None, stuff_raw: bool = False) -> bytes:
        use_raw = self.raw_mode if raw_mode is None else raw_mode
        prefix = RAW_PREFIX if use_raw else NORMAL_PREFIX
        payload_len = len(self.payload)
        frame = bytearray(prefix)
        frame.extend(
            (
                self.dest & 0xFF,
                self.src & 0xFF,
                self.packet_id & 0xFF,
                self.command & 0xFF,
                (payload_len >> 8) & 0xFF,
                payload_len & 0xFF,
            )
        )
        frame.extend(self.payload)
        crc = crc16_modbus(frame[len(prefix):])
        frame.extend(((crc >> 8) & 0xFF, crc & 0xFF))
        data = bytes(frame)
        return _stuff_raw_body(data) if stuff_raw and use_raw else data

    def to_record(self) -> dict:
        return {
            "stream_offset": self.stream_offset,
            "raw_mode": self.raw_mode,
            "raw": hex_bytes(self.encode(raw_mode=self.raw_mode)),
            "dest": f"0x{self.dest:02X}",
            "dest_name": self.dest_name,
            "src": f"0x{self.src:02X}",
            "src_name": self.src_name,
            "packet_id": self.packet_id,
            "cmd": f"0x{self.command:02X}",
            "cmd_name": self.command_name,
            "len": len(self.payload),
            "payload": hex_bytes(self.payload),
            "crc_received": None if self.crc_received is None else f"0x{self.crc_received:04X}",
            "crc_calc": None if self.crc_calculated is None else f"0x{self.crc_calculated:04X}",
            "crc_ok": self.crc_ok,
        }


def build_packet(
    *,
    dest: int,
    src: int,
    packet_id: int,
    command: int,
    payload: bytes | bytearray = b"",
    raw_mode: bool = False,
    stuff_raw: bool = False,
) -> bytes:
    packet = AirTouchPacket(
        dest=dest,
        src=src,
        packet_id=packet_id,
        command=command,
        payload=bytes(payload),
        raw_mode=raw_mode,
    )
    return packet.encode(stuff_raw=stuff_raw)


def parse_packet(frame: bytes, *, stream_offset: int = 0) -> AirTouchPacket:
    raw_mode = frame.startswith(RAW_PREFIX)
    if raw_mode:
        clean = unstuff_raw_body(frame)
        prefix_len = len(RAW_PREFIX)
    elif frame.startswith(NORMAL_PREFIX):
        clean = frame
        prefix_len = len(NORMAL_PREFIX)
    else:
        raise PacketParseError("missing AirTouch prefix")

    if len(clean) < prefix_len + 8:
        raise PacketParseError("packet is too short")

    shell = prefix_len
    payload_len = (clean[shell + 4] << 8) | clean[shell + 5]
    frame_len = prefix_len + 8 + payload_len
    if len(clean) < frame_len:
        raise PacketParseError("packet is incomplete")
    if len(clean) > frame_len:
        clean = clean[:frame_len]

    payload_start = shell + 6
    payload_end = payload_start + payload_len
    crc_received = (clean[payload_end] << 8) | clean[payload_end + 1]
    crc_calculated = crc16_modbus(clean[shell:payload_end])

    return AirTouchPacket(
        dest=clean[shell],
        src=clean[shell + 1],
        packet_id=clean[shell + 2],
        command=clean[shell + 3],
        payload=clean[payload_start:payload_end],
        raw_mode=raw_mode,
        crc_received=crc_received,
        crc_calculated=crc_calculated,
        stream_offset=stream_offset,
    )


def _prefix_len_at(data: bytes, index: int) -> int:
    if data[index:index + 4] == RAW_PREFIX:
        return len(RAW_PREFIX)
    if data[index:index + 2] == NORMAL_PREFIX:
        return len(NORMAL_PREFIX)
    return 0


def extract_packets(data: bytes, *, max_payload_len: int = 4096) -> list[AirTouchPacket]:
    packets: list[AirTouchPacket] = []
    index = 0
    while index <= len(data) - 10:
        prefix_len = _prefix_len_at(data, index)
        if prefix_len == 0:
            index += 1
            continue

        candidate = unstuff_raw_body(data[index:]) if prefix_len == len(RAW_PREFIX) else data[index:]
        if len(candidate) < prefix_len + 8:
            break

        shell = prefix_len
        payload_len = (candidate[shell + 4] << 8) | candidate[shell + 5]
        frame_len = prefix_len + 8 + payload_len
        if payload_len > max_payload_len:
            index += 1
            continue
        if len(candidate) < frame_len:
            index += 1
            continue

        try:
            packets.append(parse_packet(candidate[:frame_len], stream_offset=index))
        except PacketParseError:
            index += 1
            continue
        index += frame_len
    return packets
