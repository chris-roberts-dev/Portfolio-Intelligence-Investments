# Data Model Reference

`docs/dev-guide.md` Sections 8 and 10 are normative. This document summarizes the Phase 4 persisted model boundary; it does not replace the model definitions or accounting rules.

## User

The custom Django user model is the authentication principal. Portfolio ownership is always derived from authenticated server context.

## Asset

`Asset` is the canonical internal instrument identity for the USD MVP. Supported public-MVP asset types are U.S.-listed common stocks and ETFs; cash is represented through portfolio ledger cash rather than as an arbitrary ticker.

## AssetProviderSymbol

Maps one canonical `Asset` to a provider-specific symbol. Market-data requests resolve user symbols through this mapping before invoking a configured provider adapter.

## Portfolio

An owned USD portfolio containing metadata and an optional canonical benchmark asset reference. Holdings are not stored as authoritative portfolio state.

## Transaction

The append/replay ledger supports the canonical Phase 4 transaction types:

- `DEPOSIT`
- `WITHDRAWAL`
- `BUY`
- `SELL`
- optional `DIVIDEND`

Ledger ordering is deterministic using occurrence time, source sequence, and stable identifier. BUY/SELL cash effects are derived according to the canonical accounting rules. Long-only replay validation rejects a transaction batch that would create an invalid negative position.

## Derived state

Positions, cash, book accounting, valuation, returns, allocation, movers, review items, and analytics are derived by application services and the deterministic quantitative engine. React never persists or independently calculates these states.

See model definitions under `backend/apps/assets/models.py` and `backend/apps/portfolios/models.py`, and Sections 8/10 of `docs/dev-guide.md` for the authoritative contract.
