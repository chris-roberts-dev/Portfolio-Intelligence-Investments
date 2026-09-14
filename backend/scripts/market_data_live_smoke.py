"""Opt-in bounded live smoke test for the yfinance market-data adapter.

This script is intentionally excluded from deterministic pytest/PR CI. Run it
only when live Yahoo Finance access is explicitly desired.
"""

from __future__ import annotations

import json
from datetime import date
from uuid import UUID

from apps.market_data.providers.base import ResolvedProviderAsset
from apps.market_data.providers.yfinance import YFinanceMarketDataProvider
from portfolio_engine.contracts.market_data_validation import validate_price_frame

START = date(2025, 1, 2)
END = date(2025, 1, 10)

ASSETS = (
    ResolvedProviderAsset(
        asset_id=UUID("00000000-0000-0000-0000-000000000201"),
        canonical_symbol="AAPL",
        provider_symbol="AAPL",
    ),
    ResolvedProviderAsset(
        asset_id=UUID("00000000-0000-0000-0000-000000000202"),
        canonical_symbol="MSFT",
        provider_symbol="MSFT",
    ),
)


def main() -> int:
    provider = YFinanceMarketDataProvider()
    batch = provider.get_daily_bars(
        ASSETS,
        START,
        END,
    )

    failures: list[str] = []
    summary: list[dict[str, object]] = []

    for asset in ASSETS:
        issue = batch.issues.get(asset.asset_id)
        frame = batch.frames.get(asset.asset_id)

        if issue is not None:
            failures.append(f"{asset.canonical_symbol}: {issue.code}: {issue.message}")
            continue

        if not frame:
            failures.append(f"{asset.canonical_symbol}: no normalized bars returned")
            continue

        validate_price_frame(frame)

        if any(bar.source != provider.name for bar in frame):
            failures.append(f"{asset.canonical_symbol}: unexpected source provenance")
            continue

        if any(bar.retrieved_at != batch.retrieved_at for bar in frame):
            failures.append(f"{asset.canonical_symbol}: inconsistent retrieval provenance")
            continue

        if any(not START <= bar.trade_date < END for bar in frame):
            failures.append(f"{asset.canonical_symbol}: bar outside requested date bounds")
            continue

        summary.append(
            {
                "symbol": asset.canonical_symbol,
                "bar_count": len(frame),
                "first_date": frame[0].trade_date.isoformat(),
                "last_date": frame[-1].trade_date.isoformat(),
            }
        )

    if failures:
        raise RuntimeError("Live yfinance smoke failed: " + "; ".join(failures))

    if len(summary) != len(ASSETS):
        raise RuntimeError("Live yfinance smoke did not validate every requested symbol.")

    print(
        json.dumps(
            {
                "provider": provider.name,
                "retrieved_at": batch.retrieved_at.isoformat(),
                "start": START.isoformat(),
                "end": END.isoformat(),
                "results": summary,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
