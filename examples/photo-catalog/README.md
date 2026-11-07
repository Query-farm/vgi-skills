# A photo folder becomes a SQL catalog

This is the unchanged Python worker produced by Claude Code from the photo request
on the VGI agent quickstart. The agent first asked for a folder and language. The
second turn chose Python and specified the SQL interface and file handling.
See `request.txt`, `reply.txt`, and `provenance.json` for the conversation and origin.
The example language is Python; developers using the skill choose their own language.

All images are tiny, original synthetic JPEGs. Camera names, dates, and coordinates
are test metadata, not someone's personal photos. The folder includes two images
with EXIF, one without it, a corrupt file, and a nested image that should be skipped.

## Reproduce the saved build

Install `uv`, then run from this directory:

```sh
uv run demo.py
```

This runs the agent's nine SQL assertions through stock DuckDB 2.0.0 and VGI from
`query_farm`, including multiple output batches and empty input. It then prints the
exact `ATTACH` and query for your checkout and verifies this result:

| camera | year | photos |
| --- | ---: | ---: |
| (unknown) | NULL | 1 |
| Fixture Camera A | 2025 | 1 |
| Fixture Camera B | 2024 | 1 |

The original onboarding evaluation also ran nine independent checks, including a
new photo introduced after the agent finished and hashes of the unchanged inputs.
The demo runner and archive packaging were added afterward; the worker source,
pinned dependencies, lockfile, generated fixture helper, and SQL manifest are unchanged.

`photo_worker/` contains the code and its dependencies. `inputs/photos/` is read
only. The test helper regenerates disposable files under `photo_worker/tests/fixtures/`.
The worker processes JPEGs directly in the requested folder, skips symlinks and
corrupt files, and reports missing metadata as SQL NULL. It does not recurse.
It is a photo-metadata example, not a general image-format or filesystem crawler.

## Build your own

Install the `vgi-worker` skill in a fresh project, extract the sample inputs, and
paste `request.txt`. Answer the agent's language and folder questions. You can use
`reply.txt` for this example's scope, replacing Python with your chosen language.
Use the `ATTACH` and query that your own agent tests and returns.

Download bundles include `tools/verify_worker.py` so the saved example can be checked
without a clone of the skills repository. SDK and extension downloads need network
access during setup; the worker keeps photo metadata processing local.
