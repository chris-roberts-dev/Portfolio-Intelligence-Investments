"""Typed reusable query scoping for portfolio persistence models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.portfolios.models import Portfolio, Transaction
else:
    User = models.Model
    Portfolio = models.Model
    Transaction = models.Model


class PortfolioQuerySet(models.QuerySet[Portfolio]):
    """Reusable ownership scoping for portfolios."""

    def owned_by(self, user: User) -> PortfolioQuerySet:
        return self.filter(user=user)


class PortfolioManager(models.Manager[Portfolio]):
    """Manager exposing typed portfolio ownership scoping."""

    def get_queryset(self) -> PortfolioQuerySet:
        return PortfolioQuerySet(
            self.model,
            using=self._db,
        )

    def owned_by(self, user: User) -> PortfolioQuerySet:
        return self.get_queryset().owned_by(user)


class TransactionQuerySet(models.QuerySet[Transaction]):
    """Reusable ownership, portfolio, and replay scoping for transactions."""

    def owned_by(self, user: User) -> TransactionQuerySet:
        return self.filter(portfolio__user=user)

    def for_portfolio(
        self,
        portfolio: Portfolio,
    ) -> TransactionQuerySet:
        return self.filter(portfolio=portfolio)

    def through(
        self,
        as_of: datetime | None,
    ) -> TransactionQuerySet:
        if as_of is None:
            return self

        if timezone.is_naive(as_of):
            raise ValueError("as_of must be timezone-aware")

        return self.filter(occurred_at__lte=as_of)

    def ordered_for_replay(self) -> TransactionQuerySet:
        return self.order_by(
            "occurred_at",
            "source_sequence",
            "id",
        )


class TransactionManager(models.Manager[Transaction]):
    """Manager exposing typed transaction-ledger scoping."""

    def get_queryset(self) -> TransactionQuerySet:
        return TransactionQuerySet(
            self.model,
            using=self._db,
        )

    def owned_by(self, user: User) -> TransactionQuerySet:
        return self.get_queryset().owned_by(user)

    def for_portfolio(
        self,
        portfolio: Portfolio,
    ) -> TransactionQuerySet:
        return self.get_queryset().for_portfolio(portfolio)

    def through(
        self,
        as_of: datetime | None,
    ) -> TransactionQuerySet:
        return self.get_queryset().through(as_of)

    def ordered_for_replay(self) -> TransactionQuerySet:
        return self.get_queryset().ordered_for_replay()
