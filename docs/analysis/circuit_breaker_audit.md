# Circuit Breaker Audit（Heartbeat #fast）

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 0 / threshold 50
- recent 50: win_rate=0.66 wins=33 losses=17
- streak horizons: {}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 1 / threshold 50
- recent 50: win_rate=0.14 wins=7 losses=43

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=1, win_rate=0.14
- additional recent-window wins needed: 8
- tail pathology: losses=43 / wins=7 / loss_share=0.86