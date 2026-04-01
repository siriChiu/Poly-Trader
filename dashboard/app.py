#!/usr/bin/env python3
"""
Poly-Trader 可視化儀表板 (Streamlit) - v2 with Backtesting
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os

# 頁面設定
st.set_page_config(
    page_title="Poly-Trader 儀表板",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Poly-Trader 多感官量化交易系統")

# 資料庫連接
DB_PATH = os.getenv("POLY_TRADER_DB", f"sqlite:///{PROJECT_ROOT / 'poly_trader.db'}")
engine = create_engine(DB_PATH)

# 側邊欄：全局設定
st.sidebar.header("⚙️ 設定")
days_back = st.sidebar.slider("顯示過去天數", 1, 30, 7)
refresh_interval = st.sidebar.number_input("自動刷新秒數", 10, 300, 60)
auto_refresh = st.sidebar.checkbox("自動刷新", True)
if auto_refresh:
    st.rerun_interval = refresh_interval

# 載入數據函數
@st.cache_data(ttl=30)
def load_features(days: int):
    start_time = datetime.utcnow() - timedelta(days=days)
    query = text("""
        SELECT timestamp, feat_eye_dist, feat_ear_zscore, feat_nose_sigmoid,
               feat_tongue_pct, feat_body_roc
        FROM features_normalized
        WHERE timestamp >= :start
        ORDER BY timestamp
    """)
    df = pd.read_sql(query, engine, params={"start": start_time})
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

@st.cache_data(ttl=30)
def load_trades(days: int):
    start_time = datetime.utcnow() - timedelta(days=days)
    query = text("""
        SELECT timestamp, action, price, amount, model_confidence, pnl
        FROM trade_history
        WHERE timestamp >= :start
        ORDER BY timestamp DESC
    """)
    df = pd.read_sql(query, engine, params={"start": start_time})
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

@st.cache_data(ttl=30)
def load_latest_prediction():
    query = text("""
        SELECT timestamp, feat_eye_dist, feat_ear_zscore, feat_nose_sigmoid,
               feat_tongue_pct, feat_body_roc
        FROM features_normalized
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    df = pd.read_sql(query, engine)
    if not df.empty:
        weights = [0.2]*5
        vals = df.iloc[0][["feat_eye_dist","feat_ear_zscore","feat_nose_sigmoid","feat_tongue_pct","feat_body_roc"]].fillna(0).values
        score = sum(v * w for v, w in zip(vals, weights))
        import numpy as np
        confidence = 1/(1+np.exp(-score))
        df["confidence"] = confidence
        df["signal"] = "BUY" if confidence > 0.5 else "HOLD"
    return df

# 載入數據
features_df = load_features(days_back)
trades_df = load_trades(days_back)
latest_pred = load_latest_prediction()

# 頂部指標
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("數據點數", len(features_df))
with col2:
    if not latest_pred.empty:
        conf = latest_pred.iloc[0]["confidence"]
        st.metric("最新信心分數", f"{conf:.2%}", delta=f"{conf-0.5:.2%}")
    else:
        st.metric("最新信心分數", "N/A")
with col3:
    if not trades_df.empty:
        last_trade = trades_df.iloc[0]
        st.metric("最後交易", f"{last_trade['action']} @ {last_trade['price']:.0f}")
    else:
        st.metric("最後交易", "無")
with col4:
    if not trades_df.empty and "pnl" in trades_df.columns:
        total_pnl = trades_df["pnl"].sum()
        st.metric("累計 P&L", f"{total_pnl:.2f} USDT")
    else:
        st.metric("累計 P&L", "N/A")

st.divider()

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔍 特徵分析", "🤖 模型預測", "📜 交易歷史", "📈 策略回測", "🔧 參數優化", "🔬 多感官有效性"
])

