"""Shared constants and utilities imported directly by test modules."""
import sys
from pathlib import Path

import pytest

ROOT    = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "Sources"

# Make project scripts importable from tests
sys.path.insert(0, str(SOURCES / "TENDERS" / "scripts"))
sys.path.insert(0, str(SOURCES / "WORLDPOP" / "scripts"))
sys.path.insert(0, str(SOURCES / "IMD" / "scripts"))


def skip_if_missing(path: Path):
    """Skip the current test if a data file or directory does not exist."""
    if not Path(path).exists():
        pytest.skip(f"Data path not found: {path}")
