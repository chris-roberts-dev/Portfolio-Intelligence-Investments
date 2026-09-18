# Portfolio Intelligence — Overview and Navigation Requirements

**Document status:** Draft for implementation  
**Scope:** Overview/landing page and primary desktop navigation  
**Future scope:** Detailed workflows for each domain will be defined separately  

## 1. Purpose

Redesign the authenticated Portfolio Intelligence landing page so a returning user can understand portfolio performance, risk, allocation, and recent changes within seconds. Move portfolio creation and maintenance out of the Overview and into the Portfolios domain.

The Overview should answer five questions:

1. What is my portfolio worth now?
2. How is it performing over useful time periods?
3. What is driving the result?
4. Is the portfolio taking more risk or drifting away from its target?
5. What needs my attention next?

## 2. Primary Navigation

Replace the icon-only rail with an expanded left sidebar containing an icon and visible text label for every destination.

| Order | Navigation item | Suggested icon | Primary responsibility |
| --- | --- | --- | --- |
| 1 | Overview | Layout dashboard | Cross-portfolio summary, performance, risk, allocation, insights, and alerts |
| 2 | Portfolios | Briefcase | Create, edit, archive, select, and manage portfolios and holdings |
| 3 | Market Data | Trending-up chart | Research securities, compare assets, review price/fundamental trends, and discover ideas |
| 4 | Allocation Lab | Sliders or flask | Research portfolio construction, allocation methods, efficient frontiers, scenarios, and rebalancing options |
| 5 | Activity and Transactions | Receipt or arrows-left-right | Review, import, add, edit, and reconcile ledger activity |
| 6 | Market Data & Watchlists | Star or eye | Monitor saved securities, watchlists, alerts, and recent market movement |
| 7 | Settings | Gear | Configure profile, base currency, benchmarks, data preferences, notifications, and other defaults |

### 2.1 Information-architecture note

The names **Market Data** and **Market Data & Watchlists** overlap. For the current implementation, keep both requested labels and distinguish them by purpose:

- **Market Data:** open-ended discovery and research.
- **Market Data & Watchlists:** saved monitoring and alerts.

During the domain-design phase, consider shortening the second label to **Watchlists** to reduce ambiguity.

### 2.2 Sidebar behavior

- Desktop expanded width: approximately 240–264 px.
- Display the Portfolio Intelligence mark/name at the top.
- Each item includes a consistent 20–24 px outline icon and text label.
- Use a filled or softly tinted active state with a visible left accent or high-contrast background.
- Maintain a minimum 44 px target height for each item.
- Keep Settings anchored near the bottom of the sidebar.
- Provide an optional collapse control. Collapsed mode may show icons with tooltips, but expanded mode is the default desktop experience.
- On tablet/mobile, convert the sidebar to a drawer without changing the domain structure.
- Support keyboard navigation, visible focus states, semantic navigation landmarks, and accessible labels.

## 3. Overview Page Structure

The page should use a dashboard hierarchy instead of a portfolio-creation form. Portfolio creation belongs in **Portfolios**.

### 3.1 Top application bar

Include:

- Portfolio selector with an **All Portfolios** option.
- “As of” market-data timestamp and freshness indicator.
- Global search or command entry point.
- Notifications.
- User/profile menu.

### 3.2 Page header

Include:

- Title: **Overview**.
- Short welcome or orientation line, such as “Here’s how your portfolio is performing.”
- Date-range control: 1M, 3M, YTD, 1Y, 3Y, 5Y, and Max.
- Primary action: **Add transaction**.
- Secondary action: **Manage portfolios**.

## 4. “Your Portfolio” KPI Summary

Display a row of concise metric cards. Use portfolio-level values when one portfolio is selected and aggregated values when **All Portfolios** is selected.

### 4.1 Core KPI cards

