"""Create owner-bound opaque artifact storage.

Revision ID: 20260719_0001
Revises:
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260719_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "callstate_records",
        sa.Column("hashed_id", sa.String(length=64), primary_key=True),
        sa.Column("owner_hash", sa.String(length=64), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_callstate_records_owner_hash", "callstate_records", ["owner_hash"])
    op.create_index("ix_callstate_records_expires_at", "callstate_records", ["expires_at"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_hash", sa.String(length=64), nullable=False),
        sa.Column("hashed_id", sa.String(length=64), nullable=False),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notifications_owner_hash", "notifications", ["owner_hash"])
    op.create_index("ix_notifications_hashed_id", "notifications", ["hashed_id"])
    op.create_index("ix_notifications_expires_at", "notifications", ["expires_at"])

    op.create_table(
        "consent_audits",
        sa.Column("jti", sa.String(length=36), primary_key=True),
        sa.Column("owner_hash", sa.String(length=64), nullable=False),
        sa.Column("terms_version", sa.String(length=32), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("call_mode", sa.String(length=32), nullable=False),
        sa.Column("hashed_session_id", sa.String(length=64), nullable=True),
        sa.Column("session_linked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_consent_audits_owner_hash", "consent_audits", ["owner_hash"])
    op.create_index("ix_consent_audits_hashed_session_id", "consent_audits", ["hashed_session_id"])
    op.create_index("ix_consent_audits_expires_at", "consent_audits", ["expires_at"])

    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(length=36), primary_key=True),
        sa.Column("owner_hash", sa.String(length=64), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_revoked_tokens_owner_hash", "revoked_tokens", ["owner_hash"])
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_hash", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "owner_hash",
            "operation",
            "idempotency_key",
            name="uq_idempotency_owner_operation_key",
        ),
    )
    op.create_index("ix_idempotency_expires_at", "idempotency_records", ["expires_at"])


def downgrade() -> None:
    op.drop_table("idempotency_records")
    op.drop_table("revoked_tokens")
    op.drop_table("consent_audits")
    op.drop_table("notifications")
    op.drop_table("callstate_records")
