# Website onboarding results

Recorded November 7, 2026. **12/12 reviewed two-turn conversations passed**, with 124 independent SQL/input-preservation checks.

The first turn was the exact website request. Both agents had to ask for the language and source before receiving the second turn. No worker implementation, verification manifest, or oracle answers were supplied. Generated workers were not manually repaired.

| Agent | Request | Chosen language | Outcome | Independent checks |
| --- | --- | --- | --- | --- |
| claude | api | python | passed | 13 |
| codex | api | python | passed | 13 |
| claude | api | typescript | passed | 13 |
| codex | api | typescript | passed | 13 |
| claude | files | python | passed | 9 |
| codex | files | python | passed | 9 |
| claude | files | typescript | passed | 9 |
| codex | files | typescript | passed | 9 |
| claude | library | python | passed | 9 |
| codex | library | python | passed | 9 |
| claude | library | typescript | passed | 9 |
| codex | library | typescript | passed | 9 |

## What was reviewed

Skill discovery, language/source questions before implementation, the chosen language, reuse of supplied data or library code, real SQL execution, repeatable tests, and the final ATTACH/query handoff were reviewed in the saved conversations and artifacts. The independent oracle checked the generated workers against expectations outside their projects.

The [machine-readable results](results.json) include opening responses, individual check outcomes, CLI versions, recorded models, timings, prompt hashes, skill-entrypoint hashes, and review notes. Raw session events and account identifiers remain local.

The exact private feature-branch installation command was also tested in a fresh project for Codex and Claude Code; installed entrypoints, verifier, and engine reference matched the source.

## Findings and corrections

- The agents honored the developer’s language choice and paused for missing source information.
- Claude identified an incorrect DuckDB CLI launch example in the skill reference. Both builder/test skills now use the directly tested `uvx --from duckdb-cli==2.0.0 duckdb` command. The reference was corrected during this sweep; the earlier runs recovered without human help. No worker-source repair was needed.
- The independent verifier accepts a worker in a nested project directory. This accommodates a valid generated layout without changing its implementation.
- One Codex run reported that an initial CLI probe may have registered `query_farm` in DuckDB’s default local repository directory. Its final runner uses project-local storage. The harness isolates projects by instruction; it is not a filesystem sandbox.
- The Claude/Python photo build is preserved as the [downloadable worked example](../../examples/photo-catalog/), including unchanged generated worker source and nine agent-written SQL assertions. Its nine independent checks passed; the packaged download also reproduced from a fresh directory containing spaces.

## Scope

Each of three requests was exercised with Codex and Claude in Python and TypeScript. This is one run per agent/request/language combination, not a success-rate estimate or speed comparison. The configured defaults were used, with shared toolchains/package caches on macOS. The API is a deterministic loopback fixture, not a production integration. Other languages and other coding agents are outside this new conversational matrix. See the [method, commands, and limitations](README.md) and [earlier evaluations](../RESULTS.md).

The opening requests omitted a language, but this sweep’s run-directory names included the intended language label. Every agent still explicitly asked and waited for the reply. The driver now uses opaque run suffixes so future projects do not expose that hint. This sweep is evidence of the requested conversation flow, not a blinded language-selection experiment.

## Remaining release check

The new photo reproduction is included in the Linux CI workflow, but [GitHub Actions did not start the job](https://github.com/Query-farm/vgi-skills/actions/runs/42392619898) because of the account billing/spending-limit restriction. These additions have local macOS verification; a passing Linux run is still required after that restriction is resolved. The repository remains private during review.
