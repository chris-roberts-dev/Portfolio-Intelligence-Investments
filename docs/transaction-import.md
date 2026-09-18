# Transaction CSV Import Format

**Status:** Phase 4 MVP contract  
**Authority:** `docs/dev-guide.md` Sections 3.2, 8.2, 8.6-8.7, 9.2, and 10.1-10.3

The transaction ledger is authoritative for portfolio holdings. CSV import does not create or update a holdings table and does not perform financial calculations in the browser.

## File requirements

- UTF-8 CSV text only.
- Maximum file size: 262,144 bytes.
- Maximum transaction rows: 500 nonblank rows.
- The preferred end-user format uses ticker symbols and must exactly match:

```text
transaction_type,occurred_at,asset_symbol,quantity,price,fees,cash_amount
```

- The original canonical-ID format remains accepted for API/backward compatibility:

```text
transaction_type,occurred_at,asset_id,quantity,price,fees,cash_amount
```

Blank fields are represented by an empty CSV field. Additional columns are not accepted.

`occurred_at` must be an ISO-8601 datetime including a timezone offset, for example:

```text
2026-09-15T14:30:00-05:00
2026-09-15T19:30:00Z
```

For the preferred format, `asset_symbol` is a user-entered ticker such as `AAPL` or `VTI`. Symbols are normalized and resolved through the configured canonical asset-discovery boundary before transaction validation. A resolved ticker is always converted to the internal canonical `asset_id` before it is used by the ledger. An unresolved or unsupported ticker produces a row-level `ASSET_NOT_FOUND` issue; it is never silently substituted with another security.

The legacy `asset_id` column is the canonical internal asset UUID and remains useful for machine-generated files. End users do not need to know or manually enter canonical UUIDs when using `asset_symbol`.

Resolving a supported ticker during preview may add or refresh that security in the canonical asset catalog. Preview still does **not** persist transaction rows. Transaction confirmation remains the only operation that commits the CSV ledger rows.

## Supported transaction rows

### DEPOSIT

Required:

```text
transaction_type = DEPOSIT
cash_amount > 0
```

Must be blank:

```text
asset_symbol / asset_id
quantity
price
```

Example using the preferred ticker format:

```csv
transaction_type,occurred_at,asset_symbol,quantity,price,fees,cash_amount
DEPOSIT,2026-09-01T09:00:00-05:00,,,,0,10000.00
```

### WITHDRAWAL

Required:

```text
transaction_type = WITHDRAWAL
cash_amount > 0
```

Must be blank:

```text
asset_symbol / asset_id
quantity
price
```

### BUY

Required:

```text
asset_symbol (preferred) or asset_id (legacy)
quantity > 0
price > 0
fees >= 0
```

`cash_amount` must be blank. Cash is derived by the canonical ledger as:

```text
-(quantity × price + fees)
```

Example:

```csv
transaction_type,occurred_at,asset_symbol,quantity,price,fees,cash_amount
BUY,2026-09-02T10:15:00-05:00,AAPL,10,230.50,1.00,
```

### SELL

Required:

```text
asset_symbol (preferred) or asset_id (legacy)
quantity > 0
price > 0
fees >= 0
```

`cash_amount` must be blank. Cash is derived by the canonical ledger as:

```text
quantity × price - fees
```

The MVP is long-only. A row that would make a security position negative is invalid.

### DIVIDEND

Required:

```text
asset_symbol (preferred) or asset_id (legacy)
cash_amount > 0
```

`quantity` and `price` may be blank. When supplied they must be positive source metadata. Dividends are internal portfolio cash flows, not external contributions.

## Preview, ticker resolution, and atomic confirmation

Import is a two-step transaction workflow:

1. **Preview** parses the file. For the preferred `asset_symbol` format it resolves supported tickers to canonical asset IDs, then normalizes, validates, and replays candidate rows without committing transaction rows.
2. **Confirm** re-resolves ticker symbols when present, re-parses, revalidates, and commits only if every row is valid at confirmation time.

Confirmation is atomic for the transaction rows. If any row fails field validation, canonical asset resolution, database constraints, or long-only ledger replay, the complete transaction import is rolled back.

Preview does not reserve ledger ordering or guarantee that later confirmation will succeed. Confirmation is authoritative because another transaction or an asset-catalog change may occur between preview and confirmation.

The application does not claim global CSV idempotency in Phase 4. The frontend prevents accidental repeated confirmation within the same active browser interaction, but importing the same valid file again later may create additional transactions.

## Stable ordering

The database ledger is ordered by:

```text
occurred_at
source_sequence
transaction_id
```

The import service assigns `source_sequence` server-side. For rows with the same `occurred_at`, CSV row order is preserved after existing ledger entries at that timestamp.
