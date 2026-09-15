# Portfolio Intelligence Dashboard Requirements

**Document status:** Draft v1.1  
**Date:** September 15, 2026  
**Primary surface:** Authenticated portfolio overview dashboard  
**Reference:** User-provided portfolio dashboard image  

### Amendment history

| Version | Amendment | Summary |
| --- | --- | --- |
| 1.0 | Initial requirements | Portfolio overview dashboard derived from the reference design. |
| 1.1 | Speculative Portfolio Lab | Adds a required, dedicated page for constructing hypothetical portfolios and backtesting allocation and rebalancing strategies. |

## 1. Purpose

This document defines the product, UX, visual, data, interaction, accessibility, and technical requirements for the Portfolio Intelligence dashboard. The reference image establishes the desired visual hierarchy and interaction model; labels and metrics are adapted for a traditional investment portfolio rather than copied from the crypto-oriented example.

The dashboard must help an investor answer five questions within seconds:

1. What is my portfolio worth, and how has it performed?
2. What is driving that performance?
3. How is the portfolio allocated?
4. Where are the most important risks or imbalances?
5. What should I investigate next?

The dashboard is an analytical decision-support surface. It must explain observations and tradeoffs without presenting personalized financial advice as fact or implying guaranteed outcomes.

## 2. Product Goals

- Present a concise, high-confidence view of total portfolio health and performance.
- Make changes in value, return, allocation, concentration, and risk easy to understand.
- Connect summary metrics to the underlying holdings and calculations.
- Let users move from observation to deeper analysis with minimal navigation.
- Provide AI-generated explanations that are traceable to portfolio data and calculation dates.
- Support multiple data providers without exposing provider-specific behavior in the interface.
- Remain useful when portfolio data is incomplete, stale, or partially unavailable.

## 3. Scope

### 3.1 MVP scope

The initial dashboard shall include:

- Global navigation, search, notifications, and user controls.
- Portfolio selector and data-as-of indicator.
- Portfolio value and performance chart.
- Portfolio summary/breakdown card.
- Allocation visualization.
- Explainable portfolio health score.
- AI-generated portfolio summary and contextual question input.
- Holdings and movers panel with compact price charts.
- Dedicated Portfolio Lab page for constructing speculative portfolios and backtesting allocation and rebalancing strategies.
- Loading, empty, partial-data, stale-data, and error states.
- Desktop, tablet, and mobile layouts.
- Keyboard navigation and WCAG 2.2 AA support.

### 3.2 Later-phase capabilities

- Account aggregation and brokerage connections.
- Trade execution or brokerage order routing.
- Tax-lot optimization and tax-loss harvesting workflows.
- Monte Carlo projections and probabilistic goal forecasting beyond historical backtesting.
- Goal-based planning.
- Automated rebalancing.
- Real-time streaming prices.
- Natural-language actions that mutate portfolio data.

### 3.3 Non-goals for the dashboard

- Acting as a trading terminal.
- Promising future returns or displaying an unexplained “potential value.”
- Hiding missing or stale market data behind estimated values.
- Reducing portfolio quality to a score without explaining its drivers.
- Presenting AI output without calculation dates, scope, and supporting evidence.

## 4. Intended Users and Primary Journeys

### 4.1 Primary user

An individual investor who wants a clear, analytical understanding of one or more portfolios without needing institutional portfolio-management software.

### 4.2 Core journeys

| Journey | Expected outcome |
| --- | --- |
| Open the dashboard | User immediately sees portfolio value, selected-period performance, data freshness, and important alerts. |
| Change the time range | Performance chart, comparison values, and applicable summaries update consistently. |
| Inspect a chart point | User sees the date, portfolio value, period change, benchmark value/return, and any data-quality note. |
| Review portfolio health | User sees the overall score, its component scores, and the factors increasing or reducing it. |
| Investigate a concern | Selecting a risk, metric, allocation segment, or holding filters or opens supporting detail. |
| Ask a question | The assistant answers using the selected portfolio, date range, and selected dashboard context. |
| Review holdings | User scans prices, daily changes, weights, contribution, and compact trends, then opens a holding detail view. |
| Test an investment idea | User constructs a speculative portfolio, applies allocation and rebalancing rules, runs a backtest, and compares the result with alternative strategies and a benchmark. |

## 5. Reference-to-Product Translation

| Reference-image element | Portfolio Intelligence implementation |
| --- | --- |
| “Portfolio Performance” hero chart | Total portfolio market value and return, optionally compared with a benchmark. |
| “Actual” versus “Potential” | Actual portfolio versus selected benchmark; projections require a separate, clearly labeled scenario view. |
| Portfolio breakdown | Market value, cost basis, cash, total return, income, and selected risk indicators. |
| Token/stablecoin distribution | Allocation by asset class, sector, account, geography, or user-selected dimension. |
| Health score gauge | Explainable portfolio health score composed of diversification, concentration, risk, drawdown, fees, and data quality. |
| AI summary | Evidence-backed portfolio narrative with explicit as-of date and links to supporting metrics. |
| Pending/claimed activity | Data-quality alerts, unclassified transactions, account-sync issues, and review items. |
| Trending crypto cards | Holdings, top gainers, top losers, watchlist, and rebalance candidates. |

## 6. Information Architecture

### 6.1 Primary navigation

The collapsed left navigation shall provide recognizable icons, text labels on expansion or hover, tooltips, a visible active state, and keyboard access.

