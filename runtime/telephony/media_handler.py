from __future__ import annotations

import json
import numpy as np
from typing import AsyncGenerator

import structlog
from websockets.server import WebSocketServerProtocol

log = structlog.get_logger()


class TwilioMediaReceiver:
    """
    Accepts Twilio Media Streams, extracts PCM-16 audio,
    yields as async generator for transcriber.
    """

    EXPECTED_SAMPLE_RATE = 8000  # Twilio default

    @staticmethod
    async def handle_media_stream(
        websocket: WebSocketServerProtocol,
    ) -> AsyncGenerator[bytes, None]:
        """
        Twilio sends JSON frames with base64-encoded mulaw audio.
        Decode → PCM-16 upsampled to 16kHz and yield.
        """
        try:
            async for message in websocket:
                try:
                    frame = json.loads(message)
                except json.JSONDecodeError:
                    continue

                if frame.get("event") == "media":
                    payload = frame.get("media", {})
                    audio_b64 = payload.get("payload")
                    if not audio_b64:
                        continue

                    import base64
                    mulaw_bytes = base64.b64decode(audio_b64)
                    pcm16 = TwilioMediaReceiver._mulaw_to_pcm16(mulaw_bytes)
                    pcm16_upsampled = TwilioMediaReceiver._resample(pcm16, 8000, 16000)
                    yield pcm16_upsampled.tobytes()

                elif frame.get("event") == "connected":
                    await websocket.send(
                        json.dumps({"event": "start", "streamSid": frame.get("streamSid")})
                    )
                    log.info("media_stream_connected", streamSid=frame.get("streamSid"))

                elif frame.get("event") == "stop":
                    log.info("media_stream_stopped")
                    break

        except Exception as e:
            log.error("media_stream_error", error=str(e))
            raise

    @staticmethod
    def _mulaw_to_pcm16(mulaw: bytes) -> np.ndarray:
        mulaw_uint8 = np.frombuffer(mulaw, dtype=np.uint8)
        mulaw_uint8 = ~mulaw_uint8
        s = np.abs(mulaw_uint8) / 255.0
        pcm = s * 32768.0 * (np.exp(np.log(1 + 255) * s) - 1) / 255.0
        pcm[mulaw_uint8 < 128] *= -1
        return pcm.astype(np.int16)

    @staticmethod
    def _resample(pcm: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
        from scipy.signal import resample_poly
        if sr_in == sr_out:
            return pcm
        float_audio = pcm.astype(np.float32) / 32768.0
        resampled = resample_poly(float_audio, sr_out, sr_in)
        return np.clip(resampled * 32768.0, -32768, 32767).astype(np.int16)
