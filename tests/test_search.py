"""Tests for search service and glossary expansion."""

import pytest
from azure.identity import AzureCliCredential, DefaultAzureCredential

from src.search.integrated_vectorization_search import IntegratedVectorizationSearchService
from src.search.search_service import HRPolicySearchService
from src.search.search_service import expand_query_with_glossary, HR_GLOSSARY


class TestGlossaryExpansion:
    """Test the vernacular-to-formal term expansion."""

    def test_pto_expansion(self):
        result = expand_query_with_glossary("What is the PTO policy?")
        assert "Paid Time Off" in result
        assert "PTO" in result  # original term preserved

    def test_dress_code_expansion(self):
        result = expand_query_with_glossary("What is the dress code?")
        assert "Uniform Dress Code" in result

    def test_no_match_passthrough(self):
        query = "Tell me about the company"
        result = expand_query_with_glossary(query)
        assert result == query

    def test_multiple_terms(self):
        result = expand_query_with_glossary("What about PTO and holiday pay?")
        assert "Paid Time Off" in result
        # "holiday pay" is already in the query, so the formal term doesn't need appending
        assert "holiday pay" in result.lower()

    def test_case_insensitive(self):
        result = expand_query_with_glossary("what is pto?")
        assert "Paid Time Off" in result

    def test_glossary_has_entries(self):
        assert len(HR_GLOSSARY) > 10
        assert "pto" in HR_GLOSSARY
        assert "dress code" in HR_GLOSSARY
        assert "probation" in HR_GLOSSARY


class TestSearchServiceInit:
    """Test search service can be instantiated (mocked)."""

    def test_glossary_keys_are_lowercase(self):
        for key in HR_GLOSSARY:
            assert key == key.lower(), f"Glossary key should be lowercase: {key}"

    @pytest.mark.parametrize(
        "service_type",
        [IntegratedVectorizationSearchService, HRPolicySearchService],
    )
    def test_managed_identity_uses_default_credential(self, monkeypatch, service_type):
        monkeypatch.delenv("AZURE_SEARCH_API_KEY", raising=False)
        monkeypatch.setenv("USE_MANAGED_IDENTITY", "true")

        credential = service_type()._get_credential()

        assert isinstance(credential, DefaultAzureCredential)

    @pytest.mark.parametrize(
        "service_type",
        [IntegratedVectorizationSearchService, HRPolicySearchService],
    )
    def test_local_identity_uses_azure_cli_credential(self, monkeypatch, service_type):
        monkeypatch.delenv("AZURE_SEARCH_API_KEY", raising=False)
        monkeypatch.setenv("USE_MANAGED_IDENTITY", "false")

        credential = service_type()._get_credential()

        assert isinstance(credential, AzureCliCredential)
