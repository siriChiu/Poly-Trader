# Circuit Breaker Audit（Heartbeat #1373）
_generated_at: 2026-05-19T22:21:31.386030Z_

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。
- top_level_release: ready=True / recent wins=19/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 3 / threshold 50
- recent 50: win_rate=0.36 wins=18 losses=32
- streak horizons: {'240': 3}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 6 / threshold 50
- recent 50: win_rate=0.38 wins=19 losses=31

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=6, win_rate=0.38
- additional recent-window wins needed: 0
- tail pathology: losses=31 / wins=19 / loss_share=0.62