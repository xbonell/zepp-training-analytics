from pathlib import Path


def duckdb_available(path: Path) -> bool:
    return path.is_file()
