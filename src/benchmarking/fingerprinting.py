"""Deterministic fingerprints for benchmark corpus and configuration inputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def fingerprint_files(root: Path) -> str:
    """Hash relative paths and bytes for all files below ``root``."""
    if not root.is_dir():
        raise ValueError(f"Corpus directory does not exist: {root}")
    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def fingerprint_json(value: Any) -> str:
    """Hash a JSON-compatible value using a canonical representation."""
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"