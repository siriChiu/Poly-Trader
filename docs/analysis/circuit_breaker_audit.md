# Circuit Breaker Audit（Heartbeat #1524）
_generated_at: 2026-05-26T13:28:35.722297Z_

## 結論
- verdict: **canonical_breaker_active**
- summary: 1440m canonical live horizon 仍觸發 breaker：['recent_win_rate']。
- recommended_patch: 維持 breaker，改做 canonical tail root-cause / release-condition artifact。
- top_level_release: ready=False / recent wins=8/50 / need=15 / gap=7

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 1 / threshold 50
- recent 50: win_rate=0.36 wins=18 losses=32
- streak horizons: {'240': 1}

## Aligned scope（1440m canonical live horizon）
- triggered: **True** via ['recent_win_rate']
- release_ready: **False**
- streak: 41 / threshold 50
- recent 50: win_rate=0.16 wins=8 losses=42

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=41, win_rate=0.16
- additional recent-window wins needed: 7
- tail pathology: losses=42 / wins=8 / loss_share=0.84