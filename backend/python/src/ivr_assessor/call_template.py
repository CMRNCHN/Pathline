from __future__ import annotations

import math
import wave
from dataclasses import dataclass
from pathlib import Path
from enum import StrEnum
from typing import Mapping
from array import array


class InjectionMode(StrEnum):
    DTMF = "dtmf"
    MIXED = "mixed"


class TemplateStyle(StrEnum):
    PRO_AUDIO_WORKSTATION = "pro_audio_workstation"
    CLEAN_SAAS_FLOW_BUILDER = "clean_saas_flow_builder"
    NODE_BASED_VISUAL_IVR_EDITOR = "node_based_visual_ivr_editor"


class InjectionActionKind(StrEnum):
    SPEAK = "speak"
    SEND_DTMF = "send_dtmf"
    BEEP = "beep"


@dataclass(frozen=True)
class TemplateField:
    key: str
    prompt: str
    value: str
    mode: InjectionMode = InjectionMode.DTMF


@dataclass(frozen=True)
class TemplateStep:
    t_ms: int
    prompt: str
    action: InjectionActionKind
    value: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class CallTemplatePlan:
    target_number: str
    default_mode: InjectionMode
    style: TemplateStyle
    fields: list[TemplateField]
    steps: list[TemplateStep]

    def as_dict(self) -> dict[str, object]:
        return {
            "target_number": self.target_number,
            "default_mode": self.default_mode.value,
            "style": self.style.value,
            "fields": [
                {
                    "key": field.key,
                    "prompt": field.prompt,
                    "value": field.value,
                    "mode": field.mode.value,
                }
                for field in self.fields
            ],
            "steps": [
                {
                    "t_ms": step.t_ms,
                    "prompt": step.prompt,
                    "action": step.action.value,
                    "value": step.value,
                    "note": step.note,
                }
                for step in self.steps
            ],
        }

    def to_text(self) -> str:
        lines = [
            f"target_number: {self.target_number}",
            f"default_mode: {self.default_mode.value}",
            f"style: {self.style.value}",
            "fields:",
        ]
        for field in self.fields:
            lines.append(
                f"  - key: {field.key}, prompt: {field.prompt}, value: {field.value}, mode: {field.mode.value}"
            )
        lines.append("steps:")
        for step in self.steps:
            lines.append(
                f"  - t_ms: {step.t_ms}, action: {step.action.value}, prompt: {step.prompt}, value: {step.value}, note: {step.note}"
            )
        return "\n".join(lines)

    def render_beep_wav(self, output_path: Path, sample_rate: int = 44100) -> Path:
        frames = array("h")

        def append_silence(duration_ms: int) -> None:
            frames.extend([0] * int(sample_rate * (duration_ms / 1000.0)))

        def append_beep(duration_ms: int, frequency: float = 880.0, volume: float = 0.25) -> None:
            sample_count = int(sample_rate * (duration_ms / 1000.0))
            for index in range(sample_count):
                sample = int(volume * 32767 * math.sin(2 * math.pi * frequency * (index / sample_rate)))
                frames.append(sample)

        timeline = 0
        for step in self.steps:
            if step.t_ms > timeline:
                append_silence(step.t_ms - timeline)
                timeline = step.t_ms

            if step.action == InjectionActionKind.BEEP:
                append_beep(250)
                timeline += 250
            elif step.action == InjectionActionKind.SEND_DTMF:
                append_beep(120, frequency=941.0)
                append_silence(30)
                append_beep(120, frequency=941.0)
                timeline += 270
            else:
                append_silence(250)
                timeline += 250

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(frames.tobytes())

        return output_path


def build_call_template_plan(
    target_number: str,
    fields: Mapping[str, str],
    *,
    default_mode: InjectionMode = InjectionMode.DTMF,
    style: TemplateStyle = TemplateStyle.PRO_AUDIO_WORKSTATION,
    mode_overrides: Mapping[str, InjectionMode] | None = None,
) -> CallTemplatePlan:
    overrides = dict(mode_overrides or {})
    normalized_fields: list[TemplateField] = []
    steps: list[TemplateStep] = []
    current_time_ms = 0

    normalized_fields.append(
        TemplateField(
            key="phone_number",
            prompt="Dial target number",
            value=target_number,
            mode=default_mode,
        )
    )
    steps.append(
        TemplateStep(
            t_ms=current_time_ms,
            prompt="Dial target number",
            action=InjectionActionKind.SEND_DTMF,
            value=target_number,
            note="Outbound call target",
        )
    )
    current_time_ms += 1000

    for key, value in fields.items():
        mode = overrides.get(key, default_mode)
        normalized_fields.append(
            TemplateField(
                key=key,
                prompt=key.replace("_", " ").strip(),
                value=value,
                mode=mode,
            )
        )

        if mode == InjectionMode.DTMF:
            steps.append(
                TemplateStep(
                    t_ms=current_time_ms,
                    prompt=f"Inject {key}",
                    action=InjectionActionKind.BEEP,
                    value="***",
                    note=f"DTMF placeholder for {key}",
                )
            )
            steps.append(
                TemplateStep(
                    t_ms=current_time_ms + 250,
                    prompt=f"Inject {key}",
                    action=InjectionActionKind.SEND_DTMF,
                    value=value,
                    note=f"Send DTMF value for {key}",
                )
            )
        else:
            steps.append(
                TemplateStep(
                    t_ms=current_time_ms,
                    prompt=f"Inject {key}",
                    action=InjectionActionKind.SPEAK,
                    value=value,
                    note=f"Spoken injection for {key}",
                )
            )
            steps.append(
                TemplateStep(
                    t_ms=current_time_ms + 250,
                    prompt=f"Inject {key}",
                    action=InjectionActionKind.BEEP,
                    value="***",
                    note=f"Beep marker for {key}",
                )
            )

        current_time_ms += 1250

    return CallTemplatePlan(
        target_number=target_number,
        default_mode=default_mode,
        style=style,
        fields=normalized_fields,
        steps=steps,
    )


def parse_mode_overrides(entries: list[str]) -> dict[str, InjectionMode]:
    overrides: dict[str, InjectionMode] = {}
    for item in entries:
        if "=" not in item:
            raise ValueError(f"Invalid mode override entry: {item!r}. Expected key=dtmf|mixed.")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid mode override entry: {item!r}. Expected key=dtmf|mixed.")
        try:
            overrides[key] = InjectionMode(value.strip())
        except ValueError as exc:
            raise ValueError(f"Unsupported mode in override: {item!r}. Use dtmf or mixed.") from exc
    return overrides
