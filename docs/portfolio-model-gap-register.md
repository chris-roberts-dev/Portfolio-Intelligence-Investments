# Portfolio Intelligence Model Gap Register

**Status:** Active implementation tracker  
**Created:** September 15, 2026  
**Comparison sources:** `project-consolidated.md` and `code(1).r`  
**Project engine version reviewed:** `0.1.0.dev0`  

## 1. Purpose

This document tracks portfolio models, strategy capabilities, and supporting infrastructure found in the Systematic Investor Toolbox R code but not yet implemented in Portfolio Intelligence. It separates completed analytical primitives from outstanding portfolio-construction, optimization, rebalancing, and backtesting work.

The R file contains reusable models, research examples, test strategies, plotting functions, data acquisition helpers, and general utilities. This register treats a **model** as a reusable allocation method, optimizer, risk estimator, trading rule, or backtest strategy. Plotting, scraping, formatting, and generic utility functions are excluded unless they are required to operate or validate a model.

## 2. Status and Priority Legend

### Status

- `[x]` Implemented and covered by project tests.
- `[~]` Partially implemented or only an analytical primitive exists.
- `[ ]` Not implemented.
- `[D]` Deliberately deferred by the current development guide.
- `[C]` Requirements conflict must be resolved before implementation.

### Priority

| Priority | Meaning |
| --- | --- |
| P0 | Required foundation or release-blocking capability. |
| P1 | Required Portfolio Lab capability after the foundation is stable. |
| P2 | Valuable advanced portfolio research capability. |
| P3 | Specialized, experimental, or later-phase capability. |

## 3. Executive Finding

The current Python project now extends its analytical foundation through the canonical Phase 5 optimization and rebalancing layers. Target-allocation validation, current drift/notional simulation, schedule and threshold rules, and deterministic historical annual/quarterly/threshold rebalancing comparisons are implemented with explicit costs, turnover, event history, provenance, and anti-look-ahead timing.

The generic historical strategy backtester is still absent: `apps/backtesting` remains scaffolding, and buy-and-hold, moving-average, momentum, benchmark-comparison, and broader SIT strategy infrastructure remain outstanding. Advanced SIT allocation/risk models also remain outside this Phase 5 batch unless already covered elsewhere in the current project.

## 4. Existing Coverage

These items are present and should be reused rather than reimplemented inside future optimization or backtesting modules.

| Status | Existing capability | Current project location | R analogue |
| --- | --- | --- | --- |
| [x] | Simple and logarithmic returns | `portfolio_engine/performance/returns.py` | Return helpers throughout the R toolbox |
| [x] | Cumulative return | `portfolio_engine/performance/returns.py` | Backtest equity calculations |
| [x] | Annualized geometric return and CAGR | `portfolio_engine/performance/returns.py` | `compute.cagr` |
| [x] | Rolling cumulative returns | `portfolio_engine/performance/returns.py` | Rolling reporting helpers |
| [x] | Sample standard deviation and annualized volatility | `portfolio_engine/performance/statistics.py` | `compute.risk` |
| [x] | Sharpe ratio | `portfolio_engine/performance/statistics.py` | `compute.sharpe` |
| [x] | Sortino ratio and downside deviation | `portfolio_engine/performance/downside.py` | Downside-risk functions |
| [x] | Wealth, peak, and drawdown series | `portfolio_engine/performance/drawdown.py` | `compute.drawdown`, `compute.drawdowns` |
| [x] | Maximum drawdown | `portfolio_engine/performance/drawdown.py` | `compute.max.drawdown` |
| [x] | Time-weighted return | `portfolio_engine/performance/time_weighted.py` | Backtest return calculations |
| [x] | Beta | `portfolio_engine/risk/relationships.py` | Regression and beta calculations |
| [x] | Pairwise correlation | `portfolio_engine/risk/relationships.py` | Correlation calculations |
| [x] | Pairwise sample covariance | `portfolio_engine/risk/relationships.py` | Covariance calculations |
| [x] | Security-only HHI concentration | `portfolio_engine/risk/concentration.py` | `portfolio.concentration.herfindahl.index` |
| [x] | Position and total portfolio valuation | `portfolio_engine/portfolio/valuation.py` | Share-level valuation logic |
| [x] | Current allocation derived from position values | `portfolio_engine/portfolio/allocation.py` | Weight-reporting helpers |
| [~] | Hypothetical weighted portfolio return | `portfolio_engine/portfolio/weighted_returns.py` | Weight-based backtest calculations |

