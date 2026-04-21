# Circuit Breaker Audit（Heartbeat #fast）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 1 / threshold 50
- recent 50: win_rate=0.36 wins=18 losses=32
- streak horizons: {'240': 1}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 16 / threshold 50
- recent 50: win_rate=0.68 wins=34 losses=16

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=16, win_rate=0.68
- additional recent-window wins needed: 0
- tail pathology: losses=16 / wins=34 / loss_share=0.32