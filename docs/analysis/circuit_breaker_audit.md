# Circuit Breaker Audit（Heartbeat #1389）
_generated_at: 2026-05-20T14:30:42.906797Z_

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。
- top_level_release: ready=True / recent wins=41/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 4 / threshold 50
- recent 50: win_rate=0.8 wins=40 losses=10
- streak horizons: {'240': 4}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 0 / threshold 50
- recent 50: win_rate=0.82 wins=41 losses=9

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=0, win_rate=0.82
- additional recent-window wins needed: 0
- tail pathology: losses=9 / wins=41 / loss_share=0.18