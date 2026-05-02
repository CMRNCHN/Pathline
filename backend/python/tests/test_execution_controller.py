from ivr_assessor.execution_controller import ExecutionController


def test_execution_controller_refuses_unapproved_target() -> None:
    controller = ExecutionController(allowlist=["+15555550100"])

    assert controller.can_dial("+15555550100") is True
    assert controller.can_dial("+15555550101") is False
