from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user
from app.policies.models import Policy, User
from app.policies.schemas import KGGraphResponse, KGSubgraphResponse, KGNodeResponse, KGEdgeResponse, PolicyResponse
from app.policies.service import KGService, PolicyService

router = APIRouter(prefix="/api/kg", tags=["知识图谱"])


@router.get("/graph", response_model=KGGraphResponse)
async def get_full_graph(db: AsyncSession = Depends(get_db)):
    service = KGService(db)
    nodes, edges = await service.get_full_graph()
    return KGGraphResponse(
        nodes=[KGNodeResponse.model_validate(n) for n in nodes],
        edges=[KGEdgeResponse.model_validate(e) for e in edges],
    )


@router.get("/policy/{policy_id}", response_model=KGSubgraphResponse)
async def get_policy_subgraph(policy_id: UUID, db: AsyncSession = Depends(get_db)):
    kg_service = KGService(db)
    policy_service = PolicyService(db)

    nodes, edges = await kg_service.get_policy_subgraph(policy_id)
    policy = await policy_service.get_policy(policy_id)

    if not policy:
        raise HTTPException(status_code=404, detail="政策不存在")

    return KGSubgraphResponse(
        nodes=[KGNodeResponse.model_validate(n) for n in nodes],
        edges=[KGEdgeResponse.model_validate(e) for e in edges],
        policy=PolicyResponse.model_validate(policy),
    )


@router.get("/nodes")
async def query_nodes(
    policy_id: Optional[UUID] = None,
    node_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.policies.models import KGNode

    query = select(KGNode)
    if policy_id:
        query = query.where(KGNode.policy_id == policy_id)
    if node_type:
        query = query.where(KGNode.node_type == node_type)

    result = await db.execute(query)
    nodes = result.scalars().all()
    return [KGNodeResponse.model_validate(n) for n in nodes]
