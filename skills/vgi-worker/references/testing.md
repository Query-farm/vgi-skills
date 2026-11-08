# Verify a worker

The verification manifest is a portable contract used by the bundled `scripts/verify_worker.py`. Paths are relative to the manifest's project directory. The worker command is an argv array, not a shell script.

```json
{
  "schema_version": 1,
  "catalog": "demo",
  "worker": ["uv", "run", "worker.py"],
  "checks": [
    {
      "name": "known values",
      "sql": "SELECT demo.main.double(21) AS doubled",
      "columns": ["doubled"],
      "rows": [[42]]
    },
    {
      "name": "multiple batches",
      "sql": "SELECT count(*), sum(demo.main.double(i)) FROM range(5000) t(i)",
      "rows": [[5000, 24995000]]
    }
  ]
}
```

### ATTACH options and credentials

A worker that declares ATTACH options (an API token, an endpoint URL) gets them from an optional `attach_options` object. A value is either a literal (string, number or boolean) or `{"env": "VARIABLE"}`, read from the environment when the verifier runs:

```json
{
  "schema_version": 1,
  "catalog": "slack",
  "worker": ["bin/vgi-slack-worker"],
  "attach_options": {
    "token": {"env": "SLACK_TEST_TOKEN"},
    "api_url": "http://127.0.0.1:8765"
  },
  "checks": [{"sql": "SELECT team FROM slack.main.auth_info()", "rows": [["Mock Team"]]}]
}
```

Put every credential behind `env`, never in the manifest. Environment values are treated as secrets: the report's `attach_sql` shows `<redacted>`, and the value is scrubbed from every error, row and stderr line the verifier prints. A missing variable fails before the engine starts and names the variable. `TYPE` and `LOCATION` are set by the verifier and cannot be overridden. The verifier does not start helper processes: start a mock API yourself on a fixed port before running it.

`columns` is optional; omit unstable engine-generated expression labels. Every check requires expected `rows`. Use `ORDER BY` when row order matters. Use explicit casts for SQL types and compare representative values, not just row counts. JSON numbers, strings, booleans, arrays, and nulls are supported; dates/timestamps/decimals are normalized to strings.

Run with a pinned released engine:

```sh
uv run --with duckdb==2.0.0 python /path/to/skill/scripts/verify_worker.py --project . --timeout 120 --output verification.json
```

The default engine is stock DuckDB 2.0.0 with VGI from `query_farm`. To preserve a Haybarn project, use `uv run --with haybarn==2.0.0rc11 python /path/to/skill/scripts/verify_worker.py --engine haybarn --project .`. See [engine.md](engine.md) for the complete installation SQL.

The verifier emits JSON and returns a nonzero exit code on any failed assertion, malformed manifest, engine error, or timeout. Its SQL test covers the real extension, subprocess protocol, registration and binding. Add SDK/unit tests for business logic where SQL examples alone cannot cover it.

For an existing SQLLogicTest suite, use `uvx haybarn-unittest==2.0.0rc11 test/sql/worker.test` from its prepared project directory. Preserve working test conventions.

For API workers, keep fixtures deterministic and separate optional live checks. Verify request parameters, pagination termination, missing fields, upstream errors, and credentials through environment variables or the SDK's secrets mechanisms. Never embed live credentials in test artifacts.

For release verification, run the packaged artifact from an extracted temporary directory so development-only files and editable dependencies cannot mask missing files.
