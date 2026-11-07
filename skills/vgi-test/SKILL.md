---
name: vgi-test
description: Test or diagnose an existing VGI worker through a real SQL engine, reproduce protocol and binding failures, and repair worker defects.
---

# Test an existing VGI worker

Preserve the developer's worker language and build system. Inspect its launch command, SDK version, SQL surface and current tests. If the task is a new worker with no language selected, ask the developer which language to use.

For a starter-based project (`.vgi-starter.json`), read its `AGENTS.md` and use its existing `make check`, metadata checks, and SQLLogicTest files. Do not reinitialize the template or replace its suite with a second test framework. Identify the engine actually used: current starter suites run through Haybarn; a stock DuckDB requirement also needs verification through DuckDB with VGI from `query_farm`. The bundled verifier can supply that additional check.

Use [testing.md](references/testing.md) for the verification manifest and [engine.md](references/engine.md) for engine selection. This skill includes its own verifier and can be installed independently.

1. Reproduce the reported behavior with the existing test command or a minimal SQL assertion. Build and restart the actual worker first.
2. Identify the failing layer: runtime/dependency setup, worker startup, Arrow framing/schema, registration/binding, business logic, or a remote dependency. Keep stdout reserved for the stdio protocol; inspect stderr for diagnostics.
3. Add a regression assertion for the requested behavior. Use deterministic fixtures. Include null/empty/multi-batch cases when relevant to the failure.
4. Repair the cause within the requested scope and rerun the affected checks through the engine. A direct SDK client test is useful but does not replace SQL binding verification.
5. Return commands, exact tested versions, assertion results and any remaining blocker. Do not report a mocked query as a real SQL success.

```sh
uv run --with duckdb==2.0.0 python /absolute/path/to/vgi-test/scripts/verify_worker.py --project . --output verification.json
```

Do not change an expected result merely to make a failing test pass. Avoid killing unrelated worker processes; use the current test's owned process or an SDK-supported shutdown command.
