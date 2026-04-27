import sys  
sys.path.insert(0, '.')  
from analysis.sense_validator import validate_senses  
from database.models import init_db  
from config import load_config  
cfg = load_config()  
session = init_db(cfg['database']['url'])  
result = validate_senses(session)  
print('Status:', result['status'])  
for col, det in result['details'].items():  
    print(det['name'], 'IC:', det['ic'], 'null_ratio:', det['null_ratio'])  
session.close()  
