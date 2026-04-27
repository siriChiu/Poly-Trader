import sys  
sys.path.insert(0, '.')  
from data_ingestion.collector import run_collection_and_save  
from database.models import init_db  
SessionLocal = init_db('sqlite:///database/poly_trader.db')  
session = SessionLocal()  
print('Session type:', type(session))  
print('Attempting data collection...')  
success = run_collection_and_save(session)  
print('Collection success:', success)  
if success:  
    session.commit()  
    print('Data committed to database')  
else:  
    print('Collection failed')  
session.close() 
