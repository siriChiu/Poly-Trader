# Circuit Breaker Audit（Heartbeat #20260422d）

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
- streak: 22 / threshold 50
- recent 50: win_rate=0.56 wins=28 losses=22

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=22, win_rate=0.56
- additional recent-window wins needed: 0
- tail pathology: losses=22 / wins=28 / loss_share=0.44