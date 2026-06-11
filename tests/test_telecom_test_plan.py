import unittest
from analyst.telecom.telecom_test_plan import TelecomTestPlan
from analyst.telecom.telecom_test_result import TelecomTestResult, TestOutcome

class TestTelecomModels(unittest.TestCase):
    def test_test_plan_serialization(self):
        plan = TelecomTestPlan(
            test_id="test-123",
            name="Test Plan",
            target_label="Target",
            target_number_ref="REF1",
            max_duration_seconds=300,
            max_depth=5,
            max_dtmf_actions=10
        )
        data = plan.to_dict()
        self.assertEqual(data["test_id"], "test-123")
        self.assertEqual(data["max_depth"], 5)
        
        plan2 = TelecomTestPlan.from_dict(data)
        self.assertEqual(plan2.test_id, "test-123")
        self.assertEqual(plan2.max_depth, 5)

    def test_test_result_serialization(self):
        result = TelecomTestResult(
            test_id="test-123",
            session_id="session-456",
            started_at=1000.0,
            outcome=TestOutcome.PASSED
        )
        data = result.to_dict()
        self.assertEqual(data["test_id"], "test-123")
        self.assertEqual(data["outcome"], "PASSED")

if __name__ == "__main__":
    unittest.main()