| Metric | Definition/display | Supporting context |
| --- | --- | --- |
| Total portfolio value | Current market value plus eligible cash balances | Absolute daily change and percentage daily change |
| YTD return | Time-weighted return from the start of the current calendar year through the as-of date | Benchmark return and active return for the same period |
| Portfolio-to-date return | Time-weighted return from portfolio inception through the as-of date | Inception date and benchmark comparison |
| Total gain/loss | Current value plus withdrawals minus contributions and beginning value, shown in base currency | Unrealized and realized portions where available |
| Net contributions | Contributions less withdrawals for the selected period | Prevents deposits from being mistaken for investment performance |
| Risk level | Volatility or a normalized risk score, with an understandable label | Change versus the prior comparable period |

### 4.2 Optional secondary metrics

Show these in a secondary row, detail drawer, or configurable KPI area rather than overcrowding the primary summary:

- Today’s return.
- Annualized return since inception when enough history exists.
- Benchmark-relative return.
- Income received YTD, including dividends and interest.
- Sharpe ratio.
- Maximum drawdown.
- Cash percentage.
- Number of holdings.
- Estimated fees, if supported by reliable source data.

### 4.3 Metric rules

- Every return metric must state or expose its calculation methodology: time-weighted return, money-weighted return, or another explicitly defined method.
- Use the portfolio’s configured base currency and show the currency code where ambiguity is possible.
- Do not color a metric solely red or green; pair color with a sign, icon, and/or descriptive text.
- Tooltips must define technical metrics and specify the date range.
- Null or incomplete data must produce an honest unavailable/partial state, not a synthetic zero.
- Benchmark comparisons must use the same date window and compatible return methodology.

## 5. Main Dashboard Modules

### 5.1 Portfolio performance

Primary visualization: cumulative return line chart.

- Plot portfolio return against the configured benchmark.
- Support the same date ranges as the page header.
- Allow value and return views if both are available.
- Mark cash-flow events without allowing them to distort investment return.
- Provide an accessible summary and underlying tabular values.

### 5.2 Allocation snapshot

- Show current allocation using a horizontal bar or donut chart.
- Default grouping: asset class.
- Allow future grouping by sector, geography, account, or currency.
- Show target allocation when configured.
- Surface the largest drift from target.
- Link to Allocation Lab for deeper analysis.

### 5.3 Performance contributors

Show the largest positive and negative contributors for the selected period.

- Security name and ticker.
- Contribution to portfolio return.
- Security return.
- Portfolio weight.
- Link to the security research view.

Contribution should be distinguished from security return; the ranking should reflect impact on the portfolio.

### 5.4 Portfolio health and risk

Present a concise health summary with up to four items:

- Concentration risk, such as the top holding or top-five weight.
- Diversification score or status.
- Cash level relative to target.
- Volatility, drawdown, or benchmark tracking risk.

Use neutral, explainable language. Avoid presenting a simplistic proprietary score without showing its drivers.

### 5.5 Insights and actions

Provide a ranked list of specific, explainable observations. Examples:

- “Technology is 8.2 percentage points above your target allocation.”
- “Three holdings represent 41% of portfolio value.”
- “$1,850 in cash has remained unallocated for 30 days.”
- “Your portfolio outperformed its benchmark by 1.8 percentage points YTD.”

Each insight should contain:

- The observed fact.
- Why it matters.
- The data date or period.
- A relevant next action or destination.

Insights are decision support, not individualized financial advice. Avoid imperative buy/sell language.

### 5.6 Recent activity

- Show the five most recent transactions or material ledger events.
- Include date, type, security/description, quantity when relevant, and amount.
- Provide a link to **Activity and Transactions**.

### 5.7 Watchlist pulse

- Summarize notable movement among saved securities.
- Show a small list of the largest daily movers or triggered alerts.
- Link to **Market Data & Watchlists**.

## 6. Recommended Desktop Layout

Use a 12-column content grid with a maximum readable width of approximately 1440 px inside the application shell.

