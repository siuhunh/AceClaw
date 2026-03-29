# AceClaw Python 重构需求与后端设计

> 版本：0.7  
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
- 数据存储：本地文件系统（`backend/storage`，见 §4）
- 传输协议：JSON over HTTP + `text/event-stream`（SSE）

### 2.2 分层

- `api`：路由层，负责参数校验与响应协议
- `services`：业务层（agent、memory、skills）
- `schemas`：Pydantic 请求/响应模型
- `core`：配置、应用初始化
- `storage`：运行期文件（`skill/`、`memory/`）

### 2.3 本地存储根目录（统一约定）

- **唯一数据根目录**：`backend/storage/`。技能、记忆及后续扩展的本地文件型资源，**默认均放在该目录下**，读写路径均相对此根解析。
- **当前子目录**：
  - 技能：`backend/storage/skill/`（API 逻辑前缀 `skill/`）
  - 记忆：`backend/storage/memory/`（API 逻辑前缀 `memory/`）
- 配置常量见 `backend/app/core/config.py` 中的 `STORAGE_ROOT`、`SKILL_DIR`、`MEMORY_DIR`。

---

## 3. 核心能力设计

### 3.1 异步 HTTP API

基础接口（MVP）：

- `GET /health`：健康检查
- `GET /api/skills`：列出可用 skills；带 `?path=skill/xxx.md` 时读取单文件全文
- `POST /api/skills`：按路径保存技能 Markdown
- `POST /api/skills/reload`：重载 skills 缓存
- `GET /api/memories`：记忆文件列表；带 `?path=memory/xxx.md` 或 `memory/xxx.json` 时读取单文件全文
- `POST /api/memories`：按路径保存记忆文件
- `GET /api/sessions`：会话列表（按 `updated_at` 降序，数据来自 `storage/session`）
- `POST /api/chat`：对话；请求体字段 `stream` 为 `true` 时 **SSE 流式**，为 `false` 时 **JSON 同步**（不再单独提供 `/api/chat/stream`）

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

### 3.3 文件记忆

记忆目录约定（物理路径，对应 API 逻辑路径前缀 `memory/`）：

- `backend/storage/memory/{session_id}.md`：可读对话历史（主，追加块）
- `backend/storage/memory/{session_id}.json`：结构化消息列表（与 `append_turn` 同步）

策略：

- 每轮对话落盘（追加 md + 更新 json）
- `session_id` 作为会话主键
- API 中文件以逻辑路径表示，例如 `memory/main_session.md`

### 3.4 Skill 管理

技能文件约定（物理路径，对应 API 逻辑路径前缀 `skill/`）：

- 每次启动agent会自动调用available_skills()函数读取所有/backend/storage/skill/{SKILL}.md，根据名字+功能说明在汇总为backend/workspace/SKILLS_SNAPSHOT.md，参考如下：

```plaintext
<available_skills>
  <skill>
    <name>宝可梦冠军属性技能克制表</name>
    <description>这个技能可以帮助你在游玩宝可梦冠军时计算属性技能克制信息</description>
    <location>./backend/storage/skill/pokemon_dmg_skill.md</location>
  </skill>
</available_skills>
```

- 每个技能对应 `backend/storage/skill/` 下**顶层**一个 Markdown：`*.md`
- 技能标识 `name` 为文件名去掉扩展名（例如 `greeting.md` → `greeting`）
- API 中路径示例：`skill/greeting.md`

读取规则：

- **服务启动时**扫描 `backend/storage/skill/*.md` 并载入缓存
- 支持运行中通过 `POST /api/skills` 写入后自动 `reload`，或 `POST /api/skills/reload`
- 列表接口返回：技能名、逻辑路径 `path`、绝对路径 `location`、描述摘要

### 3.5 模型接入与回退策略（新增）

#### 3.5.1 配置来源优先级

1. `backend/config.toml`
2. 环境变量（可覆盖）
3. 代码默认值（DeepSeek）

#### 3.5.2 LLM 默认策略

- 默认供应商：`deepseek`
- 默认聊天实现：配置项 `llm.model_type`（或环境变量 `LLM_MODEL_TYPE`），缺省与 `provider` 对齐；**默认使用 `langchain_deepseek.ChatDeepSeek` 初始化**
- 默认模型：`deepseek-chat`
- 默认 `base_url`：`https://api.deepseek.com/v1`
- **类型映射**（`backend/app/core/model_factory.py`，由 `main` 启动时 `init_agent_llm` 初始化）：
  - `deepseek` → `ChatDeepSeek`
  - `openai`（及别名 `gpt`、`openai_compatible`）→ `langchain_openai.ChatOpenAI`
  - `ollama` → `langchain_ollama.ChatOllama`
