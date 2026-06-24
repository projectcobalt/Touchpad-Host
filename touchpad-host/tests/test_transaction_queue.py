from __future__ import annotations

import unittest

from airtouch4.commands import group_power_command
from airtouch4.packet import AirTouchPacket
from airtouch4.session.init import default_init_transactions
from airtouch4.session.queue import TransactionQueue, TransactionSpec


def packet(command: int) -> AirTouchPacket:
    return AirTouchPacket(dest=0x91, src=0x80, packet_id=1, command=command, payload=b"")


class TransactionQueueTests(unittest.TestCase):
    def test_defaults_expected_response_from_command(self) -> None:
        queue = TransactionQueue()
        queue.enqueue(TransactionSpec.from_command(group_power_command(1, True), name="group on"))

        events, spec = queue.poll(0.0)

        self.assertEqual(spec.command, 0x20)
        self.assertEqual(spec.expected_commands, (0x21,))
        self.assertEqual(events[0].event, "request")

    def test_ignores_unrelated_packet_and_completes_on_match(self) -> None:
        queue = TransactionQueue()
        queue.enqueue(TransactionSpec(0x20, expected_commands=(0x21,), name="group"))
        queue.poll(0.0)

        self.assertEqual(queue.observe(packet(0x73)), [])
        events = queue.observe(packet(0x21))

        self.assertEqual(events[0].event, "complete")
        self.assertTrue(queue.idle())

    def test_retries_then_fails(self) -> None:
        queue = TransactionQueue()
        queue.enqueue(TransactionSpec(0x61, expected_commands=(0x61,), max_attempts=2, timeout=3.0))

        _events, first = queue.poll(0.0)
        _events, none = queue.poll(2.9)
        _events, second = queue.poll(3.0)
        events, failed = queue.poll(6.0)

        self.assertEqual(first.command, 0x61)
        self.assertIsNone(none)
        self.assertEqual(second.command, 0x61)
        self.assertIsNone(failed)
        self.assertEqual(events[0].event, "failed")
        self.assertTrue(queue.idle())

    def test_blocking_failure_stops_queue(self) -> None:
        queue = TransactionQueue()
        queue.enqueue_many([
            TransactionSpec(0x61, expected_commands=(0x61,), max_attempts=1, timeout=1.0, block_on_failure=True),
            TransactionSpec(0x21, expected_commands=(0x21,)),
        ])

        queue.poll(0.0)
        events, request = queue.poll(1.0)
        events_again, request_again = queue.poll(2.0)

        self.assertEqual(events[0].event, "failed")
        self.assertIsNone(request)
        self.assertEqual(events_again, [])
        self.assertIsNone(request_again)
        self.assertFalse(queue.idle())
        self.assertEqual(queue.summary()["pending"], 1)

    def test_queues_next_after_completion(self) -> None:
        queue = TransactionQueue()
        queue.enqueue_many([
            TransactionSpec(0x55, expected_commands=(0x55,), name="pref"),
            TransactionSpec(0x61, expected_commands=(0x61,), name="params"),
        ])

        _events, first = queue.poll(0.0)
        queue.observe(packet(0x55))
        _events, second = queue.poll(0.1)

        self.assertEqual(first.command, 0x55)
        self.assertEqual(second.command, 0x61)

    def test_init_transaction_plan_matches_current_init_steps(self) -> None:
        specs = default_init_transactions()

        self.assertEqual(len(specs), 25)
        self.assertEqual(specs[0].command, 0x55)
        self.assertEqual(specs[-1].command, 0x71)
        self.assertEqual(specs[5].payload, b"\x00")
        self.assertEqual(specs[5].expected_commands, (0x53,))


if __name__ == "__main__":
    unittest.main()
