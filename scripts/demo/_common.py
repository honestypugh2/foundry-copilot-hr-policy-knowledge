"""Shared helpers for the demo / pattern-test scripts.

Keeps each ``test_pattern_*.py`` script short and consistent:
- Coloured stage banners
- Timing helper
- Result pretty-printer that always shows latency + citation count
- Default sample questions covering content / locator / hybrid intents
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from typing import Any, Iterator

# ---------------------------------------------------------------------------
# Console helpers — ANSI colours, no extra dependencies.
# ---------------------------------------------------------------------------
_USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def header(title: str, subtitle: str = "") -> None:
    bar = "=" * 76
    print()
    print(_c("1;36", bar))
    print(_c("1;36", f"  {title}"))
    if subtitle:
        print(_c("36", f"  {subtitle}"))
    print(_c("1;36", bar))


def stage(label: str, detail: str = "") -> None:
    print()
    print(_c("1;33", f"▶ {label}"))
    if detail:
        print(_c("33", f"  {detail}"))


def info(msg: str) -> None:
    print(_c("90", f"  {msg}"))


def ok(msg: str) -> None:
    print(_c("1;32", f"✔ {msg}"))


def warn(msg: str) -> None:
    print(_c("1;33", f"! {msg}"))


def err(msg: str) -> None:
    print(_c("1;31", f"✘ {msg}"))


@contextmanager
def timed(label: str) -> Iterator[dict[str, float]]:
    """Measure wall-clock latency for a code block."""
    box: dict[str, float] = {"start": time.time(), "elapsed_ms": 0.0}
    try:
        yield box
    finally:
        box["elapsed_ms"] = (time.time() - box["start"]) * 1000.0
        info(f"{label}: {box['elapsed_ms']:.0f} ms")


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------
def print_chat_result(result: dict[str, Any], *, max_chars: int = 800) -> None:
    """Render the canonical ``{answer, citations, policy_references, ...}`` shape."""
    answer = (result.get("answer") or "").strip()
    citations = result.get("citations") or []
    policy_refs = result.get("policy_references") or []
    confidence = result.get("confidence")

    print()
    print(_c("1", "  Answer:"))
    body = answer if len(answer) <= max_chars else answer[:max_chars] + " …"
    for line in body.splitlines():
        print(f"    {line}")
    print()
    print(_c("1", f"  Citations ({len(citations)}):"))
    for c in citations[:5]:
        pn = c.get("policy_number", "?")
        tt = c.get("title", "")
        print(f"    • Policy {pn} — {tt}")
    if policy_refs:
        print(_c("1", "  Policy references:"))
        for ref in policy_refs[:5]:
            print(f"    • {ref}")
    if confidence is not None:
        print(_c("1", f"  Confidence: {confidence}"))


def print_lookup_result(result: dict[str, Any]) -> None:
    """Render the ``/api/lookup`` shape (deterministic locator)."""
    docs = result.get("documents") or []
    query = result.get("query") or ""
    expanded = result.get("expanded_query") or ""
    elapsed = result.get("processing_time_ms")

    print()
    print(_c("1", f"  Query: {query}"))
    if expanded and expanded != query:
        print(_c("90", f"  Expanded (glossary): {expanded}"))
    if elapsed is not None:
        print(_c("90", f"  Server-side latency: {elapsed} ms"))
    print()
    print(_c("1", f"  Documents ({len(docs)}):"))
    if not docs:
        warn("    no matches")
        return
    for d in docs:
        print(f"    • Policy {d.get('policy_number','?')} — {d.get('parent_title','')}")
        path = d.get("metadata_storage_path") or d.get("blob_url") or ""
        if path:
            print(f"        path: {path}")
        score = d.get("score")
        if score is not None:
            print(f"        score: {score}")


# ---------------------------------------------------------------------------
# Sample questions used by every script + the storytelling demo
# ---------------------------------------------------------------------------
SAMPLE_CONTENT_QUESTION = "How much PTO do part-time employees accrue?"
SAMPLE_LOCATOR_QUESTION = "Where is the PTO policy stored?"
SAMPLE_HYBRID_QUESTION = (
    "Tell me about the Code of Ethics and where I can find the source document."
)


# ---------------------------------------------------------------------------
# Env / preflight helpers
# ---------------------------------------------------------------------------
def require_env(*names: str) -> tuple[bool, list[str]]:
    """Return ``(ok, missing)`` for the listed env vars."""
    missing = [n for n in names if not os.getenv(n)]
    return (len(missing) == 0, missing)


def preflight_block(label: str, names: tuple[str, ...]) -> bool:
    """Print a green/red preflight summary; return True if everything is present."""
    ok_flag, missing = require_env(*names)
    if ok_flag:
        ok(f"{label}: all required env vars present")
        return True
    err(f"{label}: missing env vars: {', '.join(missing)}")
    info("Set them in .env or export them in your shell, then re-run.")
    return False
