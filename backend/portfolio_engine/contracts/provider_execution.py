"""Framework-independent market-data provider execution-policy contracts.

These contracts describe timeout, retry, backoff, jitter, throttling, and
provider-specific rate-limit behavior without depending on an HTTP client,
provider SDK, Django, Redis, Celery, or authentication state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from portfolio_engine.config import (
    MARKET_DATA_MAX_ATTEMPTS,
    MARKET_DATA_RETRY_BASE_DELAY_SECONDS,
    MARKET_DATA_RETRY_JITTER_RATIO,
    MARKET_DATA_RETRY_MAX_DELAY_SECONDS,
    MARKET_DATA_TIMEOUT_SECONDS,
)


class ProviderFailureCode(StrEnum):
    """Stable provider-neutral execution failure classifications."""

    THROTTLED = "THROTTLED"
    TIMEOUT = "TIMEOUT"
    TRANSIENT = "TRANSIENT"
    NON_RETRYABLE = "NON_RETRYABLE"


@dataclass(frozen=True, slots=True)
class ProviderExecutionFailure:
    """Provider-neutral failure information used by retry policy decisions."""

    code: ProviderFailureCode
    message: str
    retry_after_seconds: float | None = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("message must not be blank")

        if self.retry_after_seconds is not None and self.retry_after_seconds < 0.0:
            raise ValueError("retry_after_seconds must not be negative")

    @property
    def retryable(self) -> bool:
        """Return whether this failure class is eligible for retry."""
        return self.code in {
            ProviderFailureCode.THROTTLED,
            ProviderFailureCode.TIMEOUT,
            ProviderFailureCode.TRANSIENT,
        }


@dataclass(frozen=True, slots=True)
class ProviderRetryPolicy:
    """Bounded exponential-backoff policy with deterministic jitter bounds."""

    max_attempts: int = MARKET_DATA_MAX_ATTEMPTS
    base_delay_seconds: float = MARKET_DATA_RETRY_BASE_DELAY_SECONDS
    max_delay_seconds: float = MARKET_DATA_RETRY_MAX_DELAY_SECONDS
    jitter_ratio: float = MARKET_DATA_RETRY_JITTER_RATIO

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        if self.base_delay_seconds < 0.0:
            raise ValueError("base_delay_seconds must not be negative")

        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError(
                "max_delay_seconds must be greater than or equal to base_delay_seconds"
            )

        if not 0.0 <= self.jitter_ratio <= 1.0:
            raise ValueError("jitter_ratio must be between 0 and 1 inclusive")

    def should_retry(
        self,
        failure: ProviderExecutionFailure,
        *,
        attempts_made: int,
    ) -> bool:
        """Return whether another attempt is permitted."""
        _validate_attempts_made(attempts_made)

        return failure.retryable and attempts_made < self.max_attempts

    def backoff_bounds(
        self,
        *,
        attempts_made: int,
        retry_after_seconds: float | None = None,
    ) -> tuple[float, float]:
        """Return inclusive lower/upper bounds for the next retry delay.

        ``attempts_made`` is one-based and represents the number of provider
        attempts already completed.

        ``retry_after_seconds`` is treated as a hard lower bound so jitter can
        never cause a retry earlier than the provider explicitly requested.
        """
        _validate_attempts_made(attempts_made)

        if retry_after_seconds is not None and retry_after_seconds < 0.0:
            raise ValueError("retry_after_seconds must not be negative")

        exponential_delay = min(
            self.base_delay_seconds * (2 ** (attempts_made - 1)),
            self.max_delay_seconds,
        )

        lower_bound = exponential_delay * (1.0 - self.jitter_ratio)
        upper_bound = exponential_delay * (1.0 + self.jitter_ratio)

        if retry_after_seconds is not None:
            lower_bound = max(lower_bound, retry_after_seconds)
            upper_bound = max(upper_bound, lower_bound)

        return max(0.0, lower_bound), upper_bound


@dataclass(frozen=True, slots=True)
class ProviderRateLimitPolicy:
    """Explicit provider-specific request-rate boundary."""

    max_requests: int
    window_seconds: float

    def __post_init__(self) -> None:
        if self.max_requests < 1:
            raise ValueError("max_requests must be at least 1")

        if self.window_seconds <= 0.0:
            raise ValueError("window_seconds must be positive")


@dataclass(frozen=True, slots=True)
class ProviderExecutionPolicy:
    """Complete provider-neutral execution policy for one adapter."""

    timeout_seconds: float = float(MARKET_DATA_TIMEOUT_SECONDS)
    retry: ProviderRetryPolicy = field(default_factory=ProviderRetryPolicy)
    rate_limit: ProviderRateLimitPolicy | None = None

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive")


def _validate_attempts_made(attempts_made: int) -> None:
    if attempts_made < 1:
        raise ValueError("attempts_made must be at least 1")
