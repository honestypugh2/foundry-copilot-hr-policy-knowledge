"""
Generate a visual architecture diagram for the SharePoint → Logic Apps →
Document Intelligence → Azure AI Search → Copilot Studio pipeline.

Usage:
    source .venv/bin/activate
    python scripts/generate_architecture_diagram.py

Output: docs/sharepoint_logicapps_architecture.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.azure.integration import LogicApps, PowerPlatform
from diagrams.azure.aimachinelearning import FormRecognizers, CognitiveSearch, AzureOpenai
from diagrams.azure.ml import BotServices
from diagrams.azure.storage import BlobStorage
from diagrams.azure.general import Files
from diagrams.custom import Custom
import os
import urllib.request

# ---------------------------------------------------------------------------
# Download a SharePoint icon (not included in the diagrams library)
# ---------------------------------------------------------------------------
ICON_DIR = os.path.join(os.path.dirname(__file__), ".icons")
os.makedirs(ICON_DIR, exist_ok=True)

SHAREPOINT_ICON = os.path.join(ICON_DIR, "sharepoint.png")
COPILOT_STUDIO_ICON = os.path.join(ICON_DIR, "copilot_studio.png")
TEAMS_ICON = os.path.join(ICON_DIR, "teams.png")

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "sharepoint_logicapps_architecture")

graph_attr = {
    "fontsize": "20",
    "bgcolor": "white",
    "pad": "0.5",
    "ranksep": "1.2",
    "nodesep": "0.8",
    "splines": "ortho",
}

node_attr = {
    "fontsize": "12",
}

edge_attr = {
    "color": "#333333",
    "penwidth": "1.5",
}

with Diagram(
    "HR Policy Knowledge — SharePoint to Copilot Studio",
    filename=OUTPUT_PATH,
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
    outformat="png",
):

    # ── SharePoint Online ──────────────────────────────────────────────
    with Cluster("SharePoint Online", graph_attr={"bgcolor": "#e8f4e8", "style": "rounded"}):
        sharepoint = Files("HR Policy Library\n(.docx / .pdf)")

    # ── Azure Logic Apps ───────────────────────────────────────────────
    with Cluster("Azure Logic Apps — Orchestration", graph_attr={"bgcolor": "#e8edf4", "style": "rounded"}):
        trigger = LogicApps("1. Trigger\n(file created/modified)")
        get_file = LogicApps("2. Get File Content")
        doc_intel = FormRecognizers("3. Document Intelligence\n(prebuilt-layout)")
        chunk = LogicApps("4. Chunk + Metadata")
        embed = AzureOpenai("5. Generate Embeddings\n(text-embedding-3-small)")
        push = LogicApps("6. Push to Index")

        trigger >> Edge(label="SharePoint event") >> get_file
        get_file >> Edge(label="binary content") >> doc_intel
        doc_intel >> Edge(label="structured JSON") >> chunk
        chunk >> Edge(label="chunks") >> embed
        embed >> Edge(label="vectors") >> push

    # ── Azure AI Search ────────────────────────────────────────────────
    with Cluster("Azure AI Search (RAG-ready)", graph_attr={"bgcolor": "#fef3e0", "style": "rounded"}):
        search_index = CognitiveSearch("hr-policy-index\n(vector + semantic)")

    # ── Copilot Studio ─────────────────────────────────────────────────
    with Cluster("Copilot Studio Agent", graph_attr={"bgcolor": "#f3e8f4", "style": "rounded"}):
        copilot = BotServices("Ask HR Policy Agent")
        knowledge = CognitiveSearch("Knowledge Source\n(Azure AI Search)")
        channels = PowerPlatform("Channels\n(Teams / Web Chat)")

        copilot >> Edge(label="hybrid retrieval") >> knowledge
        copilot >> Edge(label="publish") >> channels

    # ── Connections between clusters ───────────────────────────────────
    sharepoint >> Edge(label="file event trigger", style="bold", color="#0078d4") >> trigger
    push >> Edge(label="index documents + vectors", style="bold", color="#0078d4") >> search_index
    search_index >> Edge(label="vector + semantic ranker", style="bold", color="#0078d4") >> knowledge

print(f"\nDiagram saved to: {os.path.abspath(OUTPUT_PATH)}.png")