The hypothetical weighted return is partial because it validates and calculates one explicit period using prior-period weights. It does not create target weights, evolve holdings through time, execute simulated trades, or perform rebalancing.

## 5. Immediate MVP Model Gaps

These capabilities are already required by the current development guide and should be implemented before advanced R-model parity work.

| ID | Status | Priority | Missing capability | R reference | Recommended Python destination |
| --- | --- | --- | --- | --- | --- |
| OPT-001 | [ ] | P0 | Full aligned covariance matrix | `create.ia`, `create.cov.matrix` | `portfolio_engine/optimization/estimators.py` |
| OPT-002 | [ ] | P0 | Long-only weight constraint contract | `new.constraints`, `add.constraints` | `portfolio_engine/optimization/constraints.py` |
| OPT-003 | [ ] | P0 | Solver-result validation | R optimization wrappers | `portfolio_engine/optimization/validation.py` |
| OPT-004 | [ ] | P0 | Equal-weight allocation | `equal.weight.portfolio` | `portfolio_engine/optimization/equal_weight.py` |
| OPT-005 | [ ] | P0 | Static/custom target allocation | `static.weight.portfolio`, `custom.weight.portfolio` | `portfolio_engine/optimization/custom_weight.py` |
| OPT-006 | [ ] | P0 | Minimum-variance optimization | `min.var.portfolio` | `portfolio_engine/optimization/minimum_variance.py` |
| OPT-007 | [ ] | P0 | Maximum-Sharpe optimization | `max.sharpe.portfolio` | `portfolio_engine/optimization/maximum_sharpe.py` |
| OPT-008 | [ ] | P0 | Efficient frontier | `ef.portfolio` | `portfolio_engine/optimization/efficient_frontier.py` |
| OPT-009 | [ ] | P1 | Target-return optimization | `target.return.portfolio` | `portfolio_engine/optimization/target_return.py` |
| OPT-010 | [ ] | P1 | Target-risk optimization | `target.risk.portfolio` | `portfolio_engine/optimization/target_risk.py` |
| REB-001 | [x] | P0 | Target-allocation validation | R constraint and allocation helpers | `portfolio_engine/rebalancing/core.py` |
| REB-002 | [x] | P0 | Absolute and relative drift calculation | `compute.max.deviation` | `portfolio_engine/rebalancing/core.py` |
| REB-003 | [x] | P0 | Simulated rebalance notionals | Share allocation helpers | `portfolio_engine/rebalancing/core.py` |
| REB-004 | [x] | P0 | Monthly, quarterly, and annual schedules | `bt.rebalancing.test` | `portfolio_engine/rebalancing/rules.py`, `historical.py` |
| REB-005 | [x] | P0 | Drift-threshold rebalancing | `bt.max.deviation.rebalancing` | `portfolio_engine/rebalancing/rules.py`, `historical.py` |
| BT-001 | [ ] | P0 | Deterministic backtest state machine | `bt.run`, `bt.run.share` | `portfolio_engine/backtesting/engine.py` |
| BT-002 | [ ] | P0 | Time-bounded strategy context | R rolling-window conventions | `portfolio_engine/backtesting/context.py` |
| BT-003 | [ ] | P0 | Observe-at-`t`, execute-at-`t+1` enforcement | Execution-lag examples | `portfolio_engine/backtesting/execution.py` |
| BT-004 | [ ] | P0 | Cash and position state | `compute.cash`, share engine | `portfolio_engine/backtesting/state.py` |
| BT-005 | [ ] | P0 | Orders and simulated fills | Extended share engine | `portfolio_engine/backtesting/orders.py` |
| BT-006 | [ ] | P0 | Commission and slippage assumptions | `compute.commission` | `portfolio_engine/backtesting/costs.py` |
| BT-007 | [ ] | P0 | Buy-and-hold strategy | R baseline models | `portfolio_engine/backtesting/strategies/buy_and_hold.py` |
| BT-008 | [ ] | P0 | Moving-average strategy | `timing.strategy`, MA examples | `portfolio_engine/backtesting/strategies/moving_average.py` |
| BT-009 | [ ] | P0 | Momentum strategy | `momentum.averaged` and examples | `portfolio_engine/backtesting/strategies/momentum.py` |
| BT-010 | [ ] | P0 | Benchmark-aligned result comparison | R comparison reports | `portfolio_engine/backtesting/comparison.py` |
| BT-011 | [ ] | P0 | Equity, drawdown, trade, weight, and cost outputs | `bt.summary`, `bt.trade.summary` | `portfolio_engine/backtesting/results.py` |
| BT-012 | [ ] | P0 | Immutable and reproducible run record | R has partial configuration behavior; project guide is stricter | `apps/backtesting/models.py` and service layer |

