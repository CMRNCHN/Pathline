import json

from typer.testing import CliRunner

from ivr_assessor.call_template import InjectionMode, TemplateStyle, build_call_template_plan
from ivr_assessor.cli import app


runner = CliRunner()


def test_build_call_template_plan_defaults_to_dtmf() -> None:
    plan = build_call_template_plan(
        target_number="+15555550123",
        fields={"card_number": "placeholder"},
    )

    assert plan.default_mode == InjectionMode.DTMF
    assert plan.style == TemplateStyle.PRO_AUDIO_WORKSTATION
    assert plan.fields[0].key == "phone_number"
    assert plan.fields[1].mode == InjectionMode.DTMF
    assert [step.action for step in plan.steps] == ["send_dtmf", "beep", "send_dtmf"]


def test_build_call_template_plan_supports_mixed_mode() -> None:
    plan = build_call_template_plan(
        target_number="+15555550123",
        fields={"zip_code": "placeholder"},
        default_mode=InjectionMode.MIXED,
        style=TemplateStyle.NODE_BASED_VISUAL_IVR_EDITOR,
    )

    assert plan.default_mode == InjectionMode.MIXED
    assert plan.style == TemplateStyle.NODE_BASED_VISUAL_IVR_EDITOR
    assert [field.mode for field in plan.fields] == [InjectionMode.MIXED, InjectionMode.MIXED]
    assert [step.action for step in plan.steps] == ["send_dtmf", "speak", "beep"]


def test_call_template_command_outputs_json_plan() -> None:
    result = runner.invoke(
        app,
        [
            "call-template",
            "--target-number",
            "+15555550123",
            "--field",
            "card_number=placeholder",
            "--field",
            "zip_code=placeholder",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["default_mode"] == "dtmf"
    assert payload["style"] == "pro_audio_workstation"
    assert payload["fields"][1]["key"] == "card_number"
    assert payload["steps"][1]["action"] == "beep"


def test_call_template_command_accepts_style_override() -> None:
    result = runner.invoke(
        app,
        [
            "call-template",
            "--target-number",
            "+15555550123",
            "--style",
            "node_based_visual_ivr_editor",
            "--field",
            "zip_code=placeholder",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["style"] == "node_based_visual_ivr_editor"
