# Circuit Breaker Audit（Heartbeat #fast）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 9 / threshold 50
- recent 50: win_rate=0.44 wins=22 losses=28
- streak horizons: {'240': 9}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 13 / threshold 50
- recent 50: win_rate=0.74 wins=37 losses=13

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=13, win_rate=0.74
- additional recent-window wins needed: 0
- tail pathology: losses=13 / wins=37 / loss_share=0.26