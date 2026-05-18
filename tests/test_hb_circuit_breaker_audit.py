from scripts import hb_circuit_breaker_audit as audit


def _scope(triggered, wins, losses, streak_count, release_ready=None):
    if release_ready is None:
        release_ready = not triggered
    return {
        "scope": "horizon_1440",
        "rows_available": wins + losses,
        "triggered": triggered,
        "triggered_by": ["recent_win_rate"] if triggered else [],
        "release_ready": release_ready,
        "release_condition": {
            "release_ready": release_ready,
            "blocked_by": ["recent_win_rate"] if triggered else [],
            "streak_release_ready": streak_count < audit.CIRCUIT_BREAKER_STREAK,
            "recent_win_rate_release_ready": not triggered,
            "streak_must_be_below": audit.CIRCUIT_BREAKER_STREAK,
            "current_streak": streak_count,
            "recent_window": audit.CIRCUIT_BREAKER_WINDOW,
            "recent_win_rate_floor": audit.CIRCUIT_BREAKER_RECENT_WINRATE,
            "current_recent_window_win_rate": wins / (wins + losses),
            "current_recent_window_wins": wins,
            "required_recent_window_wins": 15,
            "additional_recent_window_wins_needed": max(0, 15 - wins),
        },
        "tail_pathology": {
            "losses_in_recent_window": losses,
            "wins_in_recent_window": wins,
            "loss_share": round(losses / (wins + losses), 4),
            "window_start_timestamp": "2026-05-17 00:00:00",
            "window_end_timestamp": "2026-05-18 00:00:00",
            "latest_rows_preview": [{"target": 0}],
        },
        "streak": {
            "count": streak_count,
            "threshold": audit.CIRCUIT_BREAKER_STREAK,
            "horizons": {"1440": streak_count},
            "rows": [{"target": 0}],
        },
        "recent_window": {
            "window_size": wins + losses,
            "wins": wins,
            "losses": losses,
            "win_rate": wins / (wins + losses),
            "rows": [{"target": 0}],
        },
        "latest_timestamp": "2026-05-18 00:00:00",
        "oldest_timestamp": "2026-05-17 00:00:00",
    }


def test_build_payload_promotes_canonical_release_truth_to_top_level_without_row_previews():
    mixed = _scope(False, wins=18, losses=32, streak_count=3, release_ready=True)
    aligned = _scope(True, wins=6, losses=44, streak_count=36, release_ready=False)

    payload = audit._build_payload(
        mixed=mixed,
        aligned=aligned,
        heartbeat="1333-productization",
        generated_at="2026-05-18T12:00:00Z",
    )

    assert payload["generated_at"] == "2026-05-18T12:00:00Z"
    assert payload["verdict"] == "canonical_breaker_active"
    assert payload["canonical_horizon_minutes"] == 1440
    assert payload["release_condition"]["release_ready"] is False
    assert payload["release_condition"]["current_recent_window_wins"] == 6
    assert payload["release_condition"]["required_recent_window_wins"] == 15
    assert payload["release_condition"]["additional_recent_window_wins_needed"] == 9
    assert payload["tail_pathology"]["losses_in_recent_window"] == 44
    assert payload["tail_pathology"]["wins_in_recent_window"] == 6
    assert payload["tail_pathology"]["loss_share"] == 0.88
    assert payload["canonical_scope"]["triggered"] is True
    assert payload["canonical_scope"]["release_ready"] is False
    assert "latest_rows_preview" not in payload["tail_pathology"]
    assert "rows" not in payload["canonical_scope"]
