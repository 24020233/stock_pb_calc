# WX Admin (Vue 3)

Minimal admin UI for the Flask API you deployed.

## Features

- Login (front-end session + `/api/health` validation)
- WeChat MP accounts CRUD (`/api/accounts`)

## Configure

Create `.env` from the example:

```bash
cp .env.example .env
```

Set:

- `VITE_API_BASE_URL` (default fallback: `http://43.134.90.115:8001`)

Dev tip (avoid CORS):

- Leave `VITE_API_BASE_URL` empty (or unset)
- Set `VITE_API_PROXY_TARGET` to your backend, Vite will proxy `/api/*` to it
- `VITE_FORCE_PROXY=1` (default in dev) forces same-origin requests so browser CORS won't block

## Run

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Build

```bash
npm run build
npm run preview
```
