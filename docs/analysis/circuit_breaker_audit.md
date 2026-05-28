# Circuit Breaker Audit（Heartbeat #1546）
_generated_at: 2026-05-28T00:06:33.338298Z_

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['streak', 'recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。
- top_level_release: ready=False / recent wins=0/50 / need=15 / gap=15

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 7 / threshold 50
- recent 50: win_rate=0.2 wins=10 losses=40
- streak horizons: {'240': 7}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['streak', 'recent_win_rate']
- release_ready: **False**
- streak: 163 / threshold 50
- recent 50: win_rate=0.0 wins=0 losses=50

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=163, win_rate=0.0
- additional recent-window wins needed: 15
- tail pathology: losses=50 / wins=0 / loss_share=1.0