from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class ResponseClip:
    id: str
    label: str
    file_path: Path
    style: str
    duration_ms: int
    tags: tuple[str, ...] = field(default_factory=tuple)


class ResponseLibrary:
    def __init__(self, clips: Sequence[ResponseClip] | None = None) -> None:
        self._clips = list(clips or [])

    @property
    def clips(self) -> list[ResponseClip]:
        return list(self._clips)

    def pick(self, label: str, style: str | None = None) -> ResponseClip:
        # Break ties deterministically so selection never depends on insertion order.
        matches = [
            clip
            for clip in self._clips
            if clip.label == label and (style is None or clip.style == style)
        ]

        if matches:
            return min(matches, key=lambda clip: clip.id)

        raise LookupError(f"No response clip found for label={label!r} style={style!r}")
