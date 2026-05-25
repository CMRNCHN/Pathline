from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class ConfidentSegment:
    text: str
    raw_text: str
    start_time: float
    end_time: float
    confidence: float  # 0–1, estimated
    is_final: bool
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        return asdict(self)


class TranscriptProcessor:
    """
    Post-process Whisper output: normalize amounts, detect low confidence,
    add metadata for IVR decision-making.
    """

    def __init__(self, confidence_threshold: float = 0.8):
        self.confidence_threshold = confidence_threshold

    def process(
        self,
        text: str,
        start_time: float,
        end_time: float,
        mlx_result: dict[str, Any] | None = None,
    ) -> ConfidentSegment:
        raw_text = text
        confidence = self._estimate_confidence(text, mlx_result)
        metadata = {}

        amounts = self._parse_amounts(text)
        if amounts:
            metadata["amounts"] = amounts
            text = self._normalize_amounts(text)

        dtmf = self._detect_dtmf_spoken(text)
        if dtmf:
            metadata["dtmf"] = dtmf

        requires_confirmation = confidence < self.confidence_threshold
        metadata["requires_confirmation"] = requires_confirmation

        return ConfidentSegment(
            text=text,
            raw_text=raw_text,
            start_time=start_time,
            end_time=end_time,
            confidence=confidence,
            is_final=False,
            metadata=metadata,
        )

    @staticmethod
    def _estimate_confidence(text: str, mlx_result: dict | None) -> float:
        if not text or len(text) < 2:
            return 0.0

        score = 0.85

        if len(text) < 5:
            score -= 0.15
        if text.isupper():
            score -= 0.1
        if len(set(text)) < len(text) * 0.3:
            score -= 0.15

        return max(0.0, min(1.0, score))

    @staticmethod
    def _parse_amounts(text: str) -> list[dict]:
        patterns = [
            (r"\$?\d+\.?\d*", "numeric"),
            (r"(one|two|three|four|five|six|seven|eight|nine|zero|ten|eleven|twelve|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)\s+(dollars?|cents?)", "spoken"),
        ]
        amounts = []
        for pattern, kind in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                amounts.append({"text": match.group(), "kind": kind, "span": match.span()})
        return amounts

    @staticmethod
    def _normalize_amounts(text: str) -> str:
        replacements = {
            r"twelve\s+fifty": "$12.50",
            r"twenty\s+five": "$25.00",
        }
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def _detect_dtmf_spoken(text: str) -> list[str]:
        dtmf_map = {
            r"\b(one|1)\b": "1",
            r"\b(two|2)\b": "2",
            r"\b(three|3)\b": "3",
            r"\b(four|4)\b": "4",
            r"\b(five|5)\b": "5",
            r"\b(six|6)\b": "6",
            r"\b(seven|7)\b": "7",
            r"\b(eight|8)\b": "8",
            r"\b(nine|9)\b": "9",
            r"\b(zero|0)\b": "0",
            r"\b(star|asterisk|\*)\b": "*",
            r"\b(pound|hash|#)\b": "#",
        }
        detected = []
        for pattern, digit in dtmf_map.items():
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(digit)
        return detected
