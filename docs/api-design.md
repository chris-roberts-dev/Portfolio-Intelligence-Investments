# API Design Reference

`docs/dev-guide.md` is the normative API/architecture authority. The generated `backend/openapi.yaml` is the machine-readable transport contract and must be regenerated with `make openapi` after API changes.

## API principles

- All application routes are under `/api/v1/`.
- Portfolio resources are authenticated and owner-scoped on the server.
- Client-supplied UUIDs are locators, never proof of authorization.
- DRF views remain thin: validate/authorize, call application service, serialize result.
- Financial calculations are not implemented in views or serializers.
- Analytical responses preserve nulls, warnings, provenance, and deterministic assumptions.
- Market-data queries preserve per-symbol status so one failed symbol does not erase successful symbols.
- Provider selection remains server-side through an allowlist/registry boundary.

## Phase 4 route families

- Authentication/session routes: `/api/v1/auth/...`
- Market bars: `POST /api/v1/market-data/bars/query/`
- Portfolios: `/api/v1/portfolios/`
- Portfolio detail/rename: `/api/v1/portfolios/{portfolio_id}/`
- Benchmark selection: `/api/v1/portfolios/{portfolio_id}/benchmark/`
- Dashboard modules/snapshot: `/api/v1/portfolios/{portfolio_id}/...`
- Transaction entry/import: `/api/v1/portfolios/{portfolio_id}/transactions/...`
- Portfolio analytics: `/api/v1/analytics/portfolios/{portfolio_id}/`
- OpenAPI schema/docs: `/api/v1/schema/`, `/api/v1/docs/`

See `backend/openapi.yaml` for exact request/response schemas and operation IDs.

## Phase 5 rebalancing route families

- Target allocations: `/api/v1/target-allocations/`
- Current point-in-time rebalance simulations: `/api/v1/rebalance-simulations/`
- Persisted historical schedule/threshold comparisons:
  `/api/v1/historical-rebalance-comparisons/`

Historical comparison creation requires an owned portfolio and target allocation,
an explicit analysis period, and an absolute drift threshold. Annual, quarterly,
and threshold policies are always included; monthly is optional. Commission and
slippage inputs default to the centralized normative zero rates and are persisted
with the result. The response/persisted result discloses adjusted-close usage,
provider retrieval provenance, engine version, decision/execution timing,
complete-case date alignment, value/return and allocation/drift series, simulated
fills, turnover, costs, and warnings.
