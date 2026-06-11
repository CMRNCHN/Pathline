"""runtime/session_manager.py — Orchestrates a live IVR mapping session.

This is the integration point that connects every component:

    Twilio (audio source)
      → Deepgram (STT)
        → PII scrubber (safety)
          → ObservationQuality (quality gate)
            → Human pickup detector (safety gate)
              → append_observation() ← THE FIRST OBSERVATION HAPPENS HERE
                → IvrMapper.observe() (world model update)
                  → DiscoveryEngine.classify_gaps() (gap generation)

One developer workflow (manual mode):
    1. Call run_manual_session() — places call, starts streaming
    2. Watch transcript printed to stdout
    3. Call inject_dtmf() to press buttons
    4. Call end_session() to hang up

The session is complete when all six Phase 1 milestones are met:
    ✓ Call placed
    ✓ Audio streamed
    ✓ Transcript produced
    ✓ Observation written
    ✓ Node created
    ✓ Gap task generated
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from runtime.discovery_engine import DiscoveryEngine
from runtime.gap_task import GapTaskQueue
from runtime.human_pickup import is_human_pickup
from runtime.ivr_mapper import CallEvent, CallEventType, IvrMapper
from runtime.observation_quality import assess as assess_quality
from runtime.pii_scrubber import scrub
from runtime.stt.deepgram_client import DeepgramStreamClient, TranscriptEvent
from runtime.storage import Session, SessionObservation, StorageBackend
from runtime.telephony.twilio_media_client import TwilioMediaClient

logger = logging.getLogger(__name__)


@dataclass
class SessionResult:
    session_id: str
    call_sid: str | None
    observations_written: int
    nodes_created: int
    gaps_generated: int
    human_pickup_aborted: bool
    ended_at: datetime
    outcome: dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """Manages one IVR mapping session end-to-end.

    Args:
        storage: Persistent storage backend.
        twilio: TwilioMediaClient for call control and media streaming.
        deepgram: DeepgramStreamClient for STT.
        mapper: IvrMapper for world model updates.
        gap_queue: GapTaskQueue for gap accumulation.
    """

    def __init__(
        self,
        storage: StorageBackend,
        twilio: TwilioMediaClient,
        deepgram: DeepgramStreamClient,
        mapper: IvrMapper,
        gap_queue: GapTaskQueue,
    ) -> None:
        self._storage = storage
        self._twilio = twilio
        self._deepgram = deepgram
        self._mapper = mapper
        self._gap_queue = gap_queue
        self._discovery = DiscoveryEngine(queue=gap_queue, storage=storage)

        # Mutable call state (reset per session)
        self._session_id: str = ''
        self._ivr_id: str = ''
        self._call_sid: str | None = None
        self._observations: int = 0
        self._nodes_before: int = 0
        self._aborted: bool = False

    # ── Public API ──────────────────────────────────────────────────────────

    async def start(self, ivr_id: str, target_number: str) -> str:
        """Place the call and return the session_id.

        Call this, then await stream(websocket) when Twilio connects.
        """
        self._session_id = str(uuid.uuid4())
        self._ivr_id = ivr_id
        self._observations = 0
        self._aborted = False
        self._nodes_before = len(self._storage.get_nodes_by_system(ivr_id))

        self._storage.start_session(Session(
            session_id=self._session_id,
            system_id=ivr_id,
        ))

        record = self._twilio.place_call(
            to=target_number,
            session_id=self._session_id,
        )
        self._call_sid = record.call_sid

        logger.info(
            'Session %s started | call %s → %s',
            self._session_id, self._call_sid, target_number,
        )
        return self._session_id

    async def stream(self, websocket: Any) -> None:
        """Process the Twilio Media Stream WebSocket.

        Run this concurrently with the WebSocket accept loop in the server.
        Returns when the call ends or is aborted.
        """
        audio_queue: asyncio.Queue = asyncio.Queue(maxsize=200)

        media_task = asyncio.create_task(
            self._twilio.handle_media_stream(websocket, audio_queue)
        )
        stt_task = asyncio.create_task(
            self._deepgram.stream(audio_queue, self._on_transcript)
        )

        await asyncio.gather(media_task, stt_task, return_exceptions=True)

    async def inject_dtmf(self, digits: str) -> None:
        """Inject DTMF tones and write an action observation."""
        if not self._call_sid:
            logger.warning('inject_dtmf called with no active call')
            return

        self._twilio.inject_dtmf(self._call_sid, digits)
        await self._write_action_observation('dtmf_injected', digits)

        self._mapper.observe(
            CallEvent(
                event_type=CallEventType.DTMF_INJECTED,
                dtmf_value=digits,
                timestamp=datetime.now(timezone.utc),
            ),
            session_id=self._session_id,
            storage=self._storage,
        )
        logger.info('[%s] DTMF injected: %s', self._session_id[:8], digits)

    def end(self) -> SessionResult:
        """Hang up the call and generate gap tasks. Returns SessionResult."""
        if self._call_sid:
            self._twilio.hangup(self._call_sid)

        # Run discovery — this generates gap tasks
        gaps = self._discovery.classify_gaps(
            mapper=self._mapper,
            system_id=self._ivr_id,
            session_id=self._session_id,
        )

        nodes_after = len(self._storage.get_nodes_by_system(self._ivr_id))
        nodes_created = nodes_after - self._nodes_before

        outcome = {
            'observations_written': self._observations,
            'nodes_created': nodes_created,
            'gaps_generated': len(gaps),
            'human_pickup_aborted': self._aborted,
        }

        self._storage.end_session(self._session_id, outcome=outcome)

        result = SessionResult(
            session_id=self._session_id,
            call_sid=self._call_sid,
            observations_written=self._observations,
            nodes_created=nodes_created,
            gaps_generated=len(gaps),
            human_pickup_aborted=self._aborted,
            ended_at=datetime.now(timezone.utc),
            outcome=outcome,
        )

        logger.info(
            'Session %s ended | %d obs | %d nodes | %d gaps',
            self._session_id[:8],
            self._observations,
            nodes_created,
            len(gaps),
        )
        return result

    # ── Internal transcript handler ─────────────────────────────────────────

    async def _on_transcript(self, event: TranscriptEvent) -> None:
        """Process one STT event. Called by DeepgramStreamClient for every result."""

        if not event.text.strip():
            return  # silence / noise frame

        # 1 ── Quality gate: skip partials
        quality = assess_quality(
            observation_id=str(uuid.uuid4()),
            transcript=event.text,
            confidence=event.confidence,
            is_final=event.is_final,
            duration_ms=event.duration_ms,
        )
        if not quality.stt_is_final:
            return  # wait for final transcript

        # 2 ── Human pickup detection
        pickup, confidence = is_human_pickup(
            transcript=event.text,
            words_per_second=quality.words_per_second,
        )
        if pickup and confidence >= 0.65:
            await self._abort_human_pickup()
            return

        # 3 ── PII scrub
        clean_text, was_scrubbed = scrub(event.text)
        if quality.is_suspicious:
            logger.warning(
                '[%s] Suspicious transcript (conf=%.2f, wps=%.1f): %r',
                self._session_id[:8],
                event.confidence,
                quality.words_per_second or 0,
                clean_text[:60],
            )

        # 4 ── Write observation ← FIRST OBSERVATION MILESTONE
        obs_id = str(uuid.uuid4())
        obs = SessionObservation(
            obs_id=obs_id,
            session_id=self._session_id,
            system_id=self._ivr_id,
            event_kind='prompt',
            event_text=clean_text,
            t_ms=event.t_ms,
            confidence=event.confidence,
            observed_at=datetime.now(timezone.utc),
            obs_schema_version='1.0',
            raw_payload={
                'pii_scrubbed':    was_scrubbed,
                'stt_is_final':    True,
                'words_per_second': quality.words_per_second,
                'is_suspicious':   quality.is_suspicious,
                'stt_channel':     event.channel,
                'duration_ms':     event.duration_ms,
            },
        )
        self._storage.append_observation(obs)
        self._observations += 1

        logger.info(
            '[%s] OBS #%d (conf=%.2f): %s',
            self._session_id[:8],
            self._observations,
            event.confidence,
            clean_text[:80],
        )

        # 5 ── Update world model ← NODE CREATION MILESTONE
        result = self._mapper.observe(
            CallEvent(
                event_type=CallEventType.PROMPT_HEARD,
                transcript=clean_text,
                stt_confidence=event.confidence,
                timestamp=datetime.now(timezone.utc),
            ),
            session_id=self._session_id,
            storage=self._storage,
        )

        if result.is_new_node:
            logger.info(
                '[%s] New node: %s (state=%s)',
                self._session_id[:8],
                (result.node_id or '')[:8],
                result.epistemic_state_transition,
            )

    async def _abort_human_pickup(self) -> None:
        """Hang up immediately when a live human is detected."""
        logger.warning('[%s] Human pickup detected — aborting', self._session_id[:8])
        self._aborted = True

        if self._call_sid:
            self._twilio.hangup(self._call_sid)

        # Write abort observation
        await self._write_action_observation('error', 'human_pickup_abort')

        self._storage.end_session(
            self._session_id,
            outcome={'failure_reason': 'human_pickup', 'aborted': True},
        )

    async def _write_action_observation(self, kind: str, text: str) -> None:
        """Write a non-prompt observation (action, error, note)."""
        obs = SessionObservation(
            obs_id=str(uuid.uuid4()),
            session_id=self._session_id,
            system_id=self._ivr_id,
            event_kind=kind,
            event_text=text,
            t_ms=int(time.time() * 1000),
            confidence=1.0,
            observed_at=datetime.now(timezone.utc),
            obs_schema_version='1.0',
            raw_payload={},
        )
        self._storage.append_observation(obs)
        self._observations += 1
