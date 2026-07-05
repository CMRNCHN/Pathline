"""Call script schema and IVR navigator.

Navigation is phrase-triggered (not timer-driven). Timeouts are a last-resort fallback.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class TimingConfig(BaseModel):
    silence_after_prompt_ms: int = 800
    max_listen_ms: int = 30_000
    timeout_fallback_ms: int = 20_000


class PhraseAction(BaseModel):
    """When the IVR says something matching `hear`, send DTMF and move on."""

    hear: list[str]
    send: str | None = None
    goto: str | None = None
    capture: str | None = None
    note: str | None = None


class StateConfig(BaseModel):
    id: str | None = None
    listen: bool = True
    when: list[PhraseAction] = Field(default_factory=list)
    on_unknown: Literal["discover", "fail", "wait"] = "discover"
    terminal: bool = False


class CallScript(BaseModel):
    id: str
    version: int = 1
    name: str
    target: str | None = None
    secrets: list[str] = Field(default_factory=list)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    start_at: str
    states: dict[str, StateConfig]

    def get_state(self, state_id: str) -> StateConfig:
        state = self.states.get(state_id)
        if state is None:
            raise KeyError(f"Unknown state: {state_id}")
        return state


class NavigationAction(BaseModel):
    type: Literal["send_dtmf", "capture", "goto", "discover", "done", "fail", "wait"]
    state: str
    send: str | None = None
    resolved_send: str | None = None
    capture_key: str | None = None
    matched_phrase: str | None = None
    matched_hear: str | None = None
    transcript: str


class IVRNavigator:
    """Phrase-driven navigator with incremental discover support."""

    def __init__(self, script: CallScript, secrets: dict[str, str] | None = None):
        self.script = script
        self.secrets = secrets or {}
        self.current_state = script.start_at
        self.captured: dict[str, str] = {}
        self.history: list[dict[str, Any]] = []
        self._pending_transcript = ""

    def feed_transcript(self, text: str) -> list[NavigationAction]:
        """Process new transcript text (append-only from STT)."""
        self._pending_transcript = f"{self._pending_transcript} {text}".strip().lower()
        return self._evaluate()

    def feed_transcript_replace(self, text: str) -> list[NavigationAction]:
        """Replace buffer — use when submitting a full manual transcript."""
        self._pending_transcript = text.strip().lower()
        return self._evaluate()

    def _evaluate(self) -> list[NavigationAction]:
        actions: list[NavigationAction] = []
        transcript = self._pending_transcript

        while True:
            state_cfg = self.script.get_state(self.current_state)

            if state_cfg.terminal:
                actions.append(NavigationAction(
                    type="done", state=self.current_state, transcript=transcript
                ))
                return actions

            match = self._match_phrase(state_cfg, transcript)
            if match is None:
                if state_cfg.on_unknown == "discover":
                    actions.append(NavigationAction(
                        type="discover", state=self.current_state, transcript=transcript
                    ))
                elif state_cfg.on_unknown == "fail":
                    actions.append(NavigationAction(
                        type="fail", state=self.current_state, transcript=transcript
                    ))
                else:
                    actions.append(NavigationAction(
                        type="wait", state=self.current_state, transcript=transcript
                    ))
                return actions

            phrase_action, matched_hear = match
            self.history.append({
                "state": self.current_state,
                "hear": matched_hear,
                "transcript": transcript,
            })

            if phrase_action.send is not None:
                resolved = resolve_send(phrase_action.send, self.secrets)
                actions.append(NavigationAction(
                    type="send_dtmf",
                    state=self.current_state,
                    send=phrase_action.send,
                    resolved_send=resolved,
                    matched_phrase=phrase_action.hear[0],
                    matched_hear=matched_hear,
                    transcript=transcript,
                ))

            if phrase_action.capture:
                self.captured[phrase_action.capture] = transcript
                actions.append(NavigationAction(
                    type="capture",
                    state=self.current_state,
                    capture_key=phrase_action.capture,
                    matched_hear=matched_hear,
                    transcript=transcript,
                ))

            if phrase_action.goto:
                self.current_state = phrase_action.goto
                self._pending_transcript = ""
                actions.append(NavigationAction(
                    type="goto",
                    state=self.current_state,
                    matched_hear=matched_hear,
                    transcript=transcript,
                ))
                continue

            return actions

    def _match_phrase(
        self, state_cfg: StateConfig, transcript: str
    ) -> tuple[PhraseAction, str] | None:
        for action in state_cfg.when:
            for phrase in action.hear:
                if phrase_matches(transcript, phrase):
                    return action, phrase
        return None

    def add_mapping(
        self,
        state_id: str,
        hear: list[str],
        send: str | None = None,
        goto: str | None = None,
        capture: str | None = None,
        note: str | None = None,
    ) -> PhraseAction:
        """Discover mode: append a new phrase mapping to a state."""
        state = self.script.get_state(state_id)
        entry = PhraseAction(hear=hear, send=send, goto=goto, capture=capture, note=note)
        state.when.append(entry)
        return entry

    def retry_after_discover(self) -> list[NavigationAction]:
        """Re-evaluate transcript after user adds a mapping."""
        return self._evaluate()


def phrase_matches(transcript: str, phrase: str) -> bool:
    """Fuzzy phrase match — substring with normalized whitespace."""
    normalized = " ".join(transcript.lower().split())
    needle = " ".join(phrase.lower().split())
    if needle in normalized:
        return True
    # Allow flexible spacing in short phrases
    pattern = re.escape(needle).replace(r"\ ", r"\s+")
    return bool(re.search(pattern, normalized))


def resolve_send(template: str, secrets: dict[str, str]) -> str:
    """Expand {secret_name} placeholders into DTMF digit string."""

    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in secrets:
            raise KeyError(f"Missing secret for DTMF template: {key}")
        return secrets[key]

    return re.sub(r"\{(\w+)\}", replacer, template)


def load_call_script(path: str | Path) -> CallScript:
    data = yaml.safe_load(Path(path).read_text())
    return CallScript.model_validate(data)
