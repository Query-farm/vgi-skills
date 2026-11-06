# TypeScript

Node 22.15+ or Bun. Install the SDK and its Arrow/RPC peers together:

```sh
npm install --save-exact @query-farm/vgi@0.48.0 @query-farm/apache-arrow@21.1.1 @query-farm/vgi-rpc@0.29.2
npm install --save-dev --save-exact tsx
```

Use `node --import tsx worker.ts`, Bun, or the project's existing compile/start command. Commit the lockfile.

```typescript
import { Worker, defineScalarFunction, int } from '@query-farm/vgi';
const double = defineScalarFunction({
  name: 'double', params: { value: int }, returns: int,
  compute: batch => Array.from(batch.getChildAt(0)!, value =>
    value == null ? null : (value as bigint) * 2n),
});
new Worker({catalog: {name: 'demo', schemas: [{path: ['main'], functions: [double]}]}}).run();
```

`int` is an instantiated BIGINT type; `int64()` is a callable type factory. BIGINT values are `bigint`, so keep arithmetic in that representation and check bounds for results that may overflow. Do not convert large integers through `Number`.

0.48.0 uses protocol vgi.v3 / 3.1.0. An older v2 engine requires a matching earlier SDK (the release README points to 0.46.x). Test the installed extension instead of guessing compatibility.

Canonical release examples, including table producers:
- https://github.com/Query-farm/vgi-typescript/blob/v0.48.0/README.md
- https://query.farm/vgi/docs/typescript/
