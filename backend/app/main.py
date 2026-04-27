from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.auth.router import router as auth_router
from app.policies.router import router as policies_router
from app.policies.admin_router import router as admin_router
from app.chat.router import router as chat_router
from app.knowledge_graph.router import router as kg_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="政策问答智能体 API",
    version="2.0.0",
    description="重构后的政策问答系统，支持JWT认证、多LLM提供商、灵活结构化数据",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(policies_router)
app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(kg_router)


@app.get("/")
async def root():
    return {"message": "政策问答智能体 API v2.0", "version": "2.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
