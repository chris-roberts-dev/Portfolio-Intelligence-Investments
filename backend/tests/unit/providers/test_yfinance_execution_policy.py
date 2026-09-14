"""Deterministic execution-policy tests for the yfinance adapter."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import pandas as pd

from apps.market_data.providers.base import ResolvedProviderAsset
from apps.market_data.providers.yfinance import (
    YFINANCE_EXECUTION_POLICY,
    YFINANCE_RATE_LIMIT_POLICY,
    YFinanceMarketDataProvider,
    YFinanceProviderIssueCode,
)
from portfolio_engine.contracts.provider_execution import (
    ProviderExecutionPolicy,
    ProviderRateLimitPolicy,
    ProviderRetryPolicy,
)

ASSET_ID = UUID("00000000-0000-0000-0000-000000000001")
RETRIEVED_AT = datetime(2026, 1, 5, 12, tzinfo=UTC)

ASSET = ResolvedProviderAsset(
    asset_id=ASSET_ID,
    canonical_symbol="AAPL",
    provider_symbol="AAPL",
)


class FakeTime:
    """Deterministic monotonic clock and sleeper."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class YFRateLimitError(RuntimeError):
    """Test double matching yfinance's stable rate-limit exception name."""

    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0],
            "High": [103.0],
            "Low": [99.0],
            "Close": [102.0],
            "Adj Close": [101.5],
            "Volume": [1_000_000],
        },
        index=pd.DatetimeIndex(
            [date(2026, 1, 2)],
            name="Date",
        ),
    )


def request_bars(
    provider: YFinanceMarketDataProvider,
):
    return provider.get_daily_bars(
        (ASSET,),
        date(2026, 1, 1),
        date(2026, 1, 4),
    )


def policy_without_rate_limit(
    *,
    max_attempts: int = 3,
    base_delay_seconds: float = 0.5,
    max_delay_seconds: float = 8.0,
    jitter_ratio: float = 0.25,
    timeout_seconds: float = 30.0,
) -> ProviderExecutionPolicy:
    return ProviderExecutionPolicy(
        timeout_seconds=timeout_seconds,
        retry=ProviderRetryPolicy(
            max_attempts=max_attempts,
            base_delay_seconds=base_delay_seconds,
            max_delay_seconds=max_delay_seconds,
            jitter_ratio=jitter_ratio,
        ),
        rate_limit=None,
    )


def test_default_yfinance_policy_has_explicit_instance_rate_limit() -> None:
    assert YFINANCE_EXECUTION_POLICY.rate_limit == YFINANCE_RATE_LIMIT_POLICY
    assert (
        ProviderRateLimitPolicy(
            max_requests=1,
            window_seconds=1.0,
        )
        == YFINANCE_RATE_LIMIT_POLICY
    )


def test_yfinance_propagates_execution_timeout_to_download_boundary() -> None:
    captured: dict[str, Any] = {}

    def downloader(**kwargs: object) -> pd.DataFrame:
        captured.update(kwargs)
        return valid_frame()

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
        execution_policy=policy_without_rate_limit(
            timeout_seconds=7.5,
            max_attempts=1,
        ),
    )

    result = request_bars(provider)

    assert captured["timeout"] == 7.5
    assert result.issues == {}
    assert ASSET_ID in result.frames


def test_transient_failures_retry_only_within_attempt_budget() -> None:
    calls = 0
    fake_time = FakeTime()

    def downloader(**_kwargs: object) -> pd.DataFrame:
        nonlocal calls
        calls += 1

        if calls < 3:
            raise ConnectionError("temporary connection failure")

        return valid_frame()

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
        execution_policy=policy_without_rate_limit(
            max_attempts=3,
            base_delay_seconds=0.5,
            max_delay_seconds=8.0,
            jitter_ratio=0.0,
        ),
        sleeper=fake_time.sleep,
        jitter_sampler=lambda lower, _upper: lower,
    )

    result = request_bars(provider)

    assert calls == 3
    assert fake_time.sleeps == [0.5, 1.0]
    assert result.issues == {}
    assert ASSET_ID in result.frames