## 6. Advanced Allocation and Optimization Gaps

| ID | Status | Priority | Missing model | R implementation | Dependency |
| --- | --- | --- | --- | --- | --- |
| ADV-001 | [C] | P1 | Inverse-volatility allocation | `risk.parity.portfolio.basic` | Covariance/risk estimator foundation |
| ADV-002 | [C] | P1 | Inverse-variance allocation | `inverse.variance.portfolio` | Covariance matrix |
| ADV-003 | [C] | P1 | Generalized risk-parity allocation | `risk.parity.portfolio` | Stable risk estimators |
| ADV-004 | [C] | P1 | Equal risk contribution | `equal.risk.contribution.portfolio` | Risk-contribution calculations and nonlinear solver |
| ADV-005 | [C] | P1 | Portfolio risk contribution | `portfolio.risk.contribution` | Covariance matrix |
| ADV-006 | [C] | P2 | Hierarchical risk parity | `hierarchical.risk.parity` | Clustering and covariance layers |
| ADV-007 | [C] | P2 | Cluster risk parity | `bt.cluster.risk.parity.*` | Historical clustering and HRP support |
| ADV-008 | [ ] | P2 | Maximum diversification | `max.div.portfolio`, `max.div.portfolio2` | Covariance matrix and optimizer |
| ADV-009 | [ ] | P2 | Minimum-correlation portfolio | `min.corr.portfolio`, `min.corr2.portfolio` | Correlation matrix and constraints |
| ADV-010 | [ ] | P2 | Minimum-average-correlation portfolio | `min.avgcor.portfolio` | Correlation matrix |
| ADV-011 | [ ] | P2 | Correlation-as-covariance optimization | `min.cor.insteadof.cov.portfolio` | Generalized quadratic optimizer |
| ADV-012 | [ ] | P2 | Minimum tracking error | `min.te.portfolio` | Benchmark weights and covariance matrix |
| ADV-013 | [ ] | P2 | Robust portfolio optimization | `rso.portfolio` | Base optimizers and resampling |
| ADV-014 | [C] | P2 | Black–Litterman posterior and allocation | `bl.compute.eqret`, `bl.compute.posterior`, `bl.compute.optimal` | Expected-return and covariance framework |
| ADV-015 | [ ] | P2 | Maximum expected-return portfolio | `max.return.portfolio` | Expected-return estimator |
| ADV-016 | [ ] | P2 | Maximum geometric-return portfolio | `max.geometric.return.portfolio` | Historical-return scenario matrix |

## 7. Alternative-Risk Optimization Gaps

