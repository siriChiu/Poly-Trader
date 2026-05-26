# Circuit Breaker Audit（Heartbeat #1518）
_generated_at: 2026-05-26T02:51:53.681525Z_

## 結論
- verdict: **mixed_horizon_false_positive**
- summary: 混合 horizon breaker 會被 240m tail labels 觸發（streak=43，recent50 win_rate=0.1400），但 1440m canonical live horizon 目前 release-ready。
- recommended_patch: 將 circuit breaker 對齊 horizon_minutes=1440 的 canonical live contract。
- top_level_release: ready=True / recent wins=42/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 43 / threshold 50
- recent 50: win_rate=0.14 wins=7 losses=43
- streak horizons: {'240': 43}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 7 / threshold 50
- recent 50: win_rate=0.84 wins=42 losses=8

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=7, win_rate=0.84
- additional recent-window wins needed: 0
- tail pathology: losses=8 / wins=42 / loss_share=0.16