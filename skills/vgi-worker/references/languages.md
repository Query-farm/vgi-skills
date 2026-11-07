# Choose a worker language

Ask the developer which language they want when creating a project without an existing or requested language. These are worker languages; the Python engine used by the test helper does not constrain that choice.

For new projects, start from the matching [published starter kit](starters.md). Its dependency constraints, lockfiles, runtime, and agent instructions are authoritative. The table below records the older standalone examples in this skill; it is not a reason to downgrade a starter or change an existing project.

| Language | Standalone SDK snapshot | Reference |
| --- | --- | --- |
| Python | vgi-python 0.49.0, Python 3.13+ | [Python](python.md) |
| TypeScript | @query-farm/vgi 0.48.0, Node 22.15+ or Bun | [TypeScript](typescript.md) |
| Go | vgi-go v0.39.0, Go 1.26+ | [Go](go.md) |
| Rust | vgi 0.49.2, Rust 1.97+ | [Rust](rust.md) |
| Java | farm.query:vgi 0.46.0, Java 21+ | [Java](java.md) |
| C# | QueryFarm.Vgi 0.23.0, .NET 10 | [C#](csharp.md) |

Snapshot checked 2026-11-06 against package registries. A published SDK version is not by itself an engine compatibility guarantee. Run the actual SQL test against the selected engine before claiming compatibility. Respect working pins in an existing project.
