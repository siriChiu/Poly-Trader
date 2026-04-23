# Circuit Breaker Audit（Heartbeat #fast）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 0 / threshold 50
- recent 50: win_rate=0.68 wins=34 losses=16
- streak horizons: {}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 35 / threshold 50
- recent 50: win_rate=0.3 wins=15 losses=35

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=35, win_rate=0.3
- additional recent-window wins needed: 0
- tail pathology: losses=35 / wins=15 / loss_share=0.7