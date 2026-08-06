"""Export the canonical benchmark BFF JSON Schema for frontend generation."""

from __future__ import annotations

import json
from pathlib import Path

from src.benchmarking.api.models import BenchmarkApiContract

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "src" / "frontend" / "src" / "generated" / "benchmark-api.schema.json"


def render_schema() -> str:
    return json.dumps(
        BenchmarkApiContract.model_json_schema(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_schema(), encoding="utf-8")


if __name__ == "__main__":
    main()