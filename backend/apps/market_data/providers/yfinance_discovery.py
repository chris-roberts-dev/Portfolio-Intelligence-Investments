"""yfinance-backed canonical asset discovery adapter.

All yfinance loading remains isolated inside dedicated yfinance provider
adapters. Discovery establishes metadata only; historical prices still flow
through ``YFinanceMarketDataProvider`` and the normal market-bar pipeline.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping, Sequence
from typing import cast

from apps.market_data.providers.discovery_base import (
    AssetDiscoveryIssue,
    AssetDiscoveryIssueCode,
    AssetDiscoveryResult,
    DiscoveredAssetType,
    DiscoveredProviderAsset,
)

type YFinanceMetadataLoader = Callable[[str], Mapping[str, object] | None]


class YFinanceAssetDiscoveryProvider:
    """Discover exact yfinance symbols within the supported USD stock/ETF universe."""

    name = "yfinance"

    def __init__(
        self,
        *,
        metadata_loader: YFinanceMetadataLoader | None = None,
    ) -> None:
        self._metadata_loader = metadata_loader or _load_yfinance_info

    def discover(
        self,
        symbols: Sequence[str],
    ) -> AssetDiscoveryResult:
        """Discover normalized symbols without fuzzy substitution."""
        requested_symbols = _normalize_symbols(symbols)
        outcomes: list[DiscoveredProviderAsset | AssetDiscoveryIssue] = []

        for requested_symbol in requested_symbols:
            try:
                metadata = self._metadata_loader(requested_symbol)
            except Exception:
                outcomes.append(
                    AssetDiscoveryIssue(
                        requested_symbol=requested_symbol,
                        code=AssetDiscoveryIssueCode.PROVIDER_ERROR,
                        message=(f"yfinance asset discovery failed for {requested_symbol}."),
                    )
                )
                continue

            outcomes.append(
                _normalize_discovery_metadata(
                    requested_symbol,
                    metadata,
                )
            )

        return AssetDiscoveryResult(
            provider=self.name,
            outcomes=tuple(outcomes),
        )


def _load_yfinance_info(
    symbol: str,
) -> Mapping[str, object] | None:
    """Load one exact-symbol metadata record through yfinance lazily."""
    yfinance_module = importlib.import_module("yfinance")
    ticker_factory = cast(
        Callable[[str], object],
        yfinance_module.Ticker,
    )
    ticker = ticker_factory(symbol)
    get_info = getattr(ticker, "get_info", None)

    if not callable(get_info):
        raise TypeError("yfinance.Ticker must expose get_info().")

    result = get_info()

    if result is None:
        return None

    if not isinstance(result, Mapping):
        raise TypeError("yfinance Ticker.get_info() must return a mapping or None.")

    return cast(Mapping[str, object], result)


def _normalize_symbols(
    symbols: Sequence[str],
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()

    for raw_symbol in symbols:
        symbol = raw_symbol.strip().upper()

        if not symbol:
            raise ValueError("Asset-discovery symbols must not be blank.")

        if symbol not in seen:
            seen.add(symbol)
            normalized.append(symbol)

    return tuple(normalized)


def _normalize_discovery_metadata(
    requested_symbol: str,
    metadata: Mapping[str, object] | None,
) -> DiscoveredProviderAsset | AssetDiscoveryIssue:
    if not metadata:
        return AssetDiscoveryIssue(
            requested_symbol=requested_symbol,
            code=AssetDiscoveryIssueCode.NOT_FOUND,
            message=f"yfinance did not find an exact symbol match for {requested_symbol}.",
        )

    provider_symbol = _text(metadata.get("symbol")).upper()

    if not provider_symbol or provider_symbol != requested_symbol:
        return AssetDiscoveryIssue(
            requested_symbol=requested_symbol,
            code=AssetDiscoveryIssueCode.NOT_FOUND,
            message=f"yfinance did not find an exact symbol match for {requested_symbol}.",
        )

    quote_type = _text(metadata.get("quoteType")).upper()
    asset_type_by_quote_type = {
        "EQUITY": DiscoveredAssetType.STOCK,
        "ETF": DiscoveredAssetType.ETF,
    }
    asset_type = asset_type_by_quote_type.get(quote_type)

    if asset_type is None:
        label = quote_type or "UNKNOWN"
        return AssetDiscoveryIssue(
            requested_symbol=requested_symbol,
            code=AssetDiscoveryIssueCode.UNSUPPORTED_ASSET_TYPE,
            message=(
                f"{requested_symbol} is a yfinance {label} instrument; "
                "only STOCK and ETF assets are supported."
            ),
        )

    currency = _text(metadata.get("currency")).upper()

    if not currency:
        return AssetDiscoveryIssue(
            requested_symbol=requested_symbol,
            code=AssetDiscoveryIssueCode.INVALID_METADATA,
            message=(
                f"yfinance metadata for {requested_symbol} did not provide a trading currency."
            ),
        )

    if currency != "USD":
        return AssetDiscoveryIssue(
            requested_symbol=requested_symbol,
            code=AssetDiscoveryIssueCode.UNSUPPORTED_CURRENCY,
            message=(
                f"{requested_symbol} trades in {currency}; "
                "the current canonical asset universe supports USD only."
            ),
        )

    exchange = _first_text(
        metadata,
        "fullExchangeName",
        "exchange",
    )

    if not exchange:
        return AssetDiscoveryIssue(
            requested_symbol=requested_symbol,
            code=AssetDiscoveryIssueCode.INVALID_METADATA,
            message=(f"yfinance metadata for {requested_symbol} did not provide an exchange."),
        )

    name = _first_text(
        metadata,
        "longName",
        "shortName",
        "displayName",
    )

    if not name:
        return AssetDiscoveryIssue(
            requested_symbol=requested_symbol,
            code=AssetDiscoveryIssueCode.INVALID_METADATA,
            message=(f"yfinance metadata for {requested_symbol} did not provide a security name."),
        )

    return DiscoveredProviderAsset(
        requested_symbol=requested_symbol,
        canonical_symbol=requested_symbol,
        provider_symbol=provider_symbol,
        name=name,
        asset_type=asset_type,
        exchange=exchange,
        currency=currency,
    )


def _first_text(
    metadata: Mapping[str, object],
    *keys: str,
) -> str:
    for key in keys:
        value = _text(metadata.get(key))

        if value:
            return value

    return ""


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
