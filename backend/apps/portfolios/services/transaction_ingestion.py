"""Owned-portfolio transaction creation and bounded CSV ingestion.

Development guide references: Sections 3.2, 8.6-8.7, 10.1-10.3, and Phase 4.

The existing transaction ledger remains authoritative. This service validates
manual and CSV inputs against the canonical ``Transaction`` model and proves
long-only replay validity with ``replay_portfolio_ledger`` before committing.
It does not calculate holdings, cost basis, returns, or valuation itself.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction as db_transaction
from django.db.models import Max
from django.utils import timezone

from apps.assets.models import Asset
from apps.portfolios.models import Portfolio, Transaction, TransactionType
from apps.portfolios.services.ledger import NegativePositionError, replay_portfolio_ledger

MAX_TRANSACTION_IMPORT_BYTES = 256 * 1024
MAX_TRANSACTION_IMPORT_ROWS = 500
TRANSACTION_IMPORT_COLUMNS = (
    "transaction_type",
    "occurred_at",
    "asset_id",
    "quantity",
    "price",
    "fees",
    "cash_amount",
)
ZERO = Decimal("0")


class TransactionWriteErrorCode(StrEnum):
    """Stable application error codes for one transaction write."""

    ASSET_NOT_FOUND = "ASSET_NOT_FOUND"
    INVALID_TRANSACTION = "INVALID_TRANSACTION"
    NEGATIVE_POSITION = "NEGATIVE_POSITION"
    ORDERING_CONFLICT = "ORDERING_CONFLICT"


class TransactionImportFileErrorCode(StrEnum):
    """Stable whole-file errors that prevent CSV row evaluation."""

    CSV_EMPTY = "CSV_EMPTY"
    CSV_TOO_LARGE = "CSV_TOO_LARGE"
    CSV_HEADER_INVALID = "CSV_HEADER_INVALID"
    CSV_PARSE_ERROR = "CSV_PARSE_ERROR"
    CSV_TOO_MANY_ROWS = "CSV_TOO_MANY_ROWS"


class TransactionImportIssueCode(StrEnum):
    """Stable per-row CSV validation issue codes."""

    REQUIRED = "REQUIRED"
    INVALID_TRANSACTION_TYPE = "INVALID_TRANSACTION_TYPE"
    INVALID_DATETIME = "INVALID_DATETIME"
    TIMEZONE_REQUIRED = "TIMEZONE_REQUIRED"
    INVALID_UUID = "INVALID_UUID"
    INVALID_DECIMAL = "INVALID_DECIMAL"
    NONFINITE_DECIMAL = "NONFINITE_DECIMAL"
    EXTRA_COLUMNS = "EXTRA_COLUMNS"
    ASSET_NOT_FOUND = "ASSET_NOT_FOUND"
    INVALID_TRANSACTION = "INVALID_TRANSACTION"
    NEGATIVE_POSITION = "NEGATIVE_POSITION"
    ORDERING_CONFLICT = "ORDERING_CONFLICT"


class TransactionWriteError(ValueError):
    """Raised when one canonical transaction cannot be committed."""

    def __init__(
        self,
        code: TransactionWriteErrorCode,
        errors: dict[str, tuple[str, ...]],
    ) -> None:
        message = next(
            (item for messages in errors.values() for item in messages),
            code.value,
        )
        super().__init__(message)
        self.code = code
        self.errors = errors


class TransactionImportFileError(ValueError):
    """Raised when CSV structure/bounds prevent row-level preview."""

    def __init__(
        self,
        code: TransactionImportFileErrorCode,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


class TransactionImportValidationError(ValueError):
    """Raised when atomic import confirmation finds invalid rows."""

    def __init__(self, preview: TransactionImportPreview) -> None:
        super().__init__("CSV import contains invalid rows and was not committed.")
        self.preview = preview


@dataclass(frozen=True, slots=True)
class TransactionWriteInput:
    """Normalized input for one canonical transaction write."""

    transaction_type: TransactionType
    occurred_at: datetime
    asset_id: UUID | None = None
    quantity: Decimal | None = None
    price: Decimal | None = None
    fees: Decimal = ZERO
    cash_amount: Decimal | None = None


@dataclass(frozen=True, slots=True)
class TransactionImportIssue:
    """One stable validation issue attached to a CSV row."""

    code: TransactionImportIssueCode
    field: str
    message: str


@dataclass(frozen=True, slots=True)
class TransactionImportRowPreview:
    """Normalized preview for one nonblank CSV row."""

    row_number: int
    valid: bool
    transaction_type: str | None
    occurred_at: str | None
    asset_id: str | None
    asset_symbol: str | None
    quantity: str | None
    price: str | None
    fees: str | None
    cash_amount: str | None
    issues: tuple[TransactionImportIssue, ...]


@dataclass(frozen=True, slots=True)
class TransactionImportPreview:
    """Atomic import preview; confirmation is allowed only when every row is valid."""

    row_count: int
    valid_count: int
    invalid_count: int
    can_import: bool
    atomic: bool
    rows: tuple[TransactionImportRowPreview, ...]


@dataclass(frozen=True, slots=True)
class TransactionImportResult:
    """Committed atomic CSV import result."""

    imported_count: int
    transactions: tuple[Transaction, ...]


@dataclass(frozen=True, slots=True)
class _ParsedCsvRow:
    row_number: int
    transaction_input: TransactionWriteInput | None
    normalized: dict[str, str | None]
    issues: tuple[TransactionImportIssue, ...]


def create_portfolio_transaction(
    portfolio: Portfolio,
    transaction_input: TransactionWriteInput,
) -> Transaction:
    """Validate, persist, and replay one transaction atomically."""
    if not isinstance(portfolio, Portfolio):
        raise TypeError("portfolio must be a Portfolio")

    with db_transaction.atomic():
        locked_portfolio = Portfolio.objects.select_for_update().get(id=portfolio.id)
        source_sequence = _next_source_sequence(
            locked_portfolio,
            transaction_input.occurred_at,
        )
        ledger_entry = _build_and_save_transaction(
            portfolio=locked_portfolio,
            transaction_input=transaction_input,
            source_sequence=source_sequence,
        )

        try:
            replay_portfolio_ledger(locked_portfolio)
        except NegativePositionError as exc:
            raise TransactionWriteError(
                TransactionWriteErrorCode.NEGATIVE_POSITION,
                {"quantity": (str(exc),)},
            ) from exc

        return ledger_entry


def preview_transaction_csv(
    portfolio: Portfolio,
    csv_text: str,
) -> TransactionImportPreview:
    """Parse and validate CSV without persisting any transaction rows."""
    parsed_rows = _parse_csv(csv_text)

    with db_transaction.atomic():
        locked_portfolio = Portfolio.objects.select_for_update().get(id=portfolio.id)
        preview, _transactions = _evaluate_parsed_rows(
            locked_portfolio,
            parsed_rows,
        )
        db_transaction.set_rollback(True)
        return preview


def import_transaction_csv(
    portfolio: Portfolio,
    csv_text: str,
) -> TransactionImportResult:
    """Revalidate and atomically commit a complete valid CSV import."""
    parsed_rows = _parse_csv(csv_text)

    with db_transaction.atomic():
        locked_portfolio = Portfolio.objects.select_for_update().get(id=portfolio.id)
        preview, transactions = _evaluate_parsed_rows(
            locked_portfolio,
            parsed_rows,
        )

        if not preview.can_import:
            raise TransactionImportValidationError(preview)

        return TransactionImportResult(
            imported_count=len(transactions),
            transactions=transactions,
        )


def _evaluate_parsed_rows(
    portfolio: Portfolio,
    parsed_rows: tuple[_ParsedCsvRow, ...],
) -> tuple[TransactionImportPreview, tuple[Transaction, ...]]:
    previews: dict[int, TransactionImportRowPreview] = {}
    transactions_by_row: dict[int, Transaction] = {}
    row_by_transaction_id: dict[UUID, int] = {}
    next_sequence_by_time: dict[datetime, int] = {}

    for parsed in parsed_rows:
        if parsed.issues or parsed.transaction_input is None:
            previews[parsed.row_number] = _preview_from_parsed(parsed)
            continue

        transaction_input = parsed.transaction_input
        source_sequence = next_sequence_by_time.get(transaction_input.occurred_at)

        if source_sequence is None:
            source_sequence = _next_source_sequence(
                portfolio,
                transaction_input.occurred_at,
            )

        next_sequence_by_time[transaction_input.occurred_at] = source_sequence + 1

        try:
            ledger_entry = _build_and_save_transaction(
                portfolio=portfolio,
                transaction_input=transaction_input,
                source_sequence=source_sequence,
            )
        except TransactionWriteError as exc:
            previews[parsed.row_number] = _preview_from_write_error(
                parsed,
                exc,
            )
            continue

        transactions_by_row[parsed.row_number] = ledger_entry
        row_by_transaction_id[ledger_entry.id] = parsed.row_number
        previews[parsed.row_number] = _preview_from_parsed(
            parsed,
            asset_symbol=ledger_entry.asset.symbol if ledger_entry.asset is not None else None,
        )

    while transactions_by_row:
        try:
            replay_portfolio_ledger(portfolio)
            break
        except NegativePositionError as exc:
            row_number = row_by_transaction_id.get(exc.transaction_id)

            if row_number is None:
                raise

            offending = transactions_by_row.pop(row_number)
            row_by_transaction_id.pop(offending.id, None)
            offending.delete()

            parsed = next(row for row in parsed_rows if row.row_number == row_number)
            previews[row_number] = _preview_from_issue(
                parsed,
                TransactionImportIssue(
                    code=TransactionImportIssueCode.NEGATIVE_POSITION,
                    field="quantity",
                    message=str(exc),
                ),
            )

    ordered_previews = tuple(previews[row.row_number] for row in parsed_rows)
    valid_transactions = tuple(
        transactions_by_row[row.row_number]
        for row in parsed_rows
        if row.row_number in transactions_by_row
    )
    valid_count = sum(1 for row in ordered_previews if row.valid)
    invalid_count = len(ordered_previews) - valid_count

    return (
        TransactionImportPreview(
            row_count=len(ordered_previews),
            valid_count=valid_count,
            invalid_count=invalid_count,
            can_import=bool(ordered_previews) and invalid_count == 0,
            atomic=True,
            rows=ordered_previews,
        ),
        valid_transactions,
    )


def _build_and_save_transaction(
    *,
    portfolio: Portfolio,
    transaction_input: TransactionWriteInput,
    source_sequence: int,
) -> Transaction:
    asset = _resolve_asset(transaction_input)
    ledger_entry = Transaction(
        portfolio=portfolio,
        transaction_type=transaction_input.transaction_type,
        asset=asset,
        occurred_at=transaction_input.occurred_at,
        source_sequence=source_sequence,
        quantity=transaction_input.quantity,
        price=transaction_input.price,
        fees=transaction_input.fees,
        cash_amount=transaction_input.cash_amount,
    )

    try:
        ledger_entry.full_clean()
    except ValidationError as exc:
        raise TransactionWriteError(
            TransactionWriteErrorCode.INVALID_TRANSACTION,
            _validation_error_messages(exc),
        ) from exc

    try:
        with db_transaction.atomic():
            ledger_entry.save()
    except IntegrityError as exc:
        raise TransactionWriteError(
            TransactionWriteErrorCode.ORDERING_CONFLICT,
            {
                "non_field_errors": (
                    "Transaction ordering conflicted with an existing ledger entry.",
                )
            },
        ) from exc

    return ledger_entry


def _resolve_asset(transaction_input: TransactionWriteInput) -> Asset | None:
    transaction_type = transaction_input.transaction_type
    asset_id = transaction_input.asset_id

    if transaction_type in (TransactionType.DEPOSIT, TransactionType.WITHDRAWAL):
        if asset_id is not None:
            raise TransactionWriteError(
                TransactionWriteErrorCode.INVALID_TRANSACTION,
                {"asset_id": ("asset_id must be absent for cash-flow transactions.",)},
            )
        return None

    if asset_id is None:
        raise TransactionWriteError(
            TransactionWriteErrorCode.INVALID_TRANSACTION,
            {"asset_id": ("asset_id is required for this transaction type.",)},
        )

    asset = Asset.objects.filter(
        id=asset_id,
        is_active=True,
        currency="USD",
    ).first()

    if asset is None:
        raise TransactionWriteError(
            TransactionWriteErrorCode.ASSET_NOT_FOUND,
            {"asset_id": ("Canonical asset was not found or is inactive.",)},
        )

    return asset


def _next_source_sequence(
    portfolio: Portfolio,
    occurred_at: datetime,
) -> int:
    maximum = (
        Transaction.objects.for_portfolio(portfolio)
        .filter(occurred_at=occurred_at)
        .aggregate(maximum=Max("source_sequence"))["maximum"]
    )
    return 0 if maximum is None else int(maximum) + 1


def _parse_csv(csv_text: str) -> tuple[_ParsedCsvRow, ...]:
    if not isinstance(csv_text, str):
        raise TypeError("csv_text must be a string")

    if not csv_text.strip():
        raise TransactionImportFileError(
            TransactionImportFileErrorCode.CSV_EMPTY,
            "CSV content must not be empty.",
        )

    byte_count = len(csv_text.encode("utf-8"))
    if byte_count > MAX_TRANSACTION_IMPORT_BYTES:
        raise TransactionImportFileError(
            TransactionImportFileErrorCode.CSV_TOO_LARGE,
            (f"CSV content exceeds the configured {MAX_TRANSACTION_IMPORT_BYTES}-byte limit."),
        )

    normalized_text = csv_text.lstrip("\ufeff")

    try:
        reader = csv.DictReader(io.StringIO(normalized_text, newline=""))
    except csv.Error as exc:
        raise TransactionImportFileError(
            TransactionImportFileErrorCode.CSV_PARSE_ERROR,
            "CSV content could not be parsed.",
        ) from exc

    fieldnames = tuple(reader.fieldnames or ())
    if fieldnames != TRANSACTION_IMPORT_COLUMNS:
        raise TransactionImportFileError(
            TransactionImportFileErrorCode.CSV_HEADER_INVALID,
            "CSV header must exactly match: " + ",".join(TRANSACTION_IMPORT_COLUMNS),
        )

    parsed_rows: list[_ParsedCsvRow] = []

    try:
        for row_number, raw_row in enumerate(reader, start=2):
            if (
                all(
                    value is None or not value.strip()
                    for key, value in raw_row.items()
                    if key is not None
                )
                and None not in raw_row
            ):
                continue

            parsed_rows.append(_parse_csv_row(row_number, raw_row))

            if len(parsed_rows) > MAX_TRANSACTION_IMPORT_ROWS:
                raise TransactionImportFileError(
                    TransactionImportFileErrorCode.CSV_TOO_MANY_ROWS,
                    (
                        "CSV content exceeds the configured "
                        f"{MAX_TRANSACTION_IMPORT_ROWS}-row limit."
                    ),
                )
    except csv.Error as exc:
        raise TransactionImportFileError(
            TransactionImportFileErrorCode.CSV_PARSE_ERROR,
            "CSV content could not be parsed.",
        ) from exc

    if not parsed_rows:
        raise TransactionImportFileError(
            TransactionImportFileErrorCode.CSV_EMPTY,
            "CSV must contain at least one nonblank transaction row.",
        )

    return tuple(parsed_rows)


def _parse_csv_row(
    row_number: int,
    raw_row: dict[str | None, str | None],
) -> _ParsedCsvRow:
    normalized = {column: _trimmed(raw_row.get(column)) for column in TRANSACTION_IMPORT_COLUMNS}
    issues: list[TransactionImportIssue] = []

    if None in raw_row:
        issues.append(
            TransactionImportIssue(
                code=TransactionImportIssueCode.EXTRA_COLUMNS,
                field="non_field_errors",
                message="CSV row contains more values than the documented header.",
            )
        )

    transaction_type: TransactionType | None = None
    raw_type = normalized["transaction_type"]
    if raw_type is None:
        issues.append(_required_issue("transaction_type"))
    else:
        canonical_type = raw_type.upper()
        normalized["transaction_type"] = canonical_type
        try:
            transaction_type = TransactionType(canonical_type)
        except ValueError:
            issues.append(
                TransactionImportIssue(
                    code=TransactionImportIssueCode.INVALID_TRANSACTION_TYPE,
                    field="transaction_type",
                    message="Unsupported transaction_type.",
                )
            )

    occurred_at: datetime | None = None
    raw_occurred_at = normalized["occurred_at"]
    if raw_occurred_at is None:
        issues.append(_required_issue("occurred_at"))
    else:
        try:
            occurred_at = datetime.fromisoformat(raw_occurred_at.replace("Z", "+00:00"))
        except ValueError:
            issues.append(
                TransactionImportIssue(
                    code=TransactionImportIssueCode.INVALID_DATETIME,
                    field="occurred_at",
                    message="occurred_at must be an ISO-8601 datetime.",
                )
            )
        else:
            if timezone.is_naive(occurred_at):
                issues.append(
                    TransactionImportIssue(
                        code=TransactionImportIssueCode.TIMEZONE_REQUIRED,
                        field="occurred_at",
                        message="occurred_at must include a timezone offset.",
                    )
                )
            else:
                normalized["occurred_at"] = occurred_at.isoformat()

    asset_id = _parse_uuid_field(
        normalized,
        field="asset_id",
        issues=issues,
    )
    quantity = _parse_decimal_field(
        normalized,
        field="quantity",
        issues=issues,
    )
    price = _parse_decimal_field(
        normalized,
        field="price",
        issues=issues,
    )
    fees = _parse_decimal_field(
        normalized,
        field="fees",
        issues=issues,
        blank_default=ZERO,
    )
    cash_amount = _parse_decimal_field(
        normalized,
        field="cash_amount",
        issues=issues,
    )

    transaction_input: TransactionWriteInput | None = None
    if transaction_type is not None and occurred_at is not None and not issues:
        transaction_input = TransactionWriteInput(
            transaction_type=transaction_type,
            occurred_at=occurred_at,
            asset_id=asset_id,
            quantity=quantity,
            price=price,
            fees=fees if fees is not None else ZERO,
            cash_amount=cash_amount,
        )

    return _ParsedCsvRow(
        row_number=row_number,
        transaction_input=transaction_input,
        normalized=normalized,
        issues=tuple(issues),
    )


def _parse_uuid_field(
    normalized: dict[str, str | None],
    *,
    field: str,
    issues: list[TransactionImportIssue],
) -> UUID | None:
    raw_value = normalized[field]
    if raw_value is None:
        return None

    try:
        parsed = UUID(raw_value)
    except ValueError:
        issues.append(
            TransactionImportIssue(
                code=TransactionImportIssueCode.INVALID_UUID,
                field=field,
                message=f"{field} must be a UUID when supplied.",
            )
        )
        return None

    normalized[field] = str(parsed)
    return parsed


def _parse_decimal_field(
    normalized: dict[str, str | None],
    *,
    field: str,
    issues: list[TransactionImportIssue],
    blank_default: Decimal | None = None,
) -> Decimal | None:
    raw_value = normalized[field]
    if raw_value is None:
        if blank_default is not None:
            normalized[field] = _decimal_text(blank_default)
        return blank_default

    try:
        parsed = Decimal(raw_value)
    except InvalidOperation:
        issues.append(
            TransactionImportIssue(
                code=TransactionImportIssueCode.INVALID_DECIMAL,
                field=field,
                message=f"{field} must be a decimal number when supplied.",
            )
        )
        return None

    if not parsed.is_finite():
        issues.append(
            TransactionImportIssue(
                code=TransactionImportIssueCode.NONFINITE_DECIMAL,
                field=field,
                message=f"{field} must be finite.",
            )
        )
        return None

    normalized[field] = _decimal_text(parsed)
    return parsed


def _preview_from_parsed(
    parsed: _ParsedCsvRow,
    *,
    asset_symbol: str | None = None,
) -> TransactionImportRowPreview:
    return TransactionImportRowPreview(
        row_number=parsed.row_number,
        valid=not parsed.issues,
        transaction_type=parsed.normalized["transaction_type"],
        occurred_at=parsed.normalized["occurred_at"],
        asset_id=parsed.normalized["asset_id"],
        asset_symbol=asset_symbol,
        quantity=parsed.normalized["quantity"],
        price=parsed.normalized["price"],
        fees=parsed.normalized["fees"],
        cash_amount=parsed.normalized["cash_amount"],
        issues=parsed.issues,
    )


def _preview_from_write_error(
    parsed: _ParsedCsvRow,
    error: TransactionWriteError,
) -> TransactionImportRowPreview:
    issue_code = {
        TransactionWriteErrorCode.ASSET_NOT_FOUND: TransactionImportIssueCode.ASSET_NOT_FOUND,
        TransactionWriteErrorCode.NEGATIVE_POSITION: TransactionImportIssueCode.NEGATIVE_POSITION,
        TransactionWriteErrorCode.ORDERING_CONFLICT: TransactionImportIssueCode.ORDERING_CONFLICT,
    }.get(error.code, TransactionImportIssueCode.INVALID_TRANSACTION)

    issues = tuple(
        TransactionImportIssue(
            code=issue_code,
            field=field,
            message=message,
        )
        for field, messages in error.errors.items()
        for message in messages
    )
    return _preview_with_issues(parsed, issues)


def _preview_from_issue(
    parsed: _ParsedCsvRow,
    issue: TransactionImportIssue,
) -> TransactionImportRowPreview:
    return _preview_with_issues(parsed, (issue,))


def _preview_with_issues(
    parsed: _ParsedCsvRow,
    issues: tuple[TransactionImportIssue, ...],
) -> TransactionImportRowPreview:
    return TransactionImportRowPreview(
        row_number=parsed.row_number,
        valid=False,
        transaction_type=parsed.normalized["transaction_type"],
        occurred_at=parsed.normalized["occurred_at"],
        asset_id=parsed.normalized["asset_id"],
        asset_symbol=None,
        quantity=parsed.normalized["quantity"],
        price=parsed.normalized["price"],
        fees=parsed.normalized["fees"],
        cash_amount=parsed.normalized["cash_amount"],
        issues=issues,
    )


def _required_issue(field: str) -> TransactionImportIssue:
    return TransactionImportIssue(
        code=TransactionImportIssueCode.REQUIRED,
        field=field,
        message=f"{field} is required.",
    )


def _trimmed(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _validation_error_messages(exc: ValidationError) -> dict[str, tuple[str, ...]]:
    if hasattr(exc, "message_dict"):
        return {
            field: tuple(str(message) for message in messages)
            for field, messages in exc.message_dict.items()
        }

    return {
        "non_field_errors": tuple(str(message) for message in exc.messages),
    }
