import threading
from pathlib import Path

# DuckDB refuses to open a connection to a file with a different
# configuration than an already-open connection in the same process (e.g.
# read_only=True while another connection holds it read-write). API query
# helpers (queries.py) open read-only connections while the sync job
# (sync_job.py) runs normalize with a read-write connection; both must
# acquire this lock before opening a connection so they never overlap.
DUCKDB_LOCK = threading.Lock()


def duckdb_available(path: Path) -> bool:
    return path.is_file()
