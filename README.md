---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 0fdc97ed31210ef38faca8cd75bf0149_4d7383d4cdf411f18de0525400de85a5
    ReservedCode1: 0lW3uAbZHH4cVGEY4Hf7Nxr/9A+aphCZlyvUbaTNJDoGSScUMMUy7jbzSkowEstXGnNPQSXJkPKbXrFlddkgM/wjbjpJVDv15Yik7/cZPaPFL2xpFjDtzrwU6aD4aQALZFrJSwYW4xahT5sQKD12FopjmRy6xHRnH7s72+qCUiJuGzsSDRydrtPDK5k=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 0fdc97ed31210ef38faca8cd75bf0149_4d7383d4cdf411f18de0525400de85a5
    ReservedCode2: 0lW3uAbZHH4cVGEY4Hf7Nxr/9A+aphCZlyvUbaTNJDoGSScUMMUy7jbzSkowEstXGnNPQSXJkPKbXrFlddkgM/wjbjpJVDv15Yik7/cZPaPFL2xpFjDtzrwU6aD4aQALZFrJSwYW4xahT5sQKD12FopjmRy6xHRnH7s72+qCUiJuGzsSDRydrtPDK5k=
---

# 沧州市劝学路小学智能体（czqxl-agent）

基于 LangChain 架构的教育智能体系统，面向小学场景提供四大核心能力：

| 模块     | 说明                             |
| ------ | ------------------------------ |
| 通用问答   | 多轮对话、学习辅导、知识答疑（SSE 流式）         |
| 教案一键生成 | 输入课题/学科/年级/课时，生成结构化完整教案        |
| 学校信息问答 | RAG 知识库增强问答，引用来源标注             |
| 智能试卷研判 | 试卷上传/粘贴，逐题解析、知识点标注、学情统计、研判报告导出 |

技术栈：**FastAPI + LangChain + SQLAlchemy + Vue3 + TypeScript + Vite + Element Plus + MySQL/Redis + Milvus(可选)**

***

## 1. 项目结构

```
czqxl-agent/
├── backend/                      # 后端服务（FastAPI）
│   ├── app/
│   │   ├── main.py               # 应用入口（CORS、路由注册、健康检查）
│   │   ├── config.py             # 环境配置（pydantic-settings）
│   │   ├── database.py           # SQLAlchemy 引擎/会话
│   │   ├── models/entities.py    # ORM 模型（10 张表）
│   │   ├── schemas/              # Pydantic 请求/响应模型
│   │   ├── routers/              # 四大模块 + 认证 + 知识库 API
│   │   ├── services/             # 业务服务层
│   │   │   ├── llm_factory.py    # LLM 统一接入（API/vLLM 双模式+降级）
│   │   │   ├── chat_service.py   # 通用问答（多轮、敏感词、流式）
│   │   │   ├── lesson_service.py # 教案生成（结构化+导出）
│   │   │   ├── school_info_service.py # 学校信息问答（RAG+引用）
│   │   │   ├── exam_service.py   # 试卷研判（逐题分析+学情统计+报告）
│   │   │   ├── rag_pipeline.py   # RAG 链路（检索+生成）
│   │   │   ├── doc_parser.py     # 文档解析（PDF/Word/Excel/OCR）
│   │   │   └── session_manager.py# 会话与消息持久化
│   │   ├── knowledge/            # 知识库接入层（向量后端可切换）
│   │   │   ├── vector_store.py   # memory / milvus / pgvector 后端
│   │   │   └── ingest.py         # 入库流程（解析-分块-向量化）
│   │   └── utils/                # SSE、安全、日志、限流
│   ├── scripts/
│   │   ├── init_db.py            # 建表（SQLite 开发/MySQL 生产）
│   │   ├── init_vector_db.py     # 初始化向量库集合
│   │   ├── create_admin.py       # 创建管理员账号
│   │   └── ingest_kb.py          # 知识库批量导入 CLI
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/                     # 前端服务（Vue3 + TS + Element Plus）
│   ├── src/
│   │   ├── api/                  # API 封装 + SSE 流式解析
│   │   ├── views/                # 四大模块页面
│   │   ├── layout/               # 主框架布局
│   │   ├── router/ stores/ types/
│   ├── package.json / vite.config.ts
│   ├── Dockerfile / nginx.conf
├── docs/schema.sql               # MySQL 建表脚本（开发文档第 4 章）
├── docker-compose.yml            # MySQL/Redis/MinIO + 后端 + 前端
└── README.md
```

***

## 2. 快速启动（本地开发）

### 2.1 后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows；Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # 按需修改 LLM 配置

# 初始化数据库（默认 SQLite，无需 MySQL 即可跑通）
python scripts/init_db.py

# 创建管理员账号
python scripts/create_admin.py --username admin --password admin123456

conda activate czqxl-backend
cd C:\Users\zhangxiang\Desktop\output\output\czqxl-agent\backend
uvicorn app.main:app --reload
```

### 2.2 前端

cd C:\Users\zhangxiang\Desktop\output\output\czqxl-agent\frontend
npm run dev

```bash
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ";" + [Environment]::GetEnvironmentVariable('Path','User')
npm run dev
```

浏览器访问 `http://127.0.0.1:5173`，用 `admin / admin123456` 登录。

