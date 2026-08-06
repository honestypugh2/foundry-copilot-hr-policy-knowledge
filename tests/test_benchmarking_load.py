from __future__ import annotations

from pathlib import Path

import pytest

from src.benchmarking.load import import_locust_csv, validate_load_target


def test_load_target_guard_requires_explicit_nonproduction_confirmation(monkeypatch):
    assert validate_load_target("http://localhost:8000") == "http://localhost:8000"
    with pytest.raises(ValueError, match="explicit"):
        validate_load_target(None)
    with pytest.raises(ValueError, match="exact remote hostname"):
        validate_load_target("https://test.example.com")
    monkeypatch.setenv("LOAD_TEST_CONFIRM_TARGET", "test.example.com")
    monkeypatch.setenv("LOAD_TEST_ENVIRONMENT", "test")
    assert validate_load_target("https://test.example.com") == "https://test.example.com"
    monkeypatch.setenv("LOAD_TEST_ENVIRONMENT", "production")
    with pytest.raises(ValueError, match="prohibited"):
        validate_load_target("https://test.example.com")


def test_locust_csv_import_stays_separate_from_experiment_results(tmp_path: Path):
    stats = tmp_path / "smoke_stats.csv"
    stats.write_text(
        "Type,Name,Request Count,Failure Count,Requests/s,50%,95%,99%\n"
        "POST,POST /api/chat,10,1,2.5,100,180,200\n"
        "POST,Aggregated,10,1,2.5,100,180,200\n",
        encoding="utf-8",
    )
    report = import_locust_csv(
        stats, concurrency=2, spawn_rate=1, duration_seconds=10
    )
    assert report.workload_type == "load_test"
    assert len(report.endpoints) == 1
    assert report.endpoints[0].failure_count == 1
    assert report.endpoints[0].p95_ms == 180