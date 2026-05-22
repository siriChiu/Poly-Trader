# Circuit Breaker Audit（Heartbeat #1444）
_generated_at: 2026-05-22T19:12:06.617976Z_

## 結論
- verdict: **mixed_horizon_false_positive**
- summary: 混合 horizon breaker 會被 240m tail labels 觸發（streak=25，recent50 win_rate=0.2200），但 1440m canonical live horizon 目前 release-ready。
- recommended_patch: 將 circuit breaker 對齊 horizon_minutes=1440 的 canonical live contract。
- top_level_release: ready=True / recent wins=24/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 25 / threshold 50
- recent 50: win_rate=0.22 wins=11 losses=39
- streak horizons: {'240': 25}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 22 / threshold 50
- recent 50: win_rate=0.48 wins=24 losses=26

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=22, win_rate=0.48
- additional recent-window wins needed: 0
- tail pathology: losses=26 / wins=24 / loss_share=0.52