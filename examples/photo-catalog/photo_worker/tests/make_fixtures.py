"""Build disposable edge-case fixtures under tests/fixtures/ (regenerated each run).

Copies (never modifies) the original photos in ../inputs/photos.
Layout of tests/fixtures/many:
  photo_000.jpg .. photo_299.jpg   copies of north/south/plain (100 each) -> >1 output batch
  UPPER.JPEG                       copy of north.jpg (case-insensitive extension)
  truncated.jpg                    first 400 bytes of north.jpg (corrupt -> skipped)
  link.jpg -> photo_000.jpg        symlink (skipped)
  dirlink.jpg -> inputs/photos  symlinked directory named like a JPEG (skipped)
  sub/inner.jpg                    nested (not recursed)
  readme.txt                       non-JPEG (ignored)
"""

import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent / "inputs" / "photos"
OUT = HERE / "fixtures"


def main() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    many = OUT / "many"
    (many / "sub").mkdir(parents=True)
    (OUT / "empty").mkdir()
    sources = ["north.jpg", "south.jpg", "plain.jpg"]
    for i in range(300):
        shutil.copyfile(SRC / sources[i % 3], many / f"photo_{i:03d}.jpg")
    shutil.copyfile(SRC / "north.jpg", many / "UPPER.JPEG")
    (many / "truncated.jpg").write_bytes((SRC / "north.jpg").read_bytes()[:400])
    os.symlink("photo_000.jpg", many / "link.jpg")
    os.symlink(SRC, many / "dirlink.jpg")
    shutil.copyfile(SRC / "north.jpg", many / "sub" / "inner.jpg")
    (many / "readme.txt").write_text("not a photo\n")


if __name__ == "__main__":
    main()
