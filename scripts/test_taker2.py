
import urllib.request, json

urls = [
    'https://fapi.binance.com/fapi/v1/takerlongshortratio?symbol=BTCUSDT&period=5m&limit=1',
    'https://fapi.binance.com/futures/data/taker-longshort-ratio?symbol=BTCUSDT&period=5m&limit=1',
    'https://fapi.binance.com/fapi/v1/topLongShortPositionRatio?symbol=BTCUSDT&period=5m&limit=1',
    'https://fapi.binance.com/fapi/v1/takerBuySellVol?symbol=BTCUSDT&period=5m&limit=1',
    'https://fapi.binance.com/futures/data/takerBuySellVol?symbol=BTCUSDT&period=5m&limit=1',
    'https://fapi.binance.com/fapi/v1/publicData/takerlongshortratio?symbol=BTCUSDT&period=5m&limit=1',
]

for url in urls:
    try:
        req = urllib.request.urlopen(url, timeout=10)
        data = json.loads(req.read())
        short_url = url.split("?")[0].split("/")[-1]
        print(f'OK [{short_url}]: OK - {json.dumps(data[0] if isinstance(data, list) else data)[:100]}')
    except Exception as e:
        short_url = url.split("?")[0].split("/")[-1]
        print(f'FAIL [{short_url}]: {e}')
