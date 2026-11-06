#!/usr/bin/env python3
"""Keep independently installable skills' shared verifier in sync."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1] / "skills"
for relative in ["scripts/verify_worker.py", "references/testing.md", "references/engine.md"]:
    target = root / "vgi-test" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / "vgi-worker" / relative, target)
