"""Tests for document ingestion helpers."""

import pytest
from src.document_processing.document_ingestion import (
    extract_policy_number,
    categorize_policy,
    generate_document_id,
)


class TestExtractPolicyNumber:
    def test_standard_format(self):
        assert extract_policy_number("51350 - Types of Leave_ Paid Time Off (PTO).docx") == "51350"

    def test_five_digit(self):
        assert extract_policy_number("50715 - Hours Worked.docx") == "50715"

    def test_six_digit(self):
        assert extract_policy_number("101100 - Blood Borne Pathogens.doc") == "101100"

    def test_no_number(self):
        assert extract_policy_number("General Guidelines.docx") == ""


class TestCategorizePolicy:
    def test_leave_category(self):
        assert categorize_policy("Types of Leave_ Paid Time Off") == "leave"

    def test_hiring_category(self):
        assert categorize_policy("Hiring_ Probationary Period") == "hiring"

    def test_ethics_category(self):
        assert categorize_policy("Code of Ethics and Related Matters") == "ethics"

    def test_safety_category(self):
        assert categorize_policy("Blood Borne Pathogens Introduction") == "safety"

    def test_compensation_category(self):
        assert categorize_policy("Hours Worked and Pay Administration") == "compensation"

    def test_general_fallback(self):
        assert categorize_policy("Some random topic") == "general"


class TestGenerateDocumentId:
    def test_deterministic(self):
        id1 = generate_document_id("/path/to/file.docx")
        id2 = generate_document_id("/path/to/file.docx")
        assert id1 == id2

    def test_different_files(self):
        id1 = generate_document_id("/path/to/file1.docx")
        id2 = generate_document_id("/path/to/file2.docx")
        assert id1 != id2
