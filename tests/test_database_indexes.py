import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.models import init_db


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"


def _index_columns(conn: sqlite3.Connection, index_name: str) -> list[str]:
    return [row[2] for row in conn.execute(f"PRAGMA index_info('{index_name}')").fetchall()]


def test_init_db_creates_composite_timestamp_symbol_indexes(tmp_path: Path):
    db_path = tmp_path / "poly_trader.sqlite"
    session = init_db(_sqlite_url(db_path))
    session.close()

    conn = sqlite3.connect(db_path)
    try:
        labels_indexes = {row[1] for row in conn.execute("PRAGMA index_list('labels')").fetchall()}
        features_indexes = {row[1] for row in conn.execute("PRAGMA index_list('features_normalized')").fetchall()}
        raw_indexes = {row[1] for row in conn.execute("PRAGMA index_list('raw_market_data')").fetchall()}

        assert "idx_labels_horizon_timestamp_symbol" in labels_indexes
        assert _index_columns(conn, "idx_labels_horizon_timestamp_symbol") == [
            "horizon_minutes",
            "timestamp",
            "symbol",
        ]

        assert "idx_features_timestamp_symbol" in features_indexes
        assert _index_columns(conn, "idx_features_timestamp_symbol") == [
            "timestamp",
            "symbol",
        ]

        assert "idx_raw_market_timestamp_symbol" in raw_indexes
        assert _index_columns(conn, "idx_raw_market_timestamp_symbol") == [
            "timestamp",
            "symbol",
        ]
    finally:
        conn.close()
