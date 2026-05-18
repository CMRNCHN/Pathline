FROM python:3.12-slim

WORKDIR /app

# gcc needed for webrtcvad-wheels, curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python package
COPY pyproject.toml .
COPY runtime/ runtime/
COPY replay/ replay/
COPY analyst/ analyst/
COPY agents/ agents/
RUN pip install --no-cache-dir -e ".[performance]"

EXPOSE 8081

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8081/healthz || exit 1

CMD ["uvicorn", "runtime.transport.streaming_server:app", \
     "--host", "0.0.0.0", "--port", "8081", "--log-level", "warning"]
