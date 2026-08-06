"""Load-test safety guard and Locust CSV normalization."""

from __future__ import annotations

import csv
import os
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field


class LoadEndpointResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str
    name: str
    request_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    requests_per_second: float = Field(ge=0)
    p50_ms: float = Field(ge=0)
    p95_ms: float = Field(ge=0)
    p99_ms: float = Field(ge=0)


class LoadTestReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    workload_type: str = "load_test"
    source: str = "locust_csv"
    concurrency: int = Field(ge=1)
    spawn_rate: float = Field(gt=0)
    duration_seconds: int = Field(ge=1)
    endpoints: list[LoadEndpointResult]


def validate_load_target(target: str | None) -> str:
    """Allow localhost or a remote host confirmed by name; always reject prod."""
    if not target:
        raise ValueError("An explicit --host target is required")
    parsed = urlparse(target)
    hostname = parsed.hostname
    if parsed.scheme not in {"http", "https"} or not hostname:
        raise ValueError("Load target must be an absolute HTTP(S) URL")
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return target
    environment = os.getenv("LOAD_TEST_ENVIRONMENT", "").strip().lower()
    if environment in {"prod", "production"}:
        raise ValueError("Production load targets are prohibited")
    confirmation = os.getenv("LOAD_TEST_CONFIRM_TARGET", "")
    if confirmation != hostname:
        raise ValueError("Set LOAD_TEST_CONFIRM_TARGET to the exact remote hostname")
    return target


def import_locust_csv(
    path: Path, *, concurrency: int, spawn_rate: float, duration_seconds: int
) -> LoadTestReport:
    endpoints: list[LoadEndpointResult] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["Name"] == "Aggregated":
                continue
            endpoints.append(
                LoadEndpointResult(
                    method=row["Type"],
                    name=row["Name"],
                    request_count=int(row["Request Count"]),
                    failure_count=int(row["Failure Count"]),
                    requests_per_second=float(row["Requests/s"]),
                    p50_ms=float(row["50%"]),
                    p95_ms=float(row["95%"]),
                    p99_ms=float(row["99%"]),
                )
            )
    return LoadTestReport(
        concurrency=concurrency,
        spawn_rate=spawn_rate,
        duration_seconds=duration_seconds,
        endpoints=endpoints,
    )