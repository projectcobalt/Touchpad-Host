from __future__ import annotations

from collections import Counter
from pathlib import Path
import unittest

from airtouch4.capture import iter_packets
from airtouch4.constants import COMMAND_NAMES
from airtouch4.packet import hex_bytes
from airtouch4.payloads import REFERENCE_DECODERS, decode_mainboard_payload
from airtouch4.payloads.registry import MAINBOARD_DECODERS


CAPTURE_PATTERNS = (
    "airtouch-rf-test-00[7-9].jsonl",
    "airtouch-rf-test-01[0-5].jsonl",
    "boot-capture-001.jsonl",
    "expansion-zones-*.jsonl",
    "live-*.jsonl",
    "live-dashboard*.jsonl",
    "live-host*.jsonl",
    "live-monitor*.jsonl",
    "main-zones-*.jsonl",
)


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


class ProtocolCoverageTests(unittest.TestCase):
    def test_all_named_internal_commands_have_decoders(self) -> None:
        missing = {
            command: name
            for command, name in COMMAND_NAMES.items()
            if command not in MAINBOARD_DECODERS and command not in REFERENCE_DECODERS
        }

        self.assertEqual(missing, {})

    def test_internal_bus_captures_do_not_decode_unknown_or_error(self) -> None:
        capture_dir = _workspace_root() / "research" / "captures"
        if not capture_dir.exists():
            self.skipTest("research captures are not present in this checkout")

        files: list[Path] = []
        for pattern in CAPTURE_PATTERNS:
            files.extend(capture_dir.glob(pattern))
        files = sorted(set(files))
        if not files:
            self.skipTest("no internal bus capture files found")

        problems: Counter[tuple[int, int, str, str]] = Counter()
        examples: dict[tuple[int, int, str, str], str] = {}
        for path in files:
            for line_no, packet, _meta in iter_packets(path):
                if not packet.crc_ok:
                    continue
                if _is_reference_or_external(packet.src, packet.dest, packet.command):
                    continue

                decoded = decode_mainboard_payload(packet.command, packet.payload)
                kind = decoded.get("type")
                if kind in {"unknown", "decode_error"}:
                    key = (
                        packet.command,
                        len(packet.payload),
                        kind,
                        str(decoded.get("error", "")),
                    )
                    problems[key] += 1
                    examples.setdefault(
                        key,
                        (
                            f"{path.name}:{line_no} "
                            f"{packet.src:02X}->{packet.dest:02X} "
                            f"payload={hex_bytes(packet.payload)}"
                        ),
                    )

        detail = "\n".join(
            f"0x{command:02X} len={length} {kind} count={count} {examples[key]} {error}"
            for key, count in problems.most_common(20)
            for command, length, kind, error in (key,)
        )
        self.assertEqual(problems, Counter(), detail)


def _is_reference_or_external(src: int, dest: int, command: int) -> bool:
    if command in REFERENCE_DECODERS:
        return True
    return (src & 0xF0) in {0xB0, 0xC0} or (dest & 0xF0) in {0xB0, 0xC0}


if __name__ == "__main__":
    unittest.main()
