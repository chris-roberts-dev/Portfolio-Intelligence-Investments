"""Explicit request and error serializers for owned-portfolio read APIs."""

from __future__ import annotations

import math
from datetime import date
from typing import Any, cast

from rest_framework import serializers

from portfolio_engine.config import DEFAULT_MAR_ANNUAL, DEFAULT_RISK_FREE_RATE


class PortfolioProviderQuerySerializer(serializers.Serializer[object]):
    """Optional provider selection for provider-backed portfolio reads."""

    provider = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=False,
        trim_whitespace=True,
    )

    @property
    def requested_provider(self) -> str | None:
        """Return the normalized explicit provider, when supplied."""
        provider = cast(str | None, self.validated_data.get("provider"))
        return provider.lower() if provider is not None else None


class PortfolioAnalyticsQuerySerializer(PortfolioProviderQuerySerializer):
    """Bounded date/assumption query for owned-portfolio analytics.

    ``start`` is inclusive and ``end`` is exclusive. Daily valuation points
    are generated only for trading sessions inside that interval.
    """

    start = serializers.DateField()
    end = serializers.DateField()
    risk_free_rate_annual = serializers.FloatField(
        required=False,
        default=DEFAULT_RISK_FREE_RATE,
    )
    minimum_acceptable_return_annual = serializers.FloatField(
        required=False,
        default=DEFAULT_MAR_ANNUAL,
    )

    @property
    def start_date(self) -> date:
        return cast(date, self.validated_data["start"])

    @property
    def end_date(self) -> date:
        return cast(date, self.validated_data["end"])

    @property
    def risk_free_rate_annual_value(self) -> float:
        return cast(float, self.validated_data["risk_free_rate_annual"])

    @property
    def minimum_acceptable_return_annual_value(self) -> float:
        return cast(float, self.validated_data["minimum_acceptable_return_annual"])

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        start = cast(date, attrs["start"])
        end = cast(date, attrs["end"])

        if end <= start:
            raise serializers.ValidationError(
                {"end": ["end must be after start; end is exclusive."]}
            )

        return attrs

    def validate_risk_free_rate_annual(self, value: float) -> float:
        return _validate_annual_effective_rate(
            value,
            field_name="risk_free_rate_annual",
        )

    def validate_minimum_acceptable_return_annual(self, value: float) -> float:
        return _validate_annual_effective_rate(
            value,
            field_name="minimum_acceptable_return_annual",
        )


class PortfolioValidationErrorSerializer(serializers.Serializer[object]):
    """Stable transport shape for portfolio request validation errors."""

    code = serializers.CharField(read_only=True)
    errors = cast(
        Any,
        serializers.DictField(
            child=serializers.ListField(child=serializers.CharField()),
            read_only=True,
        ),
    )


class PortfolioApiErrorSerializer(serializers.Serializer[object]):
    """Stable transport shape for portfolio application/system errors."""

    code = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True)


def _validate_annual_effective_rate(
    value: float,
    *,
    field_name: str,
) -> float:
    if not math.isfinite(value):
        raise serializers.ValidationError(f"{field_name} must be finite.")

    if value < -1.0:
        raise serializers.ValidationError(f"{field_name} must be greater than or equal to -1.")

    return value