Recommended destinations:

1. Overview
2. Portfolios
3. Analytics
4. Allocation and Rebalancing
5. Portfolio Lab
6. Activity and Transactions
7. Watchlists
8. AI Insights
9. Settings

Navigation items unavailable in the MVP may be omitted rather than displayed as inactive placeholders.

### 6.2 Top application bar

The header shall contain:

- Product or current-page title.
- Global search or command input.
- Notifications control with unread-state indicator.
- User avatar, name, and account menu.
- Optional keyboard-shortcut hint for search.

### 6.3 Portfolio context bar

The content area shall display:

- Portfolio selector when the user has multiple portfolios.
- Portfolio name.
- Base currency.
- Market-data as-of timestamp.
- Last successful account/data synchronization time, when relevant.
- Clear stale or partial-data badge when freshness requirements are not met.

## 7. Desktop Layout Requirements

The desktop layout shall preserve the reference image’s asymmetric hierarchy: a broad analytical canvas on the left and a narrower intelligence panel on the right.

| Region | Recommended width | Contents |
| --- | ---: | --- |
| Left navigation | 64–80 px collapsed | Primary navigation and sign-out/account control. |
| Main analytical column | 65–72% of remaining width | Performance hero, portfolio summary, allocation, health score, holdings/movers. |
| Intelligence column | 28–35% of remaining width | AI greeting/assistant, summary, alerts, contextual question input. |

Implementation requirements:

- Use a 12-column grid with consistent 16–24 px gutters.
- Keep the performance card as the dominant visual element above the fold.
- Align card edges, titles, control rows, and baselines across modules.
- Use a maximum content width appropriate for wide monitors while avoiding excessively stretched charts.
- Use sticky behavior for the application header. The right intelligence column may become sticky only if it does not hide content or create nested scrolling traps.
- Cards shall use consistent padding, corner radius, border treatment, and elevation.

## 8. Functional Component Requirements

### 8.1 Performance hero

**Purpose:** Communicate portfolio value and performance over the selected period.

The component shall provide:

- Current total market value in the portfolio base currency.
- Absolute and percentage change for the selected period.
- Time-range controls: 1W, 1M, 3M, 6M, YTD, 1Y, and All.
- Toggle between value view and return-percent view.
- Optional comparison against a user-selected benchmark.
- Portfolio series rendered as a line or area series.
- Benchmark series rendered with a visually distinct but subordinate style.
- Hover/focus tooltip containing date, portfolio value, portfolio change, benchmark value or return, and data-quality status.
- Accessible legend controls that can show or hide comparison series.
- Skeleton state while data loads.
- Empty state when the portfolio has insufficient history.
- Partial-data annotation when one or more holdings lack prices for part of the range.

Behavior requirements:

- Changing the time range shall update the headline change, chart domain, and applicable AI context.
- Performance comparisons shall use the same date range and calculation convention.
- The chart shall never interpolate across a material data gap without visually disclosing the gap.
- Dates shall follow the user’s locale and market calendar.
- Currency shall follow the portfolio base currency and user locale.
- The user shall be able to reach every data point or an equivalent summary with a keyboard.

### 8.2 Portfolio summary card

**Purpose:** Provide a compact accounting and risk snapshot.

MVP rows shall include:

- Total market value.
- Net contributions.
- Cost basis, where available.
- Cash balance and cash percentage.
- Unrealized gain/loss.
- Realized gain/loss for the selected period, where supported.
- Income received for the selected period, where supported.

Each row shall include a label, value, optional percentage change, concise definition, and click-through to supporting detail. Metrics that are unavailable shall display “Not available” with an explanation rather than zero.

### 8.3 Allocation card

**Purpose:** Show how capital is distributed and expose concentrations.

The component shall provide:

- Primary grouping selector: asset class, sector, account, geography, or currency.
- Total invested value and uninvested cash.
- Visual comparison of allocation weights.
- Exact value and percentage in hover/focus tooltips.
- Legend that remains usable without relying only on color.
- Clickable segments that filter the holdings panel or open allocation detail.
- “Other” grouping rules that are consistent and disclosed.

For the MVP, a horizontal stacked bar or compact grouped bars are preferred over a dense pie chart. The visualization must remain readable when categories have materially different sizes.

### 8.4 Portfolio health score

**Purpose:** Summarize portfolio condition while keeping the calculation explainable.

The score shall:

- Use a 0–100 scale.
- Display a semantic label such as Needs Attention, Fair, Good, or Strong.
- Show the calculation date.
- Link to component-level detail.
- Explain what improved or reduced the score.
- Display “Insufficient data” when minimum inputs are not available.

Recommended score components:

| Component | What it measures |
| --- | --- |
| Diversification | Distribution across asset classes, sectors, issuers, and accounts. |
| Concentration | Exposure to individual securities and correlated groups. |
| Volatility | Realized variability relative to the portfolio’s stated risk profile or benchmark. |
| Drawdown | Magnitude and recency of peak-to-trough declines. |
| Allocation drift | Difference between current and target allocation, when a target exists. |
| Fees | Known expense ratios and account costs, when data is available. |
| Data quality | Coverage, freshness, classification completeness, and pricing confidence. |

The overall score must not be presented until the weighting model, thresholds, missing-data rules, and versioning strategy are documented and tested. The gauge shall supplement—not replace—the numeric score and component breakdown.

### 8.5 AI intelligence panel

