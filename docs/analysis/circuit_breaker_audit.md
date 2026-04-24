# Circuit Breaker Audit（Heartbeat #20260424_1300）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 12 / threshold 50
- recent 50: win_rate=0.64 wins=32 losses=18
- streak horizons: {'240': 12}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 11 / threshold 50
- recent 50: win_rate=0.78 wins=39 losses=11

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=11, win_rate=0.78
- additional recent-window wins needed: 0
- tail pathology: losses=11 / wins=39 / loss_share=0.22