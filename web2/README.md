# Stock Selection System V2

## Directory Structure

- `backend/`: Flask application
- `frontend/`: Vue 3 + Vite application

## Setup

### Backend

1. Navigate to `backend/`.
2. Install dependencies (if not already): `pip install flask flask-cors mysql-connector-python requests pandas akshare`
3. Ensure `.env` is in the project root (parent of `web2/`).
4. Run: `python app.py`
   - Server starts at `http://0.0.0.0:8002`

### Frontend

1. Navigate to `frontend/`.
2. Install dependencies: `npm install`
3. Run dev server: `npm run dev`
   - Access at `http://localhost:5174`

## Features

- **Pipeline**: Automated 4-node stock selection process.
    - Node A: Info Gathering (Public Accounts)
    - Node B: Topic Extraction (LLM)
    - Node C: Abnormal Scan (Market Data)
    - Node D: Deep Dive (LLM + Technicals)
- **Dashboard**: View daily run status.
