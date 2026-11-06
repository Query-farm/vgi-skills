"""Read-only, unauthenticated GitHub releases over VGI's Arrow stdio transport."""

from dataclasses import dataclass
from datetime import datetime
import json
import re
from typing import Annotated, ClassVar
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

import pyarrow as pa
from vgi import Arg, Worker
from vgi.catalog import Catalog, Schema
from vgi.table_function import (
    OutputCollector,
    ProcessParams,
    TableFunctionGenerator,
    bind_fixed_schema,
    init_single_worker,
)

PAGE_SIZE = 5
MAX_PAGES = 3
TIMEOUT_SECONDS = 10
API_VERSION = "2026-03-10"
USER_AGENT = "github-releases-vgi-demo/0.1.0"
RELEASE_SCHEMA = pa.schema([
    pa.field("tag_name", pa.string(), nullable=False),
    pa.field("name", pa.string(), nullable=True),
    pa.field("published_at", pa.string(), nullable=True),
    pa.field("html_url", pa.string(), nullable=False),
    pa.field("prerelease", pa.bool_(), nullable=False),
])


class GitHubAPIError(RuntimeError):
    """An upstream response cannot be used as a release table."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_arguments(owner: str, repo: str) -> None:
    for label, value, pattern in (
        ("owner", owner, r"[A-Za-z0-9][A-Za-z0-9-]*"),
        ("repo", repo, r"[A-Za-z0-9_.-]+"),
    ):
        if not isinstance(value, str) or not re.fullmatch(pattern, value) or value in (".", ".."):
            raise ValueError(f"{label} must be a non-null, nonempty GitHub name without spaces or slashes")


def decode_releases(payload: object) -> list[dict]:
    """Validate required fields; missing optional fields become SQL NULL."""
    if not isinstance(payload, list) or len(payload) > PAGE_SIZE:
        raise GitHubAPIError(f"Malformed GitHub response: expected an array of at most {PAGE_SIZE} releases")
    rows = []
    for item in payload:
        if not isinstance(item, dict):
            raise GitHubAPIError("Malformed GitHub response: each release must be an object")
        for field in ("tag_name", "html_url"):
            if not isinstance(item.get(field), str) or not item[field]:
                raise GitHubAPIError(f"Malformed GitHub response: {field} must be a nonempty string")
        if not isinstance(item.get("prerelease"), bool):
            raise GitHubAPIError("Malformed GitHub response: prerelease must be a boolean")
        for field in ("name", "published_at"):
            if item.get(field) is not None and not isinstance(item[field], str):
                raise GitHubAPIError(f"Malformed GitHub response: {field} must be a string or null")
        published = item.get("published_at")
        if published is not None:
            try:
                parsed = datetime.fromisoformat(published)
                if parsed.tzinfo is None or "T" not in published:
                    raise ValueError("missing time or timezone")
            except ValueError as exc:
                raise GitHubAPIError("Malformed GitHub response: published_at must be ISO8601 with a timezone") from exc
        rows.append({field: item.get(field) for field in RELEASE_SCHEMA.names})
    return rows


class GitHubClient:
    """One bounded scan per function call; no credentials or environment proxies."""

    def __init__(self, base_url: str = "https://api.github.com", timeout: float = TIMEOUT_SECONDS):
        # The alternate base URL is an injection point for the local HTTP fixtures.
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.opener = build_opener(ProxyHandler({}), NoRedirects())

    def _get_page(self, url: str) -> tuple[list[dict], str]:
        request = Request(url, method="GET", headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
        })
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read()
                link = response.headers.get("Link", "")
        except HTTPError as exc:
            status = exc.code
            rate_limit = exc.headers.get("X-RateLimit-Remaining") == "0" or status == 429
            retry_after = exc.headers.get("Retry-After")
            exc.close()
            hint = " (unauthenticated rate limit reached)" if rate_limit else ""
            if retry_after:
                hint += f"; retry after {retry_after} seconds"
            raise GitHubAPIError(f"GitHub HTTP {status}{hint} for {url}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise GitHubAPIError(f"GitHub request failed for {url}: {exc}") from exc
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise GitHubAPIError("Malformed GitHub response: invalid JSON") from exc
        return decode_releases(payload), link

    def _next_url(self, link: str, current: str, initial: str) -> str | None:
        for target, relations in re.findall(r'<([^>]+)>\s*;\s*rel="([^"]+)"', link):
            if "next" not in relations.split():
                continue
            url = urljoin(current, target)
            parsed, origin = urlsplit(url), urlsplit(initial)
            query = parse_qs(parsed.query)
            valid_path = parsed.path == origin.path or re.fullmatch(r"/repositories/[0-9]+/releases", parsed.path)
            if (
                (parsed.scheme, parsed.netloc) != (origin.scheme, origin.netloc)
                or not valid_path
                or parsed.fragment
                or query.get("per_page") != [str(PAGE_SIZE)]
                or len(query.get("page", [])) != 1
                or not re.fullmatch(r"[1-9][0-9]*", query["page"][0])
            ):
                raise GitHubAPIError("Malformed GitHub pagination: next link must stay on the releases API with per_page=5")
            return url
        return None

    def fetch(self, owner: str, repo: str) -> list[dict]:
        validate_arguments(owner, repo)
        initial = f"{self.base_url}/repos/{owner}/{repo}/releases?{urlencode({'per_page': PAGE_SIZE, 'page': 1})}"
        url = initial
        seen = set()
        rows = []
        for page_index in range(MAX_PAGES):
            if url in seen:
                raise GitHubAPIError("Malformed GitHub pagination: repeated next link")
            seen.add(url)
            page, link = self._get_page(url)
            rows.extend(page)
            if not page or page_index + 1 == MAX_PAGES:
                break
            next_url = self._next_url(link, url, initial)
            if next_url is None:
                break
            url = next_url
        return rows


@dataclass(frozen=True, slots=True, kw_only=True)
class ReleasesArgs:
    owner: Annotated[str, Arg(0, doc="Public GitHub repository owner; NULL and empty names are rejected")]
    repo: Annotated[str, Arg(1, doc="Public GitHub repository name, without slashes or a .git suffix")]


@init_single_worker
@bind_fixed_schema
class Releases(TableFunctionGenerator[ReleasesArgs]):
    """Public releases, limited to three pages of five; name/published_at may be NULL."""

    FIXED_SCHEMA: ClassVar[pa.Schema] = RELEASE_SCHEMA
    client: ClassVar[GitHubClient] = GitHubClient()

    @classmethod
    def process(cls, params: ProcessParams[ReleasesArgs], state: None, out: OutputCollector) -> None:
        rows = cls.client.fetch(params.args.owner, params.args.repo)
        # At most 15 rows: send one typed Arrow batch, including a typed empty batch.
        out.emit(pa.RecordBatch.from_pylist(rows, schema=cls.FIXED_SCHEMA))
        out.finish()


class GitHubWorker(Worker):
    catalog = Catalog(
        name="github",
        comment="Unauthenticated public GitHub releases; bounded demonstration, not full history",
        schemas=[Schema(path=["main"], comment="Public release table functions", functions=[Releases])],
    )


if __name__ == "__main__":
    GitHubWorker().run()
