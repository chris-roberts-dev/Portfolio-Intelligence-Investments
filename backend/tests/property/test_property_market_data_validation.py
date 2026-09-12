"""Property tests for canonical market-data validation."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.contracts.market_data import PriceBar, PriceFrame
from portfolio_engine.contracts.market_data_validation import validate_price_frame

ASSET_ID = UUID("00000000-0000-0000-0000-000000000001")
RETRIEVED_AT = datetime(2026, 1, 1, 12, tzinfo=UTC)

DATE_OFFSETS = st.lists(
    st.integers(min_value=0, max_value=3650),
    min_size=1,
    max_size=30,
    unique=True,
).map(sorted)

OPTIONAL_POSITIVE_PRICE = st.one_of(
    st.none(),
    st.floats(
        min_value=0.01,
        max_value=1_000_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)

OPTIONAL_VOLUME = st.one_of(
    st.none(),
    st.integers(min_value=0, max_value=10_000_000_000),
)


@given(
    offsets=DATE_OFFSETS,
    price=OPTIONAL_POSITIVE_PRICE,
    volume=OPTIONAL_VOLUME,
)
def test_valid_generated_frames_are_returned_unchanged(
    offsets: list[int],
    price: float | None,
    volume: int | None,
) -> None:
    frame: PriceFrame = tuple(
        PriceBar(
            asset_id=ASSET_ID,
            trade_date=date(2020, 1, 1) + timedelta(days=offset),
            open=price,
            high=price,
            low=price,
            close=price,
            adjusted_close=price,
            volume=volume,
            source="property-test",
            retrieved_at=RETRIEVED_AT,
        )
        for offset in offsets
    )

    result = validate_price_frame(frame)

    assert result is frame
