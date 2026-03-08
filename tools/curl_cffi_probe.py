from curl_cffi import requests

URL = "https://push2.eastmoney.com/api/qt/clist/get?np=1&fltt=1&invt=2&cb=jQuery37106721039112435286_1772894267509&fs=m%3A90%2Bt%3A3%2Bf%3A!50&fields=f12%2Cf13%2Cf14%2Cf1%2Cf2%2Cf4%2Cf3%2Cf152%2Cf20%2Cf8%2Cf104%2Cf105%2Cf128%2Cf140%2Cf141%2Cf207%2Cf208%2Cf209%2Cf136%2Cf222&fid=f3&pn=1&pz=100&po=1&dect=1&ut=fa5fd1943c7b386f172d6893dbfba10b&wbp2u=%7C0%7C0%7C0%7Cweb&_=1772894267513"

response = requests.get(
    URL,
    impersonate="chrome136",
    timeout=30,
    headers={
        "Referer": "https://quote.eastmoney.com/center/gridlist.html#boards-BK0655",
        "Accept": "*/*",
    },
)
print(response.status_code)
print(response.text[:1000])
print(len(response.text))
