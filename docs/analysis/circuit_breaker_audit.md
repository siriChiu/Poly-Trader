# Circuit Breaker Audit（Heartbeat #1029）

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 4 / threshold 50
- recent 50: win_rate=0.58 wins=29 losses=21
- streak horizons: {'240': 4}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 14 / threshold 50
- recent 50: win_rate=0.18 wins=9 losses=41

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=14, win_rate=0.18
- additional recent-window wins needed: 6
- tail pathology: losses=41 / wins=9 / loss_share=0.82