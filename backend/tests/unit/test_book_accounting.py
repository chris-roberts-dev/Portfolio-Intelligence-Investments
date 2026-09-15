"""Focused tests for weighted-average analytical book accounting."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from apps.portfolios.models import TransactionType
from apps.portfolios.services.book_accounting import (
    ANALYTICAL_BOOK_COST_METHOD,
    BookAccountingEvent,
    BookAccountingUnavailableReason,
    calculate_book_accounting_events,
)

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000000901")
ASSET_ID = UUID("00000000-0000-0000-0000-000000000911")


def event(
    *,
    event_id: int,
    occurred_at: datetime,
    transaction_type: TransactionType,
    asset_id: UUID | None = None,
    quantity: str | None = None,
    price: str | None = None,
    fees: str = "0",
    cash_amount: str | None = None,
) -> BookAccountingEvent:
    return BookAccountingEvent(
        transaction_id=UUID(int=event_id),
        occurred_at=occurred_at,
        source_sequence=event_id,
        transaction_type=transaction_type,
        asset_id=asset_id,
        quantity=Decimal(quantity) if quantity is not None else None,
        price=Decimal(price) if price is not None else None,
        fees=Decimal(fees),
        cash_amount=(Decimal(cash_amount) if cash_amount is not None else None),
    )


def test_weighted_average_basis_realized_income_and_net_contributions() -> None:
    result = calculate_book_accounting_events(
        portfolio_id=PORTFOLIO_ID,
        events=(
            event(
                event_id=1,
                occurred_at=datetime(2026, 1, 1, 10, tzinfo=UTC),
                transaction_type=TransactionType.DEPOSIT,
                cash_amount="10000",
            ),
            event(
                event_id=2,
                occurred_at=datetime(2026, 1, 2, 10, tzinfo=UTC),
                transaction_type=TransactionType.BUY,
                asset_id=ASSET_ID,
                quantity="10",
                price="100",
                fees="10",
            ),
            event(
                event_id=3,
                occurred_at=datetime(2026, 1, 3, 10, tzinfo=UTC),
                transaction_type=TransactionType.BUY,
                asset_id=ASSET_ID,
                quantity="10",
                price="120",
                fees="10",
            ),
            event(
                event_id=4,
                occurred_at=datetime(2026, 1, 5, 10, tzinfo=UTC),
                transaction_type=TransactionType.SELL,
                asset_id=ASSET_ID,
                quantity="5",
                price="130",
                fees="5",
            ),
            event(
                event_id=5,
                occurred_at=datetime(2026, 1, 6, 10, tzinfo=UTC),
                transaction_type=TransactionType.DIVIDEND,
                asset_id=ASSET_ID,
                cash_amount="50",
            ),
            event(
                event_id=6,
                occurred_at=datetime(2026, 1, 7, 10, tzinfo=UTC),
                transaction_type=TransactionType.WITHDRAWAL,
                cash_amount="500",
            ),
            event(
                event_id=7,
                occurred_at=datetime(2026, 1, 20, 10, tzinfo=UTC),
                transaction_type=TransactionType.SELL,
                asset_id=ASSET_ID,
                quantity="15",
                price="200",
            ),
        ),
        as_of=datetime(2026, 1, 10, 23, tzinfo=UTC),
        period_start=datetime(2026, 1, 5, 0, tzinfo=UTC),
        period_end_exclusive=datetime(2026, 1, 7, 0, tzinfo=UTC),
    )

    assert result.accounting_method == ANALYTICAL_BOOK_COST_METHOD
    assert result.net_contributions == Decimal("9500")
    assert result.selected_period_realized_gain_loss == Decimal("90")
    assert result.selected_period_income == Decimal("50")
    assert result.selected_period_unavailable_reason is None
    assert len(result.positions) == 1

    position = result.positions[0]
    assert position.asset_id == ASSET_ID
    assert position.quantity == Decimal("15")
    assert position.cost_basis == Decimal("1665")
    assert position.average_unit_cost == Decimal("111")
    assert result.total_open_cost_basis == Decimal("1665")


def test_full_sale_removes_exact_remaining_basis() -> None:
    result = calculate_book_accounting_events(
        portfolio_id=PORTFOLIO_ID,
        events=(
            event(
                event_id=1,
                occurred_at=datetime(2026, 1, 2, 10, tzinfo=UTC),
                transaction_type=TransactionType.BUY,
                asset_id=ASSET_ID,
                quantity="3",
                price="10",
                fees="1",
            ),
            event(
                event_id=2,
                occurred_at=datetime(2026, 1, 3, 10, tzinfo=UTC),
                transaction_type=TransactionType.SELL,
                asset_id=ASSET_ID,
                quantity="3",
                price="12",
                fees="1",
            ),
        ),
        as_of=datetime(2026, 1, 4, 23, tzinfo=UTC),
        period_start=datetime(2026, 1, 1, 0, tzinfo=UTC),
        period_end_exclusive=datetime(2026, 1, 5, 0, tzinfo=UTC),
    )

    assert result.positions == ()
    assert result.total_open_cost_basis == Decimal("0")
    assert result.selected_period_realized_gain_loss == Decimal("4")


def test_future_transactions_never_affect_as_of_accounting() -> None:
    result = calculate_book_accounting_events(
        portfolio_id=PORTFOLIO_ID,
        events=(
            event(
                event_id=1,
                occurred_at=datetime(2026, 1, 2, 10, tzinfo=UTC),
                transaction_type=TransactionType.BUY,
                asset_id=ASSET_ID,
                quantity="1",
                price="100",
            ),
            event(
                event_id=2,
                occurred_at=datetime(2026, 2, 1, 10, tzinfo=UTC),
                transaction_type=TransactionType.SELL,
                asset_id=ASSET_ID,
                quantity="1",
                price="1000",
            ),
        ),
        as_of=datetime(2026, 1, 10, 23, tzinfo=UTC),
        period_start=datetime(2026, 1, 1, 0, tzinfo=UTC),
        period_end_exclusive=datetime(2026, 3, 1, 0, tzinfo=UTC),
    )

    assert result.positions[0].quantity == Decimal("1")
    assert result.total_open_cost_basis == Decimal("100")
    assert result.selected_period_realized_gain_loss == Decimal("0")


def test_future_only_selected_period_is_explicitly_unavailable() -> None:
    result = calculate_book_accounting_events(
        portfolio_id=PORTFOLIO_ID,
        events=(),
        as_of=datetime(2026, 1, 10, 23, tzinfo=UTC),
        period_start=datetime(2026, 2, 1, 0, tzinfo=UTC),
        period_end_exclusive=datetime(2026, 3, 1, 0, tzinfo=UTC),
    )

    assert result.selected_period_realized_gain_loss is None
    assert result.selected_period_income is None
    assert (
        result.selected_period_unavailable_reason
        is BookAccountingUnavailableReason.SELECTED_PERIOD_NOT_STARTED
    )
