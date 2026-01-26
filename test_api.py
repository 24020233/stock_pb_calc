import urllib.request
import json

def check_eastmoney_pb(code):
    # secid format: 1.600519 (SH), 0.000001 (SZ)
    # Guess exchange: 6 start -> 1.xxx, 0/3 start -> 0.xxx
    if code.startswith('6'):
        secid = f"1.{code}"
    else:
        secid = f"0.{code}"
        
    # f43: Price, f57: Code, f58: Name, f167: P/B Ratio (MRQ/LYR?) - Let's check fields
    # Common fields: f57(code), f58(name), f43(price), f167(PB ratio)
    url = f"http://push2.eastmoney.com/api/qt/stock/get?secid={secid}&ut=fa5fd1943c7b386f172d6893dbfba10b&fields=f43,f57,f58,f162,f167,f170"
    
    # f162: PE(Dynamic), f167: PB, f170: Market Cap?
    
    print(f"Requesting {url}")
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode('utf-8'))
        print(data)

check_eastmoney_pb("601398") # ICBC
