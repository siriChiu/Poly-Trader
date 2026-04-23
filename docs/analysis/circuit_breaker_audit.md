# Circuit Breaker Audit（Heartbeat #20260424d）

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 2 / threshold 50
- recent 50: win_rate=0.6 wins=30 losses=20
- streak horizons: {'240': 2}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 0 / threshold 50
- recent 50: win_rate=0.28 wins=14 losses=36

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=0, win_rate=0.28
- additional recent-window wins needed: 1
- tail pathology: losses=36 / wins=14 / loss_share=0.72