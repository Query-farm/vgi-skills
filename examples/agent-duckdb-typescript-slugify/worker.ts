// VGI worker exposing demo.main.slugify(VARCHAR) -> VARCHAR over stdio.
// stdout carries Arrow protocol bytes; never log to stdout.
import { Worker, defineScalarFunction, str, FunctionStability } from "@query-farm/vgi";
import { slugify } from "./src/slugify.ts";

export const slugifyFn = defineScalarFunction({
  name: "slugify",
  description:
    "Convert text to a URL slug: lowercase, transliterate accented Latin to ASCII, " +
    "collapse punctuation/whitespace runs to '-', trim edge hyphens. NULL in, NULL out.",
  params: { text: str },
  argDocs: { text: "Text to slugify" },
  returns: str,
  stability: FunctionStability.CONSISTENT,
  compute: (batch) =>
    Array.from(batch.getChildAt(0)!, (value) =>
      value == null ? null : slugify(value as string)),
});

new Worker({
  catalog: {
    name: "demo",
    comment: "Demo catalog with text utilities",
    schemas: [{ path: ["main"], functions: [slugifyFn] }],
  },
}).run();
