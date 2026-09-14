"""Shared provider error-safety tests for implemented provider boundaries."""

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import pytest

from apps.market_data.providers.base import (
    ProviderIssue,
    ResolvedProviderAsset,
)
from apps.market_data.providers.csv import (
    CsvMarketDataProvider,
    CsvProviderIssueCode,
)
from apps.market_data.providers.mock import MockMarketDataProvider
from apps.market_data.providers.safety import (
    REDACTED_PROVIDER_VALUE,
    sanitize_provider_message,
)
from apps.market_data.providers.yfinance import (
    YFinanceMarketDataProvider,
    YFinanceProviderIssueCode,
)
from portfolio_engine.contracts.provider_execution import (
    ProviderExecutionPolicy,
    ProviderRetryPolicy,
)
from tests.unit.providers.provider_error_safety_contract import (
    ProviderErrorSafetyContract,
)

ASSET_ID = UUID("00000000-0000-0000-0000-000000000001")
RETRIEVED_AT = datetime(2026, 1, 5, 12, tzinfo=UTC)
SECRET = "portfolio-provider-secret-123"

ASSET = ResolvedProviderAsset(
    asset_id=ASSET_ID,
    canonical_symbol="AAPL",
    provider_symbol="AAPL",
)


class YFRateLimitError(RuntimeError):
    """Deterministic rate-limit exception matching adapter classification."""

    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def request(provider):
    return provider.get_daily_bars(
        (ASSET,),
        date(2026, 1, 1),
        date(2026, 1, 4),
    )


def assert_logs_do_not_contain_secret(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert all(SECRET not in record.getMessage() for record in caplog.records)


def test_sanitizer_redacts_labeled_and_explicit_sensitive_values() -> None:
    message = f"api_key={SECRET} Authorization: Bearer {SECRET} opaque-value={SECRET}"

    sanitized = sanitize_provider_message(
        message,
        sensitive_values=(SECRET,),
    )

    assert SECRET not in sanitized
    assert REDACTED_PROVIDER_VALUE in sanitized


def test_mock_provider_sanitizes_configured_issue_and_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = MockMarketDataProvider(
        {},
        retrieved_at=RETRIEVED_AT,
        issues={
            ASSET_ID: ProviderIssue(
                code="FAILED",
                message=f"api_key={SECRET}",
            )
        },
    )

    result = request(provider)

    ProviderErrorSafetyContract(
        asset_id=ASSET_ID,
        expected_code="FAILED",
    ).assert_safe_result(
        result,
        secret=SECRET,
    )
    assert_logs_do_not_contain_secret(caplog)


def test_csv_provider_sanitizes_io_error_and_logs(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_path = tmp_path / f"api_key={SECRET}.csv"
    provider = CsvMarketDataProvider(
        {
            "AAPL": secret_path,
        },
        retrieved_at=RETRIEVED_AT,
    )

    result = request(provider)

    ProviderErrorSafetyContract(
        asset_id=ASSET_ID,
        expected_code=CsvProviderIssueCode.CSV_ERROR,
    ).assert_safe_result(
        result,
        secret=SECRET,
    )
    assert_logs_do_not_contain_secret(caplog)


def test_yfinance_provider_sanitizes_provider_error_and_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def downloader(**_kwargs: object):
        raise RuntimeError(f"token={SECRET}")

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
        execution_policy=ProviderExecutionPolicy(
            retry=ProviderRetryPolicy(max_attempts=1),
            rate_limit=None,
        ),
    )

    result = request(provider)

    ProviderErrorSafetyContract(
        asset_id=ASSET_ID,
        expected_code=YFinanceProviderIssueCode.PROVIDER_ERROR,
    ).assert_safe_result(
        result,
        secret=SECRET,
    )
    assert_logs_do_not_contain_secret(caplog)


def test_yfinance_throttling_has_stable_sanitized_issue(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def downloader(**_kwargs: object):
        raise YFRateLimitError(
            f"access_token={SECRET}",
            retry_after_seconds=0.0,
        )

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
        execution_policy=ProviderExecutionPolicy(
            retry=ProviderRetryPolicy(max_attempts=1),
            rate_limit=None,
        ),
    )

    result = request(provider)

    ProviderErrorSafetyContract(
        asset_id=ASSET_ID,
        expected_code=YFinanceProviderIssueCode.THROTTLED,
    ).assert_safe_result(
        result,
        secret=SECRET,
    )
    assert_logs_do_not_contain_secret(caplog)
