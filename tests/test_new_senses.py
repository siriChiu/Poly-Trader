import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

print("=== Tongue v3 ===")
from data_ingestion.tongue_sentiment import get_tongue_feature
t = get_tongue_feature()
print(f"  score={t['feat_tongue_sentiment']:.4f}, label={t['tongue_label']}")
print(f"  FNG={t['fear_greed_index']}, vol={t['volatility']}, FR={t['funding_rate']}")

print("\n=== Body v4 ===")
from data_ingestion.body_liquidation import get_body_feature
b = get_body_feature()
print(f"  score={b['feat_body_trend']:.4f}, label={b['body_label']}")
print(f"  OI_ROC={b['oi_roc']}, FR={b['funding_rate']}")
