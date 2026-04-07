#!/usr/bin/env python3
"""
Poly-Trader Dashboard v3 — gmgn.ai style dark theme
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

st.set_page_config(page_title="Poly-Trader", page_icon="📡", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""<style>
.block-container{padding:1rem 2rem}
.hero-card{background:#161616;border:1px solid #2a2a2a;border-radius:8px;padding:16px;text-align:center}
.kpi-label{color:#888;font-size:.72rem;text-transform:uppercase;letter-spacing:1px}
.kpi-value{font-size:1.4rem;font-weight:700;line-height:1.2}
.conf-bar-bg{background:#1e1e1e;border-radius:4px;height:8px;margin-top:4px}
</style>""", unsafe_allow_html=True)

from config import load_config
cfg = load_config()
engine = create_engine(cfg["database"]["url"])
API_BASE = st.sidebar.text_input("API Base", value="http://127.0.0.1:8000/api")

@st.cache_data(ttl=30)
def get_latest_market():
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT r.timestamp,
                   r.close_price,
                   r.volume,
                   r.funding_rate,
                   COALESCE(f.feat_eye, 0.5) AS feat_eye,
                   COALESCE(f.feat_ear, 0.5) AS feat_ear,
                   COALESCE(f.feat_nose, 0.5) AS feat_nose,
                   COALESCE(f.feat_tongue, 0.5) AS feat_tongue,
                   COALESCE(f.feat_body, 0.5) AS feat_body,
                   COALESCE(f.feat_pulse, 0) AS feat_pulse,
                   COALESCE(f.feat_aura, 0) AS feat_aura,
                   COALESCE(f.feat_mind, 0) AS feat_mind
            FROM raw_market_data r
            LEFT JOIN features_normalized f ON f.timestamp = r.timestamp
            ORDER BY r.timestamp DESC
            LIMIT 1
        """)).fetchone()
    return row

@st.cache_data(ttl=30)
def get_confidence():
    try:
        from model.predictor import load_predictor
        pred = load_predictor()
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT COALESCE(feat_eye, 0.5) AS feat_eye,
                       COALESCE(feat_ear, 0.5) AS feat_ear,
                       COALESCE(feat_nose, 0.5) AS feat_nose,
                       COALESCE(feat_tongue, 0.5) AS feat_tongue,
                       COALESCE(feat_body, 0.5) AS feat_body,
                       COALESCE(feat_pulse, 0) AS feat_pulse,
                       COALESCE(feat_aura, 0) AS feat_aura,
                       COALESCE(feat_mind, 0) AS feat_mind
                FROM features_normalized
                ORDER BY timestamp DESC
                LIMIT 1
            """)).fetchone()
        if row is None:
            return 0.5, "HOLD"
        feats = {
            "feat_eye": row[0], "feat_ear": row[1], "feat_nose": row[2], "feat_tongue": row[3],
            "feat_body": row[4], "feat_pulse": row[5], "feat_aura": row[6], "feat_mind": row[7]
        }
        conf = pred.predict_proba(feats)
        if conf is None:
            return 0.5, "HOLD"
        sig = "BUY" if conf >= 0.65 else ("SELL" if conf <= 0.35 else "HOLD")
        return float(conf), sig
    except Exception:
        return 0.5, "HOLD"

@st.cache_data(ttl=60)
def get_fng():
    try:
        import requests
        d = requests.get("https://api.alternative.me/fng/?limit=1&format=json",timeout=5).json()["data"][0]
        return int(d["value"]), d["value_classification"]
    except Exception:
        return None, "N/A"

