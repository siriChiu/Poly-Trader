# Circuit Breaker Audit（Heartbeat #20260424_1730）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 2 / threshold 50
- recent 50: win_rate=0.48 wins=24 losses=26
- streak horizons: {'240': 2}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 0 / threshold 50
- recent 50: win_rate=0.58 wins=29 losses=21

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=0, win_rate=0.58
- additional recent-window wins needed: 0
- tail pathology: losses=21 / wins=29 / loss_share=0.42