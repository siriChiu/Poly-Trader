# Circuit Breaker Audit（Heartbeat #1491）
_generated_at: 2026-05-24T20:14:19.298156Z_

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。
- top_level_release: ready=True / recent wins=46/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 0 / threshold 50
- recent 50: win_rate=0.56 wins=28 losses=22
- streak horizons: {}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 4 / threshold 50
- recent 50: win_rate=0.92 wins=46 losses=4

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=4, win_rate=0.92
- additional recent-window wins needed: 0
- tail pathology: losses=4 / wins=46 / loss_share=0.08