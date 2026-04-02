
path = r'C:\Users\Kazuha\repo\Poly-Trader\dashboard\app.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the tabs declaration and add a new tab
old_tabs = 'tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(['
new_tabs = 'tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(['
old_tab_names = '"🔍 特徵分析", "🤖 模型預測", "📜 交易歷史", "📈 策略回測", "🔧 參數優化", "🔬 多感官有效性"'
new_tab_names = '"🔍 特徵分析", "🤖 模型預測", "📜 交易歷史", "📈 策略回測", "🔧 參數優化", "🔬 多感官有效性", "🔄 Walk-Forward 驗證"'

content = content.replace(old_tabs, new_tabs)
content = content.replace(old_tab_names, new_tab_names)

# Add Walk-Forward tab content before the final st.divider()
wf_tab = """
with tab7:
    st.subheader("🔄 Walk-Forward 參數穩健性驗證")
    st.write("在不同時間段驗證策略參數是否穩健，避免過擬合。")

    col_wf1, col_wf2, col_wf3 = st.columns(3)
    with col_wf1:
        wf_train_days = st.slider("訓練窗口 (天)", 10, 90, 30)
    with col_wf2:
        wf_test_days = st.slider("測試窗口 (天)", 5, 30, 10)
    with col_wf3:
        wf_n_windows = st.slider("滑動次數", 3, 10, 5)

    st.write("**最佳參數設定（用於驗證）**")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        wf_conf = st.slider("Confidence 閾值", 0.5, 0.9, 0.7, key="wf_conf")
    with col_p2:
        wf_pos = st.slider("最大部位比例", 0.01, 0.10, 0.05, key="wf_pos")
    with col_p3:
        wf_stop = st.slider("止損 %%", 0.01, 0.10, 0.03, key="wf_stop")

    if st.button("🚀 執行 Walk-Forward", type="primary"):
        st.info(f"執行 {wf_n_windows} 個窗口，每個訓練 {wf_train_days} 天 + 測試 {wf_test_days} 天...")
        try:
            from backtesting.walkforward import run_walk_forward
            from sqlalchemy.orm import sessionmaker as SM
            from sqlalchemy import create_engine as CE
            from config import load_config

            cfg = load_config()
            _e = CE(cfg["database"]["url"])
            _s = SM(bind=_e)()

            best_params = {
                "confidence_threshold": wf_conf,
                "max_position_ratio": wf_pos,
                "stop_loss_pct": wf_stop,
            }

            wf_result = run_walk_forward(
                _s, best_params,
                train_days=wf_train_days,
                test_days=wf_test_days,
                n_windows=wf_n_windows
            )
            _s.close()

            summary = wf_result.get("summary", {})
            verdict = summary.get("verdict", "N/A")
            stability = summary.get("stability_score", 0)

            if verdict == "STABLE":
                st.success(f"✅ 策略穩健性：**{verdict}** (分數 {stability:.0%})")
            else:
                st.warning(f"⚠️ 策略穩健性：**{verdict}** (分數 {stability:.0%})")

            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            col_s1.metric("平均 OOS 回報", f"{summary.get('avg_oos_return', 0):.2%}")
            col_s2.metric("平均 Sharpe", f"{summary.get('avg_sharpe', 0):.2f}")
            col_s3.metric("勝率窗口 %%", f"{summary.get('pct_profitable_windows', 0):.0%}")
            col_s4.metric("打贏 B&H 窗口 %%", f"{summary.get('pct_beat_bh', 0):.0%}")

            import pandas as pd
            windows_df = pd.DataFrame(wf_result.get("windows", []))
            if not windows_df.empty:
                st.subheader("各窗口詳細結果")
                display_cols = ["window", "test_start", "test_end", "total_return",
                                "sharpe_ratio", "max_drawdown", "win_rate",
                                "alpha", "total_trades", "status"]
                show_cols = [c for c in display_cols if c in windows_df.columns]
                st.dataframe(windows_df[show_cols], use_container_width=True)

                import plotly.graph_objects as go
                fig_wf = go.Figure()
                fig_wf.add_trace(go.Bar(
                    x=[f"W{r['window']}" for _, r in windows_df.iterrows()],
                    y=[r.get("total_return", 0) * 100 for _, r in windows_df.iterrows()],
                    name="OOS 回報 %%",
                    marker_color=["green" if v > 0 else "red" for v in windows_df.get("total_return", [])]
                ))
                fig_wf.add_hline(y=0, line_dash="dash", line_color="white")
                fig_wf.update_layout(title="Walk-Forward 各窗口回報", height=300)
                st.plotly_chart(fig_wf, use_container_width=True)
        except Exception as e:
            st.exception(e)
    else:
        st.info("設定參數後點擊執行。建議先在 Tab5 找到最佳參數，再來這裡驗證穩健性。")

"""

content = content.replace("st.divider()\nst.caption(", wf_tab + "\nst.divider()\nst.caption(")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Dashboard tab7 added")
