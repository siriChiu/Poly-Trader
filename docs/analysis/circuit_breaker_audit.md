# Circuit Breaker Audit（Heartbeat #20260423i）

## 結論
- verdict: **mixed_horizon_false_positive**
- summary: 混合 horizon breaker 會被 240m tail labels 觸發（streak=64，recent50 win_rate=0.0000），但 1440m canonical live horizon 目前 release-ready。
- recommended_patch: 將 circuit breaker 對齊 horizon_minutes=1440 的 canonical live contract。

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['streak', 'recent_win_rate']
- streak: 64 / threshold 50
- recent 50: win_rate=0.0 wins=0 losses=50
- streak horizons: {'240': 64}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 3 / threshold 50
- recent 50: win_rate=0.94 wins=47 losses=3

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=3, win_rate=0.94
- additional recent-window wins needed: 0
- tail pathology: losses=3 / wins=47 / loss_share=0.06