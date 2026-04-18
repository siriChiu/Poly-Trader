#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import hb_leaderboard_candidate_probe as probe  # noqa: E402

artifact_path = PROJECT_ROOT / "data" / "leaderboard_feature_profile_probe.json"
if not artifact_path.exists():
    raise SystemExit("missing leaderboard_feature_profile_probe.json")

payload = json.loads(artifact_path.read_text(encoding="utf-8"))
top_model = payload.get("top_model") or {}
leaderboard_snapshot_created_at = payload.get("leaderboard_snapshot_created_at")
alignment = probe._build_alignment(top_model, leaderboard_snapshot_created_at=leaderboard_snapshot_created_at)
payload["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
payload["alignment"] = alignment
artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({
    "artifact": str(artifact_path),
    "dual_profile_state": alignment.get("dual_profile_state"),
    "train_selected_profile": alignment.get("train_selected_profile"),
    "leaderboard_selected_profile": alignment.get("leaderboard_selected_profile"),
    "snapshot_stale": alignment.get("artifact_recency", {}).get("alignment_snapshot_stale"),
}, ensure_ascii=False, indent=2))
