"""Property tests for framework-independent provider execution policies."""

from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.contracts.provider_execution import (
    ProviderExecutionFailure,
    ProviderFailureCode,
    ProviderRetryPolicy,
)


@given(
    max_attempts=st.integers(min_value=1, max_value=20),
    attempts_made=st.integers(min_value=1, max_value=30),
)
def test_retry_decision_never_exceeds_attempt_budget(
    max_attempts: int,
    attempts_made: int,
) -> None:
    policy = ProviderRetryPolicy(max_attempts=max_attempts)
    failure = ProviderExecutionFailure(
        code=ProviderFailureCode.TRANSIENT,
        message="temporary provider failure",
    )

    assert policy.should_retry(
        failure,
        attempts_made=attempts_made,
    ) is (attempts_made < max_attempts)


@given(
    base_delay=st.floats(
        min_value=0.0,
        max_value=10.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    extra_delay=st.floats(
        min_value=0.0,
        max_value=20.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    jitter_ratio=st.floats(
        min_value=0.0,
        max_value=1.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    attempts_made=st.integers(min_value=1, max_value=10),
)
def test_backoff_jitter_bounds_are_ordered_and_nonnegative(
    base_delay: float,
    extra_delay: float,
    jitter_ratio: float,
    attempts_made: int,
) -> None:
    max_delay = base_delay + extra_delay
    policy = ProviderRetryPolicy(
        base_delay_seconds=base_delay,
        max_delay_seconds=max_delay,
        jitter_ratio=jitter_ratio,
    )

    lower, upper = policy.backoff_bounds(
        attempts_made=attempts_made,
    )

    assert 0.0 <= lower <= upper


@given(
    retry_after=st.floats(
        min_value=0.0,
        max_value=300.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    attempts_made=st.integers(min_value=1, max_value=10),
)
def test_retry_after_never_allows_earlier_retry(
    retry_after: float,
    attempts_made: int,
) -> None:
    policy = ProviderRetryPolicy()

    lower, upper = policy.backoff_bounds(
        attempts_made=attempts_made,
        retry_after_seconds=retry_after,
    )

    assert lower >= retry_after
    assert upper >= lower


@given(
    attempts_made=st.integers(min_value=1, max_value=30),
)
def test_non_retryable_failures_never_retry(
    attempts_made: int,
) -> None:
    policy = ProviderRetryPolicy(max_attempts=30)
    failure = ProviderExecutionFailure(
        code=ProviderFailureCode.NON_RETRYABLE,
        message="permanent provider failure",
    )

    assert not policy.should_retry(
        failure,
        attempts_made=attempts_made,
    )
