# AceClaw Python 重构需求与后端设计

> 版本：0.6  
> 状态：进行中  
> 后端：**FastAPI + Uvicorn（Async HTTP + SSE）**  
> Agent 引擎：**LangChain 1.0+**  
> 语言：**Python 3.11+**

---

## 1. 目标与范围

本阶段目标是用 Python 重构并实现 OpenClaw 基础能力，先完成可运行的后端内核，覆盖：

- 异步 HTTP API（FastAPI）
- SSE 流式推送（逐步输出 Agent 执行事件）
- LangChain 1.0 Agent 运行时骨架
- 文本文件记忆（Markdown/JSON）
- Skill 扫描与管理

非本阶段重点（后续迭代）：

- 完整前端 IDE
- 复杂多 Agent 编排
- 向量数据库与重型 RAG 管线

---

## 2. 总体架构

### 2.1 技术选型

- Web：`FastAPI`
- ASGI Server：`Uvicorn`
- Agent：`LangChain 1.0+`（先以可替换的 runtime 接口落地）
- LLM 服务：**DeepSeek 优先**（OpenAI 兼容接入）
- Embedding（RAG）：**本地 Ollama 可选**，未配置时回退 DeepSeek
- 数据存储：本地文件系统（`backend/data`）
- 传输协议：JSON over HTTP + `text/event-stream`（SSE）

### 2.2 分层

- `api`：路由层，负责参数校验与响应协议
- `services`：业务层（agent、memory、skills）
- `schemas`：Pydantic 请求/响应模型
- `core`：配置、应用初始化
- `data`：运行期数据（会话记忆、快照等）

---

## 3. 核心能力设计

### 3.1 异步 HTTP API

基础接口（MVP）：

- `GET /health`：健康检查
- `GET /api/skills`：列出可用 skills
- `POST /api/skills/reload`：重载 skills
- `GET /api/memory/{session_id}`：读取会话记忆
- `POST /api/chat`：同步返回（非流式）
- `POST /api/chat/stream`：SSE 流式返回

### 3.2 SSE 事件协议

建议使用以下事件类型：

- `start`：请求开始
- `token`：增量文本片段
- `memory_saved`：记忆写入完成
- `end`：请求结束
- `error`：异常

数据格式：

```text
event: token
data: {"content":"..."}
```

### 3.3 文本文件记忆

记忆目录约定：

- `backend/data/memory/{session_id}.md`：可读对话历史（主）
- `backend/data/memory/{session_id}.json`：结构化消息（可选）

策略：

- 每轮对话落盘（追加）
- session_id 作为会话主键
- 后续可扩展摘要压缩与检索

### 3.4 Skill 管理

技能目录约定：

- `backend/skills/<skill_name>/SKILL.md`

读取规则：

- 启动时扫描并缓存
- 支持运行中重载
- 返回技能名、路径、描述（首段摘要）

### 3.5 模型接入与回退策略（新增）

#### 3.5.1 配置来源优先级

1. `backend/config.toml`
2. 环境变量（可覆盖）
3. 代码默认值（DeepSeek）

#### 3.5.2 LLM 默认策略

- 默认供应商：`deepseek`
- 默认模型：`deepseek-chat`
- 默认 `base_url`：`https://api.deepseek.com/v1`
- LangChain 接入：`langchain-openai` 的 OpenAI 兼容客户端

#### 3.5.3 Embedding 策略（知识库 / RAG）

- 当 `embedding.use_ollama_for_rag=true` 且 `embedding.provider=ollama` 且配置了 `embedding.model` 时：
  - 使用本地 `OllamaEmbeddings`
- 其它情况（未配置或配置不完整）：
  - 自动回退到 DeepSeek 对应配置（OpenAI Embeddings 兼容接口）
  - `embedding.model` 未设置时，默认复用 `llm.model`

#### 3.5.4 配置示例

- 示例文件：`backend/config.toml.example`
- 推荐本地使用方式：复制为 `backend/config.toml` 后填写 `llm.api_key`

### 3.6 启动配置与日志（新增）

#### 3.6.1 `.env` 启动加载策略

- 服务初始化时先读取 `.env`。
- 可通过以下方式指定目录：
  - 命令行：`--env-dir <dir>`
  - 环境变量：`ACE_CLAW_ENV_DIR=<dir>`
- 规则：
  - 若**指定了目录**，但该目录下不存在目标 `.env`（默认文件名 `.env`），服务启动直接抛异常并退出。
  - 若未指定目录，则尝试读取默认目录（`backend/`）下 `.env`，不存在时不阻断启动。

#### 3.6.2 请求日志能力

- 每次 HTTP 请求输出一条日志，包含：
  - method
  - path
  - status code
  - client ip
  - duration(ms)

#### 3.6.3 日志路径优先级

1. Uvicorn 启动命令行参数：`--log-path`
2. 环境变量：`ACE_CLAW_LOG_PATH`
3. 默认路径：项目 `backend/` 根目录下 `ace_claw.log`

#### 3.6.4 启动示例

```bash
python backend/app/main.py --reload --env-dir ./backend --log-path ./backend/logs/ace_claw.log
```

---


## 4. 目录与模块规划（已落地）

```text
backend/
  app/
    api/routes/
    core/
    schemas/
    services/
    main.py
  data/memory/
  skills/
  requirements.txt
  README.md
```

---

## 5. 迭代计划

### Milestone 1（当前）

- [x] 后端目录初始化
- [x] FastAPI 应用启动
- [x] 健康检查与基础 API
- [x] SSE 流式输出骨架
- [x] 文件记忆与技能扫描服务

### Milestone 2

- [x] 接入真实 LangChain ChatModel（DeepSeek / OpenAI 兼容）
- [x] 增加 Embedding Provider 选择与回退（Ollama -> DeepSeek）
- [ ] 统一事件追踪（JSONL trace）
- [ ] 增强 memory（摘要、窗口、检索）

### Milestone 3

- [ ] 加入工具执行与安全策略
- [ ] 前端联调（会话与流式渲染）

---

## 6. 运行方式

在仓库根目录执行：

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 7. 验收标准（MVP）

- 服务可启动且 `GET /health` 返回 `ok`
- `POST /api/chat` 可返回文本结果
- `POST /api/chat/stream` 以 SSE 方式逐步输出事件
- `GET /api/skills` 返回技能列表
- 会话请求后在 `backend/data/memory` 看到对应文本记忆文件