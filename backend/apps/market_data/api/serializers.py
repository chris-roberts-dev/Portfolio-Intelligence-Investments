"""Explicit DRF serializers for bounded market-bar request and response contracts."""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail

from apps.market_data.contracts import (
    MarketBarBatchMeta,
    MarketBarBatchResult,
    MarketBarInterval,
    MarketBarQueryError,
    MarketBarStatus,
    MarketBarSymbolResult,
    NormalizedMarketBarQuery,
    normalize_market_bar_query,
)
from portfolio_engine.contracts.market_data import PriceBar


class MarketBarQuerySerializer(serializers.Serializer[object]):
    """Transport contract for a bounded daily market-bar request."""

    symbols = serializers.ListField(
        child=serializers.CharField(
            allow_blank=True,
            trim_whitespace=False,
        ),
        allow_empty=True,
    )
    start = serializers.DateField()
    end = serializers.DateField()
    interval = serializers.CharField(
        required=False,
        default=MarketBarInterval.DAILY.value,
        allow_blank=True,
        trim_whitespace=False,
    )
    provider = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        trim_whitespace=False,
    )

    _normalized_query: NormalizedMarketBarQuery | None = None

    @property
    def normalized_query(self) -> NormalizedMarketBarQuery:
        """Return the authoritative normalized application contract."""
        if self._normalized_query is None:
            raise RuntimeError("normalized_query is available only after successful validation.")

        return self._normalized_query

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Delegate normalization and bounds to the application contract."""
        symbols = cast(list[str], attrs["symbols"])
        start = cast(date, attrs["start"])
        end = cast(date, attrs["end"])
        interval = cast(str, attrs["interval"])
        provider = cast(str | None, attrs.get("provider"))

        try:
            normalized_query = normalize_market_bar_query(
                symbols,
                start=start,
                end=end,
                interval=interval,
                provider=provider,
            )
        except MarketBarQueryError as exc:
            raise serializers.ValidationError(
                {
                    exc.field: [
                        ErrorDetail(
                            str(exc),
                            code=exc.code.value,
                        )
                    ]
                }
            ) from exc

        self._normalized_query = normalized_query
        attrs["symbols"] = list(normalized_query.symbols)
        attrs["interval"] = normalized_query.interval.value
        attrs["provider"] = normalized_query.provider
        return attrs


class PriceBarSerializer(serializers.Serializer[PriceBar]):
    """Read-only transport representation of one canonical daily price bar."""

    asset_id = serializers.UUIDField(read_only=True)
    trade_date = serializers.DateField(read_only=True)
    open = serializers.FloatField(read_only=True, allow_null=True)
    high = serializers.FloatField(read_only=True, allow_null=True)
    low = serializers.FloatField(read_only=True, allow_null=True)
    close = serializers.FloatField(read_only=True, allow_null=True)
    adjusted_close = serializers.FloatField(read_only=True, allow_null=True)
    volume = serializers.IntegerField(read_only=True, allow_null=True)
    source = cast(Any, serializers.CharField(read_only=True))
    retrieved_at = serializers.DateTimeField(read_only=True)


class MarketBarSymbolResultSerializer(serializers.Serializer[MarketBarSymbolResult]):
    """Read-only transport representation for one requested symbol."""

    symbol = serializers.CharField(read_only=True)
    asset_id = serializers.UUIDField(read_only=True, allow_null=True)
    status = serializers.ChoiceField(
        choices=[status.value for status in MarketBarStatus],
        read_only=True,
    )
    bars = PriceBarSerializer(many=True, read_only=True)
    warnings = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )


class MarketBarBatchMetaSerializer(serializers.Serializer[MarketBarBatchMeta]):
    """Read-only shared provenance for a market-bar result batch."""

    provider = serializers.CharField(read_only=True)
    retrieved_at = serializers.DateTimeField(read_only=True)
    interval = serializers.ChoiceField(
        choices=[interval.value for interval in MarketBarInterval],
        read_only=True,
    )
    start = serializers.DateField(read_only=True)
    end = serializers.DateField(read_only=True)


class MarketBarBatchResultSerializer(serializers.Serializer[MarketBarBatchResult]):
    """Read-only ordered application result contract."""

    results = MarketBarSymbolResultSerializer(many=True, read_only=True)
    meta = MarketBarBatchMetaSerializer(read_only=True)
    row_count = serializers.IntegerField(read_only=True)


class MarketBarValidationErrorSerializer(serializers.Serializer[object]):
    """Stable transport shape for request/provider-selection validation errors."""

    code = serializers.CharField(read_only=True)
    errors = cast(
        Any,
        serializers.DictField(
            child=serializers.ListField(child=serializers.CharField()),
            read_only=True,
        ),
    )


class MarketBarApiErrorSerializer(serializers.Serializer[object]):
    """Stable transport shape for application/provider-system errors."""

    code = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True)