- **回退**：`model_type` 无法识别时，直接使用 `ChatDeepSeek`；若按映射构建实例时抛错（依赖、参数、网络校验等），`try/except` 后**回退为 `ChatDeepSeek`**

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
### 3.7 会话管理

在storage/session/目录下，根据session_id关联对应的{session_id}.json会话记录，同时暴露给/api/sessions的GET. POST使用。

### 3.8 前端设计

- 框架：Next.js 14+ (App Router)、TypeScript

- UI 组件：Shadcn/UI、Tailwind CSS、Lucide Icons

- 编辑器：Monaco Editor（默认配置 Light Theme）

#### 3.8.1 前端布局

经典问答式风格，左中右三栏式布局：

1.左：功能导航 (Chat/Memory/Skills) + 历史会话列表
2.中：对话流展示 + 可折叠思考链可视化 (Collapsible Thoughts)
3.右：Monaco 编辑器，实时查看/编辑当前使用的 SKILL.md 或 MEMORY.md

### 3.9 服务内置工具

服务除加载用户自定义 Skills 外，必须内置以下 5 个核心基础工具（Core Tools），遵循“优先使用 LangChain 原生工具”原则，工具实现统一集中在 `backend/tools` 并在服务启动时**统一**完成初始化，技术选型与实现规范如下：

#### 3.9.1 命令行操作工具 (Command Line Interface)

- **功能描述**：允许 Agent 在受限的安全环境下执行 Shell 命令

- **实现逻辑**：直接使用 LangChain 内置工具 `langchain_community.tools.ShellTool`

- **配置要求**：初始化配置 `root_dir` 限制操作范围（沙箱化），防止修改系统关键文件；预置黑名单拦截高危指令（如 `rm -rf /`和 `shutdown`）

- **工具名称**：terminal

#### 3.9.2  Python 代码解释器 (Python REPL)

- **功能描述**：赋予 Agent 逻辑计算、数据处理和脚本执行的能力

- **实现逻辑**：直接使用 LangChain 内置工具 `langchain_experimental.tools.PythonREPLTool`

- **配置要求**：自动创建临时 Python 交互环境，需确保 experimental 包依赖安装正确

- **工具名称**：python_repl

#### 3.9.3  Fetch 网络信息获取

- **功能描述**：用于获取指定 URL 的网页内容，是 Agent 联网的核心工具

- **实现逻辑**：直接使用 LangChain 内置工具 `langchain_community.tools.RequestsGetTool`，同时支持env环境配置文件配置tavily的user_key，如果有配置tavily key则优先使用并统计查询次数和查询token数。

- **增强配置**：原生工具返回原始 HTML，Token 消耗巨大，需封装 Wrapper，通过 BeautifulSoup 或 html2text 库清洗数据，仅返回 Markdown 或纯文本内容

- **工具名称**：fetch_url，配置tavily

#### 3.9.4  文件读取工具 (File Reader)

- **功能描述**：精准读取本地指定文件内容，是 Agent Skills 机制的核心依赖，用于读取 SKILL.md 详细说明

- **实现逻辑**：直接使用 LangChain 内置工具 `langchain_community.tools.file_management.ReadFileTool`

- **配置要求**：设置 `root_dir` 为项目根目录，严禁读取项目以外的系统文件

- **工具名称**：read_file

#### 3.9.5  RAG 检索工具 (Hybrid Retrieval)

- **功能描述**：用户询问具体知识库内容（非对话历史）时，Agent 可调用此工具进行深度检索

- **技术选型**：LlamaIndex

- **实现逻辑**：支持扫描指定目录（如 `knowledge/`）下的 PDF/MD/TXT 文件构建本地索引；实现 Hybrid Search（关键词检索 BM25 + 向量检索 Vector Search）；索引文件持久化存储至本地 `storage/` 目录

- **工具名称**：search_knowledge_base
---

### 3.9 System Prompt

Agent 每次被调用时都会重新读取所有 Markdown 文件并组装 System Prompt，确保 workspace 文件的实时编辑能立即生效：

```Plain Text

┌───────────────────────────────────┐
│ <!-- Skills Snapshot -->          │  ← `backend/workspace/SKILLS_SNAPSHOT.md`（含 `{{AUTO_SKILLS}}` 注入扫描技能）
│ <!-- Soul -->                     │  ← `backend/workspace/SOUL.md` (核心设定)
│ <!-- Identity -->                 │  ← `backend/workspace/IDENTITY.md` (自我认知)
│ <!-- User Profile -->             │  ← `backend/workspace/USER.md` (用户画像)
│ <!-- Agents Guide -->             │  ← `backend/workspace/AGENTS.md` (行为准则 & 记忆操作指南)
│ <!-- Long-term Memory -->         │  ← `storage/memory/{session_id}.md`（当前会话长期记忆；无文件时用占位说明）
└───────────────────────────────────┘
```

