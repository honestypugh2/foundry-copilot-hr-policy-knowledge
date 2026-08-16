"""Versioned read-only endpoints backed by normalized local artifacts."""

from __future__ import annotations

import json
import os
import re
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query

from src.benchmarking.capabilities import capability_inventory
from src.benchmarking.copilot_credits import estimate_pattern
from src.benchmarking.api.models import (
    CapabilityResponse,
    ComparisonResponse,
    Delta,
    DecisionEvidence,
    DecisionResponse,
    DecisionScope,
    ExperimentListResponse,
    ExperimentSummary,
    NativeLinkResponse,
    PatternEvidence,
    PatternSummaryResponse,
)
from src.benchmarking.decision import (
    DecisionCandidate,
    SloThresholds,
    pareto_frontier,
    qualify_slos,
)
from src.benchmarking.models import ExperimentManifest

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
# Scope captures what makes two measurements comparable (data + boundary + harness
# knobs). git_commit/dirty_worktree are reproducibility/release concerns, not
# comparability — dirty_worktree still gates release-readiness in _publication_blockers.
_COMPARISON_SCOPE_FIELDS = (
    "schema_version",
    "runner_version",
    "dataset_name",
    "dataset_version",
    "corpus_fingerprint",
    "index_fingerprint",
    "region",
    "client_location",
    "warmup_count",
    "measured_repetitions",
    "concurrency",
    "timeout_seconds",
    "random_seed",
    "pricing_profile",
)
_COMPARISON_SCOPE_VERSION = "comparison-scope-v3"
# Derived (non-manifest) scope fields appended by _scope_values.
_DERIVED_SCOPE_FIELDS = ("measurement_boundary_class",)


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


def _prefer_path(candidate: Path, current: Path) -> bool:
    """Prefer the canonical decision-system tree, then the most recently written file.

    The same ``experiment_id`` can legitimately exist in more than one report tree
    (for example an older publication draft and the canonical decision-system run).
    The workbench must expose exactly one record per experiment, so collapse
    duplicates to the decision-system artifact and fall back to newest on ties.
    """
    candidate_canonical = "decision-system-" in candidate.as_posix()
    current_canonical = "decision-system-" in current.as_posix()
    if candidate_canonical != current_canonical:
        return candidate_canonical
    return candidate.stat().st_mtime >= current.stat().st_mtime


def _load(experiment_id: str) -> dict[str, Any]:
    if not _SAFE_ID.fullmatch(experiment_id):
        raise HTTPException(status_code=400, detail="Invalid experiment ID")
    for path in _artifact_paths():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("manifest", {}).get("experiment_id") == experiment_id:
            return _attach_copilot_credits(payload)
    raise HTTPException(status_code=404, detail="Experiment not found")


_REPO_ROOT = Path(__file__).resolve().parents[3]
_CREDIT_RATE_CARD = (
    _REPO_ROOT
    / "experiments/pricing/copilot-studio-credits-standard-harness-2026-08-01.json"
)
_CREDIT_FEATURE_MIX = (
    _REPO_ROOT / "experiments/pricing/copilot-studio-credits-feature-mix.json"
)


