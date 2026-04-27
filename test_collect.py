import sys  
sys.path.insert(0, '.')  
from data_ingestion.collector import collect_all_senses  
result = collect_all_senses()  
print('Result:', result)  
print('Type:', type(result))  
