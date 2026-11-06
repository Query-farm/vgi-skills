# C#

.NET 10, target `net10.0`. Install `dotnet add package QueryFarm.Vgi --version 0.23.0` and preserve the existing NuGet lock/version conventions.

Use `new Worker().CatalogName(...).DefaultSchema("main").RegisterScalar(...)`, then `await worker.RunFromArgsAsync(args)`. Read the actual release example for function attributes and typed Arrow arguments.

Build/publish before invoking the worker. Use a published executable or `dotnet path/to/Worker.dll` as the verifier argv; build diagnostics must not contaminate stdio protocol output.

- https://github.com/Query-farm/vgi-csharp/blob/v0.23.0/examples/docs/UpperCaseFunction.cs
- https://github.com/Query-farm/vgi-csharp/blob/v0.23.0/examples/docs/NumbersFunction.cs
- https://query.farm/vgi/docs/csharp/how-to/testing/

Test nulls, empty results, multiple batches and disposal/ownership boundaries. Use an engine integration test for aggregate registration and GROUP BY behavior.
