import urllib.request, json

# Test the correct endpoint - Binance moved it to futures/data endpoint
urls = [
    'https://fapi.binance.com/futures/data/takerlongshortratio?symbol=BTCUSDT&period=5m&limit=1',
    'https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1',
]

for url in urls:
    try:
        req = urllib.request.urlopen(url, timeout=10)
        data = json.loads(req.read())
        print(f'OK {url[:60]}...: {json.dumps(data[:1])}')
    except Exception as e:
        print(f'FAIL {url[:60]}...: {e}')
