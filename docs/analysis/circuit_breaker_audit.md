# Circuit Breaker Audit（Heartbeat #20260424w）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 10 / threshold 50
- recent 50: win_rate=0.68 wins=34 losses=16
- streak horizons: {'240': 10}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 8 / threshold 50
- recent 50: win_rate=0.84 wins=42 losses=8

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=8, win_rate=0.84
- additional recent-window wins needed: 0
- tail pathology: losses=8 / wins=42 / loss_share=0.16