#!/usr/bin/env python3
"""Build a deterministic source/runtime ZIP from an explicit file allowlist."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


def package(project: Path, includes: list[str], output_dir: Path, name: str, version: str) -> dict:
    for value in (name, version):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
            raise ValueError("name and version must contain only letters, digits, dot, underscore or hyphen")
    project = project.resolve()
    files = {}
    for entry in includes:
        relative = Path(entry)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Include must be inside the project: {entry}")
        source = project / relative
        candidates = [source] if not source.is_dir() else sorted(source.rglob("*"))
        if not source.exists():
            raise ValueError(f"Missing artifact: {entry}")
        for candidate in candidates:
            rel = candidate.relative_to(project)
            if any((project / Path(*rel.parts[:index])).is_symlink() for index in range(1, len(rel.parts) + 1)):
                raise ValueError(f"Symlinks are not package artifacts: {rel}")
            if not candidate.is_file():
                continue
            if any(part in {".git", ".venv", "__pycache__", "node_modules"} or part.startswith(".env") for part in rel.parts) or candidate.suffix.lower() in {".pem", ".key", ".p12"}:
                raise ValueError(f"Refusing local/credential artifact: {rel}")
            files[rel.as_posix()] = candidate
    if not files:
        raise ValueError("No files selected")
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{name}-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for relative, source in sorted(files.items()):
            info = zipfile.ZipInfo(relative, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (source.stat().st_mode & 0o777) << 16
            bundle.writestr(info, source.read_bytes())
    report = {"name": name, "version": version, "format": "zip", "artifact": archive.name,
              "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "files": sorted(files)}
    archive.with_suffix(".manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--include", nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    try:
        result = package(args.project, args.include, args.output_dir, args.name, args.version)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
