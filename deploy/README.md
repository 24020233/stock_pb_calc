# Deployment (Linux)

This repo is a Flask API + Vue (Vite) admin UI.

Below is a simple, production-ish setup:
- Gunicorn runs the API on `127.0.0.1:8001`
- Nginx serves the built web UI and proxies `/api/*` to Gunicorn

## 0) Prereqs

- Ubuntu/Debian host
- Python 3.11+
- Node 18+ (only needed to build the web UI)
- Nginx

## 1) Copy code to server

Recommended path: `/opt/stock_pb_calc`

## 2) Create backend env

Create `/opt/stock_pb_calc/.env` (DO NOT COMMIT). Refer to `.env.example`.

Important for production:
- `API_DEBUG=0`
- `MYSQL_*` and `MYSQL_PASSWORD`
- `PASSWORD` (UI login)
- `DAJIALA_KEY`
- `DEEPSEEK_API_KEY`

## 3) Python venv + deps

```bash
cd /opt/stock_pb_calc
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

## 4) Build the web UI

```bash
cd /opt/stock_pb_calc/web
npm install
npm run build
```

After this you should have: `/opt/stock_pb_calc/web/dist`.

## 5) systemd service

Copy `deploy/stock_pb_calc.service` to:

```bash
sudo cp /opt/stock_pb_calc/deploy/stock_pb_calc.service /etc/systemd/system/stock_pb_calc.service
sudo systemctl daemon-reload
sudo systemctl enable --now stock_pb_calc
sudo systemctl status stock_pb_calc
```

## 6) Nginx

Copy `deploy/nginx.stock_pb_calc.conf` to Nginx sites and enable:

```bash
sudo cp /opt/stock_pb_calc/deploy/nginx.stock_pb_calc.conf /etc/nginx/sites-available/stock_pb_calc
sudo ln -sf /etc/nginx/sites-available/stock_pb_calc /etc/nginx/sites-enabled/stock_pb_calc
sudo nginx -t
sudo systemctl reload nginx
```

Now visit your server IP/domain. The web UI is at `/` and API is at `/api/*`.

## Notes

- For HTTPS, add certbot or your preferred TLS setup.
- The API includes long-running endpoints; nginx proxy timeouts are set accordingly.
