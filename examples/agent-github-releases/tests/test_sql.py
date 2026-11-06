"""Real DuckDB -> VGI extension -> subprocess -> loopback HTTP integration."""

import unittest

import duckdb

from duckdb_runtime import FIXTURE_WORKER, PROJECT, attach_sql, database


class SQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = database()
        cls.con = cls.context.__enter__()
        cls.addClassCleanup(cls.context.__exit__, None, None, None)
        cls.con.execute(attach_sql(FIXTURE_WORKER))

    def test_inventory_query_uses_publication_time_and_excludes_prerelease(self):
        self.assertEqual(self.con.execute((PROJECT / "demo.sql").read_text()).fetchall(), [
            ("Analytics demo", "v1.0.0", "v2.0.0", "https://github.com/duckdb/duckdb/releases/tag/v2.0.0"),
            ("Reporting demo", "v1.1.0", "v2.0.0", "https://github.com/duckdb/duckdb/releases/tag/v2.0.0"),
        ])

    def test_http_and_malformed_errors_reach_sql(self):
        for repo, message in [("missing", "GitHub HTTP 404"), ("unavailable", "GitHub HTTP 503"), ("rate-limited", "GitHub HTTP 429"), ("malformed", "Malformed GitHub response"), ("invalid-json", "invalid JSON")]:
            with self.subTest(repo=repo), self.assertRaisesRegex(duckdb.Error, message):
                self.con.execute(f"SELECT * FROM github.main.releases('fixture', '{repo}')").fetchall()

    def test_matching_tags_and_unrelated_repositories_are_excluded(self):
        query = (PROJECT / "demo.sql").read_text().replace(
            "read_csv('inventory.csv', header = true, all_varchar = true)",
            "(SELECT * FROM (VALUES ('Matching', 'duckdb', 'duckdb', 'v2.0.0'), "
            "('Other repo', 'duckdb', 'other', 'v1.0.0'), "
            "('Other owner', 'other', 'duckdb', 'v1.0.0')) "
            "AS sample(project, owner, repo, installed_tag))",
        )
        self.assertEqual(self.con.execute(query).fetchall(), [])

    def test_empty_release_set_produces_no_inventory_rows(self):
        query = (PROJECT / "demo.sql").read_text().replace(
            "github.main.releases('duckdb', 'duckdb')",
            "github.main.releases('fixture', 'empty')",
        )
        self.assertEqual(self.con.execute(query).fetchall(), [])

    def test_invalid_and_null_arguments_reach_sql(self):
        for arguments in ["'', 'duckdb'", "'a/b', 'duckdb'", "NULL::VARCHAR, 'duckdb'", "'duckdb', NULL::VARCHAR"]:
            with self.subTest(arguments=arguments), self.assertRaisesRegex(duckdb.Error, "(?i)(must be|null|none)"):
                self.con.execute(f"SELECT * FROM github.main.releases({arguments})").fetchall()

    def test_repeated_scans_have_no_stale_rows(self):
        for repo, expected in [("duckdb", 7), ("empty", 0), ("cap", 15), ("empty", 0), ("duckdb", 7)]:
            owner = "duckdb" if repo == "duckdb" else "fixture"
            with self.subTest(repo=repo):
                self.assertEqual(self.con.execute(f"SELECT count(*) FROM github.main.releases('{owner}', '{repo}')").fetchone(), (expected,))


if __name__ == "__main__":
    unittest.main()
