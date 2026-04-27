import os
import uuid
import aiofiles
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_admin, get_current_user
from app.policies.models import Policy, User, ChatLog
from app.auth.schemas import UserResponse
from app.policies.schemas import (
    PolicyListItem,
    PolicyResponse,
    PolicyUpdate,
    PolicyUploadResponse,
    ChatLogResponse,
    DashboardStats,
)
from app.policies.service import PolicyService, ChatService, UserService, KGService, AttachmentService
from app.extraction.parser import DocumentParser
from app.extraction.extractor import PolicyExtractor
from app.config import get_settings

router = APIRouter(prefix="/api/admin", tags=["管理后台"])
settings = get_settings()


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    ps = PolicyService(db)
    cs = ChatService(db)
    us = UserService(db)

    total = await db.execute(select(func.count(Policy.id)))
    total_policies = total.scalar() or 0

    active = await db.execute(select(func.count(Policy.id)).where(Policy.status == "active"))
    active_policies = active.scalar() or 0

    parsing = await db.execute(select(func.count(Policy.id)).where(Policy.status == "parsing"))
    parsing_policies = parsing.scalar() or 0

    failed = await db.execute(select(func.count(Policy.id)).where(Policy.status == "failed"))
    failed_policies = failed.scalar() or 0

    total_users = await us.count_users()

    total_chats_result = await db.execute(select(func.count(ChatLog.id)))
    total_chats = total_chats_result.scalar() or 0

    chats_today = await cs.get_chats_today()
    chats_this_week = await cs.get_chats_this_week()

    success_rate = (active_policies / total_policies * 100) if total_policies > 0 else 0.0

    return DashboardStats(
        total_policies=total_policies,
        active_policies=active_policies,
        parsing_policies=parsing_policies,
        failed_policies=failed_policies,
        total_users=total_users,
        total_chats=total_chats,
        chats_today=chats_today,
        chats_this_week=chats_this_week,
        parse_success_rate=round(success_rate, 1),
    )


