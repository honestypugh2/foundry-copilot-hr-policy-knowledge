"""Build a PBIP/PBIR report around the MCP-authored governance semantic model."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / "project"
NAME = "pwwdemo-ai-governance"
REPORT = PROJECT / f"{NAME}.Report"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/"
REPO = "https://github.com/honestypugh2/foundry-copilot-hr-policy-knowledge"
NOTEBOOKS = f"{REPO}/blob/bp/ai-governance-oct28/notebooks/governance"

INK = "#182234"
MUTED = "#546177"
PURPLE = "#4536C7"
AMBER = "#C88A00"
TEAL = "#007E76"
WHITE = "#FFFFFF"
SLATE = "#F3F5FA"
LINE = "#E0E5EF"

TILES = (
    (1, "AI tools missing tier / owner / approver", "Missing Owners", "7", "SharePoint intake list", "tools"),
    (2, "Agents in the registry", "Registered Agents", "12", "Agent 365 + Foundry definitions", "agents"),
    (3, "Discovered / blocked AI apps", "Blocked Apps", "5", "Defender for Cloud Apps", "apps"),
    (4, "Sensitive-data events with AI", "Sensitive Events", "9", "Purview Audit / DSPM for AI", "events"),
    (5, "AI-related incidents", "Source Incidents", "3", "Defender XDR + Sentinel", "incidents"),
    (6, "Copilot & agent usage", "Usage Sessions", "2,480", "M365 usage + Copilot Studio", "sessions"),
    (7, "Guardrail blocks & traces", "Guardrail Blocks", "18", "Foundry + APIM + Log Analytics", "blocks"),
    (8, "Cost by agent / team", "Illustrative Cost", "$146.25", "Azure Cost Management", "USD / day"),
    (9, "Model drift", "Drift Flags", "2", "Azure ML / custom checks", "models flagged"),
)
PAGES = (
    ("landing", "01 | Governance landing"),
    ("architecture", "02 | How the pane works"),
    ("sources", "03 | Source & freshness"),
    ("runtime", "04 | Runtime & cost"),
    ("notebooks", "05 | Learn with notebooks"),
)


def literal(value: object) -> dict:
    if isinstance(value, bool):
        text = str(value).lower()
    elif isinstance(value, (int, float)):
        text = f"{value}D"
    else:
        text = "'" + str(value).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": text}}}


def color(value: str) -> dict:
    return {"solid": {"color": literal(value)}}


def field(table: str, name: str, *, measure: bool = False) -> dict:
    return {
        "Measure" if measure else "Column": {
            "Expression": {"SourceRef": {"Entity": table}}, "Property": name,
        }
    }


def projection(table: str, name: str, *, measure: bool = False) -> dict:
    return {
        "field": field(table, name, measure=measure),
        "queryRef": f"{table}.{name}", "nativeQueryRef": name,
    }


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class Page:
    def __init__(self, name: str, title: str):
        self.name = name
        self.visuals: list[dict] = []
        self.metadata = {
            "$schema": SCHEMA + "definition/page/2.0.0/schema.json",
            "name": name, "displayName": title, "displayOption": "FitToPage",
            "width": 1600, "height": 1000,
            "objects": {"background": [{"properties": {
                "color": color(WHITE), "transparency": literal(0),
            }}]},
        }

    def visual(
        self, name: str, kind: str, x: int, y: int, w: int, h: int, *,
        objects: dict | None = None, query: dict | None = None,
        background: str = WHITE, border: bool = False,
    ) -> dict:
        configuration = {
            "visualType": kind,
            "visualContainerObjects": {
                "background": [{"properties": {
                    "show": literal(True), "color": color(background), "transparency": literal(0),
                }}],
                "border": [{"properties": {
                    "show": literal(border), "color": color(LINE), "radius": literal(8),
                }}],
                "visualHeader": [{"properties": {"show": literal(False)}}],
            },
        }
        if objects:
            configuration["objects"] = objects
        if query:
            configuration["query"] = query
        result = {
            "$schema": SCHEMA + "definition/visualContainer/2.0.0/schema.json",
            "name": name, "position": {
                "x": x, "y": y, "width": w, "height": h, "z": len(self.visuals),
                "tabOrder": len(self.visuals),
            }, "visual": configuration,
        }
        self.visuals.append(result)
        return result

    def text(
        self, name: str, text: str, x: int, y: int, w: int, h: int, *,
        size: int = 12, foreground: str = INK, background: str = WHITE,
        bold: bool = False, border: bool = False,
    ) -> dict:
        paragraphs = [{
            "textRuns": [{"value": line, "textStyle": {
                "fontFamily": "Segoe UI", "fontSize": f"{size}pt",
                "color": foreground, "fontWeight": "bold" if bold else "normal",
            }}],
        } for line in text.split("\n")]
        return self.visual(
            name, "textbox", x, y, w, h,
            objects={"general": [{"properties": {"paragraphs": paragraphs}}]},
            background=background, border=border,
        )

    def button(
        self, name: str, label: str, target: str, x: int, y: int, w: int = 210, *,
        web: bool = False, fill: str = PURPLE,
    ) -> None:
        visual = self.visual(
            name, "actionButton", x, y, w, 42,
            objects={
                "text": [
                    {"properties": {"show": literal(True)}},
                    {"selector": {"id": "default"}, "properties": {
                        "text": literal(label), "fontColor": color(WHITE),
                        "fontSize": literal(11), "bold": literal(True),
                        "horizontalAlignment": literal("center"),
                        "verticalAlignment": literal("middle"),
                    }},
                ],
                "fill": [{"properties": {
                    "show": literal(True), "fillColor": color(fill), "transparency": literal(0),
                }, "selector": {"id": "default"}}],
                "outline": [{"properties": {"show": literal(False)}, "selector": {"id": "default"}}],
            }, background=fill,
        )
        visual["visual"]["visualContainerObjects"]["visualLink"] = [{"properties": {
            "show": literal(True),
            "type": literal("WebUrl" if web else "PageNavigation"),
            "webUrl" if web else "navigationSection": literal(target),
        }}]

    def header(self, title: str, subtitle: str) -> None:
        self.text("title", title, 28, 16, 1250, 52, size=27, bold=True)
        self.text("subtitle", subtitle, 30, 72, 1520, 32, foreground=MUTED, size=11)
        self.text(
            "synthetic-banner",
            "SYNTHETIC DEMO  |  Hosted in Azure Commercial  |  GCC / Government coverage is simulated",
            28, 110, 1544, 36, background="#FFF4D8", foreground="#795100", size=12, bold=True,
        )
        for i, (page, label) in enumerate(PAGES):
            self.button(
                f"nav-{page}", label.split(" | ")[1], page,
                28 + i * 311, 158, 300, fill=PURPLE if page == self.name else "#686F82",
            )
        self.text(
            "footer",
            "The pane reports. Native tools control. | Fixture date: 2026-10-28 (not live freshness)"
            " | No verified Agent 365 risk ingestion | Sources and links on page 3",
            28, 958, 1544, 30, foreground=MUTED, size=10,
        )

    def card(self, tile: tuple, x: int, y: int, *, walk: bool = False) -> None:
        key, title, measure, _, source, unit = tile
        bg = "#FFF8ED" if walk else SLATE
        accent = AMBER if walk else TEAL
        self.text(f"tile-{key}-title", title, x, y, 480, 52, size=15, bold=True, background=bg)
        self.text(
            f"tile-{key}-phase", ("WALK" if walk else "CRAWL") + "  |  SYNTHETIC",
            x, y + 52, 480, 25, size=10, foreground=accent, background=bg, bold=True,
        )
        self.visual(
            f"tile-{key}-value", "card", x, y + 77, 480, 66, background=bg,
            query={"queryState": {"Values": {"projections": [
                projection("Observations", measure, measure=True),
            ]}}},
            objects={
                "labels": [{"properties": {
                    "color": color(INK), "fontSize": literal(34), "labelDisplayUnits": literal(0),
                }}],
                "categoryLabels": [{"properties": {"show": literal(False)}}],
            },
        )
        self.text(
            f"tile-{key}-source", f"{unit}  |  {source}\nFixture: Oct 28, 2026  |  Connector: simulated",
            x, y + 146, 480, 49, size=10, foreground=MUTED, background=bg,
        )
        self.button(
            f"tile-{key}-detail", "View source & interpretation", "runtime" if walk else "sources",
            x, y + 197, 480, fill=accent,
        )

    def table(self, name: str, columns: list[tuple[str, str, bool]], x: int, y: int, w: int, h: int) -> None:
        self.visual(
            name, "tableEx", x, y, w, h, border=True,
            query={"queryState": {"Values": {"projections": [
                projection(table, col, measure=measure) for table, col, measure in columns
            ]}}},
            objects={
                "grid": [{"properties": {
                    "gridVertical": literal(False), "gridHorizontal": literal(True),
                    "rowPadding": literal(12), "textSize": literal(11),
                }}],
                "columnHeaders": [{"properties": {
                    "fontColor": color(INK), "backColor": color(SLATE),
                    "fontSize": literal(11), "bold": literal(True),
                }}],
                "total": [{"properties": {"totals": literal(False)}}],
            },
        )

    def save(self) -> None:
        folder = REPORT / "definition/pages" / self.name
        write(folder / "page.json", self.metadata)
        for visual in self.visuals:
            write(folder / "visuals" / visual["name"] / "visual.json", visual)


def landing() -> Page:
    page = Page(*PAGES[0])
    page.header("AI governance | One picture. Clear accountability.",
                "Crawl: establish visibility with existing tools. Walk: add runtime evidence and cost.")
    for i, tile in enumerate(TILES):
        row, col = divmod(i, 3)
        page.card(tile, 30 + col * 520, 213 + row * 245, walk=i >= 6)
    return page


def architecture() -> Page:
    page = Page(*PAGES[1])
    page.header("How the single pane works",
                "No single native console spans both target clouds. Federate evidence; keep enforcement native.")
    panels = [
        ("gcc", "Microsoft 365 GCC | SIMULATED", 30, "#EDF2FF",
         "SharePoint AI intake + approvals\nAgent 365 registry / Entra\nPurview: labels, Audit, DLP, DSPM for AI\nCopilot Studio analytics\nDefender XDR / Defender for Cloud Apps\nMicrosoft 365 usage reports"),
        ("government", "Azure Government | SIMULATED", 550, "#EAF7F1",
         "Foundry agent definitions\nFoundry guardrails + tracing\nEntra Agent ID / API Management\nApplication Insights + Log Analytics\nAzure ML / custom model checks\nDefender posture / Sentinel / cost"),
    ]
    for name, title, x, bg, text in panels:
        page.text(name+"-title", title, x, 225, 490, 44, background=bg, bold=True, size=15)
        page.text(name+"-sources", text, x, 277, 490, 260, background=bg, size=14)
    page.text(
        "landing-store",
        "Scheduled exports / queries\nControlled landing store (conceptual)\nPower BI imports selected evidence; no cross-cloud connector is deployed",
        30, 558, 1010, 110, background=SLATE, size=15, bold=True,
    )
    page.text(
        "one-picture",
        "POWER BI LANDING PAGE\nCrawl tiles + Walk tiles + source / freshness / evidence labels\nEvery tile links to its reporting detail. Native consoles own investigation and action.",
        30, 695, 1010, 125, background="#FFF4D8", size=15, bold=True,
    )
    stages = ("Decide", "Collect", "Land", "Show", "Act")
    for i, stage in enumerate(stages):
        page.text(
            "stage-"+stage.lower(), stage, 30 + 204*i, 849, 194, 50, size=15,
            foreground=WHITE, background=PURPLE, bold=True,
        )
    layers = (
        "0 | Decide & be accountable", "1 | Know what exists", "2 | Protect the data",
        "3 | Govern access", "4 | See behavior", "5 | Detect & respond", "6 | Cost",
    )
    for i, layer in enumerate(layers):
        page.text(
            f"layer-{i}", layer, 1080, 225+i*91, 490, 74, size=15,
            bold=True, background="#FFF4D8" if i == 0 else SLATE,
        )
    return page


def sources() -> Page:
    page = Page(*PAGES[2])
    page.header("Source, freshness & interpretation",
                "Nine distinct units. No blended risk score. Unknown coverage is not zero risk.")
    page.table("source-table", [
        ("Tiles", "Tile Name", False), ("Tiles", "Phase", False),
        ("Tiles", "Source System", False), ("Tiles", "Target Cloud", False),
        ("Tiles", "Unit", False), ("Tiles", "Evidence Kind", False),
        ("Observations", "Latest Value", True), ("Calendar", "Evidence Date", True),
    ], 30, 220, 1540, 390)
    page.text(
        "evidence-meaning",
        "WHAT THE NUMBERS MEAN\nAll nine metrics are synthetic fixtures dated October 28, 2026."
        "\nThey are not observations from PWW, GCC, Azure Government, or current tenant security feeds."
        "\nRefreshing the model reloads the same fixtures; it does not make them live."
        "\nRegistry count != published agents != authenticated identities != attributed security risk.",
        30, 645, 1000, 195, background=SLATE, size=15,
    )
    page.text(
        "console-warning",
        "CONSOLE LINKS\nThese open public Commercial entry points."
        "\nThey are not verified GCC / Government deep links."
        "\nAccess still depends on your signed-in tenant and roles.",
        1060, 645, 510, 142, background="#FFF4D8", size=13,
    )
    page.button("open-agent365", "Agent 365 / M365 admin", "https://admin.microsoft.com/", 1060, 805, 245, web=True)
    page.button("open-purview", "Microsoft Purview", "https://purview.microsoft.com/", 1320, 805, 245, web=True)
    page.button("open-defender", "Microsoft Defender", "https://security.microsoft.com/", 1060, 860, 245, web=True)
    page.button("open-foundry", "Microsoft Foundry", "https://ai.azure.com/", 1320, 860, 245, web=True)
    return page


def runtime() -> Page:
    page = Page(*PAGES[3])
    page.header("Walk | Runtime, cost & model behavior",
                "Synthetic examples explain the reporting shape; real connectors remain separate integrations.")
    for col, tile in enumerate(TILES[6:]):
        page.card(tile, 30+col*520, 222, walk=True)
    page.visual(
        "guardrail-trend", "lineChart", 30, 490, 1000, 350, border=True,
        query={"queryState": {
            "Category": {"projections": [projection("Calendar", "Date")]},
            "Y": {"projections": [projection("Observations", "Guardrail Blocks", measure=True)]},
        }},
        objects={"legend": [{"properties": {"show": literal(False)}}]},
    )
    page.text(
        "trend-label", "Synthetic guardrail blocks | Oct 22-28, 2026", 35, 845, 995, 40,
        size=13, foreground=MUTED,
    )
    page.text(
        "runtime-boundaries",
        "DO NOT CONFLATE\nHTTP 400 filter block != Defender alert\nDefender source alert != Agent 365 risk"
        "\nAPIM label != Entra Agent ID\nEstimated cost != actual invoice"
        "\nDrift flag != confirmed model failure\n\nNo verified Agent 365 ingestion is claimed.",
        1060, 490, 510, 350, background=SLATE, size=16,
    )
    page.button("open-apim", "APIM / Azure portal", "https://portal.azure.com/", 1060, 860, 245, web=True)
    page.button("open-azureml", "Azure ML", "https://ml.azure.com/", 1320, 860, 245, web=True)
    return page


def notebooks() -> Page:
    page = Page(*PAGES[4])
    page.header("Learn, inspect, explain | Python + notebooks",
                "The report summarizes. The notebooks teach the code, controls and evidence boundaries.")
    entries = [
        ("01", "Know the AI estate", "Inventory / source / cloud / owner / explicit gaps",
         "01_ai_estate.ipynb", "Offline synthetic by default; optional scoped Commercial reads."),
        ("02", "Govern model access", "Two APIM consumers / authentication / token counters",
         "02_govern_model_access.ipynb", "Paid model requests require explicit opt-in."),
        ("03", "Follow the evidence", "Native Agent 365 telemetry SDK / filter vs alert vs risk",
         "03_follow_the_evidence.ipynb", "Offline SDK initializer is mocked; no exporter or identity is fabricated."),
        ("04", "Governance overview", "Combined evidence / snapshots / provenance / exports",
         "04_governance_overview.ipynb", "Notebook snapshots are separate from this report's synthetic metrics."),
    ]
    for i, (num, title, description, file, boundary) in enumerate(entries):
        y = 225+i*159
        page.text(
            f"notebook-{num}", f"{num} | {title}\n{description}\n{boundary}",
            30, y, 1150, 130, size=16, background=SLATE,
        )
        page.button(f"open-notebook-{num}", "Open notebook source", f"{NOTEBOOKS}/{file}",
                    1210, y+42, 350, web=True)
    page.button("open-code", "Python evidence modules", f"{REPO}/tree/bp/ai-governance-oct28/src/governance",
                30, 885, 420, web=True, fill=TEAL)
    page.button("open-docs", "Demo code & documentation",
                f"{REPO}/blob/bp/ai-governance-oct28/docs/AIGovernanceDemo.md",
                480, 885, 480, web=True, fill=TEAL)
    return page


def build() -> None:
    write(PROJECT / f"{NAME}.pbip", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })
    write(PROJECT / f"{NAME}.SemanticModel/definition.pbism", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {"qnaEnabled": False},
    })
    write(REPORT / "definition.pbir", {
        "$schema": SCHEMA + "definitionProperties/2.0.0/schema.json", "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}},
    })
    write(REPORT / "definition/version.json", {
        "$schema": SCHEMA + "definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0",
    })
    write(REPORT / "definition/report.json", {
        "$schema": SCHEMA + "definition/report/3.0.0/schema.json",
        "themeCollection": {}, "settings": {"useStylableVisualContainerHeader": True},
    })
    write(REPORT / "definition/pages/pages.json", {
        "$schema": SCHEMA + "definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [name for name, _ in PAGES], "activePageName": "landing",
    })
    for factory in (landing, architecture, sources, runtime, notebooks):
        factory().save()
    print(f"Built {len(PAGES)} report pages under {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
