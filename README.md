# Agentic Customer Contact Copilot

Interview-ready prototype for semi-automated customer email handling with mixed intents, auth gating, workflow transparency, and Dockerized frontend/backend.

## Stack

- **Backend:** FastAPI + LangGraph (Python 3.12)
- **Frontend:** React + Vite (TypeScript)
- **Testing:** pytest + FastAPI TestClient
- **Deployment:** Docker + Docker Compose

## Project Structure

```
customer-ops-ai/
├── backend/        API, orchestration graph, auth policy, mock repos, tests
├── frontend/       Inbox simulation UI and process transparency panel
├── docker-compose.yml
├── .env.example
├── ARCHITECTURE.md
└── README.md
```

---

## Local Development

### Prerequisites

- Python 3.12+
- Node.js 20+

---

### Backend

#### 1. Create the virtual environment

```powershell
cd backend
python -m venv .venv
```

#### 2. Activate it

**PowerShell:**
```powershell
.venv\Scripts\Activate.ps1
```

**Command Prompt:**
```cmd
.venv\Scripts\activate.bat
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

#### 4. Run the server

From inside `backend/`:
```bash
uvicorn app.main:app --reload --port 8000
```

Or from the repo root:
```bash
uvicorn app.main:app --app-dir backend --reload --port 8000
```

API docs (Swagger UI): `http://localhost:8000/docs`

#### 5. Run tests

```bash
pytest
```

---

### Frontend

#### 1. Install dependencies

```bash
cd frontend
npm install
```

#### 2. Run the dev server

```bash
npm run dev
```

UI: `http://localhost:5173`

> The frontend expects the backend on `http://localhost:8000` by default.  
> Override with a `.env` file: `VITE_API_URL=http://localhost:8000`

---

## Docker (Full Stack)

Requires Docker Desktop running.

```bash
docker compose up --build
```

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:3000        |
| Backend  | http://localhost:8000        |
| API docs | http://localhost:8000/docs   |

Copy `.env.example` to `.env` before running if you need to override any defaults:

```bash
cp .env.example .env
```

---

## Mock Data

Customer and product seed data lives in `backend/data/`:
- `customers.json` — mock customer profiles used for auth verification and meter reading lookup
- `products.json` — tariff/product descriptions returned for product info requests

The mock customer available for demo auth:

| Field           | Value       |
|-----------------|-------------|
| Contract number | `LB-123456` |
| Full name       | `Julia Meyer` |
| Postal code     | `20097`     |

---

## Demo Script (Interview)

1. Open `http://localhost:5173` (or `http://localhost:3000` via Docker).
2. Send a mixed-intent email — meter reading + dynamic tariff question — **without** auth data:
   > *"I'd like to submit my meter reading of 1438 kWh and ask about your dynamic tariff. Best, Julia Meyer"*
3. **Processing panel** shows tariff info answered immediately; protected intent waits for auth.
4. Send a follow-up with the three auth fields:
   > *"Contract number LB-123456, Julia Meyer, postal code 20097."*
5. **Processing panel** shows auth verified and meter reading recorded.
6. Point to the backend logs (JSON structured, with request ID and thread ID) to discuss observability.
