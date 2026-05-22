# Circuit Breaker Audit（Heartbeat #1432）
_generated_at: 2026-05-22T07:13:10.602788Z_

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。
- top_level_release: ready=False / recent wins=13/50 / need=15 / gap=2

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 9 / threshold 50
- recent 50: win_rate=0.5 wins=25 losses=25
- streak horizons: {'240': 9}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 35 / threshold 50
- recent 50: win_rate=0.26 wins=13 losses=37

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=35, win_rate=0.26
- additional recent-window wins needed: 2
- tail pathology: losses=37 / wins=13 / loss_share=0.74