| ID | Status | Priority | Missing model | R implementation | Notes |
| --- | --- | --- | --- | --- | --- |
| RISK-001 | [ ] | P2 | Maximum Omega-ratio portfolio | `max.omega.portfolio` | Requires threshold/MAR definition. |
| RISK-002 | [ ] | P2 | Minimum maximum-loss portfolio | `min.maxloss.portfolio` | Scenario-based minimax optimization. |
| RISK-003 | [ ] | P2 | Minimum mean absolute deviation | `min.mad.portfolio` | Linear-programming risk objective. |
| RISK-004 | [ ] | P2 | Minimum downside MAD | `min.mad.downside.portfolio` | Requires minimum acceptable return. |
| RISK-005 | [ ] | P2 | Minimum downside-risk portfolio | `min.risk.downside.portfolio` | Descriptive downside deviation already exists; optimization does not. |
| RISK-006 | [C] | P2 | Value at Risk | `portfolio.var` and VaR constraints | Deferred by current development guide. |
| RISK-007 | [C] | P2 | Conditional Value at Risk | `min.cvar.portfolio` | Deferred by current development guide. |
| RISK-008 | [ ] | P2 | Conditional Drawdown at Risk | `min.cdar.portfolio` | Requires drawdown scenario construction. |
| RISK-009 | [ ] | P3 | Minimum Gini-risk portfolio | `min.gini.portfolio` | Specialized alternative risk objective. |
| RISK-010 | [ ] | P3 | Gini portfolio concentration | `portfolio.concentration.gini.coefficient` | HHI is implemented; Gini is not. |

## 8. Covariance and Risk-Estimator Gaps

| ID | Status | Priority | Missing estimator/model | R implementation |
| --- | --- | --- | --- | --- |
| EST-001 | [ ] | P0 | Complete-case aligned sample covariance matrix | `create.ia`, `cov.sample` |
| EST-002 | [ ] | P1 | Positive-definite covariance repair policy | Used by R optimization functions |
| EST-003 | [ ] | P2 | Diagonal shrinkage | `diagonal.shrinkage`, `shrink.diag` |
| EST-004 | [ ] | P2 | Constant-correlation shrinkage | `cov.const.cor`, `shrink.const.cor` |
| EST-005 | [ ] | P2 | Single-index shrinkage | `cov.market`, `shrink.single.index` |
| EST-006 | [ ] | P2 | Two-parameter shrinkage | `cov.2param`, `shrink.two.parameter` |
| EST-007 | [ ] | P2 | Ledoit–Wolf shrinkage | `ledoit.wolf.shrinkage` |
| EST-008 | [ ] | P2 | Exponentially weighted covariance | `exp.sample.shrinkage` |
| EST-009 | [ ] | P3 | Anchored and mixed shrinkage | `sample.anchored.shrinkage`, `sample.mix.shrinkage` |
| EST-010 | [ ] | P3 | Average/minimum/maximum correlation shrinkage | `average.shrinkage`, `min.shrinkage`, related helpers |
| EST-011 | [D] | P2 | Factor-model covariance and specific risk | `fm.risk.model`, `factor.model.shrinkage` |
| EST-012 | [D] | P2 | Rolling factor regression | `factor.rolling.regression` |
| EST-013 | [D] | P2 | Three-factor regression | `three.factor.rolling.regression` |
| EST-014 | [ ] | P2 | GARCH volatility forecast | `bt.forecast.garch.volatility` |
| EST-015 | [ ] | P3 | PCA risk decomposition | `bt.pca.test` |
| EST-016 | [ ] | P3 | Correlation clustering | `bt.clustering.test` |
| EST-017 | [ ] | P3 | Financial turbulence/regime measure | `bt.financial.turbulence.test` |

## 9. Additional Backtest Strategy Gaps

These are useful Portfolio Lab candidates after the MVP backtest engine and initial three strategies are stable.

