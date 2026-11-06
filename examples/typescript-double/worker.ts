import { Worker, defineScalarFunction, int } from '@query-farm/vgi';

const double = defineScalarFunction({
  name: 'double',
  params: { value: int },
  returns: int,
  compute: batch => Array.from(batch.getChildAt(0)!, value => {
    if (value == null) return null;
    const result = (value as bigint) * 2n;
    if (result < -(2n ** 63n) || result > 2n ** 63n - 1n) throw new Error('double: int64 overflow');
    return result;
  }),
});

new Worker({ catalog: { name: 'demo', schemas: [{ path: ['main'], functions: [double] }] } }).run();
