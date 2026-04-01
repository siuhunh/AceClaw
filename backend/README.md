# AceClaw Backend

FastAPI + Uvicorn backend skeleton for async HTTP and SSE streaming.

## Quick Start

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Run via Python entry (supports env and log args):

```bash
python backend/app/main.py --reload --env-dir ./backend --log-path ./backend/logs/ace_claw.log
```

## Model Configuration

1. Copy `backend/config.toml.example` to `backend/config.toml`.
2. Fill `llm.api_key` with your DeepSeek API key.

3. Optional: set embedding to local Ollama for RAG.

Fallback behavior:

- If embedding config is missing, system falls back to DeepSeek model config.
- If embedding provider is `ollama` and enabled, uses local Ollama embeddings.

## Env And Logging

- Set `ACE_CLAW_ENV_DIR` to enforce `.env` loading directory. If set but `.env` is missing, startup fails.
- Log path priority: `--log-path` > `ACE_CLAW_LOG_PATH` > `backend/ace_claw.log`.
- Request logs are written per request with method/path/status/client/duration.

## API

- `GET /health`
- `GET /api/skills`
- `POST /api/skills/reload`
- `GET /api/memory/{session_id}`
- `POST /api/chat`
- `POST /api/chat/stream`
