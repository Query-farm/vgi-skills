# Choose the SQL surface

| Need | Shape | Essential verification |
| --- | --- | --- |
| A value for each input row | Scalar | Values, null policy, output length and Arrow type |
| Rows generated from arguments, an API, or a dataset | Table | Schema, empty result, pagination and multi-batch output |
| Transform incoming rows as batches arrive | Table-in-out | All batches consumed, row count/ordering contract |
| One result per SQL group | Aggregate | Empty groups, update/combine/finalize, grouped SQL |
| See the full relation before producing rows | Buffering | State across batches and parallel producers |
| Discoverable tables, views, and functions | Catalog | information_schema discovery, schema-qualified queries |

Use a library-backed scalar/table function for a small first worker. Wrapping a file already readable by DuckDB is useful only when the worker adds requested behavior such as an API, policy, transformation, or domain library.

Follow the SDK's ownership and lifecycle rules. In Java/C#/Rust/Go, copying references to reused Arrow buffers can corrupt later batches. Keep per-invocation state in the SDK's supported state/storage facilities.

Source: https://query.farm/vgi/building-a-worker
