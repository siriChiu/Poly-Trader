# Circuit Breaker Audit（Heartbeat #1416）
_generated_at: 2026-05-21T15:08:45.966105Z_

## 結論
- verdict: **mixed_horizon_false_positive**
- summary: 混合 horizon breaker 會被 240m tail labels 觸發（streak=25，recent50 win_rate=0.1600），但 1440m canonical live horizon 目前 release-ready。
- recommended_patch: 將 circuit breaker 對齊 horizon_minutes=1440 的 canonical live contract。
- top_level_release: ready=True / recent wins=32/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 25 / threshold 50
- recent 50: win_rate=0.16 wins=8 losses=42
- streak horizons: {'240': 25}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 18 / threshold 50
- recent 50: win_rate=0.64 wins=32 losses=18

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=18, win_rate=0.64
- additional recent-window wins needed: 0
- tail pathology: losses=18 / wins=32 / loss_share=0.36