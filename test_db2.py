import sys  
sys.path.insert(0, '.')  
from data_ingestion.collector import run_collection_and_save  
from database.models import init_db  
session = init_db('sqlite:///database/poly_trader.db')  
print('Session type:', type(session))  
try:  
    success = run_collection_and_save(session)  
    print('Collection success:', success)  
    session.commit()  
    print('Session committed')  
except Exception as e:  
    print('Error:', e)  
    import traceback  
    traceback.print_exc()  
finally:  
    session.close()  
    print('Session closed') 