1. Header and controls — full width.
2. Six KPI cards — one row on wide screens; two rows at narrower desktop widths.
3. Performance chart — eight columns; allocation snapshot — four columns.
4. Contributors — seven columns; portfolio health/insights — five columns.
5. Recent activity — seven columns; watchlist pulse — five columns.

Cards should use restrained borders, 12–16 px corner radii, subtle shadows, and generous whitespace. Reserve saturated blue for actions, focus, selection, and chart emphasis.

## 7. Visual Direction

- Preserve the current professional navy and blue identity.
- Use an off-white or very light cool-gray application background.
- Use dark navy for the expanded sidebar.
- Use white cards with subtle cool-gray borders.
- Use one strong blue as the primary action/accent color.
- Use teal/green and coral/red sparingly for positive and negative movement; always include non-color cues.
- Prefer clear financial-dashboard typography with tabular numerals for monetary and percentage values.
- Keep chart gridlines light and labels legible.
- Avoid excessive gradients, glass effects, gamification, and dense Bloomberg-terminal styling.

## 8. Responsive Behavior

- **Large desktop:** full sidebar, six KPI cards, two-column analytical modules.
- **Small desktop/tablet:** full or collapsible sidebar, three KPI cards per row, stacked lower modules as needed.
- **Mobile:** drawer navigation, two KPI cards per row or horizontal KPI scroll, single-column modules, sticky key actions only when they do not obstruct content.

## 9. Data and State Requirements

### 9.1 Required states

Design and implement:

- Loading/skeleton state.
- Empty account with no portfolios.
- Portfolio with no transactions.
- Partial market data.
- Stale market data.
- Calculation unavailable.
- Error with retry path.
- Single portfolio.
- Multiple portfolios and consolidated view.

### 9.2 Empty-state behavior

For a user with no portfolio, replace the dashboard with a focused onboarding state that explains the minimum setup and provides **Create portfolio** and, if supported, **Import holdings** actions. Do not show empty metric cards as zero.

### 9.3 Data provenance

- Show the effective market-data timestamp.
- Indicate delayed or stale prices.
- Provide calculation definitions for performance and risk metrics.
- Preserve the transaction ledger as the authoritative source for holdings and cash flows.

## 10. Accessibility and Usability Acceptance Criteria

- Sidebar labels are visible by default on desktop.
- Current destination is programmatically and visually identified.
- All controls and navigation are operable by keyboard.
- Focus indicators meet contrast requirements.
- Text and meaningful UI elements meet WCAG 2.2 AA contrast targets.
- Charts have text summaries and accessible data alternatives.
- Monetary values use locale-aware formatting and tabular numerals.
- Positive/negative meaning is not conveyed by color alone.
- Tooltips are accessible by keyboard and touch.
- Layout remains usable at 200% browser zoom.

## 11. Initial Overview Acceptance Criteria

The first implementation is complete when:

1. The expanded sidebar displays all requested domains with both icon and label.
2. The Overview no longer contains portfolio creation or editing controls.
3. A portfolio selector and date-range selector control the dashboard context.
4. The KPI summary includes, at minimum, total value, YTD return, portfolio-to-date return, total gain/loss, net contributions, and risk level.
5. Performance is compared with a defined benchmark over the same period.
6. Allocation, contributors, portfolio health/insights, recent activity, and watchlist pulse are represented.
7. All metrics display an as-of date and handle unavailable data honestly.
8. Empty, loading, stale-data, and error states are implemented.
9. Accessibility requirements in Section 10 are verified.
10. Navigation labels and routes are stable enough for future domain-specific design work.

## 12. Deferred Domain Work

The following are intentionally deferred:

- Detailed Portfolios management workflows.
- Security research and screening within Market Data.
- Allocation Lab methods, optimizers, scenarios, and constraints.
- Transaction import, reconciliation, and editing workflows.
- Watchlist construction and alert configuration.
- Complete Settings information architecture.
- Personalized AI narratives or recommendations beyond explainable descriptive insights.

