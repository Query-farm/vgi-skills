import { test } from 'node:test';
import assert from 'node:assert/strict';
import { quoteCents } from '../src/rates.ts';

for (const [destination, grams, expected] of [
  ['US', 500n, 550n], ['US', 501n, 700n], ['US', 1800n, 1000n],
  ['CA', 1200n, 1650n], ['GB', 700n, 1900n], [' us ', 500n, 550n],
  ['AU', 900n, null], ['US', 0n, null], ['US', -1n, null],
  ['__proto__', 500n, null], ['constructor', 500n, null],
  ['US', 30_001n, null], ['US', 30_000n, 9400n],
  [null, 500n, null], ['US', null, null],
] as const) {
  test(`${destination}, ${grams}g => ${expected}`, () => assert.equal(quoteCents(destination, grams), expected));
}
