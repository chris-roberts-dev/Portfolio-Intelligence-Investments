# Portfolio Analytics Methodology Reference

`docs/dev-guide.md`, especially Section 11, is the normative authority for every financial definition. This file maps the current v0.1 analytical surface to its implementation and test boundaries without duplicating formulas.

| Analytical output | Authoritative implementation area | Independent test areas |
| --- | --- | --- |
| Simple/cumulative/rolling returns | `portfolio_engine/performance/returns.py` | unit/property/validation return tests |
| Time-weighted return | `portfolio_engine/performance/time_weighted.py` | unit/property/validation TWR tests |
| CAGR / annualized geometric return | `portfolio_engine/performance/returns.py` | annualized/rolling return tests |
| Annualized volatility / Sharpe | `portfolio_engine/performance/statistics.py` | performance-statistics tests |
| Sortino / downside deviation | `portfolio_engine/performance/downside.py` | Sortino tests |
| Maximum drawdown | `portfolio_engine/performance/drawdown.py` | drawdown tests |
| Beta / Pearson correlation | `portfolio_engine/risk/relationships.py` | risk-relationship tests |
| Current allocation | `portfolio_engine/portfolio/allocation.py` | allocation tests |
| Concentration | `portfolio_engine/risk/concentration.py` | concentration tests |
| Current valuation | `portfolio_engine/portfolio/valuation.py` plus application valuation service | valuation/integration tests |
| TWR attribution/movers | portfolio attribution/weighted-return kernels plus dashboard service | attribution/movers tests |

## Presentation boundary

React formats server-provided results but does not recompute canonical metrics. Nullable/undefined analytical results remain explicit and carry server diagnostics where available.

## Price conventions and provenance

Historical performance/risk calculations use the documented adjusted-price convention. Current valuation uses the documented raw-close convention. Analytical API responses expose period, as-of date, provider/source, price field, annualization factor, benchmark where applicable, engine version, assumptions, and warnings.

For exact formulas, minimum-observation rules, annualization rules, and exceptional conditions, use Section 11 and the normative constants in Section 27 of `docs/dev-guide.md`.
## Phase 5 historical rebalancing comparison

Historical schedule/threshold comparisons are implemented in
`portfolio_engine/rebalancing/historical.py` and remain narrower than the future
Phase 6 backtesting engine. The authoritative rules remain Sections 9.6-9.7,
13, 14.3, 14.5-14.6, 17.1, 19.6, 23.6, and 27 of `docs/dev-guide.md`.

Current implemented assumptions and boundaries are explicit:

- historical valuation and simulated execution use normalized `adjusted_close`;
- all required securities use the complete-case intersection of available dates;
  missing observations are never forward-filled or converted to zero;
- a rebalance decision observed on date `t` can execute only on the next aligned
  market observation;
- the application seeds the hypothetical state from the owned portfolio ledger
  observable at `00:00 UTC` on the requested `period_start`;
- later real ledger transactions are not injected into the hypothetical path;
  their presence produces `ACTUAL_LEDGER_ACTIVITY_IGNORED`;
- long-only quantities and non-negative cash are enforced, and fractional shares
  are permitted;
- commission and slippage rates are explicit assumptions using the centralized
  Section 27 defaults (currently zero) unless supplied by the request;
- buy fills use `reference_price * (1 + slippage_rate)` and sell fills use
  `reference_price * (1 - slippage_rate)`; commissions are proportional to fill
  notional; buys are scaled deterministically when needed to avoid negative cash;
- reported turnover uses the explicit convention
  `gross executed fill notional / pre-trade portfolio value` for each rebalance,
  summed across the comparison period;
- annual, quarterly, and absolute drift-threshold policies are compared by the
  application service; monthly scheduling uses the same engine abstraction and
  may be included explicitly.

Persisted comparison results retain provider/retrieval provenance, engine
version, requested and aligned periods, assumptions, value/return history,
allocation/drift history, rebalance decisions/fills, trade count, turnover,
costs, and warnings. This implementation does not introduce a generic strategy
protocol, buy-and-hold strategy, moving-average strategy, momentum strategy, or
Strategy Lab behavior.
