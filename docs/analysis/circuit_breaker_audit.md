# Circuit Breaker Audit（Heartbeat #adhoc_codex_20260605_pivot_quick_read_final_docs_resync）
_generated_at: 2026-06-05T03:46:13.125173Z_

## 結論
- verdict: **breaker_clear**
- summary: 1440m canonical live horizon 未觸發 breaker。
- recommended_patch: 維持 horizon-aligned breaker，繼續追 live q15/q35 / support route。
- top_level_release: ready=True / recent wins=20/50 / need=15 / gap=0

## Mixed scope（現況錯誤口徑）
- triggered: **False** via []
- streak: 1 / threshold 50
- recent 50: win_rate=0.54 wins=27 losses=23
- streak horizons: {'240': 1}

## Aligned scope（1440m canonical live horizon）
- triggered: **False** via []
- release_ready: **True**
- streak: 2 / threshold 50
- recent 50: win_rate=0.4 wins=20 losses=30

## Release condition
- streak < 50
- recent 50 win_rate >= 30%
- aligned_scope_now: streak=2, win_rate=0.4
- additional recent-window wins needed: 0
- tail pathology: losses=30 / wins=20 / loss_share=0.6