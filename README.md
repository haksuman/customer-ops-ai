# Customer Ops AI Copilot

A practical interview prototype for semi-automated utility customer support.
It processes inbound customer emails, routes them through a deterministic workflow, and generates a final response with clear guardrails.

## What This Project Demonstrates

- Mixed-intent email handling (public + authenticated requests in one thread)
- Deterministic auth gating for sensitive actions
- LLM-assisted extraction and response composition
- Human-in-the-loop queues for risky/unsupported cases
- End-to-end observability through workflow steps and dashboard endpoints

## How The Processing Works

The backend executes a LangGraph workflow:

1. **Extract and detect**  
   Extracts intents/entities from the latest customer message.
2. **Handle no-auth intents first**  
   Product/tariff questions are answered immediately.
3. **Apply auth policy**  
   Protected intents require verified customer identity.
4. **Handle protected intents**  
   Meter reading updates, anomaly checks, personal-data-change review flow.
5. **Fallback safety check**  
   Unsupported or unclear requests are forwarded to manual review.
6. **Aggregate final response**  
   Response parts are turned into a customer-ready email.

Core workflow definition: `backend/app/graph/workflow.py`  
Node logic: `backend/app/graph/nodes.py`

## Key Logic

- **No-auth vs auth-required intents**  
  `ProductInfoRequest` is public; meter reading, contract actions, and personal data change are protected.
- **Anomaly handling**  
  High meter-reading deviations are flagged with explicit anomaly context before response generation.
- **Fallback routing**  
  If intent detection fails or request is out of scope, the flow creates a not-handled item for operator review.
- **Small-model reliability**  
  The extractor includes regex and keyword fallbacks designed to remain robust with fast models.

## Tech Stack (And Why)

- **FastAPI**: clear, typed API surface and fast iteration for backend endpoints
- **LangGraph**: explicit stateful workflow orchestration, easier to audit than ad-hoc chaining
- **Pydantic**: structured contracts for request/response/state data
- **React + Vite + TypeScript**: fast UI development for inbox simulation and process visibility
- **pytest + TestClient**: reliable regression coverage for routing and workflow behavior
- **Docker Compose**: reproducible local full-stack run

## LLM Configuration

The backend supports `ollama` and `gemini api`.  
In production, this project uses **Gemini 3 Flash API**.

Backend env file: `backend/.env`

Typical Gemini setup:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3-flash-preview
```

Implementation: `backend/app/core/llm.py`

## Run Locally

### Prerequisites

- Python 3.12+
- Node.js 20+

### 1) Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

### 2) Frontend

```powershell
cd frontend
npm install
npm run dev
```

UI: `http://localhost:5173`  
Frontend API base can be set via `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

## Run With Docker

```bash
docker compose up --build
```

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Main API Endpoints

- `POST /api/messages/process` - process one message in a thread
- `GET /api/threads/{thread_id}` - inspect thread state and workflow history
- `GET /api/approvals` - pending human approvals
- `GET /api/not-handled-emails` - manual review queue
- `GET /api/dashboard` - operational metrics

## Project Layout

- `backend/` - workflow engine, API, mock repositories, tests
- `frontend/` - review UI and analytics views
- `backend/data/` - local mock data for customers, products, queues
- `docker-compose.yml` - full-stack local orchestration
