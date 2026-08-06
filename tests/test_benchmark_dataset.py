from __future__ import annotations

import json
from pathlib import Path

from src.benchmarking.evaluation import EvaluationCategory
from src.benchmarking.models import BenchmarkCase


def test_decision_dataset_covers_taxonomy_security_and_reliability():
    path = Path("experiments/datasets/hr-policy-decision-v1.json")
    cases = [BenchmarkCase.model_validate(item) for item in json.loads(path.read_text())]
    categories = {case.category for case in cases}

    assert categories == {category.value for category in EvaluationCategory}
    assert sum(case.case_id.startswith("gold-") for case in cases) >= 2
    assert any("Fail closed" in case.expected_behavior for case in cases)
    assert any("partial status" in case.expected_behavior for case in cases)
    assert all("SYNTH-" in source_id for case in cases for source_id in case.expected_source_ids)