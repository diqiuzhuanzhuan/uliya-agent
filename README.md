# Uliya Agent MVP

一个基于 FastAPI + Next.js 的通用 Agent Web App MVP，采用清晰的模块边界来承载 Deep Agents 风格能力：聊天、多步骤规划、工具调用、流式输出、SQLite 记忆，以及可继续扩展的 skills / RAG / 文件上传 / 会话 / 认证能力。

## 目录结构

```text
.
├── backend
│   ├── app
│   │   ├── agents        # Deep Agent 运行时封装与后续真实 SDK 适配层
│   │   ├── api           # HTTP / SSE 接口
│   │   ├── core          # 配置、事件协议
│   │   ├── db            # SQLite 初始化与 memory store
│   │   ├── models        # Pydantic schema
│   │   ├── services      # 预留业务服务层
│   │   └── tools         # 示例工具与后续工具扩展点
│   └── tests
├── frontend
│   ├── app               # Next.js App Router 页面
│   ├── components        # 聊天区 / 任务轨迹区 / 配置区
│   ├── lib               # SSE 客户端等基础能力
│   └── types             # 前端共享类型
├── scripts               # 启动脚本
└── .env.example
```

## MVP 能力

- 聊天区：发送消息并接收流式答案
- 任务轨迹区：展示 plan、steps、tool calls、memory snapshot
- 配置区：切换工具、记忆、检索、Deep Agents 模型和 skills prompt
- 会话区：管理多线程会话并回看历史对话
- 示例工具：`calculator`、`web_search_mock`、`file_reader_mock`
- 基础记忆：SQLite 持久化 thread messages
- 轨迹持久化：每次流式事件都会写入 SQLite
- 上传入口：支持上传本地文本文件，为后续 RAG 做准备
- 流式链路：FastAPI SSE -> Next.js fetch stream parser
- 真实 Deep Agents 入口：配置 `OPENAI_API_KEY` 后可切换真实 `deepagents` 运行时

## 后端设计

`backend/app/agents/deep_agent.py` 提供一个稳定的 `DeepAgentRuntime` 边界：

- 当前 MVP 默认采用可控的 Deep Agents 风格编排器，确保零额外服务时也容易理解和二次开发
- 当 `OPENAI_API_KEY` 存在且前端开启 `use_real_deepagents` 时，会切换到官方 `deepagents` SDK
- API 层与前端事件协议不依赖具体底层实现，便于后续增加 RAG、认证、文件上传和更多工具

`backend/app/services/chat_service.py` 负责把运行时和持久化连接起来；`backend/app/db/repository.py` 则统一管理线程、消息、轨迹和上传记录。

## 环境变量

复制根目录 `.env.example` 为 `.env`，按需填写：

```bash
cp .env.example .env
```

关键变量：

- `OPENAI_API_KEY`：如果后续接入真实 Deep Agents / LLM，需要配置
- `OPENAI_MODEL`：模型名，默认 `gpt-4.1-mini`
- `DATABASE_URL`：默认使用 `sqlite:///./backend/data/agent.db`
- `USE_REAL_DEEPAGENTS`：默认 `false`
- `NEXT_PUBLIC_API_BASE_URL`：前端访问后端 API 的基础地址

## 启动方式

### 1. 后端

推荐 Python 3.11+：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

运行：

```bash
../scripts/start_backend.sh
```

后端地址默认是 [http://localhost:8000](http://localhost:8000)，健康检查接口为 [http://localhost:8000/api/health](http://localhost:8000/api/health)。

### 2. 前端

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api npm run dev
```

或者直接使用脚本：

```bash
./scripts/start_frontend.sh
```

前端地址默认是 [http://localhost:3000](http://localhost:3000)。

## 流式协议

后端 `POST /api/chat/stream` 返回 `text/event-stream`，当前统一事件名为 `agent_event`，`data` 内根据 `type` 字段区分：

- `run_started`
- `plan_created`
- `memory_snapshot`
- `retrieval_result`
- `step_started`
- `tool_call`
- `tool_result`
- `step_completed`
- `answer_delta`
- `run_completed`

这样的设计能保证前端只依赖协议，不依赖具体的 agent 执行库。

## 新增接口

- `GET /api/threads`：列出会话
- `POST /api/threads`：创建会话
- `GET /api/threads/{thread_id}/messages`：读取历史消息
- `GET /api/threads/{thread_id}/traces`：读取历史轨迹
- `GET /api/uploads?thread_id=...`：列出上传资料
- `POST /api/uploads`：上传文本资料

## 真实 Deep Agents 模式

要启用真实 `deepagents` 运行时：

1. 在 `.env` 中设置 `OPENAI_API_KEY`
2. 可选地设置 `OPENAI_MODEL`
3. 启动前端后，在配置区勾选“预留真实 Deep Agents SDK 切换位”

如果密钥未配置，应用会自动回退到本地编排运行时，但保持同一套前后端协议。

## 后续扩展建议

- 在 `backend/app/agents` 中继续细化真实 `deepagents` 的事件映射与工具观测
- 在 `backend/app/tools` 中加入工具注册中心与权限控制
- 在 `backend/app/services` 中接入 RAG、文件上传、用户空间与认证
- 将 `thread_id` 与用户体系绑定，实现多会话隔离
- 使用 LangGraph / LangSmith 补充观测、回放和持久化执行状态
