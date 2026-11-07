# Start a new worker from a published kit

Choose the language with the developer before copying code. The official kits contain a worker, recipes, metadata, unit and SQL tests, agent instructions, and distribution tooling. Use the kit for a new project; preserve an existing worker or an explicitly requested standalone implementation.

| Language | Public template | Build tools in addition to git, make, and uv |
| --- | --- | --- |
| Python | [Query-farm/vgi-starter-python](https://github.com/Query-farm/vgi-starter-python) | Python 3.13+ |
| TypeScript | [Query-farm/vgi-starter-typescript](https://github.com/Query-farm/vgi-starter-typescript) | Bun (the kit's package manager/runtime) |
| Go | [Query-farm/vgi-starter-go](https://github.com/Query-farm/vgi-starter-go) | Go; preserve its `go.mod` replacements |
| Rust | [Query-farm/vgi-starter-rust](https://github.com/Query-farm/vgi-starter-rust) | Rust/Cargo; follow its declared MSRV |
| Java | [Query-farm/vgi-starter-java](https://github.com/Query-farm/vgi-starter-java) | JDK 25+ for the current kit; use its Gradle wrapper |
| C# | [Query-farm/vgi-starter-csharp](https://github.com/Query-farm/vgi-starter-csharp) | .NET SDK required by the kit |

The kit's README and dependency files define its current prerequisites and versions. They take precedence over the older standalone examples in this skill. A runtime supported by an SDK is not necessarily the build tool used by its starter.

In particular, the Java SDK's Java 21 compatibility does not make Java 21 sufficient to build the current starter, which targets release 25. Check the JDK used by Gradle and the launch script; select an installed compatible JDK for the project rather than lowering the starter's release target to make a build pass.

## Create locally

Clone the selected public repository into a **new directory**. This does not require a GitHub account or a new remote repository. For example, after the developer chooses Python and the catalog name `weather`:

```sh
git clone --depth 1 https://github.com/Query-farm/vgi-starter-python.git weather-worker
cd weather-worker
git rev-parse HEAD
git remote remove origin
make init NAME=weather
make check
```

Use the corresponding repository for the chosen language. Record the source commit before making changes. Removing the cloned upstream remote keeps subsequent work local; `.vgi-starter.json` retains template provenance. Do not use `gh repo create`, push a tag, or deploy merely to bootstrap a local worker.

If the current directory already contains skills or agent instructions, create the worker in a child directory instead of overwriting those files. Read the new worker's `AGENTS.md` and README before building. Use `make init` once: it renames the catalog, package, executable, environment variables, and SQL tests, and regenerates dependency locks. Follow the resulting launcher in the README/Makefile rather than guessing its renamed path.

## Adapt and check

Run the baseline before replacing examples. Add the requested behavior using the closest recipe and the project's metadata conventions. Update tests when the requested interface changes; do not delete checks to conceal failures. Keep deterministic examples and fixtures independent of live services or credentials.

`make check` includes the kit's static/unit checks, SQL checks over its supported transports, and metadata validation. Current kits use `haybarn-unittest` for their SQL suite. For a stock DuckDB deliverable, preserve that suite and add a stock-DuckDB verification of the requested behavior using [testing.md](testing.md). Report the two engines separately. A missing tool, package-download failure, failing baseline, or metadata error is a specific blocker, not permission to bypass a gate.

Keep the SDK's existing version constraints and lockfile. Protocol compatibility can change across minor SDK releases; inspect `make template-diff` and review tested upstream changes before upgrading. Do not replace Go's dependency patches, Java's launcher flags, or the kit's chosen runtime with a minimal example from an older SDK.

## Existing kits and releases

If `.vgi-starter.json` already has a worker `name`, it has been initialized. Extend it in place; do not initialize again. For packaging, use the existing README and release configuration. GitHub workflows, signing, Docker, and HTTP support are available options, not steps required to finish a local build. Publishing or provisioning needs to be part of the developer's request.

Background: [Query Farm starter documentation](https://query.farm/vgi/docs/concepts/starter-templates/).
