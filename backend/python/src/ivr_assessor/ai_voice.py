from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .call_template import TemplateStyle


@dataclass(frozen=True)
class VoiceGenerationSpec:
    text: str
    voice: str = os.environ.get("OPENAI_TTS_VOICE", "cedar")
    model: str = "gpt-4o-mini-tts"
    style: TemplateStyle = TemplateStyle.PRO_AUDIO_WORKSTATION
    response_format: str = "wav"
    instructions: str | None = None

    def build_instructions(self) -> str:
        style_guidance = {
            TemplateStyle.PRO_AUDIO_WORKSTATION: "Clear, precise, production-ready.",
            TemplateStyle.CLEAN_SAAS_FLOW_BUILDER: "Clean, calm, and easy to follow.",
            TemplateStyle.NODE_BASED_VISUAL_IVR_EDITOR: "Technical, structured, and concise.",
        }[self.style]

        content_guidance = infer_content_guidance(self.text)

        parts = [
            f"Style: {style_guidance}",
            f"Tone: {content_guidance['tone']}",
            f"Pacing: {content_guidance['pacing']}",
            f"Pronunciation: {content_guidance['pronunciation']}",
        ]
        if content_guidance["pauses"]:
            parts.append(f"Pauses: {content_guidance['pauses']}")
        if self.instructions:
            parts.append(self.instructions.strip())
        return "\n".join(parts)


def infer_content_guidance(text: str) -> dict[str, str]:
    normalized = " ".join(text.split())
    lowered = normalized.lower()
    has_ivr_cues = any(
        cue in lowered
        for cue in (
            "press ",
            "enter ",
            "account number",
            "zip code",
            "social security",
            "security code",
            "verification code",
            "date of birth",
            "recorded",
        )
    )
    sensitive_cues = (
        "account number",
        "zip code",
        "social security",
        "security code",
        "verification code",
        "date of birth",
    )
    has_sensitive_cue = any(cue in lowered for cue in sensitive_cues)
    has_long_digit_run = bool(re.search(r"\d{10,}", normalized))
    has_sensitive_input = has_sensitive_cue or has_long_digit_run
    has_digits = bool(re.search(r"\d", normalized))
    has_phone = bool(re.search(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", normalized))
    has_date = bool(re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", normalized))
    has_acronyms = bool(re.search(r"\b[A-Z]{2,}\b", text))

    tone = "warm, conversational, and highly natural, like a real human on a phone call."
    pacing = "casual and fluid, matching the rhythm of a real person speaking."
    pronunciation_notes: list[str] = ["Speak as a human would in a normal phone conversation, blending words naturally."]
    pauses = "Incorporate very subtle, natural micro-pauses where a person normally breathes."

    if has_ivr_cues:
        tone = "helpful, friendly, and human-like."
        pacing = "relaxed but clear, leaving just enough space for the listener to process."
        pronunciation_notes.append("Keep it completely conversational even when asking for input.")
        pauses = "Pause naturally before requested values, like a real person waiting."

    if has_sensitive_input:
        tone = "calm, compliant, and unmistakably clear, treating sensitive values with care."
        pacing = "measured, with deliberate spacing around each requested input so the caller can keep up."
        pauses = "Pause briefly before and after each requested value."

    if has_phone or has_date:
        pronunciation_notes.append("Read numbers carefully and group them in the most natural spoken units.")
    if has_digits:
        pronunciation_notes.append("Read digits distinctly, with clear grouping for codes and account numbers.")
    if has_acronyms:
        pronunciation_notes.append("Spell acronyms letter by letter.")

    return {
        "tone": tone,
        "pacing": pacing,
        "pronunciation": " ".join(pronunciation_notes),
        "pauses": pauses,
    }


def generate_voice_file(
    spec: VoiceGenerationSpec,
    output_path: Path,
    *,
    client: object | None = None,
) -> Path:
    if client is None:
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "openai is not installed. Install the package or use a virtualenv with the dependency available."
            ) from exc

        api = OpenAI()
    else:
        api = client

    result = api.audio.speech.create(
        model=spec.model,
        voice=spec.voice,
        input=spec.text,
        instructions=spec.build_instructions(),
        response_format=spec.response_format,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.stream_to_file(str(output_path))
    return output_path
