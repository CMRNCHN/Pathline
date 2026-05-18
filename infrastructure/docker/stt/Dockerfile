FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir faster-whisper>=1.0.3

# Pre-download the model at image build time so the first connect() is instant.
# Override WHISPER_MODEL at build time: docker build --build-arg WHISPER_MODEL=small.en
ARG WHISPER_MODEL=small.en
ENV WHISPER_MODEL=${WHISPER_MODEL}

RUN python - <<'EOF'
import os
from faster_whisper import WhisperModel
model = os.environ["WHISPER_MODEL"]
print(f"Downloading Whisper model: {model}")
WhisperModel(model, device="cpu", compute_type="int8")
print("Done.")
EOF

CMD ["python", "-c", "from faster_whisper import WhisperModel; import os; m=WhisperModel(os.environ['WHISPER_MODEL'],device='cpu',compute_type='int8'); print('STT model ready:', os.environ['WHISPER_MODEL'])"]
