"""Deterministic analytical book accounting from the transaction ledger.

This service implements dashboard accounting only. It is not tax-lot accounting
and must not be presented as tax-reporting basis.

Methodology:
- lifetime net contributions = DEPOSIT - WITHDRAWAL through ``as_of``;
- BUY adds quantity * execution price + fees to open book cost;
- SELL removes weighted-average open book cost for the sold quantity;
- SELL realized gain/loss = net sale proceeds - removed book cost;
- DIVIDEND is portfolio income and does not change security book cost;
- selected-period realized gain/loss and income use inclusive-start,
  exclusive-end transaction timestamps and never include transactions after
  ``as_of``;
- Decimal arithmetic is preserved throughout.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from django.utils import timezone

from apps.portfolios.models import Portfolio, Transaction, TransactionType

ZERO = Decimal("0")

ANALYTICAL_BOOK_COST_METHOD = "WEIGHTED_AVERAGE_BOOK_COST_V1"

BOOK_ACCOUNTING_ASSUMPTIONS = (
    "Open security basis uses weighted-average analytical book cost.",
    "BUY fees are capitalized into open security book cost.",
    "SELL fees reduce realized sale proceeds.",
    "DIVIDEND cash is income and does not alter security book cost.",
    "This analytical book cost is not tax-lot or tax-reporting basis.",
)


class BookAccountingError(ValueError):
    """Raised when ledger data cannot satisfy analytical book accounting."""


class BookAccountingUnavailableReason(StrEnum):
    """Stable reason a selected-period accounting metric is unavailable."""

    SELECTED_PERIOD_NOT_STARTED = "SELECTED_PERIOD_NOT_STARTED"


@dataclass(frozen=True, slots=True)
class BookAccountingEvent:
    """One deterministic ledger event consumed by book accounting."""

    transaction_id: UUID
    occurred_at: datetime
    source_sequence: int
    transaction_type: TransactionType
    asset_id: UUID | None = None
    quantity: Decimal | None = None
    price: Decimal | None = None
    fees: Decimal = ZERO
    cash_amount: Decimal | None = None


@dataclass(frozen=True, slots=True)
class BookCostPosition:
    """One open position's analytical weighted-average book cost."""

    asset_id: UUID
    quantity: Decimal
    cost_basis: Decimal
    average_unit_cost: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioBookAccountingResult:
    """Immutable analytical accounting result through one ledger as-of time."""

    portfolio_id: UUID
    as_of: datetime
    positions: tuple[BookCostPosition, ...]
    total_open_cost_basis: Decimal
    net_contributions: Decimal
    selected_period_realized_gain_loss: Decimal | None
    selected_period_income: Decimal | None
    selected_period_unavailable_reason: BookAccountingUnavailableReason | None
    accounting_method: str = ANALYTICAL_BOOK_COST_METHOD
    assumptions: tuple[str, ...] = BOOK_ACCOUNTING_ASSUMPTIONS


def calculate_portfolio_book_accounting(
    portfolio: Portfolio,
    *,
    as_of: datetime,
    period_start: datetime,
    period_end_exclusive: datetime,
) -> PortfolioBookAccountingResult:
    """Calculate analytical book accounting from one owned ledger."""
    if not isinstance(portfolio, Portfolio):
        raise TypeError("portfolio must be a Portfolio")

    transactions = Transaction.objects.for_portfolio(portfolio).through(as_of).ordered_for_replay()
    events = tuple(_event_from_transaction(transaction) for transaction in transactions)

    return calculate_book_accounting_events(
        portfolio_id=portfolio.id,
        events=events,
        as_of=as_of,
        period_start=period_start,
        period_end_exclusive=period_end_exclusive,
    )


