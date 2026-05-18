# cspell:ignore faster-whisper whisper ctranslate logprob
"""STT (Speech-to-Text) service factory.

Reads STT_BACKEND env var to select the transcriber:
    faster-whisper  (default) — local, free, runs on CPU or GPU
    deepgram        — cloud, paid, real-time streaming
    simulated       — deterministic transcript script for runtime validation

Both transcribers expose the same interface:
    connect() -> bool
    process_audio(pcm_bytes: bytes) -> None  (async)
    close() -> None  (async)
    stats() -> dict
    INPUT_FORMAT: str  — "pcm16_16k" | "mulaw_8k"

Swap by setting STT_BACKEND in .env — no other code changes required.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import math
import os
import time
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "small.en"
_DEFAULT_CONFIDENCE_MIN = 0.6
_SIMULATED_TRANSCRIPT_SCRIPT: tuple[tuple[str, bool, bool], ...] = (
    ("a", True, True),
    ("press 1 for billing", True, True),
    ("press 1 for billing", True, True),
    ("representative", True, True),
)


def create_transcriber(
    on_transcript: Callable[[str, bool, bool], None] | None = None,
    on_status: Callable[[str], None] | None = None,
) -> Any:
    """Return the configured STT transcriber.

    STT_BACKEND=faster-whisper  → FasterWhisperTranscriber (default)
    STT_BACKEND=deepgram        → DeepgramTranscriber
    STT_BACKEND=simulated       → SimulatedTranscriber
    """
    backend = os.getenv("STT_BACKEND", "faster-whisper").lower()
    if backend == "deepgram":
        from .transcription import DeepgramTranscriber
        return DeepgramTranscriber(on_transcript=on_transcript, on_status=on_status)
    if backend == "simulated":
        return SimulatedTranscriber(on_transcript=on_transcript, on_status=on_status)
    return FasterWhisperTranscriber(on_transcript=on_transcript, on_status=on_status)


class SimulatedTranscriber:
    """Deterministic transcript emitter for downstream runtime validation."""

    INPUT_FORMAT = "mulaw_8k"

    def __init__(
        self,
        on_transcript: Callable[[str, bool, bool], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        script: tuple[tuple[str, bool, bool], ...] | None = None,
    ) -> None:
        self.on_transcript = on_transcript
        self.on_status = on_status
        self._script = script or _SIMULATED_TRANSCRIPT_SCRIPT
        self._connected = False
        self._closed = False
        self._chunks_seen = 0
        self._bytes_seen = 0
        self._transcripts_emitted = 0
        self._next_script_index = 0
        self._connected_at: float | None = None
        self._last_chunk_at: float | None = None
        self._last_transcript_at: float | None = None

    def _notify(self, msg: str) -> None:
        if self.on_status:
            try:
                self.on_status(msg)
            except Exception as exc:
                logger.error("on_status callback raised: %s", exc)

    async def connect(self) -> bool:
        self._connected = True
        self._closed = False
        self._connected_at = time.monotonic()
        self._notify(
            f"[simulated-stt] ready — deterministic script with {len(self._script)} transcript events"
        )
        return True

    async def process_audio(self, pcm_bytes: bytes) -> None:
        self._chunks_seen += 1
        self._bytes_seen += len(pcm_bytes)
        self._last_chunk_at = time.monotonic()
        if not self._connected or self._next_script_index >= len(self._script):
            return
        text, is_final, speech_final = self._script[self._next_script_index]
        self._next_script_index += 1
        self._transcripts_emitted += 1
        self._last_transcript_at = time.monotonic()
        if self.on_transcript:
            try:
                self.on_transcript(text, is_final, speech_final)
            except Exception as exc:
                logger.error("on_transcript callback raised: %s", exc, exc_info=True)

    async def close(self) -> None:
        self._connected = False
        self._closed = True

    def stats(self) -> dict[str, Any]:
        return {
            "backend": "simulated",
            "connected": self._connected,
            "closed": self._closed,
            "chunks_seen": self._chunks_seen,
            "bytes_seen": self._bytes_seen,
            "transcripts_emitted": self._transcripts_emitted,
            "script_length": len(self._script),
            "script_index": self._next_script_index,
            "last_chunk_at": self._last_chunk_at,
            "last_transcript_at": self._last_transcript_at,
            "connected_at": self._connected_at,
        }


class FasterWhisperTranscriber:
    """Local real-time-ish transcriber using faster-whisper (CTranslate2).

    Audio contract:
        process_audio() receives complete utterances (PCM16 16kHz bytes)
        already segmented by VoiceActivityDetector — NOT raw streaming frames.
        Each call is one utterance; the result is emitted as a single
        (text, is_final=True, speech_final=True) callback.

    Latency profile (CPU, small.en):
        2-3s utterance + 300ms VAD silence + ~500ms inference ≈ 3-4s total.
        Acceptable for IVR — the caller has already finished speaking.

    GPU acceleration:
        WHISPER_DEVICE=cuda  +  pip install "ctranslate2[cuda]"
        WHISPER_COMPUTE_TYPE=float16   (vs default int8 on CPU)
    """

    INPUT_FORMAT = "pcm16_16k"

    def __init__(
        self,
        on_transcript: Callable[[str, bool, bool], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        model_size: str | None = None,
        beam_size: int = 1,
        best_of: int = 1,
        language: str = "en",
        device: str | None = None,
        compute_type: str | None = None,
        confidence_min: float | None = None,
    ) -> None:
        self.on_transcript = on_transcript
        self.on_status = on_status

        self._model_size = model_size or os.getenv("WHISPER_MODEL", _DEFAULT_MODEL)
        self._beam_size = beam_size
        self._best_of = best_of
        self._language = language
        self._device = device or os.getenv("WHISPER_DEVICE", "cpu")
        self._compute_type = compute_type or os.getenv(
            "WHISPER_COMPUTE_TYPE",
            "float16" if self._device == "cuda" else "int8",
        )
        self._confidence_min = confidence_min or float(
            os.getenv("WHISPER_CONFIDENCE_MIN", str(_DEFAULT_CONFIDENCE_MIN))
        )
        self._download_root = os.getenv("WHISPER_DOWNLOAD_ROOT")
        self._model_path_override = os.getenv("WHISPER_MODEL_PATH", "").strip()
        self._local_files_only = os.getenv("WHISPER_LOCAL_FILES_ONLY", "").lower() in {
            "1", "true", "yes", "on",
        }

        self._model: Any = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=20)
        self._worker_task: asyncio.Task[None] | None = None

        # Diagnostics
        self._utterances_queued = 0
        self._transcripts_emitted = 0
        self._transcripts_dropped_confidence = 0
        self._connect_time: float | None = None
        self._total_inference_ms = 0.0
        self._last_connect_ms = 0.0
        self._last_inference_ms = 0.0
        self._max_queue_size_seen = 0
        self._utterances_dropped_queue_full = 0
        self._last_enqueue_at: float | None = None
        self._last_dequeue_at: float | None = None
        self._last_transcript_at: float | None = None
        self._model_source = ""
        self._resolved_model_target = ""
        self._expected_hf_cache_dir = self._compute_expected_hf_cache_dir()

    def _notify(self, msg: str) -> None:
        logger.debug("notify: %s", msg)
        if self.on_status:
            try:
                self.on_status(msg)
            except Exception as exc:
                logger.error("on_status callback raised: %s", exc)

    async def connect(self) -> bool:
        """Load the Whisper model in a thread pool (non-blocking)."""
        self._notify(
            f"[faster-whisper] loading model {self._resolved_model_label()!r} "
            f"on {self._device} ({self._compute_type})…"
        )
        t0 = time.monotonic()
        loop = asyncio.get_running_loop()
        try:
            self._model = await loop.run_in_executor(
                self._executor, self._load_model_sync
            )
        except Exception as exc:
            self._notify(f"[faster-whisper] model load failed: {exc}")
            logger.error("FasterWhisper model load failed: %s", exc, exc_info=True)
            return False

        elapsed_ms = (time.monotonic() - t0) * 1000
        self._connect_time = time.monotonic()
        self._last_connect_ms = elapsed_ms
        self._notify(
            f"[faster-whisper] ✓ model loaded in {elapsed_ms:.0f} ms — ready"
        )
        logger.info(
            "FasterWhisper model %r loaded in %.0f ms (device=%s)",
            self._model_size, elapsed_ms, self._device,
        )

        # Start background worker that drains the utterance queue.
        self._worker_task = asyncio.create_task(self._worker_loop())
        return True

    def _load_model_sync(self) -> Any:
        from faster_whisper import WhisperModel  # type: ignore[import]
        model_target, kwargs = self._resolve_model_target()
        return WhisperModel(
            model_target,
            device=self._device,
            compute_type=self._compute_type,
            **kwargs,
        )

    def _resolve_model_target(self) -> tuple[str, dict[str, Any]]:
        kwargs: dict[str, Any] = {}

        if self._download_root:
            kwargs["download_root"] = self._download_root

        override = self._model_path_override
        if override:
            override_path = Path(override).expanduser()
            model_target = str(override_path)
            self._model_source = "path_override"
            self._resolved_model_target = model_target
            kwargs["local_files_only"] = True
            return model_target, kwargs

        self._model_source = "model_name"
        self._resolved_model_target = self._model_size
        kwargs["local_files_only"] = self._local_files_only
        return self._model_size, kwargs

    def _compute_expected_hf_cache_dir(self) -> str | None:
        if self._model_path_override:
            return None
        try:
            from faster_whisper.utils import _MODELS  # type: ignore[attr-defined]
            from huggingface_hub.constants import HF_HUB_CACHE
        except Exception:
            return None

        repo_id = _MODELS.get(self._model_size)
        if not repo_id:
            return None
        normalized = "models--" + repo_id.replace("/", "--")
        return str(Path(HF_HUB_CACHE) / normalized)

    def _resolved_model_label(self) -> str:
        model_target, _ = self._resolve_model_target()
        return model_target

    async def process_audio(self, pcm_bytes: bytes) -> None:
        """Queue one utterance for transcription (non-blocking)."""
        if self._model is None:
            logger.warning("process_audio called before model is loaded — dropping utterance")
            return
        if self._queue.full():
            # Drop oldest to prevent unbounded back-pressure.
            try:
                dropped = self._queue.get_nowait()
                self._utterances_dropped_queue_full += 1
                logger.warning(
                    "utterance queue full — dropped oldest (%d bytes)", len(dropped or b"")
                )
            except asyncio.QueueEmpty:
                pass
        await self._queue.put(pcm_bytes)
        self._utterances_queued += 1
        self._last_enqueue_at = time.monotonic()
        self._max_queue_size_seen = max(self._max_queue_size_seen, self._queue.qsize())

    async def _worker_loop(self) -> None:
        logger.debug("FasterWhisper worker: starting")
        loop = asyncio.get_running_loop()
        while True:
            pcm_bytes = await self._queue.get()
            self._last_dequeue_at = time.monotonic()
            if pcm_bytes is None:
                break
            try:
                t0 = time.monotonic()
                results = await loop.run_in_executor(
                    self._executor, self._transcribe_sync, pcm_bytes
                )
                elapsed_ms = (time.monotonic() - t0) * 1000
                self._total_inference_ms += elapsed_ms
                self._last_inference_ms = elapsed_ms
                logger.debug(
                    "FasterWhisper inference: %.0f ms, %d segment(s)", elapsed_ms, len(results)
                )
                for text, confidence in results:
                    if confidence < self._confidence_min:
                        self._transcripts_dropped_confidence += 1
                        logger.debug(
                            "transcript dropped (confidence=%.2f < %.2f): %s",
                            confidence, self._confidence_min, text[:60],
                        )
                        continue
                    self._transcripts_emitted += 1
                    self._last_transcript_at = time.monotonic()
                    logger.debug(
                        "transcript #%d (conf=%.2f): %s",
                        self._transcripts_emitted, confidence, text[:80],
                    )
                    if self.on_transcript:
                        try:
                            self.on_transcript(text, True, True)
                        except Exception as exc:
                            logger.error("on_transcript callback raised: %s", exc, exc_info=True)
            except Exception as exc:
                logger.error("FasterWhisper transcription error: %s", exc, exc_info=True)
                self._notify(f"[faster-whisper] transcription error: {exc}")
            finally:
                self._queue.task_done()
        logger.debug("FasterWhisper worker: stopped")

    def _transcribe_sync(self, pcm_bytes: bytes) -> list[tuple[str, float]]:
        """Run Whisper inference synchronously (called in thread pool)."""
        import numpy as np  # type: ignore[import]
        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self._model.transcribe(
            samples,
            beam_size=self._beam_size,
            best_of=self._best_of,
            language=self._language,
            vad_filter=False,  # VAD already done upstream
        )
        results: list[tuple[str, float]] = []
        for seg in segments:
            text = (seg.text or "").strip()
            if not text:
                continue
            confidence = math.exp(max(seg.avg_logprob, -10))
            results.append((text, confidence))
        return results

    async def close(self) -> None:
        """Drain the utterance queue, stop the worker, release the model."""
        logger.debug(
            "FasterWhisper close: utterances_queued=%d transcripts_emitted=%d",
            self._utterances_queued, self._transcripts_emitted,
        )
        # Sentinel stops the worker after all queued utterances are processed.
        await self._queue.put(None)
        if self._worker_task is not None:
            try:
                await asyncio.wait_for(self._worker_task, timeout=30)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._worker_task.cancel()
            self._worker_task = None
        self._executor.shutdown(wait=False)
        self._model = None
        logger.debug("FasterWhisper close: done")

    def stats(self) -> dict[str, Any]:
        avg_latency = (
            self._total_inference_ms / self._transcripts_emitted
            if self._transcripts_emitted > 0
            else 0.0
        )
        return {
            "backend": "faster-whisper",
            "model": self._model_size,
            "model_source": self._model_source or ("path_override" if self._model_path_override else "model_name"),
            "resolved_model_target": self._resolved_model_target or self._resolved_model_label(),
            "download_root": self._download_root,
            "local_files_only": self._local_files_only or bool(self._model_path_override),
            "expected_hf_cache_dir": self._expected_hf_cache_dir,
            "device": self._device,
            "utterances_queued": self._utterances_queued,
            "transcripts_emitted": self._transcripts_emitted,
            "transcripts_dropped_confidence": self._transcripts_dropped_confidence,
            "avg_inference_ms": round(avg_latency, 1),
            "connected": self._model is not None,
            "queue_size": self._queue.qsize(),
            "max_queue_size_seen": self._max_queue_size_seen,
            "utterances_dropped_queue_full": self._utterances_dropped_queue_full,
            "last_connect_ms": round(self._last_connect_ms, 1),
            "last_inference_ms": round(self._last_inference_ms, 1),
            "last_enqueue_at": self._last_enqueue_at,
            "last_dequeue_at": self._last_dequeue_at,
            "last_transcript_at": self._last_transcript_at,
        }