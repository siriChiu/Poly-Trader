# Circuit Breaker Audit（Heartbeat #20260425_1259）

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 0 / threshold 50
- recent 50: win_rate=0.44 wins=22 losses=28
- streak horizons: {}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 2 / threshold 50
- recent 50: win_rate=0.04 wins=2 losses=48

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=2, win_rate=0.04
- additional recent-window wins needed: 13
- tail pathology: losses=48 / wins=2 / loss_share=0.96