with tab1:
    st.subheader("多感官特徵趨勢")
    if not features_df.empty:
        fig = go.Figure()
        for col in ["feat_eye_dist","feat_ear_zscore","feat_nose_sigmoid","feat_tongue_pct","feat_body_roc"]:
            fig.add_trace(go.Scatter(x=features_df["timestamp"], y=features_df[col],
                                     mode='lines+markers', name=col))
        fig.update_layout(height=400, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("特徵相關性")
        corr = features_df[["feat_eye_dist","feat_ear_zscore","feat_nose_sigmoid","feat_tongue_pct","feat_body_roc"]].corr()
        fig_corr = px.imshow(corr, text_auto=True, aspect="auto", color_continuous_scale='RdBu')
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("暫無特徵數據")

with tab2:
    st.subheader("模型預測详情")
    if not latest_pred.empty:
        lp = latest_pred.iloc[0]
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("**最新特徵**")
            st.json({
                "feat_eye_dist": lp["feat_eye_dist"],
                "feat_ear_zscore": lp["feat_ear_zscore"],
                "feat_nose_sigmoid": lp["feat_nose_sigmoid"],
                "feat_tongue_pct": lp["feat_tongue_pct"],
                "feat_body_roc": lp["feat_body_roc"]
            })
        with col_b:
            st.write("**預測結果**")
            st.success(f"信心分數: **{lp['confidence']:.2%}**")
            st.info(f"交易信號: **{lp['signal']}**")
            st.write(f"時間: {lp['timestamp']}")
    else:
        st.warning("無預測數據")

with tab3:
    st.subheader("交易歷史")
    if not trades_df.empty:
        st.dataframe(trades_df, use_container_width=True, height=400)
        if "pnl" in trades_df.columns:
            trades_df["cum_pnl"] = trades_df["pnl"].cumsum()
            fig_pnl = px.line(trades_df.sort_values("timestamp"), x="timestamp", y="cum_pnl",
                              title="累計 P&L", markers=True)
            st.plotly_chart(fig_pnl, use_container_width=True)
    else:
        st.info("暫無交易記錄")

with tab4:
    st.subheader("策略回測")
    # 參數選擇
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        start_dt = st.date_input("開始日期", datetime.utcnow() - timedelta(days=30))
    with col_c:
        end_dt = st.date_input("結束日期", datetime.utcnow())
    with col_b:
        initial_capital = st.number_input("初始資金 (USDT)", 1000.0, 1000000.0, 10000.0)

    if st.button("🚀 執行回測", type="primary"):
        st.info("正在執行回測，請稍候...")
        try:
            from backtesting.engine import run_backtest
            from backtesting.metrics import calculate_metrics
            from sqlalchemy.orm import Session
            from database.models import init_db
            from config import load_config

            cfg = load_config()
            db_url = cfg["database"]["url"]
            engine_local = create_engine(db_url)
            SessionLocal = sessionmaker(bind=engine_local)
            session = SessionLocal()

            start_date = datetime.combine(start_dt, datetime.min.time())
            end_date = datetime.combine(end_dt, datetime.max.time())

            results = run_backtest(
                session=session,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                confidence_threshold=0.7,
                max_position_ratio=0.05,
                stop_loss_pct=0.03,
                symbol=cfg["trading"]["symbol"]
            )
            session.close()

            if results:
                equity_df = results["equity_curve"]
                trades = results["trade_log"]
                metrics = calculate_metrics(equity_df["equity"], trades)

                # 顯示結果
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                col_m1.metric("總回報", f"{metrics['total_return']:.2%}")
                col_m2.metric("夏普比率", f"{metrics['sharpe_ratio']:.2f}")
                col_m3.metric("最大回撤", f"{metrics['max_drawdown']:.2%}")
                col_m4.metric("交易次數", int(metrics.get('total_trades', 0)))

                # 收益曲線
                fig_equity = go.Figure()
                fig_equity.add_trace(go.Scatter(x=equity_df.index, y=equity_df["equity"],
                                                mode='lines', name='策略 equity'))
                fig_equity.update_layout(title='回測資金曲線', xaxis_title='日期', yaxis_title='USDT')
                st.plotly_chart(fig_equity, use_container_width=True)

                # 交易列表
                if not trades.empty:
                    st.dataframe(trades, use_container_width=True)
            else:
                st.error("回測失敗，可能是數據不足。")
        except Exception as e:
            st.exception(e)
    else:
        st.info("請選擇日期範圍並點擊執行回測。")

with tab5:
    st.subheader("參數優化")
    st.write("調整參數範圍以搜索最佳策略配置。這可能需要幾分鐘。")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        conf_range = st.slider("Confidence 閾值", 0.5, 0.9, (0.6, 0.8), step=0.05)
    with col_b:
        pos_range = st.slider("最大部位比例", 0.01, 0.1, (0.02, 0.06), step=0.01)
    with col_c:
        stop_range = st.slider("止損 %", 0.01, 0.1, (0.02, 0.05), step=0.01)

    # _grid steps
    col_d, col_e, col_f = st.columns(3)
    with col_d:
        conf_steps = st.number_input("Confidence steps", 2, 10, 3)
    with col_e:
        pos_steps = st.number_input("部位比例 steps", 2, 10, 3)
    with col_f:
        stop_steps = st.number_input("止損 steps", 2, 10, 2)

    if st.button("🔍 開始優化搜索", type="secondary"):
        st.info("開始參數網格搜索...")
        try:
            from backtesting.optimizer import grid_search
            from database.models import init_db
            from config import load_config
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy import create_engine

            cfg = load_config()
            db_url = cfg["database"]["url"]
            engine_local = create_engine(db_url)
            SessionLocal = sessionmaker(bind=engine_local)
            session = SessionLocal()

            # 生成網格
            conf_values = [round(conf_range[0] + i * (conf_range[1]-conf_range[0])/(conf_steps-1), 2) for i in range(conf_steps)]
            pos_values = [round(pos_range[0] + i * (pos_range[1]-pos_range[0])/(pos_steps-1), 2) for i in range(pos_steps)]
            stop_values = [round(stop_range[0] + i * (stop_range[1]-stop_range[0])/(stop_steps-1), 3) for i in range(stop_steps)]

            st.write(f"網格大小：{len(conf_values)} x {len(pos_values)} x {len(stop_values)} = {len(conf_values)*len(pos_values)*len(stop_values)} 次回測")

            results_df = grid_search(
                session=session,
                confidence_thresholds=conf_values,
                max_position_ratios=pos_values,
                stop_loss_pcts=stop_values,
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
                initial_capital=10000.0,
                symbol=cfg["trading"]["symbol"]
            )
            session.close()

            if not results_df.empty:
                st.success(f"優化完成，共測試 {len(results_df)} 組參數")

                # 顯示最佳結果
                best_sharpe = results_df.loc[results_df["sharpe_ratio"].idxmax()]
                st.write("**最佳參數（Sharpe 最高）**：")
                st.json(best_sharpe.to_dict())

                # 熱圖：Confidence vs Position Ratio (固定 stop_loss 為中位數)
                median_stop = results_df["stop_loss_pct"].median()
                pivot_df = results_df[results_df["stop_loss_pct"] == median_stop]
                pivot = pivot_df.pivot_table(index="confidence_threshold", columns="max_position_ratio", values="sharpe_ratio")
                fig_heat = px.imshow(pivot, text_auto=True, aspect="auto", title=f"Sharpe Ratio (stop_loss={median_stop:.3f})")
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.error("優化失敗，可能數據不足或回測錯誤。")
        except Exception as e:
            st.exception(e)

with tab6:
    st.subheader("🔬 多感官有效性分析")
    st.write("量化每个感官特征与未来收益率的相关性（IC）及分位数胜率。")

    # 从 config 加载
    cfg = load_config()
    db_url = cfg["database"]["url"]
    engine_local = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine_local)
    session = SessionLocal()

    try:
        from analysis.sense_effectiveness import compute_information_coefficient, compute_win_rate_by_feature_quantile

        # 1. 计算 IC
        st.write("**📌 信息系数 (IC)**")
        ic = compute_information_coefficient(session, cfg["trading"]["symbol"], horizon_hours=24)
        if ic:
            ic_df = pd.DataFrame(list(ic.items()), columns=["Feature", "IC"])
            fig_ic = px.bar(ic_df, x="Feature", y="IC", title="Information Coefficient (Spearman) by Feature", color="IC", color_continuous_scale="RdYlGn")
            st.plotly_chart(fig_ic, use_container_width=True)
            st.dataframe(ic_df, use_container_width=True)
        else:
            st.warning("暂无足够数据计算 IC")

        # 2. 分位数胜率
        st.write("**📊 分位数胜率热图**")
        quantile_df = compute_win_rate_by_feature_quantile(session, cfg["trading"]["symbol"], horizon_hours=24, n_quantiles=5)
        if not quantile_df.empty:
            # 热图：特征 vs 分位数，值为 win_rate
            pivot = quantile_df.pivot_table(index="quantile", columns="feature", values="win_rate")
            fig_heat = px.imshow(pivot, text_auto=".1%", aspect="auto", title="Win Rate by Feature Quantile", color_continuous_scale="YlOrRd")
            st.plotly_chart(fig_heat, use_container_width=True)

            # 显示原始数据
            st.write("原始数据：")
            st.dataframe(quantile_df, use_container_width=True)
        else:
            st.warning("暂无足够数据计算分位数胜率")
    except Exception as e:
        st.error(f"分析失败: {e}")
    finally:
        session.close()

st.divider()
st.caption("💡 提示：若要啟用真實數據，請完成多感官數據寫入與模型訓練流程。")
