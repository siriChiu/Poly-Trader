# Circuit Breaker Audit（Heartbeat #1517）
_generated_at: 2026-05-26T01:14:22.805426Z_

## 結論
- verdict: **mixed_horizon_false_positive**
- summary: 混合 horizon breaker 會被 240m tail labels 觸發（streak=38，recent50 win_rate=0.1800），但 1440m canonical live horizon 目前 release-ready。
- recommended_patch: 將 circuit breaker 對齊 horizon_minutes=1440 的 canonical live contract。
- top_level_release: ready=True / recent wins=44/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 38 / threshold 50
- recent 50: win_rate=0.18 wins=9 losses=41
- streak horizons: {'240': 38}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 5 / threshold 50
- recent 50: win_rate=0.88 wins=44 losses=6

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=5, win_rate=0.88
- additional recent-window wins needed: 0
- tail pathology: losses=6 / wins=44 / loss_share=0.12