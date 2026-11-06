---
name: vgi-package
description: Package a tested VGI worker for another developer or a release, with explicit runtime requirements, integrity hashes, and an attach example.
---

# Package a VGI worker

Inspect the worker's language, build system, target platform, existing release conventions, and the requested delivery method. Preserve the developer's language. Prepare a local reviewable artifact; publish or deploy only when the user requested that action.

For an executable, build with its normal release tooling. For a source/runtime package, include pinned dependencies and the launch instructions. Choose explicitly between these forms; a source archive is not a self-contained binary.

Use the existing project package command when there is one. Otherwise, the bundled `scripts/package_worker.py` creates a ZIP from an explicit allowlist of project files and writes a SHA-256 manifest. It refuses symlinks, escaping paths and obvious credential files. It never uploads anything.

```sh
python /absolute/path/to/vgi-package/scripts/package_worker.py \
  --project . --name my-worker --version 0.1.0 \
  --include worker.py pyproject.toml uv.lock README.md vgi-worker.json \
  --output-dir dist
```

Select the real artifacts for the chosen language. Include a tested `ATTACH`/`SELECT` example, supported OS/architecture, required runtime, exact SDK version, license information supplied by the project, and test commands. Exclude credentials and local configuration.

Extract the artifact into a fresh temporary directory, run its documented build/install steps, and run its SQL tests using published dependencies. Record the artifact hash and verification result. Fix missing files before handing it off.

For hosted workers, prepare the application's existing deployment configuration and use https://query.farm/vgi/distributing-a-worker for the supported transport/distribution choices. Treat cloud account changes and publication as actions within the user's requested scope, never as a prerequisite to a local worker.