| ID | Status | Priority | Missing strategy family | R implementation/examples |
| --- | --- | --- | --- | --- |
| STR-001 | [ ] | P1 | Fixed 60/40 portfolio | `bt.new.60.40.test` |
| STR-002 | [ ] | P1 | Permanent Portfolio | `bt.permanent.portfolio*.test` |
| STR-003 | [ ] | P2 | Couch Potato portfolio | `couch.potato.strategy` |
| STR-004 | [ ] | P2 | 7Twelve portfolio | `bt.7twelve.strategy.test` |
| STR-005 | [ ] | P1 | Target-volatility allocation | `target.vol.strategy` |
| STR-006 | [ ] | P2 | Adaptive Asset Allocation | `bt.aaa.combo`, `bt.aaa.minrisk` |
| STR-007 | [ ] | P1 | Relative-strength rotation | `rotation.strategy` |
| STR-008 | [ ] | P2 | Dual momentum | `bt.dual.momentum.test` |
| STR-009 | [ ] | P2 | Probabilistic momentum | `bt.probabilistic.momentum.test` |
| STR-010 | [ ] | P2 | Adjusted momentum | `bt.adjusted.momentum.test` |
| STR-011 | [ ] | P2 | Calendar and seasonality rules | `calendar.strategy` and calendar examples |
| STR-012 | [ ] | P3 | Regime-detection strategy | `bt.regime.detection.test` |
| STR-013 | [ ] | P3 | PCA/clustering strategy | PCA and clustering backtests |
| STR-014 | [ ] | P3 | Historical pattern matching | `bt.matching.find`, DTW/DDTW examples |
| STR-015 | [ ] | P2 | Volatility position sizing | `bt.volatility.position.sizing.test` |
| STR-016 | [ ] | P2 | Fixed stop | `bt.price.stop` and fixed-stop examples |
| STR-017 | [ ] | P2 | Trailing stop | Trailing-stop examples |
| STR-018 | [ ] | P3 | Time stop and combined time/price stop | `bt.time.stop`, `bt.time.price.stop` |
| STR-019 | [ ] | P3 | Profit target | Stop-strategy examples |
| STR-020 | [D] | P3 | Intraday strategies | Intraday examples |
| STR-021 | [D] | P3 | Pair-trading strategies | Pair/intraday examples |

## 10. Supporting Backtest Infrastructure Gaps

These items are not standalone models, but model results will be incomplete or misleading without them.

| ID | Status | Priority | Missing capability | R reference |
| --- | --- | --- | --- | --- |
| INF-001 | [~] | P0 | Share-level portfolio state evolution | `bt.run.share`, `bt.run.share.ex` |
| INF-002 | [~] | P0 | Cash ledger for simulated activity | `compute.cash` |
| INF-003 | [~] | P0 | Commission model | `compute.commission` |
| INF-004 | [~] | P0 | Buy/sell slippage model | Execution-price examples |
| INF-005 | [~] | P0 | Trade and rebalance event history | `bt.trade.summary` |
| INF-006 | [~] | P0 | Portfolio turnover calculation | `compute.turnover` |
| INF-007 | [ ] | P0 | Exposure calculation | `compute.exposure` |
| INF-008 | [ ] | P1 | Dividend and split handling | `bt.unadjusted.add.div.split` |
| INF-009 | [ ] | P1 | Contributions and withdrawals | Cash-flow event helpers |
| INF-010 | [ ] | P1 | Fractional/whole-share and lot-rounding policy | `round.lot` functions |
| INF-011 | [ ] | P1 | Minimum trade size and residual-cash handling | Allocation helpers |
| INF-012 | [ ] | P1 | Strategy comparison result contract | R side-by-side reports |
| INF-013 | [ ] | P1 | Saved experiment cloning and comparison | Required by Portfolio Lab requirements |
| INF-014 | [D] | P3 | Tax-lot accounting | Extended R share engine |
| INF-015 | [D] | P3 | Wash-sale handling | `record.wash.sale`, `check.wash.sale` |
| INF-016 | [D] | P3 | Intraday execution and liquidity modeling | Intraday examples |

## 11. Additional Performance Metric Gaps

