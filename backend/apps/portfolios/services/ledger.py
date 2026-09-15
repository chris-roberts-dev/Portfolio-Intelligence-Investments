"""Deterministic transaction-ledger replay and cash accounting.

Development guide references: Sections 10.1-10.3.

The transaction ledger is authoritative for owned-portfolio quantities and cash.
Replay uses Decimal arithmetic and deterministic transaction ordering. Deposits
and withdrawals are external cash flows; buys, sells, and dividends are
internal portfolio cash movements.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from apps.portfolios.models import Portfolio, Transaction, TransactionType

ZERO = Decimal("0")


class LedgerReplayError(ValueError):
    """Base error for invalid ledger state encountered during replay."""


class NegativePositionError(LedgerReplayError):
    """Raised when a SELL would create a negative long-only position."""


class CashFlowClassification(StrEnum):
    """Performance-relevant cash-flow classification."""

    EXTERNAL = "EXTERNAL"
    INTERNAL = "INTERNAL"


@dataclass(frozen=True, slots=True)
class PositionQuantity:
    """One non-zero security quantity produced by ledger replay."""

    asset_id: UUID
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class LedgerCashFlow:
    """One signed cash movement produced by a ledger transaction."""

    transaction_id: UUID
    occurred_at: datetime
    source_sequence: int
    transaction_type: TransactionType
    classification: CashFlowClassification
    amount: Decimal


@dataclass(frozen=True, slots=True)
class LedgerReplayResult:
    """Deterministic holdings and cash state derived from the transaction ledger."""

    portfolio_id: UUID
    as_of: datetime | None
    cash_balance: Decimal
    positions: tuple[PositionQuantity, ...]
    cash_flows: tuple[LedgerCashFlow, ...]
    net_external_cash_flow: Decimal
    net_internal_cash_flow: Decimal
    transaction_count: int


def replay_portfolio_ledger(
    portfolio: Portfolio,
    *,
    as_of: datetime | None = None,
) -> LedgerReplayResult:
    """Replay one portfolio ledger through an optional inclusive as-of time."""
    if not isinstance(portfolio, Portfolio):
        raise TypeError("portfolio must be a Portfolio")

    transactions = Transaction.objects.for_portfolio(portfolio).through(as_of).ordered_for_replay()

    return _replay_transactions(
        portfolio_id=portfolio.id,
        transactions=transactions,
        as_of=as_of,
    )


def _replay_transactions(
    *,
    portfolio_id: UUID,
    transactions: Iterable[Transaction],
    as_of: datetime | None,
) -> LedgerReplayResult:
    quantities: dict[UUID, Decimal] = {}
    cash_balance = ZERO
    net_external_cash_flow = ZERO
    net_internal_cash_flow = ZERO
    cash_flows: list[LedgerCashFlow] = []
    transaction_count = 0

    for ledger_entry in transactions:
        transaction_count += 1

        try:
            transaction_type = TransactionType(ledger_entry.transaction_type)
        except ValueError as exc:
            raise LedgerReplayError(
                f"Unsupported transaction type {ledger_entry.transaction_type!r}."
            ) from exc

        if transaction_type == TransactionType.DEPOSIT:
            cash_change = _required_decimal(
                ledger_entry.cash_amount,
                field_name="cash_amount",
                transaction_id=ledger_entry.id,
            )
            classification = CashFlowClassification.EXTERNAL
            net_external_cash_flow += cash_change

        elif transaction_type == TransactionType.WITHDRAWAL:
            cash_amount = _required_decimal(
                ledger_entry.cash_amount,
                field_name="cash_amount",
                transaction_id=ledger_entry.id,
            )
            cash_change = -cash_amount
            classification = CashFlowClassification.EXTERNAL
            net_external_cash_flow += cash_change

        elif transaction_type == TransactionType.BUY:
            asset_id = _required_asset_id(ledger_entry)
            quantity = _required_decimal(
                ledger_entry.quantity,
                field_name="quantity",
                transaction_id=ledger_entry.id,
            )
            price = _required_decimal(
                ledger_entry.price,
                field_name="price",
                transaction_id=ledger_entry.id,
            )
            fees = _required_decimal(
                ledger_entry.fees,
                field_name="fees",
                transaction_id=ledger_entry.id,
            )

            quantities[asset_id] = quantities.get(asset_id, ZERO) + quantity
            cash_change = -(quantity * price + fees)
            classification = CashFlowClassification.INTERNAL
            net_internal_cash_flow += cash_change

        elif transaction_type == TransactionType.SELL:
            asset_id = _required_asset_id(ledger_entry)
            quantity = _required_decimal(
                ledger_entry.quantity,
                field_name="quantity",
                transaction_id=ledger_entry.id,
            )
            price = _required_decimal(
                ledger_entry.price,
                field_name="price",
                transaction_id=ledger_entry.id,
            )
            fees = _required_decimal(
                ledger_entry.fees,
                field_name="fees",
                transaction_id=ledger_entry.id,
            )
            current_quantity = quantities.get(asset_id, ZERO)
            ending_quantity = current_quantity - quantity

            if ending_quantity < ZERO:
                raise NegativePositionError(
                    "SELL transaction "
                    f"{ledger_entry.id} would create a negative position "
                    f"for asset {asset_id}."
                )

            quantities[asset_id] = ending_quantity
            cash_change = quantity * price - fees
            classification = CashFlowClassification.INTERNAL
            net_internal_cash_flow += cash_change

        elif transaction_type == TransactionType.DIVIDEND:
            _required_asset_id(ledger_entry)
            cash_change = _required_decimal(
                ledger_entry.cash_amount,
                field_name="cash_amount",
                transaction_id=ledger_entry.id,
            )
            classification = CashFlowClassification.INTERNAL
            net_internal_cash_flow += cash_change

        cash_balance += cash_change
        cash_flows.append(
            LedgerCashFlow(
                transaction_id=ledger_entry.id,
                occurred_at=ledger_entry.occurred_at,
                source_sequence=ledger_entry.source_sequence,
                transaction_type=transaction_type,
                classification=classification,
                amount=cash_change,
            )
        )

    positions = tuple(
        PositionQuantity(
            asset_id=asset_id,
            quantity=quantity,
        )
        for asset_id, quantity in sorted(
            quantities.items(),
            key=lambda item: item[0].hex,
        )
        if quantity != ZERO
    )

    return LedgerReplayResult(
        portfolio_id=portfolio_id,
        as_of=as_of,
        cash_balance=cash_balance,
        positions=positions,
        cash_flows=tuple(cash_flows),
        net_external_cash_flow=net_external_cash_flow,
        net_internal_cash_flow=net_internal_cash_flow,
        transaction_count=transaction_count,
    )


def _required_asset_id(
    ledger_entry: Transaction,
) -> UUID:
    asset_id = ledger_entry.asset_id

    if asset_id is None:
        raise LedgerReplayError(f"Transaction {ledger_entry.id} requires an asset.")

    return asset_id


def _required_decimal(
    value: Decimal | None,
    *,
    field_name: str,
    transaction_id: UUID,
) -> Decimal:
    if value is None:
        raise LedgerReplayError(f"Transaction {transaction_id} requires {field_name}.")

    return value
