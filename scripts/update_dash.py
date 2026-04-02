
import re
path = r'C:\Users\Kazuha\repo\Poly-Trader\dashboard\app.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace the 4-col metrics display to add more metrics
old_metrics = """                col_m1.metric("總回報", f"{metrics['total_return']:.2%}")
                col_m2.metric("夏普比率", f"{metrics['sharpe_ratio']:.2f}")
                col_m3.metric("最大回撤", f"{metrics['max_drawdown']:.2%}")
                col_m4.metric("交易次數", int(metrics.get('total_trades', 0)))"""

new_metrics = """                st.metric("總回報", f"{metrics['total_return']:.2%}")
                st.metric("年化回報", f"{metrics.get('annual_return', 0):.2%}")
                st.metric("夏普比率", f"{metrics['sharpe_ratio']:.2f}")
                st.metric("索提諾比率", f"{metrics.get('sortino_ratio', 0):.2f}")
                st.metric("最大回撤", f"{metrics['max_drawdown']:.2%}")
                st.metric("卡爾瑪比率", f"{metrics.get('calmar_ratio', 0):.2f}")
                st.metric("勝率", f"{metrics.get('win_rate', 0):.1%}")
                st.metric("盈虧比", f"{metrics.get('profit_factor', 0):.2f}")
                st.metric("交易次數", int(metrics.get('total_trades', 0)))
                st.metric("Win/Loss/Draw", f"{metrics.get('n_wins', 0)}/{metrics.get('n_losses', 0)}/{metrics.get('n_draws', 0)}")
                st.metric("最大連續虧損", int(metrics.get('max_consecutive_losses', 0)))
                cost = results.get("total_trading_cost", 0) if 'results' in dir() else 0
                if cost > 0:
                    st.metric("手續費+滑點", f"-${int(cost)} USDT")"""

if old_metrics in content:
    content = content.replace(old_metrics, new_metrics)
    print("Replaced metrics section")
else:
    print("Warning: old_metrics not found exactly, trying line-by-line")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Dashboard updated")
