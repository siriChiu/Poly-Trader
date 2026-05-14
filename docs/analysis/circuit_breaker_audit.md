# Circuit Breaker Audit（Heartbeat #1211）

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 6 / threshold 50
- recent 50: win_rate=0.32 wins=16 losses=34
- streak horizons: {'240': 6}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 8 / threshold 50
- recent 50: win_rate=0.22 wins=11 losses=39

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=8, win_rate=0.22
- additional recent-window wins needed: 4
- tail pathology: losses=39 / wins=11 / loss_share=0.78