**Purpose:** Turn dashboard data into understandable, actionable investigation paths.

The panel shall include:

- Context-aware greeting or neutral assistant heading.
- Daily or on-demand portfolio summary.
- Two to four prioritized observations.
- “Why this matters” explanation for material observations.
- Links that navigate to the supporting metric, holding, chart range, or analytical view.
- Input labeled similarly to “Ask about this portfolio” or “Ask about selected data.”
- Clear disclosure of the selected portfolio, date range, and dashboard element included in the question context.
- Expand control for a full assistant workspace.

AI output requirements:

- Every material numeric claim shall be grounded in calculated portfolio data.
- The response shall state the relevant as-of date.
- The interface shall distinguish facts, estimates, scenarios, and general education.
- The assistant shall not imply certainty, guaranteed results, or fiduciary advice.
- When data is incomplete, the assistant shall identify the limitation rather than infer missing values.
- Generated summaries shall be stored with calculation/model metadata sufficient for audit and reproducibility.
- A user shall be able to dismiss a summary and regenerate it.

### 8.6 Alerts and review items

The intelligence panel shall summarize items requiring attention, including:

- Stale or failed account synchronization.
- Missing or stale prices.
- Unclassified transactions.
- Material allocation drift.
- Concentration threshold breaches.
- Significant portfolio movement.
- Corporate actions requiring review, when available.

Each count shall open a filtered detail view. Severity shall be communicated through text/iconography in addition to color.

### 8.7 Holdings and movers panel

**Purpose:** Make the portfolio’s underlying drivers scannable.

Recommended tabs:

- Holdings
- Top Gainers
- Top Losers
- Largest Contributors
- Largest Detractors
- Watchlist
- Rebalance Candidates, when target allocations exist

Each compact holding card or row shall display:

- Symbol and security name.
- Asset icon or fallback initials.
- Latest price and currency.
- Daily or selected-period percentage change.
- Portfolio weight.
- Contribution to selected-period return, when calculated.
- Compact sparkline.
- Price timestamp and delayed-data label where applicable.

The user shall be able to sort, scroll, or page through holdings and open a detailed security view. Positive and negative movement shall use signs, arrows, and text—not color alone.

### 8.8 Search

Global search shall support:

- Portfolios.
- Accounts.
- Holdings by symbol or company name.
- Dashboard metrics and analytical views.
- Commands or navigation shortcuts in a later phase.

Search results shall be keyboard navigable and grouped by result type.

## 9. Speculative Portfolio Lab and Backtesting

### 9.1 Purpose and product role

Portfolio Intelligence shall include a dedicated **Portfolio Lab** page where a user can construct a hypothetical portfolio, define an investment strategy, run historically accurate backtests, compare alternatives, and save reproducible experiments.

The Portfolio Lab is a required product surface, not a modal attached to the overview dashboard. It shall be accessible from primary navigation and use a route such as `/portfolio-lab`. The page must keep hypothetical assets, results, and transactions clearly separated from the user’s actual portfolio and brokerage data.

The page shall help the user answer:

1. How would this portfolio have performed historically?
2. How does the result change under a different allocation method?
3. How do calendar, threshold, and hybrid rebalancing rules compare?
4. What risk, drawdown, turnover, and cost accompanied the return?
5. Which assumptions materially drive the result?
6. Can the exact experiment be reproduced later?

Historical results shall always be labeled as hypothetical and shall never be presented as a forecast or guarantee of future performance.

### 9.2 Page structure

The desktop page shall use a configurable two-region workspace:

| Region | Purpose | Required content |
| --- | --- | --- |
| Strategy builder | Configure the experiment | Portfolio assets, allocation methodology, rebalancing rules, test period, benchmark, cash flows, costs, and advanced assumptions. |
| Results workspace | Analyze and compare outcomes | Summary metrics, charts, allocation history, trades/rebalances, assumptions, warnings, and saved-run comparison. |

The strategy builder may use a persistent left panel, stepper, or drawer. It shall remain editable without losing the most recent successful result. Unsaved configuration changes must be visually distinguished from the last executed configuration.

Recommended workflow:

1. Choose a starting point.
2. Select the investment universe and assets.
3. Select an allocation methodology.
4. Select a rebalancing methodology.
5. Define backtest assumptions.
6. Validate the configuration.
7. Run the backtest.
8. Review, compare, save, clone, or export the result.

### 9.3 Speculative portfolio construction

The user shall be able to start from:

- A blank speculative portfolio.
- A copy of an actual portfolio, with no connection back to live holdings.
- A saved watchlist.
- A previously saved Portfolio Lab experiment.
- A system-provided educational template.

The builder shall support:

- Search and entry of one or more ticker symbols.
- Security name, asset type, exchange, trading currency, and provider identifier confirmation.
- Duplicate-symbol and ambiguous-symbol resolution.
- Inclusion of a cash allocation.
- Drag, keyboard, or explicit-control reordering where ordering is meaningful.
- Removal and replacement of assets.
- Per-asset minimum and maximum weight constraints.
- Optional group constraints by asset class, sector, geography, or user-defined group.
- A validation summary before execution.

The UI shall identify assets that lack sufficient history for the requested test period. The user must choose whether to shorten the test period, remove the asset, use an explicitly documented inception rule, or cancel the run. The system shall not silently backfill a security with a proxy.

### 9.4 Allocation methodologies

The page shall support multiple portfolio-allocation methods through a versioned strategy interface. At minimum, the strategy catalog shall include:

