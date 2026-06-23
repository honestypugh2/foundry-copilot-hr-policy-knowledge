"""Regression guard for ``AGENT_INSTRUCTIONS`` in ``hr_policy_agent.py``.

The HR Policy Agent's instructions enforce hard grounding rules: cite
the policy number, decline when the answer isn't in the KB, and don't
paraphrase in ways that change meaning. Those rules are the contract
between Pattern B and the customer; an accidental edit that softens
them would silently degrade response quality. These tests ensure each
critical phrase remains in the prompt.
"""

import re
import pytest

from src.agents.hr_policy_agent import AGENT_INSTRUCTIONS, AGENT_NAME


def test_agent_name_is_stable():
    """The Foundry portal entry depends on this exact name."""
    assert AGENT_NAME == "HRPolicyAgent"


def test_instructions_reference_hr_policy_assistant_role():
    assert "HR Policy Assistant" in AGENT_INSTRUCTIONS


def test_instructions_require_kb_only_answers():
    """Rule 1 \u2014 only answer from the retrieved policy documents."""
    assert "Only answer based on the HR policy documents" in AGENT_INSTRUCTIONS


def test_instructions_have_decline_clause():
    """Rule 2 \u2014 explicit decline + HR-rep escalation when the KB doesn't cover it."""
    assert "could not find this information" in AGENT_INSTRUCTIONS
    assert "HR representative" in AGENT_INSTRUCTIONS


def test_instructions_require_policy_number_citation():
    """Rule 3 \u2014 always cite the policy number and title."""
    assert "cite the specific policy number and title" in AGENT_INSTRUCTIONS


def test_instructions_forbid_meaning_changing_paraphrase():
    """Rule 4 \u2014 do not paraphrase in ways that change meaning."""
    assert "do not paraphrase in ways that change meaning" in AGENT_INSTRUCTIONS


def test_instructions_handle_vernacular():
    """Rule 6 \u2014 PTO / dress-code style vernacular maps to formal names."""
    assert "PTO" in AGENT_INSTRUCTIONS
    assert "Paid Time Off" in AGENT_INSTRUCTIONS


def test_instructions_specify_response_format():
    """Response format block enumerates the citation footer."""
    assert "RESPONSE FORMAT" in AGENT_INSTRUCTIONS
    assert "Source:" in AGENT_INSTRUCTIONS


def test_instructions_use_policy_citation_marker():
    """The bracketed citation marker that downstream parsers regex on."""
    pattern = re.compile(r"\[Policy\s+\w+\s*-\s*Title\]", re.IGNORECASE)
    assert pattern.search(AGENT_INSTRUCTIONS), (
        "Expected the bracketed [Policy XXXXX - Title] citation marker in "
        "AGENT_INSTRUCTIONS \u2014 the orchestrator's policy-reference regex "
        "depends on this exact shape."
    )