These metrics should not block the optimization foundation, but several support the planned Portfolio Lab comparison view.

| ID | Status | Priority | Missing metric | R implementation |
| --- | --- | --- | --- | --- |
| MET-001 | [ ] | P1 | Calmar ratio | `compute.calmar` |
| MET-002 | [ ] | P2 | R-squared | `compute.R2` |
| MET-003 | [ ] | P2 | DVR metric | `compute.DVR` |
| MET-004 | [ ] | P2 | Average drawdown | `compute.avg.drawdown` |
| MET-005 | [ ] | P2 | Conditional Drawdown at Risk metric | `compute.cdar` |
| MET-006 | [C] | P2 | Historical VaR metric | `compute.var` |
| MET-007 | [C] | P2 | Historical CVaR metric | `compute.cvar` |
| MET-008 | [~] | P1 | Turnover | `compute.turnover` |
| MET-009 | [x] | P1 | Allocation drift/deviation | `compute.max.deviation` |
| MET-010 | [ ] | P2 | Exposure percentage | `compute.exposure` |
| MET-011 | [ ] | P3 | Ulcer Index | `ulcer.index` |
| MET-012 | [ ] | P3 | EV ratio | `ev.ratio` |

## 12. Requirements Conflict Requiring Resolution

The consolidated project contains conflicting scope instructions:

1. The Portfolio Dashboard Requirements v1.1 make a dedicated Portfolio Lab mandatory and list risk-based allocation among its P0 capabilities.
2. The development guide’s deferred-scope section prohibits risk parity, Black–Litterman, hierarchical risk parity, and VaR/CVaR before a later amendment.

The development guide states that code must conform to its normative rules unless it is explicitly amended. Therefore, an implementation agent should not add the conflicting capabilities until the guide is amended.

### Required resolution

- [ ] Decide which advanced allocation models belong in the first Portfolio Lab release.
- [ ] Amend the development guide’s MVP scope and deferred-scope sections.
- [ ] Define the formulas, constraints, missing-data behavior, solver validation, provenance, and test requirements for every model moved into scope.
- [ ] Align the Portfolio Dashboard Requirements, development guide, roadmap, and acceptance gates.

Recommended first-release decision:

- Move inverse-volatility allocation and one canonical risk-parity/ERC implementation into Portfolio Lab P1.
- Keep Black–Litterman, HRP, VaR/CVaR optimization, factor models, and advanced tactical strategies deferred until the base optimizer and backtest engine are proven.

## 13. Recommended Implementation Order

### Phase 1 — Optimization contracts and estimators

**Goal:** Establish trustworthy inputs and solver boundaries.

- [ ] Define immutable optimization request/result contracts.
- [ ] Implement complete-case return alignment for an asset set.
- [ ] Implement sample covariance matrix and expected-return estimates.
- [ ] Define weight bounds, total-weight, cash, and feasibility rules.
- [ ] Implement independent solver-result validation.
- [ ] Attach analytical provenance, warnings, assumptions, and engine version.
- [ ] Add unit, property, validation, and independent numerical-reference tests.

**Exit gate:** The engine produces deterministic, validated estimator and constraint objects without performing portfolio optimization.

### Phase 2 — Initial allocation optimizers

**Goal:** Deliver the canonical allocation comparison required by the development guide.

- [ ] Implement equal-weight allocation.
- [ ] Implement static/custom target weights.
- [ ] Implement minimum-variance allocation.
- [ ] Implement maximum-Sharpe allocation.
- [ ] Implement efficient frontier generation.
- [ ] Implement target-return and target-risk helpers if needed by frontier generation.
- [ ] Revalidate all returned weights and objectives outside the solver.
- [ ] Persist reproducible optimization runs through the Django application layer.
- [ ] Add comparison API contracts and tests.

**Exit gate:** A user can compare current, equal-weight, minimum-variance, and maximum-Sharpe allocations and view a validated efficient frontier.

### Phase 3 — Rebalancing engine

