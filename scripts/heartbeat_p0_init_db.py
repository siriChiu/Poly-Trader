"""P0 Fix: Initialize databases and collect fresh data. DBs are 0 bytes."""
import sys
import os

# Add project root to path
ROOT = '/home/kazuha/Poly-Trader'
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from database.models import init_db

# Initialize poly_trader.db (the primary DB)
db_path = os.path.join(ROOT, 'data', 'poly_trader.db')
db_url = f"sqlite:///{db_path}"

print(f"Initializing DB: {db_path}")
session = init_db(db_url)
print(f"DB initialized successfully")
print(f"DB file size: {os.path.getsize(db_path)} bytes")

# Try to collect fresh data
try:
    from data_ingestion.collector import run_collection_and_save
    print("\nAttempting data collection...")
    success = run_collection_and_save(session)
    if success:
        from sqlalchemy import text
        count = session.execute(text("SELECT COUNT(*) FROM raw_market_data")).fetchone()[0]
        print(f"Collection successful! {count} raw records saved")
    else:
        print("Collection failed - checking which senses failed")
        # Try individual senses
        try:
            from data_ingestion.eye_okx import get_eye_feature
            eye = get_eye_feature()
            print(f"  Eye: price={eye.get('current_price') if eye else 'FAILED'}")
        except Exception as e:
            print(f"  Eye: ERROR - {e}")
        
        try:
            from data_ingestion.nose_futures import get_nose_feature
            nose = get_nose_feature()
            print(f"  Nose: {nose}")
        except Exception as e:
            print(f"  Nose: ERROR - {e}")
            
        try:
            from data_ingestion.macro_data import fetch_vix_dxy_latest
            macro = fetch_vix_dxy_latest()
            print(f"  Macro VIX/DXY: {macro}")
        except Exception as e:
            print(f"  Macro: ERROR - {e}")
                
except Exception as e:
    print(f"Collection setup error: {e}")
    import traceback
    traceback.print_exc()

session.close()
print("\n=== DB initialization complete ===")
