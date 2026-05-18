# Circuit Breaker Audit（Heartbeat #1327-productization-finalverify）

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 26 / threshold 50
- recent 50: win_rate=0.28 wins=14 losses=36
- streak horizons: {'240': 26}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 23 / threshold 50
- recent 50: win_rate=0.2 wins=10 losses=40

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=23, win_rate=0.2
- additional recent-window wins needed: 5
- tail pathology: losses=40 / wins=10 / loss_share=0.8