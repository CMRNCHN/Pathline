"""WER (Word Error Rate) + latency benchmark for STT backends.

Loads WAV + ground-truth pairs from a fixtures directory, runs the
configured STT backend, and reports WER and per-utterance latency.

Usage:
    python -m benchmarks.wer_benchmark \\
        --backend faster-whisper \\
        --fixtures backend/python/tests/fixtures/audio/

Each fixture pair:
    call_001.wav   — audio file (any sample rate; will be resampled)
    call_001.txt   — ground truth transcript (plain text, one line)

Outputs:
    - Console table with per-file WER, confidence, latency
    - JSON report written to BENCHMARK_OUTPUT (default: /tmp/wer_report.json)
    - Markdown summary printed to stdout (suitable for CI PR comments)

Generate fixture WAVs from known text (requires TTS_BACKEND=piper or openai):
    python -m benchmarks.wer_benchmark --generate-fixtures \\
        --fixture-texts "press one for billing" "press two for support"
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import math
import os
import re
import struct
import time
import wave
from pathlib import Path
from typing import Any


# ─── Text normalization ────────────────────────────────────────────────────────

_PUNCT_RE = re.compile(r"[^\w\s]")


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return " ".join(_PUNCT_RE.sub("", text.lower()).split())


# ─── WER computation ──────────────────────────────────────────────────────────

def word_error_rate(reference: str, hypothesis: str) -> float:
    """Compute WER between two strings.

    Returns a float in [0, ∞). Values > 1.0 indicate the hypothesis
    is longer than the reference (possible hallucination).
    """
    ref = normalize_text(reference).split()
    hyp = normalize_text(hypothesis).split()

    if not ref:
        return 0.0 if not hyp else float("inf")

    # Dynamic programming edit distance (substitutions, deletions, insertions).
    r, h = len(ref), len(hyp)
    dp = list(range(h + 1))
    for i in range(1, r + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, h + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[j] = prev[j - 1]
            else:
                dp[j] = 1 + min(prev[j], dp[j - 1], prev[j - 1])

    return dp[h] / len(ref)


# ─── Data classes ──────────────────────────────────────────────────────────────

@dataclasses.dataclass
class FileBenchmarkResult:
    filename: str
    reference: str
    hypothesis: str
    wer: float
    confidence: float
    latency_ms: float
    hallucination: bool  # WER > 1.0


@dataclasses.dataclass
class BenchmarkReport:
    backend: str
    model: str
    mean_wer: float
    mean_confidence: float
    mean_latency_ms: float
    results: list[FileBenchmarkResult]

    def as_json(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "model": self.model,
            "mean_wer": round(self.mean_wer, 4),
            "mean_confidence": round(self.mean_confidence, 4),
            "mean_latency_ms": round(self.mean_latency_ms, 1),
            "results": [
                {
                    "filename": r.filename,
                    "reference": r.reference,
                    "hypothesis": r.hypothesis,
                    "wer": round(r.wer, 4),
                    "confidence": round(r.confidence, 4),
                    "latency_ms": round(r.latency_ms, 1),
                    "hallucination": r.hallucination,
                }
                for r in self.results
            ],
        }

    def as_markdown(self) -> str:
        lines = [
            f"## WER Benchmark — {self.backend} ({self.model})",
            "",
            f"| Metric | Value |",
            f"|---|---|",
            f"| Mean WER | {self.mean_wer:.1%} |",
            f"| Mean confidence | {self.mean_confidence:.2f} |",
            f"| Mean latency | {self.mean_latency_ms:.0f} ms |",
            f"| Files tested | {len(self.results)} |",
            "",
            "### Per-file results",
            "",
            "| File | WER | Confidence | Latency (ms) | Hallucination |",
            "|---|---|---|---|---|",
        ]
        for r in self.results:
            flag = "⚠️" if r.hallucination else ""
            lines.append(
                f"| {r.filename} | {r.wer:.1%} | {r.confidence:.2f} "
                f"| {r.latency_ms:.0f} | {flag} |"
            )
        return "\n".join(lines)


# ─── WAV loader ───────────────────────────────────────────────────────────────

def load_wav_as_pcm16_16k(wav_path: Path) -> bytes:
    """Read a WAV file and return PCM16 at 16kHz (mono), ready for Whisper."""
    try:
        import audioop  # type: ignore[import]
    except ModuleNotFoundError:
        import audioop_lts as audioop  # type: ignore[import,no-redef]

    with wave.open(str(wav_path), "rb") as wf:
        src_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())

    # Mix stereo → mono
    if n_channels == 2:
        samples = struct.unpack(f"<{len(raw)//2}h", raw)
        raw = struct.pack(
            f"<{len(samples)//2}h",
            *[(samples[i] + samples[i + 1]) // 2 for i in range(0, len(samples), 2)],
        )

    # Normalize to int16
    if sampwidth != 2:
        raw = audioop.lin2lin(raw, sampwidth, 2)

    # Resample to 16kHz
    if src_rate != 16000:
        raw, _ = audioop.ratecv(raw, 2, 1, src_rate, 16000, None)

    return raw


# ─── Benchmark runner ─────────────────────────────────────────────────────────

class WERBenchmark:
    """Run WER + latency benchmarks against a fixtures directory."""

    def __init__(
        self,
        fixtures_dir: Path,
        backend: str = "faster-whisper",
        model: str | None = None,
    ) -> None:
        self._fixtures_dir = fixtures_dir
        self._backend = backend
        self._model = model or os.environ.get("WHISPER_MODEL", "small.en")

    def _load_pairs(self) -> list[tuple[Path, str]]:
        pairs = []
        for wav in sorted(self._fixtures_dir.glob("*.wav")):
            txt = wav.with_suffix(".txt")
            if txt.exists():
                pairs.append((wav, txt.read_text(encoding="utf-8").strip()))
        if not pairs:
            raise FileNotFoundError(
                f"No .wav + .txt pairs found in {self._fixtures_dir}"
            )
        return pairs

    def _transcribe_faster_whisper(self, pcm_bytes: bytes) -> tuple[str, float]:
        """Return (transcript, confidence). Runs synchronously."""
        import numpy as np
        from faster_whisper import WhisperModel

        device = os.environ.get("WHISPER_DEVICE", "cpu")
        compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
        model = WhisperModel(self._model, device=device, compute_type=compute_type)

        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = model.transcribe(
            samples, beam_size=1, best_of=1, language="en", vad_filter=False
        )
        texts, confidences = [], []
        for seg in segments:
            texts.append(seg.text.strip())
            if seg.avg_logprob is not None:
                confidences.append(math.exp(seg.avg_logprob))

        transcript = " ".join(t for t in texts if t)
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return transcript, confidence

    def run(self) -> BenchmarkReport:
        pairs = self._load_pairs()
        results: list[FileBenchmarkResult] = []

        for wav_path, reference in pairs:
            pcm = load_wav_as_pcm16_16k(wav_path)

            t0 = time.monotonic()
            if self._backend == "faster-whisper":
                hypothesis, confidence = self._transcribe_faster_whisper(pcm)
            else:
                raise ValueError(f"Unknown benchmark backend: {self._backend!r}")
            latency_ms = (time.monotonic() - t0) * 1000

            wer = word_error_rate(reference, hypothesis)
            results.append(
                FileBenchmarkResult(
                    filename=wav_path.name,
                    reference=reference,
                    hypothesis=hypothesis,
                    wer=wer,
                    confidence=confidence,
                    latency_ms=latency_ms,
                    hallucination=wer > 1.0,
                )
            )
            print(
                f"  {wav_path.name}: WER={wer:.1%} conf={confidence:.2f} "
                f"lat={latency_ms:.0f}ms  hyp={hypothesis!r}"
            )

        mean_wer = sum(r.wer for r in results) / len(results)
        mean_conf = sum(r.confidence for r in results) / len(results)
        mean_lat = sum(r.latency_ms for r in results) / len(results)

        return BenchmarkReport(
            backend=self._backend,
            model=self._model,
            mean_wer=mean_wer,
            mean_confidence=mean_conf,
            mean_latency_ms=mean_lat,
            results=results,
        )


# ─── Fixture generator ────────────────────────────────────────────────────────

async def generate_fixtures(
    texts: list[str],
    output_dir: Path,
    tts_backend: str = "piper",
) -> None:
    """Generate WAV + ground-truth pairs using the configured TTS backend."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend/python/src"))

    from ivr_assessor.tts_service import create_tts, PiperTTS
    import io, wave

    tts = create_tts()
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, text in enumerate(texts, 1):
        name = f"fixture_{i:03d}"
        wav_path = output_dir / f"{name}.wav"
        txt_path = output_dir / f"{name}.txt"

        mulaw_bytes = await tts.synthesize(text)

        # mulaw → WAV container so load_wav_as_pcm16_16k can read it
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(1)  # mulaw = 1 byte/sample
            wf.setframerate(8000)
            wf.writeframes(mulaw_bytes)
        wav_path.write_bytes(buf.getvalue())
        txt_path.write_text(text, encoding="utf-8")
        print(f"Generated {wav_path.name}: {text!r}")


