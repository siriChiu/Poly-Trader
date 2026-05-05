"""
Aura 磁場感 — 資金費率與持倉量背離
數據源: OKX futures data (funding_rate, oi_roc 已收集)
同向=趨勢一致, 反向=分歧(磁場拉扯)
"""
import math

def compute_aura(funding_rate, oi_roc):
    if funding_rate is None or oi_roc is None:
        return 0
    product = funding_rate * oi_roc
    if product >= 0:
        return math.tanh(product * 10000) * 0.3
    else:
        return -math.tanh(product * 10000) * 0.6
