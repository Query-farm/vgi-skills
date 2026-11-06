import { test } from "node:test";
import assert from "node:assert/strict";
import { slugify } from "../src/slugify.ts";

const cases: [string, string][] = [
  ["Hello World", "hello-world"],
  ["Héllo, Wörld!", "hello-world"],
  ["  --Crème Brûlée--  ", "creme-brulee"],
  ["Straße & Æsir Œuvre", "strasse-aesir-oeuvre"],
  ["Łódź, Søren, Ðorđe, Þór", "lodz-soren-dorde-thor"],
  ["İstanbul ÇAĞ", "istanbul-cag"],
  ["a...b___c\t\n d", "a-b-c-d"],
  ["already-a-slug", "already-a-slug"],
  ["v2.0 Release (beta)", "v2-0-release-beta"],
  ["ﬁnal ①", "final-1"],
  ["!!!", ""],
  ["", ""],
];

for (const [input, expected] of cases) {
  test(`slugify(${JSON.stringify(input)})`, () => assert.equal(slugify(input), expected));
}

test("output for Latin input is ASCII", () => {
  const out = slugify("ÀÁÂÃÄÅàáâãäåÇçÈÉÊËèéêëÌÍÎÏìíîïÑñÒÓÔÕÖòóôõöÙÚÛÜùúûüÝýÿ");
  assert.match(out, /^[a-z0-9-]*$/);
});
