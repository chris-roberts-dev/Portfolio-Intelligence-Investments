"""Provider-neutral safety helpers for externally visible provider errors."""

from __future__ import annotations

import re
from collections.abc import Sequence

from apps.market_data.providers.base import ProviderIssue

REDACTED_PROVIDER_VALUE = "[REDACTED]"

_AUTHORIZATION_PATTERN = re.compile(
    r"(?i)(?P<prefix>\bauthorization\b\s*[:=]\s*)"
    r"(?P<value>[^\r\n,;]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"""(?ix)
    (?P<prefix>
        ["']?
        (?:
            api[_-]?key
            |apikey
            |access[_-]?token
            |token
            |client[_-]?secret
            |secret
            |password
        )
        ["']?
        \s*[:=]\s*
    )
    (?P<quote>["']?)
    (?P<value>[^"'\s,;&]+)
    (?P=quote)
    """
)


def sanitize_provider_message(
    message: str,
    *,
    sensitive_values: Sequence[str] = (),
) -> str:
    """Return provider-originated text with credential-like values redacted."""
    sanitized = message

    for sensitive_value in sorted(
        {value for value in sensitive_values if value},
        key=len,
        reverse=True,
    ):
        sanitized = sanitized.replace(
            sensitive_value,
            REDACTED_PROVIDER_VALUE,
        )

    sanitized = _AUTHORIZATION_PATTERN.sub(
        lambda match: f"{match.group('prefix')}{REDACTED_PROVIDER_VALUE}",
        sanitized,
    )
    sanitized = _BEARER_PATTERN.sub(
        f"Bearer {REDACTED_PROVIDER_VALUE}",
        sanitized,
    )
    sanitized = _SENSITIVE_ASSIGNMENT_PATTERN.sub(
        _replace_sensitive_assignment,
        sanitized,
    )

    return sanitized


def safe_provider_issue(
    code: str,
    message: str,
    *,
    sensitive_values: Sequence[str] = (),
) -> ProviderIssue:
    """Construct a ProviderIssue whose message is safe for serialization/logging."""
    return ProviderIssue(
        code=code,
        message=sanitize_provider_message(
            message,
            sensitive_values=sensitive_values,
        ),
    )


def _replace_sensitive_assignment(
    match: re.Match[str],
) -> str:
    quote = match.group("quote")

    return f"{match.group('prefix')}{quote}{REDACTED_PROVIDER_VALUE}{quote}"
