from __future__ import annotations

from src.benchmarking.fingerprinting import fingerprint_files, fingerprint_json


def test_file_fingerprint_is_deterministic_and_content_sensitive(tmp_path):
    (tmp_path / "nested").mkdir()
    first = tmp_path / "nested" / "a.txt"
    first.write_text("alpha", encoding="utf-8")
    (tmp_path / "b.txt").write_text("beta", encoding="utf-8")

    baseline = fingerprint_files(tmp_path)
    assert baseline == fingerprint_files(tmp_path)
    first.write_text("changed", encoding="utf-8")
    assert fingerprint_files(tmp_path) != baseline


def test_json_fingerprint_uses_canonical_key_order():
    assert fingerprint_json({"b": 2, "a": 1}) == fingerprint_json({"a": 1, "b": 2})