"""Token validation helpers."""

from __future__ import annotations

import hmac


def is_valid_token(expected_token: str, provided_token: str) -> bool:
    if not expected_token:
        return True
    return hmac.compare_digest(expected_token, provided_token)
