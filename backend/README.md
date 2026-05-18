# Backend (Module 1)

FastAPI service: Supabase JWT auth, threaded chat history, OpenAI Chat Completions streaming (SSE), optional LangSmith tracing.

## Setup

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp ../.env.example .env
# Edit .env with your keys
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/me` | Auth test (Bearer JWT) |
| POST | `/api/chat/stream` | SSE chat stream |

### Chat stream

```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT" \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"THREAD_UUID","content":"Hello"}'
```

## Environment

See root `.env.example` for all variables.
