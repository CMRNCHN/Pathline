import unittest
from unittest.mock import MagicMock, patch
from ivr_assessor.testing.telecom_test_plan import TelecomTestPlan
from ivr_assessor.testing.safety_guards import SafetyGuards
from ivr_assessor.events.event_types import EventType

class TestSafetyGuards(unittest.TestCase):
    def setUp(self):
        self.plan = TelecomTestPlan(
            test_id="test-123",
            name="Test Plan",
            target_label="Target",
            target_number_ref="REF1",
            max_duration_seconds=10,
            max_depth=5,
            max_dtmf_actions=3
        )
        self.guards = SafetyGuards(self.plan, "session-456")

    @patch('ivr_assessor.events.event_bus.EventBus.publish')
    def test_duration_guard(self, mock_publish):
        self.guards.start_time = 0 # Force old start time
        self.assertFalse(self.guards.check_duration())
        self.assertTrue(self.guards.triggered)
        self.assertEqual(self.guards.reason, "duration exceeded")
        mock_publish.assert_called_once()
        self.assertEqual(mock_publish.call_args[0][0].type, EventType.SAFETY_GUARD_TRIGGERED)

    @patch('ivr_assessor.events.event_bus.EventBus.publish')
    def test_dtmf_guard(self, mock_publish):
        self.assertTrue(self.guards.check_dtmf(2))
        self.assertFalse(self.guards.check_dtmf(4))
        self.assertTrue(self.guards.triggered)
        self.assertEqual(self.guards.reason, "dtmf limit exceeded")

    @patch('ivr_assessor.events.event_bus.EventBus.publish')
    def test_depth_guard(self, mock_publish):
        self.assertTrue(self.guards.check_depth(3))
        self.assertFalse(self.guards.check_depth(6))
        self.assertTrue(self.guards.triggered)
        self.assertEqual(self.guards.reason, "depth exceeded")

if __name__ == "__main__":
    unittest.main()
