# SQL engine

Stock DuckDB 2.0.0 can load VGI from Query Farm's signed extension repository. It is the default engine for new quickstart projects. Preserve an existing application's engine choice.

```sh
uvx duckdb-cli==2.0.0
```

In DuckDB, configure the repository once on each machine or execution environment:

```sql
SET allow_extension_repositories = 'allowed';
CREATE EXTENSION REPOSITORY IF NOT EXISTS query_farm
    WITH PREFIX 'https://duckdb-extensions.query.farm';
INSTALL vgi FROM query_farm;
LOAD vgi FROM query_farm;

ATTACH 'demo' AS demo (TYPE vgi, LOCATION 'your worker command');
SELECT demo.main.your_function(21);
DETACH demo;
```

For later sessions, use `LOAD vgi FROM query_farm`. Plain `LOAD vgi` does not find an extension in a custom repository's installation directory. The opt-in setting is needed again when installing; the repository registration persists in normal interactive use.

The verifier uses `duckdb==2.0.0`, registers the repository in a temporary directory, and reports the actual engine, VGI extension version, and platform. It keeps signature verification enabled. Python is the test driver; the worker can use any supported language.

The recorded stock-DuckDB checks ran on macOS ARM64 with VGI extension `ddc96dc7a9`. Check build availability for a different version/platform and report installation failures accurately.

## Haybarn alternative

Haybarn 2.0.0rc11 is also tested. Keep it for an existing Haybarn project or when the developer selects it:

```sh
uvx haybarn-cli==2.0.0rc11
```

```sql
INSTALL vgi FROM community;
LOAD vgi;
```

Use `--engine haybarn` with the verifier and install `haybarn==2.0.0rc11` in its Python environment. Do not silently replace an application's engine when a selected build is unavailable.

Sources: [DuckDB extension repositories](https://duckdb.org/docs/2.0/extensions/extension_repositories), [Query Farm repository setup](https://query.farm/blog/duckdb-2-query-farm-repository/), and [Haybarn installation](https://query.farm/products/haybarn/install).
