# Circuit Breaker Audit（Heartbeat #20260424u）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 5 / threshold 50
- recent 50: win_rate=0.72 wins=36 losses=14
- streak horizons: {'240': 5}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 4 / threshold 50
- recent 50: win_rate=0.92 wins=46 losses=4

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=4, win_rate=0.92
- additional recent-window wins needed: 0
- tail pathology: losses=4 / wins=46 / loss_share=0.08