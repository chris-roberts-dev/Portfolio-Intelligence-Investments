# Transaction CSV Import Format

**Status:** Phase 4 MVP contract  
**Authority:** `docs/dev-guide.md` Sections 3.2, 8.6-8.7, 10.1-10.3

The transaction ledger is authoritative for portfolio holdings. CSV import does not create or update a holdings table and does not perform financial calculations in the browser.

## File requirements

- UTF-8 CSV text only.
- Maximum file size: 262,144 bytes.
- Maximum transaction rows: 500 nonblank rows.
- Header must exactly match:

```text
transaction_type,occurred_at,asset_id,quantity,price,fees,cash_amount
```

Blank fields are represented by an empty CSV field. Additional columns are not accepted.

`occurred_at` must be an ISO-8601 datetime including a timezone offset, for example:

```text
2026-09-15T14:30:00-05:00
2026-09-15T19:30:00Z
```

`asset_id` is the canonical internal asset UUID. The importer does not treat a ticker symbol as proof of asset identity and does not silently substitute an unresolved security.

## Supported transaction rows

### DEPOSIT

Required:

```text
transaction_type = DEPOSIT
cash_amount > 0
```

Must be blank:

```text
asset_id
quantity
price
```

Example:

```csv
transaction_type,occurred_at,asset_id,quantity,price,fees,cash_amount
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
asset_id
quantity
price
```

### BUY

Required:

```text
asset_id
quantity > 0
price > 0
fees >= 0
```

`cash_amount` must be blank. Cash is derived by the canonical ledger as:

```text
-(quantity × price + fees)
```

### SELL

Required:

```text
asset_id
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
asset_id
cash_amount > 0
```

`quantity` and `price` may be blank. When supplied they must be positive source metadata. Dividends are internal portfolio cash flows, not external contributions.

## Preview and atomic confirmation

Import is a two-step workflow:

1. **Preview** parses, normalizes, validates, and replays candidate rows without committing them.
2. **Confirm** re-parses and revalidates the original CSV text and commits only if every row is valid at confirmation time.

Confirmation is atomic. If any row fails field validation, canonical asset resolution, database constraints, or long-only ledger replay, the entire import is rolled back.

Preview does not reserve ledger ordering or guarantee that later confirmation will succeed. Confirmation is authoritative because another transaction may be written between preview and confirmation.

The application does not claim global CSV idempotency in Phase 4. The frontend prevents accidental repeated confirmation within the same active browser interaction, but importing the same valid file again later may create additional transactions.

## Stable ordering

The database ledger is ordered by:

```text
occurred_at
source_sequence
transaction_id
```

The import service assigns `source_sequence` server-side. For rows with the same `occurred_at`, CSV row order is preserved after existing ledger entries at that timestamp.
