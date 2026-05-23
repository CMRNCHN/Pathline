from __future__ import annotations

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Any

import structlog

log = structlog.get_logger()


class TranscriptDB:
    """
    Local SQLite ledger for calls, transcripts, confidence, amounts.
    Lives at Pathline/data/transcripts.db
    """

    def __init__(self, db_path: str | Path = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "transcripts.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_sid TEXT UNIQUE NOT NULL,
                    customer_id TEXT,
                    invoice_id TEXT,
                    created_at TEXT NOT NULL,
                    duration_seconds REAL,
                    transcript_path TEXT,
                    audio_path TEXT,
                    full_transcript TEXT,
                    segment_count INTEGER,
                    min_confidence REAL,
                    requires_confirmation INTEGER,
                    metadata TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_id INTEGER NOT NULL,
                    sequence INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    raw_text TEXT,
                    start_time REAL,
                    end_time REAL,
                    confidence REAL,
                    metadata TEXT,
                    FOREIGN KEY(call_id) REFERENCES calls(id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_calls_sid ON calls(call_sid)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_calls_customer ON calls(customer_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_calls_created ON calls(created_at)
                """
            )
            conn.commit()
            log.info("transcript_db_initialized", path=str(self.db_path))

    def log_call(
        self,
        call_sid: str,
        transcript_path: str | None = None,
        audio_path: str | None = None,
        duration_seconds: float | None = None,
        segments: list[dict] | None = None,
        customer_id: str | None = None,
        invoice_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Insert call + segments. Returns call_id.
        """
        if metadata is None:
            metadata = {}

        full_transcript = "\n".join([s.get("text", "") for s in (segments or [])])
        min_confidence = min([s.get("confidence", 1.0) for s in (segments or [])], default=1.0)
        requires_confirmation = 1 if min_confidence < 0.8 else 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO calls (
                    call_sid, customer_id, invoice_id, created_at,
                    duration_seconds, transcript_path, audio_path,
                    full_transcript, segment_count, min_confidence,
                    requires_confirmation, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    call_sid,
                    customer_id,
                    invoice_id,
                    datetime.utcnow().isoformat(),
                    duration_seconds,
                    transcript_path,
                    audio_path,
                    full_transcript,
                    len(segments or []),
                    min_confidence,
                    requires_confirmation,
                    json.dumps(metadata),
                ),
            )
            call_id = cursor.lastrowid

            for seq, seg in enumerate(segments or []):
                conn.execute(
                    """
                    INSERT INTO segments (
                        call_id, sequence, text, raw_text, start_time, end_time,
                        confidence, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        call_id,
                        seq,
                        seg.get("text", ""),
                        seg.get("raw_text", ""),
                        seg.get("start", 0.0),
                        seg.get("end", 0.0),
                        seg.get("confidence", 1.0),
                        json.dumps(seg.get("metadata", {})),
                    ),
                )
            conn.commit()
            log.info("call_logged", call_sid=call_sid, call_id=call_id, segments=len(segments or []))
            return call_id

    def get_call(self, call_sid: str) -> dict | None:
        """Fetch call + segments by call_sid."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            call = conn.execute(
                "SELECT * FROM calls WHERE call_sid = ?",
                (call_sid,),
            ).fetchone()
            if not call:
                return None

            segments = conn.execute(
                "SELECT * FROM segments WHERE call_id = ? ORDER BY sequence",
                (call["id"],),
            ).fetchall()

            return {
                **dict(call),
                "segments": [dict(s) for s in segments],
                "metadata": json.loads(call["metadata"] or "{}"),
            }

    def search_calls(
        self,
        customer_id: str | None = None,
        invoice_id: str | None = None,
        min_confidence: float | None = None,
        requires_confirmation: bool | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Query calls by filters."""
        query = "SELECT * FROM calls WHERE 1=1"
        params = []

        if customer_id:
            query += " AND customer_id = ?"
            params.append(customer_id)
        if invoice_id:
            query += " AND invoice_id = ?"
            params.append(invoice_id)
        if min_confidence is not None:
            query += " AND min_confidence >= ?"
            params.append(min_confidence)
        if requires_confirmation is not None:
            query += " AND requires_confirmation = ?"
            params.append(1 if requires_confirmation else 0)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def search_transcript(self, query_text: str, limit: int = 20) -> list[dict]:
        """Full-text search transcripts by keyword."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT c.* FROM calls c
                WHERE c.full_transcript LIKE ?
                ORDER BY c.created_at DESC LIMIT ?
                """,
                (f"%{query_text}%", limit),
            ).fetchall()
            return [dict(r) for r in rows]
