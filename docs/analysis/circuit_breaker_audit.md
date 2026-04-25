# Circuit Breaker Audit（Heartbeat #20260425_084505）

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 9 / threshold 50
- recent 50: win_rate=0.34 wins=17 losses=33
- streak horizons: {'240': 9}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 49 / threshold 50
- recent 50: win_rate=0.02 wins=1 losses=49

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=49, win_rate=0.02
- additional recent-window wins needed: 14
- tail pathology: losses=49 / wins=1 / loss_share=0.98