@st.cache_data(ttl=30)
def get_price_history(days=7):
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT timestamp,close_price FROM raw_market_data WHERE timestamp>=:s ORDER BY timestamp ASC"),{"s":datetime.utcnow()-timedelta(days=days)}).fetchall()
    if not rows:
        return pd.DataFrame(columns=["timestamp","close_price"])
    df = pd.DataFrame(rows,columns=["timestamp","close_price"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

@st.cache_data(ttl=30)
def get_sense_history(hours=24):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT timestamp,
                   COALESCE(feat_eye, 0.5) AS eye,
                   COALESCE(feat_ear, 0.5) AS ear,
                   COALESCE(feat_nose, 0.5) AS nose,
                   COALESCE(feat_tongue, 0.5) AS tongue,
                   COALESCE(feat_body, 0.5) AS body,
                   COALESCE(feat_pulse, 0) AS pulse,
                   COALESCE(feat_aura, 0) AS aura,
                   COALESCE(feat_mind, 0) AS mind
            FROM features_normalized
            WHERE timestamp >= :s
            ORDER BY timestamp ASC
        """), {"s": datetime.utcnow() - timedelta(hours=hours)}).fetchall()
    if not rows:
        return pd.DataFrame(columns=["ts", "eye", "ear", "nose", "tongue", "body", "pulse", "aura", "mind"])
    df = pd.DataFrame(rows, columns=["ts", "eye", "ear", "nose", "tongue", "body", "pulse", "aura", "mind"])
    df["ts"] = pd.to_datetime(df["ts"])
    return df

@st.cache_data(ttl=30)
def get_price_sense_overlay(days=7):
    """Nearest-match 對齊價格與多特徵，提供同圖走勢。"""
    price_df = get_price_history(days=days)
    sense_df = get_sense_history(hours=days * 24)
    cols = ["timestamp", "close_price", "eye", "ear", "nose", "tongue", "body", "pulse", "aura", "mind"]
    if price_df.empty or sense_df.empty:
        return pd.DataFrame(columns=cols)

    price_df = price_df.sort_values("timestamp").copy().rename(columns={"timestamp": "ts"})
    sense_df = sense_df.sort_values("ts").copy()
    merged = pd.merge_asof(price_df, sense_df, on="ts", direction="nearest", tolerance=pd.Timedelta("120min"))
    if merged.empty:
        merged = price_df.rename(columns={"ts": "timestamp"}).copy()
        merged = merged.merge(sense_df, how="left", left_on="timestamp", right_on="ts")
        merged = merged.drop(columns=["ts"], errors="ignore").ffill().bfill()
    else:
        merged = merged.rename(columns={"ts": "timestamp"})
        merged["timestamp"] = pd.to_datetime(merged["timestamp"])
        for c in ["eye", "ear", "nose", "tongue", "body", "pulse", "aura", "mind"]:
            if c in merged.columns:
                merged[c] = pd.to_numeric(merged[c], errors="coerce").ffill().bfill()
    return merged[[c for c in cols if c in merged.columns]].copy()

@st.cache_data(ttl=30)
def get_trade_history(days=30):
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT timestamp,action,price,amount,model_confidence,pnl FROM trade_history WHERE timestamp>=:s ORDER BY timestamp DESC"),{"s":datetime.utcnow()-timedelta(days=days)}).fetchall()
    if not rows:
        return pd.DataFrame(columns=["timestamp","close_price"])
    df = pd.DataFrame(rows,columns=["timestamp","action","price","amount","confidence","pnl"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

SENSE_LABELS = {"eye":"👁 眼","ear":"👂 耳","nose":"👃 鼻","tongue":"👅 舌","body":"🏃 身","pulse":"💓 脈","aura":"🌌 氣","mind":"🧠 心"}
SENSE_COLORS = {"eye":"#00b0ff","ear":"#69ff47","nose":"#ff6d00","tongue":"#e040fb","body":"#ffea00","pulse":"#ff1744","aura":"#00e5ff","mind":"#b2ff59"}

# ── HERO ROW ──────────────────────────────────────────
market_row = get_latest_market()
confidence, signal = get_confidence()
fng_val, fng_label = get_fng()

btc_price = round(float(market_row[1]),2) if market_row else 0
funding_bps = float(market_row[3])*10000 if market_row and market_row[3] else 0
conf_pct = round(confidence*100,1) if confidence else 50

sig_color = "#00e676" if signal=="BUY" else ("#ff1744" if signal=="SELL" else "#ffea00")
fr_color = "#ff1744" if funding_bps < 0 else "#00e676"
fng_color = "#ff1744" if fng_val and fng_val<30 else ("#00e676" if fng_val and fng_val>70 else "#ffea00")
conf_color = "#00e676" if conf_pct>=65 else ("#ff1744" if conf_pct<=35 else "#ffea00")

c1,c2,c3,c4,c5 = st.columns([2,2,2,2,2])
with c1:
    st.markdown(f"""<div class="hero-card"><div class="kpi-label">交易信號</div>
        <div class="kpi-value" style="color:{sig_color};font-size:2rem">{signal}</div></div>""",unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="hero-card"><div class="kpi-label">校準信心</div>
        <div class="kpi-value" style="color:{conf_color}">{conf_pct}%</div>
        <div class="conf-bar-bg"><div style="width:{conf_pct}%;background:{conf_color};height:8px;border-radius:4px"></div></div></div>""",unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="hero-card"><div class="kpi-label">BTC 價格</div>
        <div class="kpi-value" style="color:#fff">${btc_price:,.0f}</div></div>""",unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="hero-card"><div class="kpi-label">資金費率</div>
        <div class="kpi-value" style="color:{fr_color}">{funding_bps:+.2f} bps</div></div>""",unsafe_allow_html=True)
with c5:
    st.markdown(f"""<div class="hero-card"><div class="kpi-label">恐懼貪婪</div>
        <div class="kpi-value" style="color:{fng_color}">{fng_val if fng_val else "--"}</div>
        <div style="color:#888;font-size:.75rem">{fng_label}</div></div>""",unsafe_allow_html=True)

st.markdown("---")

# ── TABS ──────────────────────────────────────────────
tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8 = st.tabs([
    "📡 信號儀表板","🔬 五感分析","📈 策略回測","🔧 參數優化","🔄 Walk-Forward","📜 交易歷史","🧬 特徵有效性","🧪 Web CLI"
])

# ── TAB1: 信號儀表板
with tab1:
    col_price, col_sense = st.columns([3,2])
    with col_price:
        st.subheader("BTC 價格")
        price_df = get_price_history(days=7)
        if not price_df.empty:
            trend_color = "#00e676" if price_df["close_price"].iloc[-1]>=price_df["close_price"].iloc[0] else "#ff1744"
            fig_p = go.Figure(go.Scatter(x=price_df["timestamp"],y=price_df["close_price"],mode="lines",
                line=dict(color=trend_color,width=1.5)))
            fig_p.update_layout(plot_bgcolor="#0d0d0d",paper_bgcolor="#0d0d0d",font_color="#e0e0e0",height=300,
                xaxis=dict(gridcolor="#2a2a2a"),yaxis=dict(gridcolor="#2a2a2a"),margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_p,use_container_width=True)
        else:
            st.info("無價格數據")
    with col_sense:
        st.subheader("八特徵即時")
        sd = get_sense_history(hours=1)
        if not sd.empty:
            latest = sd.iloc[-1]
            for key,label in SENSE_LABELS.items():
                val = latest.get(key)
                if val is None or (isinstance(val,float) and np.isnan(float(val))):
                    c,b = "#555",50
                else:
                    norm = min(max((float(val)+1)/2,0),1)
                    b = int(norm*100)
                    c = "#00e676" if norm>0.6 else ("#ff1744" if norm<0.4 else "#ffea00")
                val_str = f"{float(val):.4f}" if val is not None else "N/A"
                st.markdown(f"""<div style="margin-bottom:6px">
                    <div style="display:flex;justify-content:space-between;font-size:.8rem">
                        <span>{label}</span><span style="color:{c}">{val_str}</span></div>
                    <div style="background:#1e1e1e;border-radius:3px;height:5px">
                        <div style="width:{b}%;background:{c};height:5px;border-radius:3px"></div></div>
                </div>""",unsafe_allow_html=True)
        else:
            st.warning("目前沒有可畫的特徵資料；通常是資料窗還沒累積，或新的欄位尚未補齊。")

    st.subheader("價格 × 多特徵走勢")
    ov = get_price_sense_overlay(days=7)
    if not ov.empty and ov[[c for c in ["eye","ear","nose","tongue","body","pulse","aura","mind"] if c in ov.columns]].notna().any().any():
        fig_ov = go.Figure()
        fig_ov.add_trace(go.Scatter(x=ov["timestamp"], y=ov["close_price"], mode="lines", name="BTC 價格", line=dict(color="#ffffff", width=2)))
        pmin = float(ov["close_price"].min())
        pmax = float(ov["close_price"].max())
        pr = max(pmax - pmin, 1e-9)
        for key in ["eye", "ear", "nose", "tongue", "body", "pulse", "aura", "mind"]:
            if key in ov.columns and ov[key].notna().any():
                series = pd.to_numeric(ov[key], errors="coerce")
                if series.notna().sum() == 0:
                    continue
                smin = float(series.min())
                smax = float(series.max())
                sr = max(smax - smin, 1e-9)
                scaled = pmin + ((series - smin) / sr) * pr
                fig_ov.add_trace(go.Scatter(x=ov["timestamp"], y=scaled, mode="lines", name=key, line=dict(width=1.2, color=SENSE_COLORS.get(key, "#aaa")), opacity=0.75))
        fig_ov.update_layout(title="價格 × 多特徵走勢（nearest-match 對齊）", plot_bgcolor="#0d0d0d", paper_bgcolor="#0d0d0d", font_color="#e0e0e0", height=420, xaxis=dict(gridcolor="#2a2a2a"), yaxis=dict(gridcolor="#2a2a2a"), hovermode="x unified", legend=dict(bgcolor="#161616", bordercolor="#2a2a2a", borderwidth=1))
        st.plotly_chart(fig_ov, use_container_width=True)
    else:
        st.info("價格 × 多特徵走勢暫時沒有可對齊的資料：請先累積更多同時間窗樣本，或檢查新舊特徵是否都有寫入。")

# ── TAB2: 五感分析
with tab2:
    hrs = st.slider("顯示小時數",1,168,24,key="t2h")
    sdf = get_sense_history(hours=hrs)
    if not sdf.empty:
        fig2 = go.Figure()
        for col_n,label in SENSE_LABELS.items():
            if col_n in sdf.columns:
                fig2.add_trace(go.Scatter(x=sdf["ts"],y=sdf[col_n],mode="lines",name=label,line=dict(width=1,color=SENSE_COLORS.get(col_n,"#aaa"))))
        fig2.update_layout(plot_bgcolor="#0d0d0d",paper_bgcolor="#0d0d0d",font_color="#e0e0e0",height=400,
            xaxis=dict(gridcolor="#2a2a2a"),yaxis=dict(gridcolor="#2a2a2a"),hovermode="x unified",
            legend=dict(bgcolor="#161616",bordercolor="#2a2a2a",borderwidth=1))
        st.plotly_chart(fig2,use_container_width=True)
        sc = [c for c in SENSE_LABELS if c in sdf.columns]
        corr = sdf[sc].corr()
        fig_c = px.imshow(corr,text_auto=".2f",aspect="auto",color_continuous_scale="RdBu_r",range_color=[-1,1])
        fig_c.update_layout(paper_bgcolor="#0d0d0d",font_color="#e0e0e0",height=350,title="相關性矩陣")
        st.plotly_chart(fig_c,use_container_width=True)
    else:
        st.warning("目前沒有可畫的特徵資料；通常是資料窗還沒累積，或新的欄位尚未補齊。")

# ── TAB3: 策略回測
with tab3:
    ca,cb,cc,cd = st.columns(4)
    with ca: sd3 = st.date_input("開始",datetime.utcnow()-timedelta(days=30),key="t3s")
    with cb: ed3 = st.date_input("結束",datetime.utcnow(),key="t3e")
    with cc: ic3 = st.number_input("初始資金",1000.0,1e6,10000.0,key="t3ic")
    with cd: cr3 = st.slider("手續費 %%",0.0,0.5,0.1,step=0.05,key="t3cr")

    if st.button("執行回測",type="primary",use_container_width=True,key="bt3"):
        with st.spinner("回測中..."):
            try:
                from backtesting.engine import run_backtest
                from backtesting.metrics import calculate_metrics
                from sqlalchemy.orm import sessionmaker as SM3
                from sqlalchemy import create_engine as CE3
                _e3 = CE3(cfg["database"]["url"])
                _s3 = SM3(bind=_e3)()
                res = run_backtest(session=_s3,
                    start_date=datetime.combine(sd3,datetime.min.time()),
                    end_date=datetime.combine(ed3,datetime.max.time()),
                    initial_capital=ic3, commission_rate=cr3/100,
                    symbol=cfg["trading"]["symbol"])
                _s3.close()
                if res is None:
                    st.error("回測引擎沒有回傳結果；請先確認資料窗、symbol 與時間範圍。")
                elif res.get("equity_curve") is not None and not res["equity_curve"].empty:
                    eq_df = res["equity_curve"]
                    eq = eq_df["equity"]
                    mx = calculate_metrics(eq,res["trade_log"],benchmark_return=res.get("buy_hold_return",0),freq_minutes=5)
                    tr = mx["total_return"]; bh = res.get("buy_hold_return",0)/100; alpha = tr-bh
                    cost = res.get("total_trading_cost",0)
                    k1,k2,k3,k4,k5,k6 = st.columns(6)
                    k1.metric("總回報",f"{tr:.2%}",delta=f"B&H {bh:.2%}")
                    k2.metric("Alpha",f"{alpha:.2%}")
                    k3.metric("夏普",f"{mx['sharpe_ratio']:.2f}")
                    k4.metric("索提諾",f"{mx.get('sortino_ratio',0):.2f}")
                    k5.metric("最大回撤",f"{mx['max_drawdown']:.2%}")
                    k6.metric("交易成本",f"-${cost:.0f}")
                    k7,k8,k9,k10,k11,k12 = st.columns(6)
                    k7.metric("賣出勝率",f"{mx.get('sell_win_rate', mx.get('win_rate',0)):.1%}")
                    k8.metric("盈虧比",f"{mx.get('profit_factor',0):.2f}")
                    k9.metric("交易次數",int(mx.get("total_trades",0)))
                    k10.metric("W/L/D",f"{mx.get('n_wins',0)}/{mx.get('n_losses',0)}/{mx.get('n_draws',0)}")
                    k11.metric("連虧最長",int(mx.get("max_consecutive_losses",0)))
                    k12.metric("卡爾瑪",f"{mx.get('calmar_ratio',0):.2f}")
                    fig_eq = go.Figure()
                    rc = "#00e676" if tr>=0 else "#ff1744"
                    fig_eq.add_trace(go.Scatter(x=eq_df.index,y=eq,mode="lines",name="策略",line=dict(color=rc,width=2)))
                    bh_c = res.get("buy_hold_curve")
                    if bh_c is not None and not bh_c.empty:
                        fig_eq.add_trace(go.Scatter(x=bh_c.index,y=bh_c,mode="lines",name="Buy & Hold",line=dict(color="#555",width=1.5,dash="dash")))
                    fig_eq.update_layout(title="資金曲線 vs Buy & Hold",plot_bgcolor="#0d0d0d",paper_bgcolor="#0d0d0d",
                        font_color="#e0e0e0",height=350,xaxis=dict(gridcolor="#2a2a2a"),yaxis=dict(gridcolor="#2a2a2a"),
                        legend=dict(bgcolor="#161616"),hovermode="x unified")
                    st.plotly_chart(fig_eq,use_container_width=True)
                    st.caption(f"權益曲線點數：{len(eq_df)}，最後權益：{float(eq.iloc[-1]):.2f}")
                    tl = res["trade_log"]
                    if not tl.empty:
                        sc3 = [c for c in ["timestamp","action","price","amount","confidence","pnl","gross_pnl","commission_slippage","reason"] if c in tl.columns]
                        st.dataframe(tl[sc3],use_container_width=True,height=280)
                else:
                    st.error("回測無權益曲線：通常是資料窗不足、symbol 不匹配，或時間範圍內沒有可交易樣本。")
            except Exception as e:
                st.exception(e)
    else:
        st.caption("設定後點擊執行。")

# ── TAB4: 參數優化
with tab4:
    st.caption("搜索最佳 confidence / position / stop-loss 以 Sharpe 排序")
    p1,p2,p3 = st.columns(3)
    with p1: cr4 = st.slider("Conf 範圍",0.5,0.9,(0.6,0.8),step=0.05,key="t4cr")
    with p2: pr4 = st.slider("部位範圍",0.01,0.1,(0.02,0.06),step=0.01,key="t4pr")
    with p3: sr4 = st.slider("止損範圍",0.01,0.1,(0.02,0.05),step=0.01,key="t4sr")
    p4,p5,p6 = st.columns(3)
    with p4: cs4 = st.number_input("Conf steps",2,8,3,key="cs4a")
    with p5: ps4 = st.number_input("Pos steps",2,8,3,key="ps4a")
    with p6: ss4 = st.number_input("Stop steps",2,8,2,key="ss4a")
    if st.button("開始優化",type="primary",use_container_width=True,key="bt4"):
        with st.spinner("網格搜索..."):
            try:
                from backtesting.optimizer import grid_search
                from sqlalchemy.orm import sessionmaker as SM4
                from sqlalchemy import create_engine as CE4
                _e4 = CE4(cfg["database"]["url"]); _s4 = SM4(bind=_e4)()
                def _ls(lo,hi,n): return [round(lo+i*(hi-lo)/(n-1),4) for i in range(int(n))]
                rdf = grid_search(session=_s4,
                    confidence_thresholds=_ls(*cr4,cs4),max_position_ratios=_ls(*pr4,ps4),stop_loss_pcts=_ls(*sr4,ss4),
                    start_date=datetime.utcnow()-timedelta(days=30),end_date=datetime.utcnow(),initial_capital=10000.0,symbol=cfg["trading"]["symbol"])
                _s4.close()
                if not rdf.empty:
                    best = rdf.loc[rdf["sharpe_ratio"].idxmax()]
                    st.success(f"最佳 Sharpe {best['sharpe_ratio']:.2f} — conf={best['confidence_threshold']} pos={best['max_position_ratio']} stop={best['stop_loss_pct']}")
                    st.dataframe(rdf.sort_values("sharpe_ratio",ascending=False),use_container_width=True,height=300)
                    med = rdf["stop_loss_pct"].median()
                    piv = rdf[rdf["stop_loss_pct"]==med].pivot_table(index="confidence_threshold",columns="max_position_ratio",values="sharpe_ratio")
                    fig_h = px.imshow(piv,text_auto=".2f",aspect="auto",color_continuous_scale="RdYlGn",title=f"Sharpe 熱圖 (stop={med:.3f})")
                    fig_h.update_layout(paper_bgcolor="#0d0d0d",font_color="#e0e0e0")
                    st.plotly_chart(fig_h,use_container_width=True)
                else:
                    st.error("無結果，數據不足。")
            except Exception as e: st.exception(e)
    else: st.caption("設定後點擊執行。")

# ── TAB5: Walk-Forward
with tab5:
    st.caption("滑動窗口驗證，判斷參數是否穩健 (STABLE / UNSTABLE)")
    w1,w2,w3 = st.columns(3)
    with w1: wf_tr = st.slider("訓練窗口(天)",10,90,30,key="wtr")
    with w2: wf_te = st.slider("測試窗口(天)",5,30,10,key="wte")
    with w3: wf_n = st.slider("滑動次數",3,10,5,key="wfn")
    w4,w5,w6 = st.columns(3)
    with w4: wf_c = st.slider("Confidence",0.5,0.9,0.7,key="wfc")
    with w5: wf_p = st.slider("部位比例",0.01,0.1,0.05,key="wfp")
    with w6: wf_s = st.slider("止損",0.01,0.1,0.03,key="wfs")
    if st.button("執行 Walk-Forward",type="primary",use_container_width=True,key="bwf"):
        with st.spinner(f"執行 {wf_n} 個窗口..."):
            try:
                from backtesting.walkforward import run_walk_forward
                from sqlalchemy.orm import sessionmaker as SM5
                from sqlalchemy import create_engine as CE5
                _e5 = CE5(cfg["database"]["url"]); _s5 = SM5(bind=_e5)()
                wfr = run_walk_forward(_s5,{"confidence_threshold":wf_c,"max_position_ratio":wf_p,"stop_loss_pct":wf_s},train_days=wf_tr,test_days=wf_te,n_windows=wf_n)
                _s5.close()
                sm = wfr.get("summary",{})
                vd = sm.get("verdict","N/A"); sc = sm.get("stability_score",0)
                if vd=="STABLE": st.success(f"✅ {vd} — 穩健性 {sc:.0%}")
                else: st.warning(f"⚠️ {vd} — 穩健性 {sc:.0%}")
                wc1,wc2,wc3,wc4 = st.columns(4)
                wc1.metric("平均OOS回報",f"{sm.get('avg_oos_return',0):.2%}")
                wc2.metric("平均Sharpe",f"{sm.get('avg_sharpe',0):.2f}")
                wc3.metric("獲利窗口",f"{sm.get('pct_profitable_windows',0):.0%}")
                wc4.metric("打贏B&H",f"{sm.get('pct_beat_bh',0):.0%}")
                wd = pd.DataFrame(wfr.get("windows",[]))
                if not wd.empty:
                    st.dataframe(wd,use_container_width=True)
                    bc = ["#00e676" if v>0 else "#ff1744" for v in wd.get("total_return",[])]
                    fg = go.Figure(go.Bar(x=[f"W{r}" for r in wd.get("window",range(len(wd)))],y=[v*100 for v in wd.get("total_return",[])],marker_color=bc))
                    fg.add_hline(y=0,line_dash="dash",line_color="#888")
                    fg.update_layout(title="各窗口OOS回報(%%)",plot_bgcolor="#0d0d0d",paper_bgcolor="#0d0d0d",font_color="#e0e0e0",height=260,xaxis=dict(gridcolor="#2a2a2a"),yaxis=dict(gridcolor="#2a2a2a"))
                    st.plotly_chart(fg,use_container_width=True)
            except Exception as e: st.exception(e)
    else: st.caption("設定後執行。建議先在 Tab4 找最佳參數。")

# ── TAB6: 交易歷史
with tab6:
    d6 = st.slider("顯示天數",1,90,30,key="t6d")
    trd = get_trade_history(days=d6)
    if not trd.empty:
        tpnl = trd["pnl"].sum() if "pnl" in trd.columns else 0
        nt = len(trd); nw = len(trd[trd["pnl"]>0]) if "pnl" in trd.columns else 0
        tc1,tc2,tc3 = st.columns(3)
        tc1.metric("累計P&L",f"{tpnl:.2f} USDT",delta=f"勝率 {nw/nt:.0%}" if nt else "0%")
        tc2.metric("交易次數",nt); tc3.metric("獲利筆數",nw)
        fig_pl = go.Figure(go.Scatter(x=trd.sort_values("timestamp")["timestamp"],y=trd.sort_values("timestamp")["pnl"].cumsum(),mode="lines",fill="tozeroy",
            line=dict(color="#00e676" if tpnl>=0 else "#ff1744"),fillcolor="rgba(0,230,118,.1)" if tpnl>=0 else "rgba(255,23,68,.1)"))
        fig_pl.update_layout(title="累計P&L",plot_bgcolor="#0d0d0d",paper_bgcolor="#0d0d0d",font_color="#e0e0e0",height=240,xaxis=dict(gridcolor="#2a2a2a"),yaxis=dict(gridcolor="#2a2a2a"))
        st.plotly_chart(fig_pl,use_container_width=True)
        st.dataframe(trd,use_container_width=True,height=280)
    else:
        st.info("無交易記錄")

# ── TAB7: 特徵有效性
with tab7:
    try:
        from sqlalchemy.orm import sessionmaker as SM7
        from sqlalchemy import create_engine as CE7
        from analysis.sense_effectiveness import compute_information_coefficient, compute_win_rate_by_feature_quantile
        _e7 = CE7(cfg["database"]["url"]); _s7 = SM7(bind=_e7)()
        ic = compute_information_coefficient(_s7,cfg["trading"]["symbol"],horizon_hours=24)
        if ic:
            ic_df = pd.DataFrame(list(ic.items()),columns=["Feature","IC"])
            ic_df["color"] = ic_df["IC"].apply(lambda v:"#00e676" if abs(v)>=0.05 else "#ff1744")
            fi = go.Figure(go.Bar(x=ic_df["Feature"],y=ic_df["IC"],marker_color=ic_df["color"]))
            fi.add_hline(y=0.05,line_dash="dash",line_color="#888",annotation_text="0.05")
            fi.add_hline(y=-0.05,line_dash="dash",line_color="#888")
            fi.update_layout(title="IC 特徵有效性",plot_bgcolor="#0d0d0d",paper_bgcolor="#0d0d0d",font_color="#e0e0e0",height=300,xaxis=dict(gridcolor="#2a2a2a"),yaxis=dict(gridcolor="#2a2a2a"))
            st.plotly_chart(fi,use_container_width=True)
        qdf = compute_win_rate_by_feature_quantile(_s7,cfg["trading"]["symbol"],horizon_hours=24,n_quantiles=5)
        if not qdf.empty:
            piv = qdf.pivot_table(index="quantile",columns="feature",values="win_rate")
            fq = px.imshow(piv,text_auto=".1%%",aspect="auto",color_continuous_scale="RdYlGn",range_color=[0,1],title="分位數勝率熱圖")
            fq.update_layout(paper_bgcolor="#0d0d0d",font_color="#e0e0e0",height=300)
            st.plotly_chart(fq,use_container_width=True)
        _s7.close()
    except Exception as e:
        st.error(f"分析失敗: {e}")


# ── TAB8: Web CLI / API control ───────────────────────
with tab8:
    st.subheader("Web CLI 參數控制")
    st.caption("把 CLI 參數同步到 Web：單次回測 / 網格搜索 / Walk-Forward")

    c1, c2, c3 = st.columns(3)
    with c1:
        days = st.slider("回測天數", 1, 365, 30, key="web_days")
        confidence_threshold = st.slider("confidence_threshold", 0.0, 1.0, 0.55, 0.01, key="web_conf")
    with c2:
        max_position_ratio = st.slider("max_position_ratio", 0.0, 1.0, 0.05, 0.01, key="web_pos")
        stop_loss_pct = st.slider("stop_loss_pct", 0.0, 1.0, 0.02, 0.01, key="web_stop")
    with c3:
        mode = st.selectbox("模式", ["single", "grid", "walkforward"], key="web_mode")
        n_windows = st.number_input("n_windows", 1, 20, 5, key="web_nw")

    if st.button("執行 Web 回測", type="primary", use_container_width=True):
        import requests
        params = {
            "days": days,
            "confidence_threshold": confidence_threshold,
            "max_position_ratio": max_position_ratio,
            "stop_loss_pct": stop_loss_pct,
            "test_days": 10,
            "train_days": 30,
            "n_windows": int(n_windows),
            "mode": mode,
        }
        try:
            resp = requests.get(f"{API_BASE}/backtest", params=params, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            st.json(data)
        except Exception as e:
            st.error(f"Web 回測失敗: {e}")

    if st.button("刷新特徵與模型統計", use_container_width=True):
        import requests
        try:
            senses = requests.get(f"{API_BASE}/senses", timeout=30).json()
            stats = requests.get(f"{API_BASE}/model/stats", timeout=30).json()
            st.write("### Feature Scores")
            st.json(senses)
            st.write("### Model Stats")
            st.json(stats)
        except Exception as e:
            st.error(f"刷新失敗: {e}")
