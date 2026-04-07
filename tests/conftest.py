"""Pytest configuration helpers for adding project root to Python path.

This ensures tests can import the top-level `src` package when pytest
is run from the repository root (or from the tests directory).
"""
import os
import sys

# Insert project root (one level above tests/) at front of sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
