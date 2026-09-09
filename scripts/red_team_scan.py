"""Local AI Red Teaming Agent scan against the HR-policy agents.

Additive example for the red-teaming / continuous-evaluation (production) story.
It does NOT modify any authoritative benchmark artifact. Uses the Azure AI
Evaluation SDK's ``RedTeam`` (PyRIT) to probe a target agent with adversarial
objectives across content-harm risk categories and attack strategies, producing
an Attack Success Rate (ASR) scorecard.

Targets: b (Foundry prompt agent), hosted (Foundry hosted agent), copilot
(Copilot Studio, local scan only — cloud red teaming does not support it).

Pairs with the deterministic jailbreak/secret-disclosure custom evaluator in
``scripts/evaluate_security_foundry.py`` (SecurityRefusalEvaluator).

Install (Python 3.10-3.13):
    uv pip install "azure-ai-evaluation[redteam]"

Examples:
    python -m scripts.red_team_scan --target hosted \
      --risk-categories Violence HateUnfairness --attack-strategies EASY MODERATE \
      --num-objectives 5 --output experiments/red-team/hosted-redteam.json

    python -m scripts.red_team_scan --target b \
      --custom-attack-prompts experiments/red-team/hr_policy_attack_objectives.json
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.evaluation.red_team_targets import build_target


def _resolve_project() -> Any:
    """Foundry project endpoint string, or a hub-project dict, per the SDK."""
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    if endpoint:
        return endpoint
    return {
        "subscription_id": os.environ["EXPECTED_AZURE_SUBSCRIPTION_ID"],
        "resource_group_name": os.environ["AZURE_RESOURCE_GROUP"],
        "project_name": os.environ["AZURE_AI_PROJECT_NAME"],
    }


async def _run(args: argparse.Namespace) -> int:
    try:
        from azure.ai.evaluation.red_team import AttackStrategy, RedTeam, RiskCategory
    except ImportError:
        print(
            "The AI Red Teaming Agent requires the redteam extra (PyRIT):\n"
            '  uv pip install "azure-ai-evaluation[redteam]"   (Python 3.10-3.13)'
        )
        return 2
    from azure.identity import AzureCliCredential

    risk_by_name = {category.name.lower(): category for category in RiskCategory}
    strategy_by_name = {strategy.name.lower(): strategy for strategy in AttackStrategy}
    risks = [risk_by_name[name.lower()] for name in args.risk_categories] if args.risk_categories else None
    strategies = [strategy_by_name[name.lower()] for name in args.attack_strategies] if args.attack_strategies else None

    target = build_target(args.target, agent_name=args.agent_name, lane=args.lane)

    red_team_kwargs: dict[str, Any] = {
        "azure_ai_project": _resolve_project(),
        "credential": AzureCliCredential(process_timeout=30),
        "num_objectives": args.num_objectives,
    }
    if risks:
        red_team_kwargs["risk_categories"] = risks
    if args.custom_attack_prompts:
        red_team_kwargs["custom_attack_seed_prompts"] = str(args.custom_attack_prompts)
    red_team = RedTeam(**red_team_kwargs)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    scan_kwargs: dict[str, Any] = {
        "target": target,
        "scan_name": args.scan_name,
        "output_path": str(args.output),
    }
    if strategies:
        scan_kwargs["attack_strategies"] = strategies

    result = await red_team.scan(**scan_kwargs)
    scorecard = getattr(result, "scorecard", None) or (result.get("scorecard") if isinstance(result, dict) else None)
    print(f"Red team scan complete. Scorecard saved to {args.output}")
    if scorecard:
        print(f"Scorecard summary: {scorecard.get('risk_category_summary', scorecard)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Local AI Red Teaming Agent scan for the HR-policy agents")
    parser.add_argument("--target", required=True, help="b | hosted | copilot")
    parser.add_argument("--agent-name", help="Hosted agent name (for --target hosted)")
    parser.add_argument("--lane", help="Copilot Studio lane suffix (for --target copilot), e.g. A / A2 / C")
    parser.add_argument("--risk-categories", nargs="*", help="Violence HateUnfairness Sexual SelfHarm ProtectedMaterial CodeVulnerability UngroundedAttributes")
    parser.add_argument("--attack-strategies", nargs="*", help="EASY MODERATE DIFFICULT or specific e.g. Base64 Flip Jailbreak IndirectAttack Tense")
    parser.add_argument("--num-objectives", type=int, default=5)
    parser.add_argument("--custom-attack-prompts", type=Path, help="JSON of custom attack seed prompts")
    parser.add_argument("--scan-name", default="hr-policy-red-team")
    parser.add_argument("--output", type=Path, default=Path("experiments/red-team/red-team-scan.json"))
    args = parser.parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