**Goal:** Convert validated target allocations into transparent simulations.

- [x] Implement target-weight validation.
- [x] Implement absolute and relative drift.
- [x] Implement simulated target values and trade notionals.
- [x] Implement monthly, quarterly, and annual schedules.
- [x] Implement absolute drift-threshold rebalancing.
- [x] Implement deterministic cash and cost treatment for historical rebalancing comparisons.
- [x] Calculate trade count, turnover, maximum drift, and costs for historical rebalancing comparisons.
- [x] Persist reproducible current and historical rebalance simulations/comparisons.

**Exit gate:** A user can compare scheduled and threshold-based rebalancing against buy-and-hold using identical inputs and assumptions.

### Phase 4 — Backtest engine foundation

**Goal:** Create the deterministic simulation substrate before adding strategy breadth.

- [ ] Define strategy protocol and time-bounded `StrategyContext`.
- [ ] Enforce observe-at-`t`, execute-at-`t+1` structurally.
- [ ] Implement portfolio state, holdings, cash, orders, and fills.
- [ ] Implement commission and slippage models.
- [ ] Implement warm-up requirements and missing-price policies.
- [ ] Implement benchmark alignment.
- [ ] Produce equity, returns, drawdown, allocation, trade, turnover, and cost series.
- [ ] Persist immutable run configuration, versions, warnings, and results.
- [ ] Add look-ahead tripwire tests and deterministic replay tests.

**Exit gate:** The same run inputs produce equivalent outputs, no strategy can access future data, and failed runs remain auditable.

### Phase 5 — Initial strategy catalog

**Goal:** Meet the current MVP backtesting gate.

- [ ] Buy-and-hold.
- [ ] Moving-average timing.
- [ ] Momentum.
- [ ] Scheduled allocation rebalancing.
- [ ] Threshold allocation rebalancing.
- [ ] Benchmark and frictionless-baseline comparisons.
- [ ] Strategy comparison API and Portfolio Lab presentation contracts.

**Exit gate:** Users can run, save, reopen, and compare the required strategies with explicit assumptions and standard metrics.

### Phase 6 — Risk-based allocations

**Goal:** Expand Portfolio Lab allocation methodologies after resolving scope conflicts.

- [ ] Inverse volatility.
- [ ] Inverse variance.
- [ ] Risk parity/equal risk contribution.
- [ ] Risk contribution reporting.
- [ ] Maximum diversification.
- [ ] Target volatility.
- [ ] Add stability, degenerate-covariance, and infeasible-constraint tests.

**Exit gate:** Risk-based strategies behave deterministically and remain stable under documented edge cases.

### Phase 7 — Estimator expansion

**Goal:** Reduce optimizer sensitivity to noisy sample covariance inputs.

- [ ] Ledoit–Wolf shrinkage.
- [ ] Constant-correlation shrinkage.
- [ ] Diagonal shrinkage.
- [ ] Single-index shrinkage.
- [ ] Two-parameter shrinkage.
- [ ] Exponentially weighted covariance.
- [ ] Estimator comparison and provenance.

**Exit gate:** Every optimization result identifies its estimator and can be reproduced using the retained configuration and data cutoff.

### Phase 8 — Advanced portfolio research models

**Goal:** Add sophisticated models only after the standard engine is numerically validated.

- [ ] Hierarchical risk parity.
- [ ] Cluster risk parity.
- [ ] Black–Litterman.
- [ ] Minimum tracking error.
- [ ] Robust/resampled optimization.
- [ ] Minimum-correlation models.
- [ ] CVaR and CDaR optimization.
- [ ] Omega, MAD, downside-risk, and Gini objectives.
- [ ] Factor risk models and factor-aware optimization.

**Exit gate:** Each advanced model has a normative formula, independent reference fixtures, failure behavior, and explicit product labeling.

### Phase 9 — Tactical and experimental strategies

**Goal:** Build a curated research library without destabilizing core portfolio analysis.

