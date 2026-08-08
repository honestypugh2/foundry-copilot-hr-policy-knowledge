# Pattern A: Direct Azure AI Search

## Outcome

Copilot Studio retrieves from `hr-policy-index` and writes the answer. No
repository-owned agent runs in the answer path. Build this pattern first.

## Choose an option

### Option A1: Azure AI Search knowledge

Use this default when the indexed HR corpus is the source of truth. It supports
hybrid/vector retrieval and native Copilot Studio citations.

### Option A-SP: SharePoint knowledge

Use SharePoint instead when document permissions must follow each user's
SharePoint access. Search freshness and vernacular matching depend on Microsoft
365 indexing rather than this repository's Search index.

A-SP is a repository setup option within the blog's citation-friendly Pattern A
branch, not a sixth published retrieval pattern.

Do not add both options to the first test agent. Validate one retrieval source
at a time.

## Prerequisites

- Complete the [shared foundation](README.md#shared-foundation).
- Use a Copilot Studio agent that supports the selected knowledge source.
- For A1, grant the connection identity **Search Index Data Reader**.
- For A-SP, grant test users read access to the SharePoint library.

## Build Option A1

1. In Copilot Studio, open **Knowledge -> Add knowledge -> Azure AI Search**.
2. Create an Entra ID connection using the Search service root endpoint.
3. Select `hr-policy-index` and add it to the agent.
4. Paste the [shared Copilot instructions](../CopilotStudioIntegration.md#shared-copilot-instructions).
5. Disable general-knowledge answers for the isolated test.
6. Save and start a new test session.

The complete click path is in
[Pattern A wiring](../CopilotStudioIntegration.md#pattern-a-wiring--azure-ai-search-as-knowledge-source).

## Build Option A-SP

Follow [Pattern A-SP wiring](../CopilotStudioIntegration.md#pattern-a-sp-wiring--sharepoint-as-a-knowledge-source),
then wait until the source status is **Ready** before testing.

## Validate

Ask:

```text
What does Policy 20030 say about the probationary period?
```

Pass when the answer is grounded in Policy 20030 and includes a working native
citation. For A-SP, also test with a user who lacks access to confirm ACLs are
enforced.

The repository-side Search smoke test verifies the index, not Copilot Studio:

```bash
source .venv/bin/activate
python -m scripts.demo.test_pattern_a \
  -q "What does Policy 20030 say about the probationary period?"
```

## Stop or continue

- **Stop with A** when answer quality, citations, latency, and permissions meet
  the scenario.
- Continue to [Pattern A2](pattern-a2-foundry-iq.md) when retrieval needs
  agentic query planning or stronger multi-policy comparison.
- Continue to [Pattern B](pattern-b-foundry-agent.md) when every answer must be
  synthesized after required retrieval, especially when policy wording needs
  tighter control.
- Go directly to [Pattern C](pattern-c-document-locator.md) when the requirement
  is an exact document URL rather than an answer.

## Deeper references

- [Data pipeline and indexing options](../DataPipelineAndTesting.md)
- [Pattern A limitations](../CopilotStudioIntegration.md#pattern-a-limitations-and-pattern-b-mitigations)
- [Full test catalog](../CopilotStudioTestingGuide.md#starter-query-catalog)