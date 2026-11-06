import { FunctionStability, Worker, defineScalarFunction, str } from "@query-farm/vgi";
import { slugify } from "./slugify.ts";

export const slugifyFn = defineScalarFunction({
  name: "slugify",
  description:
    "Convert text to a URL slug: lowercase, transliterate accented Latin to ASCII, " +
    "collapse punctuation/whitespace runs into a single hyphen, trim hyphens. NULL in, NULL out.",
  params: { text: str },
  returns: str,
  stability: FunctionStability.CONSISTENT,
  examples: [{ sql: "SELECT demo.main.slugify('Héllo, Wörld!')", description: "returns 'hello-world'" }],
  compute: (batch) =>
    Array.from(batch.getChildAt(0)!, (v) => (v == null ? null : slugify(String(v)))),
});

new Worker({
  catalog: {
    name: "demo",
    comment: "Demo VGI catalog exposing text utilities.",
    schemas: [{ path: ["main"], comment: "Text utilities.", functions: [slugifyFn] }],
  },
}).run();
