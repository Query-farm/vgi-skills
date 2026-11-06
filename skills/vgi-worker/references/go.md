# Go

Go 1.26+. Use `go get github.com/Query-farm/vgi-go/vgi@v0.39.0` and commit go.mod/go.sum.

The consumer's go.mod must include this replacement; a dependency's replace directives do not propagate:

```text
replace github.com/google/flatbuffers => github.com/rustyconover/flatbuffers v25.12.20-0.20261026151427-0acd09bcd1ff+incompatible
```

Use `NewWorker(WithCatalogName(...))`, register functions, then `RunStdio()` as in the tagged README. Build the binary before the SQL check and put its path in the verifier's worker argv.

Follow Arrow allocator/record ownership and release rules. A separate Arrow fork replacement is needed for shared memory; start with stdio unless shared memory was requested.

Read the current scalar/table interfaces and real examples here:
- https://github.com/Query-farm/vgi-go/blob/v0.39.0/README.md
- https://query.farm/vgi/docs/go/