def test_retry_uses_injected_jitter_bounds() -> None:
    calls = 0
    sampled_bounds: list[tuple[float, float]] = []
    slept: list[float] = []

    def downloader(**_kwargs: object) -> pd.DataFrame:
        nonlocal calls
        calls += 1

        if calls == 1:
            raise TimeoutError("temporary timeout")

        return valid_frame()

    def sample_jitter(lower: float, upper: float) -> float:
        sampled_bounds.append((lower, upper))
        return (lower + upper) / 2.0

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
        execution_policy=policy_without_rate_limit(
            max_attempts=2,
            base_delay_seconds=2.0,
            max_delay_seconds=2.0,
            jitter_ratio=0.25,
        ),
        sleeper=slept.append,
        jitter_sampler=sample_jitter,
    )

    result = request_bars(provider)

    assert calls == 2
    assert sampled_bounds == [(1.5, 2.5)]
    assert slept == [2.0]
    assert result.issues == {}


def test_exhausted_throttling_maps_to_stable_provider_issue() -> None:
    calls = 0
    fake_time = FakeTime()

    def downloader(**_kwargs: object) -> pd.DataFrame:
        nonlocal calls
        calls += 1
        raise YFRateLimitError(
            "too many requests",
            retry_after_seconds=5.0,
        )

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
        execution_policy=policy_without_rate_limit(
            max_attempts=2,
            base_delay_seconds=0.5,
            max_delay_seconds=8.0,
            jitter_ratio=0.0,
        ),
        sleeper=fake_time.sleep,
        jitter_sampler=lambda lower, _upper: lower,
    )

    result = request_bars(provider)

    assert calls == 2
    assert fake_time.sleeps == [5.0]
    assert ASSET_ID not in result.frames
    assert result.issues[ASSET_ID].code == YFinanceProviderIssueCode.THROTTLED


def test_non_retryable_download_failure_is_not_retried() -> None:
    calls = 0
    slept: list[float] = []

    def downloader(**_kwargs: object) -> pd.DataFrame:
        nonlocal calls
        calls += 1
        raise RuntimeError("permanent provider failure")

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
        execution_policy=policy_without_rate_limit(max_attempts=5),
        sleeper=slept.append,
        jitter_sampler=lambda lower, _upper: lower,
    )

    result = request_bars(provider)

    assert calls == 1
    assert slept == []
    assert result.issues[ASSET_ID].code == YFinanceProviderIssueCode.PROVIDER_ERROR


def test_data_quality_failure_occurs_outside_retry_loop() -> None:
    calls = 0
    slept: list[float] = []

    def downloader(**_kwargs: object) -> pd.DataFrame:
        nonlocal calls
        calls += 1
        frame = valid_frame()
        frame.loc[:, "Open"] = 0.0
        return frame

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
        execution_policy=policy_without_rate_limit(max_attempts=5),
        sleeper=slept.append,
        jitter_sampler=lambda lower, _upper: lower,
    )

    result = request_bars(provider)

    assert calls == 1
    assert slept == []
    assert result.issues[ASSET_ID].code == YFinanceProviderIssueCode.DATA_QUALITY_ERROR


def test_instance_rate_limit_delays_second_download_attempt() -> None:
    calls = 0
    fake_time = FakeTime()

    def downloader(**_kwargs: object) -> pd.DataFrame:
        nonlocal calls
        calls += 1
        return valid_frame()

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
        execution_policy=ProviderExecutionPolicy(
            retry=ProviderRetryPolicy(max_attempts=1),
            rate_limit=ProviderRateLimitPolicy(
                max_requests=1,
                window_seconds=1.0,
            ),
        ),
        sleeper=fake_time.sleep,
        monotonic_clock=fake_time.monotonic,
    )

    first_result = request_bars(provider)
    second_result = request_bars(provider)

    assert calls == 2
    assert fake_time.sleeps == [1.0]
    assert first_result.issues == {}
    assert second_result.issues == {}
