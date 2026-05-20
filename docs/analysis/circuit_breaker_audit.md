# Circuit Breaker Audit（Heartbeat #1384）
_generated_at: 2026-05-20T09:14:20.814630Z_

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。
- top_level_release: ready=True / recent wins=29/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 0 / threshold 50
- recent 50: win_rate=0.64 wins=32 losses=18
- streak horizons: {}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 0 / threshold 50
- recent 50: win_rate=0.58 wins=29 losses=21

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=0, win_rate=0.58
- additional recent-window wins needed: 0
- tail pathology: losses=21 / wins=29 / loss_share=0.42