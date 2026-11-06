"""Launch the real worker against a disposable HTTP fixture, never GitHub."""

from github_worker import GitHubClient, GitHubWorker, Releases
from tests.http_fixture import fixture_server


if __name__ == "__main__":
    with fixture_server() as (base_url, requests):
        Releases.client = GitHubClient(base_url)
        GitHubWorker().run()
