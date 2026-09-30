"""Paths to the liblouis tables bundled with this package."""
from pathlib import Path

TABLES_DIR = Path(__file__).parent / "tables"


def table_path(name: str) -> str:
    """Absolute path of a bundled table, usable in a liblouis table list."""
    return str(TABLES_DIR / name)
