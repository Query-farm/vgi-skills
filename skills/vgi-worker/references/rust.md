# Rust

Rust 1.97+. For a new project:

```sh
cargo add vgi@=0.49.2 arrow-array@59.2.0 arrow-schema@59.2.0
```

Commit Cargo.lock for worker applications. Match directly imported Arrow crate versions to the SDK. Build with `cargo build --release`; point the SQL verifier at the actual executable.

Use `Worker::new()`, `register_scalar`, `set_catalog(CatalogModel { ... })`, then `run()`. Read the tagged examples for the current function traits and catalog model:
- https://github.com/Query-farm/vgi-rust/blob/v0.49.2/examples/docs/src/bin/calcscalar.rs
- https://github.com/Query-farm/vgi-rust/blob/v0.49.2/examples/docs/src/bin/calc.rs
- https://query.farm/vgi/docs/rust/

Table producers must explicitly signal completion. HTTP multi-batch producers need the SDK's continuation support; verify the selected transport, not only stdio. Avoid retaining borrowed/reused batch buffers across invocations.
