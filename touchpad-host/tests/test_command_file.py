from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from airtouch4.command_file import load_transactions, transaction_from_record


class CommandFileTests(unittest.TestCase):
    def test_transaction_from_record_defaults_expected_response(self) -> None:
        spec = transaction_from_record({"command": "0x20", "payload": "41 00", "name": "group on"})

        self.assertEqual(spec.command, 0x20)
        self.assertEqual(spec.payload, bytes.fromhex("41 00"))
        self.assertEqual(spec.expected_commands, (0x21,))
        self.assertEqual(spec.name, "group on")

    def test_transaction_from_record_explicit_expected(self) -> None:
        spec = transaction_from_record({"cmd": 0x40, "payload": [0, 26, 6, 13], "expected": ["0x41"], "timeout": 1.5, "require_match": "false"})

        self.assertEqual(spec.command, 0x40)
        self.assertEqual(spec.payload, bytes((0, 26, 6, 13)))
        self.assertEqual(spec.expected_commands, (0x41,))
        self.assertEqual(spec.timeout, 1.5)
        self.assertFalse(spec.require_match)

    def test_load_transactions_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "commands.jsonl"
            path.write_text(
                '# comment\n{"command":"0x21","name":"status"}\n{"command":"0x53","payload":"00"}\n',
                encoding="utf-8",
            )

            specs = load_transactions(path)

        self.assertEqual([spec.command for spec in specs], [0x21, 0x53])
        self.assertEqual(specs[1].payload, b"\x00")


if __name__ == "__main__":
    unittest.main()
