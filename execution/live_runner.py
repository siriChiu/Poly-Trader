from __future__ import annotations

import hashlib
import json
import pickle
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
from sqlalchemy import text

from backtesting import strategy_lab
from backtesting.model_leaderboard import ModelLeaderboard
from data_ingestion.collector import run_collection_and_save
from execution.execution_service import ExecutionRejectError, ExecutionService
from feature_engine.preprocessor import run_preprocessor
from utils.logger import setup_logger

logger = setup_logger(__name__, log_file="data/live_trading/poly_trader_live.log")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIVE_MODEL_ROOT = PROJECT_ROOT / "data" / "live_models"
DEFAULT_LIVE_TRADING_ROOT = PROJECT_ROOT / "data" / "live_trading"

SENSITIVE_KEYS = {"api_key", "apikey", "api_secret", "apisecret", "passphrase", "secret", "password", "token"}
SHADOW_CANDIDATE_ACTION = "SHADOW_BUY_CANDIDATE"

LIVE_RUNNER_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS live_runner_runs (
        id TEXT PRIMARY KEY,
        strategy_name TEXT NOT NULL,
        strategy_hash TEXT NOT NULL,
        symbol TEXT,
        venue TEXT,
        mode TEXT,
        model_artifact_path TEXT,
        status TEXT NOT NULL,
        config_json TEXT,
        started_at TEXT NOT NULL,
        stopped_at TEXT,
        last_heartbeat_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS live_runner_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        strategy_name TEXT NOT NULL,
        strategy_hash TEXT NOT NULL,
        symbol TEXT,
        venue TEXT,
        feature_timestamp TEXT,
        price REAL,
        signal TEXT,
        action TEXT,
        side TEXT,
        qty REAL,
        quote_amount REAL,
        order_id TEXT,
        client_order_id TEXT,
        order_submitted INTEGER,
        dry_run INTEGER,
        model_confidence REAL,
        entry_quality REAL,
        allowed_layers INTEGER,
        regime_gate TEXT,
        structure_bucket TEXT,
        reason TEXT,
        payload_json TEXT,
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_live_runner_decisions_strategy_ts ON live_runner_decisions (strategy_hash, symbol, venue, feature_timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_live_runner_decisions_run_created ON live_runner_decisions (run_id, created_at)",
)


@dataclass
class FrozenModelArtifact:
    model: Any
    model_path: Path
    metadata_path: Path
    metadata: Dict[str, Any]

    @property
    def feature_columns(self) -> List[str]:
        return list(self.metadata.get("feature_columns") or [])

    @property
    def model_name(self) -> str:
        return str(self.metadata.get("model_name") or "unknown")

    def confidence_for_row(self, row: Dict[str, Any]) -> float:
        values = [[float(row.get(col) or 0.0) for col in self.feature_columns]]
        if not self.feature_columns:
            return 0.5
        if self.model_name in {"logistic_regression", "mlp", "svm"} and hasattr(self.model, "scaler"):
            values = self.model.scaler.transform(values)
        try:
            proba = self.model.predict_proba(values)
            if len(proba) and len(proba[0]) > 1:
                return float(proba[0][1])
            if len(proba) and len(proba[0]) == 1:
                return float(proba[0][0])
        except Exception as exc:
            logger.warning("live model confidence fallback: %s", exc)
        return 0.5


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> Optional[str]:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except Exception:
        return None


def strategy_hash(strategy: Dict[str, Any]) -> str:
    return sha256_text(
        canonical_json(
            {
                "name": strategy.get("name"),
                "slug": strategy.get("slug"),
                "definition": strategy.get("definition"),
                "schema_version": strategy.get("schema_version"),
            }
        )
    )


def redact_config(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).lower().replace("-", "_").replace(" ", "_")
            compact_key = normalized_key.replace("_", "")
            if normalized_key in SENSITIVE_KEYS or compact_key in SENSITIVE_KEYS:
                cleaned[key] = "[REDACTED]" if item else ""
            else:
                cleaned[key] = redact_config(item)
        return cleaned
    if isinstance(value, list):
        return [redact_config(item) for item in value]
    return value


def normalize_symbol(symbol: Any) -> str:
    value = str(symbol or "BTC/USDT").strip().upper()
    if "/" in value:
        return value
    for quote in ("USDT", "USDC", "BUSD", "BTC", "ETH"):
        if value.endswith(quote) and len(value) > len(quote):
            return f"{value[:-len(quote)].rstrip('-_')}/{quote}"
    return value.replace("-", "/") if "-" in value else value


def compact_symbol(symbol: Any) -> str:
    return normalize_symbol(symbol).replace("/", "")


def load_saved_strategy(identifier: str) -> Dict[str, Any]:
    strategy = strategy_lab.load_strategy(identifier)
    if strategy:
        return strategy
    for row in strategy_lab.load_all_strategies(include_internal=True):
        if identifier in {str(row.get("name") or ""), str(row.get("slug") or "")}:
            return row
    raise FileNotFoundError(f"Saved strategy not found: {identifier}")


def ensure_audit_tables(session) -> None:
    for statement in LIVE_RUNNER_SCHEMA:
        session.execute(text(statement))
    session.commit()


def _sqlite_db_path(session) -> str:
    bind = session.get_bind()
    if bind is None or not bind.url.database:
        raise RuntimeError("Live runner requires a file-backed SQLite database URL")
    return str(bind.url.database)


def _read_sql_frame(db_path: str, query: str) -> pd.DataFrame:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def _normalize_timestamp_column(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "timestamp" not in df.columns:
        return df
    result = df.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="coerce", utc=True).dt.tz_convert(None)
    return result.dropna(subset=["timestamp"])


def load_training_frame(db_path: str) -> tuple[pd.DataFrame, str, List[str]]:
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        feature_columns = [row[1] for row in conn.execute("PRAGMA table_info(features_normalized)").fetchall()]
        label_columns = [row[1] for row in conn.execute("PRAGMA table_info(labels)").fetchall()]
    finally:
        conn.close()

    if not feature_columns:
        raise RuntimeError("features_normalized table is missing or empty")

    selected_feature_cols = [
        col
        for col in [
            "timestamp",
            "symbol",
            "regime_label",
            "feat_eye",
            "feat_ear",
            "feat_nose",
            "feat_tongue",
            "feat_body",
            "feat_pulse",
            "feat_aura",
            "feat_mind",
            "feat_vix",
            "feat_dxy",
            "feat_rsi14",
            "feat_macd_hist",
            "feat_atr_pct",
            "feat_vwap_dev",
            "feat_bb_pct_b",
            "feat_nw_width",
            "feat_nw_slope",
            "feat_adx",
            "feat_choppiness",
            "feat_donchian_pos",
            "feat_4h_bias50",
            "feat_4h_bias20",
            "feat_4h_bias200",
            "feat_4h_rsi14",
            "feat_4h_macd_hist",
            "feat_4h_bb_pct_b",
            "feat_4h_dist_bb_lower",
            "feat_4h_ma_order",
            "feat_4h_dist_swing_low",
            "feat_4h_vol_ratio",
            "feat_local_bottom_score",
            "feat_local_top_score",
            "feat_turning_point_score",
        ]
        if col in feature_columns
    ]
    features_df = _normalize_timestamp_column(
        _read_sql_frame(db_path, f"SELECT {', '.join(selected_feature_cols)} FROM features_normalized ORDER BY timestamp")
    )
    if features_df.empty:
        raise RuntimeError("No feature rows available for live model freeze")

    wanted_label_cols = [
        col
        for col in [
            "timestamp",
            "symbol",
            "horizon_minutes",
            "label_spot_long_win",
            "simulated_pyramid_win",
        ]
        if col in label_columns
    ]
    if wanted_label_cols:
        label_query = f"SELECT {', '.join(wanted_label_cols)} FROM labels"
        if "horizon_minutes" in wanted_label_cols:
            label_query += " WHERE horizon_minutes = 1440 OR horizon_minutes IS NULL"
        label_query += " ORDER BY timestamp"
        labels_df = _normalize_timestamp_column(_read_sql_frame(db_path, label_query))
        if not labels_df.empty:
            if "symbol" in labels_df.columns and "symbol" in features_df.columns:
                labels_df = labels_df.drop_duplicates(subset=["timestamp", "symbol"], keep="last")
                features_df = features_df.merge(labels_df, on=["timestamp", "symbol"], how="left")
            fallback_labels = labels_df.drop(columns=["symbol"], errors="ignore").drop_duplicates(subset=["timestamp"], keep="last")
            features_df = features_df.merge(fallback_labels, on="timestamp", how="left", suffixes=("", "__fallback"))
            for label_col in ("simulated_pyramid_win", "label_spot_long_win"):
                fallback_col = f"{label_col}__fallback"
                if fallback_col in features_df.columns:
                    if label_col in features_df.columns:
                        features_df[label_col] = features_df[label_col].where(features_df[label_col].notna(), features_df[fallback_col])
                    else:
                        features_df[label_col] = features_df[fallback_col]
                    features_df = features_df.drop(columns=[fallback_col])

    target_col = "simulated_pyramid_win" if "simulated_pyramid_win" in features_df.columns else "label_spot_long_win"
    if target_col not in features_df.columns:
        raise RuntimeError("No supported training target found for live model freeze")
    feature_cols = [col for col in features_df.columns if col.startswith("feat_")]
    train_df = features_df.dropna(subset=[target_col]).copy()
    if train_df.empty:
        raise RuntimeError(f"No labeled rows available for {target_col}")
    return train_df, target_col, feature_cols


def load_latest_strategy_row(session, symbol: str) -> Dict[str, Any]:
    symbol_key = compact_symbol(symbol)
    row = session.execute(
        text(
            """
            WITH raw_latest AS (
                SELECT timestamp, replace(replace(symbol, '/', ''), '-', '') AS symbol_key, MAX(id) AS max_id
                FROM raw_market_data
                WHERE close_price IS NOT NULL
                GROUP BY timestamp, replace(replace(symbol, '/', ''), '-', '')
            )
            SELECT f.timestamp, r.close_price,
                   f.feat_4h_bias50, f.feat_4h_bias200,
                   f.feat_nose, f.feat_pulse, f.feat_ear,
                   COALESCE(f.regime_label, 'unknown') AS regime_label,
                   f.feat_4h_bb_pct_b, f.feat_4h_dist_bb_lower, f.feat_4h_dist_swing_low,
                   f.feat_local_bottom_score, f.feat_local_top_score,
                   f.*
            FROM features_normalized f
            JOIN raw_latest rk
              ON rk.timestamp = f.timestamp
             AND rk.symbol_key = replace(replace(COALESCE(f.symbol, :symbol), '/', ''), '-', '')
            JOIN raw_market_data r ON r.id = rk.max_id
            WHERE f.feat_4h_bias50 IS NOT NULL
              AND r.close_price IS NOT NULL
              AND replace(replace(COALESCE(f.symbol, :symbol), '/', ''), '-', '') = :symbol_key
            ORDER BY f.timestamp DESC
            LIMIT 1
            """
        ),
        {"symbol": normalize_symbol(symbol), "symbol_key": symbol_key},
    ).mappings().first()
    if not row:
        raise RuntimeError(f"No Strategy Lab-compatible feature row available for {symbol}")
    return dict(row)


def ensure_model_artifact(
    *,
    session,
    strategy: Dict[str, Any],
    refresh: bool = False,
    root: Path = DEFAULT_LIVE_MODEL_ROOT,
) -> FrozenModelArtifact:
    definition = strategy.get("definition") if isinstance(strategy.get("definition"), dict) else {}
    params = definition.get("params") if isinstance(definition.get("params"), dict) else {}
    model_name = str(params.get("model_name") or "rule_baseline")
    if model_name == "rule_baseline":
        raise RuntimeError("rule_baseline does not need a frozen model artifact")

    root.mkdir(parents=True, exist_ok=True)
    s_hash = strategy_hash(strategy)
    slug = str(strategy.get("slug") or strategy_lab._strategy_slug(str(strategy.get("name") or "strategy")))
    base = root / f"{slug}-{s_hash[:12]}-{model_name}"
    model_path = base.with_suffix(".pkl")
    metadata_path = base.with_suffix(".json")

    if not refresh and model_path.exists() and metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("strategy_hash") == s_hash and metadata.get("model_name") == model_name:
            with model_path.open("rb") as handle:
                model = pickle.load(handle)
            return FrozenModelArtifact(model=model, model_path=model_path, metadata_path=metadata_path, metadata=metadata)

    db_path = _sqlite_db_path(session)
    train_df, target_col, feature_cols = load_training_frame(db_path)
    lb = ModelLeaderboard(train_df.copy(), target_col=target_col)
    X = train_df[feature_cols].fillna(0).values
    y = train_df[target_col].fillna(0).astype(int).values
    model = lb._train_model(X, y, model_name)
    if model is None:
        raise RuntimeError(f"{model_name} returned no model")

    with model_path.open("wb") as handle:
        pickle.dump(model, handle)
    model_hash = sha256_file(model_path)
    metadata = {
        "artifact_schema_version": 1,
        "created_at": utc_now_iso(),
        "strategy_name": strategy.get("name"),
        "strategy_slug": strategy.get("slug"),
        "strategy_hash": s_hash,
        "model_name": model_name,
        "target": target_col,
        "target_col": target_col,
        "feature_columns": feature_cols,
        "feature_count": len(feature_cols),
        "training_rows": int(len(train_df)),
        "training_min_timestamp": str(train_df["timestamp"].min()) if "timestamp" in train_df.columns else None,
        "training_max_timestamp": str(train_df["timestamp"].max()) if "timestamp" in train_df.columns else None,
        "model_hash": model_hash,
        "model_sha256": model_hash,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return FrozenModelArtifact(model=model, model_path=model_path, metadata_path=metadata_path, metadata=metadata)


class LiveTradingRunner:
    def __init__(
        self,
        config: Dict[str, Any],
        session,
        *,
        run_id: Optional[str] = None,
        model_artifact: Optional[FrozenModelArtifact] = None,
        trading_root: Path = DEFAULT_LIVE_TRADING_ROOT,
    ):
        self.config = config or {}
        self.session = session
        self.live_cfg = self.config.get("live_runner") if isinstance(self.config.get("live_runner"), dict) else {}
        self.trading_cfg = self.config.get("trading") if isinstance(self.config.get("trading"), dict) else {}
        self.execution_cfg = self.config.get("execution") if isinstance(self.config.get("execution"), dict) else {}
        self.symbol = normalize_symbol(self.live_cfg.get("symbol") or self.trading_cfg.get("symbol") or "BTC/USDT")
        self.venue = str(self.execution_cfg.get("venue") or self.trading_cfg.get("venue") or "okx").lower()
        self.strategy_name = str(
            self.live_cfg.get("strategy_name") or "Auto Leaderboard · 重掃 random_forest Hybrid #01"
        )
        self.strategy = load_saved_strategy(self.strategy_name)
        self.strategy_hash = strategy_hash(self.strategy)
        self.run_id = run_id or f"live-{uuid.uuid4().hex[:12]}"
        self.model_artifact = model_artifact
        self.trading_root = Path(trading_root)
        self.jsonl_path = self.trading_root / f"{self.run_id}.jsonl"
        ensure_audit_tables(self.session)

    def start_run(self, *, refresh_model: bool = False) -> None:
        if self.model_artifact is None:
            self.model_artifact = ensure_model_artifact(session=self.session, strategy=self.strategy, refresh=refresh_model)
        now = utc_now_iso()
        self.session.execute(
            text(
                """
                INSERT OR REPLACE INTO live_runner_runs(
                    id, strategy_name, strategy_hash, symbol, venue, mode, model_artifact_path,
                    status, config_json, started_at, stopped_at, last_heartbeat_at
                )
                VALUES (
                    :id, :strategy_name, :strategy_hash, :symbol, :venue, :mode, :model_artifact_path,
                    :status, :config_json, :started_at, NULL, :last_heartbeat_at
                )
                """
            ),
            {
                "id": self.run_id,
                "strategy_name": str(self.strategy.get("name") or self.strategy_name),
                "strategy_hash": self.strategy_hash,
                "symbol": self.symbol,
                "venue": self.venue,
                "mode": str(self.execution_cfg.get("mode") or "paper"),
                "model_artifact_path": str(self.model_artifact.model_path) if self.model_artifact else None,
                "status": "running",
                "config_json": canonical_json(redact_config(self.config)),
                "started_at": now,
                "last_heartbeat_at": now,
            },
        )
        self.session.commit()

    def stop_run(self, status: str = "stopped") -> None:
        now = utc_now_iso()
        self.session.execute(
            text("UPDATE live_runner_runs SET status=:status, stopped_at=:stopped_at WHERE id=:id"),
            {"status": status, "stopped_at": now, "id": self.run_id},
        )
        self.session.commit()

    def _append_jsonl(self, payload: Dict[str, Any]) -> None:
        self.trading_root.mkdir(parents=True, exist_ok=True)
        with self.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str) + "\n")

    def _record_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        created_at = utc_now_iso()
        payload = dict(decision.get("payload") or {})
        params = {
            "run_id": self.run_id,
            "strategy_name": str(self.strategy.get("name") or self.strategy_name),
            "strategy_hash": self.strategy_hash,
            "symbol": self.symbol,
            "venue": self.venue,
            "feature_timestamp": decision.get("feature_timestamp"),
            "price": decision.get("price"),
            "signal": decision.get("signal"),
            "action": decision.get("action"),
            "side": decision.get("side"),
            "qty": decision.get("qty"),
            "quote_amount": decision.get("quote_amount"),
            "order_id": decision.get("order_id"),
            "client_order_id": decision.get("client_order_id"),
            "order_submitted": 1 if decision.get("order_submitted") else 0,
            "dry_run": 1 if decision.get("dry_run") else 0 if decision.get("dry_run") is not None else None,
            "model_confidence": decision.get("model_confidence"),
            "entry_quality": decision.get("entry_quality"),
            "allowed_layers": decision.get("allowed_layers"),
            "regime_gate": decision.get("regime_gate"),
            "structure_bucket": decision.get("structure_bucket"),
            "reason": decision.get("reason"),
            "payload_json": canonical_json(payload),
            "created_at": created_at,
        }
        self.session.execute(
            text(
                """
                INSERT INTO live_runner_decisions(
                    run_id, strategy_name, strategy_hash, symbol, venue, feature_timestamp, price,
                    signal, action, side, qty, quote_amount, order_id, client_order_id,
                    order_submitted, dry_run, model_confidence, entry_quality, allowed_layers,
                    regime_gate, structure_bucket, reason, payload_json, created_at
                )
                VALUES (
                    :run_id, :strategy_name, :strategy_hash, :symbol, :venue, :feature_timestamp, :price,
                    :signal, :action, :side, :qty, :quote_amount, :order_id, :client_order_id,
                    :order_submitted, :dry_run, :model_confidence, :entry_quality, :allowed_layers,
                    :regime_gate, :structure_bucket, :reason, :payload_json, :created_at
                )
                """
            ),
            params,
        )
        self.session.execute(
            text("UPDATE live_runner_runs SET last_heartbeat_at=:now WHERE id=:id"),
            {"now": created_at, "id": self.run_id},
        )
        self.session.commit()
        output = {**params, "payload": payload}
        self._append_jsonl(output)
        return output

    def _load_open_layers(self) -> List[Dict[str, Any]]:
        rows = self.session.execute(
            text(
                """
                SELECT action, order_submitted, payload_json
                FROM live_runner_decisions
                WHERE strategy_hash=:strategy_hash AND symbol=:symbol AND venue=:venue
                ORDER BY id ASC
                """
            ),
            {"strategy_hash": self.strategy_hash, "symbol": self.symbol, "venue": self.venue},
        ).mappings().all()
        layers: List[Dict[str, Any]] = []
        for row in rows:
            if not row.get("order_submitted"):
                continue
            try:
                payload = json.loads(row.get("payload_json") or "{}")
            except Exception:
                payload = {}
            if row.get("action") == "SELL_ALL":
                layers = []
            elif row.get("action") == "BUY_LAYER":
                layer = payload.get("layer") if isinstance(payload.get("layer"), dict) else {}
                if layer:
                    layers.append(dict(layer))
        return layers

    def _feature_timestamp_already_acted(self, feature_timestamp: Any) -> bool:
        if not self.live_cfg.get("one_action_per_feature_timestamp", True):
            return False
        count = self.session.execute(
            text(
                """
                SELECT COUNT(*) FROM live_runner_decisions
                WHERE strategy_hash=:strategy_hash
                  AND symbol=:symbol
                  AND venue=:venue
                  AND feature_timestamp=:feature_timestamp
                  AND action IN ('BUY_LAYER', 'SELL_ALL')
                """
            ),
            {
                "strategy_hash": self.strategy_hash,
                "symbol": self.symbol,
                "venue": self.venue,
                "feature_timestamp": str(feature_timestamp),
            },
        ).scalar()
        return int(count or 0) > 0

    def _shadow_candidate_enabled(self) -> bool:
        return bool(
            self.live_cfg.get("shadow_candidate_enabled")
            or self.live_cfg.get("force_shadow_candidate")
            or self.live_cfg.get("shadow_evidence_mode")
        )

    def _shadow_candidate_qty(self) -> float:
        try:
            return max(float(self.live_cfg.get("shadow_candidate_qty", 0.00001)), 0.0)
        except (TypeError, ValueError):
            return 0.00001

    def _shadow_candidate_already_recorded(self, feature_timestamp: Any) -> bool:
        if not self.live_cfg.get("one_shadow_candidate_per_feature_timestamp", True):
            return False
        if feature_timestamp is None:
            return False
        count = self.session.execute(
            text(
                """
                SELECT COUNT(*) FROM live_runner_decisions
                WHERE strategy_hash=:strategy_hash
                  AND symbol=:symbol
                  AND venue=:venue
                  AND feature_timestamp=:feature_timestamp
                  AND action=:action
                """
            ),
            {
                "strategy_hash": self.strategy_hash,
                "symbol": self.symbol,
                "venue": self.venue,
                "feature_timestamp": str(feature_timestamp),
                "action": SHADOW_CANDIDATE_ACTION,
            },
        ).scalar()
        return int(count or 0) > 0

    def _maybe_force_shadow_candidate(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Turn a no-trade HOLD into a no-submit shadow candidate for 24h evidence.

        This lane intentionally does not call ExecutionService.  It exists so the
        standalone runner can keep producing timestamped paper/shadow proposals
        for DB/JSONL + 1440m-label reconciliation while live buy/add remains
        fail-closed.
        """
        if not self._shadow_candidate_enabled():
            return decision
        if decision.get("action") in {"BUY_LAYER", "SELL_ALL", SHADOW_CANDIDATE_ACTION}:
            return decision
        if decision.get("reason") in {"market_collection_failed", "feature_preprocess_failed", "invalid_price", "feature_timestamp_already_acted"}:
            return decision
        price = float(decision.get("price") or 0.0)
        feature_ts = decision.get("feature_timestamp")
        if price <= 0 or not feature_ts:
            return decision
        if self._shadow_candidate_already_recorded(feature_ts):
            return {
                **decision,
                "reason": "shadow_candidate_already_recorded",
                "payload": {
                    **dict(decision.get("payload") or {}),
                    "shadow_candidate_contract": {
                        "status": "duplicate_skipped",
                        "action": SHADOW_CANDIDATE_ACTION,
                        "feature_timestamp": feature_ts,
                        "order_submission_enabled": False,
                        "risk_on_order_enabled": False,
                    },
                },
            }
        qty = self._shadow_candidate_qty()
        quote_amount = qty * price if qty > 0 else None
        original = {
            "signal": decision.get("signal"),
            "action": decision.get("action"),
            "reason": decision.get("reason"),
            "entry_checks": dict(_payload.get("entry_checks") or {}) if isinstance((_payload := decision.get("payload")), dict) else {},
        }
        payload = dict(decision.get("payload") or {})
        payload["original_decision"] = original
        payload["shadow_candidate_contract"] = {
            "status": "recording_no_submit_shadow_candidate",
            "source": "live_runner.shadow_candidate_enabled",
            "action": SHADOW_CANDIDATE_ACTION,
            "side": "buy",
            "qty": qty,
            "quote_amount": quote_amount,
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
            "operator_message": "Standalone runner forced a paper/shadow candidate for 24h outcome evidence; no order is submitted.",
        }
        return {
            **decision,
            "signal": "SHADOW_BUY",
            "action": SHADOW_CANDIDATE_ACTION,
            "side": "buy",
            "qty": qty,
            "quote_amount": quote_amount,
            "order_submitted": False,
            "dry_run": True,
            "reason": "shadow_candidate_for_24h_gate",
            "payload": payload,
        }

    def _recent_top_k_history(self, limit: int = 500) -> List[float]:
        rows = self.session.execute(
            text(
                """
                SELECT model_confidence FROM live_runner_decisions
                WHERE strategy_hash=:strategy_hash AND symbol=:symbol AND venue=:venue
                  AND model_confidence IS NOT NULL
                ORDER BY id DESC LIMIT :limit
                """
            ),
            {"strategy_hash": self.strategy_hash, "symbol": self.symbol, "venue": self.venue, "limit": int(limit)},
        ).all()
        return [float(row[0]) for row in rows if row[0] is not None]

    def _build_decision(self, row: Dict[str, Any], confidence: float, open_layers: List[Dict[str, Any]]) -> Dict[str, Any]:
        definition = self.strategy.get("definition") if isinstance(self.strategy.get("definition"), dict) else {}
        params = definition.get("params") if isinstance(definition.get("params"), dict) else {}
        entry = params.get("entry") if isinstance(params.get("entry"), dict) else {}
        price = float(row.get("close_price") or 0.0)
        feature_ts = str(row.get("timestamp"))
        b50 = float(row.get("feat_4h_bias50") or 0.0)
        b200 = float(row.get("feat_4h_bias200") or 0.0)
        nose = float(row.get("feat_nose") if row.get("feat_nose") is not None else 0.5)
        pulse = float(row.get("feat_pulse") if row.get("feat_pulse") is not None else 0.5)
        ear = float(row.get("feat_ear") if row.get("feat_ear") is not None else 0.0)
        regime = str(row.get("regime_label") or "unknown").lower()
        bb_pct_b = row.get("feat_4h_bb_pct_b")
        dist_bb_lower = row.get("feat_4h_dist_bb_lower")
        dist_swing_low = row.get("feat_4h_dist_swing_low")
        bottom_score = float(row.get("feat_local_bottom_score") or 0.0)
        top_score = float(row.get("feat_local_top_score") or 0.0)

        horizon = strategy_lab._investment_horizon_profile(params)
        bias50_max = strategy_lab._adjust_value_by_horizon(float(entry.get("bias50_max", -3.0)), horizon, short_delta=1.0, long_delta=-1.0)
        conf_min = strategy_lab._clamp01(strategy_lab._adjust_value_by_horizon(float(entry.get("confidence_min", 0.35)), horizon, short_delta=-0.10, long_delta=0.08))
        entry_quality_min = strategy_lab._clamp01(strategy_lab._adjust_value_by_horizon(float(entry.get("entry_quality_min", 0.0) or 0.0), horizon, short_delta=-0.08, long_delta=0.08))
        regime_min = float(entry.get("regime_bias200_min", -10.0))
        allowed_regimes = strategy_lab._normalize_allowed_regimes(entry.get("allowed_regimes"))
        top_k_percent = float(entry.get("top_k_percent", 0.0) or 0.0)
        layers_pct = params.get("layers") if isinstance(params.get("layers"), list) else [0.2, 0.3, 0.5]
        capital_quote = float(self.live_cfg.get("capital_quote") or params.get("initial_capital") or 10000.0)
        capital_cfg = strategy_lab._capital_management_config(params)
        turning_cfg = strategy_lab._turning_point_config(params)
        stop_loss = strategy_lab._adjust_value_by_horizon(float(params.get("stop_loss", -0.05)), horizon, short_delta=0.02, long_delta=-0.03)
        tp_bias = strategy_lab._adjust_value_by_horizon(float(params.get("take_profit_bias", 4.0)), horizon, short_delta=-1.2, long_delta=1.2)
        tp_roi = strategy_lab._adjust_value_by_horizon(float(params.get("take_profit_roi", 0.08)), horizon, short_delta=-0.03, long_delta=0.04)

        regime_gate = strategy_lab._compute_regime_gate(
            b200,
            regime,
            regime_min,
            float(bb_pct_b) if bb_pct_b is not None else None,
            float(dist_bb_lower) if dist_bb_lower is not None else None,
            float(dist_swing_low) if dist_swing_low is not None else None,
            bias50_value=b50,
        )
        structure_quality = strategy_lab._compute_4h_structure_quality(
            bb_pct_b_value=float(bb_pct_b) if bb_pct_b is not None else None,
            dist_bb_lower_value=float(dist_bb_lower) if dist_bb_lower is not None else None,
            dist_swing_low_value=float(dist_swing_low) if dist_swing_low is not None else None,
        )
        structure_bucket = strategy_lab._structure_bucket(regime_gate, structure_quality)
        rule_entry_quality = strategy_lab._compute_entry_quality(
            b50,
            nose,
            pulse,
            ear,
            float(bb_pct_b) if bb_pct_b is not None else None,
            float(dist_bb_lower) if dist_bb_lower is not None else None,
            float(dist_swing_low) if dist_swing_low is not None else None,
            regime_label=regime,
            regime_gate=regime_gate,
            structure_bucket=structure_bucket,
        )
        entry_quality = round(0.6 * strategy_lab._clamp01(confidence) + 0.4 * rule_entry_quality, 4)
        allowed_layers = strategy_lab._allowed_layers_for_signal(regime_gate, entry_quality, len(layers_pct))

        base = {
            "feature_timestamp": feature_ts,
            "price": price,
            "signal": "HOLD",
            "action": "HOLD",
            "side": None,
            "qty": None,
            "quote_amount": None,
            "model_confidence": round(float(confidence), 6),
            "entry_quality": entry_quality,
            "allowed_layers": allowed_layers,
            "regime_gate": regime_gate,
            "structure_bucket": structure_bucket,
            "reason": "conditions_not_met",
            "payload": {
                "inputs": {
                    "bias50": b50,
                    "bias200": b200,
                    "nose": nose,
                    "pulse": pulse,
                    "ear": ear,
                    "regime": regime,
                    "local_bottom_score": bottom_score,
                    "local_top_score": top_score,
                },
                "open_layers": open_layers,
            },
        }

        if price <= 0:
            base["reason"] = "invalid_price"
            return base

        if open_layers:
            avg = strategy_lab._entry_layers_avg_price(open_layers)
            pnl_pct = (price - avg) / avg if avg > 0 else 0.0
            turning_take_profit = bool(turning_cfg.get("enabled")) and top_score >= float(turning_cfg.get("top_score_take_profit") or 1.0)
            if pnl_pct <= stop_loss:
                return {**base, **self._sell_all_payload(price, open_layers, "stop_loss", pnl_pct)}
            if b50 > tp_bias or pnl_pct > tp_roi or turning_take_profit:
                reason = "tp_turning_point" if turning_take_profit else ("tp_bias" if b50 > tp_bias else "tp_roi")
                return {**base, **self._sell_all_payload(price, open_layers, reason, pnl_pct)}

        top_k_pass = strategy_lab._passes_rolling_top_k_gate(confidence, self._recent_top_k_history(), top_k_percent)
        turning_gate_ok = (not turning_cfg.get("enabled")) or bottom_score >= float(turning_cfg.get("bottom_score_min") or 0.0)
        can_enter = (
            regime_gate != "BLOCK"
            and allowed_layers > 0
            and strategy_lab._regime_allowed(regime, allowed_regimes)
            and entry_quality >= entry_quality_min
            and top_k_pass
            and turning_gate_ok
            and b50 <= bias50_max
            and confidence >= conf_min
            and b200 >= regime_min
        )

        if not can_enter:
            base["reason"] = "entry_conditions_not_met"
            base["payload"]["entry_checks"] = {
                "regime_gate": regime_gate != "BLOCK",
                "allowed_layers": allowed_layers > 0,
                "regime_allowed": strategy_lab._regime_allowed(regime, allowed_regimes),
                "entry_quality": entry_quality >= entry_quality_min,
                "top_k": top_k_pass,
                "turning_gate": turning_gate_ok,
                "bias50": b50 <= bias50_max,
                "confidence": confidence >= conf_min,
                "bias200": b200 >= regime_min,
            }
            return base

        next_layer_idx = len(open_layers)
        if next_layer_idx >= len(layers_pct) or allowed_layers < next_layer_idx + 1:
            base["reason"] = "no_layer_available"
            return base
        if next_layer_idx == 1 and b50 > float(entry.get("layer2_bias_max", bias50_max - 1.5)):
            base["reason"] = "layer2_bias_not_met"
            return base
        if next_layer_idx == 2 and b50 > float(entry.get("layer3_bias_max", bias50_max - 3.0)):
            base["reason"] = "layer3_bias_not_met"
            return base
        if next_layer_idx > 0 and not strategy_lab._reserve_unlocked(capital_cfg, open_layers, price):
            base["reason"] = "reserve_not_unlocked"
            return base

        quote_amount = float(strategy_lab._layer_budget(next_layer_idx, layers_pct, capital_quote, capital_cfg))
        qty = quote_amount / price
        layer_payload = {
            "price": price,
            "coins": qty,
            "layer": next_layer_idx + 1,
            "timestamp": feature_ts,
            "regime": regime,
            "regime_gate": regime_gate,
            "entry_quality": entry_quality,
            "allowed_layers": allowed_layers,
            "capital_mode": capital_cfg.get("mode"),
        }
        return {
            **base,
            "signal": f"BUY_L{next_layer_idx + 1}",
            "action": "BUY_LAYER",
            "side": "buy",
            "qty": qty,
            "quote_amount": quote_amount,
            "reason": f"buy_layer_{next_layer_idx + 1}",
            "payload": {**base["payload"], "layer": layer_payload},
        }

    def _sell_all_payload(self, price: float, open_layers: List[Dict[str, Any]], reason: str, pnl_pct: float) -> Dict[str, Any]:
        qty = sum(float(layer.get("coins") or 0.0) for layer in open_layers)
        return {
            "signal": reason.upper(),
            "action": "SELL_ALL",
            "side": "sell",
            "qty": qty,
            "quote_amount": qty * price,
            "reason": reason,
            "payload": {"open_layers": open_layers, "pnl_pct": pnl_pct, "sell_all": True},
        }

    def run_cycle(
        self,
        *,
        collect_market: bool = True,
        preprocess: bool = True,
        submit_orders: bool = True,
    ) -> Dict[str, Any]:
        if collect_market:
            collected = run_collection_and_save(self.session, self.symbol)
            if not collected:
                return self._record_decision(
                    {
                        "feature_timestamp": None,
                        "signal": "COLLECT_FAILED",
                        "action": "HOLD",
                        "reason": "market_collection_failed",
                        "payload": {},
                    }
                )
        if preprocess:
            features = run_preprocessor(self.session, self.symbol)
            if not features:
                return self._record_decision(
                    {
                        "feature_timestamp": None,
                        "signal": "PREPROCESS_FAILED",
                        "action": "HOLD",
                        "reason": "feature_preprocess_failed",
                        "payload": {},
                    }
                )
        if self.model_artifact is None:
            self.model_artifact = ensure_model_artifact(session=self.session, strategy=self.strategy)

        row = load_latest_strategy_row(self.session, self.symbol)
        confidence = self.model_artifact.confidence_for_row(row)
        open_layers = self._load_open_layers()
        decision = self._build_decision(row, confidence, open_layers)
        decision = self._maybe_force_shadow_candidate(decision)

        if decision.get("action") in {"BUY_LAYER", "SELL_ALL"} and self._feature_timestamp_already_acted(decision.get("feature_timestamp")):
            decision.update({"signal": "DUPLICATE_SKIP", "action": "HOLD", "side": None, "qty": None, "quote_amount": None, "reason": "feature_timestamp_already_acted"})

        if submit_orders and decision.get("action") in {"BUY_LAYER", "SELL_ALL"} and decision.get("qty"):
            try:
                service = ExecutionService(self.config, db_session=self.session)
                result = service.submit_order(
                    symbol=self.symbol,
                    side=str(decision["side"]),
                    order_type=str(self.live_cfg.get("order_type") or "market"),
                    qty=float(decision["qty"]),
                    price=float(decision["price"]),
                    venue=self.venue,
                    reduce_only=decision.get("action") == "SELL_ALL",
                    reason=f"live_runner:{decision.get('reason')}",
                    model_confidence=float(decision.get("model_confidence") or 0.0),
                )
                order = result.get("order") or {}
                decision.update(
                    {
                        "order_submitted": True,
                        "dry_run": bool(result.get("dry_run")),
                        "order_id": order.get("id"),
                        "client_order_id": order.get("client_order_id"),
                    }
                )
                decision["payload"] = {**dict(decision.get("payload") or {}), "execution_result": result}
            except ExecutionRejectError as exc:
                decision.update({"order_submitted": False, "dry_run": None, "reason": f"execution_rejected:{exc.code}"})
                decision["payload"] = {**dict(decision.get("payload") or {}), "execution_reject": exc.to_payload()}
            except Exception as exc:
                decision.update({"order_submitted": False, "dry_run": None, "reason": f"execution_failed:{exc}"})
                decision["payload"] = {**dict(decision.get("payload") or {}), "execution_error": str(exc)}
        else:
            decision.setdefault("order_submitted", False)

        return self._record_decision(decision)


def runner_interval_seconds(config: Dict[str, Any], fallback: int = 300) -> int:
    live_cfg = config.get("live_runner") if isinstance(config.get("live_runner"), dict) else {}
    try:
        return max(1, int(float(live_cfg.get("interval_seconds", fallback))))
    except (TypeError, ValueError):
        return fallback
