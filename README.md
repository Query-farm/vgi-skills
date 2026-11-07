# VGI skills

Build, test, and package [VGI workers](https://query.farm/vgi/) with your coding agent. Choose **Python, TypeScript, Go, Rust, Java, or C#**. Get a real worker, repeatable SQL tests, and the exact `ATTACH` statement.

This repository is the portable source for three independently installable skills:

| Skill | Use it to |
| --- | --- |
| `vgi-worker` | Create or extend a worker, run it, verify SQL results, and repair implementation failures |
| `vgi-test` | Diagnose and test an existing worker through a real SQL engine |
| `vgi-package` | Prepare a local distribution artifact, integrity manifest, and runtime instructions |

For a new project, the builder asks which language you want if you have not already chosen one. Existing projects keep their language and tooling.

## Installation

Use the portable [skills CLI](https://github.com/vercel-labs/skills) from your project directory:

```sh
npx skills add Query-farm/vgi-skills --skill vgi-worker
```

Select your coding agent when prompted, or pass `--agent codex`, `--agent claude-code`, `--agent cursor`, `--agent github-copilot`, or `--agent opencode`. Install all three skills by omitting `--skill`. Pin a release or commit using `Query-farm/vgi-skills@<ref>`.

During pre-release review, use `Query-farm/vgi-skills@feat/initial-agent-skills`. The draft repository is private until its owner approves publication; use authenticated GitHub access or install from a local checkout.

### Manual installation

Copy a complete folder from `skills/` into your project's skill directory. Each folder includes all of its runtime references and helpers.

| Agent | Project directory |
| --- | --- |
| Codex | `.agents/skills/` |
| Claude Code | `.claude/skills/` |
| Cursor | `.cursor/skills/` |
| GitHub Copilot | `.github/skills/` |
| OpenCode | `.opencode/skills/` |

Use `$vgi-worker` in Codex, `/vgi-worker` in Claude Code, or ask your agent to use the `vgi-worker` skill. Restart/reload the agent if it does not discover a new skill. Cloud agents need the skill and toolchain inside their execution environment; a personal desktop install does not automatically travel with them.

### Native plugins

The same skills are packaged for Codex and Claude Code. After publication:

```sh
codex plugin marketplace add Query-farm/vgi-skills
codex plugin add vgi@query-farm
```

In Claude Code:

```text
/plugin marketplace add Query-farm/vgi-skills
/plugin install vgi@query-farm
```

Claude plugin skills are namespaced: `/vgi:vgi-worker`, `/vgi:vgi-test`, and `/vgi:vgi-package`. For a local pre-release check use `claude --plugin-dir /path/to/vgi-skills`.

## Start a worker

Choose your language and describe the SQL capability:

```text
Use the vgi-worker skill. Build a TypeScript VGI worker that exposes
demo.main.slugify(VARCHAR). Normalize accented Latin text, lowercase it,
replace punctuation and spaces with hyphens, and preserve SQL NULL.
Run it locally through stock DuckDB and leave repeatable tests and the exact
ATTACH and SELECT statements. Do not deploy it.
```

Substitute any supported language. The [website quickstart](https://query.farm/vgi/build-with-an-agent/) has installation help and copyable requests for APIs, local data, and existing libraries. Name your language in the request, or let the agent ask before it writes code.

## Verification

The shared verifier consumes a project-local `vgi-worker.json`, starts the worker through the actual VGI extension, and checks expected SQL results:

```sh
uv run --with duckdb==2.0.0 python \
  skills/vgi-worker/scripts/verify_worker.py \
  --project examples/python-double --output verification.json
```

The helper uses Python as a test driver; your worker can use any supported language. See [the manifest contract](skills/vgi-worker/references/testing.md). A compile/import check does not replace SQL verification.

Stock DuckDB 2.0.0 is the default tested engine, using `INSTALL vgi FROM query_farm` and `LOAD vgi FROM query_farm`. See [engine setup](skills/vgi-worker/references/engine.md) for repository registration. Haybarn remains supported with `--engine haybarn` and `haybarn==2.0.0rc11`. Never silently replace an existing project’s engine.

## Examples and compatibility

- [Shipping margins: one function to an actionable SQL report](examples/shipping-margin/) — fictional orders/rates with verified results

- [Python scalar fixture](examples/python-double/)
- [TypeScript scalar fixture](examples/typescript-double/) — run `npm ci` first
- [Agent-built TypeScript worker on stock DuckDB](examples/agent-duckdb-typescript-slugify/) — the recorded demo’s source and tests
- [Original Haybarn TypeScript example](examples/agent-typescript-slugify/) — also reverified on stock DuckDB
- [SDK versions and language references](skills/vgi-worker/references/languages.md)
- [SDK compatibility evidence on Haybarn](evals/compatibility.json)
- [Stock DuckDB checks of generated workers](evals/stock-duckdb.json)
- [Agent evaluation results](evals/RESULTS.md)

SDK compatibility checks and agent evaluations are different measurements. Do not generalize a single successful run into a universal five-minute guarantee.

## Development

```sh
uv run --with duckdb==2.0.0 python -m unittest discover -s tests -v
python3 scripts/validate.py
claude plugin validate . --strict
```

`vgi-test` ships its own verifier and references so it works when installed alone. After editing the canonical copies under `vgi-worker`, run `python3 scripts/sync_shared.py`; validation checks they match.

To evaluate a skill with an installed, authenticated coding agent:

```sh
python3 scripts/evaluate.py --agent codex --case python-build
python3 scripts/evaluate.py --agent claude --case typescript-build
python3 scripts/evaluate.py --agent claude --case shipping-report
python3 scripts/evaluate.py --agent claude --case typescript-build --without-skill
```

These commands invoke real agent sessions and consume normal account usage. They create disposable projects under `.eval-runs/`, retain prompts/logs/results, impose a deadline, and independently verify generated workers. The harness uses the agent's configured/default model; it does not select a model. Additional cases cover language choice, repair, and packaging. Keep raw account-specific logs out of published results.

### Recorded integration build

[GitHub releases + local inventory](examples/agent-github-releases/) was generated by Codex in a filmed interactive session. It includes the API worker, paginated HTTP fixtures, SQL tests, a live-query runner, and the captured result. The fictional inventory is labeled; live API calls are separate from deterministic CI.