| Method | Required behavior |
| --- | --- |
| Custom weights | User supplies target weights; weights plus cash must total 100% within a documented tolerance. |
| Equal weight | Capital is divided equally among included assets, subject to constraints. |
| Market-cap weight | Weights use point-in-time market-cap data where reliable historical data exists; unavailable history must block or explicitly limit the method. |
| Inverse volatility | Lower-volatility assets receive higher weights based on a configurable trailing lookback window. |
| Risk parity | Assets are weighted toward a target risk contribution under documented covariance and constraint rules. |
| Minimum variance | Optimizer minimizes expected portfolio variance subject to configured constraints. |
| Mean-variance | Optimizer balances expected return and variance using explicit, user-visible assumptions; it shall not be the default. |

Each method shall expose:

- Plain-language description.
- Required data and minimum lookback period.
- Configurable parameters and defaults.
- Constraints and feasibility errors.
- Strategy version.
- The target weights generated at every rebalance event.

Optimization failure, singular covariance, insufficient lookback, infeasible constraints, and unstable solutions shall return clear diagnostic messages. The engine must not silently substitute a different method.

### 9.5 Rebalancing methodologies

The user shall be able to compare at least the following approaches:

| Method | Configuration |
| --- | --- |
| Buy and hold | No rebalancing after initial allocation. |
| Calendar based | Weekly, monthly, quarterly, semiannual, or annual schedule with a defined trading-day convention. |
| Threshold based | Rebalance when an asset or group deviates from target by an absolute or relative tolerance. |
| Calendar plus threshold | Evaluate drift on scheduled dates and trade only when a threshold is breached. |
| Contribution based | Direct recurring contributions toward underweight assets before selling holdings. |
| Tactical rule based | Apply an approved, versioned signal or regime rule using only information available at the decision time. |

Rebalancing configuration shall include:

- Target-weight source.
- Review frequency.
- Drift threshold definition.
- Full versus partial rebalance behavior.
- Trade execution timing.
- Minimum trade size.
- Fractional-share availability.
- Cash reserve target.
- Transaction-cost and slippage assumptions.
- Treatment of dividends, distributions, and recurring contributions/withdrawals.
- Optional turnover constraint.

The interface shall preview the rule in plain language before execution, for example: “Review monthly; rebalance to equal weights when any holding is more than 5 percentage points from target; execute at the next available close.”

### 9.6 Backtest configuration

Every run shall capture:

- Experiment name and optional description.
- Start and end date.
- Initial capital.
- Base currency.
- Price-data provider and data cutoff.
- Benchmark.
- Allocation strategy and complete parameters.
- Rebalancing strategy and complete parameters.
- Lookback and warm-up rules.
- Execution-price convention.
- Trading calendar.
- Dividend and distribution treatment.
- Corporate-action treatment.
- Contribution and withdrawal schedule.
- Transaction costs, slippage, and fees.
- Fractional-share and cash handling.
- Tax treatment, or an explicit “taxes excluded” statement.

Default values shall be visible and included in saved configuration. Advanced assumptions may be collapsed, but no material assumption may be hidden from the results.

### 9.7 Backtesting integrity and bias controls

The backtesting engine shall enforce the following non-negotiable rules:

- No signal, price, fundamental value, classification, or market-cap value may be used before it was available to the strategy.
- A decision calculated using closing data shall execute no earlier than the next permitted execution point unless the strategy explicitly models a valid same-session order convention.
- Rolling statistics and optimization inputs shall use only trailing observations available at the decision timestamp.
- Corporate actions and adjusted prices shall be handled consistently without double-counting distributions.
- Benchmark and portfolio returns shall use aligned calendars and clearly disclosed gap rules.
- Rebalance dates falling on non-trading days shall follow a documented convention.
- Missing prices shall not be forward-filled beyond an approved limit without a visible warning.
- Delisted securities and changes in the eligible universe shall follow a documented point-in-time policy.
- The system shall disclose when available data may contain survivorship bias.
- Randomized or stochastic methods shall store their random seed.
- Rounding, residual cash, fractional shares, and transaction sequencing shall be deterministic.

The engine shall reject configurations that cannot be tested without violating these rules. Warnings shall be classified as blocking or non-blocking and stored with the run.

### 9.8 Required results and metrics

The results header shall prominently display:

- Ending value.
- Cumulative return.
- Compound annual growth rate.
- Annualized volatility.
- Maximum drawdown.
- Sharpe ratio with disclosed risk-free-rate assumption.
- Benchmark return.
- Excess return.
- Total transaction costs.
- Turnover.

The detailed metrics panel should additionally support:

- Sortino ratio.
- Calmar ratio.
- Beta and alpha.
- Tracking error and information ratio.
- Downside deviation.
- Best and worst period.
- Recovery duration.
- Value at Risk and Conditional Value at Risk where the methodology is approved and clearly labeled.
- Number of rebalances and trades.
- Contributions, withdrawals, income, fees, and residual cash.

Every metric shall link to its definition, calculation convention, and effective sample period. Ratios shall display “Not available” rather than misleading values when the sample is insufficient or the denominator is invalid.

### 9.9 Required result visualizations

The results workspace shall include:

- Growth of a nominal investment for strategy and benchmark.
- Portfolio value over time.
- Drawdown curve.
- Rolling return and rolling volatility.
- Allocation weights over time.
- Rebalance-event markers.
- Asset contribution to total return.
- Periodic return heatmap or table.
- Turnover and transaction-cost history.

