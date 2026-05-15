# Circuit Breaker Audit（Heartbeat #1262）

## 結論
- verdict: **mixed_horizon_false_positive**
- summary: 混合 horizon breaker 會被 240m tail labels 觸發（streak=10，recent50 win_rate=0.1800），但 1440m canonical live horizon 目前 release-ready。
- recommended_patch: 將 circuit breaker 對齊 horizon_minutes=1440 的 canonical live contract。

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 10 / threshold 50
- recent 50: win_rate=0.18 wins=9 losses=41
- streak horizons: {'240': 10}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 29 / threshold 50
- recent 50: win_rate=0.42 wins=21 losses=29

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=29, win_rate=0.42
- additional recent-window wins needed: 0
- tail pathology: losses=29 / wins=21 / loss_share=0.58