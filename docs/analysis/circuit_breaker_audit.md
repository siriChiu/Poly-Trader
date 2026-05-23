# Circuit Breaker Audit（Heartbeat #1467）
_generated_at: 2026-05-23T19:14:02.284552Z_

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。
- top_level_release: ready=False / recent wins=6/50 / need=15 / gap=9

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 0 / threshold 50
- recent 50: win_rate=0.72 wins=36 losses=14
- streak horizons: {}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 4 / threshold 50
- recent 50: win_rate=0.12 wins=6 losses=44

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=4, win_rate=0.12
- additional recent-window wins needed: 9
- tail pathology: losses=44 / wins=6 / loss_share=0.88