# Circuit Breaker Audit（Heartbeat #1337）
_generated_at: 2026-05-18T16:35:56.845411Z_

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。
- top_level_release: ready=False / recent wins=5/50 / need=15 / gap=10

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 5 / threshold 50
- recent 50: win_rate=0.3 wins=15 losses=35
- streak horizons: {'240': 5}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 9 / threshold 50
- recent 50: win_rate=0.1 wins=5 losses=45

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=9, win_rate=0.1
- additional recent-window wins needed: 10
- tail pathology: losses=45 / wins=5 / loss_share=0.9