每个组件间以 \n\n 分隔，每个组件带 HTML 注释标签便于调试定位。

## 4. 目录与模块规划（已落地）

```text
backend/
  workspace/          # §3.9 System Prompt：SKILLS_SNAPSHOT / SOUL / IDENTITY / USER / AGENTS（每次请求重读）
  app/
    api/routes/       # health, chat, skills, memories, sessions
    core/             # config, model_factory, storage_paths
    schemas/
    services/         # agent_runtime, system_prompt, memory_store, skill_manager, storage_files
    main.py
  tools/              # §3.9 Core Tools：terminal, python_repl, fetch_url, read_file, search_knowledge_base
  storage/
    skill/            # *.md，API: skill/<name>.md
    memory/           # *.md / *.json，API: memory/<session_id>.md|json
    workspace/        # ShellTool 终端沙箱（与上列 `backend/workspace/` 不同）
    knowledge/        # RAG 源文档（PDF/MD/TXT）
    index/knowledge/  # LlamaIndex 持久化索引
  requirements.txt
  README.md

frontend/             # Next.js 14 App Router，见 §3.7
  app/                # layout, page, globals.css
  components/         # app-shell, monaco-editor-panel
  lib/                # api 客户端、SSE 解析、cn()
  package.json
  README.md
```

---

## 5. 迭代计划

### Milestone 1（当前）

- 后端目录初始化
- FastAPI 应用启动
- 健康检查与基础 API
- SSE 流式输出骨架
- 文件记忆与技能扫描服务

### Milestone 2

- 接入真实 LangChain ChatModel（DeepSeek / OpenAI 兼容）
- 增加 Embedding Provider 选择与回退（Ollama -> DeepSeek）
- 统一事件追踪（JSONL trace）
- 增强 memory（摘要、窗口、检索）

### Milestone 3

- 加入工具执行与安全策略
- 前端联调（会话与流式渲染）

---

## 6. 运行方式

在仓库根目录执行：

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

前端（另开终端）：

```bash
cd frontend
npm install
npm run dev
```

默认前端 `http://localhost:3000`，后端 `http://127.0.0.1:8000`；可通过 `frontend/.env.local` 设置 `NEXT_PUBLIC_API_BASE_URL`。

---

## 7. 后台 API 规范

### 7.1 通用约定

- **物理根目录**：`backend/storage/`。所有通过 API 读写的本地文件，均落盘在该目录下。
- **逻辑路径 → 物理路径**（默认、相对 `backend/storage/`）：
  - `skill/<rest>` → `backend/storage/skill/<rest>`
  - `memory/<rest>` → `backend/storage/memory/<rest>`
- 服务端校验逻辑路径，禁止 `..` 越界出上述子目录。
- `GET` 列表接口**无请求体**；若需读取单个文件，使用 **Query** `path`（与下表一致）。

### 7.2 接口一览


| 方法   | 路径                   | 说明                                                                        |
| ---- | -------------------- | ------------------------------------------------------------------------- |
| GET  | `/health`            | 健康检查，返回 `ok`                                                              |
| GET  | `/api/usage`         | 聚合用量；当前含 `tavily` 字段（未配置 Key 时 `configured=false`）；Tavily 调用仍写 `ace_claw` 日志 |
| POST | `/api/chat`          | 见 §7.3                                                                    |
| GET  | `/api/skills`        | 无 `path`：技能列表；有 `path=skill/xxx.md`：返回该文件 `content`                       |
| POST | `/api/skills`        | 请求体 `{"path": "skill/xxx.md", "content": "..."}` 保存并刷新缓存                  |
| POST | `/api/skills/reload` | 仅重载缓存                                                                     |
| GET  | `/api/memories`      | 无 `path`：记忆条目列表；有 `path=memory/xxx.md` 或 `memory/xxx.json`：返回文件 `content` |
| POST | `/api/memories`      | 请求体 `{"path": "memory/...", "content": "..."}`                            |
| GET  | `/api/sessions`      | 会话列表（按 `updated_at` 降序）                                                   |


### 7.3 `POST /api/chat`

请求体（JSON）：

```json
{
  "message": "查询一下北京的天气",
  "session_id": "main_session",
  "stream": true
}
```

- `stream: true`：响应 `Content-Type: text/event-stream`（SSE），事件类型见 §3.2。
- `stream: false`：响应 JSON，形如 `{ "session_id": "...", "output": "..." }`。

### 7.4 验收（与 §7 对齐）

- 服务可启动且 `GET /health` 正常。
- `POST /api/chat` 在 `stream` 为 `true` / `false` 时分别对应 SSE 与 JSON。
- `GET/POST /api/skills`、`GET/POST /api/memories`、`GET /api/sessions` 行为与上表一致；磁盘文件位于 `backend/storage/skill/*`、`backend/storage/memory/*`。

