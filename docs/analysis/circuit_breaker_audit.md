# Circuit Breaker Audit（Heartbeat #20260423m）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 7 / threshold 50
- recent 50: win_rate=0.86 wins=43 losses=7
- streak horizons: {'240': 7}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 3 / threshold 50
- recent 50: win_rate=0.82 wins=41 losses=9

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=3, win_rate=0.82
- additional recent-window wins needed: 0
- tail pathology: losses=9 / wins=41 / loss_share=0.18