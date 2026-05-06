# IVR Assessor Backend

## Quick Start

Create a local virtual environment and install the package in editable mode:

```bash
cd backend/python
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Run the CLI from anywhere after activation:

```bash
python -m ivr_assessor.cli version
python -m ivr_assessor.cli --help
```

Run the test suite:

```bash
python -m pytest -q
```

## Optional Audio Quality Add-ons

These are optional and **disabled by default** unless you set the related env var.

- **AssemblyAI real-time transcription** (paid)
  - Env: `ASSEMBLYAI_API_KEY`
  - Current status: placeholder class present (`AssemblyAITranscriber`) with graceful disabled behavior when key is missing.
- **Twilio Voice Intelligence post-call analytics** (paid)
  - Env: `TWILIO_INTELLIGENCE_SERVICE_SID`
  - Current status: placeholder class present (`TwilioVoiceIntelligence`) with graceful disabled behavior when SID is missing.
- **Dolby.io audio enhancement** (free tier then paid)
  - Env: `DOLBY_API_KEY`
  - Current status: placeholder class present (`DolbyAudioEnhancer`) with graceful disabled behavior when key is missing.

Reference env entries are already included in `backend/python/.env.example`.
