# Circuit Breaker Audit（Heartbeat #1433）
_generated_at: 2026-05-22T08:12:16.913272Z_

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。
- top_level_release: ready=False / recent wins=7/50 / need=15 / gap=8

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 15 / threshold 50
- recent 50: win_rate=0.38 wins=19 losses=31
- streak horizons: {'240': 15}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 43 / threshold 50
- recent 50: win_rate=0.14 wins=7 losses=43

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=43, win_rate=0.14
- additional recent-window wins needed: 8
- tail pathology: losses=43 / wins=7 / loss_share=0.86