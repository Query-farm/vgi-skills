#!/usr/bin/env python3
"""Run explicit VGI SQL assertions in a disposable DuckDB or Haybarn connection.

Standard-library launcher; the engine child imports the selected engine package.
The parent enforces a deadline and owns the test's process group on POSIX.
"""
from __future__ import annotations

import argparse
import datetime as dt
import decimal
import importlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import time
import tempfile


def read_manifest(project: Path) -> dict:
    spec = json.loads((project / "vgi-worker.json").read_text())
    if spec.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    if not isinstance(spec.get("catalog"), str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", spec["catalog"]):
        raise ValueError("catalog must be a SQL identifier (letters, digits, underscores)")
    if not isinstance(spec.get("worker"), list) or not spec["worker"] or not all(isinstance(v, str) and v and "\0" not in v for v in spec["worker"]):
        raise ValueError("worker must be a nonempty argv array of strings")
    if not isinstance(spec.get("checks"), list) or not spec["checks"]:
        raise ValueError("checks must contain at least one SQL assertion")
    for check in spec["checks"]:
        if not isinstance(check, dict) or not isinstance(check.get("sql"), str) or not check["sql"].strip():
            raise ValueError("every check needs SQL")
        if not isinstance(check.get("rows"), list) or not all(isinstance(row, list) for row in check["rows"]):
            raise ValueError("every check needs expected rows as an array of arrays")
        if "columns" in check and (not isinstance(check["columns"], list) or not all(isinstance(v, str) for v in check["columns"])):
            raise ValueError("columns must be an array of names")
    return spec


def normalized(value):
    if isinstance(value, (dt.datetime, dt.date, dt.time, decimal.Decimal)):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (list, tuple)):
        return [normalized(item) for item in value]
    if isinstance(value, dict):
        return {str(key): normalized(item) for key, item in value.items()}
    return value


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_engine(project: Path, engine: str) -> dict:
    module = importlib.import_module(engine)

    spec = read_manifest(project)
    os.chdir(project)
    command = shlex.join(spec["worker"]) if os.name != "nt" else subprocess.list2cmdline(spec["worker"])
    catalog = spec["catalog"]
    attach = f"ATTACH {sql_string(catalog)} AS \"{catalog}\" (TYPE vgi, LOCATION {sql_string(command)});"
    result = {"status": "failed", "engine": engine, "engine_version": module.__version__, "worker": spec["worker"], "attach_sql": attach, "checks": []}
    # Isolate repository registration from the developer's own engine settings.
    repository_dir = tempfile.TemporaryDirectory(prefix="vgi-verifier-repositories-")
    config = {"extension_repository_directory": repository_dir.name} if engine == "duckdb" else {}
    con = module.connect(":memory:", config=config)
    try:
        if engine == "duckdb":
            con.execute("SET allow_extension_repositories = 'allowed';")
            con.execute("CREATE EXTENSION REPOSITORY query_farm WITH PREFIX 'https://duckdb-extensions.query.farm';")
            con.execute("INSTALL vgi FROM query_farm; LOAD vgi FROM query_farm;")
        else:
            con.execute("INSTALL vgi FROM community; LOAD vgi;")
        result["extension_version"] = con.execute("SELECT extension_version FROM duckdb_extensions() WHERE extension_name='vgi'").fetchone()[0]
        result["extension_repository"] = "query_farm" if engine == "duckdb" else "community"
        result["platform"] = con.execute("PRAGMA platform").fetchone()[0]
        con.execute(attach)
        for index, check in enumerate(spec["checks"]):
            item = {"name": check.get("name", f"check-{index + 1}"), "sql": check["sql"], "status": "failed"}
            try:
                cursor = con.execute(check["sql"])
                rows = normalized(cursor.fetchall())
                columns = [column[0] for column in cursor.description]
                item.update(rows=rows, columns=columns)
                if rows != check["rows"]:
                    item["error"] = "Rows differ from expected results"
                    item["expected_rows"] = check["rows"]
                elif "columns" in check and columns != check["columns"]:
                    item["error"] = "Column names differ from expected results"
                    item["expected_columns"] = check["columns"]
                else:
                    item["status"] = "passed"
            except Exception as exc:
                item["error"] = str(exc)
            result["checks"].append(item)
        result["status"] = "passed" if all(item["status"] == "passed" for item in result["checks"]) else "failed"
        con.execute(f'DETACH "{catalog}"')
    finally:
        con.close()
        repository_dir.cleanup()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--engine", choices=["duckdb", "haybarn"], default="duckdb")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--_run", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    start = time.monotonic()
    try:
        if args.timeout <= 0:
            raise ValueError("timeout must be positive")
        project = args.project.resolve()
        read_manifest(project)
        if args._run:
            result = run_engine(project, args.engine)
        else:
            process = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--project", str(project), "--engine", args.engine, "--_run"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                start_new_session=os.name != "nt",
            )
            try:
                stdout, stderr = process.communicate(timeout=args.timeout)
                if stderr:
                    print(stderr, file=sys.stderr, end="")
                try:
                    result = json.loads(stdout)
                except json.JSONDecodeError:
                    result = {"status": "failed", "error": "Engine runner did not return JSON", "exit_code": process.returncode, "output": stdout[-4000:]}
                if process.returncode and result.get("status") == "passed":
                    result.update(status="failed", error="Engine runner exited unsuccessfully", exit_code=process.returncode)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                result = {"status": "failed", "error": "Verification timed out", "timeout_seconds": args.timeout}
    except Exception as exc:
        result = {"status": "failed", "error": str(exc), "error_type": type(exc).__name__}
    result["elapsed_seconds"] = round(time.monotonic() - start, 3)
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