All charts shall use the shared ECharts theme, accessible legends, keyboard-equivalent summaries, synchronized date cursors where useful, and exportable underlying data. Tooltips shall distinguish target weights from realized weights and pre-trade from post-trade values.

### 9.10 Strategy comparison

The user shall be able to compare at least three saved or newly executed runs side by side. Comparison shall provide:

- Overlaid growth and drawdown charts.
- Aligned metric table.
- Parameter-difference table.
- Common benchmark and date-window controls.
- Clear warnings when runs use different data snapshots, currencies, dates, assumptions, or benchmark definitions.
- Ability to designate a baseline run.
- Ability to clone a run and change one or more parameters.

The comparison view shall not rank strategies solely by return. Risk, drawdown, costs, turnover, and data limitations shall remain visible.

### 9.11 Saved experiments and reproducibility

Each successful run shall receive an immutable run identifier and store:

- Owner and timestamps.
- Full normalized configuration.
- Portfolio constituent identifiers.
- Strategy code/version identifiers.
- Price and reference-data snapshot identifiers or reproducible cutoff metadata.
- Calculation-engine version.
- Warnings and data-quality report.
- Output metrics and result-series references.
- Random seed where applicable.

Users shall be able to name, save, clone, archive, and reopen experiments. Editing a saved experiment shall create a new run rather than mutate historical results. A saved run must display whether it can still be reproduced exactly with retained data and code versions.

### 9.12 Execution and status behavior

- Backtests shall run as asynchronous jobs when execution is not predictably immediate.
- The UI shall show queued, validating, running, succeeded, failed, and canceled states.
- Users shall be able to leave the page and return without losing a run.
- Repeated submission of an identical request shall not create duplicate work unintentionally.
- Users shall be able to cancel a queued or running job where technically safe.
- A failed run shall retain its configuration, validation output, and actionable error details.
- Results shall appear only after the full run completes and passes output validation.

### 9.13 AI assistance within the Portfolio Lab

The assistant may:

- Explain strategy and metric definitions.
- Summarize differences between completed runs.
- Identify which assumptions drove a result.
- Suggest educational experiments, such as testing a different rebalance threshold.
- Generate a draft configuration for explicit user review.

The assistant shall not silently execute a backtest, modify a saved experiment, choose an “optimal” strategy without qualification, or describe historical outperformance as expected future performance. AI commentary must cite the relevant run, date range, configuration, and result metrics.

### 9.14 Portfolio Lab responsive behavior

- On large screens, configuration and results may appear side by side.
- On tablet, the builder shall collapse into a drawer or stepper above the results.
- On mobile, configuration shall use a sequential flow and results shall use vertically stacked metric cards and full-screen chart detail.
- Long parameter and metric tables shall transform into labeled cards or support accessible horizontal scrolling.
- Running, saved, and comparison states must remain recoverable across breakpoint changes.

### 9.15 Portfolio Lab acceptance criteria

The Portfolio Lab is ready for release when:

1. A user can create a hypothetical portfolio without changing an actual portfolio.
2. The builder validates symbols, weights, constraints, required history, and date range before execution.
3. The user can run custom-weight, equal-weight, and at least one risk-based allocation strategy.
4. The user can test buy-and-hold, calendar-based, threshold-based, and calendar-plus-threshold rebalancing.
5. Costs, slippage, dividends, cash, fractional shares, and execution timing are configurable or explicitly declared by the system.
6. Automated tests prove that no future observation can enter allocation, signal, or execution decisions.
7. Results include return, volatility, drawdown, risk-adjusted performance, turnover, costs, benchmark comparison, and allocation history.
8. A user can compare at least three runs and see both result and configuration differences.
9. Every saved run includes sufficient configuration, version, and data-cutoff metadata to reproduce or explain the result.
10. Failed and canceled runs preserve configuration and provide actionable status.
11. The interface clearly labels all results as hypothetical and historical.
12. The primary builder and results workflows are usable by keyboard and at supported responsive widths.

## 10. Interaction and Cross-Filtering Requirements

- Selecting a portfolio updates every dashboard module through a single shared portfolio context.
- Selecting a time range updates performance metrics, return attribution, mover rankings, and AI context where those calculations depend on time.
- Selecting an allocation segment filters the holdings panel and displays a removable filter chip.
- Selecting a health-score component opens or reveals its supporting metrics.
- Selecting a holding opens its detail route without losing the originating portfolio/time context.
- All filters shall have a visible reset mechanism.
- Browser back/forward behavior shall restore route-level selections.
- Shareable dashboard URLs should encode portfolio, time range, comparison, and tab state without exposing sensitive account identifiers.

## 11. Data and Calculation Requirements

### 11.1 Required entities

The dashboard requires normalized data for:

- User and portfolio.
- Account and provider connection.
- Security/instrument master.
- Position snapshots.
- Cash balances.
- Transactions and cash flows.
- Price history and corporate actions.
- Benchmark price history.
- Target allocation, when configured.
- Calculated returns, risk metrics, contribution, and health-score components.
- Data-quality events and calculation metadata.
- Speculative portfolio definitions and constituent constraints.
- Versioned allocation and rebalancing strategy definitions.
- Backtest configurations, jobs, immutable runs, warnings, and result series.
- Rebalance events, simulated orders, simulated fills, costs, and residual cash.
- Historical point-in-time classifications and market-cap inputs where required by a strategy.

