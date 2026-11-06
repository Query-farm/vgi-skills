"""Run the bundled verifier with its extension cache confined to the project.

The skill itself is never modified. Only the connection's extension_directory
is added to a temporary copy; all assertions, timeouts, and subprocess checks
remain the bundled verifier's own implementation.
"""

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


def main() -> int:
    project = Path(__file__).resolve().parent
    source = project.parent.parent / "skills/vgi-worker/scripts/verify_worker.py"
    original = source.read_text()
    target = 'config = {"extension_repository_directory": repository_dir.name} if engine == "duckdb" else {}'
    replacement = 'config = {"extension_repository_directory": repository_dir.name, "extension_directory": str(project / ".cache/duckdb/extensions")} if engine == "duckdb" else {}'
    if original.count(target) != 1:
        raise RuntimeError("Bundled verifier changed: review its extension-directory setup before running")
    with TemporaryDirectory(prefix="github-vgi-verifier-") as directory:
        verifier = Path(directory) / "verify_worker.py"
        verifier.write_text(original.replace(target, replacement))
        return subprocess.call([
            sys.executable, str(verifier), "--project", str(project),
            "--timeout", "120", "--output", str(project / "verification.json"),
        ], cwd=project)


if __name__ == "__main__":
    raise SystemExit(main())