@router.post("/policies/upload", response_model=PolicyUploadResponse)
async def upload_policy(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    os.makedirs(settings.upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in [".pdf", ".docx", ".doc"]:
        raise HTTPException(status_code=400, detail="仅支持 PDF、DOCX、DOC 格式")

    file_id = str(uuid.uuid4())
    file_path = os.path.join(settings.upload_dir, f"{file_id}{ext}")

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        if len(content) > settings.max_file_size_bytes:
            raise HTTPException(status_code=400, detail=f"文件大小不能超过 {settings.max_file_size_mb}MB")
        await f.write(content)

    policy_service = PolicyService(db)
    policy = await policy_service.create_policy(
        name=file.filename or "未命名政策",
        uploader_id=current_user.id,
        file_path=file_path,
    )

    try:
        parser = DocumentParser()
        if ext == ".pdf":
            raw_text = parser.parse_pdf(file_path)
        else:
            raw_text = parser.parse_docx(file_path)

        policy.raw_text = raw_text
        policy.raw_text_updated_at = datetime.utcnow()
        await db.commit()

        extractor = PolicyExtractor()
        result = await extractor.extract(raw_text, policy.id)

        await policy_service.update_structured_data(
            policy_id=policy.id,
            structured_data=result.get("structured_data", {}),
            doc_type=result.get("doc_type"),
            policy_level=result.get("policy_level"),
            issuing_body=result.get("issuing_body"),
            policy_subject=result.get("policy_subject"),
            effective_date=result.get("effective_date"),
            deadline=result.get("deadline"),
            consultation_contact=result.get("consultation_contact"),
            consultation_phone=result.get("consultation_phone"),
            consultation_website=result.get("consultation_website"),
        )

        kg_service = KGService(db)
        await kg_service.build_graph_from_policy(
            policy_id=policy.id,
            structured_data=result.get("structured_data", {}),
            policy_name=result.get("policy_name", file.filename or "政策"),
        )

        return PolicyUploadResponse(
            id=policy.id,
            name=policy.name,
            status=policy.status,
            doc_type=policy.doc_type,
            policy_level=policy.policy_level,
            message="政策解析成功",
        )

    except Exception as e:
        await policy_service.update_status(policy.id, "failed")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.post("/policies/upload-text")
async def upload_policy_text(
    name: str = Form(...),
    raw_text: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    policy_service = PolicyService(db)
    policy = await policy_service.create_policy(
        name=name,
        uploader_id=current_user.id,
    )
    policy.raw_text = raw_text
    policy.raw_text_updated_at = datetime.utcnow()
    await db.commit()

    try:
        extractor = PolicyExtractor()
        result = await extractor.extract(raw_text, policy.id)

        await policy_service.update_structured_data(
            policy_id=policy.id,
            structured_data=result.get("structured_data", {}),
            doc_type=result.get("doc_type"),
            policy_level=result.get("policy_level"),
            issuing_body=result.get("issuing_body"),
            policy_subject=result.get("policy_subject"),
            effective_date=result.get("effective_date"),
            deadline=result.get("deadline"),
            consultation_contact=result.get("consultation_contact"),
            consultation_phone=result.get("consultation_phone"),
            consultation_website=result.get("consultation_website"),
        )

        kg_service = KGService(db)
        await kg_service.build_graph_from_policy(
            policy_id=policy.id,
            structured_data=result.get("structured_data", {}),
            policy_name=result.get("policy_name", name),
        )

        return PolicyUploadResponse(
            id=policy.id,
            name=policy.name,
            status=policy.status,
            doc_type=policy.doc_type,
            policy_level=policy.policy_level,
            message="政策解析成功",
        )

    except Exception as e:
        await policy_service.update_status(policy.id, "failed")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.patch("/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: UUID,
    data: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    service = PolicyService(db)
    policy = await service.update_policy(policy_id, data)
    if not policy:
        raise HTTPException(status_code=404, detail="政策不存在")
    return PolicyResponse.model_validate(policy)


@router.delete("/policies/{policy_id}")
async def delete_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    service = PolicyService(db)
    if not await service.delete_policy(policy_id):
        raise HTTPException(status_code=404, detail="政策不存在")
    return {"message": "删除成功"}


@router.get("/policies", response_model=list[PolicyListItem])
async def admin_list_policies(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    service = PolicyService(db)
    policies = await service.list_policies(status=status, skip=skip, limit=limit)
    return [PolicyListItem.model_validate(p) for p in policies]


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    service = UserService(db)
    users = await service.list_users(skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    role: str = Query(..., pattern="^(admin|user)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    service = UserService(db)
    user = await service.update_user_role(user_id, role)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    service = UserService(db)
    if not await service.delete_user(user_id):
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"message": "删除成功"}


@router.get("/queries", response_model=list[ChatLogResponse])
async def list_chat_logs(
    skip: int = 0,
    limit: int = 50,
    user_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    service = ChatService(db)
    logs = await service.get_all_logs(skip=skip, limit=limit, user_id=user_id)
    return [ChatLogResponse.model_validate(log) for log in logs]


@router.post("/re-parse/{policy_id}", response_model=PolicyUploadResponse)
async def reparse_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    policy_service = PolicyService(db)
    policy = await policy_service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="政策不存在")

    if not policy.raw_text:
        raise HTTPException(status_code=400, detail="政策原始文本为空，请先上传文件")

    await policy_service.update_status(policy_id, "parsing")

    try:
        extractor = PolicyExtractor()
        result = await extractor.extract(policy.raw_text, policy.id)

        await policy_service.update_structured_data(
            policy_id=policy.id,
            structured_data=result.get("structured_data", {}),
            doc_type=result.get("doc_type"),
            policy_level=result.get("policy_level"),
            issuing_body=result.get("issuing_body"),
            policy_subject=result.get("policy_subject"),
            effective_date=result.get("effective_date"),
            deadline=result.get("deadline"),
            consultation_contact=result.get("consultation_contact"),
            consultation_phone=result.get("consultation_phone"),
            consultation_website=result.get("consultation_website"),
        )

        kg_service = KGService(db)
        await kg_service.build_graph_from_policy(
            policy_id=policy.id,
            structured_data=result.get("structured_data", {}),
            policy_name=result.get("policy_name", policy.name),
        )

        return PolicyUploadResponse(
            id=policy.id,
            name=policy.name,
            status=policy.status,
            doc_type=policy.doc_type,
            policy_level=policy.policy_level,
            message="重新解析成功",
        )

    except Exception as e:
        await policy_service.update_status(policy_id, "failed")
        raise HTTPException(status_code=500, detail=f"重新解析失败: {str(e)}")