### 11.2 Core metric definitions

At minimum, the implementation specification shall define and test:

- Market value by holding, account, and portfolio.
- Net deposits and withdrawals.
- Daily and selected-period gain/loss.
- Money-weighted return and time-weighted return, including which appears by default.
- Benchmark-relative return.
- Asset-allocation weights.
- Contribution to return.
- Volatility and maximum drawdown.
- Concentration measures.
- Allocation drift.
- Health-score inputs and aggregation.
- Backtest cumulative return, CAGR, volatility, drawdown, risk-adjusted metrics, turnover, and simulated costs.
- Target and realized allocation at every simulated rebalance.

### 11.3 Time-series integrity

- Calculations shall use only information available as of each observation date.
- Adjusted and unadjusted price usage shall be explicit and consistent.
- Corporate actions shall be applied without double-counting returns.
- Market holidays, weekends, missing prices, and differing trading calendars shall be handled deterministically.
- No future observation may influence a historical dashboard value.
- Recomputed analytical outputs shall retain calculation version, source-data cutoff, and run timestamp.

### 11.4 Data freshness

Every market-sensitive module shall expose an as-of time. Suggested states:

| State | Behavior |
| --- | --- |
| Current | Display normally. |
| Delayed | Show a delayed-data label and timestamp. |
| Stale | Show a warning and explain which metrics may be affected. |
| Partial | Identify affected accounts/holdings and calculate only under documented rules. |
| Unavailable | Preserve the layout and display a retry or resolution path. |

## 12. API and Frontend Data Contract Requirements

The frontend shall receive display-ready analytical payloads from the backend rather than reimplementing financial calculations in React.

Recommended read endpoints or equivalent query contracts:

- `GET /api/v1/portfolios`
- `GET /api/v1/portfolios/{id}/dashboard`
- `GET /api/v1/portfolios/{id}/performance`
- `GET /api/v1/portfolios/{id}/allocation`
- `GET /api/v1/portfolios/{id}/health`
- `GET /api/v1/portfolios/{id}/holdings`
- `GET /api/v1/portfolios/{id}/alerts`
- `GET /api/v1/portfolios/{id}/insights`
- `POST /api/v1/portfolios/{id}/assistant/messages`
- `GET /api/v1/portfolio-lab/strategies`
- `POST /api/v1/portfolio-lab/experiments`
- `GET /api/v1/portfolio-lab/experiments`
- `GET /api/v1/portfolio-lab/experiments/{id}`
- `POST /api/v1/portfolio-lab/backtests`
- `GET /api/v1/portfolio-lab/backtests/{run_id}`
- `POST /api/v1/portfolio-lab/backtests/{run_id}/cancel`
- `GET /api/v1/portfolio-lab/backtests/{run_id}/results`
- `POST /api/v1/portfolio-lab/comparisons`

Every analytical response shall include:

- Portfolio identifier.
- Base currency.
- Requested and effective date range.
- Data-as-of timestamp.
- Calculation timestamp and calculation version.
- Source/provider coverage status.
- Values with sufficient raw precision for correct formatting.
- Explicit nulls and reason codes for unavailable metrics.
- Stable identifiers for drill-down navigation.

Portfolio Lab run responses shall additionally include immutable run identifier, normalized strategy configuration, strategy and engine versions, data cutoff/snapshot metadata, execution assumptions, validation warnings, job status, and reproducibility status.

The API shall authorize access at the portfolio/account level. Client-supplied portfolio identifiers must never be treated as proof of access.

## 13. Visualization Requirements

The React frontend shall use Apache ECharts for the performance chart, allocation chart, health visualization, holding sparklines, and Portfolio Lab result visualizations.

Implementation requirements:

- Charts shall resize through a `ResizeObserver` or equivalent container-aware mechanism.
- Shared chart theme tokens shall control type, gridlines, semantic colors, tooltips, and focus styling.
- ECharts ARIA support shall be enabled where applicable.
- Every chart shall have a text summary or data-table alternative.
- Tooltips shall be accessible by pointer and keyboard-equivalent interaction.
- Chart animations shall respect `prefers-reduced-motion`.
- Large time series shall be downsampled in a documented, visually faithful manner.
- The frontend shall not invent or interpolate calculated values for presentation convenience.

## 14. Visual Design System

### 14.1 Visual direction

The interface should feel modern, calm, analytical, and premium. It shall use generous whitespace, light neutral surfaces, thin borders, restrained elevation, and a limited accent palette. Information density should be high enough for analysis without resembling a trading terminal.

### 14.2 Semantic color roles

| Role | Usage |
| --- | --- |
| Primary blue | Portfolio series, selected controls, links, focus accents. |
| Positive green | Positive change and healthy status, accompanied by icon/text. |
| Negative red/orange | Negative change, loss, or elevated risk, accompanied by icon/text. |
| Comparison violet | Benchmark or secondary analytical series. |
| Warning amber | Stale data, allocation drift, and review-needed states. |
| Neutral gray | Secondary text, gridlines, inactive controls, and surfaces. |

Exact tokens shall be defined in the frontend design-token layer rather than embedded directly in components. Light theme is required for the MVP; tokens shall be structured so a dark theme can be added later.

### 14.3 Typography and number formatting

