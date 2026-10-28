"""Publish only isolated pwwdemo Power BI items; validate with read-only DAX."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import httpx

from scripts.demo.powerbi.build_report import NAME, PAGES, REPORT, ROOT

FABRIC = "https://api.fabric.microsoft.com/v1"
PBI = "https://api.powerbi.com/v1.0/myorg"
TENANT = "8632ad35-17e0-4994-978b-61afd7ed90d7"


def access_token(audience: str) -> str:
    result = subprocess.run(
        ["az", "account", "get-access-token", "--resource", audience, "-o", "json"],
        text=True, capture_output=True, timeout=60,
    )
    if result.returncode:
        raise RuntimeError("Azure CLI token acquisition failed; authenticate in the demo tenant.")
    token = json.loads(result.stdout)["accessToken"]
    encoded = token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    if claims.get("tid") != TENANT:
        raise ValueError("Token tenant does not match the authorized demo tenant.")
    return token


class Service:
    def __init__(self):
        self.client = httpx.Client(timeout=90, headers={
            "Authorization": "Bearer " + access_token("https://api.fabric.microsoft.com"),
            "x-ms-fabric-skill": "semantic-model-authoring",
        })

    def close(self) -> None:
        self.client.close()

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = path if path.startswith("https://") else FABRIC + path
        parsed = urlparse(url)
        if (parsed.scheme != "https" or parsed.netloc != "api.fabric.microsoft.com"
                or not parsed.path.startswith("/v1/")):
            raise ValueError("Refusing to send credentials outside the Fabric API.")
        response = self.client.request(method, url, **kwargs)
        if response.is_error:
            raise RuntimeError(f"Fabric {method} failed ({response.status_code}): {response.text[:1500]}")
        return response

    def values(self, path: str) -> list[dict]:
        rows = []
        while path:
            body = self.request("GET", path).json()
            rows.extend(body["value"])
            path = body.get("continuationUri", "")
        return rows

    def workspace(self, name: str) -> dict:
        matches = [w for w in self.values("/workspaces") if w["displayName"] == name]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one accessible workspace named {name!r}.")
        workspace = matches[0]
        details = self.request("GET", f"/workspaces/{workspace['id']}").json()
        capacities = self.values("/capacities")
        capacity = next((c for c in capacities if c["id"] == details.get("capacityId")), None)
        if not capacity or capacity.get("state") != "Active":
            raise ValueError("Workspace must have an accessible active capacity.")
        return workspace

    def complete(self, response: httpx.Response) -> dict:
        if response.status_code != 202:
            return response.json() if response.content else {}
        operation = response.headers.get("x-ms-operation-id")
        if not operation:
            operation = urlparse(response.headers["Location"]).path.rstrip("/").rsplit("/", 1)[-1]
        location = f"/operations/{UUID(operation)}"
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            time.sleep(max(1, min(int(response.headers.get("Retry-After", "3")), 15)))
            response = self.request("GET", location)
            body = response.json()
            if body.get("status") in ("Failed", "Cancelled"):
                raise RuntimeError(f"Fabric operation failed: {body}")
            if body.get("status") == "Succeeded":
                return body
        raise TimeoutError("Fabric operation still pending; inspect workspace before retrying.")


def definition(folder: Path, model_id: str | None = None) -> dict:
    parts = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or ".pbi" in path.parts or path.name == ".platform":
            continue
        relative = path.relative_to(folder).as_posix()
        if not (relative in ("definition.pbir", "definition.pbism")
                or relative.startswith("definition/") and path.suffix in (".json", ".tmdl")):
            continue
        data = path.read_bytes()
        if relative == "definition.pbir" and model_id:
            body = json.loads(data)
            body["datasetReference"] = {"byConnection": {"connectionString": f"semanticmodelid={model_id}"}}
            data = json.dumps(body).encode()
        parts.append({
            "path": relative, "payload": base64.b64encode(data).decode(),
            "payloadType": "InlineBase64",
        })
    if not parts:
        raise ValueError("No definition parts found.")
    return {"parts": parts}


def publish(service: Service, workspace: dict) -> dict:
    wid = workspace["id"]
    items = service.values(f"/workspaces/{wid}/items")
    models = [i for i in items if i["type"] == "SemanticModel" and i["displayName"] == NAME]
    if len(models) != 1:
        raise ValueError("Expected the single MCP-authored model; do not retry model deployment blindly.")
    model_id = models[0]["id"]
    reports = [i for i in items if i["type"] == "Report" and i["displayName"] == NAME]
    if reports:
        raise FileExistsError("Report already exists; refusing to overwrite or create a duplicate.")
    body = {
        "displayName": NAME, "description": "Synthetic AI governance landing page; no live cross-cloud feeds.",
        "definition": definition(REPORT, model_id),
    }
    result = service.complete(service.request("POST", f"/workspaces/{wid}/reports", json=body))
    if not result.get("id"):
        matches = [i for i in service.values(f"/workspaces/{wid}/items")
                   if i["type"] == "Report" and i["displayName"] == NAME]
        if len(matches) != 1:
            raise RuntimeError("Report create finished but item identity is ambiguous; inspect workspace.")
        result = matches[0]
    return {
        "workspace_id": wid, "workspace_name": workspace["displayName"],
        "model_id": model_id, "report_id": result["id"],
        "report_url": f"https://app.powerbi.com/groups/{wid}/reports/{result['id']}",
        "evidence_kind": "Synthetic", "fixture_date": "2026-10-28",
    }


def inspect_report(service: Service, workspace: dict) -> dict:
    """Recover a receipt and verify the binding/pages without creating any item."""
    wid = workspace["id"]
    items = service.values(f"/workspaces/{wid}/items")
    models = [i for i in items if i["type"] == "SemanticModel" and i["displayName"] == NAME]
    reports = [i for i in items if i["type"] == "Report" and i["displayName"] == NAME]
    if len(models) != 1 or len(reports) != 1:
        raise ValueError("Expected exactly one governance report and semantic model.")
    report_id, model_id = reports[0]["id"], models[0]["id"]
    with httpx.Client(timeout=90, headers={
        "Authorization": "Bearer " + access_token("https://analysis.windows.net/powerbi/api"),
    }) as client:
        base = f"{PBI}/groups/{wid}/reports/{report_id}"
        response = client.get(base)
        response.raise_for_status()
        if response.json().get("datasetId") != model_id:
            raise ValueError("Published report is not bound to the expected governance model.")
        response = client.get(base + "/pages")
        response.raise_for_status()
        pages = response.json()["value"]
        if {p["displayName"] for p in pages} != {title for _, title in PAGES}:
            raise ValueError("Published report pages do not match the five-page source.")
    return {
        "workspace_id": wid, "workspace_name": workspace["displayName"],
        "model_id": model_id, "report_id": report_id,
        "report_url": f"https://app.powerbi.com/groups/{wid}/reports/{report_id}",
        "evidence_kind": "Synthetic", "fixture_date": "2026-10-28", "pages": pages,
    }


def update_report(service: Service, workspace: dict, receipt_path: Path) -> dict:
    receipt = json.loads(receipt_path.read_text())
    current = inspect_report(service, workspace)
    if any(receipt.get(key) != current[key] for key in ("workspace_id", "model_id", "report_id")):
        raise ValueError("Receipt does not match the deployed governance items; refusing update.")
    service.complete(service.request(
        "POST",
        f"/workspaces/{current['workspace_id']}/reports/{current['report_id']}/updateDefinition",
        json={"definition": definition(REPORT, current["model_id"])},
    ))
    return inspect_report(service, workspace)


def refresh_and_validate(workspace: dict, model_id: str, *, refresh: bool = True) -> dict:
    with httpx.Client(timeout=90, headers={
        "Authorization": "Bearer " + access_token("https://analysis.windows.net/powerbi/api"),
    }) as client:
        base = f"{PBI}/groups/{workspace['id']}/datasets/{model_id}"
        if refresh:
            response = client.post(base + "/refreshes", json={"type": "Full", "commitMode": "transactional"})
            response.raise_for_status()
            location = response.headers.get("Location")
            if not location:
                raise RuntimeError("Refresh accepted without a polling location; inspect the service.")
            # Regional Location hosts are normal; poll through the canonical PBI
            # API with a validated operation ID rather than forwarding credentials.
            request_id = str(UUID(urlparse(location).path.rstrip("/").rsplit("/", 1)[-1]))
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                result = client.get(base + "/refreshes/" + request_id)
                result.raise_for_status()
                body = result.json()
                if body.get("status") == "Completed":
                    break
                if body.get("status") in ("Failed", "Cancelled", "Disabled"):
                    raise RuntimeError(f"Refresh failed; configure connections in the service: {body}")
                time.sleep(3)
            else:
                raise TimeoutError("Refresh still pending; inspect the service before retrying.")
        dax = (
            'EVALUATE ROW("Missing Owners",[Missing Owners],"Registered Agents",[Registered Agents],'
            '"Blocked Apps",[Blocked Apps],"Sensitive Events",[Sensitive Events],'
            '"Source Incidents",[Source Incidents],"Usage Sessions",[Usage Sessions],'
            '"Guardrail Blocks",[Guardrail Blocks],"Illustrative Cost",[Illustrative Cost],'
            '"Drift Flags",[Drift Flags],"Mixed Units",[Latest Value])'
        )
        response = client.post(base + "/executeQueries", json={
            "queries": [{"query": dax}], "serializerSettings": {"includeNulls": True},
        })
        response.raise_for_status()
        data = response.json()
        if "error" in data or any("error" in r for r in data.get("results", [])):
            raise RuntimeError(f"DAX validation failed: {data}")
        rows = data["results"][0]["tables"][0]["rows"]
        expected = [7, 12, 5, 9, 3, 2480, 18, 146.25, 2]
        names = ["Missing Owners", "Registered Agents", "Blocked Apps", "Sensitive Events",
                 "Source Incidents", "Usage Sessions", "Guardrail Blocks", "Illustrative Cost", "Drift Flags"]
        for name, value in zip(names, expected, strict=True):
            if rows[0][f"[{name}]"] != value:
                raise ValueError(f"Unexpected synthetic measure: {name}")
        if rows[0].get("[Mixed Units]") is not None:
            raise ValueError("Mixed units must never produce an aggregate.")
        return {"refresh": "Completed" if refresh else "Not requested", "measures": rows[0]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default="ffia-hc01-lab")
    parser.add_argument("--publish-report", action="store_true")
    parser.add_argument("--refresh-validate", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--inspect-report", action="store_true")
    parser.add_argument("--update-report", action="store_true")
    args = parser.parse_args()
    if not any((args.publish_report, args.refresh_validate, args.validate_only,
                args.inspect_report, args.update_report)):
        parser.error("Choose a publish, update, inspect, refresh or validation operation.")
    if args.publish_report and args.update_report:
        parser.error("Publish and update are mutually exclusive.")
    service = Service()
    try:
        workspace = service.workspace(args.workspace)
        receipt_path = ROOT / ".local/deployment.json"
        if args.publish_report:
            receipt = publish(service, workspace)
            receipt_path.parent.mkdir(exist_ok=True)
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
            print(json.dumps(receipt, indent=2))
        if args.inspect_report:
            receipt = inspect_report(service, workspace)
            receipt_path.parent.mkdir(exist_ok=True)
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
            print(json.dumps(receipt, indent=2))
        if args.update_report:
            receipt = update_report(service, workspace, receipt_path)
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
            print(json.dumps(receipt, indent=2))
        if args.refresh_validate or args.validate_only:
            models = [i for i in service.values(f"/workspaces/{workspace['id']}/items")
                      if i["type"] == "SemanticModel" and i["displayName"] == NAME]
            if len(models) != 1:
                raise ValueError("Semantic model name is missing or ambiguous.")
            print(json.dumps(refresh_and_validate(
                workspace, models[0]["id"], refresh=args.refresh_validate,
            ), indent=2))
    finally:
        service.close()


if __name__ == "__main__":
    main()
