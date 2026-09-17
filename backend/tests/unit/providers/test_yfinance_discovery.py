"""Unit coverage for the yfinance asset-discovery adapter."""

from __future__ import annotations

from collections.abc import Mapping

from apps.market_data.providers.discovery_base import (
    AssetDiscoveryIssue,
    AssetDiscoveryIssueCode,
    DiscoveredAssetType,
    DiscoveredProviderAsset,
)
from apps.market_data.providers.yfinance_discovery import (
    YFinanceAssetDiscoveryProvider,
)


def metadata(
    symbol: str,
    *,
    quote_type: str = "EQUITY",
    currency: str = "USD",
    exchange: str = "NasdaqGS",
    name: str | None = None,
) -> Mapping[str, object]:
    return {
        "symbol": symbol,
        "quoteType": quote_type,
        "currency": currency,
        "fullExchangeName": exchange,
        "longName": name or f"{symbol} Security",
    }


def test_discovers_exact_supported_stock_and_etf_in_request_order() -> None:
    records = {
        "AAPL": metadata("AAPL"),
        "QQQ": metadata(
            "QQQ",
            quote_type="ETF",
            exchange="NasdaqGM",
            name="Invesco QQQ Trust",
        ),
    }
    calls: list[str] = []

    def loader(symbol: str) -> Mapping[str, object] | None:
        calls.append(symbol)
        return records.get(symbol)

    result = YFinanceAssetDiscoveryProvider(
        metadata_loader=loader,
    ).discover((" qqq ", "AAPL", "qqq"))

    assert calls == ["QQQ", "AAPL"]
    assert result.provider == "yfinance"
    assert result.outcomes == (
        DiscoveredProviderAsset(
            requested_symbol="QQQ",
            canonical_symbol="QQQ",
            provider_symbol="QQQ",
            name="Invesco QQQ Trust",
            asset_type=DiscoveredAssetType.ETF,
            exchange="NasdaqGM",
            currency="USD",
        ),
        DiscoveredProviderAsset(
            requested_symbol="AAPL",
            canonical_symbol="AAPL",
            provider_symbol="AAPL",
            name="AAPL Security",
            asset_type=DiscoveredAssetType.STOCK,
            exchange="NasdaqGS",
            currency="USD",
        ),
    )


def test_missing_exact_symbol_is_not_found_without_fuzzy_substitution() -> None:
    result = YFinanceAssetDiscoveryProvider(
        metadata_loader=lambda _symbol: metadata("QQQ"),
    ).discover(("QQQQ",))

    issue = result.outcomes[0]
    assert isinstance(issue, AssetDiscoveryIssue)
    assert issue.code is AssetDiscoveryIssueCode.NOT_FOUND


def test_unsupported_instrument_type_remains_explicit() -> None:
    result = YFinanceAssetDiscoveryProvider(
        metadata_loader=lambda symbol: metadata(
            symbol,
            quote_type="CRYPTOCURRENCY",
        ),
    ).discover(("BTC-USD",))

    issue = result.outcomes[0]
    assert isinstance(issue, AssetDiscoveryIssue)
    assert issue.code is AssetDiscoveryIssueCode.UNSUPPORTED_ASSET_TYPE
    assert "only STOCK and ETF" in issue.message


def test_non_usd_security_is_rejected() -> None:
    result = YFinanceAssetDiscoveryProvider(
        metadata_loader=lambda symbol: metadata(
            symbol,
            currency="CAD",
        ),
    ).discover(("SHOP.TO",))

    issue = result.outcomes[0]
    assert isinstance(issue, AssetDiscoveryIssue)
    assert issue.code is AssetDiscoveryIssueCode.UNSUPPORTED_CURRENCY
    assert "CAD" in issue.message


def test_incomplete_metadata_is_failed_explicitly() -> None:
    raw = dict(metadata("QQQ"))
    raw.pop("currency")

    result = YFinanceAssetDiscoveryProvider(
        metadata_loader=lambda _symbol: raw,
    ).discover(("QQQ",))

    issue = result.outcomes[0]
    assert isinstance(issue, AssetDiscoveryIssue)
    assert issue.code is AssetDiscoveryIssueCode.INVALID_METADATA


def test_provider_failure_is_per_symbol_and_sanitized() -> None:
    def loader(symbol: str) -> Mapping[str, object] | None:
        if symbol == "QQQ":
            raise RuntimeError("token=super-secret upstream failed")
        return metadata(symbol)

    result = YFinanceAssetDiscoveryProvider(
        metadata_loader=loader,
    ).discover(("QQQ", "AAPL"))

    first = result.outcomes[0]
    second = result.outcomes[1]

    assert isinstance(first, AssetDiscoveryIssue)
    assert first.code is AssetDiscoveryIssueCode.PROVIDER_ERROR
    assert first.message == "yfinance asset discovery failed for QQQ."
    assert isinstance(second, DiscoveredProviderAsset)
