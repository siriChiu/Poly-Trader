.timeout 1000  
SELECT COUNT(*) FROM raw_market_data;  
SELECT COUNT(*) FROM features_normalized;  
SELECT COUNT(*) FROM labels;  
SELECT close_price, fear_greed_index FROM raw_market_data ORDER BY timestamp DESC LIMIT 1;  
