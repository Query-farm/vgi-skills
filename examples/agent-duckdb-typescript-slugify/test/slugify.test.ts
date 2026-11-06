import { test } from "node:test";
import assert from "node:assert/strict";
import { slugify } from "../src/slugify.ts";

const cases: [string, string][] = [
  ["Hello, World!", "hello-world"],
  ["  --Crème Brûlée--  ", "creme-brulee"],
  ["Ångström Øresund Straße", "angstrom-oresund-strasse"],
  ["Łódź & Kraków", "lodz-krakow"],
  ["Æsir/Œuvre__Þorn", "aesir-oeuvre-thorn"],
  ["multiple   spaces\t\nand...dots", "multiple-spaces-and-dots"],
  ["already-a-slug", "already-a-slug"],
  ["Version 2.0 (beta)", "version-2-0-beta"],
  ["İstanbul", "istanbul"],
  ["!!!", ""],
  ["", ""],
];

for (const [input, expected] of cases) {
  test(`slugify(${JSON.stringify(input)})`, () => {
    assert.equal(slugify(input), expected);
    assert.match(slugify(input), /^(?:[a-z0-9]+(?:-[a-z0-9]+)*)?$/);
  });
}
