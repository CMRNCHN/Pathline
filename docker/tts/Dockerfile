FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Download piper binary (Linux x86_64)
ARG PIPER_VERSION=2023.11.14-2
RUN curl -fsSL \
    "https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/piper_linux_x86_64.tar.gz" \
    | tar -xz -C /usr/local/bin --strip-components=1 piper/piper \
    && chmod +x /usr/local/bin/piper

# Download default voice (en_US-lessac-medium)
ARG VOICE_NAME=en_US-lessac-medium
ARG HF_BASE=https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium
RUN mkdir -p /app/voices \
    && curl -fsSL "${HF_BASE}/${VOICE_NAME}.onnx" -o "/app/voices/${VOICE_NAME}.onnx" \
    && curl -fsSL "${HF_BASE}/${VOICE_NAME}.onnx.json" -o "/app/voices/${VOICE_NAME}.onnx.json"

ENV PIPER_BINARY=/usr/local/bin/piper
ENV PIPER_VOICE=/app/voices/en_US-lessac-medium.onnx

# Smoke-test: synthesize one phrase to confirm binary + voice work
RUN echo "press one" | piper --model /app/voices/en_US-lessac-medium.onnx --output-raw > /dev/null \
    && echo "TTS smoke test passed"

CMD ["python", "-c", "import os; print('TTS ready — binary:', os.environ['PIPER_BINARY'], 'voice:', os.environ['PIPER_VOICE'])"]
