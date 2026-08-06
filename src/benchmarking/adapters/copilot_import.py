"""Import externally measured Copilot Studio A/A2 rows."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from src.benchmarking.models import CaseResult


class CopilotStudioImportRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    measurement_boundary: str
    result: CaseResult


def load_copilot_studio_results(path: Path) -> list[CaseResult]:
    """Load manual/proxy measurements without claiming automated invocation."""
    results: list[CaseResult] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if "copilot" not in str(payload.get("measurement_boundary", "")).lower():
                raise ValueError("Copilot imports require an explicit Copilot measurement boundary")
            row = CopilotStudioImportRow.model_validate(payload)
            results.append(row.result)
    return results