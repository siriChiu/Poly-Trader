# Circuit Breaker Audit（Heartbeat #1435）
_generated_at: 2026-05-22T10:13:08.951343Z_

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。
- top_level_release: ready=False / recent wins=4/50 / need=15 / gap=11

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 1 / threshold 50
- recent 50: win_rate=0.38 wins=19 losses=31
- streak horizons: {'240': 1}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 0 / threshold 50
- recent 50: win_rate=0.08 wins=4 losses=46

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=0, win_rate=0.08
- additional recent-window wins needed: 11
- tail pathology: losses=46 / wins=4 / loss_share=0.92