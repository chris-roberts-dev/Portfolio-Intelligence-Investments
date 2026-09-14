"""Unit tests for framework-independent provider execution policies."""

import pytest

from portfolio_engine.config import (
    MARKET_DATA_MAX_ATTEMPTS,
    MARKET_DATA_TIMEOUT_SECONDS,
)
from portfolio_engine.contracts.provider_execution import (
    ProviderExecutionFailure,
    ProviderExecutionPolicy,
    ProviderFailureCode,
    ProviderRateLimitPolicy,
    ProviderRetryPolicy,
)


def test_default_execution_timeout_is_normative_30_seconds() -> None:
    policy = ProviderExecutionPolicy()

    assert MARKET_DATA_TIMEOUT_SECONDS == 30
    assert policy.timeout_seconds == 30.0


@pytest.mark.parametrize("timeout_seconds", [0.0, -0.1, -30.0])
def test_execution_policy_rejects_nonpositive_timeout(
    timeout_seconds: float,
) -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        ProviderExecutionPolicy(timeout_seconds=timeout_seconds)


def test_default_retry_budget_is_bounded() -> None:
    policy = ProviderRetryPolicy()
    failure = ProviderExecutionFailure(
        code=ProviderFailureCode.TRANSIENT,
        message="temporary provider failure",
    )

    assert policy.max_attempts == MARKET_DATA_MAX_ATTEMPTS
    assert policy.should_retry(failure, attempts_made=1)
    assert policy.should_retry(failure, attempts_made=2)
    assert not policy.should_retry(failure, attempts_made=3)


@pytest.mark.parametrize(
    "code",
    [
        ProviderFailureCode.THROTTLED,
        ProviderFailureCode.TIMEOUT,
        ProviderFailureCode.TRANSIENT,
    ],
)
def test_retryable_failure_classifications_are_stable(
    code: ProviderFailureCode,
) -> None:
    failure = ProviderExecutionFailure(
        code=code,
        message="retryable provider failure",
    )

    assert failure.retryable


def test_non_retryable_failure_is_never_retried() -> None:
    policy = ProviderRetryPolicy(max_attempts=10)
    failure = ProviderExecutionFailure(
        code=ProviderFailureCode.NON_RETRYABLE,
        message="permanent provider failure",
    )

    assert not failure.retryable

    for attempts_made in range(1, 10):
        assert not policy.should_retry(
            failure,
            attempts_made=attempts_made,
        )


def test_throttled_failure_preserves_retry_after_classification() -> None:
    failure = ProviderExecutionFailure(
        code=ProviderFailureCode.THROTTLED,
        message="provider rate limit exceeded",
        retry_after_seconds=12.0,
    )

    assert failure.code is ProviderFailureCode.THROTTLED
    assert failure.retryable
    assert failure.retry_after_seconds == 12.0


def test_retry_after_is_hard_lower_backoff_bound() -> None:
    policy = ProviderRetryPolicy(
        base_delay_seconds=1.0,
        max_delay_seconds=8.0,
        jitter_ratio=0.25,
    )

    lower, upper = policy.backoff_bounds(
        attempts_made=1,
        retry_after_seconds=10.0,
    )

    assert lower == 10.0
    assert upper == 10.0


def test_exponential_backoff_is_capped_before_jitter() -> None:
    policy = ProviderRetryPolicy(
        base_delay_seconds=2.0,
        max_delay_seconds=4.0,
        jitter_ratio=0.25,
    )

    lower, upper = policy.backoff_bounds(attempts_made=5)

    assert lower == pytest.approx(3.0)
    assert upper == pytest.approx(5.0)


@pytest.mark.parametrize(
    ("max_requests", "window_seconds"),
    [
        (0, 1.0),
        (-1, 1.0),
        (1, 0.0),
        (1, -1.0),
    ],
)
def test_rate_limit_policy_rejects_invalid_bounds(
    max_requests: int,
    window_seconds: float,
) -> None:
    with pytest.raises(ValueError):
        ProviderRateLimitPolicy(
            max_requests=max_requests,
            window_seconds=window_seconds,
        )


def test_provider_specific_rate_limit_policy_is_explicit() -> None:
    rate_limit = ProviderRateLimitPolicy(
        max_requests=5,
        window_seconds=1.0,
    )
    execution_policy = ProviderExecutionPolicy(
        rate_limit=rate_limit,
    )

    assert execution_policy.rate_limit == rate_limit
