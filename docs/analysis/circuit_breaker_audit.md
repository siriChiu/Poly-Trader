# Circuit Breaker Audit（Heartbeat #20260425_050356）

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 0 / threshold 50
- recent 50: win_rate=0.5 wins=25 losses=25
- streak horizons: {}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 20 / threshold 50
- recent 50: win_rate=0.46 wins=23 losses=27

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=20, win_rate=0.46
- additional recent-window wins needed: 0
- tail pathology: losses=27 / wins=23 / loss_share=0.54