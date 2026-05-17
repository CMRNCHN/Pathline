# Replay Media Uses Local Artifact Resolution

Date: 2026-05-15

## Decision

Replay media playback resolves only local WAV artifacts and serves them through `/api/replays/<session_id>/media`. Waveform metadata is generated on demand from those same local WAV artifacts.

## Context

Replay state can carry a `recording_reference`, but that reference may be a call SID, a Twilio recording URL, or a local recording name depending on how the session was captured. The review workspace needs deterministic cursor-tied playback without adding network fetches, Twilio credential handling, or hot-path behavior.

## Consequences

- The media route looks for local WAV files by session id, call sid, and recording reference under configured recording directories.
- Missing media remains an explicit 404 and the waveform payload exposes `media_available=false`.
- Remote Twilio recording download remains outside replay loading; recordings must already exist locally before playback appears.
- Replay cursor offsets remain derived from persisted operational events, not from audio analysis.
- Waveform peaks/RMS buckets are derived from local media for visualization only and do not affect replay state reconstruction.