***

## 3. LLM 模型配置

系统支持 **API 模式（OpenAI 兼容）** 与 **本地 vLLM 模式** 双接入，可在 `.env` 中切换，模型不可用时自动降级到备用模型。

| 环境变量               | 说明                                   | 示例                              |
| ------------------ | ------------------------------------ | ------------------------------- |
| `LLM_MODE`         | `api`（OpenAI 兼容接口）或 `local`（本地 vLLM） | `api`                           |
| `LLM_BASE_URL`     | API 模式 Base 地址                       | `https://api.deepseek.com/v1`   |
| `LLM_API_KEY`      | API Key                              | `sk-xxx`                        |
| `LLM_MODEL`        | 主模型                                  | `deepseek-chat`                 |
| `LLM_MODEL_STRONG` | 复杂任务模型（教案/试卷研判）                      | `deepseek-chat`                 |
| `VLLM_BASE_URL`    | local 模式 Base 地址（vLLM 的 /v1 端点）      | `http://127.0.0.1:8000/v1`      |
| `VLLM_MODEL`       | local 模式模型名                          | `Qwen/Qwen2.5-7B-Instruct`      |
| `FALLBACK_LLM_*`   | 降级通道（主模型失败时自动切换）                     | `FALLBACK_LLM_MODEL=qwen-turbo` |

vLLM 本地部署示例：

```bash
vllm serve Qwen/Qwen2.5-7B-Instruct --served-model-name Qwen/Qwen2.5-7B-Instruct --port 8000
# 然后在 .env 中设置 LLM_MODE=local、VLLM_BASE_URL=http://127.0.0.1:8000/v1
```

***

## 4. 知识库导入

学校信息问答（RAG）依赖知识库文档。支持：`pdf / docx / doc / xlsx / xls / pptx / txt / md / png / jpg / jpeg`。

```bash
cd backend

# 方式一：批量导入目录（推荐：目录名即知识域，如 kb_docs/招生）
mkdir -p kb_docs/招生 kb_docs/作息
# 将学校文件放入对应目录后：
python scripts/ingest_kb.py --dir ./kb_docs

# 方式二：导入单个文件并指定知识域
python scripts/ingest_kb.py --file ./kb_docs/招生简章.pdf --category 招生

# 方式三：管理员在前端「知识库」接口上传（/api/kb/upload）
```

向量库后端通过 `VECTOR_BACKEND` 切换：

- `memory`（默认）：内存关键词检索，**无需 Milvus 即可直接运行**，适合小规模/演示；
- `milvus`：生产环境，需部署 Milvus（参考 docker-compose）；
- `pgvector`：若使用 PostgreSQL 可选用。

***

## 5. Docker 部署（服务器）

```bash
# 1. 准备环境变量
cp backend/.env.example .env
# 修改 .env 中的 LLM / 数据库密码等

# 2. 构建并启动（MySQL/Redis/MinIO + 后端 + 前端）
docker compose up -d --build

# 3. 初始化管理员
docker compose exec backend python scripts/create_admin.py --username admin --password admin123456

# 4. 导入知识库
docker compose exec backend python scripts/ingest_kb.py --dir ./kb_docs

# 5. 访问
# 前端: http://服务器IP:8080
# 后端API: http://服务器IP:8000/api  (健康检查 /health)
```

> 说明：前端 Nginx 已配置 `/api` 反向代理且**关闭 SSE 缓冲**（`proxy_buffering off`），流式输出实时到达浏览器。

***

## 6. 主要 API 一览

| 模块   | 方法   | 路径                                       | 说明              |
| ---- | ---- | ---------------------------------------- | --------------- |
| 认证   | POST | `/api/auth/login`                        | 登录获取 Token      |
| 通用问答 | POST | `/api/chat/sessions`                     | 创建会话            |
| 通用问答 | POST | `/api/chat/chat`                         | SSE 流式多轮对话      |
| 教案   | POST | `/api/lesson/generate`                   | 一键生成教案          |
| 教案   | GET  | `/api/lesson/plans/{id}/export?fmt=docx` | 导出 Word         |
| 学校信息 | POST | `/api/school_info/chat`                  | RAG 问答（SSE，含引用） |
| 试卷   | POST | `/api/exam/upload`                       | 上传试卷解析          |
| 试卷   | POST | `/api/exam/{id}/analyze`                 | 逐题智能分析          |
| 试卷   | GET  | `/api/exam/{id}/report/export`           | 导出研判报告 Word     |
| 知识库  | POST | `/api/kb/upload`                         | 文档入库            |

***

## 7. 注意事项

- 默认数据库为 SQLite（`data/school_agent.db`），生产环境切换 MySQL：设置 `DATABASE_URL` 后重新 `init_db.py` 或用 `docs/schema.sql` 建表。
- SSE 流式接口在生产 Nginx 部署时**务必保留** **`proxy_buffering off`**。
- 试卷图片识别（OCR）需要安装 `rapidocr_onnxruntime`（已列入 requirements 可选依赖）。
- 系统提示词与敏感词策略位于 `app/prompts/`，可按学校实际情况调整。
  *（内容由AI生成，仅供参考）*

