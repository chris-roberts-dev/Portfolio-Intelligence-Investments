"""Owner-scoped portfolio lifecycle mutations.

Development guide references: Sections 4.3, 7.5, 8.5, 8.6, and 21.1.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, cast
from uuid import UUID

from django.db import transaction

from apps.accounts.models import User
from apps.portfolios.models import Portfolio


class PortfolioDeletionErrorCode(StrEnum):
    """Stable application error codes for permanent portfolio deletion."""

    RETAINED_HISTORY = "PORTFOLIO_DELETE_BLOCKED"


class PortfolioDeletionError(RuntimeError):
    """Raised when a portfolio cannot be permanently deleted safely."""

    def __init__(
        self,
        code: PortfolioDeletionErrorCode,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


@transaction.atomic
def delete_empty_owned_portfolio(
    *,
    user: User,
    portfolio_id: UUID,
) -> None:
    """Delete one owned portfolio only when no persisted dependent rows exist.

    The owner-scoped portfolio row is locked before checking dependencies. Any
    transaction ledger entry, optimization run, target allocation, rebalance
    simulation, or future persisted reverse relation blocks deletion so the
    application does not silently define a cascading retention policy.
    """
    portfolio = Portfolio.objects.owned_by(user).select_for_update().filter(id=portfolio_id).first()

    if portfolio is None:
        raise Portfolio.DoesNotExist

    if _has_persisted_dependents(portfolio):
        raise PortfolioDeletionError(
            PortfolioDeletionErrorCode.RETAINED_HISTORY,
            (
                "This portfolio contains retained transaction or analytical history "
                "and cannot currently be permanently deleted."
            ),
        )

    portfolio.delete()


def _has_persisted_dependents(portfolio: Portfolio) -> bool:
    """Return whether any persisted row points back to the portfolio."""
    portfolio_meta = cast(Any, portfolio)._meta

    for relation in portfolio_meta.related_objects:
        if not (relation.one_to_many or relation.one_to_one):
            continue

        related_model = cast(Any, relation.related_model)
        relation_field_name = cast(str, relation.field.name)
        if related_model._base_manager.filter(**{relation_field_name: portfolio}).exists():
            return True

    return False
