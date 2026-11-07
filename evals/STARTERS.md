# Starter-kit integration results

Recorded November 7, 2026, on macOS ARM64. **All six published kits passed initialization and `make check`; all six also passed eight independent stock-DuckDB checks.** Two fresh coding-agent builds selected and adapted the correct starter, preserved its checks, and passed independent verification.

## Published-kit checks

Each kit was cloned from its public repository into a disposable directory, its source commit recorded, its upstream remote removed, and `make init NAME=skills_<language>` run before `make check`. No worker-source fixes were applied to make these baselines pass.

| Kit | Published commit | Resolved SDK | `make check` | Stock DuckDB |
| --- | --- | --- | --- | --- |
| Python | `aa4ee91` | vgi-python 0.49.1 | passed | 8/8 |
| TypeScript | `c0e40b6` | @query-farm/vgi 0.48.1 | passed | 8/8 |
| Go | `02c15e1` | vgi-go 0.40.1 | passed | 8/8 |
| Rust | `ff1587c` | vgi 0.49.3 | passed | 8/8 |
| Java | `659b4d4` | farm.query:vgi 0.46.1 | passed with JDK 27 | 8/8 |
| C# | `206fcdc` | QueryFarm.Vgi 0.24.0 | passed | 8/8 |

The initial Java check failed because the default JDK was 21 and the kit targets release 25. Selecting the already-installed JDK 27 for that command resolved it. The template source and global Java configuration were unchanged. The skill now distinguishes the SDK's runtime compatibility from the kit's build requirement.

`make check` ran each initialized kit's static and unit checks, SQL tests over stdio/launch/HTTP, and metadata validation. The kits use **Haybarn 2.0.0rc11** for SQLLogicTest; those results are not presented as stock-DuckDB tests. Metadata checks reached L2, not optional AI assurance L3.

The independent stock check used **DuckDB 2.0.0**, signed Query Farm VGI `b744d094ed`, and the kit's actual executable. It checked catalog discovery, scalar/NULL behavior, a constant-argument constraint, named table arguments and their constraint, an empty table, 25,000 rows across batches, and a paginated local fixture API. It made no production API calls.

## Fresh agent builds

The prompt chose a language and requested `badge.main.initials(name VARCHAR) -> VARCHAR`, preserving NULL and handling whitespace. It named the installed `vgi-worker` skill but did **not** mention starters, a repository, `make init`, or `make check`. Each agent had to discover that workflow from the updated skill.

| Agent | Chosen language | Observed behavior | Independent result |
| --- | --- | --- | --- |
| Codex | Python | Cloned the Python kit, initialized `badge`, kept the SDK lock and quality checks, added function metadata and tests, and supplied a stock-DuckDB target and SQL handoff | `make check` passed; 7/7 stock checks |
| Claude Code | TypeScript | Cloned the TypeScript kit, initialized `badge`, kept Bun and the SDK lock, added metadata and tests, and distinguished Haybarn checks from stock DuckDB | `make check` passed; 7/7 stock checks |

Both kept parent project instructions intact and removed the starter's upstream remote. No human edits repaired their worker implementations. The independent verifier reran `make check` and asserted SQL results outside the generated manifest, including unseen names, tabs/newlines, NULL/empty input, result type, and 10,000 varying inputs. Claude's added stock-DuckDB target uses the installed skill verifier, with a documented `VERIFIER` override; this evaluation does not claim its child project is a standalone distribution archive.

The [machine-readable evidence](starters.json) includes full source revisions, resolved SDK versions, timings, prompts, installed skill hashes, review notes, and individual results. Raw CLI streams and local paths remain in ignored evaluation directories.

## Repeat the agent checks

With authenticated local Codex and Claude CLIs, run:

```sh
python3 scripts/evaluate_starter_builds.py
uv run scripts/verify_starter_build.py .eval-runs/starter-integration/agents/<run>
```

The first command invokes two real agents and consumes normal account usage. It uses their configured defaults, fresh projects, and a twenty-minute build deadline. Review each conversation and generated diff, then run the independent verifier for each reported directory. Do not replace behavioral review with an exit code alone.

To repeat a kit baseline, clone its repository from the [starter reference](../skills/vgi-worker/references/starters.md), check out the recorded revision, remove the upstream remote, run `make init NAME=skills_<language>`, and run `make check`. Follow that kit's prerequisites and use its actual launcher for stock-DuckDB checks.

## Scope and release status

These are six deterministic kit checks and **two** native-agent build evaluations, not six agent-language evaluations or a reliability estimate. They share a machine and package caches. The [earlier onboarding sweep](onboarding/RESULTS.md) remains evidence for its recorded skill version; it predates the starter workflow. Current language selection and existing-project preservation rules remain in the skill.

The private skills repository's Linux CI is still blocked by GitHub's account billing/spending restriction. Local macOS checks passed; a new Linux CI pass and owner review remain release gates. No main-branch publication or deployment was performed.
