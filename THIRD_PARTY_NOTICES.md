# Third-Party Notices

Portfolio Intelligence uses third-party open-source software. This notice records
direct dependencies whose addition is materially relevant to the project's
implementation or external-data boundary.

## yfinance

- Package: `yfinance`
- Project license: Apache License 2.0
- Purpose in Portfolio Intelligence: optional market-data provider adapter for
  historical daily market bars
- Portfolio Intelligence version constraint: `1.7.0`

yfinance is an independent open-source project and is not affiliated with,
endorsed by, or vetted by Yahoo.

Market data accessed through yfinance originates from Yahoo services and may be
subject to separate provider terms and usage restrictions. Deployers of
Portfolio Intelligence are responsible for reviewing the applicable upstream
terms before using that data in production or commercial workflows.

This project keeps yfinance-specific behavior behind the
`MarketDataProvider` adapter boundary. The quantitative engine does not import
or depend on yfinance.

## Systematic Investor Toolbox (SIT)

Portions of the portfolio mathematics and algorithm structure in this package are adapted from the supplied **Systematic Investor Toolbox (SIT)** R source by Systematic Investor. This Python package is an **altered/adapted implementation**, not the original SIT source and not a claim of authorship over the original work.

Original notice from the supplied source:

> This software is provided 'as-is', without any express or implied warranty. In no event will the authors be held liable for any damages arising from the use of this software.
>
> Permission is granted to anyone to use this software for any purpose, including commercial applications, and to alter it and redistribute it freely, subject to the following restrictions:
>
> 1. The origin of this software must not be misrepresented; you must not claim that you wrote the original software. If you use this software in a product, an acknowledgment in the product documentation would be appreciated but is not required.
> 2. Altered source versions must be plainly marked as such, and must not be misrepresented as being the original software.
> 3. This notice may not be removed or altered from any source distribution.

Source project references in the supplied file include `SystematicInvestor.wordpress.com` and `systematicinvestor.github.io`.

## Playwright

The Phase 4 end-to-end test runner uses Microsoft Playwright and
`@playwright/test` 1.49.1 under the Apache License 2.0. The dependency is pinned
in the self-contained `frontend/e2e/package-lock.json`; no Playwright source is
vendored into this repository.

## Apache ECharts

The frontend visualization layer uses Apache ECharts 6.1.0 under the Apache License
2.0. ECharts is installed as an npm dependency and no ECharts source is vendored
into this repository. ECharts depends on zrender 6.1.0 (BSD-3-Clause) and tslib
2.3.0 (0BSD), which are recorded transitively in `frontend/package-lock.json`.
