"""Centralized normative configuration for the quantitative engine.

Development guide reference: Section 27.

Only constants required by implemented phases belong here. Additional normative
constants are added when their corresponding functionality is implemented.
"""

MAX_BAR_QUERY_SYMBOLS = 50
MAX_BAR_QUERY_CALENDAR_DAYS = 7305
MAX_BAR_QUERY_ROWS = 500_000

MAX_MISSING_EXPECTED_OBSERVATION_RATIO = 0.10

MARKET_DATA_TIMEOUT_SECONDS = 30

MARKET_DATA_MAX_ATTEMPTS = 3
MARKET_DATA_RETRY_BASE_DELAY_SECONDS = 0.5
MARKET_DATA_RETRY_MAX_DELAY_SECONDS = 8.0
MARKET_DATA_RETRY_JITTER_RATIO = 0.25
