# Circuit Breaker Audit（Heartbeat #1192）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 11 / threshold 50
- recent 50: win_rate=0.32 wins=16 losses=34
- streak horizons: {'240': 11}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 3 / threshold 50
- recent 50: win_rate=0.34 wins=17 losses=33

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=3, win_rate=0.34
- additional recent-window wins needed: 0
- tail pathology: losses=33 / wins=17 / loss_share=0.66