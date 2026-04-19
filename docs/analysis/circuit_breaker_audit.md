# Circuit Breaker Audit（Heartbeat #20260419h）

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['streak', 'recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 1 / threshold 50
- recent 50: win_rate=0.54 wins=27 losses=23
- streak horizons: {'240': 1}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['streak', 'recent_win_rate']
- release_ready: **False**
- streak: 240 / threshold 50
- recent 50: win_rate=0.0 wins=0 losses=50

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=240, win_rate=0.0
- additional recent-window wins needed: 15
- tail pathology: losses=50 / wins=0 / loss_share=1.0