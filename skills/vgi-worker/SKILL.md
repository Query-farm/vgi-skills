---
name: vgi-worker
description: Build or extend a VGI worker that exposes libraries, APIs, or datasets as SQL functions and catalogs. Verify the result through a real VGI-enabled SQL engine.
---

# Build a VGI worker

Deliver a working worker in the developer's chosen language, repeatable tests, and the exact SQL needed to attach and query it.

## Choose the language and scope

Use the language explicitly requested. For an existing worker, preserve its language and build system unless asked to migrate. For a new project with no language specified, ask the developer to choose **Python, TypeScript, Go, Rust, Java, or C#** before generating code. Do not silently choose Python. You can inspect the environment and clarify the desired SQL interface while awaiting that choice.

Read [languages.md](references/languages.md), then only the chosen language's reference. Determine whether the capability is a scalar, table, table-in-out, aggregate, buffering function, or catalog; consult [function-shapes.md](references/function-shapes.md) if that decision is unclear. Keep the requested SQL names and semantics.

## Implement against an actual release

Read the project's dependency versions first. Use the installed SDK's signatures and the corresponding release examples. The current website and repository main can describe different SDK releases; do not mix their APIs. Start with published packages and pin the version resolved for a new project. Read [engine.md](references/engine.md) for the SQL engine setup.

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

Create a `vgi-worker.json` verification manifest with the real launch arguments, catalog, and representative SQL assertions. Run the bundled verifier from the project directory:

```sh
uv run --with duckdb==2.0.0 python /absolute/path/to/vgi-worker/scripts/verify_worker.py --project .
```

Resolve `/absolute/path/to/vgi-worker` from this skill's location. An existing project may use its own equivalent SQLLogicTest or integration suite instead. Fix failures caused by your implementation and rerun affected checks. Report a dependency or engine failure precisely; never substitute an SDK-only check and call SQL verification passed.

The local tests use disposable fixtures. Run and repair them within the requested task without pausing for approval after every check. Hosting, account creation, paid resources, and publication are separate actions governed by the user's instructions.

## Handoff

Return the worker/project paths, chosen language and pinned SDK version, engine version, commands actually run, their results, and the tested `ATTACH`/`SELECT` statements. Include unresolved failures explicitly. Distinguish measured elapsed time from an estimate. Do not claim a five-minute result without a recorded run.
