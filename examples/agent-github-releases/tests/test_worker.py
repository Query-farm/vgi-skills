from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pyarrow as pa
from vgi.table_function import OutputCollector

from github_worker import (
    API_VERSION, GitHubAPIError, GitHubClient, RELEASE_SCHEMA,
    Releases, ReleasesArgs, TIMEOUT_SECONDS, USER_AGENT, decode_releases,
)
from tests.http_fixture import PAGES, fixture_server


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.server = fixture_server()
        self.base_url, self.requests = self.server.__enter__()
        self.addCleanup(self.server.__exit__, None, None, None)
        self.client = GitHubClient(self.base_url)

    def test_two_pages_follow_link_and_send_unauthenticated_headers(self):
        rows = self.client.fetch("duckdb", "duckdb")
        self.assertEqual(rows, decode_releases(PAGES["1"]) + decode_releases(PAGES["7"]))
        self.assertEqual([parse_qs(urlsplit(r["path"]).query)["page"] for r in self.requests], [["1"], ["7"]])
        for request in self.requests:
            headers = {k.lower(): v for k, v in request["headers"].items()}
            self.assertEqual(headers["user-agent"], USER_AGENT)
            self.assertEqual(headers["accept"], "application/vnd.github+json")
            self.assertEqual(headers["x-github-api-version"], API_VERSION)
            self.assertNotIn("authorization", headers)
            self.assertNotIn("cookie", headers)

    def test_empty_page_stops_even_with_next_link(self):
        self.assertEqual(self.client.fetch("fixture", "empty"), [])
        self.assertEqual(len(self.requests), 1)

    def test_three_page_limit(self):
        rows = self.client.fetch("fixture", "cap")
        self.assertEqual(len(rows), 15)
        self.assertEqual(len(self.requests), 3)
        self.assertEqual(rows[-1]["tag_name"], "page-3-row-4")

    def test_invalid_arguments_do_not_send_http(self):
        for owner, repo in [(None, "duckdb"), ("duckdb", None), ("", "repo"), ("a/b", "repo"), ("owner", "../repo"), ("owner", ".."), ("owner", " has space"), (1, "repo")]:
            with self.subTest(owner=owner, repo=repo), self.assertRaisesRegex(ValueError, "must be"):
                self.client.fetch(owner, repo)
        self.assertEqual(self.requests, [])

    def test_malformed_responses(self):
        for repo in ["malformed", "invalid-json", "invalid-field"]:
            with self.subTest(repo=repo), self.assertRaisesRegex(GitHubAPIError, "Malformed GitHub response"):
                self.client.fetch("fixture", repo)

    def test_upstream_http_errors(self):
        for repo, status in [("missing", 404), ("forbidden", 403), ("unavailable", 503), ("redirect", 302)]:
            with self.subTest(repo=repo), self.assertRaisesRegex(GitHubAPIError, f"GitHub HTTP {status}"):
                self.client.fetch("fixture", repo)
        with self.assertRaisesRegex(GitHubAPIError, "429.*rate limit.*retry after 60"):
            self.client.fetch("fixture", "rate-limited")

    def test_timeout_is_explicit_and_reported(self):
        with patch.object(self.client.opener, "open", side_effect=TimeoutError("timed out")) as mocked:
            with self.assertRaisesRegex(GitHubAPIError, "request failed.*timed out"):
                self.client.fetch("duckdb", "duckdb")
        self.assertEqual(mocked.call_args.kwargs["timeout"], TIMEOUT_SECONDS)

    def test_invalid_pagination_is_rejected(self):
        for repo, message in [("loop", "repeated next link"), ("external-link", "next link must stay")]:
            with self.subTest(repo=repo), self.assertRaisesRegex(GitHubAPIError, message):
                self.client.fetch("fixture", repo)
        self.assertEqual(len(self.requests), 2)

    def test_response_fields_and_nullability(self):
        for field, value in [("tag_name", None), ("html_url", 5), ("prerelease", None), ("name", 5), ("published_at", "bad date"), ("published_at", "2026-06-01")]:
            row = deepcopy(PAGES["1"][0])
            row[field] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(GitHubAPIError, field):
                decode_releases([row])
        rows = decode_releases([PAGES["1"][3]])
        self.assertIsNone(rows[0]["name"])
        self.assertIsNone(rows[0]["published_at"])
        self.assertFalse(RELEASE_SCHEMA.field("prerelease").nullable)
        self.assertTrue(RELEASE_SCHEMA.field("name").nullable)

    def test_arrow_batches_and_empty_schema(self):
        for owner, repo, count in [("duckdb", "duckdb", 7), ("fixture", "empty", 0)]:
            with self.subTest(repo=repo), patch.object(Releases, "client", self.client):
                out = OutputCollector(RELEASE_SCHEMA)
                params = SimpleNamespace(args=ReleasesArgs(owner=owner, repo=repo))
                Releases.process(params, None, out)
                out.validate()
                self.assertTrue(out.finished)
                batch = out.data_batch.batch
                self.assertEqual(batch.num_rows, count)
                self.assertEqual(batch.schema, RELEASE_SCHEMA)
                self.assertEqual(batch.column(4).type, pa.bool_())


if __name__ == "__main__":
    unittest.main()
