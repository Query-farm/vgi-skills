"""Disposable loopback HTTP server. Unexpected requests fail; there is no live fallback."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

PAGES = json.loads((Path(__file__).parent / "fixtures/releases.json").read_text())


@contextmanager
def fixture_server():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            requests.append({"path": self.path, "headers": dict(self.headers)})
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            page = query.get("page", [""])[0]
            base = f"http://127.0.0.1:{self.server.server_port}"
            status, body, headers = 200, [], {}
            if query.get("per_page") != ["5"] or not page.isdigit():
                status, body = 400, {"message": "Expected per_page=5 and page"}
            elif parsed.path == "/repos/duckdb/duckdb/releases" and page in PAGES:
                body = PAGES[page]
                if page == "1":
                    # Deliberately skip to page 7: following Link is required.
                    headers["Link"] = f'<{base}{parsed.path}?per_page=5&page=7>; rel="next", <{base}{parsed.path}?per_page=5&page=7>; rel="last"'
            elif parsed.path == "/repos/fixture/empty/releases":
                body = []
                headers["Link"] = f'<{base}{parsed.path}?per_page=5&page=2>; rel="next"'
            elif parsed.path == "/repos/fixture/malformed/releases":
                body = {"message": "An object is not a release list"}
            elif parsed.path == "/repos/fixture/invalid-json/releases":
                body = b"{broken JSON"
            elif parsed.path == "/repos/fixture/invalid-field/releases":
                body = [{**PAGES["1"][0], "prerelease": "false"}]
            elif parsed.path == "/repos/fixture/missing/releases":
                status, body = 404, {"message": "Not Found"}
            elif parsed.path == "/repos/fixture/forbidden/releases":
                status, body = 403, {"message": "Forbidden"}
            elif parsed.path == "/repos/fixture/rate-limited/releases":
                status, body = 429, {"message": "Too many requests"}
                headers = {"X-RateLimit-Remaining": "0", "Retry-After": "60"}
            elif parsed.path == "/repos/fixture/unavailable/releases":
                status, body = 503, {"message": "Unavailable"}
            elif parsed.path == "/repos/fixture/loop/releases":
                body = PAGES["1"]
                headers["Link"] = f'<{base}{parsed.path}?per_page=5&page=1>; rel="next"'
            elif parsed.path == "/repos/fixture/external-link/releases":
                body = PAGES["1"]
                headers["Link"] = '<https://example.invalid/releases?per_page=5&page=2>; rel="next"'
            elif parsed.path == "/repos/fixture/redirect/releases":
                status, headers = 302, {"Location": "https://example.invalid/releases"}
            elif parsed.path == "/repos/fixture/cap/releases" and int(page) <= 3:
                body = [{**PAGES["1"][0], "tag_name": f"page-{page}-row-{i}"} for i in range(5)]
                headers["Link"] = f'<{base}{parsed.path}?per_page=5&page={int(page) + 1}>; rel="next"'
            else:
                status, body = 500, {"message": "Unexpected fixture request"}
            raw = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
