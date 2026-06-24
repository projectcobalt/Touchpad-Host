"""Load raw RS485 command transactions from JSONL files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .session.queue import RESPONSE_COMMANDS, TransactionSpec


class CommandFileError(ValueError):
    """Raised when a command JSONL file contains an invalid entry."""


def parse_int(value: Any, *, field: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise CommandFileError(f"{field} must be an integer or integer string")


def parse_hex_payload(value: Any) -> bytes:
    if value is None:
        return b""
    if isinstance(value, list):
        return bytes(parse_int(item, field="payload item") & 0xFF for item in value)
    if not isinstance(value, str):
        raise CommandFileError("payload must be a hex string or byte list")
    compact = value.replace(" ", "").replace(":", "").replace("-", "")
    if not compact:
        return b""
    if len(compact) % 2:
        raise CommandFileError("payload hex must contain whole bytes")
    return bytes.fromhex(compact)


def parse_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off"):
            return False
    if value in (0, 1):
        return bool(value)
    raise CommandFileError(f"{field} must be boolean")


def transaction_from_record(record: dict[str, Any]) -> TransactionSpec:
    command = parse_int(record.get("command", record.get("cmd")), field="command")
    expected_value = record.get("expected_commands", record.get("expected"))
    expected: tuple[int, ...]
    if expected_value is None:
        expected = RESPONSE_COMMANDS.get(command, (command,))
    elif isinstance(expected_value, list):
        expected = tuple(parse_int(item, field="expected item") for item in expected_value)
    else:
        expected = (parse_int(expected_value, field="expected"),)
    return TransactionSpec(
        command=command,
        payload=parse_hex_payload(record.get("payload", "")),
        expected_commands=expected,
        name=str(record.get("name", f"cmd_0x{command:02X}")),
        max_attempts=parse_int(record.get("max_attempts", 3), field="max_attempts"),
        timeout=float(record.get("timeout", 3.0)),
        require_match=parse_bool(record.get("require_match", True), field="require_match"),
        block_on_failure=parse_bool(record.get("block_on_failure", False), field="block_on_failure"),
    )


def load_transactions(path: Path) -> list[TransactionSpec]:
    transactions = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise CommandFileError(f"{path}:{line_no}: {exc}") from exc
            if not isinstance(record, dict):
                raise CommandFileError(f"{path}:{line_no}: record must be a JSON object")
            try:
                transactions.append(transaction_from_record(record))
            except Exception as exc:
                raise CommandFileError(f"{path}:{line_no}: {exc}") from exc
    return transactions
