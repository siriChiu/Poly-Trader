# Circuit Breaker Audit（Heartbeat #fast）

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 0 / threshold 50
- recent 50: win_rate=0.64 wins=32 losses=18
- streak horizons: {}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 10 / threshold 50
- recent 50: win_rate=0.02 wins=1 losses=49

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=10, win_rate=0.02
- additional recent-window wins needed: 14
- tail pathology: losses=49 / wins=1 / loss_share=0.98