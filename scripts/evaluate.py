#!/usr/bin/env python3
"""Run fresh native agent sessions and independently verify generated workers.

Uses the developer's installed/authenticated agent. No model override. Runs are
kept outside the tracked source. This invokes real agents and may consume usage.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "python-build": ("vgi-worker", "Build a Python VGI worker exposing demo.main.slugify(VARCHAR) -> VARCHAR. Lowercase text, transliterate accented Latin characters to ASCII, replace runs of punctuation or whitespace with a single hyphen, and trim leading/trailing hyphens. Preserve SQL NULL. Run the worker through Haybarn, add repeatable tests, and leave vgi-worker.json with the actual launch argv and catalog demo in this project. Use published dependencies and pin them. Do not publish or deploy."),
    "typescript-build": ("vgi-worker", "Build a TypeScript VGI worker exposing demo.main.slugify(VARCHAR) -> VARCHAR. Lowercase text, transliterate accented Latin characters to ASCII, replace runs of punctuation or whitespace with a single hyphen, and trim leading/trailing hyphens. Preserve SQL NULL. Run the worker through Haybarn, add repeatable tests, and leave vgi-worker.json with the actual launch argv and catalog demo in this project. Use published dependencies and pin them. Do not publish or deploy."),
    "language-choice": ("vgi-worker", "Build a new VGI worker that makes a text slugification function available from SQL. This is an empty project and I have not selected a programming language yet."),
    "repair-typescript": ("vgi-test", "The existing TypeScript VGI worker should double BIGINT values, but its output is wrong. Reproduce the defect through Haybarn, fix the worker, and run repeatable SQL regression tests including nulls and multiple batches. Keep the worker in TypeScript. Do not publish or deploy."),
    "package-python": ("vgi-package", "Package this existing Python VGI worker as a source/runtime ZIP called demo-worker version 0.1.0 in dist. Include a SHA-256 manifest and runtime/attach/test instructions. Extract and verify the packaged worker through Haybarn in a temporary directory. Do not publish or deploy. Keep vgi-worker.json at the project root in the archive."),
}
for language_id, language_name in {"go": "Go", "rust": "Rust", "java": "Java", "csharp": "C#"}.items():
    CASES[f"{language_id}-build"] = ("vgi-worker", CASES["python-build"][1].replace("Build a Python VGI worker", f"Build a {language_name} VGI worker"))


def execute(command, cwd, timeout, prompt=None):
    start = time.monotonic()
    proc = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE if prompt else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(prompt, timeout=timeout)
        return proc.returncode, stdout, stderr, round(time.monotonic() - start, 3)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate()
        return 124, stdout, stderr + "\nEvaluation deadline exceeded", round(time.monotonic() - start, 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=["codex", "claude"], required=True)
    parser.add_argument("--case", choices=list(CASES), required=True)
    parser.add_argument("--without-skill", action="store_true")
    parser.add_argument("--engine", choices=["duckdb", "haybarn"], default="duckdb")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--runs-dir", type=Path, default=ROOT / ".eval-runs")
    args = parser.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = args.runs_dir / f"{stamp}-{args.agent}-{args.case}-{'baseline' if args.without_skill else 'skill'}"
    project = run / "project"
    project.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    skill, task = CASES[args.case]
    if args.engine == "duckdb":
        task = task.replace("Haybarn", "stock DuckDB 2.0.0 with VGI from query_farm")
    if args.case.endswith('build'):
        task += '\nThe verification manifest format is {"schema_version":1,"catalog":"demo","worker":["executable","argument"],"checks":[{"name":"description","sql":"SELECT ...","rows":[["expected value"]]}]}. Use the real launch argv and appropriate expected rows. This format is an evaluation output contract, independent of the skill.'
    if args.case in {"repair-typescript", "package-python"}:
        fixture = "typescript-double" if args.case == "repair-typescript" else "python-double"
        shutil.copytree(ROOT / "examples" / fixture, project, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("node_modules", "verification.json", "__pycache__"))
        if args.case == "repair-typescript":
            worker = project / "worker.ts"
            worker.write_text(worker.read_text().replace("* 2n", "+ 2n"))
    if not args.without_skill:
        target = project / (".agents" if args.agent == "codex" else ".claude") / "skills" / skill
        shutil.copytree(ROOT / "skills" / skill, target)
        task = f"Use the {skill} skill installed at {target / 'SKILL.md'}.\n\n" + task
    else:
        task += "\nOfficial SDK documentation is at https://query.farm/vgi/docs/ and source repositories under https://github.com/Query-farm."
    task += "\nWork only in this disposable project (and temporary build/test directories). Do not read other evaluation runs, unrelated local repositories, or user files. Do not spawn additional agents."
    (run / "prompt.txt").write_text(task)
    if args.agent == "codex":
        command = ["codex", "exec", "--ephemeral", "--json", "-s", "danger-full-access", "-c", 'approval_policy="never"', "-C", str(project), "-o", str(run / "response.txt"), "-"]
    else:
        command = ["claude", "-p", "--output-format", "stream-json", "--verbose", "--no-session-persistence",
                   "--permission-mode", "acceptEdits", "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch,Skill",
                   "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--setting-sources", ""]
    code, stdout, stderr, seconds = execute(command, project, args.timeout, task)
    (run / "events.jsonl").write_text(stdout)
    (run / "stderr.txt").write_text(stderr)
    result = {"agent": args.agent, "agent_version": subprocess.check_output([args.agent, "--version"], text=True).strip(),
              "case": args.case, "with_skill": not args.without_skill, "started_at": stamp,
              "agent_seconds": seconds, "agent_exit_code": code, "status": "failed", "cache": "shared package caches; fresh project/session"}
    result['harness_version'] = 2
    result['engine'] = args.engine
    if args.case == "language-choice":
        response = (run / "response.txt").read_text() if (run / "response.txt").exists() else stdout
        generated = [p for p in project.rglob("*") if p.suffix in {".py", ".ts", ".rs", ".go", ".java", ".cs"} and not any(part in {".git", ".agents", ".claude"} for part in p.parts)]
        result["language_question"] = any(word in response.lower() for word in ["which language", "what language", "choose a language", "language would", "language do", "prefer"])
        result["worker_files_created"] = len(generated)
        result["status"] = "passed" if code == 0 and result["language_question"] and not generated else "failed"
    elif (project / "vgi-worker.json").exists():
        try:
            if args.case == "package-python":
                import zipfile
                import hashlib
                archive = project / "dist" / "demo-worker-0.1.0.zip"
                manifest = json.loads(archive.with_suffix(".manifest.json").read_text())
                if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest["sha256"]:
                    raise ValueError("Package hash mismatch")
                extracted = run / "extracted"
                with zipfile.ZipFile(archive) as bundle:
                    if any(Path(name).is_absolute() or ".." in Path(name).parts for name in bundle.namelist()):
                        raise ValueError("Unsafe archive path")
                    bundle.extractall(extracted)
                project = extracted
            spec = json.loads((project / "vgi-worker.json").read_text())
            # Assert the user's contract independently of tests generated by the agent.
            if args.case.endswith("build"):
                spec["checks"] = [
                    {"name": "independent values", "sql": "SELECT demo.main.slugify('Hello, VGI!'), demo.main.slugify('Café crème'), demo.main.slugify('  a---b  '), demo.main.slugify('')", "rows": [["hello-vgi", "cafe-creme", "a-b", ""]]},
                    {"name": "independent null", "sql": "SELECT demo.main.slugify(NULL::VARCHAR)", "rows": [[None]]},
                    {"name": "independent multi-batch", "sql": "SELECT count(*) FROM range(10000) WHERE demo.main.slugify('Hello, VGI! ' || range::VARCHAR) = 'hello-vgi-' || range::VARCHAR", "rows": [[10000]]},
                ]
            else:
                spec["checks"] = json.loads((ROOT / "examples/python-double/vgi-worker.json").read_text())["checks"]
            (run / "agent-manifest.json").write_text((project / "vgi-worker.json").read_text())
            (project / "vgi-worker.json").write_text(json.dumps(spec, indent=2))
            engine_package = "duckdb==2.0.0" if args.engine == "duckdb" else "haybarn==2.0.0rc11"
            verify = ["uv", "run", "--with", engine_package, "python", str(ROOT / "skills/vgi-worker/scripts/verify_worker.py"), "--engine", args.engine, "--project", str(project)]
            vcode, vout, verr, vseconds = execute(verify, project, 180)
            (run / "verification.json").write_text(vout)
            (run / "verification-stderr.txt").write_text(verr)
            result.update(verification_exit_code=vcode, verification_seconds=vseconds)
            result["status"] = "passed" if code == 0 and vcode == 0 else "failed"
        except Exception as exc:
            result["error"] = str(exc)
    else:
        result["error"] = "Agent did not produce vgi-worker.json"
    (run / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({**result, "artifacts": str(run)}, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
