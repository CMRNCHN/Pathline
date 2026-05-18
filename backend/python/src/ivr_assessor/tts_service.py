# cspell:ignore piper mulaw ulaw ratecv lin2ulaw
"""TTS (Text-to-Speech) service factory.

Reads TTS_BACKEND env var to select the engine:
    piper   (default) — local, free, Piper binary + ONNX voice model
    openai  — cloud, paid, wraps existing ai_voice.py

Both expose the same interface:
    synthesize(text: str) -> bytes   (mulaw 8kHz WAV bytes, Twilio-compatible)

Common IVR phrases are pre-rendered into an LRU cache at warmup() time.

Setup for Piper (local):
    1. Install binary:  brew install piper-tts
       OR download from https://github.com/rhasspy/piper/releases
    2. Download voice:
       curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
       curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
    3. Set PIPER_VOICE=/path/to/en_US-lessac-medium.onnx in .env
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import shutil
import struct
import wave
from collections import OrderedDict

logger = logging.getLogger(__name__)

# Common IVR phrases pre-warmed into the cache at startup.
IVR_WARMUP_PHRASES: list[str] = [
    "yes", "no", "okay", "thank you", "please hold", "please wait",
    "goodbye", "I'm sorry", "one moment please",
    "press one", "press two", "press three", "press four", "press five",
    "press six", "press seven", "press eight", "press nine", "press zero",
    "press star", "press pound",
]


# ─── audioop shim (same as audio_pipeline.py) ────────────────────────────────
try:
    import audioop  # type: ignore[import]
except ModuleNotFoundError:
    try:
        import audioop_lts as audioop  # type: ignore[import,no-redef]
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Neither 'audioop' (stdlib ≤3.12) nor 'audioop-lts' (PyPI) found."
        ) from exc


class PiperNotFoundError(RuntimeError):
    """Raised when the piper binary is not found on PATH or at PIPER_BINARY."""


class _LRUCache:
    """Simple OrderedDict-based LRU cache."""

    def __init__(self, maxsize: int = 200) -> None:
        self._cache: OrderedDict[str, bytes] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> bytes | None:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, key: str, value: bytes) -> None:
        self._cache[key] = value
        self._cache.move_to_end(key)
        while len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    def __len__(self) -> int:
        return len(self._cache)


class PiperTTS:
    """Local TTS using the Piper binary.

    Synthesizes text → WAV via `piper` subprocess, converts to mulaw 8kHz
    for Twilio compatibility. Results are cached by normalized text.

    Env vars:
        PIPER_BINARY  — path to the piper binary (default: auto-detect via PATH)
        PIPER_VOICE   — path to the .onnx voice model file (required)
    """

    def __init__(self, cache_size: int = 200) -> None:
        self._binary = os.getenv("PIPER_BINARY") or shutil.which("piper")
        self._voice = os.getenv("PIPER_VOICE", "")
        self._cache = _LRUCache(maxsize=cache_size)

    def _check_binary(self) -> str:
        if not self._binary:
            raise PiperNotFoundError(
                "piper binary not found. Install with: brew install piper-tts\n"
                "Or set PIPER_BINARY=/path/to/piper in .env"
            )
        return self._binary

    def _check_voice(self) -> str:
        if not self._voice:
            raise PiperNotFoundError(
                "PIPER_VOICE env var not set. Download a voice model and set:\n"
                "  PIPER_VOICE=/path/to/en_US-lessac-medium.onnx"
            )
        return self._voice

    def _cache_key(self, text: str) -> str:
        return text.strip().lower()

    async def synthesize(self, text: str) -> bytes:
        """Return mulaw 8kHz WAV bytes for the given text.

        Raises PiperNotFoundError if piper binary or voice model is missing.
        """
        key = self._cache_key(text)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        binary = self._check_binary()
        voice = self._check_voice()

        wav_bytes = await self._run_piper(binary, voice, text)
        mulaw_bytes = self._wav_to_mulaw8k(wav_bytes)
        self._cache.set(key, mulaw_bytes)
        return mulaw_bytes

    async def _run_piper(self, binary: str, voice: str, text: str) -> bytes:
        """Run piper binary asynchronously, return raw WAV bytes."""
        proc = await asyncio.create_subprocess_exec(
            binary,
            "--model", voice,
            "--output-raw",  # raw PCM on stdout
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(input=text.encode("utf-8"))
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"piper exited {proc.returncode}: {err}")

        # piper --output-raw writes raw PCM (22050Hz, 16-bit, mono by default).
        # Wrap in a minimal WAV header so _wav_to_mulaw8k can parse sample rate.
        sample_rate = int(os.getenv("PIPER_SAMPLE_RATE", "22050"))
        return self._raw_pcm_to_wav(stdout, sample_rate=sample_rate)

    @staticmethod
    def _raw_pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 22050) -> bytes:
        """Wrap raw int16 PCM in a WAV container."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # int16
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        return buf.getvalue()

    @staticmethod
    def _wav_to_mulaw8k(wav_bytes: bytes) -> bytes:
        """Convert WAV (any sample rate, int16, mono) → mulaw 8kHz WAV."""
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            src_rate = wf.getframerate()
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            raw_frames = wf.readframes(wf.getnframes())

        # Mix down to mono if stereo.
        if n_channels == 2:
            samples = struct.unpack(f"<{len(raw_frames)//2}h", raw_frames)
            mono = struct.pack(f"<{len(samples)//2}h", *[
                (samples[i] + samples[i+1]) // 2 for i in range(0, len(samples), 2)
            ])
        else:
            mono = raw_frames

        # Ensure int16 width.
        if sampwidth != 2:
            mono = audioop.lin2lin(mono, sampwidth, 2)

        # Resample to 8kHz.
        if src_rate != 8000:
            mono, _ = audioop.ratecv(mono, 2, 1, src_rate, 8000, None)

        # Encode mulaw.
        return audioop.lin2ulaw(mono, 2)

    async def warmup(self) -> None:
        """Pre-render IVR_WARMUP_PHRASES into cache. Errors are logged but not raised."""
        logger.info("PiperTTS warmup: pre-rendering %d phrases", len(IVR_WARMUP_PHRASES))
        for phrase in IVR_WARMUP_PHRASES:
            try:
                await self.synthesize(phrase)
            except Exception as exc:
                logger.warning("PiperTTS warmup failed for %r: %s", phrase, exc)
        logger.info("PiperTTS warmup complete (%d cached)", len(self._cache))


class OpenAITTS:
    """TTS fallback using OpenAI's gpt-4o-mini-tts (wraps ai_voice.py).

    Used when TTS_BACKEND=openai or as automatic fallback when piper is missing.
    """

    async def synthesize(self, text: str) -> bytes:
        """Return mulaw 8kHz bytes for text. Runs ai_voice in thread pool."""
        from .ai_voice import VoiceGenerationSpec, generate_voice_file  # type: ignore[attr-defined]
        import asyncio
        import pathlib
        import tempfile
        spec = VoiceGenerationSpec(text=text)
        loop = asyncio.get_running_loop()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = pathlib.Path(f.name)
        try:
            await loop.run_in_executor(None, generate_voice_file, spec, tmp)
            wav_bytes = tmp.read_bytes()
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass
        return PiperTTS._wav_to_mulaw8k(wav_bytes)


def create_tts() -> PiperTTS | OpenAITTS:
    """Return the configured TTS engine.

    TTS_BACKEND=piper   → PiperTTS (default)
    TTS_BACKEND=openai  → OpenAITTS
    """
    backend = os.getenv("TTS_BACKEND", "piper").lower()
    if backend == "openai":
        return OpenAITTS()
    return PiperTTS()
