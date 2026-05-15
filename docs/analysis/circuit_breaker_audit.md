# Circuit Breaker Audit（Heartbeat #1251）

## 結論
- verdict: **mixed_horizon_false_positive**
- summary: 混合 horizon breaker 會被 240m tail labels 觸發（streak=13，recent50 win_rate=0.2000），但 1440m canonical live horizon 目前 release-ready。
- recommended_patch: 將 circuit breaker 對齊 horizon_minutes=1440 的 canonical live contract。

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 13 / threshold 50
- recent 50: win_rate=0.2 wins=10 losses=40
- streak horizons: {'240': 13}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 2 / threshold 50
- recent 50: win_rate=0.96 wins=48 losses=2

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=2, win_rate=0.96
- additional recent-window wins needed: 0
- tail pathology: losses=2 / wins=48 / loss_share=0.04