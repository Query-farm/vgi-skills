// Pure slugify logic, independent of VGI so it can be unit tested directly.

// Latin letters that Unicode NFKD does not decompose into ASCII + combining marks.
const SPECIAL: Record<string, string> = {
  "ß": "ss", "ẞ": "ss",
  "æ": "ae", "Æ": "ae",
  "œ": "oe", "Œ": "oe",
  "ø": "o", "Ø": "o",
  "đ": "d", "Đ": "d",
  "ð": "d", "Ð": "d",
  "þ": "th", "Þ": "th",
  "ł": "l", "Ł": "l",
  "ħ": "h", "Ħ": "h",
  "ı": "i",
  "ŀ": "l", "Ŀ": "l",
  "ŧ": "t", "Ŧ": "t",
  "ŋ": "n", "Ŋ": "n",
  "ĸ": "k",
};
const SPECIAL_RE = new RegExp(`[${Object.keys(SPECIAL).join("")}]`, "gu");

/**
 * Lowercase, transliterate accented Latin characters to ASCII, collapse runs of
 * punctuation/whitespace/symbols into a single hyphen, and trim edge hyphens.
 * Letters and digits from non-Latin scripts are kept as-is.
 */
export function slugify(input: string): string {
  return input
    .replace(SPECIAL_RE, (ch) => SPECIAL[ch]!)
    .normalize("NFKD")
    .replace(/\p{M}+/gu, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
}
