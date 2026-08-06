from __future__ import annotations

import json
from pathlib import Path

from src.benchmarking.cli import main
from tests.test_benchmarking_phase1 import _manifest


def test_cli_emits_versioned_offline_artifacts(tmp_path: Path):
    manifest = _manifest().model_copy(
        update={
            "experiment_id": "cli-smoke",
            "warmup_count": 1,
            "measured_repetitions": 2,
        }
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(), encoding="utf-8")
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "pto-location",
                    "query": "Where is the PTO policy?",
                    "category": "document_location",
                    "expected_behavior": "retrieve",
                    "expected_source_ids": ["50010"],
                }
            ]
        ),
        encoding="utf-8",
    )
    fixtures_path = tmp_path / "fixtures.json"
    fixtures_path.write_text(
        json.dumps(
            {
                "Where is the PTO policy?": [
                    {
                        "policy_number": "50010",
                        "title": "Paid Time Off",
                        "score": 3.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "reports"

    assert (
        main(
            [
                "--manifest",
                str(manifest_path),
                "--cases",
                str(cases_path),
                "--fixture-responses",
                str(fixtures_path),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    rows = [
        json.loads(line)
        for line in (output_dir / "cli-smoke.results.jsonl").read_text().splitlines()
    ]
    assert len(rows) == 2
    assert all(row["local_metrics"]["recall_at_k"] == 1.0 for row in rows)
    aggregate = json.loads(
        (output_dir / "cli-smoke.report.json").read_text(encoding="utf-8")
    )["aggregate"]
    assert aggregate["provenance"]["fixture_mode"] is True
    assert aggregate["provenance"]["workload_type"] == "controlled_experiment"
    markdown = (output_dir / "cli-smoke.report.md").read_text(encoding="utf-8")
    assert "Controlled development experiment" in markdown
    assert "not Azure performance evidence" in markdown
    assert json.loads(
        (output_dir / "cli-smoke.manifest.json").read_text(encoding="utf-8")
    )["schema_version"] == "1.0"