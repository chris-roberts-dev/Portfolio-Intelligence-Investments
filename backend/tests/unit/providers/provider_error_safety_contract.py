"""Reusable assertions for provider error-safety behavior."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from apps.market_data.providers.base import ProviderBatchResult
from apps.market_data.providers.safety import REDACTED_PROVIDER_VALUE


@dataclass(frozen=True, slots=True)
class ProviderErrorSafetyContract:
    """Expected externally visible safety behavior for one provider failure."""

    asset_id: UUID
    expected_code: str

    def assert_safe_result(
        self,
        result: ProviderBatchResult,
        *,
        secret: str,
    ) -> None:
        issue = result.issues[self.asset_id]

        assert issue.code == self.expected_code
        assert secret not in issue.message
        assert REDACTED_PROVIDER_VALUE in issue.message
        assert self.asset_id not in result.frames
