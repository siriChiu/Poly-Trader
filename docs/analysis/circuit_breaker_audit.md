# Circuit Breaker Audit（Heartbeat #1525）
_generated_at: 2026-05-26T15:29:53.760554Z_

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。
- top_level_release: ready=False / recent wins=2/50 / need=15 / gap=13

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 4 / threshold 50
- recent 50: win_rate=0.36 wins=18 losses=32
- streak horizons: {'240': 4}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 48 / threshold 50
- recent 50: win_rate=0.04 wins=2 losses=48

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=48, win_rate=0.04
- additional recent-window wins needed: 13
- tail pathology: losses=48 / wins=2 / loss_share=0.96