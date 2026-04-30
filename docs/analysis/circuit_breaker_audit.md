# Circuit Breaker Audit（Heartbeat #1149）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 3 / threshold 50
- recent 50: win_rate=0.42 wins=21 losses=29
- streak horizons: {'240': 3}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 3 / threshold 50
- recent 50: win_rate=0.5 wins=25 losses=25

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=3, win_rate=0.5
- additional recent-window wins needed: 0
- tail pathology: losses=25 / wins=25 / loss_share=0.5