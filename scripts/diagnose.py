#!/usr/bin/env python3
"""Unified diagnostic entrypoint for Poly-Trader.

This replaces the old pile of one-off *_check.py scripts with a few stable modes:

  - health: DB/table/schema/data-quality summary
  - ic:     quick IC / regime IC report
  - env:    Python / venv / package sanity
  - dbs:    inspect all SQLite databases in the repo

Examples:
  python scripts/diagnose.py health
  python scripts/diagnose.py ic --label label_spot_long_win
  python scripts/diagnose.py env
  python scripts/diagnose.py dbs
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_CANDIDATES = [
    ROOT / "poly_trader.db",
    ROOT / "data" / "poly_trader.db",
    ROOT / "scripts" / "poly_trader.db",
    ROOT / "tests" / "poly_trader.db",
]

IMPORTANT_TABLES = [
    "features_normalized",
    "labels",
    "raw_market_data",
    "trade_history",
    "model_metrics",
]

FEATURE_PREFIXES = ("feat_",)


def pick_db_path(explicit: str | None = None) -> Path:
    if explicit:
        p = Path(explicit).expanduser()
        if p.exists():
            return p
        raise SystemExit(f"DB not found: {p}")

    env_db = os.getenv("POLY_TRADER_DB")
    if env_db:
        p = Path(env_db).expanduser()
        if p.exists():
            return p

    for p in DEFAULT_DB_CANDIDATES:
        if p.exists():
            return p

    # Fall back to any non-empty *.db under the repo.
    for p in sorted(ROOT.rglob("*.db")):
        try:
            if p.stat().st_size > 0:
                return p
        except OSError:
            continue

    raise SystemExit("No SQLite database found. Tried POLY_TRADER_DB and common repo paths.")


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    except sqlite3.DatabaseError:
        return []
    return [r["name"] for r in rows]


def table_count(conn: sqlite3.Connection, table: str) -> int | None:
    try:
        row = conn.execute(f'SELECT COUNT(*) AS c FROM "{table}"').fetchone()
        return int(row["c"]) if row is not None else None
    except sqlite3.DatabaseError:
        return None


def print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def safe_float(x):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def is_numeric_column(name: str, sample_values: Sequence[object]) -> bool:
    # Prefer the explicit feature prefixes and known numeric columns.
    if name.startswith(FEATURE_PREFIXES):
        return True
    numeric_hits = 0
    non_null = 0
    for v in sample_values:
        if v is None:
            continue
        non_null += 1
        if isinstance(v, (int, float)):
            numeric_hits += 1
            continue
        try:
            float(v)
            numeric_hits += 1
        except Exception:
            pass
    return non_null > 0 and numeric_hits / non_null >= 0.8


def pearson(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) < 3 or len(y) < 3:
        return None
    try:
        import numpy as np
    except Exception:
        return None
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    if np.nanstd(xa) == 0 or np.nanstd(ya) == 0:
        return None
    return float(np.corrcoef(xa, ya)[0, 1])


def describe_table(conn: sqlite3.Connection, table: str) -> None:
    cols = table_columns(conn, table)
    count = table_count(conn, table)
    if count is None:
        print(f"{table}: not available")
        return

    print(f"{table}: rows={count}, cols={len(cols)}")
    if not cols:
        return

    # Show recent timestamp if available.
    if "timestamp" in cols:
        try:
            latest = conn.execute(f'SELECT MAX(timestamp) AS ts FROM "{table}"').fetchone()["ts"]
            print(f"  latest timestamp: {latest}")
        except sqlite3.DatabaseError:
            pass

    # Show null coverage for useful columns.
    key_cols = [
        c for c in cols
        if c in {"timestamp", "symbol", "regime_label", "label_spot_long_win", "label_sell_win", "horizon_minutes"}
        or c.startswith("feat_")
        or c in {"close_price", "volume", "funding_rate", "fear_greed_index", "stablecoin_mcap", "polymarket_prob"}
    ]
    key_cols = key_cols[:14]
    if key_cols:
        items = []
        for c in key_cols:
            try:
                row = conn.execute(
                    f'SELECT COUNT(*) AS n, SUM(CASE WHEN "{c}" IS NOT NULL THEN 1 ELSE 0 END) AS nn FROM "{table}"'
                ).fetchone()
                n = int(row["n"])
                nn = int(row["nn"] or 0)
                items.append(f"{c}:{nn}/{n}({fmt_pct(nn / n if n else None)})")
            except sqlite3.DatabaseError:
                continue
        if items:
            print("  coverage:")
            for item in items:
                print(f"    - {item}")

    if "regime_label" in cols:
        try:
            rows = conn.execute(
                f'SELECT regime_label, COUNT(*) AS c FROM "{table}" GROUP BY regime_label ORDER BY c DESC'
            ).fetchall()
            dist = ", ".join([f"{r['regime_label']!s}:{r['c']}" for r in rows])
            print(f"  regime: {dist}")
        except sqlite3.DatabaseError:
            pass

    if table == "labels":
        for label_col in ["label_spot_long_win", "label_sell_win"]:
            if label_col in cols:
                try:
                    rows = conn.execute(
                        f'SELECT {label_col} AS v, COUNT(*) AS c FROM "{table}" GROUP BY {label_col} ORDER BY c DESC'
                    ).fetchall()
                    dist = ", ".join([f"{r['v']!s}:{r['c']}" for r in rows])
                    print(f"  {label_col}: {dist}")
                except sqlite3.DatabaseError:
                    pass


def health_mode(db_path: Path) -> None:
    print_section("Database")
    print(db_path)
    with connect(db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        print(f"tables: {[r['name'] for r in tables]}")

        for table in IMPORTANT_TABLES:
            print_section(table)
            describe_table(conn, table)

        # If features/labels exist, show a quick join summary.
        if "features_normalized" in {r['name'] for r in tables} and "labels" in {r['name'] for r in tables}:
            print_section("Feature/label join")
            try:
                exact = conn.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM features_normalized f
                    JOIN labels l ON f.timestamp = l.timestamp AND f.symbol = l.symbol
                    WHERE l.label_spot_long_win IS NOT NULL
                    """
                ).fetchone()["c"]
                ts_only = conn.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM features_normalized f
                    JOIN labels l ON f.timestamp = l.timestamp
                    WHERE l.label_spot_long_win IS NOT NULL
                    """
                ).fetchone()["c"]
                print(f"exact join rows (timestamp+symbol): {exact}")
                print(f"timestamp-only join rows: {ts_only}")
                if exact == 0 and ts_only > 0:
                    print("  note: symbol alignment is the blocker; label data exists but exact join misses it")
            except sqlite3.DatabaseError as e:
                print(f"join failed: {e}")


def collect_feature_rows(conn: sqlite3.Connection, label_col: str):
    cols = table_columns(conn, "features_normalized")
    if not cols:
        return [], []

    # Sample a handful of rows to infer numeric columns.
    sample = conn.execute('SELECT * FROM features_normalized LIMIT 50').fetchall()
    sample_map = {c: [] for c in cols}
    for row in sample:
        for c in cols:
            sample_map[c].append(row[c])

    feature_cols = [c for c in cols if is_numeric_column(c, sample_map[c]) and c not in {"id"}]
    feature_cols = [c for c in feature_cols if c not in {"timestamp", "symbol", "regime_label", label_col}]
    if not feature_cols:
        return [], []

    def fetch_rows(join_sql: str):
        return conn.execute(join_sql).fetchall()

    exact_sql = f'''
        SELECT f.timestamp AS timestamp,
               COALESCE(f.symbol, l.symbol) AS symbol,
               {', '.join([f'f."{c}" AS "{c}"' for c in feature_cols])},
               l."{label_col}" AS label,
               COALESCE(f.regime_label, l.regime_label) AS regime
        FROM features_normalized f
        JOIN labels l ON f.timestamp = l.timestamp AND f.symbol = l.symbol
        WHERE l."{label_col}" IS NOT NULL
        '''
    rows = fetch_rows(exact_sql)

    if not rows:
        ts_sql = f'''
            SELECT f.timestamp AS timestamp,
                   COALESCE(f.symbol, l.symbol) AS symbol,
                   {', '.join([f'f."{c}" AS "{c}"' for c in feature_cols])},
                   l."{label_col}" AS label,
                   COALESCE(f.regime_label, l.regime_label) AS regime
            FROM features_normalized f
            JOIN labels l ON f.timestamp = l.timestamp
            WHERE l."{label_col}" IS NOT NULL
            '''
        rows = fetch_rows(ts_sql)

    return feature_cols, rows


def ic_mode(db_path: Path, label_col: str) -> None:
    with connect(db_path) as conn:
        tables = {r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "features_normalized" not in tables or "labels" not in tables:
            raise SystemExit("ic mode requires features_normalized and labels tables")
        if label_col not in table_columns(conn, "labels"):
            raise SystemExit(f"label column not found in labels: {label_col}")

        feature_cols, rows = collect_feature_rows(conn, label_col)
        if not feature_cols:
            raise SystemExit("No numeric feature columns found")
        if not rows:
            raise SystemExit("No joined rows found; check timestamp/symbol alignment")

        print_section("IC summary")
        print(f"rows: {len(rows)}")
        print(f"label: {label_col}")

        # Global IC: compute per-feature correlations over available pairs only.
        scores = []
        for c in feature_cols:
            xs, ys = [], []
            for r in rows:
                x = safe_float(r[c])
                y = safe_float(r['label'])
                if x is None or y is None:
                    continue
                xs.append(x)
                ys.append(y)
            ic = pearson(xs, ys)
            if ic is not None:
                scores.append((abs(ic), ic, c, len(xs)))
        scores.sort(reverse=True)
        print("\nTop IC features:")
        for _, ic, c, n in scores[:20]:
            print(f"  {c:24s} IC={ic:+.4f}  n={n}")

        regimes = [str(r['regime'] or 'unknown') for r in rows]
        reg_counts = Counter(regimes)
        print("\nRegime counts:")
        for reg, cnt in sorted(reg_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {reg}: {cnt}")

        print("\nRegime IC (top 8 per regime):")
        regime_indexed = defaultdict(list)
        for i, reg in enumerate(regimes):
            regime_indexed[reg].append(i)

        for reg, idxs in sorted(regime_indexed.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            if len(idxs) < 50:
                continue
            reg_scores = []
            for c in feature_cols:
                xs, ys = [], []
                for i in idxs:
                    x = safe_float(rows[i][c])
                    y = safe_float(rows[i]['label'])
                    if x is None or y is None:
                        continue
                    xs.append(x)
                    ys.append(y)
                ic = pearson(xs, ys)
                if ic is not None:
                    reg_scores.append((abs(ic), ic, c))
            reg_scores.sort(reverse=True)
            print(f"  {reg} (n={len(idxs)}):")
            for _, ic, c in reg_scores[:8]:
                print(f"    {c:24s} IC={ic:+.4f}")


def env_mode() -> None:
    print_section("Python")
    print(sys.executable)
    print(sys.version.replace("\n", " "))

    print_section("Project root")
    print(ROOT)

    print_section("Venv")
    venv_python = ROOT / "venv" / "bin" / "python"
    print(f"exists: {venv_python.exists()}")
    if venv_python.exists():
        print(f"path: {venv_python}")

    print_section("Core packages")
    for pkg in ["numpy", "pandas", "sqlalchemy", "sklearn"]:
        spec = importlib.util.find_spec(pkg)
        if spec is None:
            print(f"{pkg}: MISSING")
            continue
        try:
            mod = __import__(pkg)
            print(f"{pkg}: {getattr(mod, '__version__', 'installed')}")
        except Exception:
            print(f"{pkg}: installed")


def dbs_mode() -> None:
    print_section("SQLite databases")
    candidates = sorted({*DEFAULT_DB_CANDIDATES, *ROOT.rglob("*.db")})
    for p in candidates:
        if not p.exists() or p.stat().st_size == 0:
            continue
        try:
            conn = sqlite3.connect(str(p))
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            print(f"{p.relative_to(ROOT) if p.is_relative_to(ROOT) else p}: {len(tables)} tables")
            conn.close()
        except Exception as e:
            print(f"{p}: ERROR {e}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--db", help="Explicit SQLite DB path")
    sub = parser.add_subparsers(dest="command", required=True)

    p_health = sub.add_parser("health", help="DB / schema / data quality summary", parents=[parent])
    p_health.set_defaults(func=lambda a: health_mode(pick_db_path(a.db)))

    p_ic = sub.add_parser("ic", help="IC / regime IC report", parents=[parent])
    p_ic.add_argument("--label", default="label_spot_long_win", help="Label column to score against")
    p_ic.set_defaults(func=lambda a: ic_mode(pick_db_path(a.db), a.label))

    p_env = sub.add_parser("env", help="Environment sanity checks", parents=[parent])
    p_env.set_defaults(func=lambda a: env_mode())

    p_dbs = sub.add_parser("dbs", help="List SQLite DBs in the repo", parents=[parent])
    p_dbs.set_defaults(func=lambda a: dbs_mode())

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