def calculate_book_accounting_events(
    *,
    portfolio_id: UUID,
    events: Iterable[BookAccountingEvent],
    as_of: datetime,
    period_start: datetime,
    period_end_exclusive: datetime,
) -> PortfolioBookAccountingResult:
    """Calculate weighted-average book accounting without database access."""
    _validate_times(
        as_of=as_of,
        period_start=period_start,
        period_end_exclusive=period_end_exclusive,
    )

    ordered_events = tuple(
        sorted(
            events,
            key=lambda event: (
                event.occurred_at,
                event.source_sequence,
                event.transaction_id.hex,
            ),
        )
    )
    quantities: dict[UUID, Decimal] = {}
    cost_bases: dict[UUID, Decimal] = {}
    net_contributions = ZERO

    selected_period_started = as_of >= period_start
    selected_realized_gain_loss: Decimal | None = ZERO if selected_period_started else None
    selected_income: Decimal | None = ZERO if selected_period_started else None

    for event in ordered_events:
        if timezone.is_naive(event.occurred_at):
            raise BookAccountingError(
                f"Transaction {event.transaction_id} occurred_at must be timezone-aware."
            )

        if event.occurred_at > as_of:
            continue

        transaction_type = TransactionType(event.transaction_type)
        in_selected_period = period_start <= event.occurred_at < period_end_exclusive

        if transaction_type is TransactionType.DEPOSIT:
            net_contributions += _required_positive_decimal(
                event.cash_amount,
                field_name="cash_amount",
                transaction_id=event.transaction_id,
            )
            continue

        if transaction_type is TransactionType.WITHDRAWAL:
            net_contributions -= _required_positive_decimal(
                event.cash_amount,
                field_name="cash_amount",
                transaction_id=event.transaction_id,
            )
            continue

        asset_id = _required_asset_id(event)

        if transaction_type is TransactionType.BUY:
            quantity = _required_positive_decimal(
                event.quantity,
                field_name="quantity",
                transaction_id=event.transaction_id,
            )
            price = _required_positive_decimal(
                event.price,
                field_name="price",
                transaction_id=event.transaction_id,
            )
            fees = _required_nonnegative_decimal(
                event.fees,
                field_name="fees",
                transaction_id=event.transaction_id,
            )
            quantities[asset_id] = quantities.get(asset_id, ZERO) + quantity
            cost_bases[asset_id] = cost_bases.get(asset_id, ZERO) + (quantity * price + fees)
            continue

        if transaction_type is TransactionType.SELL:
            quantity = _required_positive_decimal(
                event.quantity,
                field_name="quantity",
                transaction_id=event.transaction_id,
            )
            price = _required_positive_decimal(
                event.price,
                field_name="price",
                transaction_id=event.transaction_id,
            )
            fees = _required_nonnegative_decimal(
                event.fees,
                field_name="fees",
                transaction_id=event.transaction_id,
            )
            open_quantity = quantities.get(asset_id, ZERO)
            open_cost_basis = cost_bases.get(asset_id, ZERO)

            if quantity > open_quantity:
                raise BookAccountingError(
                    f"SELL transaction {event.transaction_id} exceeds the "
                    f"open quantity for asset {asset_id}."
                )

            if quantity == open_quantity:
                removed_cost_basis = open_cost_basis
                ending_quantity = ZERO
                ending_cost_basis = ZERO
            else:
                removed_cost_basis = open_cost_basis * quantity / open_quantity
                ending_quantity = open_quantity - quantity
                ending_cost_basis = open_cost_basis - removed_cost_basis

            quantities[asset_id] = ending_quantity
            cost_bases[asset_id] = ending_cost_basis

            if in_selected_period and selected_realized_gain_loss is not None:
                net_proceeds = quantity * price - fees
                selected_realized_gain_loss += net_proceeds - removed_cost_basis

            continue

        if transaction_type is TransactionType.DIVIDEND:
            income = _required_positive_decimal(
                event.cash_amount,
                field_name="cash_amount",
                transaction_id=event.transaction_id,
            )

            if in_selected_period and selected_income is not None:
                selected_income += income

            continue

        raise BookAccountingError(f"Unsupported transaction type {transaction_type!r}.")

    positions = tuple(
        BookCostPosition(
            asset_id=asset_id,
            quantity=quantity,
            cost_basis=cost_bases[asset_id],
            average_unit_cost=cost_bases[asset_id] / quantity,
        )
        for asset_id, quantity in sorted(
            quantities.items(),
            key=lambda item: item[0].hex,
        )
        if quantity != ZERO
    )
    total_open_cost_basis = sum(
        (position.cost_basis for position in positions),
        ZERO,
    )

    unavailable_reason = (
        None
        if selected_period_started
        else BookAccountingUnavailableReason.SELECTED_PERIOD_NOT_STARTED
    )

    return PortfolioBookAccountingResult(
        portfolio_id=portfolio_id,
        as_of=as_of,
        positions=positions,
        total_open_cost_basis=total_open_cost_basis,
        net_contributions=net_contributions,
        selected_period_realized_gain_loss=selected_realized_gain_loss,
        selected_period_income=selected_income,
        selected_period_unavailable_reason=unavailable_reason,
    )


def _event_from_transaction(transaction: Transaction) -> BookAccountingEvent:
    try:
        transaction_type = TransactionType(transaction.transaction_type)
    except ValueError as exc:
        raise BookAccountingError(
            f"Unsupported transaction type {transaction.transaction_type!r}."
        ) from exc

    return BookAccountingEvent(
        transaction_id=transaction.id,
        occurred_at=transaction.occurred_at,
        source_sequence=transaction.source_sequence,
        transaction_type=transaction_type,
        asset_id=transaction.asset_id,
        quantity=transaction.quantity,
        price=transaction.price,
        fees=transaction.fees,
        cash_amount=transaction.cash_amount,
    )


def _validate_times(
    *,
    as_of: datetime,
    period_start: datetime,
    period_end_exclusive: datetime,
) -> None:
    for field_name, value in (
        ("as_of", as_of),
        ("period_start", period_start),
        ("period_end_exclusive", period_end_exclusive),
    ):
        if timezone.is_naive(value):
            raise BookAccountingError(f"{field_name} must be timezone-aware")

    if period_start >= period_end_exclusive:
        raise BookAccountingError("period_start must be earlier than period_end_exclusive")


def _required_asset_id(event: BookAccountingEvent) -> UUID:
    if event.asset_id is None:
        raise BookAccountingError(f"Transaction {event.transaction_id} requires an asset.")

    return event.asset_id


def _required_positive_decimal(
    value: Decimal | None,
    *,
    field_name: str,
    transaction_id: UUID,
) -> Decimal:
    if value is None or value <= ZERO:
        raise BookAccountingError(f"Transaction {transaction_id} requires positive {field_name}.")

    return value


def _required_nonnegative_decimal(
    value: Decimal | None,
    *,
    field_name: str,
    transaction_id: UUID,
) -> Decimal:
    if value is None or value < ZERO:
        raise BookAccountingError(
            f"Transaction {transaction_id} requires non-negative {field_name}."
        )

    return value
