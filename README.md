# Policy QA Agent (政策问答智能体)

[English](#english) | [中文](#中文)

---

## English

### Overview

**Policy QA Agent** is an intelligent policy Q&A platform built with RAG (Retrieval-Augmented Generation) and Large Language Models. It supports automatic policy document parsing, semantic Q&A, timeline visualization, and policy compatibility analysis.

### Features

- **Smart Q&A**: Ask questions in natural language and get accurate answers with source citations
- **Document Parsing**: Upload PDF/Word documents, automatically extract key information
- **Timeline View**: Visualize policy dates (application start, deadline, etc.)
- **Policy Comparison**: Analyze overlapping and mutually exclusive relationships between policies
- **Knowledge Graph**: Visualize policy structure and relationships
- **Admin Dashboard**: Manage policies and monitor query statistics

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 + Tailwind CSS + Radix UI + TypeScript |
| Backend | FastAPI + Python 3.11+ |
| Database | SQLite |
| Vector Store | ChromaDB |
| LLM | Alibaba Cloud Tongyi Qianwen (DashScope) |
| Container | Docker & Docker Compose |

### Quick Start

#### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (optional)
- Alibaba Cloud DashScope API Key

#### Method 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/V123d/policy_question.git
cd policy_question

# Configure environment variables
cp backend/.env.example backend/.env
# Edit backend/.env and add your DASHSCOPE_API_KEY

# Start all services
docker-compose up -d
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

#### Method 2: Manual Setup

**Backend:**

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your DASHSCOPE_API_KEY
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

### Usage

1. Open http://localhost:3000/admin to access the admin dashboard
2. Upload a policy PDF/Word file
3. Wait for parsing to complete (automatic key point extraction)
4. Go to http://localhost:3000/chat to start asking questions

### Project Structure

```
policy_question/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── config.py         # Configuration
│   │   ├── auth/             # Authentication
│   │   ├── chat/             # Q&A module
│   │   ├── policies/         # Policy management
│   │   ├── extraction/       # Document parsing
│   │   ├── knowledge_graph/  # Knowledge graph
│   │   └── services/         # Business logic (RAG, LLM)
│   ├── uploads/              # Uploaded files
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── (user)/          # User pages
│   │   │   ├── chat/        # Q&A interface
│   │   │   ├── timeline/    # Policy timeline
│   │   │   ├── policies/    # Policy library
│   │   │   └── page.tsx     # Home
│   │   ├── (auth)/          # Auth pages
│   │   │   ├── login/
│   │   │   └── register/
│   │   └── (admin)/         # Admin pages
│   ├── components/          # UI components
│   ├── context/             # React context
│   ├── lib/                 # Utilities
│   ├── package.json
│   └── Dockerfile
├── data/                    # Data directory
│   ├── policies/            # Original policy files
│   └── chroma/             # ChromaDB vector data
├── docker-compose.yml
└── README.md
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/register` | User registration |
| GET | `/api/policies` | List all policies |
| POST | `/api/policies/upload` | Upload policy document |
| GET | `/api/policies/{id}` | Get policy details |
| POST | `/api/chat` | Submit Q&A query |
| GET | `/api/chat/history` | Get chat history |
| GET | `/api/knowledge-graph` | Get knowledge graph data |

### Environment Variables

```env
# Backend (.env)
DASHSCOPE_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///./policy_qa.db
CHROMA_PATH=./chroma
```

```env
# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### License

MIT License

---

## 中文

### 项目简介

**政策问答智能体** 是一个基于 RAG（检索增强生成）和大语言模型的智能政策问答平台。支持政策文档自动解析、智能语义问答、时间轴可视化和政策叠加互斥分析。

### 主要功能

- **智能问答**: 自然语言提问，自动检索政策文档并生成准确答案，附带来源引用
- **文档解析**: 支持上传 PDF/Word 文档，自动提取政策要点
- **时间轴展示**: 可视化展示申报开始/截止等时间节点
- **政策对比**: 分析多政策间的叠加适用和互斥关系
- **知识图谱**: 可视化政策结构和关联关系
- **管理后台**: 政策管理、查询统计、用户管理

### 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | Next.js 14 + Tailwind CSS + Radix UI + TypeScript |
| 后端 | FastAPI + Python 3.11+ |
| 数据库 | SQLite |
| 向量库 | ChromaDB |
| 大模型 | 阿里云通义千问（DashScope） |
| 容器化 | Docker & Docker Compose |

### 快速开始

#### 前置条件

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose（可选）
- 阿里云 DashScope API Key

#### 方式一：Docker 部署（推荐）

```bash
# 克隆仓库
git clone https://github.com/V123d/policy_question.git
cd policy_question

# 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入你的 DASHSCOPE_API_KEY

# 启动所有服务
docker-compose up -d
```

访问地址：
- 前端页面：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

#### 方式二：本地开发

**后端：**

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 DASHSCOPE_API_KEY
uvicorn app.main:app --reload --port 8000
```

**前端：**

```bash
cd frontend
npm install
npm run dev
```

### 使用说明

1. 打开 http://localhost:3000/admin 进入管理后台
2. 上传一份政策 PDF/Word 文件
3. 等待解析完成（自动提取要点、入库向量库）
4. 回到前台 http://localhost:3000/chat 开始提问

### 项目结构

```
policy_question/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── config.py       # 配置文件
│   │   ├── auth/           # 用户认证
│   │   ├── chat/           # 问答模块
│   │   ├── policies/        # 政策管理
│   │   ├── extraction/     # 文档解析
│   │   ├── knowledge_graph/ # 知识图谱
│   │   └── services/       # 业务逻辑（RAG、LLM）
│   ├── uploads/            # 上传文件目录
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # 前端应用
│   ├── app/
│   │   ├── (user)/         # 用户页面
│   │   │   ├── chat/       # 智能问答
│   │   │   ├── timeline/   # 政策时间轴
│   │   │   ├── policies/   # 政策库
│   │   │   └── page.tsx    # 首页
│   │   ├── (auth)/         # 认证页面
│   │   │   ├── login/
│   │   │   └── register/
│   │   └── (admin)/        # 管理后台
│   ├── components/         # UI 组件
│   ├── context/            # React 上下文
│   ├── lib/                # 工具函数
│   ├── package.json
│   └── Dockerfile
├── data/                   # 数据目录
│   ├── policies/           # 原始政策文件
│   └── chroma/            # ChromaDB 向量数据
├── docker-compose.yml
└── README.md
```

### API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/register` | 用户注册 |
| GET | `/api/policies` | 获取政策列表 |
| POST | `/api/policies/upload` | 上传政策文档 |
| GET | `/api/policies/{id}` | 获取政策详情 |
| POST | `/api/chat` | 提交问答查询 |
| GET | `/api/chat/history` | 获取聊天历史 |
| GET | `/api/knowledge-graph` | 获取知识图谱数据 |

### 环境变量

```env
# 后端 (.env)
DASHSCOPE_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///./policy_qa.db
CHROMA_PATH=./chroma
```

```env
# 前端 (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### License

MIT License
