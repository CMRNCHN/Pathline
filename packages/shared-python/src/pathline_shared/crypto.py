from __future__ import annotations

import hashlib
import hmac
import os
import re
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


PHONE_PATTERN = re.compile(r"\+?\d{7,15}")
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


def hash_session_id(session_id: str, pepper: str) -> str:
    """Hash session identifiers for storage — never store raw IDs."""
    return hmac.new(
        pepper.encode(),
        session_id.encode(),
        hashlib.sha256,
    ).hexdigest()


def redact_pii(text: str) -> str:
    """Redact phone numbers and emails from log strings."""
    text = PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
    return EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact PII from dict values for logging."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = redact_pii(value)
        elif isinstance(value, dict):
            result[key] = redact_dict(value)
        elif isinstance(value, list):
            result[key] = [
                redact_pii(v) if isinstance(v, str) else v for v in value
            ]
        else:
            result[key] = value
    return result


def encrypt_payload(plaintext: bytes, key: bytes) -> bytes:
    """AES-GCM encrypt; returns nonce + ciphertext."""
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt_payload(encrypted: bytes, key: bytes) -> bytes:
    """AES-GCM decrypt; expects nonce + ciphertext."""
    nonce, ciphertext = encrypted[:12], encrypted[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)
