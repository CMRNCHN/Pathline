from __future__ import annotations

# Module-level singletons — set by main.py at startup, read by routes.
# Using module globals avoids circular imports that arise from `import main`.

session_manager = None   # SessionManager
broadcaster = None       # LiveBroadcaster
transcriber = None       # StreamingWhisperTranscriber
storage = None           # TranscriptStorage
dtmf_generator = None    # DTMFGenerator
voice_synthesizer = None # VoiceSynthesizer
twilio_client = None     # TwilioTelephonyClient

SUITES: dict = {}
DTMF_PRESETS: dict = {}
VOICE_PRESETS: dict = {}
