# Phase 6 Batch 2 — Buy-and-Hold Backend Workflow

**Status:** Implemented in Milestone 3 / Phase 6 Batch 2  
**Canonical authority:** `docs/dev-guide.md`  
**Guide sections:** 9.6–9.7, 14, 15.2–15.3, 17.1–17.2, 19.6, 20.2, 23.7, 24 Phase 6

## Scope

This batch adds exactly one canonical strategy—buy-and-hold—and the first persisted owner-scoped backtest backend workflow. It deliberately does not add moving-average, momentum, benchmark comparison, Strategy Lab, parameter search, or later-phase analytical models.

## Canonical buy-and-hold semantics

A buy-and-hold run starts from positive USD cash and explicit long-only risky-asset target weights that sum to one.

1. The engine observes the first complete-case aligned adjusted-close observation in the requested evaluation period.
2. The strategy creates initial buy intents from that decision-date portfolio value and the configured target weights.
3. Those intents do **not** fill at the same close. They become eligible at the next complete-case aligned observation.
4. The execution layer uses that later date's `adjusted_close`, applies configured slippage and commission, and proportionally scales buys when required to preserve non-negative cash.
5. After the initial security position is established, buy-and-hold emits no further orders.
6. Fractional shares are permitted. Short positions, margin, leverage, silent forward filling, and zero substitution are prohibited.

For a target weight `w_i`, decision-date total portfolio value `V_t`, and decision-date adjusted close `P_i,t`, the initial order intent quantity is:

```text
quantity_i = V_t * w_i / P_i,t
```

This quantity is an **intent**, not a fill. Actual fill quantity may be proportionally scaled by the existing execution layer when next-observation prices and explicit costs would otherwise exceed cash.

## Persistence and reproducibility

`BacktestRun` persists:

- owner;
- run status;
- strategy identity and version;
- backtest-method and engine versions;
- requested inclusive-start/exclusive-end period;
- included canonical asset IDs;
- normalized strategy parameters and target weights;
- initial cash;
- commission and slippage assumptions;
- provider and adjusted-close convention;
- retrieval timestamp and deterministic data fingerprint;
- structured warnings;
- structured result JSON;
- start/completion timestamps;
- stable failure code/message for failed runs.

Expected analytical failures after persistence begins remain auditable as `FAILED` resources rather than disappearing as transport-only errors.

## API

The authenticated owner-scoped endpoints are:

```text
GET  /api/v1/backtest-runs/
POST /api/v1/backtest-runs/
GET  /api/v1/backtest-runs/{run_id}/
```

Example request:

```json
{
  "strategy": "BUY_AND_HOLD",
  "start": "2026-01-02",
  "end": "2026-09-16",
  "initial_cash": "100000.00000000",
  "target_weights": [
    {"asset_id": "<uuid-a>", "weight": 0.6},
    {"asset_id": "<uuid-b>", "weight": 0.4}
  ],
  "commission_rate": 0.0,
  "slippage_rate": 0.0
}
```

The end date is exclusive, matching the canonical market-bar contract.

## Result scope in this batch

The persisted result exposes the foundation outputs already produced by `portfolio_engine.backtesting`:

- aligned dates;
- valued portfolio-state snapshots and weights;
- equity/value series;
- simple-return series;
- decisions;
- later execution events;
- simulated fills;
- commission/slippage cost history and totals;
- trade count and turnover;
- assumptions;
- warnings;
- requested/aligned period provenance;
- provider/data fingerprint;
- engine, backtest-method, and strategy versions.

This batch does not yet add drawdown series, CAGR, volatility, Sharpe, Sortino, maximum-drawdown summary, or benchmark comparison. Those remain Section 23.7 work.

## Validation focus

The batch adds fixtures proving:

- the first decision uses only the first eligible observation;
- the initial allocation executes only on the next aligned observation;
- modifying post-decision prices cannot change the decision;
- commission-driven buy scaling preserves non-negative cash;
- exact quantities, cash, turnover, costs, equity values, and returns in a manually calculable example;
- complete-case missing-data behavior without forward fill;
- deterministic equivalent outputs for identical persisted inputs;
- owner-scoped list/detail API behavior;
- stable failed-run persistence for insufficient history;
- framework/provider independence of the strategy layer.
