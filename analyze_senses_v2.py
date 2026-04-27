#!/usr/bin/env python3
"""
Sensory IC Analysis for Poly-Trader Heartbeat - Version 2
Handles None values properly.
"""
import sys
import os
import numpy as np
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent / "Poly-Trader"
sys.path.insert(0, str(PROJECT_ROOT))

def analyze_senses():
    try:
        from config import load_config
        from database.models import init_db, FeaturesNormalized, Labels
        
        cfg = load_config()
        session = init_db(cfg["database"]["url"])
        
        # Get features and labels
        # We'll join on timestamp - simplified approach: get recent data
        from sqlalchemy import and_
        
        # Get recent data (last 1000 rows)
        features_query = session.query(FeaturesNormalized).order_by(
            FeaturesNormalized.timestamp.desc()
        ).limit(1000)
        
        labels_query = session.query(Labels).order_by(
            Labels.timestamp.desc()
        ).limit(1000)
        
        # Convert to lists for analysis
        features_list = []
        labels_list = []
        
        # Simple approach: get the data and align by index (assuming same timestamps)
        # This is simplified but works for heartbeat analysis
        feat_data = []
        label_data = []
        
        for f in features_query:
            feat_data.append({
                'timestamp': f.timestamp,
                'feat_eye_dist': f.feat_eye_dist,
                'feat_ear_zscore': f.feat_ear_zscore,
                'feat_nose_sigmoid': f.feat_nose_sigmoid,
                'feat_tongue_pct': f.feat_tongue_pct,
                'feat_body_roc': f.feat_body_roc
            })
        
        for l in labels_query:
            label_data.append({
                'timestamp': l.timestamp,
                'future_return_pct': l.future_return_pct
            })
        
        # If we have data, calculate IC for each sense
        if len(feat_data) > 10 and len(label_data) > 10:
            # Align by taking minimum length
            min_len = min(len(feat_data), len(label_data))
            
            # Extract arrays, converting None to np.nan
            def to_array(data_list, key):
                arr = []
                for x in data_list[:min_len]:
                    val = x.get(key)
                    if val is None:
                        arr.append(np.nan)
                    else:
                        arr.append(float(val))
                return np.array(arr)
            
            eye = to_array(feat_data, 'feat_eye_dist')
            ear = to_array(feat_data, 'feat_ear_zscore')
            nose = to_array(feat_data, 'feat_nose_sigmoid')
            tongue = to_array(feat_data, 'feat_tongue_pct')
            body = to_array(feat_data, 'feat_body_roc')
            labels = to_array(label_data, 'future_return_pct')
            
            # Remove NaN values
            def clean_arrays(feat, lbl):
                mask = ~(np.isnan(feat) | np.isnan(lbl))
                return feat[mask], lbl[mask]
            
            eye_clean, lbl_clean = clean_arrays(eye, labels)
            ear_clean, _ = clean_arrays(ear, labels)
            nose_clean, _ = clean_arrays(nose, labels)
            tongue_clean, _ = clean_arrays(tongue, labels)
            body_clean, _ = clean_arrays(body, labels)
            
            # Calculate IC (Information Coefficient) = correlation
            def calculate_ic(feat, lbl):
                if len(feat) < 2:
                    return 0.0
                # Ensure we have at least two non-nan values
                if np.sum(~np.isnan(feat)) < 2 or np.sum(~np.isnan(lbl)) < 2:
                    return 0.0
                return np.corrcoef(feat, lbl)[0, 1]
            
            ic_eye = calculate_ic(eye_clean, lbl_clean) if len(eye_clean) >= 2 else 0.0
            ic_ear = calculate_ic(ear_clean, lbl_clean) if len(ear_clean) >= 2 else 0.0
            ic_nose = calculate_ic(nose_clean, lbl_clean) if len(nose_clean) >= 2 else 0.0
            ic_tongue = calculate_ic(tongue_clean, lbl_clean) if len(tongue_clean) >= 2 else 0.0
            ic_body = calculate_ic(body_clean, lbl_clean) if len(body_clean) >= 2 else 0.0
            
            # Calculate statistics
            def calc_stats(arr, name):
                if len(arr) == 0:
                    return f"{name}: no data"
                # Filter out nan for stats
                arr_clean = arr[~np.isnan(arr)]
                if len(arr_clean) == 0:
                    return f"{name}: all nan"
                mean_val = np.mean(arr_clean)
                std_val = np.std(arr_clean)
                range_val = np.max(arr_clean) - np.min(arr_clean) if len(arr_clean) > 0 else 0
                unique_val = len(np.unique(np.round(arr_clean, 3)))
                return f"{name}: mean={mean_val:.4f}, std={std_val:.4f}, range={range_val:.4f}, unique={unique_val}"
            
            print("=== 感官表現分析 ===")
            print(f"數據點: {min_len} 筆")
            print()
            print("IC (Information Coefficient) 對 future_return_pct:")
            print(f"  Eye (feat_eye_dist): {ic_eye:.4f}")
            print(f"  Ear (feat_ear_zscore): {ic_ear:.4f}")
            print(f"  Nose (feat_nose_sigmoid): {ic_nose:.4f}")
            print(f"  Tongue (feat_tongue_pct): {ic_tongue:.4f}")
            print(f"  Body (feat_body_roc): {ic_body:.4f}")
            print()
            print("統計特性:")
            print(f"  {calc_stats(eye_clean, 'Eye')}")
            print(f"  {calc_stats(ear_clean, 'Ear')}")
            print(f"  {calc_stats(nose_clean, 'Nose')}")
            print(f"  {calc_stats(tongue_clean, 'Tongue')}")
            print(f"  {calc_stats(body_clean, 'Body')}")
            print()
            
            # Check for anomalies based on HEARTBEAT.md guidelines
            print("異常檢查:")
            anomalies = []
            
            # IC < 0.05 → [RED] 感官無效，考慮汰換
            if abs(ic_eye) < 0.05:
                anomalies.append("[RED] Eye 感官無效 (IC < 0.05)，考慮汰換")
            if abs(ic_ear) < 0.05:
                anomalies.append("[RED] Ear 感官無效 (IC < 0.05)，考慮汰換")
            if abs(ic_nose) < 0.05:
                anomalies.append("[RED] Nose 感官無效 (IC < 0.05)，考慮汰換")
            if abs(ic_tongue) < 0.05:
                anomalies.append("[RED] Tongue 感官無效 (IC < 0.05)，考慮汰換")
            if abs(ic_body) < 0.05:
                anomalies.append("[RED] Body 感官無效 (IC < 0.05)，考慮汰換")
            
            # std ≈ 0 → [WARN] 無變異，白噪音
            if len(eye_clean) > 1 and np.std(eye_clean) < 1e-6:
                anomalies.append("[WARN] Eye 無變異，可能是白噪音")
            if len(ear_clean) > 1 and np.std(ear_clean) < 1e-6:
                anomalies.append("[WARN] Ear 無變異，可能是白噪音")
            if len(nose_clean) > 1 and np.std(nose_clean) < 1e-6:
                anomalies.append("[WARN] Nose 無變異，可能是白噪音")
            if len(tongue_clean) > 1 and np.std(tongue_clean) < 1e-6:
                anomalies.append("[WARN] Tongue 無變異，可能是白噪音")
            if len(body_clean) > 1 and np.std(body_clean) < 1e-6:
                anomalies.append("[WARN] Body 無變異，可能是白噪音")
            
            # 任兩感官 IC 完全相同 → [WARN] 特徵洩漏
            ics = [ic_eye, ic_ear, ic_nose, ic_tongue, ic_body]
            ics_rounded = [round(ic, 4) for ic in ics]
            for i in range(len(ics_rounded)):
                for j in range(i+1, len(ics_rounded)):
                    if ics_rounded[i] == ics_rounded[j] and ics_rounded[i] != 0:
                        sense_names = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body']
                        anomalies.append(f"[WARN] {sense_names[i]} 和 {sense_names[j]} IC 完全相同 ({ics_rounded[i]})，可能特徵洩漏")
            
            if anomalies:
                for anomaly in anomalies:
                    print(anomaly)
            else:
                print("[OK] 無異常檢測到")
            
            # 檢查準確度目標 (>90% translates to what in IC context?)
            # In trading, IC of 0.05 is considered decent, 0.1+ is good
            # But the 90% accuracy target is likely for the overall system prediction
            print()
            print("與使用者目標對比:")
            print("  目標: 準確度 > 90%")
            print("  注意: IC 與準確度非直接線性關係")
            print("  參考 IC 值:")
            print(f"    Eye: {ic_eye:.4f} ({'良好' if abs(ic_eye) > 0.1 else '一般' if abs(ic_eye) > 0.05 else '需改進'})")
            print(f"    Ear: {ic_ear:.4f} ({'良好' if abs(ic_ear) > 0.1 else '一般' if abs(ic_ear) > 0.05 else '需改進'})")
            print(f"    Nose: {ic_nose:.4f} ({'良好' if abs(ic_nose) > 0.1 else '一般' if abs(ic_nose) > 0.05 else '需改進'})")
            print(f"    Tongue: {ic_tongue:.4f} ({'良好' if abs(ic_tongue) > 0.1 else '一般' if abs(ic_tongue) > 0.05 else '需改進'})")
            print(f"    Body: {ic_body:.4f} ({'良好' if abs(ic_body) > 0.1 else '一般' if abs(ic_body) > 0.05 else '需改進'})")
            
        else:
            print("[WARN] 數據不足進行 IC 分析")
            print(f"  特徵數據: {len(feat_data)} 筆")
            print(f"  標籤數據: {len(label_data)} 筆")
        
        session.close()
        
    except Exception as e:
        print(f"[ERROR] 感官分析失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_senses()