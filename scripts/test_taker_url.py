#!/usr/bin/env python3
import requests
urls = [
    'https://www.okx.com/api/v5/rubik/stat/taker-volume?ccy=BTC&instType=SWAP&period=5m&limit=1',
    'https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=BTC&period=5m&limit=1',
    'https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-volume?ccy=BTC&period=5m&limit=1',
]
for url in urls:
    try:
        r = requests.get(url, timeout=10)
        print(url, r.status_code, r.text[:200])
    except Exception as exc:
        print(url, exc)
