# Circuit Breaker Audit（Heartbeat #1493）
_generated_at: 2026-05-24T22:09:04.370982Z_

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。
- top_level_release: ready=True / recent wins=40/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 0 / threshold 50
- recent 50: win_rate=0.46 wins=23 losses=27
- streak horizons: {}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 1 / threshold 50
- recent 50: win_rate=0.8 wins=40 losses=10

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=1, win_rate=0.8
- additional recent-window wins needed: 0
- tail pathology: losses=10 / wins=40 / loss_share=0.2