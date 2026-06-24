"""Touchscreen-side session helpers for the internal AirTouch bus."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ..constants import ADDR_MAIN_BOARD, ADDR_TOUCHPAD_1, ADDR_TOUCHPAD_2, ADDR_TOUCHPAD_EXPANDED
from ..packet import AirTouchPacket, extract_packets, hex_bytes
from ..payloads import decode_mainboard_payload

DEFAULT_SYNC_COMMANDS = (
    0x61,  # parameters
    0x75,  # AC base info
    0x79,  # AC settings
    0x23,  # AC status
    0x53,  # group names
    0x21,  # group status
    0x59,  # main display
    0x33,  # favourites, request payload is index in later pass
    0x6D,  # password info, request payload is index in later pass
    0x3D,  # programs
    0x43,  # AC runtime status
    0x37,  # AC timer status
    0x51,  # turbo group
    0x67,  # grouping
    0x69,  # spill
    0x71,  # sensor list
)

TOUCHPAD_SLOT_TO_ADDRESS = {
    1: ADDR_TOUCHPAD_1,
    2: ADDR_TOUCHPAD_2,
}

TOUCHPAD_ADDRESS_TO_SLOT = {address: slot for slot, address in TOUCHPAD_SLOT_TO_ADDRESS.items()}


@dataclass
class TouchscreenSession:
    src: int = ADDR_TOUCHPAD_1
    dest: int = ADDR_MAIN_BOARD
    raw_mode: bool = True
    heartbeat_payload: bytes = bytes.fromhex("00 EA 00")
    heartbeat_interval: float = 30.0
    sync_commands: tuple[int, ...] = DEFAULT_SYNC_COMMANDS
    next_packet_id: int = 0
    auto_address: bool = False
    seen_touchpad_addresses: set[int] = field(default_factory=set)
    seen_touchpads: dict[int, dict[str, Any]] = field(default_factory=dict)
    _rx_buffer: bytearray = field(default_factory=bytearray)
    _last_heartbeat: float = field(default=0.0)

    def build_packet(self, command: int, payload: bytes = b"") -> tuple[AirTouchPacket, bytes]:
        packet = AirTouchPacket(
            dest=self.dest,
            src=self.src,
            packet_id=self.next_packet_id,
            command=command,
            payload=payload,
            raw_mode=self.raw_mode,
        )
        self.next_packet_id = (self.next_packet_id + 1) & 0xFF
        wire = packet.encode(stuff_raw=self.raw_mode)
        return packet, wire

    def build_heartbeat(self) -> tuple[AirTouchPacket, bytes]:
        return self.build_packet(0x26, self.heartbeat_payload)

    def build_touchpad_info_request(self) -> tuple[AirTouchPacket, bytes]:
        return self.build_packet_to(ADDR_TOUCHPAD_EXPANDED, 0x1F, bytes.fromhex("FF 01"))

    def build_packet_to(self, dest: int, command: int, payload: bytes = b"") -> tuple[AirTouchPacket, bytes]:
        original_dest = self.dest
        self.dest = dest
        try:
            return self.build_packet(command, payload)
        finally:
            self.dest = original_dest

    def build_sync_requests(self) -> list[tuple[AirTouchPacket, bytes]]:
        return [self.build_packet(command) for command in self.sync_commands]

    def due_heartbeat(self, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        return self._last_heartbeat == 0.0 or current - self._last_heartbeat >= self.heartbeat_interval

    def mark_heartbeat_sent(self, now: float | None = None) -> None:
        self._last_heartbeat = time.monotonic() if now is None else now

    def feed_rx(self, data: bytes) -> list[AirTouchPacket]:
        self._rx_buffer.extend(data)
        packets = extract_packets(bytes(self._rx_buffer))
        if packets:
            last = packets[-1]
            consumed = last.stream_offset + len(last.encode(raw_mode=last.raw_mode))
            del self._rx_buffer[:consumed]
        elif len(self._rx_buffer) > 8192:
            del self._rx_buffer[:-1024]
        for packet in packets:
            self.observe_packet(packet)
        return packets

    def observe_packet(self, packet: AirTouchPacket) -> None:
        decoded = decode_mainboard_payload(packet.command, packet.payload)
        if decoded.get("expanded_name") != "touchpad_address_presence":
            return
        address = decoded.get("address")
        if address not in (1, 2):
            return
        self.seen_touchpad_addresses.add(address)
        self.seen_touchpads[address] = decoded
        if self.auto_address:
            self.choose_available_address()

    def choose_available_address(self, preferred_source: int | None = None, *, allow_occupied: bool = False) -> int | None:
        preferred_slot = None if preferred_source is None else TOUCHPAD_ADDRESS_TO_SLOT.get(preferred_source)
        occupied = set(self.seen_touchpad_addresses)

        if allow_occupied and preferred_source is not None:
            self.src = preferred_source
            return self.src

        if preferred_slot in (1, 2) and preferred_slot not in occupied:
            self.src = TOUCHPAD_SLOT_TO_ADDRESS[preferred_slot]
            return self.src

        for slot in (1, 2):
            if slot not in occupied:
                self.src = TOUCHPAD_SLOT_TO_ADDRESS[slot]
                return self.src

        return None

    def source_slot(self) -> int | None:
        return TOUCHPAD_ADDRESS_TO_SLOT.get(self.src)

    def source_address_conflicts(self) -> bool:
        slot = self.source_slot()
        return slot is not None and slot in self.seen_touchpad_addresses

    def occupied_touchpad_addresses(self) -> list[int]:
        return [TOUCHPAD_SLOT_TO_ADDRESS[slot] for slot in sorted(self.seen_touchpad_addresses) if slot in TOUCHPAD_SLOT_TO_ADDRESS]


def parse_hex_payload(text: str) -> bytes:
    compact = text.replace(" ", "").replace(":", "").replace("-", "")
    if len(compact) % 2:
        raise ValueError(f"hex payload must contain whole bytes: {text!r}")
    return bytes.fromhex(compact)


def parse_command_list(text: str) -> tuple[int, ...]:
    commands = []
    for item in text.split(","):
        stripped = item.strip()
        if not stripped:
            continue
        commands.append(int(stripped, 0))
    return tuple(commands)


def describe_packet(packet: AirTouchPacket) -> str:
    crc_status = "built" if packet.crc_received is None else "ok" if packet.crc_ok else "bad"
    return (
        f"{packet.src_name}->{packet.dest_name} seq={packet.packet_id:02X} "
        f"cmd={packet.command_name}(0x{packet.command:02X}) len={len(packet.payload)} "
        f"crc={crc_status} payload={hex_bytes(packet.payload)}"
    )