def _attach_copilot_credits(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach a deterministic Credits estimate for Copilot Studio front-door runs."""
    aggregate = payload.get("aggregate") or {}
    provenance = aggregate.get("provenance") or {}
    if provenance.get("measurement_boundary") != "copilot_studio_direct_line":
        return payload
    pattern = str(payload.get("manifest", {}).get("pattern") or "")
    messages = int(aggregate.get("count") or 0) or 1
    try:
        estimate = estimate_pattern(
            pattern,
            rate_card_path=_CREDIT_RATE_CARD,
            feature_mix_path=_CREDIT_FEATURE_MIX,
            messages=messages,
        )
    except (ValueError, FileNotFoundError):
        return payload
    provenance["copilot_credits"] = {
        "credits_per_message": estimate.credits_per_message,
        "estimated_total_credits": estimate.estimated_total_credits,
        "messages": estimate.messages,
        "byo_foundry_tokens": estimate.byo_foundry_tokens,
        "has_uncertain_events": estimate.has_uncertain_events,
        "rate_profile": estimate.rate_profile,
    }
    aggregate["provenance"] = provenance
    return payload


def _summary(payload: dict[str, Any]) -> ExperimentSummary:
    manifest = payload["manifest"]
    aggregate = payload["aggregate"]
    latency = aggregate.get("client_wall_time") or {}
    provenance = aggregate.get("provenance", {})
    return ExperimentSummary(
        schema_version=aggregate["schema_version"],
        experiment_id=manifest["experiment_id"],
        pattern=manifest["pattern"],
        retrieval_mode=manifest["retrieval_mode"],
        dataset_name=manifest["dataset_name"],
        dataset_version=manifest["dataset_version"],
        git_commit=manifest["git_commit"],
        corpus_fingerprint=manifest.get("corpus_fingerprint"),
        index_fingerprint=manifest.get("index_fingerprint"),
        model_deployment=manifest.get("model_deployment"),
        answer_model=manifest.get("answer_model"),
        created_at=manifest["created_at"],
        count=aggregate["count"],
        success_rate=aggregate.get("success_rate"),
        latency_p50_ms=latency.get("p50_ms"),
        latency_p95_ms=latency.get("p95_ms"),
        latency_p99_ms=latency.get("p99_ms"),
        quality=provenance.get("quality"),
        security_pass_rate=provenance.get("security_pass_rate"),
        estimated_variable_cost=provenance.get("estimated_variable_cost"),
        sample_warning=aggregate.get("sample_warning"),
        comparison_scope=_comparison_scope(payload),
        provenance=provenance,
    )


def _boundary_class(invocation_path: str) -> str:
    """Group invocation paths into latency-comparable measurement classes.

    Runs in different classes (e.g. Copilot front door vs deployed Foundry
    agent) include different hops, so their latency is never ranked together.
    """
    prefixes = {
        "copilot_studio_direct_line:": "copilot_front_door",
        "foundry_hosted_agent:": "deployed_foundry_agent",
        "agent_framework_local:": "agent_framework_local",
    }
    for prefix, label in prefixes.items():
        if invocation_path.startswith(prefix):
            return label
    exact = {
        "direct_search_sdk": "direct_search",
        "direct_search_fixture": "direct_search",
        "direct_knowledge_base_retrieve": "direct_knowledge_base",
        "foundry_responses_agent_mcp": "foundry_responses",
        "deterministic_lookup": "deterministic_lookup",
        "fixture": "fixture",
    }
    return exact.get(invocation_path, invocation_path)


def _scope_values(payload: dict[str, Any]) -> dict[str, Any]:
    manifest = ExperimentManifest.model_validate(payload["manifest"])
    values = manifest.model_dump(
        mode="json",
        include=set(_COMPARISON_SCOPE_FIELDS),
    )
    values["measurement_boundary_class"] = _boundary_class(manifest.invocation_path)
    return values


def _comparison_scope(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        {
            "algorithm": _COMPARISON_SCOPE_VERSION,
            "values": _scope_values(payload),
        },
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()[:24]


@router.get("/capabilities", response_model=CapabilityResponse)
def capabilities() -> CapabilityResponse:
    artifact_count = len(experiments().items)
    return CapabilityResponse(
        source_version="microsoft-asset-reuse-matrix-2026-08-03",
        capabilities=capability_inventory(artifact_count),
    )


@router.get("/experiments", response_model=ExperimentListResponse)
def experiments() -> ExperimentListResponse:
    by_id: dict[str, tuple[Path, ExperimentSummary]] = {}
    for path in _artifact_paths():
        summary = _summary(_attach_copilot_credits(json.loads(path.read_text(encoding="utf-8"))))
        key = summary.experiment_id or path.as_posix()
        existing = by_id.get(key)
        if existing is None or _prefer_path(path, existing[0]):
            by_id[key] = (path, summary)
    items = [summary for _, summary in by_id.values()]
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
    baseline_payload = _load(baseline)
    candidate_payload = _load(candidate)
    baseline_summary = _summary(baseline_payload)
    candidate_summary = _summary(candidate_payload)
    incompatibility_reasons = []
    baseline_scope = _scope_values(baseline_payload)
    candidate_scope = _scope_values(candidate_payload)
    for field in (*_COMPARISON_SCOPE_FIELDS, *_DERIVED_SCOPE_FIELDS):
        if baseline_scope[field] != candidate_scope[field]:
            incompatibility_reasons.append(f"{field} differs")
    metrics = ("latency_p95_ms", "quality", "success_rate", "estimated_variable_cost")
    # Each metric is only comparable when the dimensions it actually depends on match.
    metric_requirements: dict[str, tuple[str, ...]] = {
        "latency_p95_ms": ("measurement_boundary_class",),
        "success_rate": ("measurement_boundary_class",),
        "quality": ("dataset_name", "dataset_version"),
        "estimated_variable_cost": ("measurement_boundary_class", "pricing_profile"),
    }
    deltas: dict[str, Delta] = {}
    for metric in metrics:
        differing = [field for field in metric_requirements[metric] if baseline_scope[field] != candidate_scope[field]]
        if differing:
            caveat: str | None = "Not comparable across " + ", ".join(field.replace("_", " ") for field in differing)
        elif metric == "quality" and baseline_summary.answer_model != candidate_summary.answer_model:
            caveat = f"Model differs ({baseline_summary.answer_model or 'n/a'} vs {candidate_summary.answer_model or 'n/a'}) — quality reflects the whole solution, model included"
        else:
            caveat = None
        deltas[metric] = _delta(
            getattr(baseline_summary, metric),
            getattr(candidate_summary, metric),
            comparable=not differing,
            caveat=caveat,
        )
    return ComparisonResponse(
        baseline=baseline_summary,
        candidate=candidate_summary,
        compatible_scope=not incompatibility_reasons,
        incompatibility_reasons=incompatibility_reasons,
        deltas=deltas,
    )


@router.get("/decisions", response_model=DecisionResponse)
def decisions(
    goal: Literal["quality", "balanced", "speed"] = "balanced",
    scope: str | None = Query(default=None, pattern=r"^[a-f0-9]{24}$"),
    minimum_quality: float = Query(default=0.85, ge=0, le=1),
    maximum_latency_p95_ms: float = Query(default=30000, ge=0),
    minimum_success_rate: float = Query(default=0.99, ge=0, le=1),
    minimum_security_pass_rate: float = Query(default=1.0, ge=0, le=1),
    maximum_estimated_variable_cost: float = Query(default=0.05, ge=0),
) -> DecisionResponse:
    payloads = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in _artifact_paths()
    ]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for payload in payloads:
        grouped.setdefault(_comparison_scope(payload), []).append(payload)
    available_scopes = [
        DecisionScope(
            scope_id=scope_id,
            experiment_ids=sorted(item["manifest"]["experiment_id"] for item in items),
        )
        for scope_id, items in sorted(grouped.items())
    ]
    comparable_scopes = {
        scope_id: items for scope_id, items in grouped.items() if len(items) >= 2
    }
    selected_scope = scope
    blockers: list[str] = []
    if selected_scope and selected_scope not in comparable_scopes:
        blockers.append("Selected scope does not contain at least two compatible experiments.")
        selected_scope = None
    elif not selected_scope and len(comparable_scopes) == 1:
        selected_scope = next(iter(comparable_scopes))
    elif not selected_scope and len(comparable_scopes) > 1:
        blockers.append("Multiple comparable scopes are available; select one explicitly.")
    elif not selected_scope:
        blockers.append("At least two compatible experiments are required for a decision.")

    thresholds = SloThresholds(
        minimum_quality=minimum_quality,
        maximum_latency_p95_ms=maximum_latency_p95_ms,
        minimum_success_rate=minimum_success_rate,
        minimum_security_pass_rate=minimum_security_pass_rate,
        maximum_estimated_variable_cost=maximum_estimated_variable_cost,
    )
    if not selected_scope:
        return DecisionResponse(
            goal=goal,
            thresholds=thresholds,
            available_scopes=available_scopes,
            selection_method=_selection_method(goal),
            blockers=blockers,
        )

    selected_payloads = comparable_scopes[selected_scope]
    summaries = [_summary(payload) for payload in selected_payloads]
    candidates = [
        DecisionCandidate(
            configuration_id=summary.experiment_id,
            quality=summary.quality,
            latency_p95_ms=summary.latency_p95_ms,
            success_rate=summary.success_rate,
            security_pass_rate=summary.security_pass_rate,
            estimated_variable_cost=summary.estimated_variable_cost,
            comparison_scope=selected_scope,
        )
        for summary in summaries
    ]
    frontier = pareto_frontier(candidates)
    qualifications = {
        item.configuration_id: item for item in qualify_slos(candidates, thresholds)
    }
    evidence: list[DecisionEvidence] = []
    publishable_ids: list[str] = []
    for payload, summary in zip(selected_payloads, summaries, strict=True):
        qualification = qualifications[summary.experiment_id]
        publication_blockers = _publication_blockers(payload, summary)
        publication_ready = not publication_blockers
        if qualification.qualified and publication_ready and summary.experiment_id in frontier:
            publishable_ids.append(summary.experiment_id)
        evidence.append(
            DecisionEvidence(
                experiment_id=summary.experiment_id,
                pattern=summary.pattern,
                qualified=qualification.qualified,
                qualification_failures=qualification.failures,
                on_pareto_frontier=summary.experiment_id in frontier,
                publication_ready=publication_ready,
                publication_blockers=publication_blockers,
            )
        )
    recommended = _recommend(goal, summaries, publishable_ids)
    leading_id: str | None = None
    leading_reason: str | None = None
    if not recommended:
        blockers.append("No compatible configuration passes all SLO and release-readiness gates.")
        complete_ids = {
            summary.experiment_id
            for summary in summaries
            if summary.quality is not None
            and summary.latency_p95_ms is not None
            and summary.estimated_variable_cost is not None
        }
        qualified_ids = [
            item.experiment_id
            for item in evidence
            if item.qualified and item.experiment_id in complete_ids
        ]
        frontier_ids = [eid for eid in frontier if eid in complete_ids]
        for tier in (qualified_ids, frontier_ids, sorted(complete_ids)):
            leading_id = _recommend(goal, summaries, tier)
            if leading_id:
                break
        if leading_id:
            lead = next(item for item in evidence if item.experiment_id == leading_id)
            if lead.qualified and lead.publication_blockers:
                leading_reason = "Clears every SLO; pending release sign-off — " + "; ".join(
                    lead.publication_blockers
                )
            elif lead.qualified:
                leading_reason = "Clears every SLO gate"
            elif lead.qualification_failures:
                leading_reason = f"Best on {goal}; not yet SLO-qualified — " + "; ".join(
                    lead.qualification_failures
                )
            else:
                leading_reason = f"Best available on {goal}"
    return DecisionResponse(
        goal=goal,
        thresholds=thresholds,
        selected_scope=selected_scope,
        available_scopes=available_scopes,
        evidence=evidence,
        frontier_experiment_ids=frontier,
        recommended_experiment_id=recommended,
        leading_experiment_id=leading_id,
        leading_reason=leading_reason,
        selection_method=_selection_method(goal),
        blockers=blockers,
    )


@router.get("/patterns/{pattern}/summary", response_model=PatternSummaryResponse)
def pattern_summary(pattern: str) -> PatternSummaryResponse:
    if pattern not in _PATTERNS:
        raise HTTPException(status_code=404, detail="Unknown pattern")
    matching = [item for item in experiments().items if item.pattern == pattern]
    automation, telemetry = _PATTERN_BOUNDARIES[pattern]
    measured = [
        item
        for item in matching
        if item.git_commit != "synthetic" and item.provenance.get("fixture_mode") is not True
    ]
    evidence_status = (
        "measured" if measured else "fixture_only" if matching else "run_required"
    )
    return PatternSummaryResponse(
        item=PatternEvidence(
            pattern=pattern,  # type: ignore[arg-type]
            automation_boundary=automation,
            telemetry_boundary=telemetry,
            implementation_status="implemented",
            evidence_status=evidence_status,
            experiment_count=len(matching),
            latest=(measured or matching or [None])[0],
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


def _delta(baseline: float | None, candidate: float | None, *, comparable: bool = True, caveat: str | None = None) -> Delta:
    if baseline is None or candidate is None:
        return Delta(comparable=comparable, caveat=caveat)
    absolute = candidate - baseline
    return Delta(
        absolute=absolute,
        relative=absolute / baseline if baseline != 0 else None,
        comparable=comparable,
        caveat=caveat,
    )


def _publication_blockers(
    payload: dict[str, Any], summary: ExperimentSummary
) -> list[str]:
    blockers: list[str] = []
    manifest = ExperimentManifest.model_validate(payload["manifest"])
    if manifest.dirty_worktree:
        blockers.append("dirty worktree")
    if summary.sample_warning:
        blockers.append(summary.sample_warning)
    if summary.provenance.get("synthetic") is True or manifest.git_commit == "synthetic":
        blockers.append("synthetic evidence")
    aggregate = payload["aggregate"]
    if summary.provenance.get("measurement_boundary") != "copilot_studio_direct_line":
        blockers.append("Copilot Studio front-door evidence required")
    if not aggregate.get("quality_by_category"):
        blockers.append("category-level deterministic quality required")
    if not aggregate.get("rate_confidence_intervals"):
        blockers.append("rate confidence intervals required")
    required_counts = (
        "success_count",
        "partial_count",
        "error_count",
        "timeout_count",
        "throttle_count",
    )
    if any(field not in aggregate for field in required_counts):
        blockers.append("explicit outcome counts required")
    if summary.quality is None or summary.security_pass_rate is None:
        blockers.append("deterministic quality and security evidence required")
    if summary.provenance.get("evaluation_release_ready") is False:
        blockers.extend(summary.provenance.get("evaluation_release_blockers") or [
            "native Copilot Studio evaluation contains nondecisive results"
        ])
    if summary.estimated_variable_cost is None:
        blockers.append("estimated variable cost required")
    return blockers


def _selection_method(goal: str) -> str:
    if goal == "quality":
        return "highest quality, then lowest p95 latency and variable cost"
    if goal == "speed":
        return "lowest p95 latency, then highest quality and lowest variable cost"
    return "minimum equal-weight normalized distance to the quality, latency, and cost ideal"


def _recommend(
    goal: str,
    summaries: list[ExperimentSummary],
    eligible_ids: list[str],
) -> str | None:
    eligible = [item for item in summaries if item.experiment_id in eligible_ids]
    if not eligible:
        return None
    complete = [(item, _decision_values(item)) for item in eligible]
    if goal == "quality":
        return min(
            complete,
            key=lambda pair: (-pair[1][0], pair[1][1], pair[1][2]),
        )[0].experiment_id
    if goal == "speed":
        return min(
            complete,
            key=lambda pair: (pair[1][1], -pair[1][0], pair[1][2]),
        )[0].experiment_id
    metrics = (
        [values[0] for _, values in complete],
        [values[1] for _, values in complete],
        [values[2] for _, values in complete],
    )
    ranges = [(min(values), max(values)) for values in metrics]

    def distance(values: tuple[float, float, float]) -> float:
        normalized = []
        for index, value in enumerate(values):
            low, high = ranges[index]
            normalized.append(0.0 if high == low else (value - low) / (high - low))
        quality_distance = 1 - normalized[0]
        return quality_distance**2 + normalized[1] ** 2 + normalized[2] ** 2

    return min(
        complete,
        key=lambda pair: (distance(pair[1]), pair[0].experiment_id),
    )[0].experiment_id


def _decision_values(item: ExperimentSummary) -> tuple[float, float, float]:
    if (
        item.quality is None
        or item.latency_p95_ms is None
        or item.estimated_variable_cost is None
    ):
        raise ValueError("Recommendation candidate has incomplete decision metrics")
    return item.quality, item.latency_p95_ms, item.estimated_variable_cost