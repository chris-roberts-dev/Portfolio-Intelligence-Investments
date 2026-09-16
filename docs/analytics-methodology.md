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
