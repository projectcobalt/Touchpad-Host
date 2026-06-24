from __future__ import annotations

import unittest

from airtouch4.packet import AirTouchPacket
from airtouch4.session.init import InitStep, TouchscreenInitStateMachine, default_init_steps


def response(command: int, payload: bytes = b"") -> AirTouchPacket:
    return AirTouchPacket(dest=0x91, src=0x80, packet_id=1, command=command, payload=payload)


class TouchscreenInitStateMachineTests(unittest.TestCase):
    def test_default_plan_matches_apk_shape(self) -> None:
        steps = default_init_steps()

        self.assertEqual([step.command for step in steps[:5]], [0x55, 0x61, 0x75, 0x79, 0x23])
        self.assertEqual([step.payload for step in steps if step.command == 0x53], [b"\x00", b"\x01", b"\x02", b"\x03"])
        self.assertEqual([step.payload for step in steps if step.command == 0x33], [b"\x00", b"\x01", b"\x02", b"\x03"])
        self.assertEqual([step.payload for step in steps if step.command == 0x6D], [b"\x01", b"\x02"])
        self.assertFalse(next(step for step in steps if step.command == 0x75).required)
        self.assertTrue(next(step for step in steps if step.command == 0x61).required)

    def test_request_and_advance_on_matching_response(self) -> None:
        init = TouchscreenInitStateMachine(steps=[
            InitStep(0x61, required=True, name="parameters"),
            InitStep(0x21, required=True, name="group status"),
        ])

        events, request = init.poll(10.0)
        self.assertEqual(request.command, 0x61)
        self.assertEqual(request.attempt, 1)
        self.assertEqual(events[-1].event, "request")

        events = init.observe(response(0x61))
        self.assertEqual(events[0].event, "complete")

        events, request = init.poll(10.1)
        self.assertEqual(request.command, 0x21)
        self.assertEqual(init.current_index, 1)

    def test_ignores_non_matching_response(self) -> None:
        init = TouchscreenInitStateMachine(steps=[InitStep(0x75, name="ac base")])
        init.poll(1.0)

        self.assertEqual(init.observe(response(0x21)), [])
        self.assertEqual(init.current_index, 0)

    def test_retries_after_interval(self) -> None:
        init = TouchscreenInitStateMachine(steps=[InitStep(0x75, retry_interval=3.0, max_attempts=2)])
        _events, first = init.poll(0.0)
        _events, too_soon = init.poll(2.9)
        _events, second = init.poll(3.0)

        self.assertEqual(first.attempt, 1)
        self.assertIsNone(too_soon)
        self.assertEqual(second.attempt, 2)

    def test_optional_step_degrades_and_continues(self) -> None:
        init = TouchscreenInitStateMachine(steps=[
            InitStep(0x75, max_attempts=1, retry_interval=1.0, name="ac base"),
            InitStep(0x21, required=True, name="group status"),
        ])

        init.poll(0.0)
        events, request = init.poll(1.0)

        self.assertEqual(events[0].event, "degraded")
        self.assertEqual(request.command, 0x21)
        self.assertTrue(init.degraded)
        self.assertEqual(init.summary()["skipped_optional"], ["0x75"])

    def test_required_step_fails_and_blocks(self) -> None:
        init = TouchscreenInitStateMachine(steps=[InitStep(0x61, required=True, max_attempts=1, retry_interval=1.0)])

        init.poll(0.0)
        events, request = init.poll(1.0)

        self.assertEqual(events[0].event, "failed")
        self.assertIsNone(request)
        self.assertTrue(init.failed)
        self.assertEqual(init.summary()["state"], "failed")

        events, request = init.poll(2.0)
        self.assertEqual(events, [])
        self.assertIsNone(request)

    def test_required_step_can_recover_after_late_response(self) -> None:
        init = TouchscreenInitStateMachine(steps=[
            InitStep(0x61, required=True, max_attempts=1, retry_interval=1.0),
            InitStep(0x21, required=True),
        ])
        init.poll(0.0)
        init.poll(1.0)

        events = init.observe(response(0x61))

        self.assertEqual(events[0].event, "recovered")
        self.assertFalse(init.failed)
        self.assertEqual(init.current_index, 1)

    def test_finished_emits_once(self) -> None:
        init = TouchscreenInitStateMachine(steps=[InitStep(0x21)])
        init.poll(0.0)

        events = init.observe(response(0x21))
        self.assertEqual([event.event for event in events], ["complete", "finished"])
        events, request = init.poll(1.0)

        self.assertEqual(events, [])
        self.assertIsNone(request)


if __name__ == "__main__":
    unittest.main()
