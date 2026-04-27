# Circuit Breaker Audit（Heartbeat #1084）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 0 / threshold 50
- recent 50: win_rate=0.34 wins=17 losses=33
- streak horizons: {}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 14 / threshold 50
- recent 50: win_rate=0.72 wins=36 losses=14

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=14, win_rate=0.72
- additional recent-window wins needed: 0
- tail pathology: losses=14 / wins=36 / loss_share=0.28