from __future__ import annotations

import csv
import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_CURATED_CSV = _ROOT / "eval" / "datasets" / "hr_qa_testset.csv"
_HOSTED_JSONL = (
    _ROOT
    / "src"
    / "hosted_agent"
    / ".foundry"
    / "datasets"
    / "hr-policy-agent-curated-v1.jsonl"
)
_HOSTED_EVAL_CONFIG = _ROOT / "src" / "hosted_agent" / "eval-builtins.yaml"


def test_hosted_eval_dataset_adapts_every_curated_case() -> None:
    with _CURATED_CSV.open(newline="", encoding="utf-8") as csv_file:
        curated_rows = list(csv.DictReader(csv_file))
    with _HOSTED_JSONL.open(encoding="utf-8") as jsonl_file:
        hosted_rows = [json.loads(line) for line in jsonl_file if line.strip()]

    assert len(hosted_rows) == len(curated_rows) == 13
    for curated, hosted in zip(curated_rows, hosted_rows, strict=True):
        assert hosted.keys() == {
            "query",
            "expected_behavior",
            "ground_truth",
            "context",
        }
        assert hosted["query"] == curated["question"]
        assert hosted["ground_truth"] == curated["reference_answer"]
        assert hosted["context"] == curated["tags"]
        assert hosted["expected_behavior"].strip()


def test_hosted_eval_config_uses_curated_data_and_builtin_evaluators() -> None:
    config = _HOSTED_EVAL_CONFIG.read_text(encoding="utf-8")

    assert 'version: "2"' in config
    assert "hr-policy-agent-curated-v1.jsonl" in config
    for evaluator in (
        "builtin.relevance",
        "builtin.task_adherence",
        "builtin.intent_resolution",
    ):
        assert f"- {evaluator}" in config
    assert "builtin.tool_call_accuracy" not in config


def test_custom_rubric_matches_hr_policy_retrieval_contract() -> None:
    rubric_path = (
        _ROOT
        / "src"
        / "hosted_agent"
        / "evaluators"
        / "hr-policy-agent-curated-builtins-v1"
        / "rubric_dimensions.json"
    )
    dimensions = json.loads(rubric_path.read_text(encoding="utf-8"))
    dimension_ids = {dimension["id"] for dimension in dimensions}

    assert dimension_ids == {
        "retrieval_first",
        "evidence_grounding",
        "exact_policy_citation",
        "source_footer",
        "correct_abstention",
        "directness_and_precision",
    }