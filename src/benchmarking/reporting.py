"""JSONL, JSON, and Markdown report writers for benchmark artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from src.benchmarking.models import AggregateReport, CaseResult, ExperimentManifest


def write_jsonl(path: Path, results: list[CaseResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(result.model_dump_json(by_alias=True) for result in results)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def write_report_json(
    path: Path, manifest: ExperimentManifest, report: AggregateReport
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "manifest": manifest.model_dump(mode="json"),
        "aggregate": report.model_dump(mode="json"),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_report_markdown(
    path: Path, manifest: ExperimentManifest, report: AggregateReport
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    latency = report.client_wall_time
    latency_rows = "Client wall-time metrics unavailable."
    if latency:
        latency_rows = "\n".join(
            [
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Minimum | {latency.minimum_ms:.2f} ms |",
                f"| Mean | {latency.mean_ms:.2f} ms |",
                f"| Standard deviation | {latency.standard_deviation_ms:.2f} ms |",
                f"| p50 | {latency.p50_ms:.2f} ms |",
                f"| p95 | {latency.p95_ms:.2f} ms |",
                f"| p99 | {latency.p99_ms:.2f} ms |",
                f"| Maximum | {latency.maximum_ms:.2f} ms |",
            ]
        )
    temperature_rows = ["| Temperature | Samples | p50 | p95 |", "| --- | ---: | ---: | ---: |"]
    for label, summary in (
        ("Cold", report.cold_client_wall_time),
        ("Warm", report.warm_client_wall_time),
    ):
        if summary:
            temperature_rows.append(
                f"| {label} | {summary.count} | {summary.p50_ms:.2f} ms | {summary.p95_ms:.2f} ms |"
            )
    if len(temperature_rows) == 2:
        temperature_rows.append("| Unspecified | 0 | n/a | n/a |")
    category_rows = ["| Category | Samples | Mean | p95 |", "| --- | ---: | ---: | ---: |"]
    for category, summary in report.by_category.items():
        category_rows.append(
            f"| `{category}` | {summary.count} | {summary.mean_ms:.2f} ms | {summary.p95_ms:.2f} ms |"
        )
    stage_rows = ["| Stage | Observations | Mean | p95 |", "| --- | ---: | ---: | ---: |"]
    for name, summary in report.by_stage.items():
        stage_rows.append(
            f"| `{name}` | {summary.count} | {summary.mean_ms:.2f} ms | {summary.p95_ms:.2f} ms |"
        )
    if len(stage_rows) == 2:
        stage_rows.append("| Unavailable | 0 | n/a | n/a |")
    activity_rows = [
        "| Activity type | Records | Elapsed observations | p50 | Input tokens | Output tokens | Reasoning tokens |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for activity_type, summary in report.by_activity_type.items():
        elapsed = summary.elapsed_ms
        activity_rows.append(
            f"| `{activity_type}` | {summary.record_count} | "
            f"{elapsed.count if elapsed else 0} | "
            f"{f'{elapsed.p50_ms:.2f} ms' if elapsed else 'n/a'} | "
            f"{summary.input_tokens} | {summary.output_tokens} | {summary.reasoning_tokens} |"
        )
    if len(activity_rows) == 2:
        activity_rows.append("| Unavailable | 0 | 0 | n/a | 0 | 0 | 0 |")
    warning = f"\n> {report.sample_warning}\n" if report.sample_warning else ""
    fixture_notice = ""
    if report.provenance.get("fixture_mode"):
        fixture_notice = (
            "\n> Synthetic fixture mode: timing values measure only local contract "
            "execution and are not Azure performance evidence.\n"
        )
    path.write_text(
        "\n".join(
            [
                f"# Experiment {manifest.experiment_id}",
                "",
                "Controlled development experiment; not production telemetry or a load test.",
                "",
                f"- Pattern: `{manifest.pattern}`",
                f"- Invocation: `{manifest.invocation_path}`",
                f"- Dataset: `{manifest.dataset_name}` version `{manifest.dataset_version}`",
                f"- Git commit: `{manifest.git_commit}` (dirty: `{manifest.dirty_worktree}`)",
                f"- Samples: `{report.count}`",
                f"- Success rate: `{report.success_rate:.1%}`",
                warning,
                fixture_notice,
                "## Client-observed latency",
                "",
                latency_rows,
                "",
                "## Cold and warm latency",
                "",
                "\n".join(temperature_rows),
                "",
                "## Latency by query category",
                "",
                "\n".join(category_rows),
                "",
                "## Instrumented stage observations",
                "",
                "\n".join(stage_rows),
                "",
                "## Service activity observations",
                "",
                "\n".join(activity_rows),
                "",
                "Each stage or activity duration is summarized as an independent observation. "
                "Parallel activity durations are never summed into a request critical path.",
            ]
        ),
        encoding="utf-8",
    )