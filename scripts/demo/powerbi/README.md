# AI governance Power BI landing page

The `pwwdemo-ai-governance` report presents six Crawl tiles and three Walk tiles,
an architecture view, source interpretation, runtime examples, and links to the
repository's four governance notebooks. The report summarizes evidence; native
Microsoft tools remain responsible for enforcement and investigation.

## Published report

- Workspace: `ffia-hc01-lab` on the existing F8 capacity.
- [Open the report](https://app.powerbi.com/groups/2243a0cb-c089-43ec-bc28-1213de9a8a42/reports/f53c745c-eb34-4b12-90d2-1858472e6dd6).
- Report and semantic model display name: `pwwdemo-ai-governance`.

The five pages are **Governance landing**, **How the pane works**,
**Source & freshness**, **Runtime & cost**, and **Learn with notebooks**.
Navigation buttons connect the pages; console and notebook buttons open external
websites. Power BI access and external console permissions are evaluated
independently for the signed-in user.
Button visibility is configured globally, while label text, alignment and colors
target the Power BI button's `default` render-state selector.

## Data and interpretation

**Every metric and trend is synthetic.** The fixture covers October 22-28, 2026.
Refresh reloads the same fixture; it is not a live freshness indicator.
Microsoft 365 GCC and Azure Government panels illustrate target architecture,
not deployed cross-cloud connectors. Console links open Commercial entry points.

| Phase | Measure | October 28 value | Illustrative source |
|---|---|---:|---|
| Crawl | Missing Owners | 7 tools | SharePoint intake |
| Crawl | Registered Agents | 12 agents | Agent 365 / Foundry |
| Crawl | Blocked Apps | 5 apps | Defender for Cloud Apps |
| Crawl | Sensitive Events | 9 events | Purview |
| Crawl | Source Incidents | 3 incidents | Defender XDR / Sentinel |
| Crawl | Usage Sessions | 2,480 sessions | M365 / Copilot Studio |
| Walk | Guardrail Blocks | 18 blocks | Foundry / APIM / Log Analytics |
| Walk | Illustrative Cost | USD 146.25 per day | Cost Management |
| Walk | Drift Flags | 2 models flagged | Azure ML / custom checks |

These are different units, not components of a combined risk score.
`Latest Value` deliberately returns blank without a single tile in context.
A model filter block, a Defender alert, and agent-attributed Agent 365 risk are
different evidence types. This report does not establish Agent 365 telemetry
ingestion or attributed risk.

The Import semantic model has a three-table star:

- `Tiles`: nine source, phase, cloud, unit and provenance definitions.
- `Calendar`: seven contiguous fixture dates.
- `Observations`: 63 tile/day values and explicit KPI measures.

Embedded Power Query fixtures require no external data-source credentials.
Single-direction relationships connect observations to tile and date dimensions.
The exported semantic model definition contains the fixture itself; no live
tenant exports are packaged into the report.

## Source layout

All Power BI assets are contained in this directory:

- [build_report.py](build_report.py): generates five pages, visual bindings,
  navigation and PBIP scaffolding.
- [project/](project/): editable Power BI Project source, including the exported
  semantic model and generated PBIR report.
- [service.py](service.py): isolated report publishing, receipt-matched updates,
  metadata inspection, model refresh and exact-value validation.
- [validate_report.py](validate_report.py): official Microsoft JSON-schema,
  navigation, tile-presence and page-boundary checks.
- [test_powerbi.py](test_powerbi.py): offline layout, packaging and service-safety
  regression tests.
- [requirements.txt](requirements.txt): additional schema-validation dependencies;
  HTTPX and pytest come from the repository environment.

Open [the PBIP project](project/pwwdemo-ai-governance.pbip) in a current Windows
Power BI Desktop version with PBIP/PBIR support. The local report uses a relative
semantic-model reference. Publishing creates an in-memory service binding without
changing that local reference. Desktop opening and browser visual rendering are
separate from JSON-schema and service-metadata validation.

## Build and validate

Commands run from the repository root using its Python environment:

```bash
uv pip install -r scripts/demo/powerbi/requirements.txt
.venv/bin/python -m scripts.demo.powerbi.build_report
.venv/bin/python -m scripts.demo.powerbi.validate_report
.venv/bin/python -m pytest scripts/demo/powerbi/test_powerbi.py -q
.venv/bin/ruff check scripts/demo/powerbi
```

Schema validation downloads Microsoft's public schemas once and caches them under
ignored `.local/schemas/`. Layout changes belong in the generator rather than in
individual generated visual files. The generator does not rewrite the semantic
model's exported definition.

## Service interface

The service client uses Azure CLI authentication, checks the demo tenant claim,
resolves the workspace by name and requires an accessible active capacity.
Tokens stay in memory and are never written to the project. Fabric requests carry
the semantic-model authoring skill header. Operation polling uses the canonical
API host even when the response identifies a regional endpoint.

```bash
# Read-only: validate all nine values and the blank mixed-unit total.
.venv/bin/python -m scripts.demo.powerbi.service --validate-only

# Read-only service calls: verify model binding and five page titles.
# Writes only the ignored local deployment receipt.
.venv/bin/python -m scripts.demo.powerbi.service --inspect-report

# Explicit model data refresh followed by the same value validation.
.venv/bin/python -m scripts.demo.powerbi.service --refresh-validate

# Create only when this report is absent and exactly one same-named model exists.
.venv/bin/python -m scripts.demo.powerbi.service --publish-report

# Update only the report matching the local receipt, resolved workspace and model.
.venv/bin/python -m scripts.demo.powerbi.service --update-report
```

The published model already exists. `--publish-report` does not deploy a model and
refuses duplicate reports. An interrupted create must be inspected before any
retry. `--inspect-report` can recover the ignored `.local/deployment.json` receipt
without creating, deleting or replacing service items. Updates do not alter the
semantic model or other workspace items.

The semantic model was authored and exported with the Power BI modeling
integration. Model object changes use that integration; exporting persists them
to the local project. Deployment from saved model files uses the
[Fabric semantic-model definition API](https://learn.microsoft.com/en-us/rest/api/fabric/semanticmodel/items/create-semantic-model).
This client intentionally exposes no model replacement, item deletion, capacity
management, tenant settings or permission-management commands.

## Notebook integration

The learning page links to the existing presentation branch notebook sources:

1. [AI estate inventory](../../../notebooks/governance/01_ai_estate.ipynb).
2. [Govern model access](../../../notebooks/governance/02_govern_model_access.ipynb).
3. [Follow the evidence](../../../notebooks/governance/03_follow_the_evidence.ipynb),
   including the native Agent 365 telemetry SDK walkthrough.
4. [Governance overview](../../../notebooks/governance/04_governance_overview.ipynb).

Notebook execution remains independent of Power BI. Optional saved live snapshots
and paid-inference gates in the notebooks do not change this report's fixtures.
The report's documentation button opens the existing
[governance code reference](../../../docs/AIGovernanceDemo.md), rather than relying
on unpublished Power BI source files.
