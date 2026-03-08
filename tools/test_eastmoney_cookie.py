import ssl
import urllib.request
from selenium import webdriver
import time

URL = "https://push2.eastmoney.com/api/qt/clist/get?np=1&fltt=1&invt=2&cb=jQuery371012205888331287862_1772877396769&fs=b:bk0655+f:!50&fields=f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f7,f15,f18,f16,f17,f10,f8,f9,f23&fid=f3&pn=2&pz=10&po=1&dect=1&ut=fa5fd1943c7b386f172d6893dbfba10b&wbp2u=7025305900436274|0|1|0|web&_=1772877397027"
COOKIE = "qgqp_b_id=3c11fd0bb029fea7cce0fe00e53743db; st_nvi=NIsEuamOh1i-Vrqzx5poj2c60; fullscreengg=1; fullscreengg2=1; st_si=70394992564962; st_asi=delete; nid18=062561e06a16d0e24652763142451407; nid18_create_time=1772891746916; gviem=KV-2-DSzn7u6mKlpLskaV23b8; gviem_create_time=1772891746916; wsc_checkuser_ok=1; st_pvi=53293101253638; st_sp=2025-01-27%2010%3A48%3A59; st_inirUrl=https%3A%2F%2Fwww.google.com.hk%2F; st_sn=23; st_psi=20260308191159273-113200301353-7622618406"
COOKIES = {
    "qgqp_b_id": "3c11fd0bb029fea7cce0fe00e53743db",
    "st_nvi": "NIsEuamOh1i-Vrqzx5poj2c60",
    "fullscreengg": "1",
    "fullscreengg2": "1",
    "st_si": "70394992564962",
    "st_asi": "delete",
    "nid18": "062561e06a16d0e24652763142451407",
    "nid18_create_time": "1772891746916",
    "gviem": "KV-2-DSzn7u6mKlpLskaV23b8",
    "gviem_create_time": "1772891746916",
    "wsc_checkuser_ok": "1",
    "st_pvi": "53293101253638",
    "st_sp": "2025-01-27 10:48:59",
    "st_inirUrl": "https://www.google.com.hk/",
    "st_sn": "23",
    "st_psi": "20260308191159273-113200301353-7622618406",
}


def test_http():
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Cookie": COOKIE,
        "Referer": "https://www.eastmoney.com/",
        "Accept": "*/*",
    }
    req = urllib.request.Request(URL, headers=headers)
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
            body = resp.read(1000)
            print("HTTP", {
                "status": resp.status,
                "content_type": resp.headers.get("Content-Type"),
                "body_prefix": body.decode("utf-8", errors="replace")[:300],
            })
    except Exception as e:
        print("HTTP", {"error_type": type(e).__name__, "error": str(e)})


def test_selenium():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    try:
        driver.get('https://www.eastmoney.com/')
        time.sleep(1)
        for name, value in COOKIES.items():
            driver.add_cookie({"name": name, "value": value, "domain": ".eastmoney.com", "path": "/"})
        driver.get(URL)
        time.sleep(1)
        text = driver.execute_script("return document.body ? document.body.innerText : document.documentElement.innerText;")
        print("SELENIUM", repr((text or '')[:300]))
    except Exception as e:
        print("SELENIUM", {"error_type": type(e).__name__, "error": str(e)})
    finally:
        driver.quit()


if __name__ == "__main__":
    test_http()
    test_selenium()
