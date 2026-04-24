# Circuit Breaker Audit（Heartbeat #fast）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 19 / threshold 50
- recent 50: win_rate=0.54 wins=27 losses=23
- streak horizons: {'240': 19}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 15 / threshold 50
- recent 50: win_rate=0.7 wins=35 losses=15

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=15, win_rate=0.7
- additional recent-window wins needed: 0
- tail pathology: losses=15 / wins=35 / loss_share=0.3