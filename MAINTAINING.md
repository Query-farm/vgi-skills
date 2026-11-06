# Maintaining the skills

## Design choices

One portable skill format supports several agents. Each skill is independently installable: the testing helper and essential references are copied into vgi-test by a checked sync script. Native plugin metadata is a thin distribution layer over the same folders.

Keep the entrypoints short. They describe the outcome, preserve the developer's language choice, and route to one language reference. Release-specific SDK pitfalls belong in those references. Deterministic verification and packaging belong in scripts so each agent does not need to reinvent them.

The first milestone is a real query returning the expected rows. Source compilation, unit tests, and transport tests are useful but cannot replace an engine integration test. The agent reports actual commands, versions, and failures. New projects ask for a language; existing projects retain their conventions.

The packaged example is a worker, not a new native DuckDB extension binary. Stock DuckDB 2.0.0 and Haybarn 2.0.0rc11 are both supported by the verifier. Check the selected engine’s VGI build for the relevant version and platform. Stock DuckDB uses the signed query_farm repository; Haybarn uses community.

## Release checks

1. Check each SDK's published version and runtime requirements. Update only the affected language reference; do not copy repository-main APIs into a pinned-release recipe.
2. Run the fixture SQL checks and helper tests. Use `scripts/sync_shared.py`, `scripts/validate.py`, and the native plugin validator.
3. For behavior changes, run fresh native agent evaluations with independent assertions. Include the relevant language and a no-skill baseline when evaluating whether guidance helps. Preserve failures and harness exclusions in the report.
4. Recheck portable installation in a disposable project. Keep install compatibility separate from live-agent execution results.
5. Review the sanitized results, release notes, skill metadata, and website evidence together. Never publish raw agent event logs or account-specific paths.

The website imports reviewed results with `scripts/sync-vgi-agent-evidence.mjs` in query-farm-astro. Updating the skills does not silently rewrite marketing claims. Remeasure any timing claim after a material toolchain or workflow change.

## Reference practices

- [Agent Skills specification](https://agentskills.io/specification): portable SKILL.md metadata and supporting resources.
- [Agent Skills authoring guidance](https://agentskills.io/skill-creation/best-practices): focused instructions and progressive disclosure.
- [Codex skills](https://developers.openai.com/codex/skills/): discovery, explicit invocation, and optional UI metadata.
- [Claude Code skills](https://code.claude.com/docs/en/skills): portable skill folders, invocation, and supporting files.
- [Claude Code plugins](https://code.claude.com/docs/en/plugins): distribution without duplicating the skill's implementation.
- [Skills CLI](https://github.com/vercel-labs/skills): project installation for multiple coding agents.

The evaluation harness is an exploratory development tool. It uses the locally configured models and shared caches; it is not a controlled model benchmark. Current recorded coverage and limitations are in [evals/RESULTS.md](evals/RESULTS.md).
