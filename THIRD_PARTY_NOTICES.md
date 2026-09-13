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
