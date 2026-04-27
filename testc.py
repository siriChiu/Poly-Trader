import sys  
sys.path.insert(0, '.')  
from data_ingestion.collector import collect_all_senses  
r = collect_all_senses()  
print('Price:', r.close_price if r else 'None')  
print('FNG:', r.fear_greed_index if r else 'None')  
