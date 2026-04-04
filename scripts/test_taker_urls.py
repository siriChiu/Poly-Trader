import urllib.request, json

# Test alternative endpoints for taker ratio
urls = [
    'https://fapi.binance.com/futures/data/takerBuySellVol?symbol=BTCUSDT&period=5m&limit=1',
    'https://fapi.binance.com/fapi/v1/takerBuySellVol?symbol=BTCUSDT&period=5m&limit=1',
    'https://fapi.binance.com/fapi/v1/topLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1',
    'https://fapi.binance.com/fapi/v1/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1',
]

for url in urls:
    try:
        req = urllib.request.urlopen(url, timeout=10)
        data = json.loads(req.read())
        print(f'OK [{url.split("?")[0].split("/")[-1]}]: {json.dumps(data[:1] if isinstance(data, list) else data)}')
    except Exception as e:
        print(f'FAIL [{url.split("?")[0].split("/")[-1]}]: {e}')
