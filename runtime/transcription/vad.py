from __future__ import annotations

import numpy as np
from collections import deque

import webrtcvad


class VoiceActivityDetector:
    """
    webrtcvad wrapper. Filters silence, yields only speech frames.
    Modes: 0=most permissive, 3=most aggressive (default 2).
    """

    def __init__(self, mode: int = 2, frame_duration_ms: int = 20):
        self.vad = webrtcvad.Vad(mode)
        self.frame_duration_ms = frame_duration_ms
        self.sample_rate = 16000
        self.frame_size = int(self.sample_rate * frame_duration_ms / 1000)

    def is_speech(self, pcm16_chunk: bytes) -> bool:
        """Return True if chunk contains speech."""
        return self.vad.is_speech(pcm16_chunk, self.sample_rate)

    def filter_silence(self, pcm16_chunk: bytes) -> bytes | None:
        """Return chunk if speech, else None."""
        if self.is_speech(pcm16_chunk):
            return pcm16_chunk
        return None


class SpeechBuffer:
    """
    Accumulate speech frames until silence detected.
    Yields complete utterances (speech + trailing silence margin).
    """

    def __init__(self, vad: VoiceActivityDetector, silence_threshold: int = 3):
        self.vad = vad
        self.silence_threshold = silence_threshold
        self.buffer = deque()
        self.silence_frames = 0
        self.in_speech = False

    def feed(self, pcm16_chunk: bytes) -> bytes | None:
        """Feed a chunk. Return complete utterance if one ended, else None."""
        is_speech = self.vad.is_speech(pcm16_chunk)

        if is_speech:
            self.silence_frames = 0
            self.in_speech = True
            self.buffer.append(pcm16_chunk)
            return None

        if self.in_speech:
            self.silence_frames += 1
            if self.silence_frames < self.silence_threshold:
                self.buffer.append(pcm16_chunk)
                return None
            else:
                utterance = b"".join(self.buffer)
                self.buffer.clear()
                self.silence_frames = 0
                self.in_speech = False
                return utterance

        return None
