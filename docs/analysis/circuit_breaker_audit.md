# Circuit Breaker Audit（Heartbeat #20260425_070309）

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 3 / threshold 50
- recent 50: win_rate=0.44 wins=22 losses=28
- streak horizons: {'240': 3}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 41 / threshold 50
- recent 50: win_rate=0.08 wins=4 losses=46

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=41, win_rate=0.08
- additional recent-window wins needed: 11
- tail pathology: losses=46 / wins=4 / loss_share=0.92