import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import re

PORT = 8000
DIRECTORY = "/Users/linhao/code/AI/stock_pb_calc"

class StockHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Serve static files
        if self.path == '/' or self.path == '/index.html':
            self.path = '/index.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        
        # API Endpoint
        if self.path.startswith('/api/pb'):
            self.handle_pb_request()
            return
            
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def handle_pb_request(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        code = params.get('code', [''])[0].strip()
        
        if not code:
            self.send_error(400, "Missing code")
            return
            
        try:
            # Determine market
            # 600/601/603/605/688 -> 1. (SH)
            # 000/002/300 -> 0. (SZ)
            # 4/8 -> 0. (Beijing? 0.8xxxx for BJ) -> Eastmoney usually uses 0 for SZ/BJ
            
            secid = ""
            if re.match(r'^(60|68)', code):
                secid = f"1.{code}"
            elif re.match(r'^(00|30)', code):
                secid = f"0.{code}"
            elif re.match(r'^(4|8)', code):
                secid = f"0.{code}"
            else:
                # Default try SH if unknown, or maybe 0?
                # Let's try to infer or error.
                pass
            
            if not secid:
                # Fallback logic: if start with 6->1, else 0
                if code.startswith('6'): secid = f"1.{code}"
                else: secid = f"0.{code}"

            url = f"http://push2.eastmoney.com/api/qt/stock/get?secid={secid}&ut=fa5fd1943c7b386f172d6893dbfba10b&fields=f43,f57,f58,f162,f167"
            
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
                
                if data and data.get('data'):
                    d = data['data']
                    price = d.get('f43', 0) / 100.0 if d.get('f43') != '-' else 0
                    pb = d.get('f167', 0) / 100.0 if d.get('f167') != '-' else 0
                    pe = d.get('f162', 0) / 100.0 if d.get('f162') != '-' else 0
                    name = d.get('f58', 'Unknown')
                    
                    response_data = {
                        "name": name,
                        "code": code,
                        "price": price,
                        "pb": pb,
                        "pe": pe
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'{"error": "Stock not found"}')
                    
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f'{{"error": "{str(e)}"}}'.encode('utf-8'))

if __name__ == "__main__":
    # Ensure allow_reuse_address to avoid "Address already in use" on restarts
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), StockHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
