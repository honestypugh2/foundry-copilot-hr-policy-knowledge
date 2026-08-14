"""CLI for the Copilot Studio Credits cost lane (estimate + reconcile).

Examples:
  # Forward estimate of Credits/message for a pattern (35 measured messages):
  python -m src.benchmarking.copilot_credits_cli estimate \
    --pattern C --messages 35 \
    --output experiments/reports/decision-system-20260811/copilot-front-door/c/release-v2/credits-estimate.json

  # Reconcile the estimate against billed Credits exported from the
  # Power Platform admin center consumption grid:
  python -m src.benchmarking.copilot_credits_cli reconcile \
    --pattern C --messages 35 \
    --consumption ~/Downloads/copilot-studio-consumption.csv \
    --output .../credits-reconciliation.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.benchmarking.copilot_credits import (
    estimate_pattern,
    parse_consumption_csv,
    reconcile,
)

DEFAULT_RATE_CARD = Path(
    "experiments/pricing/copilot-studio-credits-standard-harness-2026-08-01.json"
)
DEFAULT_FEATURE_MIX = Path("experiments/pricing/copilot-studio-credits-feature-mix.json")


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pattern", required=True, help="A, A2, B, C, or Hosted")
    parser.add_argument("--messages", type=int, default=1)
    parser.add_argument("--rate-card", type=Path, default=DEFAULT_RATE_CARD)
    parser.add_argument("--feature-mix", type=Path, default=DEFAULT_FEATURE_MIX)
    parser.add_argument("--output", type=Path, default=None)


def _write(output: Path | None, payload: dict) -> None:
    text = json.dumps(payload, indent=2) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(f"Wrote {output}")
    else:
        print(text)


def _estimate(args: argparse.Namespace) -> int:
    estimate = estimate_pattern(
        args.pattern,
        rate_card_path=args.rate_card,
        feature_mix_path=args.feature_mix,
        messages=args.messages,
    )
    _write(args.output, estimate.model_dump())
    print(
        f"{args.pattern}: {estimate.credits_per_message:g} Credits/message x "
        f"{estimate.messages} = {estimate.estimated_total_credits:g} Credits "
        f"(estimate){' + Foundry tokens (separate lane)' if estimate.byo_foundry_tokens else ''}"
    )
    return 0


def _reconcile(args: argparse.Namespace) -> int:
    estimate = estimate_pattern(
        args.pattern,
        rate_card_path=args.rate_card,
        feature_mix_path=args.feature_mix,
        messages=args.messages,
    )
    consumption = parse_consumption_csv(args.consumption)
    result = reconcile(estimate, consumption)
    _write(
        args.output,
        {"estimate": estimate.model_dump(), "reconciliation": result.model_dump()},
    )
    print(
        f"{args.pattern}: estimated {result.estimated_total_credits:g} vs billed "
        f"{result.billed_total_credits:g} Credits (delta {result.delta_credits:+g})"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copilot Studio Credits cost lane")
    sub = parser.add_subparsers(dest="command", required=True)

    estimate = sub.add_parser("estimate", help="Forward Credits estimate from config")
    _add_common(estimate)
    estimate.set_defaults(func=_estimate)

    rec = sub.add_parser("reconcile", help="Compare estimate to billed consumption")
    _add_common(rec)
    rec.add_argument(
        "--consumption",
        type=Path,
        required=True,
        help="CSV exported from the admin-center consumption grid (agent,credits[,period,meter])",
    )
    rec.set_defaults(func=_reconcile)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
