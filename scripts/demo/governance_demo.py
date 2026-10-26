"""Governance evidence CLI: offline by default; --live performs scoped reads only."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

from src.governance.evidence import (
    coverage,
    export_estate,
    load_snapshot,
    markdown_table,
    overview,
    synthetic_estate,
)
from src.governance.live import collect_live


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="Read one Commercial project/resource group.")
    mode.add_argument("--snapshot", type=Path, help="Read a prior normalized export; preserve timestamps.")
    parser.add_argument("--export", type=Path, help="Write normalized JSON and CSV into a new directory.")
    parser.add_argument("--hosted-principal-id", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        if args.live:
            load_dotenv(Path(__file__).resolve().parents[2] / ".env")
            estate = collect_live(os.environ, tuple(args.hosted_principal_id))
        elif args.snapshot:
            estate = load_snapshot(args.snapshot)
        else:
            estate = synthetic_estate()
        print("Governance evidence overview (not a compliance or risk score)")
        print(markdown_table(overview(estate)))
        print("\nEvidence kinds:", coverage(estate))
        for row in estate.evidence:
            if row.status in ("error", "unknown"):
                print(f"[{row.status.upper()}] {row.asset_id}: {row.observation}")
        if args.export:
            for path in export_estate(estate, args.export):
                print(f"Exported: {path}")
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"[FAIL] {exc}")
        return 1
    if any(row.status == "error" for row in estate.evidence):
        return 1
    return 2 if any(row.status == "unknown" for row in estate.evidence) else 0


if __name__ == "__main__":
    raise SystemExit(main())
