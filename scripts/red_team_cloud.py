"""Cloud AI Red Teaming Agent (Microsoft Foundry SDK) for the Foundry agents.

Additive example for the production / continuous-evaluation story — it does NOT
change any authoritative benchmark artifact. Creates a red team and a run
against a deployed Foundry Agent (prompt agent ``HRPolicyAgent`` for Pattern B,
or the hosted container agent) with built-in agentic safety evaluators
(Prohibited Actions, Task Adherence, Sensitive Data Leakage), then polls and
saves the output items. Results appear under the project's Evaluations -> Red
team tab and support scheduled post-deployment scans.

Cloud red teaming supports Foundry project deployments, Azure OpenAI model
deployments, and Foundry Agents (prompt/container) only — not Copilot Studio.

Install: pip install "azure-ai-projects>=2.0.0"
Docs: https://learn.microsoft.com/azure/foundry/how-to/develop/run-ai-red-teaming-cloud

Example:
    python -m scripts.red_team_cloud --agent-name HRPolicyAgent \
      --attack-strategies Flip Base64 IndirectJailbreak --num-turns 5 \
      --output experiments/red-team/cloud-redteam-b.json
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv


def main(argv: list[str] | None = None) -> int:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Cloud AI Red Teaming Agent for a Foundry agent")
    parser.add_argument("--agent-name", default=os.getenv("AZURE_AI_AGENT_NAME", "HRPolicyAgent"))
    parser.add_argument("--attack-strategies", nargs="*", default=["Flip", "Base64", "IndirectJailbreak"])
    parser.add_argument("--num-turns", type=int, default=5)
    parser.add_argument("--red-team-name", default="HR Policy Agent Red Team")
    parser.add_argument("--run-name", default="hr-policy-red-team-run")
    parser.add_argument("--output", type=Path, default=Path("experiments/red-team/cloud-redteam-output.json"))
    args = parser.parse_args(argv)

    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5-mini")

    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import (
        AgentTaxonomyInput,
        AzureAIAgentTarget,
        EvaluationTaxonomy,
        RiskCategory,
    )
    from azure.identity import DefaultAzureCredential

    with DefaultAzureCredential() as credential:
        with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:
            client = project_client.get_openai_client()

            agent = project_client.agents.get(args.agent_name)
            latest = getattr(getattr(agent, "versions", None), "latest", None)
            agent_version = getattr(latest, "version", None) or getattr(agent, "version", "1")
            target = AzureAIAgentTarget(name=args.agent_name, version=agent_version)

            red_team = client.evals.create(
                name=args.red_team_name,
                data_source_config={"type": "azure_ai_source", "scenario": "red_team"},
                testing_criteria=[
                    {"type": "azure_ai_evaluator", "name": "Prohibited Actions",
                     "evaluator_name": "builtin.prohibited_actions", "evaluator_version": "1"},
                    {"type": "azure_ai_evaluator", "name": "Task Adherence",
                     "evaluator_name": "builtin.task_adherence", "evaluator_version": "1",
                     "initialization_parameters": {"deployment_name": model_deployment}},
                    {"type": "azure_ai_evaluator", "name": "Sensitive Data Leakage",
                     "evaluator_name": "builtin.sensitive_data_leakage", "evaluator_version": "1"},
                ],
            )
            print(f"Created red team: {red_team.id}")

            taxonomy = project_client.beta.evaluation_taxonomies.create(
                name=args.agent_name,
                body=EvaluationTaxonomy(
                    description="Taxonomy for HR policy agent red teaming",
                    taxonomy_input=AgentTaxonomyInput(
                        risk_categories=[RiskCategory.PROHIBITED_ACTIONS],
                        target=target,
                    ),
                ),
            )
            print(f"Created taxonomy: {taxonomy.id}")

            eval_run = client.evals.runs.create(
                eval_id=red_team.id,
                name=args.run_name,
                data_source={
                    "type": "azure_ai_red_team",
                    "item_generation_params": {
                        "type": "red_team_taxonomy",
                        "attack_strategies": args.attack_strategies,
                        "num_turns": args.num_turns,
                        "source": {"type": "file_id", "id": taxonomy.id},
                    },
                    "target": target.as_dict(),
                },
            )
            print(f"Created run: {eval_run.id}, status: {eval_run.status}")

            while True:
                run = client.evals.runs.retrieve(run_id=eval_run.id, eval_id=red_team.id)
                print(f"Status: {run.status}")
                if run.status in ("completed", "failed", "canceled"):
                    break
                time.sleep(10)

            items = list(client.evals.runs.output_items.list(run_id=run.id, eval_id=red_team.id))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            payload = [item.as_dict() if hasattr(item, "as_dict") else item for item in items]
            args.output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            print(
                f"Saved {len(items)} output items to {args.output}. "
                f"Portal: Evaluations -> Red team -> '{args.red_team_name}'"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
