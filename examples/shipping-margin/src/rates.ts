// Fictional USD rates for a reproducible example, not a carrier price list.
export const RATES = {
  US: { base: 400n, per500g: 150n },
  CA: { base: 900n, per500g: 250n },
  GB: { base: 1200n, per500g: 350n },
} as const;

export function quoteCents(destination: string | null, weightGrams: bigint | null): bigint | null {
  if (destination == null || weightGrams == null || weightGrams <= 0n || weightGrams > 30_000n) return null;
  const code = destination.trim().toUpperCase();
  if (!Object.hasOwn(RATES, code)) return null;
  const rate = RATES[code as keyof typeof RATES];
  return rate.base + ((weightGrams + 499n) / 500n) * rate.per500g;
}
