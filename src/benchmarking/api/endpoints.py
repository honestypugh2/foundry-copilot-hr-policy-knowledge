"""Versioned read-only endpoints backed by normalized local artifacts."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.benchmarking.api.models import (
    CapabilityResponse,
    ComparisonResponse,
    ExperimentListResponse,
    ExperimentSummary,
    NativeLinkResponse,
    PatternEvidence,
    PatternSummaryResponse,
)

router = APIRouter(prefix="/api/benchmarking", tags=["benchmarking"])
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")
_DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "experiments" / "reports"
_PATTERNS = {"A", "A2", "B", "C", "Hosted"}
_PATTERN_BOUNDARIES = {
    "A": ("automated direct Search; Copilot Studio capture is external", "client and Search diagnostics"),
    "A2": ("direct Knowledge Base adapter or external Copilot Studio import", "KB activity when exposed; Copilot orchestration external"),
    "B": ("automated Foundry Agent invocation", "agent spans; MCP internals unavailable unless emitted"),
    "C": ("automated deterministic lookup", "lookup boundary; upstream router model tracked separately"),
    "Hosted": ("automated Agent Framework invocation", "Agent Framework spans and container request timing"),
}
_LINK_ENV = {
    "application_insights": ("BENCHMARK_LINK_APPLICATION_INSIGHTS", "Preview"),
    "grafana": ("BENCHMARK_LINK_GRAFANA", "GA"),
    "foundry": ("BENCHMARK_LINK_FOUNDRY", "provider-dependent"),
    "search": ("BENCHMARK_LINK_SEARCH", "GA"),
    "load_testing": ("BENCHMARK_LINK_LOAD_TESTING", "GA"),
    "cost_management": ("BENCHMARK_LINK_COST_MANAGEMENT", "GA"),
}


def _root() -> Path:
    return Path(os.getenv("BENCHMARK_ARTIFACT_DIR", _DEFAULT_ROOT)).resolve()


def _artifact_paths() -> list[Path]:
    root = _root()
    if not root.is_dir():
        return []
    legacy = [
        path
        for path in root.glob("*.json")
        if not path.name.endswith((".manifest.json", ".report.json"))
    ]
    canonical = list(root.rglob("*.report.json"))
    return sorted({*legacy, *canonical})


def _load(experiment_id: str) -> dict[str, Any]:
    if not _SAFE_ID.fullmatch(experiment_id):
        raise HTTPException(status_code=400, detail="Invalid experiment ID")
    for path in _artifact_paths():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("manifest", {}).get("experiment_id") == experiment_id:
            return payload
    raise HTTPException(status_code=404, detail="Experiment not found")


def _summary(payload: dict[str, Any]) -> ExperimentSummary:
    manifest = payload["manifest"]
    aggregate = payload["aggregate"]
    latency = aggregate.get("client_wall_time") or {}
    provenance = aggregate.get("provenance", {})
    return ExperimentSummary(
        schema_version=aggregate["schema_version"],
        experiment_id=manifest["experiment_id"],
        pattern=manifest["pattern"],
        dataset_name=manifest["dataset_name"],
        dataset_version=manifest["dataset_version"],
        git_commit=manifest["git_commit"],
        corpus_fingerprint=manifest.get("corpus_fingerprint"),
        index_fingerprint=manifest.get("index_fingerprint"),
        model_deployment=manifest.get("model_deployment"),
        created_at=manifest["created_at"],
        count=aggregate["count"],
        success_rate=aggregate["success_rate"],
        latency_p50_ms=latency.get("p50_ms"),
        latency_p95_ms=latency.get("p95_ms"),
        latency_p99_ms=latency.get("p99_ms"),
        quality=provenance.get("quality"),
        security_pass_rate=provenance.get("security_pass_rate"),
        estimated_variable_cost=provenance.get("estimated_variable_cost"),
        sample_warning=aggregate.get("sample_warning"),
        provenance=provenance,
    )


@router.get("/capabilities", response_model=CapabilityResponse)
def capabilities() -> CapabilityResponse:
    artifact_count = len(_artifact_paths())
    return CapabilityResponse.model_validate(
        {
            "schema_version": "1.0",
            "source_version": "local-artifacts-v1",
            "capabilities": [
                {
                    "name": "experiments",
                    "status": "available" if artifact_count else "not_configured",
                    "freshness": "file-backed",
                    "release_status": "GA",
                    "source_version": "artifact-schema-1.0",
                    "artifact_count": artifact_count,
                },
                {
                    "name": "production_telemetry",
                    "status": (
                        "available"
                        if os.getenv("BENCHMARK_LINK_APPLICATION_INSIGHTS")
                        else "not_configured"
                    ),
                    "freshness": None,
                    "release_status": "provider-dependent",
                    "source_version": "genai-otel",
                    "artifact_count": 0,
                },
            ],
        }
    )


@router.get("/experiments", response_model=ExperimentListResponse)
def experiments() -> ExperimentListResponse:
    items = [
        _summary(json.loads(path.read_text(encoding="utf-8")))
        for path in _artifact_paths()
    ]
    return ExperimentListResponse(
        items=sorted(items, key=lambda item: item.created_at, reverse=True)
    )


@router.get("/experiments/{experiment_id}")
def experiment(experiment_id: str) -> dict[str, Any]:
    return _load(experiment_id)


@router.get("/comparisons", response_model=ComparisonResponse)
def comparison(
    baseline: str = Query(min_length=1), candidate: str = Query(min_length=1)
) -> ComparisonResponse:
    baseline_summary = _summary(_load(baseline))
    candidate_summary = _summary(_load(candidate))
    incompatibility_reasons = []
    for field in ("dataset_name", "dataset_version", "corpus_fingerprint", "index_fingerprint"):
        if getattr(baseline_summary, field) != getattr(candidate_summary, field):
            incompatibility_reasons.append(f"{field} differs")
    metrics = ("latency_p95_ms", "quality", "success_rate", "estimated_variable_cost")
    return ComparisonResponse(
        baseline=baseline_summary,
        candidate=candidate_summary,
        compatible_scope=not incompatibility_reasons,
        incompatibility_reasons=incompatibility_reasons,
        deltas={
            metric: _delta(
                getattr(baseline_summary, metric),
                getattr(candidate_summary, metric),
            )
            for metric in metrics
        },
    )


@router.get("/patterns/{pattern}/summary", response_model=PatternSummaryResponse)
def pattern_summary(pattern: str) -> PatternSummaryResponse:
    if pattern not in _PATTERNS:
        raise HTTPException(status_code=404, detail="Unknown pattern")
    matching = [item for item in experiments().items if item.pattern == pattern]
    automation, telemetry = _PATTERN_BOUNDARIES[pattern]
    return PatternSummaryResponse(
        item=PatternEvidence(
            pattern=pattern,  # type: ignore[arg-type]
            automation_boundary=automation,
            telemetry_boundary=telemetry,
            experiment_count=len(matching),
            latest=matching[0] if matching else None,
        )
    )


@router.get(
    "/links/{resource_type}/{source_id}",
    response_model=NativeLinkResponse,
)
def native_link(resource_type: str, source_id: str) -> NativeLinkResponse:
    if resource_type not in _LINK_ENV or not _SAFE_ID.fullmatch(source_id):
        raise HTTPException(status_code=404, detail="Unknown link target")
    env_name, release_status = _LINK_ENV[resource_type]
    url = os.getenv(env_name)
    if url and not url.startswith("https://"):
        return NativeLinkResponse(
            resource_type=resource_type,
            source_id=source_id,
            status="degraded",
            release_status=release_status,
        )
    return NativeLinkResponse(
        resource_type=resource_type,
        source_id=source_id,
        status="available" if url else "not_configured",
        authoritative_url=url,
        release_status=release_status,
    )


def _delta(baseline: float | None, candidate: float | None) -> dict[str, float | None]:
    if baseline is None or candidate is None:
        return {"absolute": None, "relative": None}
    absolute = candidate - baseline
    return {
        "absolute": absolute,
        "relative": absolute / baseline if baseline != 0 else None,
    }