"""Validate generated PBIR against Microsoft's published schemas and local links."""

from __future__ import annotations

import json
from urllib.parse import urlparse

import httpx
import jsonschema
from referencing import Registry, Resource

from scripts.demo.powerbi.build_report import NAME, PAGES, PROJECT, REPORT, ROOT, TILES


def validate() -> None:
    cache = ROOT / ".local/schemas"
    cache.mkdir(parents=True, exist_ok=True)

    def retrieve(uri: str) -> Resource:
        parsed = urlparse(uri)
        if parsed.hostname != "developer.microsoft.com" or not parsed.path.startswith("/json-schemas/"):
            raise ValueError(f"Untrusted schema URI: {uri}")
        relative = parsed.path.removeprefix("/json-schemas/")
        path = cache / relative
        if path.exists():
            contents = json.loads(path.read_text())
        else:
            response = httpx.get(
                "https://raw.githubusercontent.com/microsoft/json-schemas/main/" + relative,
                timeout=40, follow_redirects=True,
            )
            response.raise_for_status()
            contents = response.json()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(contents))
        return Resource.from_contents(contents)

    registry = Registry(retrieve=retrieve)
    paths = sorted(REPORT.rglob("*.json")) + [REPORT / "definition.pbir",
        PROJECT / f"{NAME}.pbip", PROJECT / f"{NAME}.SemanticModel/definition.pbism"]
    for path in paths:
        document = json.loads(path.read_text())
        uri = document["$schema"]
        schema = retrieve(uri).contents
        validator = jsonschema.Draft7Validator(
            {"$ref": uri}, registry=registry.with_resource(uri, Resource.from_contents(schema)),
        )
        errors = sorted(validator.iter_errors(document), key=lambda error: str(error.path))
        if errors:
            raise ValueError(f"{path.relative_to(ROOT)}: {errors[0].message} at {list(errors[0].path)}")

    pages = {name for name, _ in PAGES}
    for path in (REPORT / "definition/pages").glob("*/visuals/*/visual.json"):
        visual = json.loads(path.read_text())
        position = visual["position"]
        if position["x"] < 0 or position["y"] < 0 or (
            position["x"] + position["width"] > 1600
            or position["y"] + position["height"] > 1000
        ):
            raise ValueError(f"Visual falls outside page: {path}")
        for link in visual["visual"]["visualContainerObjects"].get("visualLink", []):
            props = link["properties"]
            if "navigationSection" in props:
                target = props["navigationSection"]["expr"]["Literal"]["Value"].strip("'")
                if target not in pages:
                    raise ValueError(f"Broken page navigation: {target}")
    landing = REPORT / "definition/pages/landing/visuals"
    for key, *_ in TILES:
        if not (landing / f"tile-{key}-value/visual.json").exists():
            raise ValueError("Missing landing tile.")
    print(f"Validated {len(paths)} Power BI definition files against official schemas; nine tiles and navigation resolve.")


if __name__ == "__main__":
    validate()
