# Circuit Breaker Audit（Heartbeat #1447）
_generated_at: 2026-05-22T22:12:29.705131Z_

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。
- top_level_release: ready=False / recent wins=14/50 / need=15 / gap=1

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 39 / threshold 50
- recent 50: win_rate=0.18 wins=9 losses=41
- streak horizons: {'240': 39}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 36 / threshold 50
- recent 50: win_rate=0.28 wins=14 losses=36

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=36, win_rate=0.28
- additional recent-window wins needed: 1
- tail pathology: losses=36 / wins=14 / loss_share=0.72