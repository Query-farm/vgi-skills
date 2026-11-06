# Which orders lose money after shipping?

A runnable VGI example that brings a shipping library into a DuckDB query. The rates and five orders are fictional. Money is stored as integer USD cents. This is a worked example, not a timed autonomous-agent benchmark or a real carrier quotation service.

The story starts with one quote. But the useful question is about all the orders, so the worker accepts destination and weight columns. DuckDB combines the returned prices with the order table and finds negative margins. An unsupported destination returns NULL and stays in the review queue.

## Run it

Requires Node 22.15+ and uv. From this directory:

```sh
npm ci
npm test
npm run typecheck
npm run verify:sql
```

The verifier installs VGI from Query Farm's signed repository in stock DuckDB 2.0.0, starts the actual worker, and checks seven SQL assertions. The tests include the displayed report, missing rates, NULL inputs, empty input, and 10,000 rows. Fifteen unit cases cover the shipping rule's boundaries.

## Use it from SQL

Open `uvx duckdb-cli==2.0.0` in this directory:

```sql
SET allow_extension_repositories = 'allowed';
CREATE EXTENSION REPOSITORY IF NOT EXISTS query_farm
  WITH PREFIX 'https://duckdb-extensions.query.farm';
INSTALL vgi FROM query_farm;
LOAD vgi FROM query_farm;
ATTACH 'shipping' AS shipping
  (TYPE vgi, LOCATION 'node --import tsx worker.ts');

SELECT shipping.main.quote_cents('US', 500::BIGINT); -- 550
```

Load `orders.sql` in the CLI with `.read orders.sql`. The `orders needing attention` assertion in `vgi-worker.json` is the complete report query. It returns A-103 (−$2.50), A-102 (−$2.00), and A-105 (missing quote, needs review).

## Replace the sample rule

`src/rates.ts` is the boundary to replace with your organization's shipping library or an API client. Keep business rules out of duplicate SQL implementations when that existing library is their source of truth. A real service needs its actual pricing semantics, credentials, request limits, error handling, and fixture tests. Currency conversions and taxes are outside this sample.

The TypeScript implementation is one concrete example. The same VGI contract can be implemented in Python, Go, Rust, Java, or C# using that language's SDK. The quickstart lets the developer choose.
