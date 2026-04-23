# Circuit Breaker Audit（Heartbeat #20260423g）

## 結論
- verdict: **mixed_horizon_false_positive**
- summary: 混合 horizon breaker 會被 240m tail labels 觸發（streak=202，recent50 win_rate=0.0000），但 1440m canonical live horizon 目前 release-ready。
- recommended_patch: 將 circuit breaker 對齊 horizon_minutes=1440 的 canonical live contract。

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['streak', 'recent_win_rate']
- streak: 202 / threshold 50
- recent 50: win_rate=0.0 wins=0 losses=50
- streak horizons: {'240': 202}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 0 / threshold 50
- recent 50: win_rate=1.0 wins=50 losses=0

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=0, win_rate=1.0
- additional recent-window wins needed: 0
- tail pathology: losses=0 / wins=50 / loss_share=0.0