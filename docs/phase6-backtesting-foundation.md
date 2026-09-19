# Phase 6 deterministic backtesting foundation

**Status:** Implemented foundation batch  
**Guide authority:** `docs/dev-guide.md` Sections 9.6-9.7, 14, 17.1-17.2, 19.4, 19.6, 20.2-20.3, 23.7, and 27

## Scope implemented

This batch adds only the framework-independent deterministic backtesting kernel. It does not add a strategy catalog, Django persistence/API endpoints, background jobs, benchmark comparison, or Strategy/Portfolio Lab UI.

The kernel provides:

- an immutable `StrategyContext` whose visible price history is capped at the decision date;
- a minimal internal `BacktestStrategy` protocol with explicit name, version, and warm-up count;
- immutable long-only position/cash state and valued portfolio snapshots;
- normalized buy/sell order intents and simulated fills;
- decision-at-`t`, execution-at-next-aligned-observation semantics;
- adjusted-close observation and execution-price basis;
- explicit commission and slippage assumptions using the normative defaults;
- deterministic proportional scaling of buys that would otherwise overdraw cash;
- explicit rejection of sell orders that would create short positions;
- complete-case execution/valuation dates with no forward fill or zero substitution;
- portfolio-value/equity series, simple return series, position/weight history, decisions, fills, costs, turnover, and warnings;
- requested/aligned period provenance, provider/retrieval/data-fingerprint inputs, engine version, backtest method version, and strategy version.

`BACKTEST_METHOD_VERSION` begins at `1.0`. `PORTFOLIO_ENGINE_VERSION` remains `0.2.0` in this foundation batch so released Phase 5 optimization/rebalancing provenance and regression fixtures are not changed mid-phase. The engine version can be deliberately advanced at the v0.3 release boundary after the full Phase 6 release gate is satisfied.

## Execution semantics

For each aligned daily adjusted-close observation:

1. orders decided on the prior aligned date execute at the current adjusted close;
2. sells execute before buys so available proceeds are deterministic;
3. commission and slippage are applied to fills;
4. buys are proportionally scaled when the requested cash cost exceeds available cash;
5. the resulting portfolio is valued at the current adjusted-close reference prices;
6. the strategy receives only history with `trade_date <= as_of` and the immutable post-execution portfolio state;
7. any generated orders become eligible only on the next aligned observation.

An order generated on the final aligned date is retained as a decision and accompanied by an `UNEXECUTED_FINAL_ORDERS` warning. It is never filled at that same close.

## Deliberate Phase 5 reuse boundary

This batch reuses the existing canonical `PriceBar`/`PriceFrame` contract, normative cost defaults, weight tolerance, and engine-version provenance. It does **not** import or wrap the Phase 5 historical-rebalancing engine.

No Phase 5 state/execution primitive was extracted because the released historical-rebalancing execution path is target-allocation specific and changing it is not strictly required to establish the generic Phase 6 strategy boundary. The new backtesting execution layer follows the same normative Section 14.5-14.6 fill/cost formulas while keeping the v0.2 path unchanged. Architecture tests explicitly preserve the one-way boundary: Phase 5 rebalancing must not depend on Phase 6 backtesting.

## Batch 2 extension

The next bounded Phase 6 batch now adds the first concrete strategy and persistence boundary without changing the generic engine semantics above:

- canonical `BUY_AND_HOLD` strategy in `portfolio_engine/strategies/buy_and_hold.py`;
- explicit initial target weights that sum to one;
- first-decision allocation using information available through the first eligible aligned close;
- next-aligned-adjusted-close execution through the existing generic execution layer;
- persisted owner-scoped `BacktestRun` records with normalized inputs, versions, costs, warnings, result JSON, provider identity, retrieval timestamp, and deterministic data fingerprint;
- authenticated `GET/POST /api/v1/backtest-runs/` and `GET /api/v1/backtest-runs/{run_id}/`;
- failed expected analytical runs retained as auditable `FAILED` resources.

The buy-and-hold strategy is intentionally separate from the generic backtesting package. The engine remains strategy-agnostic and the Django service remains orchestration-only.

## Explicitly incomplete after Batch 2

The following Section 23.7/public-MVP items remain for later Phase 6 batches:

- moving-average strategy;
- momentum strategy;
- benchmark comparison;
- drawdown curve;
- CAGR/annualized return;
- volatility;
- Sharpe ratio;
- Sortino ratio;
- maximum drawdown summary;
- Strategy/Portfolio Lab UI;
- Playwright backtest workflow.

No risk parity, Black-Litterman, HRP, VaR/CVaR, factor model, AI, brokerage, parameter-search, or free-form user strategy feature is introduced here.
