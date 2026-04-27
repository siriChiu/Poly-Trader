import sys  
sys.path.insert(0, '.')  
from data_ingestion.collector import run_collection_and_save  
from database.models import init_db  
SessionLocal = init_db('sqlite:///database/poly_trader.db')  
session = SessionLocal()  
print('Session created')  
success = run_collection_and_save(session)  
print('Collection success:', success)  
if success:  
    session.commit()  
    print('Data committed')  
else:  
    print('Collection failed')  
session.close() 
