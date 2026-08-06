from scripts.export_benchmark_api_schema import OUTPUT, render_schema


def test_committed_benchmark_api_schema_matches_pydantic_contract():
    assert OUTPUT.read_text(encoding="utf-8") == render_schema()