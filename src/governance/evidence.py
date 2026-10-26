"""Small, explicit evidence records shared by the governance CLI and notebooks."""

from __future__ import annotations

import csv
import html
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

EvidenceKind = Literal["synthetic", "live", "snapshot", "unavailable", "unverified"]
Status = Literal["observed", "attention", "unknown", "error"]
Category = Literal["inventory", "control", "usage", "security", "visibility"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Asset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    asset_id: str
    name: str
    platform: str
    cloud: Literal["Azure Commercial", "Azure Government", "Microsoft 365 GCC", "Unknown"]
    owner: str = "Unassigned"
    runtime: str
    source: str
    evidence_kind: EvidenceKind
    collected_at: AwareDatetime


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    asset_id: str
    category: Category
    observation: str
    status: Status
    evidence_kind: EvidenceKind
    source: str
    collected_at: AwareDatetime
    http_status: int | None = Field(default=None, ge=100, le=599)
    total_tokens: int | None = Field(default=None, ge=0)
    remaining_tokens: int | None = Field(default=None, ge=0)
    latency_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    request_count: int | None = Field(default=None, ge=0)
    signal_count: int | None = Field(default=None, ge=0)
    event_at: AwareDatetime | None = None
    correlation_id: str | None = None

    @model_validator(mode="after")
    def validate_unknown(self) -> Evidence:
        if self.evidence_kind in ("unavailable", "unverified") and self.status == "observed":
            raise ValueError("Unavailable/unverified evidence cannot assert an observation.")
        return self


class Estate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    assets: tuple[Asset, ...]
    evidence: tuple[Evidence, ...]

    @model_validator(mode="after")
    def validate_links(self) -> Estate:
        ids = [asset.asset_id for asset in self.assets]
        if len(ids) != len(set(ids)):
            raise ValueError("Asset IDs must be unique.")
        if any(row.asset_id not in ids for row in self.evidence):
            raise ValueError("Every evidence row must reference an inventory asset.")
        return self


def synthetic_estate() -> Estate:
    """Illustrative records, never copied from a customer tenant or live alerts."""
    stamp = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
    definitions = (
        ("prompt-agent", "pwwdemo-prompt-agent", "Foundry", "prompt"),
        ("hosted-agent", "pwwdemo-hosted-agent", "Foundry", "hosted"),
        ("gateway", "pwwdemo-ai-gateway", "API Management", "model API"),
        ("external-ai", "pwwdemo-external-ai", "External AI", "browser application"),
    )
    assets = tuple(Asset(
        asset_id=key, name=name, platform=platform, runtime=runtime,
        cloud="Azure Commercial", owner="Synthetic demo team",
        source="synthetic fixture: src/governance/evidence.py",
        evidence_kind="synthetic", collected_at=stamp,
    ) for key, name, platform, runtime in definitions)
    rows = [
        Evidence(
            asset_id=asset.asset_id, category="inventory", status="observed",
            evidence_kind="synthetic", source=asset.source, collected_at=stamp,
            observation="Illustrative inventory entry; not a discovered tenant resource.",
        ) for asset in assets
    ]
    for consumer, code, tokens, remaining in (
        ("asset-agent", 200, 120, 1880),
        ("partner-app", 200, 180, 1820),
        ("partner-app", 429, None, 0),
    ):
        rows.append(Evidence(
            asset_id="gateway", category="usage", status="observed" if code == 200 else "attention",
            observation=f"{consumer}: synthetic HTTP {code}; separate consumer counters.",
            evidence_kind="synthetic", source=assets[2].source, collected_at=stamp,
            http_status=code, total_tokens=tokens, remaining_tokens=remaining,
            request_count=1,
        ))
    rows.extend((
        Evidence(
            asset_id="gateway", category="control", status="observed",
            observation="Synthetic content-filter block; not evidence of a Defender alert.",
            evidence_kind="synthetic", source=assets[2].source, collected_at=stamp,
            http_status=400,
        ),
        Evidence(
            asset_id="hosted-agent", category="visibility", status="unknown",
            observation="Agent 365 ingestion and attributed risk have not been verified.",
            evidence_kind="unverified", source="Agent 365 / Defender (not queried)",
            collected_at=stamp,
        ),
        Evidence(
            asset_id="external-ai", category="security", status="unknown",
            observation="No browser-AI connector; security visibility is unknown, not zero risk.",
            evidence_kind="unavailable", source="No collector configured", collected_at=stamp,
        ),
    ))
    return Estate(assets=assets, evidence=tuple(rows))


def overview(estate: Estate) -> list[dict[str, str]]:
    """Describe evidence coverage, not a compliance score or merged risk rating."""
    result = []
    for asset in estate.assets:
        rows = [row for row in estate.evidence if row.asset_id == asset.asset_id]
        signals = [row.signal_count for row in rows if row.signal_count is not None]
        result.append({
            "asset": asset.name, "platform": asset.platform, "cloud": asset.cloud,
            "owner": asset.owner, "runtime": asset.runtime,
            "inventory": asset.evidence_kind,
            "evidence": ", ".join(sorted({row.evidence_kind for row in rows})) or "unverified",
            "gaps/errors": str(sum(row.status in ("unknown", "error") for row in rows)),
            "security": (
                f"Source alerts: {sum(signals)}; agent attribution unverified; not a zero-risk assertion"
                if signals else "No verified risk feed; not a zero-risk assertion"
            ),
            "as_of": asset.collected_at.isoformat(), "source": asset.source,
        })
    return result


def coverage(estate: Estate) -> dict[str, int]:
    counts = Counter(row.evidence_kind for row in estate.evidence)
    return {kind: counts[kind] for kind in
            ("synthetic", "live", "snapshot", "unavailable", "unverified")}


def markdown_table(rows: Sequence[Mapping[str, object]]) -> str:
    if not rows:
        return "No evidence rows. This is not a zero-risk assertion."

    def cell(value: object) -> str:
        return html.escape(str(value)).replace("|", "&#124;").replace("\n", " ")

    columns = list(rows[0])
    lines = [
        "| " + " | ".join(cell(c) for c in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    lines.extend("| " + " | ".join(cell(row.get(c, "")) for c in columns) + " |" for row in rows)
    return "\n".join(lines)


def export_estate(estate: Estate, directory: Path) -> tuple[Path, Path]:
    """Export only normalized fields; never serialize SDK objects or HTTP bodies."""
    directory.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = directory / "estate.json", directory / "overview.csv"
    if json_path.exists() or csv_path.exists():
        raise FileExistsError("Export exists; choose a new output directory.")
    with json_path.open("x", encoding="utf-8") as stream:
        stream.write(estate.model_dump_json(indent=2))
    rows = overview(estate)
    with csv_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["asset"])
        writer.writeheader()
        # CSV consumers can interpret names as formulas even when quoted.
        writer.writerows({
            key: "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value
            for key, value in row.items()
        } for row in rows)
    return json_path, csv_path


def load_snapshot(path: Path) -> Estate:
    estate = Estate.model_validate(json.loads(path.read_text(encoding="utf-8")))
    return Estate(
        assets=tuple(asset.model_copy(update={
            "evidence_kind": "snapshot" if asset.evidence_kind == "live" else asset.evidence_kind,
        }) for asset in estate.assets),
        evidence=tuple(row.model_copy(update={
            "evidence_kind": "snapshot" if row.evidence_kind == "live" else row.evidence_kind,
        }) for row in estate.evidence),
    )
