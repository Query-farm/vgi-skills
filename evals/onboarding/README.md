# Website onboarding evaluation

This suite starts with the three short requests people can copy from the website. Each run uses a fresh project, installs `vgi-worker` with the skills CLI, and sends the request unchanged to Codex or Claude Code. The first turn does not specify a language or source. The second turn supplies the developer's choice and input data, through the **same agent session**.

The matrix covers API integration, local photos, and an existing validation library in Python and TypeScript, with both agents: 12 conversations. Each agent sees each opening request twice, with a different language in the reply. These are not repeated trials under identical conditions, a model comparison, or a reliability estimate. Other languages have separate [earlier coverage](../RESULTS.md); other coding agents have installation coverage only.

## Run it

Use authenticated local Codex and Claude Code CLIs, Node/npm, uv, and the required worker toolchains. This consumes normal agent account usage. The harness does not choose a model. Agents can download public documentation and packages, but must keep artifacts local and preserve supplied inputs.

Start the read-only fixture service in one terminal:

```sh
python3 scripts/onboarding_fixtures.py serve --url-file .eval-runs/onboarding-service/url.txt
```

In another terminal, point at the website checkout being reviewed:

```sh
python3 scripts/run_onboarding_matrix.py \
  --website-source /path/to/query-farm-astro/src/lib/vgi-agents.ts \
  --base-url-file .eval-runs/onboarding-service/url.txt \
  --workers 2
```

`requests.json` must match the website source. Each run retains its installation log, prompts, responses, CLI events, generated project, file hashes, and independent SQL results under ignored `.eval-runs/onboarding/`. A run has a three-minute initial-turn deadline and a fifteen-minute build deadline. The independent verifier has its own 150-second deadline. Stop the fixture service after API verification finishes.

The CLI driver resumes explicit session IDs using the supported [Codex non-interactive interface](https://learn.chatgpt.com/docs/non-interactive-mode) and [Claude Code headless interface](https://code.claude.com/docs/en/headless). Raw events can contain account information and must stay local.

## What counts as success

Review the actual first response, generated source, test evidence, and final handoff. Record that review in `reviews.json`; the collector does not infer conversational success from a keyword match.

- The agent discovers and reads the installed skill, asks for the missing language and source, and writes no implementation before the reply.
- It uses the chosen language and supplied source. A library worker must call the existing library, not duplicate its rule.
- It runs the worker through VGI in stock DuckDB and leaves repeatable checks plus usable `ATTACH` and query instructions.
- Independent SQL assertions pass. Their expected results are outside the agent project and are not taken from its own verification manifest.
- Supplied input files remain unchanged.

The oracle checks catalog/function discovery, exact values, NULLs, empty inputs, repeated or large scans, and source-specific failure cases. API cases cover pagination, a CSV join retaining zero-count customers, 10,001 records, 503/429/malformed/cyclic responses, and a response not supplied during the build. Photo cases add a new photo after the build. Library cases check extra inputs and 10,000 rows. Generated manifests provide the launch command, not the oracle's expected answers.

Publish the reviewed summary with:

```sh
python3 scripts/collect_onboarding_results.py
```

The collector exports an explicit field allowlist, redacts local paths/service ports, retains every recorded attempt, and fails if any completed run lacks review. Keep failures in the report when retrying. Native-agent conversations remain manual; deterministic fixtures, helper tests, and the saved [photo example](../../examples/photo-catalog/) also run in CI.

## Limits

These are functional checks, not a security sandbox or proof against malicious generated code. Runs use separate projects but share a machine, installed toolchains, and package caches. Fixture HTTP data is deterministic and local; it does not test real-service authentication, credentials, or network availability. The saved photo example processes JPEG metadata; it is not a complete photo-library product. Wall times include tool and package work and must not become a five-minute promise.
