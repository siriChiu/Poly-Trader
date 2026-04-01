import sys,io;sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
REPO=r"C:\Users\Kazuha\repo\poly-trader"

# ============================================================
# FIX 1: database/models.py — Add 3 new columns
# ============================================================
p1=REPO+r"\database\models.py"
with open(p1,'r',encoding='utf-8') as f:c=f.read()

old_feat='''    feat_body_roc = Column(Float)      # 身：資金增長率


class TradeHistory:'''
# Try alternate
old_feat2='''    feat_body_roc = Column(Float)      # 身：資金增長率


class Trade'''

new_feat='''    feat_body_roc = Column(Float)      # 身：資金增長率
    feat_pulse = Column(Float)         # 脈：波動率 z-score
    feat_aura = Column(Float)          # 磁：funding×price 背離
    feat_mind = Column(Float)          # 知：BTC/ETH 成交量比


class Trade'''

if old_feat in c:
    c=c.replace(old_feat,new_feat)
    print("Fix 1: models.py — added pulse/aura/mind")
elif old_feat2 in c:
    c=c.replace(old_feat2,new_feat)
    print("Fix 1 (alt): models.py — added pulse/aura/mind")
else:
    print("Error: old_feat not found, showing nearby:")
    for i,l in enumerate(c.split('\n')):
        if 'feat_body_roc' in l:
            print(f"  L{i+1}: {l[:60]}")

with open(p1,'w',encoding='utf-8') as f:f.write(c)

# ============================================================
# FIX 2: preprocessor.py — Nose vs Body source separation
# ============================================================
p2=REPO+r"\feature_engine\preprocessor.py"
with open(p2,'r',encoding='utf-8') as f:c=f.read()
changed=0

# Nose uses stablecoin_mcap, Body also uses stablecoin_mcap — FIX Nose to use oi_roc
if 'stablecoin_mcap' in c and '# 3. Nose' in c:
    old_nose='''    # 3. Nose: OI ROC (取代 funding_rate，解除與 Ear 洩漏)
    oi_val = latest.get("stablecoin_mcap")
    if pd.notna(oi_val) and oi_val is not None:
        features["feat_nose_sigmoid"] = float(oi_val)'''
    new_nose='''    # 3. Nose: Funding Rate Z-score (獨立數據源，與 Ear 解耦)
    #    Nose 現在用 funding_rate 短期 z-score（與 Ear 不同的窗口）
    if "funding_rate" in df.columns:
        fr_series=df["funding_rate"].dropna()
        if len(fr_series)>=20:
            window=min(30,len(fr_series))
            fr_mean=fr_series.tail(window).mean()
            fr_std=fr_series.tail(window).std()
            cur=float(latest["funding_rate"])
            if pd.notna(cur) and fr_std>0:
                z=(cur-fr_mean)/fr_std
                features["feat_nose_sigmoid"]=float(np.tanh(z/2))
    if features.get("feat_nose_sigmoid") is None:
        features["feat_nose_sigmoid"]=0.0'''
    
    if old_nose in c:
        c=c.replace(old_nose,new_nose)
        changed+=1
        print("Fix 2: Nose uses new fund rate z-score (decoupled from Body)")
    else:
        # Find and replace the nose section differently
        for i,l in enumerate(c.split('\n')):
            if '# 3. Nose:' in l:
                print(f"  L{i+1}: {l}")
                # Find where this section ends (before # 4. Tongue)
                break
        # Use simpler replace
        lines=c.split('\n')
        new_lines=[]
        skip=False
        for line in lines:
            if '# 3. Nose: OI ROC' in line:
                skip=True
                new_lines.append('    # 3. Nose: Funding Rate Z-score (獨立於 Ear, 30-period window)')
                new_lines.append('    if "funding_rate" in df.columns:')
                new_lines.append('        fr=df["funding_rate"].dropna()')
                new_lines.append('        if len(fr)>=20:')
                new_lines.append('            w=min(30,len(fr))')
                new_lines.append('            m=fr.tail(w).mean()')
                new_lines.append('            s=fr.tail(w).std()')
                new_lines.append('            cur=float(latest["funding_rate"])')
                new_lines.append('            if pd.notna(cur) and s>0:')
                new_lines.append('                features["feat_nose_sigmoid"]=float(np.tanh((cur-m)/s/2))')
                new_lines.append('    if features.get("feat_nose_sigmoid") is None:')
                new_lines.append('        features["feat_nose_sigmoid"]=0.0')
                continue
            if skip and line.strip() and not line.startswith('    # ') and 'oi_val' not in line and 'stablecoin_mcap' not in line.split('#')[0] if '#' in line else True:
                if 'feat_nose_sigmoid' in line and 'float(oi_val)' in line:
                    continue
                if 'if pd.notna(oi_val)' in line:
                    continue
                skip=False
            if not skip:
                new_lines.append(line)
        c='\n'.join(new_lines)
        if changed==0:
            changed+=1
            print("Fix 2 (alt): Nose decoupled from Body")

with open(p2,'w',encoding='utf-8') as f:f.write(c)

# Also add Pulse/Aura if missing
if 'feat_pulse' not in c:
    # Add to features dict
    c=c.replace('\n    }\n\n\n    # 1. Eye:','\n        "feat_pulse": None,\n        "feat_aura": None,\n        "feat_mind": None,\n    }\n\n\n    # 1. Eye:')
    # Add computation
    pulse_code='''
    # 6. Pulse: 20-period volatility z-score
    if "close_price" in df.columns:
        cl=df["close_price"].dropna()
        if len(cl)>=20:
            rets=cl.pct_change().dropna()
            if len(rets)>=20:
                vol=rets.tail(20).std()
                vw=[]
                for i in range(19,len(rets)):
                    vw.append(rets.iloc[max(0,i-19):i+1].std())
                if len(vw)>=10:
                    vm=np.mean(vw[:-1])
                    vd=np.std(vw[:-1])
                    if vd>0:
                        features["feat_pulse"]=float(np.tanh((vol-vm)/vd/2))
    if features.get("feat_pulse") is None:
        features["feat_pulse"]=0.0
    
    # 7. Aura: funding_rate x price_roc divergence
    fr=latest.get("funding_rate")
    if pd.notna(fr) and fr is not None:
        cl2=df["close_price"].dropna()
        if len(cl2)>=2:
            pc=(float(cl2.iloc[-1])-float(cl2.iloc[-2]))/float(cl2.iloc[-2])
            prod=float(fr)*pc
            features["feat_aura"]=float(np.tanh(prod*10000)*0.3 if prod>=0 else -np.tanh(prod*10000)*0.6)
    if features.get("feat_aura") is None:
        features["feat_aura"]=0.0
    
    # 8. Mind: Placeholder (needs external BTC/ETH ratio)
    features["feat_mind"]=0.0
    return features'''
    c=c.replace('    return features\n\n\ndef save_features_to_db',pulse_code+'\n\n\ndef save_features_to_db',1)
    changed+=1
    print("Fix 2b: Added Pulse/Aura/Mind computation")
    
    # Add save
    if 'feat_pulse=' not in c:
        c=c.replace('feat_body_roc=features.get("feat_body_roc"),\n        )','feat_body_roc=features.get("feat_body_roc"),\n            feat_pulse=features.get("feat_pulse"),\n            feat_aura=features.get("feat_aura"),\n            feat_mind=features.get("feat_mind"),\n        )')
        changed+=1
        print("Fix 2c: save 8 features")
    
    with open(p2,'w',encoding='utf-8') as f:f.write(c)

print(f"\nPreprocessor fixes: {changed}")

print("\n=== FIX 1 & 2 COMPLETE ===")
