# Circuit Breaker Audit（Heartbeat #1271）

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 2 / threshold 50
- recent 50: win_rate=0.28 wins=14 losses=36
- streak horizons: {'240': 2}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 42 / threshold 50
- recent 50: win_rate=0.16 wins=8 losses=42

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=42, win_rate=0.16
- additional recent-window wins needed: 7
- tail pathology: losses=42 / wins=8 / loss_share=0.84