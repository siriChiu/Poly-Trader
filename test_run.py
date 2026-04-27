from data_ingestion.collector import run_collection_and_save  
from database.models import init_db  
SessionLocal = init_db('sqlite:///database/poly_trader.db')  
from database.models import Session  
session = SessionLocal()  
success = run_collection_and_save(session)  
print('Success:', success)  
session.close() 
