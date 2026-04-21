# Circuit Breaker Audit（Heartbeat #20260422f）

## 結論
- verdict: **mixed_horizon_false_positive**
- summary: 混合 horizon breaker 會被 240m tail labels 觸發（streak=0，recent50 win_rate=0.2800），但 1440m canonical live horizon 目前 release-ready。
- recommended_patch: 將 circuit breaker 對齊 horizon_minutes=1440 的 canonical live contract。

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 0 / threshold 50
- recent 50: win_rate=0.28 wins=14 losses=36
- streak horizons: {}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 31 / threshold 50
- recent 50: win_rate=0.38 wins=19 losses=31

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=31, win_rate=0.38
- additional recent-window wins needed: 0
- tail pathology: losses=31 / wins=19 / loss_share=0.62