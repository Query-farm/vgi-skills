// Pure slug logic, kept separate from the worker so it can be unit-tested.

// Latin letters that Unicode does not decompose into base + combining mark.
const LATIN_SPECIAL: Record<string, string> = {
  "ß": "ss", "ẞ": "ss", "æ": "ae", "œ": "oe", "ø": "o", "đ": "d", "ð": "d",
  "þ": "th", "ł": "l", "ħ": "h", "ı": "i", "ŀ": "l", "ŧ": "t", "ŋ": "n",
  "ĸ": "k", "ſ": "s", "ƒ": "f",
};
const LATIN_SPECIAL_RE = new RegExp(`[${Object.keys(LATIN_SPECIAL).join("")}]`, "gu");

/**
 * Lowercase, transliterate accented Latin characters to ASCII, collapse runs of
 * punctuation/whitespace (any non-letter, non-digit) into one hyphen, and trim
 * leading/trailing hyphens. Letters from non-Latin scripts are kept as-is.
 */
export function slugify(input: string): string {
  return input
    .toLowerCase()
    .normalize("NFKD")
    .replace(/(\p{Script=Latin})\p{M}+/gu, "$1") // drop diacritics on Latin letters
    .replace(LATIN_SPECIAL_RE, (c) => LATIN_SPECIAL[c]!)
    .normalize("NFC")
    .replace(/[^\p{L}\p{N}\p{M}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
}
