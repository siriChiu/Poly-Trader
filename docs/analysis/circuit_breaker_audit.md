# Circuit Breaker Audit（Heartbeat #1554）
_generated_at: 2026-05-28T03:10:39.696138Z_

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['streak', 'recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。
- top_level_release: ready=False / recent wins=0/50 / need=15 / gap=15

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 11 / threshold 50
- recent 50: win_rate=0.22 wins=11 losses=39
- streak horizons: {'240': 11}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['streak', 'recent_win_rate']
- release_ready: **False**
- streak: 166 / threshold 50
- recent 50: win_rate=0.0 wins=0 losses=50

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=166, win_rate=0.0
- additional recent-window wins needed: 15
- tail pathology: losses=50 / wins=0 / loss_share=1.0