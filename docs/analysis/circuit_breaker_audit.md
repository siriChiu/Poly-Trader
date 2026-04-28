# Circuit Breaker Audit（Heartbeat #1098）

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 11 / threshold 50
- recent 50: win_rate=0.48 wins=24 losses=26
- streak horizons: {'240': 11}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 37 / threshold 50
- recent 50: win_rate=0.26 wins=13 losses=37

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=37, win_rate=0.26
- additional recent-window wins needed: 2
- tail pathology: losses=37 / wins=13 / loss_share=0.74