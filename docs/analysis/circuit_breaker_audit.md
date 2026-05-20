# Circuit Breaker Audit（Heartbeat #1377）
_generated_at: 2026-05-20T02:14:25.327474Z_

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。
- top_level_release: ready=True / recent wins=27/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 2 / threshold 50
- recent 50: win_rate=0.42 wins=21 losses=29
- streak horizons: {'240': 2}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 0 / threshold 50
- recent 50: win_rate=0.54 wins=27 losses=23

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=0, win_rate=0.54
- additional recent-window wins needed: 0
- tail pathology: losses=23 / wins=27 / loss_share=0.46