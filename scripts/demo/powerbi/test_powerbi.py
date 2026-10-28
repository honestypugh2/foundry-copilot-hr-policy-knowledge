"""Offline tests for synthetic report layout and safe service packaging."""

import base64
import json
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from scripts.demo.powerbi import build_report as report
from scripts.demo.powerbi import service


@pytest.fixture
def pages():
    return [report.landing(), report.architecture(), report.sources(),
            report.runtime(), report.notebooks()]


def test_all_pages_have_explicit_provenance_and_valid_navigation(pages):
    names = {name for name, _ in report.PAGES}
    for page in pages:
        banner = next(v for v in page.visuals if v["name"] == "synthetic-banner")
        text = json.dumps(banner)
        assert "SYNTHETIC DEMO" in text
        assert "Azure Commercial" in text
        assert "simulated" in text
        for visual in page.visuals:
            pos = visual["position"]
            assert 0 <= pos["x"] <= 1600 - pos["width"]
            assert 0 <= pos["y"] <= 1000 - pos["height"]
            for link in visual["visual"]["visualContainerObjects"].get("visualLink", []):
                props = link["properties"]
                if "navigationSection" in props:
                    assert props["navigationSection"]["expr"]["Literal"]["Value"].strip("'") in names


@pytest.mark.parametrize("tile", report.TILES)
def test_landing_tiles_bind_measures_not_static_numbers(tile):
    key, _, measure, *_ = tile
    visuals = {v["name"]: v for v in report.landing().visuals}
    value = visuals[f"tile-{key}-value"]["visual"]["query"]["queryState"]["Values"]["projections"]
    assert value == [report.projection("Observations", measure, measure=True)]
    phase = json.dumps(visuals[f"tile-{key}-phase"])
    assert ("CRAWL" if key <= 6 else "WALK") in phase
    assert "SYNTHETIC" in phase


def test_all_button_labels_and_colors_target_default_render_state(pages):
    count = 0
    for page in pages:
        for visual in page.visuals:
            if visual["visual"]["visualType"] != "actionButton":
                continue
            objects = visual["visual"]["objects"]
            text = objects["text"]
            assert any("selector" not in entry and entry["properties"].get("show") == report.literal(True)
                       for entry in text)
            default = next(entry["properties"] for entry in text
                           if entry.get("selector") == {"id": "default"})
            assert default["text"]["expr"]["Literal"]["Value"].strip("'")
            assert default["fontColor"] == report.color(report.WHITE)
            assert default["horizontalAlignment"] == report.literal("center")
            assert default["verticalAlignment"] == report.literal("middle")
            fill = next(entry for entry in objects["fill"]
                        if entry.get("selector") == {"id": "default"})
            assert fill["properties"]["show"] == report.literal(True)
            count += 1
    assert count == 49


def test_package_rebinds_without_mutating_local_reference(tmp_path):
    local = {"datasetReference": {"byPath": {"path": "../model.SemanticModel"}}}
    (tmp_path / "definition.pbir").write_text(json.dumps(local))
    (tmp_path / "notes.txt").write_text("do not upload")
    (tmp_path / ".pbi").mkdir()
    (tmp_path / ".pbi/cache.json").write_text("{}")
    payload = service.definition(tmp_path, "model-id")
    assert len(payload["parts"]) == 1
    remote = json.loads(base64.b64decode(payload["parts"][0]["payload"]))
    assert remote["datasetReference"] == {
        "byConnection": {"connectionString": "semanticmodelid=model-id"},
    }
    assert json.loads((tmp_path / "definition.pbir").read_text()) == local


def test_duplicate_report_is_never_recreated():
    fake = Mock()
    fake.values.return_value = [
        {"type": "SemanticModel", "displayName": report.NAME, "id": "model"},
        {"type": "Report", "displayName": report.NAME, "id": "existing"},
    ]
    with pytest.raises(FileExistsError):
        service.publish(fake, {"id": "workspace"})
    fake.request.assert_not_called()


@pytest.mark.parametrize("url", [
    "https://example.com/v1/workspaces",
    "https://api.fabric.microsoft.com:444/v1/workspaces",
    "https://api.fabric.microsoft.com/other",
])
def test_credentials_never_leave_canonical_fabric_host(url):
    fake = SimpleNamespace(client=Mock())
    with pytest.raises(ValueError, match="credentials"):
        service.Service.request(fake, "GET", url)
    fake.client.request.assert_not_called()


