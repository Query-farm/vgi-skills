# Evaluation results

Recorded 2026-11-06.

macOS ARM64; fresh project and agent session; shared dependency caches; some runs concurrent.

Native Codex/Claude CLI sessions. Generated workers independently checked through the selected engine (Haybarn 2.0.0rc11 or stock DuckDB 2.0.0 with VGI from query_farm). Language-choice cases check that no worker was generated before the developer selected a language. Repair cases use a seeded wrong-result bug. Packaging cases verify the hash and SQL behavior of an extracted archive.

Small exploratory sample, not a reliability or speed guarantee. CLI configured/default models, not a controlled model comparison. Agent duration includes its own tests; independent verification duration is recorded separately. No cold-cache or Windows/Linux native-agent measurements. Other agents have portable installation checks, not live execution evaluations.

## Completed sessions

| Agent | Case | Engine | Skill | Result | Agent time | Independent verification |
| --- | --- | --- | --- | --- | ---: | ---: |
| claude | typescript-build | haybarn | yes | passed | 102.6s | 1.6s |
| codex | python-build | haybarn | yes | passed | 253.3s | 3.1s |
| claude | language-choice | not-run | yes | passed | 15.6s | 0.0s |
| claude | python-build | haybarn | yes | passed | 160.0s | 3.2s |
| claude | repair-typescript | haybarn | yes | passed | 65.9s | 0.9s |
| codex | typescript-build | haybarn | yes | passed | 319.0s | 0.7s |
| claude | typescript-build | haybarn | no | Excluded: harness contract | 169.4s | 0.3s |
| codex | language-choice | not-run | yes | passed | 38.8s | 0.0s |
| claude | package-python | haybarn | yes | passed | 123.3s | 2.6s |
| codex | python-build | haybarn | no | Excluded: harness contract | 273.7s | 0.1s |
| claude | typescript-build | haybarn | no | passed | 156.4s | 0.7s |
| claude | go-build | haybarn | yes | passed | 152.4s | 0.5s |
| claude | rust-build | haybarn | yes | passed | 157.8s | 0.5s |
| codex | python-build | haybarn | no | passed | 294.8s | 0.7s |
| claude | csharp-build | haybarn | yes | passed | 135.3s | 0.8s |
| claude | java-build | haybarn | yes | passed | 136.5s | 1.2s |
| claude | typescript-build | duckdb | yes | passed | 98.4s | 1.0s |
| codex | python-build | duckdb | yes | passed | 258.5s | 1.4s |
| claude | shipping-report | duckdb | yes | passed | 167.6s | 1.1s |

## Interpretation

The successful build runs return independently checked slugification results, preserve NULL, and handle 10,000 input rows. The shipping-report case separately checks the shipping rule, a five-order report that preserves missing quotes, NULL handling, empty input, and 10,000 rows. A small successful sample establishes that the workflow can work today; it does not establish a universal completion rate or a five-minute guarantee.

Both build skills and no-skill baselines receive the same task and output manifest contract in harness version 2. The first TypeScript baseline used harness version 1, which omitted that private contract; it is retained but excluded from comparisons. Any similarly affected baseline is explicitly marked in the JSON report.

All runs use the locally configured/default model. Claude reports its model in the event stream; Codex's event stream does not identify it. See results.json for exact CLI versions and run-level metadata.

## Portable installation

The skills CLI installed all three skills successfully for Codex, Claude Code, Cursor, GitHub Copilot, and OpenCode in a temporary project. Cursor, Copilot, and OpenCode were not available here for authenticated live-agent execution. Installation compatibility is not labeled as an end-to-end agent pass.

## SDK and engine compatibility

All six current published SDKs passed real SQL smoke checks against Haybarn 2.0.0rc11 on macOS ARM64. Go, Rust, Java, and C# cover scalar/null/multi-batch plus nonempty and empty table results. Python and TypeScript scalar fixtures cover known values, nulls, multiple batches, and empty input. See compatibility.json for versions and assertions. The subsequent stock DuckDB recheck of the agent-generated workers is recorded separately in stock-duckdb.json, without changing their code or relabeling the original build timings. New native-agent runs identify their engine in the table above.

## Reproduce

Run `python3 scripts/evaluate.py --agent codex --case python-build`, or use `--agent claude`. Use `--engine haybarn` to reproduce the original engine path; the current default is stock DuckDB. Build cases are available for python, typescript, go, rust, java, and csharp. Add `--without-skill` for the baseline. Run `python3 scripts/collect_results.py` to regenerate this report. Raw events and generated projects stay in the ignored .eval-runs directory; published summaries contain no account metadata or local paths.

## Filmed integration build

A separate interactive Codex session built a Python GitHub releases table and joined its live API data to a sample local inventory. The CLI reported 7m 11s of work; the full screen capture includes setup and waiting (8m 11s). The generated project passed 16 tests and five SQL verifier assertions. Independent checking matched live SQL rows against a direct API response. The initial folder trust prompt was confirmed; no human source corrections were supplied. See [the recorded run metadata](github-integration.json) and [source and reproduction commands](../examples/agent-github-releases/README.md). This run is outside the automated harness table above.
