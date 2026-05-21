# Circuit Breaker Audit（Heartbeat #1414）
_generated_at: 2026-05-21T13:11:05.511540Z_

## 結論
- verdict: **mixed_horizon_false_positive**
- summary: 混合 horizon breaker 會被 240m tail labels 觸發（streak=18，recent50 win_rate=0.2600），但 1440m canonical live horizon 目前 release-ready。
- recommended_patch: 將 circuit breaker 對齊 horizon_minutes=1440 的 canonical live contract。
- top_level_release: ready=True / recent wins=41/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 18 / threshold 50
- recent 50: win_rate=0.26 wins=13 losses=37
- streak horizons: {'240': 18}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 9 / threshold 50
- recent 50: win_rate=0.82 wins=41 losses=9

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=9, win_rate=0.82
- additional recent-window wins needed: 0
- tail pathology: losses=9 / wins=41 / loss_share=0.18