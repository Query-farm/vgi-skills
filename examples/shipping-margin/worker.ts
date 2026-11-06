import { Worker, defineScalarFunction, str, int, FunctionStability } from '@query-farm/vgi';
import { quoteCents } from './src/rates.ts';

const quote = defineScalarFunction({
  name: 'quote_cents',
  description: 'Fictional shipping estimate in USD cents. Unknown destinations and invalid weights return NULL.',
  params: { destination: str, weight_g: int },
  returns: int,
  stability: FunctionStability.CONSISTENT,
  compute: batch => {
    const destinations = batch.getChildAt(0)!;
    const weights = batch.getChildAt(1)!;
    return Array.from({ length: batch.numRows }, (_, i) =>
      quoteCents(destinations.get(i) as string | null, weights.get(i) as bigint | null));
  },
});

new Worker({ catalog: {
  name: 'shipping',
  comment: 'Fictional shipping rates for the VGI worked example.',
  schemas: [{ path: ['main'], functions: [quote] }],
} }).run();
