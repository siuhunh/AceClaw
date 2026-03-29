# AceClaw Frontend

Next.js 14 (App Router) + TypeScript + Tailwind CSS + Monaco Editor（Light / `vs`）+ Lucide。布局对齐 `dev.md` §3.7：左导航与列表、中栏对话与可折叠 SSE 思考链、右侧 Monaco 编辑 `skill/` 与 `memory/` 文件。

## 前置

1. 启动后端（默认 `http://127.0.0.1:8000`，已配置 CORS 允许 `localhost:3000`）。
2. 复制环境变量：`cp .env.local.example .env.local`（可按需修改 API 地址）。

## 命令

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 <http://localhost:3000>。

## API 对接

| 能力 | 调用 |
|------|------|
| 健康检查 | `GET /health` |
| 会话列表 | `GET /api/sessions` |
| 对话（SSE / JSON） | `POST /api/chat`，`stream: true \| false` |
| 技能列表与读取 | `GET /api/skills`、`GET /api/skills?path=...` |
| 保存技能 | `POST /api/skills` |
| 记忆列表与读取 | `GET /api/memories`、`GET /api/memories?path=...` |
| 保存记忆 | `POST /api/memories` |

## 说明

- **Shadcn/UI**：当前使用 Tailwind 自绘按钮与布局，视觉与交互接近文档中的三栏 IDE 形态；后续可再执行 `npx shadcn-ui@latest init` 替换为官方组件。
- **思考链**：展示 SSE 原始事件行（`start` / `token` / `memory_saved` / `end` 等），便于与 `dev.md` §3.2 对照调试。
