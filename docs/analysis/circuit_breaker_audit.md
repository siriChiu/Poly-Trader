# Circuit Breaker Audit（Heartbeat #1407）
_generated_at: 2026-05-21T06:19:26.750211Z_

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。
- top_level_release: ready=True / recent wins=50/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 6 / threshold 50
- recent 50: win_rate=0.52 wins=26 losses=24
- streak horizons: {'240': 6}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 0 / threshold 50
- recent 50: win_rate=1.0 wins=50 losses=0

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=0, win_rate=1.0
- additional recent-window wins needed: 0
- tail pathology: losses=0 / wins=50 / loss_share=0.0