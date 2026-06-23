# Copilot Studio screenshots

This folder holds the screenshots referenced by
[../../CopilotStudioTestingGuide.md](../../CopilotStudioTestingGuide.md).

Screenshots are intentionally captured against the **production**
Copilot Studio UI (https://copilotstudio.microsoft.com) so the guide
matches what testers see. PNGs are not committed yet — the guide
renders fine without them (alt text shows in place of the image).

## Capture checklist

When you can take the screenshots, save them with these exact filenames
so the guide's existing image links resolve.

| # | Filename | Where in the UI | Used by |
| - | -------- | --------------- | ------- |
| 01 | `01-create-agent.png` | **Create → New agent** dialog with name `Ask HR Policy Agent` filled in | Step A |
| 02 | `02-overview-instructions.png` | Agent **Overview** page with the Instructions textbox highlighted | Step A |
| 03 | `03-generative-ai-settings.png` | **Settings → Generative AI** with orchestration = Yes, general knowledge = Off | Step A |
| 04 | `04-add-knowledge-aisearch.png` | **Knowledge → Add knowledge → Featured → Azure AI Search** | Step B (Pattern A) |
| 05 | `05-knowledge-connection.png` | Azure AI Search connection dialog (endpoint + key + `hr-policy-index`) | Step B (Pattern A) |
| 06 | `06-knowledge-ready.png` | Knowledge page showing `hr-policy-index` status = **Ready** | Step B (Pattern A) |
| 07 | `07-agents-add-foundry-agent.png` | **Agents → Add an agent → Connect to an external agent → Microsoft Foundry (Preview)** | Step C (Pattern B) |
| 08 | `08-foundry-agent-config.png` | Foundry agent tool configuration with `HRPolicyAgent` selected + Completion = generative AI | Step C (Pattern B) |
| 09 | `09-rest-tool-import.png` | **Tools → Add a tool → New tool → REST API** with `openapi-v2.json` or `openapi-lookup-v2.json` uploaded | Step C Option B / Step D |
| 10 | `10-rest-tool-auth-query.png` | REST tool authentication panel: `code` parameter, **Location = Query** (not Header) | Step C Option B / Step D |
| 11 | `11-test-pane-content.png` | Test pane: content question (Pattern A) showing citation card | Test scenarios A1–A3 |
| 12 | `12-test-pane-pattern-b.png` | Test pane: same content question routed through Pattern B with inline `[Policy XXXXX – Title]` citations | Test scenarios B1–B3 |
| 13 | `13-test-pane-lookup.png` | Test pane: locator question (Pattern C) with verbatim `blob_url` in answer body | Test scenarios C1–C3 |
| 14 | `14-test-pane-hybrid.png` | Test pane: hybrid question — content + appended link from `lookupHRPolicyDocument` | Test scenarios Hy1–Hy2 |
| 15 | `15-activity-trace.png` | Test pane **Activity** tab showing which tool/knowledge source was invoked for the last turn | "Verify routing" sections |
| 16 | `16-foundry-portal-agents.png` | Foundry portal **Agents** tab listing both `HRPolicyAgent` (Pattern B) and `hr-policy-agent` (Hosted) | Step E (Hosted Agent) |
| 17 | `17-connection-error.png` | "Let's get you connected first" error in Test pane | Troubleshooting |
| 18 | `18-manage-connections.png` | **Manage connections** page with the Azure AI Foundry Agent Service connection | Troubleshooting |

## Capture tips

- Use a window width of ~1400 px so panes don't wrap.
- Crop to the panel of interest (don't capture the full browser
  chrome). Leave 8–12 px of breathing room.
- Redact tenant names, subscription IDs, and any API keys that
  appear in the URL bar or connection forms.
- Save as PNG (lossless). Target file size < 250 KB per image; if
  bigger, run through `pngquant --quality=70-90` first.
- File naming is fixed — the guide's image links are case-sensitive
  and depend on the prefix number for ordering.
