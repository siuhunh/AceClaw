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
3. Optional: set `llm.model_type` to `openai` or `ollama` for alternate chat backends; invalid types or build failures fall back to `ChatDeepSeek`.
4. Optional: set embedding to local Ollama for RAG.

Fallback behavior:

- If embedding config is missing, system falls back to DeepSeek model config.
- If embedding provider is `ollama` and enabled, uses local Ollama embeddings.

## Env And Logging

- Set `ACE_CLAW_ENV_DIR` to enforce `.env` loading directory. If set but `.env` is missing, startup fails.
- Log path priority: `--log-path` > `ACE_CLAW_LOG_PATH` > `backend/ace_claw.log`.
- Request logs are written per request with method/path/status/client/duration.

## Storage layout

本地业务文件**只**使用目录 **`backend/storage/`** 作为根；API 中的 `path` 均相对该根解析。

- Skills: `backend/storage/skill/*.md` — 逻辑路径 `skill/my_skill.md`
- Memories: `backend/storage/memory/{session_id}.md` 与 `{session_id}.json` — 逻辑路径 `memory/main_session.md` / `memory/main_session.json`

## Skills

Add or edit `.md` files under `backend/storage/skill/`. On startup the server scans `*.md` and caches metadata; `POST /api/skills` can save content; `POST /api/skills/reload` refreshes the cache.

## Agent 编排

对话与工具调用优先使用 **`langchain.agents.create_agent`**（LangChain 1.x 推荐入口，底层为精简 LangGraph 范式）。若当前环境无法创建该 Agent，则回退为 `bind_tools` 手写循环。

**System Prompt**：每次请求从 **`backend/workspace/`** 读取 `SKILLS_SNAPSHOT.md`、`SOUL.md`、`IDENTITY.md`、`USER.md`、`AGENTS.md` 组装（见 `dev.md` §3.9）；`SKILLS_SNAPSHOT.md` 中 `{{AUTO_SKILLS}}` 会替换为当前扫描的技能列表；末尾拼接当前会话的 `storage/memory/{session_id}.md` 作为长期记忆块。

## Core tools (§3.9)

启动时 `main` 依次调用 `init_agent_llm` 与 `init_core_tools`，注册 5 个工具供 Agent 调用：

| 名称 | 说明 |
|------|------|
| `terminal` | `ShellTool`，根目录 `storage/workspace`，黑名单拦截高危命令 |
| `python_repl` | `PythonREPLTool` |
| `fetch_url` | HTTP GET + HTML 转文本；若设置 `TAVILY_API_KEY` 则非 URL 输入走 Tavily 搜索（调用写 `ace_claw` 日志，见 `GET /api/usage`） |
| `read_file` | `ReadFileTool`，根目录为 `backend/` |
| `search_knowledge_base` | LlamaIndex 向量 + BM25 融合（失败则 `rank-bm25` 关键词）；文档目录 `storage/knowledge/`，索引 `storage/index/knowledge/` |

## API (see `dev.md` §7)

- `GET /api/usage` — 聚合用量 JSON（当前为 `{ "tavily": { ... } }`）；未配置 Tavily 时 `tavily.configured` 为 false；调用仍写 `ace_claw` 日志
- `GET /health`
- `POST /api/chat` — body `{ "message", "session_id", "stream" }`；`stream: true` 时返回 SSE，`false` 时返回 JSON
- `GET /api/skills` — list；`GET /api/skills?path=skill/foo.md` — read one file
- `POST /api/skills` — `{ "path", "content" }`
- `POST /api/skills/reload`
- `GET /api/memories` — list；`GET /api/memories?path=memory/x.md` — read one file
- `POST /api/memories` — `{ "path", "content" }`
- `GET /api/sessions` — sessions sorted by `updated_at`