- [ ] Permanent Portfolio, 60/40, Couch Potato, and 7Twelve templates.
- [ ] Relative-strength rotation and dual momentum.
- [ ] Adaptive Asset Allocation.
- [ ] Calendar/seasonality strategies.
- [ ] Regime and turbulence strategies.
- [ ] PCA/clustering strategies.
- [ ] Stops, profit targets, and volatility position sizing.
- [ ] Pattern matching only after research-governance requirements are defined.

**Exit gate:** Strategies are versioned, reproducible, clearly labeled as hypothetical, and cannot bypass the canonical execution engine.

## 14. Cross-Cutting Definition of Done

A model or strategy is not complete merely because it returns a number. Every completed register item must satisfy all applicable conditions below.

- [ ] Formula and assumptions are documented normatively.
- [ ] Input and output contracts are immutable and framework independent.
- [ ] Dates, annualization, return convention, and price field are explicit.
- [ ] No missing value is silently converted to zero or forward-filled.
- [ ] Solver or numerical success is independently validated.
- [ ] Failure and infeasibility produce typed, actionable results.
- [ ] Analytical provenance and engine/model version are returned.
- [ ] Unit tests cover known analytical fixtures.
- [ ] Property tests cover invariants and generated edge cases.
- [ ] Validation tests compare selected results with an independent implementation or analytical solution.
- [ ] Look-ahead tripwire tests exist for every time-dependent model.
- [ ] Same inputs, versions, and data cutoff reproduce equivalent results.
- [ ] API and persistence layers do not recalculate authoritative mathematics.
- [ ] UI labels distinguish historical, simulated, estimated, and actual values.
- [ ] Limitations and data-quality warnings remain attached to saved results.
- [ ] Relevant development-guide and acceptance-gate sections are updated.

## 15. Suggested Progress Summary

Update this table as phases move forward.

| Phase | Status | Owner | Target | Notes |
| --- | --- | --- | --- | --- |
| 1. Optimization contracts and estimators | Not started |  |  |  |
| 2. Initial allocation optimizers | Not started |  |  |  |
| 3. Rebalancing engine | Release audit pending |  |  | Historical annual/quarterly/threshold comparison and the Rebalancing Lab frontend are implemented; generic strategy/buy-and-hold work remains Phase 6 scope. |
| 4. Backtest engine foundation | Not started |  |  |  |
| 5. Initial strategy catalog | Not started |  |  |  |
| 6. Risk-based allocations | Blocked by scope amendment |  |  |  |
| 7. Estimator expansion | Not started |  |  |  |
| 8. Advanced research models | Deferred |  |  |  |
| 9. Tactical/experimental strategies | Deferred |  |  |  |

## 16. Maintenance Rules

When completing or changing an item:

1. Change its status marker in the relevant register table.
2. Record the implementation module and public API name.
3. Link the tests or validation fixture in the notes column.
4. Update the phase progress summary.
5. Add a dated entry to the change log.
6. If the mathematical behavior differs from the R implementation, document the intentional difference rather than preserving accidental parity.
7. Treat the project development guide—not the legacy R code—as the final authority after any necessary amendment.

## 17. Change Log

| Date | Change | Author |
| --- | --- | --- |
| 2026-09-15 | Initial gap register created from consolidated Python project and Systematic Investor Toolbox R comparison. |  |
| 2026-09-18 | Reconciled Phase 5 rebalancing status: target/drift/notional rules and historical annual/quarterly/threshold comparisons implemented; shared backtest infrastructure remains partial until Phase 6. |  |
| 2026-09-18 | Added the Rebalancing Lab frontend for target selection/creation, current drift/trade simulation, persisted policy comparison, provenance/warnings, and the deterministic browser workflow; v0.2 release audit remains. |  |

---

The R toolbox should be used as a capability inventory and independent reference source, not copied wholesale into the Python architecture. Portfolio Intelligence should retain its existing deterministic contracts, provenance rules, anti-look-ahead protections, typed failures, and independent validation requirements as each model is implemented.
