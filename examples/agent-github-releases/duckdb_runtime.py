"""Shared engine setup; downloaded extensions and registrations stay in this project."""

from contextlib import contextmanager
from pathlib import Path
import shlex

import duckdb

PROJECT = Path(__file__).resolve().parent
LIVE_WORKER = [".venv/bin/python", "github_worker.py"]
FIXTURE_WORKER = [".venv/bin/python", "-m", "tests.fixture_worker"]


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def attach_sql(argv: list[str]) -> str:
    return f"ATTACH 'github' AS github (TYPE vgi, LOCATION {sql_string(shlex.join(argv))});"


@contextmanager
def database():
    cache = PROJECT / ".cache" / "duckdb"
    con = duckdb.connect(":memory:", config={
        "extension_directory": str(cache / "extensions"),
        "extension_repository_directory": str(cache / "repositories"),
    })
    try:
        con.execute("SET allow_extension_repositories = 'allowed';")
        con.execute("CREATE EXTENSION REPOSITORY IF NOT EXISTS query_farm WITH PREFIX 'https://duckdb-extensions.query.farm';")
        con.execute("INSTALL vgi FROM query_farm; LOAD vgi FROM query_farm;")
        yield con
    finally:
        con.close()
