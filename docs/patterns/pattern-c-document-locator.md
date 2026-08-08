# Pattern C: Deterministic Document Locator

## Outcome

Copilot Studio calls `POST /api/lookup` to return the authoritative filename and
URL. The lookup path does not use an LLM to synthesize policy content. In the
blog's dual-tool design, locator questions route here while explanatory questions
route to A, A2, or B.

## Choose an option

### Option C1: Local development

Run FastAPI locally to validate lookup behavior. Copilot Studio cannot call
`localhost`; use this option for repository-side testing only.

### Option C2: Deployed REST tool

Deploy the backend to an HTTPS endpoint and import the OpenAPI contract into
Copilot Studio.

## Prerequisites

- `hr-policy-index` is populated with source URLs.
- The backend can authenticate to Azure AI Search.
- For C2, the OpenAPI `host` is replaced with the deployed backend hostname.

## Build and validate C1

```bash
source .venv/bin/activate
python -m src.backend.main
```

In a second terminal:

```bash
source .venv/bin/activate
python -m scripts.demo.test_pattern_c \
  -q "Where is the Code of Ethics policy?"
```

## Build C2

1. Deploy the FastAPI backend.
2. Set the deployed hostname in `copilot/openapi-lookup-v2.json`.
3. In Copilot Studio, select **Tools -> Add a tool -> New tool -> REST API**.
4. Import the OpenAPI file and configure authentication.
5. Confirm the user's locator request maps to the required `query` input.
6. Add the [Pattern C router instructions](../CopilotStudioLookupRouting.md#pattern-c-router-instructions).
7. Save and start a new test session.

## Validate

Ask:

```text
Give me the link to the part-time PTO policy.
```

Pass when Copilot Studio calls `lookupHRPolicyDocument` and returns the exact
filename and URL for Policy 50020 without replacing it with a policy summary.

## Stop or continue

- **Stop with C** when deterministic document location is the complete need.
- Combine C with A, A2, or B only after each route passes independently and the
  routing distinction is explicit.
- Continue to [Hosted](pattern-hosted-agent.md) only when custom runtime control
  is also required.

## Deeper references

- [Complete Pattern C wiring](../CopilotStudioLookupRouting.md)
- [Hybrid routing example](../CopilotStudioHybridExample.md)