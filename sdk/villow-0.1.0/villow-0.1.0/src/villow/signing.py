from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass


KEY_ID_HEADER = "x-worklane-key-id"
SIGNATURE_HEADER = "x-worklane-signature"
TIMESTAMP_HEADER = "x-worklane-timestamp"
NONCE_HEADER = "x-worklane-nonce"
PUBLISHER_ID_HEADER = "x-worklane-publisher-id"
AGENT_ID_HEADER = "x-worklane-agent-id"
IDEMPOTENCY_KEY_HEADER = "x-worklane-idempotency-key"


@dataclass(frozen=True)
class SigningPrincipal:
    publisher_id: str
    agent_id: str
    key_id: str
    nonce: str
    timestamp: int
    idempotency_key: str


def request_body_hash(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def canonical_request(
    method: str,
    path: str,
    body: bytes,
    *,
    timestamp: int,
    nonce: str,
    key_id: str,
    publisher_id: str,
    agent_id: str,
    idempotency_key: str,
) -> str:
    return "\n".join(
        [
            method.upper(),
            path,
            str(timestamp),
            nonce,
            key_id,
            publisher_id,
            agent_id,
            idempotency_key,
            request_body_hash(body),
        ]
    )


def sign_request(
    method: str,
    path: str,
    body: bytes,
    *,
    key_id: str,
    secret: str,
    publisher_id: str,
    agent_id: str,
    idempotency_key: str,
    timestamp: int | None = None,
    nonce: str | None = None,
) -> dict[str, str]:
    timestamp = int(timestamp or time.time())
    nonce = nonce or secrets.token_hex(16)
    canonical = canonical_request(
        method,
        path,
        body,
        timestamp=timestamp,
        nonce=nonce,
        key_id=key_id,
        publisher_id=publisher_id,
        agent_id=agent_id,
        idempotency_key=idempotency_key,
    )
    digest = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        KEY_ID_HEADER: key_id,
        SIGNATURE_HEADER: f"v1:{digest}",
        TIMESTAMP_HEADER: str(timestamp),
        NONCE_HEADER: nonce,
        PUBLISHER_ID_HEADER: publisher_id,
        AGENT_ID_HEADER: agent_id,
        IDEMPOTENCY_KEY_HEADER: idempotency_key,
    }


def verify_request_signature(
    method: str,
    path: str,
    body: bytes,
    headers: dict[str, str],
    *,
    secret: str,
    now: int | None = None,
    max_skew_seconds: int = 300,
) -> SigningPrincipal:
    normalized = {key.lower(): value for key, value in headers.items()}
    try:
        key_id = normalized[KEY_ID_HEADER]
        signature = normalized[SIGNATURE_HEADER]
        timestamp = int(normalized[TIMESTAMP_HEADER])
        nonce = normalized[NONCE_HEADER]
        publisher_id = normalized[PUBLISHER_ID_HEADER]
        agent_id = normalized.get(AGENT_ID_HEADER, "")
        idempotency_key = normalized.get(IDEMPOTENCY_KEY_HEADER, "")
    except (KeyError, ValueError) as exc:
        raise ValueError("missing_or_invalid_signature_headers") from exc

    now = int(now or time.time())
    if abs(now - timestamp) > max_skew_seconds:
        raise ValueError("stale_signature_timestamp")

    canonical = canonical_request(
        method,
        path,
        body,
        timestamp=timestamp,
        nonce=nonce,
        key_id=key_id,
        publisher_id=publisher_id,
        agent_id=agent_id,
        idempotency_key=idempotency_key,
    )
    expected = "v1:" + hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("invalid_signature")
    return SigningPrincipal(publisher_id, agent_id, key_id, nonce, timestamp, idempotency_key)
