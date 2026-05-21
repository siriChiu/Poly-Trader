# Circuit Breaker Audit（Heartbeat #1421）
_generated_at: 2026-05-21T20:13:48.264095Z_

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。
- top_level_release: ready=True / recent wins=16/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 0 / threshold 50
- recent 50: win_rate=0.42 wins=21 losses=29
- streak horizons: {}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 1 / threshold 50
- recent 50: win_rate=0.32 wins=16 losses=34

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=1, win_rate=0.32
- additional recent-window wins needed: 0
- tail pathology: losses=34 / wins=16 / loss_share=0.68