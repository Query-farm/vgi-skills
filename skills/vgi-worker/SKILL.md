---
name: vgi-worker
description: Build or extend a VGI worker that exposes libraries, APIs, or datasets as SQL functions and catalogs. Verify the result through a real VGI-enabled SQL engine.
---

# Build a VGI worker

Deliver a working worker in the developer's chosen language, repeatable tests, and the exact SQL needed to attach and query it.

## Choose the language and scope

Use the language explicitly requested. For an existing worker, preserve its language and build system unless asked to migrate. For a new project with no language specified, ask the developer to choose **Python, TypeScript, Go, Rust, Java, or C#** before generating code. Do not silently choose Python. You can inspect the environment and clarify the desired SQL interface while awaiting that choice.

Read [languages.md](references/languages.md). For a new project, use the matching published [starter kit](references/starters.md), then follow its `AGENTS.md`, README, dependency locks, and closest example. The language references here are standalone SDK examples; use them when needed, and do not replace a starter's tested dependency versions with their older snapshots. Determine whether the capability is a scalar, table, table-in-out, aggregate, buffering function, or catalog; consult [function-shapes.md](references/function-shapes.md) if that decision is unclear. Keep the requested SQL names and semantics.

## Start from working scaffolding

For a new worker, initialize the chosen starter in a new project directory and run its baseline `make check` before adapting it. Preserve any existing agent instructions and installed skills; do not unpack a template over an occupied directory. Keep the work local unless the developer asked for a remote repository or deployment. A requested standalone script or a runtime constraint incompatible with the kit can use a compatible SDK approach instead.

For an existing worker, including one already marked by `.vgi-starter.json`, use its current layout and checks. Do not clone over it or run template initialization again. Keep the starter's metadata, unit tests, and SQL tests current as you change its functions. Follow its own instructions for lockfiles and generated files.

## Implement against an actual release

Read the project's dependency versions first. Use the installed SDK's signatures and the corresponding release examples. The current website and repository main can describe different SDK releases; do not mix their APIs. Preserve the starter's SDK constraints, patches, and lockfiles: a minor SDK change can change the wire protocol. Use `make template-diff` to review upstream changes rather than upgrading a worker's SDK blindly. Read [engine.md](references/engine.md) for the SQL engine setup.

Build the smallest worker that meets the request. Preserve existing repository conventions. Include typed parameters, useful catalog/function descriptions, explicit null behavior, and a repeatable launch command. Workers process Arrow batches; avoid serializing a whole relation into row-by-row RPC calls.

Concrete pitfalls:

- The Python distribution is `vgi-python`; its import is `vgi`. `vgi-rpc` is the transport underneath it.
- Stdio carries Arrow protocol bytes. Send diagnostics to stderr, never print banners to stdout.
- Match the advertised output schema, including integer width and nullability. Test empty input and more than one batch when applicable.
- Register functions in the actual catalog/schema used by the SQL test. Inspect the current API for schema paths; older examples use different parameter names.
- Rebuild and restart the worker before testing changed code. Prefer a direct subprocess during development to avoid stale pooled processes.
- Test API-backed workers with local fixtures; a live API check is useful separately. Respect the requested authentication and data access boundaries.

## Close the loop through SQL

Use [testing.md](references/testing.md). Exercise business logic, worker transport, and SQL binding as applicable. A compiled worker or passing unit test alone does not establish SQL compatibility.

For a starter-based worker, run its required `make check`, including metadata and SQL checks; keep its existing suite as the source of truth. Check which engine that suite actually runs. The current starters use Haybarn's SQLLogicTest runner, so also verify through stock DuckDB with VGI from `query_farm` when stock DuckDB is requested. Never label a Haybarn-only run as stock-DuckDB verification.

When no equivalent suite covers the requested engine and behavior, create a `vgi-worker.json` with the real launch arguments, catalog, and representative assertions, and run the bundled verifier from the project directory:

```sh
uv run --with duckdb==2.0.0 python /absolute/path/to/vgi-worker/scripts/verify_worker.py --project .
```

Resolve `/absolute/path/to/vgi-worker` from this skill's location. Fix failures caused by your implementation and rerun affected checks. Keep a failing baseline separate from a regression you introduced. Report a dependency or engine failure precisely; never weaken the starter's checks or substitute an SDK-only check and call SQL verification passed.

The local tests use disposable fixtures. Run and repair them within the requested task without pausing for approval after every check. Hosting, account creation, paid resources, and publication are separate actions governed by the user's instructions.

## Handoff

Return the worker/project paths, chosen language, starter source/revision when used, resolved SDK version, actual test engines, commands run, their results, and the tested `ATTACH`/`SELECT` statements. Include unresolved failures explicitly. Distinguish measured elapsed time from an estimate. Do not claim a five-minute result without a recorded run.
