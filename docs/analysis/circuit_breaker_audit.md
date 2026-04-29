# Circuit Breaker Audit（Heartbeat #1142）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 0 / threshold 50
- recent 50: win_rate=0.44 wins=22 losses=28
- streak horizons: {}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 1 / threshold 50
- recent 50: win_rate=0.48 wins=24 losses=26

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=1, win_rate=0.48
- additional recent-window wins needed: 0
- tail pathology: losses=26 / wins=24 / loss_share=0.52