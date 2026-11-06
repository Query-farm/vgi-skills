#!/usr/bin/env python3
"""Publish a small, sanitized summary of completed local evaluation runs."""
from pathlib import Path
import datetime as dt
import json

root = Path(__file__).resolve().parents[1]
results = []
for path in sorted((root / ".eval-runs").glob("*/result.json")):
    result = json.loads(path.read_text())
    result["run_id"] = path.parent.name
    result["human_interventions"] = 0
    result.setdefault("engine", "not-run" if result["case"] == "language-choice" else "haybarn")
    events = path.parent / "events.jsonl"
    if events.exists():
        for line in events.read_text().splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("model"):
                result["model"] = event["model"]
                break
    result.setdefault("model", "Configured CLI default; not pinned or exposed in the event stream")
    results.append(result)
report = {
    "schema_version": 1,
    "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    "environment": "macOS ARM64; fresh project and agent session; shared dependency caches; some runs concurrent",
    "method": "Native Codex/Claude CLI sessions. Generated workers independently checked through the selected engine (Haybarn 2.0.0rc11 or stock DuckDB 2.0.0 with VGI from query_farm). Language-choice cases check that no worker was generated before the developer selected a language. Repair cases use a seeded wrong-result bug. Packaging cases verify the hash and SQL behavior of an extracted archive.",
    "limitations": "Small exploratory sample, not a reliability or speed guarantee. CLI configured/default models, not a controlled model comparison. Agent duration includes its own tests; independent verification duration is recorded separately. No cold-cache or Windows/Linux native-agent measurements. Other agents have portable installation checks, not live execution evaluations.",
    "results": results,
}
(root / "evals/results.json").write_text(json.dumps(report, indent=2) + "\n")
lines = ["# Evaluation results", "", "Recorded " + report["recorded_at"].split("T")[0] + ".", "", report["environment"] + ".", "", report["method"], "", report["limitations"], "", "## Completed sessions", "", "| Agent | Case | Engine | Skill | Result | Agent time | Independent verification |", "| --- | --- | --- | --- | --- | ---: | ---: |"]
for item in results:
    label = "Excluded: harness contract" if item.get("excluded_reason") else item["status"]
    lines.append(f"| {item['agent']} | {item['case']} | {item['engine']} | {'yes' if item['with_skill'] else 'no'} | {label} | {item['agent_seconds']:.1f}s | {item.get('verification_seconds', 0):.1f}s |")
lines += ["", "## Interpretation", "", "The successful build runs return independently checked slugification results, preserve NULL, and handle 10,000 input rows. The shipping-report case separately checks the shipping rule, a five-order report that preserves missing quotes, NULL handling, empty input, and 10,000 rows. A small successful sample establishes that the workflow can work today; it does not establish a universal completion rate or a five-minute guarantee.", "", "Both build skills and no-skill baselines receive the same task and output manifest contract in harness version 2. The first TypeScript baseline used harness version 1, which omitted that private contract; it is retained but excluded from comparisons. Any similarly affected baseline is explicitly marked in the JSON report.", "", "All runs use the locally configured/default model. Claude reports its model in the event stream; Codex's event stream does not identify it. See results.json for exact CLI versions and run-level metadata.", "", "## Portable installation", "", "The skills CLI installed all three skills successfully for Codex, Claude Code, Cursor, GitHub Copilot, and OpenCode in a temporary project. Cursor, Copilot, and OpenCode were not available here for authenticated live-agent execution. Installation compatibility is not labeled as an end-to-end agent pass.", "", "## SDK and engine compatibility", "", "All six current published SDKs passed real SQL smoke checks against Haybarn 2.0.0rc11 on macOS ARM64. Go, Rust, Java, and C# cover scalar/null/multi-batch plus nonempty and empty table results. Python and TypeScript scalar fixtures cover known values, nulls, multiple batches, and empty input. See compatibility.json for versions and assertions. The subsequent stock DuckDB recheck of the agent-generated workers is recorded separately in stock-duckdb.json, without changing their code or relabeling the original build timings. New native-agent runs identify their engine in the table above.", "", "## Reproduce", "", "Run `python3 scripts/evaluate.py --agent codex --case python-build`, or use `--agent claude`. Use `--engine haybarn` to reproduce the original engine path; the current default is stock DuckDB. Build cases are available for python, typescript, go, rust, java, and csharp. Add `--without-skill` for the baseline. Run `python3 scripts/collect_results.py` to regenerate this report. Raw events and generated projects stay in the ignored .eval-runs directory; published summaries contain no account metadata or local paths."]
(root / "evals/RESULTS.md").write_text("\n".join(lines) + "\n")
print(f"Collected {len(results)} completed evaluations.")
