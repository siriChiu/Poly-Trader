# Circuit Breaker Audit（Heartbeat #1358）
_generated_at: 2026-05-19T12:10:04.916864Z_

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。
- top_level_release: ready=False / recent wins=10/50 / need=15 / gap=5

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 12 / threshold 50
- recent 50: win_rate=0.52 wins=26 losses=24
- streak horizons: {'240': 12}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 4 / threshold 50
- recent 50: win_rate=0.2 wins=10 losses=40

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=4, win_rate=0.2
- additional recent-window wins needed: 5
- tail pathology: losses=40 / wins=10 / loss_share=0.8