from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, get_optional_user
from app.policies.models import Policy, User
from app.policies.schemas import (
    PolicyListItem,
    PolicyResponse,
    PolicyStructuredDataResponse,
)
from app.policies.service import PolicyService

router = APIRouter(prefix="/api/policies", tags=["政策"])


@router.get("", response_model=list[PolicyListItem])
async def list_policies(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    service = PolicyService(db)
    policies = await service.list_policies(status=status, skip=skip, limit=limit)
    return [PolicyListItem.model_validate(p) for p in policies]


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: UUID, db: AsyncSession = Depends(get_db)):
    service = PolicyService(db)
    policy = await service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="政策不存在")
    return PolicyResponse.model_validate(policy)


@router.get("/{policy_id}/structured", response_model=PolicyStructuredDataResponse)
async def get_policy_structured(policy_id: UUID, db: AsyncSession = Depends(get_db)):
    service = PolicyService(db)
    policy = await service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="政策不存在")

    consultation = {}
    if policy.consultation_contact:
        consultation["contact"] = policy.consultation_contact
    if policy.consultation_phone:
        consultation["phone"] = policy.consultation_phone
    if policy.consultation_website:
        consultation["website"] = policy.consultation_website

    return PolicyStructuredDataResponse(
        id=policy.id,
        name=policy.name,
        doc_type=policy.doc_type,
        policy_level=policy.policy_level,
        policy_subject=policy.policy_subject,
        effective_date=policy.effective_date,
        deadline=policy.deadline,
        consultation=consultation,
        structured_data=policy.structured_data or {},
    )


@router.get("/{policy_id}/raw-text")
async def get_raw_text(policy_id: UUID, db: AsyncSession = Depends(get_db)):
    service = PolicyService(db)
    policy = await service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="政策不存在")
    return {"raw_text": policy.raw_text or ""}


@router.get("/search/keyword")
async def search_policies(keyword: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    if not keyword or len(keyword.strip()) < 1:
        return []
    service = PolicyService(db)
    policies = await service.search_policies(keyword.strip(), limit=limit)
    return [PolicyListItem.model_validate(p) for p in policies]


@router.get("/timeline/all")
async def get_timeline(db: AsyncSession = Depends(get_db)):
    service = PolicyService(db)
    policies = await service.get_timeline_policies()
    result = []
    for p in policies:
        sd = p.structured_data or {}
        result.append({
            "id": str(p.id),
            "name": p.name,
            "deadline": str(p.deadline) if p.deadline else None,
            "effective_date": str(p.effective_date) if p.effective_date else None,
            "issuing_body": p.issuing_body,
            "doc_type": p.doc_type,
            "structured_data_keys": list(sd.keys()),
        })
    return result
