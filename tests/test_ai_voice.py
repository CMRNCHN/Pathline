from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from runtime.media.ai_voice import VoiceGenerationSpec, generate_voice_file
from runtime.state.call_template import TemplateStyle


@dataclass
class FakeSpeechResult:
    output_path: Path | None = None

    def stream_to_file(self, path: str) -> None:
        self.output_path = Path(path)
        self.output_path.write_bytes(b"fake-audio")


class FakeSpeechAPI:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> FakeSpeechResult:
        self.calls.append(kwargs)
        return FakeSpeechResult()


class FakeAudioAPI:
    def __init__(self) -> None:
        self.speech = FakeSpeechAPI()


class FakeClient:
    def __init__(self) -> None:
        self.audio = FakeAudioAPI()


def test_voice_spec_builds_style_instructions() -> None:
    spec = VoiceGenerationSpec(
        text="Hello world",
        style=TemplateStyle.NODE_BASED_VISUAL_IVR_EDITOR,
        instructions="Keep it dry.",
    )

    instructions = spec.build_instructions()

    assert "Technical, structured, and concise." in instructions
    assert "Keep it dry." in instructions


def test_voice_spec_adapts_to_ivr_and_numeric_content() -> None:
    spec = VoiceGenerationSpec(
        text="Welcome to Citicards. Press 1 for billing. Enter 5254750052231448 and ZIP code 91303.",
        style=TemplateStyle.PRO_AUDIO_WORKSTATION,
    )

    instructions = spec.build_instructions()

    assert "calm, compliant, and unmistakably clear" in instructions
    assert "measured, with deliberate spacing around each requested input" in instructions
    assert "Read digits distinctly" in instructions
    assert "Pause briefly before and after each requested value." in instructions


def test_generate_voice_file_calls_openai_and_writes_output(tmp_path: Path) -> None:
    fake_client = FakeClient()
    out = tmp_path / "voice.wav"
    spec = VoiceGenerationSpec(
        text="Hello world",
        style=TemplateStyle.CLEAN_SAAS_FLOW_BUILDER,
    )

    result = generate_voice_file(spec, out, client=fake_client)  # type: ignore[arg-type]

    assert result == out
    assert out.exists()
    assert out.read_bytes() == b"fake-audio"
    assert fake_client.audio.speech.calls[0]["voice"] == "cedar"
    assert fake_client.audio.speech.calls[0]["response_format"] == "wav"