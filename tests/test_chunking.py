"""Tests for fixed-size chunking with overlap."""

import pytest

from src.document_processing.chunking import fixed_size_chunking, TextChunk


def test_empty_text_returns_empty_list():
    assert fixed_size_chunking("") == []


def test_invalid_size_raises():
    with pytest.raises(ValueError):
        fixed_size_chunking("abc", size=0)


def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        fixed_size_chunking("abc", size=4, overlap=4)


def test_chunking_no_overlap_and_indices_and_ids():
    text = "abcdefghij"
    chunks = fixed_size_chunking(text, size=4, overlap=0, document_id="doc")
    assert [c.text for c in chunks] == ["abcd", "efgh", "ij"]
    assert [c.chunk_index for c in chunks] == [0, 1, 2]

    for idx, c in enumerate(chunks):
        parts = c.chunk_id.split(":")
        assert parts[0] == "doc"
        assert parts[1] == str(idx)
        assert len(parts[2]) == 32
        assert isinstance(c, TextChunk)


def test_chunking_with_overlap():
    text = "abcdefghij"
    # size=4, overlap=2 -> step=2
    chunks = fixed_size_chunking(text, size=4, overlap=2, document_id="d1")
    # expected starts: 0:'abcd', 2:'cdef', 4:'efgh', 6:'ghij'
    assert [c.text for c in chunks] == ["abcd", "cdef", "efgh", "ghij"]
    assert [c.chunk_index for c in chunks] == [0, 1, 2, 3]


def test_chunk_ids_are_deterministic():
    text = "x" * 30
    a = fixed_size_chunking(text, size=10, overlap=2, document_id="same")
    b = fixed_size_chunking(text, size=10, overlap=2, document_id="same")
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