def test_regional_lro_uses_canonical_api_without_requiring_result(monkeypatch):
    op = "427f6c34-b64e-4ee4-8ea5-b533c0e203ef"
    initial = httpx.Response(202, headers={
        "Location": f"https://regional.analysis.windows.net/v1/operations/{op}",
        "x-ms-operation-id": op,
    })
    fake = Mock()
    fake.request.return_value = httpx.Response(200, json={"status": "Succeeded"})
    monkeypatch.setattr(service.time, "sleep", lambda _: None)
    assert service.Service.complete(fake, initial) == {"status": "Succeeded"}
    assert [call.args for call in fake.request.call_args_list] == [
        ("GET", f"/operations/{op}"),
    ]


def test_bad_operation_id_cannot_be_followed():
    fake = Mock()
    with pytest.raises(ValueError):
        service.Service.complete(fake, httpx.Response(202, headers={
            "Location": "https://example.com/leak-token",
        }))
    fake.request.assert_not_called()


def test_wrong_tenant_token_rejected(monkeypatch):
    claims = base64.urlsafe_b64encode(json.dumps({"tid": "other"}).encode()).decode().rstrip("=")
    result = SimpleNamespace(returncode=0, stdout=json.dumps({"accessToken": f"x.{claims}.x"}))
    monkeypatch.setattr(service.subprocess, "run", lambda *args, **kwargs: result)
    with pytest.raises(ValueError, match="tenant"):
        service.access_token("https://api.fabric.microsoft.com")


def test_update_rejects_receipt_for_different_item(tmp_path, monkeypatch):
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"workspace_id": "w", "model_id": "m", "report_id": "other"}))
    monkeypatch.setattr(service, "inspect_report", lambda *args: {
        "workspace_id": "w", "model_id": "m", "report_id": "own",
    })
    fake = Mock()
    with pytest.raises(ValueError, match="refusing update"):
        service.update_report(fake, {"id": "w"}, receipt)
    fake.request.assert_not_called()


def test_validate_only_checks_exact_values_and_blank_total(monkeypatch):
    names = ["Missing Owners", "Registered Agents", "Blocked Apps", "Sensitive Events",
             "Source Incidents", "Usage Sessions", "Guardrail Blocks", "Illustrative Cost", "Drift Flags"]
    rows = {f"[{name}]": value for name, value in zip(
        names, [7, 12, 5, 9, 3, 2480, 18, 146.25, 2], strict=True,
    )}
    rows["[Mixed Units]"] = None
    client = Mock()
    client.post.return_value = httpx.Response(
        200, json={"results": [{"tables": [{"rows": [rows]}]}]},
        request=httpx.Request("POST", "https://api.powerbi.com"),
    )
    manager = Mock()
    manager.__enter__ = Mock(return_value=client)
    manager.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(service.httpx, "Client", lambda **kwargs: manager)
    monkeypatch.setattr(service, "access_token", lambda _: "fake")
    result = service.refresh_and_validate({"id": "w"}, "m", refresh=False)
    assert result["refresh"] == "Not requested"
    assert client.post.call_count == 1
    assert client.post.call_args.args[0].endswith("/executeQueries")
    rows["[Mixed Units]"] = 1
    client.post.return_value = httpx.Response(
        200, json={"results": [{"tables": [{"rows": [rows]}]}]},
        request=httpx.Request("POST", "https://api.powerbi.com"),
    )
    with pytest.raises(ValueError, match="Mixed units"):
        service.refresh_and_validate({"id": "w"}, "m", refresh=False)


def test_scaffold_generates_local_model_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "ROOT", tmp_path)
    monkeypatch.setattr(report, "PROJECT", tmp_path)
    monkeypatch.setattr(report, "REPORT", tmp_path / f"{report.NAME}.Report")
    report.build()
    reference = json.loads((report.REPORT / "definition.pbir").read_text())
    assert reference["datasetReference"]["byPath"]["path"] == f"../{report.NAME}.SemanticModel"
    metadata = json.loads((report.REPORT / "definition/pages/pages.json").read_text())
    assert metadata["pageOrder"] == [name for name, _ in report.PAGES]
