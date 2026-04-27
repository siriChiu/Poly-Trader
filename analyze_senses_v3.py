#!/usr/bin/env python3
"""
Sensory IC Analysis for Poly-Trader Heartbeat - Version 3
Windows encoding compatible.
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
        features_query = session.query(FeaturesNormalized).order_by(
            FeaturesNormalized.timestamp.desc()
        ).limit(1000)
        
        labels_query = session.query(Labels).order_by(
            Labels.timestamp.desc()
        ).limit(1000)
        
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
        
        if len(feat_data) > 10 and len(label_data) > 10:
            min_len = min(len(feat_data), len(label_data))
            
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
            
            def clean_arrays(feat, lbl):
                mask = ~(np.isnan(feat) | np.isnan(lbl))
                return feat[mask], lbl[mask]
            
            eye_clean, lbl_clean = clean_arrays(eye, labels)
            ear_clean, _ = clean_arrays(ear, labels)
            nose_clean, _ = clean_arrays(nose, labels)
            tongue_clean, _ = clean_arrays(tongue, labels)
            body_clean, _ = clean_arrays(body, labels)
            
            def calculate_ic(feat, lbl):
                if len(feat) < 2:
                    return 0.0
                if np.sum(~np.isnan(feat)) < 2 or np.sum(~np.isnan(lbl)) < 2:
                    return 0.0
                return np.corrcoef(feat, lbl)[0, 1]
            
            ic_eye = calculate_ic(eye_clean, lbl_clean) if len(eye_clean) >= 2 else 0.0
            ic_ear = calculate_ic(ear_clean, lbl_clean) if len(ear_clean) >= 2 else 0.0
            ic_nose = calculate_ic(nose_clean, lbl_clean) if len(nose_clean) >= 2 else 0.0
            ic_tongue = calculate_ic(tongue_clean, lbl_clean) if len(tongue_clean) >= 2 else 0.0
            ic_body = calculate_ic(body_clean, lbl_clean) if len(body_clean) >= 2 else 0.0
            
            def calc_stats(arr, name):
                if len(arr) == 0:
                    return f"{name}: no data"
                arr_clean = arr[~np.isnan(arr)]
                if len(arr_clean) == 0:
                    return f"{name}: all nan"
                mean_val = np.mean(arr_clean)
                std_val = np.std(arr_clean)
                range_val = np.max(arr_clean) - np.min(arr_clean) if len(arr_clean) > 0 else 0
                unique_val = len(np.unique(np.round(arr_clean, 3)))
                return f"{name}: mean={mean_val:.4f}, std={std_val:.4f}, range={range_val:.4f}, unique={unique_val}"
            
            print("=== Sensory Performance Analysis ===")
            print(f"Data points: {min_len} records")
            print()
            print("IC (Information Coefficient) vs future_return_pct:")
            print(f"  Eye (feat_eye_dist): {ic_eye:.4f}")
            print(f"  Ear (feat_ear_zscore): {ic_ear:.4f}")
            print(f"  Nose (feat_nose_sigmoid): {ic_nose:.4f}")
            print(f"  Tongue (feat_tongue_pct): {ic_tongue:.4f}")
            print(f"  Body (feat_body_roc): {ic_body:.4f}")
            print()
            print("Statistical Characteristics:")
            print(f"  {calc_stats(eye_clean, 'Eye')}")
            print(f"  {calc_stats(ear_clean, 'Ear')}")
            print(f"  {calc_stats(nose_clean, 'Nose')}")
            print(f"  {calc_stats(tongue_clean, 'Tongue')}")
            print(f"  {calc_stats(body_clean, 'Body')}")
            print()
            
            # Check for anomalies based on HEARTBEAT.md guidelines (without emojis for Windows compatibility)
            print("Anomaly Check:")
            anomalies = []
            
            # IC < 0.05 -> Sensor ineffective, consider replacement
            if abs(ic_eye) < 0.05:
                anomalies.append("[!] Eye sensor ineffective (IC < 0.05), consider replacement")
            if abs(ic_ear) < 0.05:
                anomalies.append("[!] Ear sensor ineffective (IC < 0.05), consider replacement")
            if abs(ic_nose) < 0.05:
                anomalies.append("[!] Nose sensor ineffective (IC < 0.05), consider replacement")
            if abs(ic_tongue) < 0.05:
                anomalies.append("[!] Tongue sensor ineffective (IC < 0.05), consider replacement")
            if abs(ic_body) < 0.05:
                anomalies.append("[!] Body sensor ineffective (IC < 0.05), consider replacement")
            
            # std ≈ 0 -> No variation, white noise
            if len(eye_clean) > 1 and np.std(eye_clean) < 1e-6:
                anomalies.append("[!] Eye has no variation, possibly white noise")
            if len(ear_clean) > 1 and np.std(ear_clean) < 1e-6:
                anomalies.append("[!] Ear has no variation, possibly white noise")
            if len(nose_clean) > 1 and np.std(nose_clean) < 1e-6:
                anomalies.append("[!] Nose has no variation, possibly white noise")
            if len(tongue_clean) > 1 and np.std(tongue_clean) < 1e-6:
                anomalies.append("[!] Tongue has no variation, possibly white noise")
            if len(body_clean) > 1 and np.std(body_clean) < 1e-6:
                anomalies.append("[!] Body has no variation, possibly white noise")
            
            # Any two sensors have identical IC -> Feature leakage
            ics = [ic_eye, ic_ear, ic_nose, ic_tongue, ic_body]
            ics_rounded = [round(ic, 4) for ic in ics]
            for i in range(len(ics_rounded)):
                for j in range(i+1, len(ics_rounded)):
                    if ics_rounded[i] == ics_rounded[j] and ics_rounded[i] != 0:
                        sense_names = ['Eye', 'Ear', 'Nose', 'Tongue', 'Body']
                        anomalies.append(f"[!] {sense_names[i]} and {sense_names[j]} have identical IC ({ics_rounded[i]}), possible feature leakage")
            
            if anomalies:
                for anomaly in anomalies:
                    print(anomaly)
            else:
                print("[OK] No anomalies detected")
            
            print()
            print("Comparison with User Target:")
            print("  Target: Accuracy > 90%")
            print("  Note: IC and accuracy are not directly linearly related")
            print("  Reference IC values:")
            print(f"    Eye: {ic_eye:.4f} ({'Good' if abs(ic_eye) > 0.1 else 'Fair' if abs(ic_eye) > 0.05 else 'Needs Improvement'})")
            print(f"    Ear: {ic_ear:.4f} ({'Good' if abs(ic_ear) > 0.1 else 'Fair' if abs(ic_ear) > 0.05 else 'Needs Improvement'})")
            print(f"    Nose: {ic_nose:.4f} ({'Good' if abs(ic_nose) > 0.1 else 'Fair' if abs(ic_nose) > 0.05 else 'Needs Improvement'})")
            print(f"    Tongue: {ic_tongue:.4f} ({'Good' if abs(ic_tongue) > 0.1 else 'Fair' if abs(ic_tongue) > 0.05 else 'Needs Improvement'})")
            print(f"    Body: {ic_body:.4f} ({'Good' if abs(ic_body) > 0.1 else 'Fair' if abs(ic_body) > 0.05 else 'Needs Improvement'})")
            
        else:
            print("[WARN] Insufficient data for IC analysis")
            print(f"  Feature data: {len(feat_data)} records")
            print(f"  Label data: {len(label_data)} records")
        
        session.close()
        
    except Exception as e:
        print(f"[ERROR] Sensory analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_senses()