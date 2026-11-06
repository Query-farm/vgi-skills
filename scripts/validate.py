#!/usr/bin/env python3
"""Validate portable package structure, local references, and shared copies."""
from pathlib import Path
import json
import re

root = Path(__file__).resolve().parents[1]
errors = []
for skill in sorted((root / "skills").iterdir()):
    source = skill / "SKILL.md"
    text = source.read_text()
    if not text.startswith("---\n") or f"name: {skill.name}\n" not in text or "description: " not in text:
        errors.append(f"Invalid skill metadata: {source}")
    if len(text.splitlines()) > 500:
        errors.append(f"Skill entrypoint too long: {source}")
    for page in skill.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", page.read_text()):
            if "://" not in target and not target.startswith("#") and not (page.parent / target.split("#")[0]).exists():
                errors.append(f"Missing reference: {page}: {target}")
for relative in ["scripts/verify_worker.py", "references/testing.md", "references/engine.md"]:
    if (root / "skills/vgi-worker" / relative).read_bytes() != (root / "skills/vgi-test" / relative).read_bytes():
        errors.append(f"Shared file drift: {relative}; run scripts/sync_shared.py")
for relative in [".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"]:
    json.loads((root / relative).read_text())
if errors:
    raise SystemExit("\n".join(errors))
print("Validated 3 portable skills, references, manifests, and shared files.")
