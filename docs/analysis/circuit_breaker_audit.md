# Circuit Breaker Audit（Heartbeat #1434）
_generated_at: 2026-05-22T09:21:14.771102Z_

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。
- top_level_release: ready=False / recent wins=1/50 / need=15 / gap=14

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 19 / threshold 50
- recent 50: win_rate=0.34 wins=17 losses=33
- streak horizons: {'240': 19}

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