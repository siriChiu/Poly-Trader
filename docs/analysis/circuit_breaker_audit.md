# Circuit Breaker Audit（Heartbeat #1415）
_generated_at: 2026-05-21T14:09:36.950227Z_

## 結論
- verdict: **mixed_horizon_false_positive**
- summary: 混合 horizon breaker 會被 240m tail labels 觸發（streak=21，recent50 win_rate=0.2000），但 1440m canonical live horizon 目前 release-ready。
- recommended_patch: 將 circuit breaker 對齊 horizon_minutes=1440 的 canonical live contract。
- top_level_release: ready=True / recent wins=35/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **True** via ['recent_win_rate']
- streak: 21 / threshold 50
- recent 50: win_rate=0.2 wins=10 losses=40
- streak horizons: {'240': 21}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 15 / threshold 50
- recent 50: win_rate=0.7 wins=35 losses=15

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=15, win_rate=0.7
- additional recent-window wins needed: 0
- tail pathology: losses=15 / wins=35 / loss_share=0.3