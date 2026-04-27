import uuid
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, get_optional_user
from app.policies.models import Policy, User, ChatLog, ChatSession
from app.policies.schemas import ChatAskRequest, ChatAskResponse, ChatHistoryResponse, SessionResponse
from app.chat.service import ChatService
from app.extraction.llm_providers import get_llm_provider
from app.policies.service import PolicyService

router = APIRouter(prefix="/api/chat", tags=["问答"])


@router.post("/ask", response_model=ChatAskResponse)
async def ask_question(
    request: ChatAskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    user_id = current_user.id if current_user else None

    if request.session_id:
        query = select(ChatSession).where(ChatSession.id == request.session_id)
        if user_id:
            query = query.where(ChatSession.user_id == user_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        if not session:
            session = ChatSession(id=request.session_id, user_id=user_id, name=request.question[:50] or "新会话")
            db.add(session)
    else:
        session_id = uuid.uuid4()
        session = ChatSession(
            id=session_id,
            user_id=user_id,
            name=request.question[:50] or "新会话",
        )
        db.add(session)
        await db.flush()
        session_id = session.id

    service = ChatService(db)
    result = await service.answer_question(
        question=request.question,
        user_id=user_id,
        session_id=session_id,
        model_provider=request.model_provider,
    )

    session.name = request.question[:50] or "新会话"
    session.updated_at = func.now()
    await db.commit()

    return ChatAskResponse(
        answer=result["answer"],
        session_id=session_id,
        cited_policies=result["cited_policies"],
    )


@router.post("/ask/stream")
async def ask_stream(
    request: ChatAskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    user_id = current_user.id if current_user else None

    if request.session_id:
        query = select(ChatSession).where(ChatSession.id == request.session_id)
        if user_id:
            query = query.where(ChatSession.user_id == user_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        if not session:
            session = ChatSession(id=request.session_id, user_id=user_id, name=request.question[:50] or "新会话")
            db.add(session)
            await db.flush()
    else:
        session_id = uuid.uuid4()
        session = ChatSession(
            id=session_id,
            user_id=user_id,
            name=request.question[:50] or "新会话",
        )
        db.add(session)
        await db.flush()
        request.session_id = session_id

    async def generate():
        import time
        start_time = time.time()
        provider = get_llm_provider(request.model_provider)

        from app.chat.service import ChatService as CS
        service = CS(db)
        intent = await service._route_question(request.question, provider)
        matched = await service._get_matched_policies(intent)

        history_logs = []
        if request.session_id:
            result = await db.execute(
                select(ChatLog)
                .where(ChatLog.session_id == request.session_id)
                .order_by(ChatLog.created_at.desc())
                .limit(6)
            )
            history_logs = list(result.scalars().all()[::-1])

        history_parts = []
        for log in history_logs:
            history_parts.append(f"用户：{log.question}")
            history_parts.append(f"助手：{log.answer}")
        history_str = "\n".join(history_parts)

        cited = service._build_cited_policies(matched, intent)

        SYSTEM_PROMPT_ANSWER = """你是一个专业的政策问答助手。你的职责是根据提供的政策结构化数据，准确回答用户的问题。

回答原则：
1. 答案必须严格基于提供的政策结构化数据，不要编造信息
2. 如果提供的数据中包含相关政策信息，请基于这些信息给出准确回答
3. 如果数据中没有相关信息，请明确告知用户，而不是猜测
4. 回答应该清晰、有条理，适当使用列表和结构化格式
5. 回答中应引用具体的政策名称和数据来源
6. 如果当前问题与之前的对话历史相关，请结合历史上下文综合回答

请根据"【用户当前问题】"中的问题，结合以下上下文进行回答："""

        context = service._build_context(request.question, history_str, matched, intent)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_ANSWER},
            {"role": "user", "content": context},
        ]

        full_answer = ""
        try:
            async for delta in provider.generate_stream(messages):
                full_answer += delta
                yield f"data: {json.dumps({'type': 'content', 'delta': delta})}\n\n"

            elapsed_ms = int((time.time() - start_time) * 1000)

            chat_log = ChatLog(
                user_id=user_id,
                session_id=request.session_id,
                question=request.question,
                answer=full_answer,
                model_provider=provider.provider_name,
                model_name=provider.model_name,
                response_time_ms=elapsed_ms,
                cited_policies=cited,
            )
            db.add(chat_log)
            session.name = request.question[:50] or "新会话"
            await db.commit()

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'session_id': str(request.session_id), 'cited_policies': cited})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/history/{session_id}", response_model=list[ChatHistoryResponse])
async def get_history(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .where(ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")

    result = await db.execute(
        select(ChatLog)
        .where(ChatLog.session_id == session_id)
        .order_by(ChatLog.created_at.asc())
    )
    logs = result.scalars().all()
    return [ChatHistoryResponse.model_validate(log) for log in logs]


@router.get("/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(50)
    )
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "created_at": str(s.created_at),
            "updated_at": str(s.updated_at),
        }
        for s in sessions
    ]


@router.post("/sessions/{session_id}/rename")
async def rename_session(
    session_id: UUID,
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .where(ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    session.name = name
    await db.commit()
    return {"message": "会话重命名成功", "name": name}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .where(ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    await db.delete(session)
    await db.commit()
    return {"message": "会话删除成功"}