- Use a legible sans-serif UI typeface.
- Use tabular numerals for financial values where supported.
- Establish clear styles for page title, card title, hero value, body, label, caption, and metadata.
- Format values consistently by locale and currency.
- Abbreviated values such as `$128.4K` may appear in summary positions, but exact values must be available on focus/hover or in detail views.
- Always display a sign for directional percentage changes.
- Do not use excessive decimal precision.

## 15. Responsive Requirements

### 15.1 Large desktop

- Display navigation, main analytical column, and intelligence column concurrently.
- Keep hero performance and AI summary above the fold where practical.

### 15.2 Tablet and small desktop

- Collapse the side navigation.
- Move the intelligence panel below the performance hero or expose it as a dedicated panel/drawer.
- Use a two-column card grid where space permits.

### 15.3 Mobile

- Use a single-column layout.
- Replace persistent left navigation with an accessible menu or bottom navigation.
- Use horizontally scrollable segmented controls only when all options remain discoverable.
- Convert holding cards to full-width rows.
- Provide a full-screen chart detail view for precise inspection.
- Ensure no essential information is available only through hover.

Target breakpoint behavior shall be tested at approximately 360 px, 768 px, 1024 px, 1440 px, and a wide desktop viewport.

## 16. Accessibility Requirements

- Meet WCAG 2.2 AA for the dashboard’s supported flows.
- Maintain at least 4.5:1 contrast for normal text and 3:1 for large text and meaningful UI graphics.
- Provide visible keyboard focus states.
- Support complete keyboard operation for navigation, filters, tabs, cards, charts, dialogs, and assistant controls.
- Provide programmatic labels for icons and icon-only buttons.
- Announce asynchronous state changes and filtering results appropriately.
- Do not use color as the sole indicator of gain, loss, warning, selection, or score state.
- Provide reduced-motion behavior.
- Use semantic headings and landmarks in a logical order.
- Preserve usable zoom through 200% without loss of content or function.

## 17. Loading, Empty, Error, and Edge States

Each module shall define and test:

- Initial loading skeleton.
- Background refresh state that does not blank existing data.
- Empty portfolio state with a clear import/connect/manual-entry path.
- Insufficient history state.
- Missing benchmark state.
- Provider/API failure state.
- Partial portfolio state.
- Stale market-data state.
- Unsupported security or missing classification state.
- AI summary unavailable state that leaves the analytical dashboard fully usable.
- Invalid or infeasible Portfolio Lab configuration.
- Insufficient lookback or price history.
- Backtest queued, running, failed, canceled, and completed states.
- Historical data limitations or survivorship-bias warning.
- Saved run that is viewable but no longer exactly reproducible.
- Retry behavior and user-facing error message.

Errors in one module shall not cause the entire dashboard to fail when the remaining data is valid.

## 18. Performance Requirements

- Render a useful dashboard shell and loading state promptly on first navigation.
- Target Largest Contentful Paint under 2.5 seconds on a representative broadband connection and production-like build.
- Avoid layout shift when charts and cards load.
- Lazy-load lower-page holdings and noncritical assistant history.
- Cache portfolio-summary responses according to data freshness and user authorization rules.
- Cancel or disregard stale requests when users rapidly switch portfolios or time ranges.
- Virtualize or paginate large holdings lists.
- Keep chart interactions responsive with multi-year daily data.
- Execute long-running backtests asynchronously and avoid blocking interactive dashboard requests.
- Define run-time, memory, constituent-count, history-length, and concurrent-job limits for Portfolio Lab workloads.
- Cache identical completed backtests only when authorization, engine version, strategy version, and source-data snapshot match.

Specific performance budgets shall be measured in CI or a repeatable performance test environment before release.

## 19. Security and Privacy Requirements

- Require authentication for every portfolio route and API request.
- Enforce object-level authorization on the server.
- Encrypt provider tokens and sensitive account data at rest and in transit.
- Never send credentials, provider tokens, or unnecessary personally identifiable information to an AI model.
- Limit AI context to the selected user-authorized portfolio and requested analytical scope.
- Log access to sensitive portfolio data and generated insights according to the application’s audit policy.
- Redact account numbers by default.
- Sanitize user-entered content rendered in assistant responses.
- Apply rate limits to assistant and expensive analytical endpoints.
- Keep speculative portfolios and simulated transactions logically separated from actual holdings and brokerage actions.
- Authorize saved experiments and backtest runs at the owner/workspace level and prevent identifier-based cross-user access.

## 20. Analytics and Observability

Capture privacy-conscious events for:

- Dashboard load success/failure and latency.
- Portfolio and time-range changes.
- Chart comparison use.
- Allocation and health-score drill-downs.
- Holding detail opens.
- Alert opens and resolutions.
- AI question submission, response success/failure, and cited-insight navigation.
- Empty-state connection/import starts.
- Portfolio Lab configuration validation, run start/completion/failure/cancellation, saved experiment, clone, comparison, and export events.

Operational monitoring shall cover provider failures, stale data, calculation failures, frontend exceptions, API latency, chart-render failures, and AI grounding failures. Analytics must not capture raw portfolio values or assistant prompts unless the privacy policy explicitly permits it.

## 21. MVP Priorities

