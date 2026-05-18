# Circuit Breaker Audit（Heartbeat #1338）
_generated_at: 2026-05-18T17:15:47.636409Z_

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。
- top_level_release: ready=False / recent wins=4/50 / need=15 / gap=11

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 7 / threshold 50
- recent 50: win_rate=0.3 wins=15 losses=35
- streak horizons: {'240': 7}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 11 / threshold 50
- recent 50: win_rate=0.08 wins=4 losses=46

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=11, win_rate=0.08
- additional recent-window wins needed: 11
- tail pathology: losses=46 / wins=4 / loss_share=0.92