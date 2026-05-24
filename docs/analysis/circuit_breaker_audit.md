# Circuit Breaker Audit（Heartbeat #1478）
_generated_at: 2026-05-24T06:26:34.052418Z_

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。
- top_level_release: ready=True / recent wins=42/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 8 / threshold 50
- recent 50: win_rate=0.68 wins=34 losses=16
- streak horizons: {'240': 8}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 0 / threshold 50
- recent 50: win_rate=0.84 wins=42 losses=8

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=0, win_rate=0.84
- additional recent-window wins needed: 0
- tail pathology: losses=8 / wins=42 / loss_share=0.16