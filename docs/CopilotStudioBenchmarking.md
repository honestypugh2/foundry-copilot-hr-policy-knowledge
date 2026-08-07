# Benchmarking through Copilot Studio

Run end-to-end measurements against the real, published Copilot Studio agents
configured for each pattern. The intentionally empty `TestAgent` is only an
extension synchronization smoke test and is not a benchmark target. This
repository owns the benchmark dataset, manifests, Direct Line runner, normalized
evidence, and cross-pattern reports. The extension manages exported agent source;
it is not a Python invocation API.

## Measurement model

Run every architecture twice when possible:

1. Run its direct repository adapter to measure the component boundary.
2. Run the same cases through each published pattern agent to measure the complete
  Copilot Studio experience.

The Copilot Studio run records client wall time, answer text, exposed citations,
conversation/activity IDs, and raw Direct Line activities. Copilot-owned model
tokens, internal tool duration, and orchestration stages remain unavailable unless
the service explicitly returns them. Do not subtract direct-adapter latency from
end-to-end latency and label the result as Copilot overhead.

## Configure one real agent per pattern

Use separate agents so each end-to-end run exposes exactly one retrieval path.
Do not put all tools on one benchmark agent and ask the orchestrator to choose;
that measures routing accuracy in addition to the pattern and can send a query
down the wrong path.

| Pattern agent | Required configuration |
| --- | --- |
| **A** | Add only `hr-policy-index` as an Azure AI Search knowledge source. Do not add a Foundry agent, Foundry IQ tool, or REST lookup tool. |
| **A2** | Add only `hr-knowledge-base` through **Build → Tools → Foundry IQ**. |
| **B** | Add only the `HRPolicyAgent` Microsoft Foundry external agent. |
| **C** | Add only the deterministic lookup REST tool from `copilot/openapi-lookup-v2.json`. |
| **Hosted** | Add only the deployed `hr-policy-agent` Microsoft Foundry external agent. |

Give all five agents the same top-level HR instructions and select the same
Copilot Studio model (currently Claude Sonnet 4.6). Send the original dataset
question unchanged. The difference between agents must be the configured
knowledge/tool path, not a `/benchmark` prefix.

> **Pattern A model boundary.** Pattern A is "direct Search" because it has no
> repo-owned backend agent or answer-model call. Copilot Studio still uses its
> selected model to synthesize an answer from Search results. A truly model-free
> Search baseline exists only in the direct repository adapter, outside Copilot
> Studio.

For auditable citation grading, have benchmark routes preserve native structured
citations when available and end policy claims with this fallback format:

```text
[Policy 50010 - Paid Time Off]
```

For each real pattern agent in its VS Code extension window:

1. Use **Get changes** before editing.
2. Verify its instructions, selected knowledge/tool, and exported model setting.
3. Use **Preview changes** and verify only that pattern agent changed.
4. Use **Apply changes** to synchronize the development agent.
5. Publish the agent to the Mobile app channel in Copilot Studio. Applying source
   changes does not prove that the channel is running the new published version.

Use non-production copies of the real agents for repeatable benchmark runs.

## Configure Direct Line

In Copilot Studio, open **Channels > Mobile app** and copy the Token Endpoint.
Each agent has a distinct schema name and token endpoint. Pass them explicitly to
the benchmark CLI; this avoids silently measuring whichever agent happens to be
in `.env`:

```dotenv
COPILOT_STUDIO_ENVIRONMENT_ID=<power-platform-environment-id>
COPILOT_STUDIO_AGENT_SCHEMA=<pattern-agent-schema-name>
COPILOT_STUDIO_TOKEN_ENDPOINT=<pattern-agent-mobile-app-token-endpoint>
```

The benchmark CLI loads `.env`. Never commit the token endpoint or tenant-specific
agent identifiers.

## Generate versioned manifests

Generate one manifest per real agent after applying or exporting its source. The
generator hashes that agent's files into `configuration_version` and records its
name and selected Copilot Studio model.

```bash
source .venv/bin/activate
python -m scripts.generate_copilot_benchmark_manifests \
  --pattern A \
  --agent-name 'Ask HR Policy Agent - A' \
  --agent-source '/path/to/Ask HR Policy Agent - A' \
  --dataset experiments/datasets/copilot-hr-policy-v1.json \
  --output-dir experiments/manifests/copilot-studio \
  --corpus-fingerprint '<current-corpus-fingerprint>' \
  --index-fingerprint '<current-index-fingerprint>' \
  --model-deployment 'Claude Sonnet 4.6' \
  --repetitions 3
```

Repeat for A2, B, C, and Hosted using each exported agent directory. Use
fingerprints from the same corpus and index configuration. Regenerate a manifest
after any model, prompt, action, knowledge, corpus, index, agent, or deployment
change.

## Run all five patterns

Run against non-production copies of the real agents. Start with one
case/repetition, then run the complete dataset. This example runs Pattern A;
repeat it with each pattern's manifest, schema, and token endpoint.

```bash
source .venv/bin/activate
python -m src.benchmarking.cli \
  --manifest experiments/manifests/copilot-studio/copilot-ask-hr-policy-agent-a.json \
  --cases experiments/datasets/copilot-hr-policy-v1.json \
  --output-dir experiments/reports/copilot-studio/a \
  --copilot-studio \
  --copilot-environment-id '<power-platform-environment-id>' \
  --copilot-agent-schema '<pattern-a-agent-schema>' \
  --copilot-token-endpoint '<pattern-a-mobile-app-token-endpoint>'
```

Each case starts a fresh Direct Line conversation to avoid cross-case memory.
Warmups and measured repetitions come from each manifest. Keep concurrency at one
for controlled comparison; use the separate load harness for capacity testing.

## Validate before comparison

For each report, verify:

- `aggregate.provenance.measurement_boundary` is
  `copilot_studio_direct_line`.
- `configuration_version` is identical across the five manifests when the same
  applied `TestAgent` revision was used.
- The manifest and token endpoint identify the intended real pattern agent.
- The response used that agent's only configured knowledge/tool path; inspect
  raw `activity` to confirm it.
- Citations contain the expected policy numbers. A missing structured citation
  or explicit `[Policy ...]` marker is scored as missing evidence.
- Each agent revision was published before its first measured run.

Direct and Copilot Studio results may be shown side by side, but only rows with
the same dataset, corpus/index fingerprints, region, deployment versions, and
run conditions are eligible for architecture recommendations.