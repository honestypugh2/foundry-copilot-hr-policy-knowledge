"""Regression guard for ``AGENT_INSTRUCTIONS`` in ``hr_policy_agent.py``.

The HR Policy Agent's instructions enforce hard grounding rules: cite
the policy number, decline when the answer isn't in the KB, and don't
paraphrase in ways that change meaning. Those rules are the contract
between Pattern B and the customer; an accidental edit that softens
them would silently degrade response quality. These tests ensure each
critical phrase remains in the prompt.
"""

import re

from src.agents.hr_policy_agent import AGENT_INSTRUCTIONS, AGENT_NAME


def test_agent_identity_and_grounding_contract_are_stable():
    assert AGENT_NAME == "HRPolicyAgent"
    required_rules = (
        "HR Policy Assistant",
        "Only answer based on the HR policy documents",
        "could not find this information",
        "HR representative",
        "cite the specific policy number and title",
        "do not paraphrase in ways that change meaning",
        "PTO",
        "Paid Time Off",
        "RESPONSE FORMAT",
        "Source:",
    )
    for rule in required_rules:
        assert rule in AGENT_INSTRUCTIONS

    pattern = re.compile(r"\[Policy\s+\w+\s*-\s*Title\]", re.IGNORECASE)
    assert pattern.search(AGENT_INSTRUCTIONS), (
        "Expected the bracketed [Policy XXXXX - Title] citation marker in "
        "AGENT_INSTRUCTIONS \u2014 the orchestrator's policy-reference regex "
        "depends on this exact shape."
    )