# ─── CLI entry point ──────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="WER benchmark for IVR STT backends")
    parser.add_argument("--backend", default="faster-whisper")
    parser.add_argument("--model", default=None, help="Whisper model size (e.g. small.en)")
    parser.add_argument(
        "--fixtures",
        default="backend/python/tests/fixtures/audio",
        help="Path to directory containing .wav + .txt pairs",
    )
    parser.add_argument(
        "--output",
        default=os.environ.get("BENCHMARK_OUTPUT", "/tmp/wer_report.json"),
        help="Path for JSON output",
    )
    parser.add_argument(
        "--generate-fixtures",
        action="store_true",
        help="Generate fixture WAV files from --fixture-texts using TTS",
    )
    parser.add_argument(
        "--fixture-texts",
        nargs="+",
        default=[
            "press one for billing",
            "press two for support",
            "please hold while we connect your call",
            "your account balance is zero dollars",
            "thank you for calling goodbye",
        ],
    )
    args = parser.parse_args()

    fixtures_dir = Path(args.fixtures)

    if args.generate_fixtures:
        asyncio.run(generate_fixtures(args.fixture_texts, fixtures_dir))
        return

    print(f"Running WER benchmark: backend={args.backend} fixtures={fixtures_dir}")
    bench = WERBenchmark(fixtures_dir, backend=args.backend, model=args.model)
    report = bench.run()

    print()
    print(report.as_markdown())

    out = Path(args.output)
    out.write_text(json.dumps(report.as_json(), indent=2), encoding="utf-8")
    print(f"\nJSON report written to {out}")


if __name__ == "__main__":
    main()