| Priority | Capability |
| --- | --- |
| P0 | Portfolio context, value, selected-period return, performance series, holdings list, data freshness, loading/error states, authorization. |
| P0 | Responsive shell, navigation, accessibility baseline, and consistent formatting. |
| P0 | Dedicated Portfolio Lab foundation: speculative portfolio builder, custom/equal/risk-based allocation, buy-and-hold/calendar/threshold/hybrid rebalancing, reproducible backtests, benchmark comparison, and required integrity controls. |
| P1 | Benchmark comparison, allocation, portfolio summary, movers, and cross-filtering. |
| P1 | Explainable health-score components; do not release an opaque overall score. |
| P1 | Grounded AI summary with as-of date and supporting links. |
| P1 | Advanced Portfolio Lab allocation methods, saved experiments, three-run comparison, exports, and AI-assisted explanation. |
| P2 | Advanced alerts, target allocation drift, rebalance candidates, watchlists, and richer assistant conversation. |

## 22. Acceptance Criteria

The dashboard is ready for MVP release when:

1. An authorized user can select a portfolio and view its value, return, allocation, holdings, and freshness status.
2. Performance values and chart points reconcile to tested backend calculations for every supported time range.
3. Benchmark comparison uses the same effective period and clearly identifies the benchmark.
4. Selecting an allocation segment filters the holdings view and can be reset.
5. The health score either explains every component and missing-data rule or remains component-only until that model is approved.
6. AI summaries identify their as-of date, remain within the selected portfolio context, and link material claims to supporting dashboard data.
7. Missing, stale, and partial data are distinguishable from valid zero values.
8. A failure in the AI or one analytical module does not prevent use of the rest of the dashboard.
9. The primary dashboard flow is usable by keyboard and passes the agreed automated and manual accessibility checks.
10. Layouts are verified at mobile, tablet, standard desktop, and wide desktop widths.
11. Financial numbers use consistent locale, currency, sign, and precision rules.
12. API access-control tests prove that a user cannot retrieve another user’s portfolio by changing an identifier.
13. Performance and error telemetry are available before production release.
14. The dedicated Portfolio Lab satisfies all acceptance criteria in Section 9.15 and remains clearly isolated from actual portfolio holdings and trading activity.

## 23. Recommended Delivery Sequence

### Phase 1 — Dashboard foundation

- Application shell, routes, design tokens, responsive grid, portfolio context, API client, formatting utilities, and reusable card/chart primitives.

### Phase 2 — Core portfolio visibility

- Performance hero, portfolio summary, holdings panel, data freshness, loading/empty/error states, and reconciliation tests.

### Phase 3 — Portfolio diagnostics

- Allocation, benchmark comparison, contribution, risk metrics, health-score components, and cross-filtering.

### Phase 4 — Speculative Portfolio Lab

- Hypothetical portfolio builder, versioned allocation strategies, rebalancing rules, bias-safe backtest engine, asynchronous runs, results visualizations, saved experiments, and strategy comparison.

### Phase 5 — Intelligence layer

- Alerts, grounded AI summaries, contextual questions, evidence links, audit metadata, and AI-specific safety tests.

### Phase 6 — Optimization workflows

- Target allocations, drift, rebalance candidates, scenarios, tax-aware capabilities, and approved action workflows.

## 24. Decisions Required Before Implementation

The following product decisions should be resolved before final UI implementation:

1. Which return method is the dashboard default: time-weighted, money-weighted, or a simpler value change?
2. Which default benchmark applies, and may each portfolio select its own benchmark?
3. Are multiple brokerage accounts consolidated into one portfolio view in the MVP?
4. Which health-score components have sufficient data and approved mathematical definitions?
5. What constitutes current, delayed, and stale data for each provider and asset type?
6. Which allocation dimensions are required in the first release?
7. Will the first release support only USD or multiple base currencies?
8. Does the assistant provide educational explanations only, or may it generate clearly labeled scenarios and recommendations?
9. Which notifications are informational versus actionable?
10. Is manual portfolio entry supported alongside provider imports?
11. Which allocation and rebalancing methods are mandatory for the first Portfolio Lab release beyond the minimum set in Section 9.15?
12. Which historical data source will support delisted securities, point-in-time classifications, market capitalization, dividends, and corporate actions?
13. What risk-free rate series and annualization convention will be used for risk-adjusted metrics?
14. Which transaction-cost, slippage, fractional-share, and tax assumptions are the defaults?
15. Must saved backtests remain exactly reproducible indefinitely, or may older runs become view-only when data/code retention expires?
16. What limits apply to assets per run, history length, concurrent jobs, and saved experiments?

## 25. Design Handoff Deliverables

Before frontend implementation, the design package should include:

- Desktop, tablet, and mobile dashboard frames.
- Component inventory and variants.
- Design-token definitions for color, type, spacing, radius, shadow, and motion.
- Performance, allocation, health, and sparkline chart specifications.
- Loading, empty, stale, partial, and error-state designs.
- Keyboard and focus behavior annotations.
- AI summary and assistant response states, including evidence presentation.
- Responsive behavior annotations.
- Sample data demonstrating positive, negative, mixed, missing, and stale scenarios.
- Approved metric definitions and copy glossary.
- Portfolio Lab builder, validation, running, failure, results, comparison, saved-experiment, and mobile states.
- Allocation-method and rebalancing-method parameter controls with plain-language rule previews.
- Backtest disclosures, assumption summary, bias/data-quality warnings, and reproducibility indicators.

---

This document defines the target dashboard experience. Detailed financial formulas, provider ingestion contracts, and AI evaluation procedures should remain in their respective normative technical specifications and be referenced by implementation stories rather than duplicated inconsistently in frontend code.
