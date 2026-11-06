"""Run demo.sql against live GitHub, print the rows, and save live-result.json."""

from datetime import datetime, timezone
import json
import os
import time

import duckdb

from duckdb_runtime import LIVE_WORKER, PROJECT, attach_sql, database
from github_worker import MAX_PAGES, PAGE_SIZE


def print_table(columns, rows):
    displayed = [["NULL" if value is None else str(value) for value in row] for row in rows]
    widths = [max(len(column), *(len(row[i]) for row in displayed)) if displayed else len(column) for i, column in enumerate(columns)]
    def line(row):
        return "| " + " | ".join(value.ljust(width) for value, width in zip(row, widths)) + " |"
    print(line(columns))
    print("|-" + "-|-".join("-" * width for width in widths) + "-|")
    for row in displayed:
        print(line(row))
    if not rows:
        print("(0 rows)")


def main():
    os.chdir(PROJECT)
    start = time.monotonic()
    with database() as con:
        attach = attach_sql(LIVE_WORKER)
        con.execute(attach)
        sql = (PROJECT / "demo.sql").read_text()
        cursor = con.execute(sql)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        result = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "source": "https://api.github.com/repos/duckdb/duckdb/releases",
            "live_api": True,
            "inventory": "inventory.csv (fictional sample data)",
            "limits": {"max_pages": MAX_PAGES, "per_page": PAGE_SIZE, "max_releases": MAX_PAGES * PAGE_SIZE},
            "selection": "Most recently published non-prerelease among fetched rows; differing tags are not necessarily safe upgrades",
            "engine": "duckdb",
            "engine_version": duckdb.__version__,
            "extension_version": con.execute("SELECT extension_version FROM duckdb_extensions() WHERE extension_name = 'vgi'").fetchone()[0],
            "platform": con.execute("PRAGMA platform").fetchone()[0],
            "attach_sql": attach,
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "elapsed_seconds": round(time.monotonic() - start, 3),
        }
        con.execute("DETACH github")
    (PROJECT / "live-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"Live GitHub integration at {result['recorded_at']}")
    print(f"Limit: {MAX_PAGES} pages × {PAGE_SIZE} releases; latest stable publication within this fetched window.")
    print("Inventory is fictional. Tag differences require review; they are not guarantees of safe upgrades.\n")
    print_table(columns, rows)
    print("\nSaved live-result.json")
    print("Reproduce: uv run --frozen python run_demo.py")


if __name__ == "__main__":
    main()
