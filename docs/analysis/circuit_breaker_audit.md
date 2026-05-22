# Circuit Breaker Audit（Heartbeat #1446）
_generated_at: 2026-05-22T21:09:38.406683Z_

## 結論
- verdict: **mixed_horizon_false_positive**
- summary: 混合 horizon breaker 會被 240m tail labels 觸發（streak=34，recent50 win_rate=0.1800），但 1440m canonical live horizon 目前 release-ready。
- recommended_patch: 將 circuit breaker 對齊 horizon_minutes=1440 的 canonical live contract。
- top_level_release: ready=True / recent wins=19/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 34 / threshold 50
- recent 50: win_rate=0.18 wins=9 losses=41
- streak horizons: {'240': 34}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 31 / threshold 50
- recent 50: win_rate=0.38 wins=19 losses=31

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=31, win_rate=0.38
- additional recent-window wins needed: 0
- tail pathology: losses=31 / wins=19 / loss_share=0.62