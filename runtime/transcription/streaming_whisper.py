from __future__ import annotations

import asyncio
import numpy as np
from collections import deque
from dataclasses import dataclass
from typing import AsyncGenerator

import mlx_whisper

from runtime.transcription.vad import VoiceActivityDetector, SpeechBuffer
from runtime.transcription.confidence import TranscriptProcessor, ConfidentSegment


@dataclass
class TranscriptSegment:
    text: str
    raw_text: str
    start_time: float
    end_time: float
    confidence: float
    is_final: bool
    metadata: dict


class StreamingWhisperTranscriber:
    DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
    SAMPLE_RATE = 16000
    SEGMENT_DURATION = 2.0
    OVERLAP = 0.5

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        language: str = "en",
        initial_prompt: str | None = None,
        use_vad: bool = True,
        confidence_threshold: float = 0.8,
    ):
        self.model = model
        self.language = language
        self.initial_prompt = initial_prompt
        self.use_vad = use_vad
        self.vad = VoiceActivityDetector(mode=2) if use_vad else None
        self.speech_buffer = SpeechBuffer(self.vad) if use_vad else None
        self.processor = TranscriptProcessor(confidence_threshold=confidence_threshold)
        self._warm()

    def _warm(self) -> None:
        silence = np.zeros(16000, dtype=np.float32)
        mlx_whisper.transcribe(
            silence,
            path_or_hf_repo=self.model,
            language=self.language,
            verbose=False,
        )

    async def stream_transcribe(
        self,
        audio_chunks: AsyncGenerator[bytes, None],
    ) -> AsyncGenerator[ConfidentSegment, None]:
        """Consume PCM-16 chunks, yield confident segments."""
        loop = asyncio.get_event_loop()
        buffer = deque()
        total_samples = 0
        last_transcribed_samples = 0
        segment_sample_count = int(self.SAMPLE_RATE * self.SEGMENT_DURATION)
        overlap_samples = int(self.SAMPLE_RATE * self.OVERLAP)

        async for chunk in audio_chunks:
            if self.use_vad and self.speech_buffer:
                utterance = self.speech_buffer.feed(chunk)
                if utterance is None:
                    continue
                chunk = utterance

            samples = (
                np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
            )
            buffer.append(samples)
            total_samples += len(samples)

            if total_samples - last_transcribed_samples >= segment_sample_count:
                audio = np.concatenate(buffer)
                start_idx = max(0, total_samples - segment_sample_count - overlap_samples)
                transcribe_audio = audio[start_idx : start_idx + segment_sample_count]

                result = await loop.run_in_executor(
                    None,
                    self._transcribe_blocking,
                    transcribe_audio,
                )

                if result["text"].strip():
                    start_time = last_transcribed_samples / self.SAMPLE_RATE
                    end_time = (
                        (last_transcribed_samples + segment_sample_count)
                        / self.SAMPLE_RATE
                    )
                    confident_segment = self.processor.process(
                        result["text"].strip(),
                        start_time,
                        end_time,
                        result,
                    )
                    yield confident_segment

                last_transcribed_samples += segment_sample_count - overlap_samples
                buffer.clear()

        if buffer:
            audio = np.concatenate(buffer)
            result = await loop.run_in_executor(
                None,
                self._transcribe_blocking,
                audio,
            )
            if result["text"].strip():
                start_time = last_transcribed_samples / self.SAMPLE_RATE
                end_time = total_samples / self.SAMPLE_RATE
                confident_segment = self.processor.process(
                    result["text"].strip(),
                    start_time,
                    end_time,
                    result,
                )
                confident_segment.is_final = True
                yield confident_segment

    def _transcribe_blocking(self, audio: np.ndarray) -> dict:
        kwargs = {
            "path_or_hf_repo": self.model,
            "language": self.language,
            "word_timestamps": False,
            "verbose": False,
            "condition_on_previous_text": False,
        }
        if self.initial_prompt:
            kwargs["initial_prompt"] = self.initial_prompt
        return mlx_whisper.transcribe(audio, **kwargs)
