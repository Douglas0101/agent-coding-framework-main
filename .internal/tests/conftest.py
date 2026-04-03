"""Pytest configuration for .internal/ test suite.

Adds .internal/ to sys.path so tests can import from scripts/ and other
sibling packages within the .internal/ directory.
"""

import sys
from pathlib import Path

INTERNAL_ROOT = Path(__file__).resolve().parent

if str(INTERNAL_ROOT) not in sys.path:
    sys.path.insert(0, str(INTERNAL_ROOT))
