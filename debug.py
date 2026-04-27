import sys  
sys.path.insert(0, r'C:\Users\Kazuha\repo\Poly-Trader')  
from data_ingestion.collector import run_collection_and_save  
from database.models import init_db  
SessionLocal = init_db('sqlite:///database/poly_trader.db')  
session = SessionLocal()  
success = run_collection_and_save(session)  
print('Success:', success)  
session.close() 
