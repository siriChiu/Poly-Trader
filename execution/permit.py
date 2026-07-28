from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any, Mapping, Optional

PERMIT_SECRET_ENV = "POLY_TRADER_EXECUTION_PERMIT_SECRET"
MIN_SECRET_BYTES = 32


def canonical_permit_claims(claims: Mapping[str, Any]) -> str:
    return json.dumps(
        dict(claims),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def execution_permit_secret(secret: Optional[str] = None) -> bytes:
    value = str(secret if secret is not None else os.getenv(PERMIT_SECRET_ENV, ""))
    encoded = value.encode("utf-8")
    if len(encoded) < MIN_SECRET_BYTES:
        raise ValueError(f"{PERMIT_SECRET_ENV} must contain at least {MIN_SECRET_BYTES} UTF-8 bytes")
    return encoded


def sign_execution_permit(claims: Mapping[str, Any], *, secret: Optional[str] = None) -> dict[str, Any]:
    normalized_claims = dict(claims)
    signature = hmac.new(
        execution_permit_secret(secret),
        canonical_permit_claims(normalized_claims).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {"algorithm": "HMAC-SHA256", "claims": normalized_claims, "signature": signature}


def verify_execution_permit_signature(
    permit: Mapping[str, Any],
    *,
    secret: Optional[str] = None,
) -> tuple[bool, dict[str, Any]]:
    if str(permit.get("algorithm") or "") != "HMAC-SHA256":
        return False, {}
    claims = permit.get("claims")
    signature = str(permit.get("signature") or "")
    if not isinstance(claims, Mapping) or len(signature) != 64:
        return False, {}
    normalized_claims = dict(claims)
    expected = hmac.new(
        execution_permit_secret(secret),
        canonical_permit_claims(normalized_claims).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected), normalized_claims
